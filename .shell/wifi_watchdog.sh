#!/bin/sh
# (C) 2026 mlengle https://github.com/mlengle
# (C) 2026 ghzserg https://github.com/ghzserg/zmod
#
# Wi-Fi watchdog. Started by wifi.sh once zmod manages Wi-Fi; exits when it no longer does.
# wifi_reconnect.sh only reacts to wpa_supplicant events, so it cannot help when there is
# no event at all (no association after boot, a stuck link). Once a minute this checks wlan0
# and repairs only the broken step:
#   not associated 2 min        -> wpa_cli reassociate
#   not associated 4 min        -> full restart (wifi.sh)
#   associated, no IPv4 address -> wifi_reconnect.sh CONNECTED at minutes 1, 3, 7; restart at 10
#   gateway silent 3 min        -> reassociate; 6 min -> restart (only if the gateway has
#                                  answered ping/arping since association, so a router that
#                                  ignores ping never triggers anything)
#   wpa_supplicant not running  -> restart
# Restarts back off: gap 300 s, doubled after each one up to 3600 s; reset only when the
# gateway answers (association alone is not enough: an AP without DHCP would loop).
# A new wpa_supplicant PID means someone restarted Wi-Fi: the counters start over.
# Not covered: wlan0 missing (USB dongle gone) - nothing is done then.
# Usage: wifi_watchdog.sh start | run | once

source /usr/data/zmod/zmod/.shell/0.sh

IF=wlan0
ZSHELL=/usr/data/zmod/zmod/.shell
LOGDIR=${MOD_CONF}/mod_data/log
LOG=$LOGDIR/wifi_watchdog.log
STATE=/run/wifi_watchdog.state
PIDFILE=/run/wifi_watchdog.pid
BOOTCOPY=/run/wifi_watchdog.bootlog
INTERVAL=60
FIRST_DELAY=120
SCAN_WAIT=8
GAP_MIN=300
GAP_MAX=3600

log() {
    [ -f "$LOG" ] && [ "$(wc -c < "$LOG")" -gt 65536 ] && mv -f "$LOG" "$LOG.1"
    echo "$(date '+%F %T') $*" >> "$LOG"
}

# assoc_bad gw_bad dhcp_bad last_restart gap gw_seen wpa_pid
load_state() {
    assoc_bad=0; gw_bad=0; dhcp_bad=0; last_restart=0; gap=$GAP_MIN; gw_seen=0; wpa_pid=0
    [ -f "$STATE" ] && read -r assoc_bad gw_bad dhcp_bad last_restart gap gw_seen wpa_pid < "$STATE"
    case "$assoc_bad.$gw_bad.$dhcp_bad.$last_restart.$gap.$gw_seen.$wpa_pid" in
        *[!0-9.]*|*..*|.*|*.) assoc_bad=0; gw_bad=0; dhcp_bad=0; last_restart=0; gap=$GAP_MIN; gw_seen=0; wpa_pid=0 ;;
    esac
}
save_state() { echo "$assoc_bad $gw_bad $dhcp_bad $last_restart $gap $gw_seen $wpa_pid" > "$STATE"; }
reset_counters() { assoc_bad=0; gw_bad=0; dhcp_bad=0; gw_seen=0; gw_mute=0; }

uptime_s() { cut -d. -f1 /proc/uptime; }

# The conditions under which wifi.sh manages Wi-Fi (they can change without a reboot,
# e.g. Wi-Fi handed back to the stock screen)
zmod_manages_wifi() {
    [ -f ${MOD_CONF}/mod/SKIP_ZMOD ] || [ -f ${MOD_CONF}/mod/REMOVE ] || [ -f ${MOD_CONF}/mod/FULL_REMOVE ] && return 1
    grep -q "wifi = 1" ${MOD_CONF}/mod_data/variables.cfg || return 1
    [ -f "$FFCONFIG" ] || return 1
    grep -q -e '"wifiStationStatus" : true' -e '"ethernetStatus" : true' -e '"wifiHotspotStatus" : true' \
        -e '"isManual" : true' -e '"isUdhcpc" : false' "$FFCONFIG" && return 1
    grep '^[[:space:]]*ssid=' ${WPA_CONFIG} | grep -qv 'ssid="flashforge_5G"'
}

# wifi.sh or fix_config.sh (which starts wifi.sh at boot) is running. Checked only right
# before an action. busybox ps on AD5M has no -w, but prints full command lines into a pipe.
zmod_busy() {
    ps | grep -E '/wifi\.sh( |$)|/fix_config\.sh( |$)|S00fix' | grep -v grep >/dev/null
}

# Tells a stuck wpa_supplicant from a dead driver/USB chip: process state, kernel wait channel,
# operstate, USB device, and a fresh scan (age = seconds since the driver last saw our AP).
diag() {
    p=$(pidof wpa_supplicant | cut -d' ' -f1)
    ps_st=$(sed -n 's/^State:[[:space:]]*\([A-Z]\).*/\1/p' /proc/$p/status 2>/dev/null)
    wchan=$(cat /proc/$p/wchan 2>/dev/null)
    oper=$(cat /sys/class/net/$IF/operstate 2>/dev/null)
    dev=$(readlink -f /sys/class/net/$IF/device 2>/dev/null)
    usb=$(cat $dev/../idVendor $dev/../idProduct 2>/dev/null | tr '\n' ':')
    # AD5M: klogd keeps kernel lines in /var/log/messages (the dmesg ring is small); AD5X has no such file
    if [ -f /var/log/messages ]; then kmsg="cat /var/log/messages"; else kmsg=dmesg; fi
    usbdisc=$($kmsg 2>/dev/null | grep -c 'USB disconnect')
    usblast=$($kmsg 2>/dev/null | grep 'USB disconnect' | tail -1 | cut -c1-15)
    # wpa_cli waits up to 10 s per call on a hung wpa_supplicant: do not ask a dead or D-state one
    if [ -z "$p" ] || [ "$ps_st" = D ]; then
        [ -n "$p" ] && wst_txt="$ps_st ${wchan:-?}" || wst_txt="not running"
        log "  wpa_supplicant $wst_txt | $IF ${oper:-?} | usb ${usb:-none} disconnects ${usbdisc:-?} ${usblast} | wpa_cli skipped"
        return
    fi
    st=$(wpa_cli -i $IF status 2>/dev/null | grep -E '^(wpa_state|bssid|freq|ip_address)=' | tr '\n' ' ')
    log "  $st| wpa_supplicant $ps_st ${wchan:-?} | $IF ${oper:-?} | usb ${usb:-none} disconnects ${usbdisc:-?} ${usblast}"
    # a scan pulls the radio off the channel: not while associated
    case "$st" in *wpa_state=COMPLETED*) return ;; esac
    ssid=$(sed -n 's/^[[:space:]]*ssid="\(.*\)"/\1/p' ${WPA_CONFIG} | grep -v '^flashforge_5G$' | head -1)
    scan=$(wpa_cli -i $IF scan 2>/dev/null)
    case "$scan" in
        OK) sleep $SCAN_WAIT ;;
        FAIL-BUSY) ;;
        *) log "  scan ${scan:-no reply}"; return ;;
    esac
    # age = seconds since the driver last saw the AP; <= SCAN_WAIT means seen in this scan
    seen=$(wpa_cli -i $IF scan_results 2>/dev/null | awk -F'\t' -v s="$ssid" '$5 == s {print $1, $2 "MHz", $3 "dBm"}')
    ages=""
    for b in $(echo "$seen" | cut -d' ' -f1); do
        ages="$ages $(wpa_cli -i $IF bss $b 2>/dev/null | sed -n 's/^age=//p')s"
    done
    log "  scan $scan '$ssid': $(echo ${seen:-not seen}) age${ages:- -}"
}

reassociate() {
    log "$1: reassociate"
    diag
    wpa_cli -i $IF reassociate >/dev/null 2>&1
}

full_restart() {
    now=$(uptime_s)
    [ "$last_restart" -gt 0 ] && [ $((now - last_restart)) -lt "$gap" ] && return
    ngap=$gap
    if [ "$last_restart" -gt 0 ]; then
        ngap=$((gap * 2)); [ $ngap -gt $GAP_MAX ] && ngap=$GAP_MAX
    fi
    log "restart Wi-Fi: $1 (next restart not before $ngap s unless the gateway answers)"
    diag
    # diag takes seconds: a WIFI macro may have started wifi.sh meanwhile, do not run a second one
    if zmod_busy; then log "  wifi.sh started meanwhile: restart skipped"; return; fi
    gap=$ngap
    # wifi.sh rotates wifi.log; keep the boot one, it shows why the link never came up
    if [ ! -f "$BOOTCOPY" ] && [ -f "$LOGDIR/wifi.log" ]; then
        cp -f "$LOGDIR/wifi.log" "$LOGDIR/wifi_boot.log" && touch "$BOOTCOPY"
    fi
    last_restart=$now
    reset_counters
    save_state
    $ZSHELL/wifi.sh >/dev/null 2>&1
    wpa_pid=$(pidof wpa_supplicant | cut -d' ' -f1)
    wpa_pid=${wpa_pid:-0}
}

gw_alive() {
    # frames are arriving: the link is alive, no need to fork ping (once ping has armed gw_seen)
    read -r rx < /sys/class/net/$IF/statistics/rx_packets
    rx_ok=1; [ "$rx" = "$last_rx" ] && rx_ok=0; last_rx=$rx
    [ $rx_ok = 1 ] && { [ $gw_seen = 1 ] || [ "${gw_mute:-0}" -ge 3 ]; } && return 0
    # a gateway that never answered ping/arping: stop probing after 3 tries (until reassociation)
    [ $gw_seen = 0 ] && [ "${gw_mute:-0}" -ge 3 ] && return 1
    if ping -c 2 -W 3 "$1" >/dev/null 2>&1 || arping -I $IF -c 2 -w 3 "$1" >/dev/null 2>&1; then
        gw_seen=1; gw_mute=0; return 0
    fi
    [ $gw_seen = 0 ] && gw_mute=$(( ${gw_mute:-0} + 1 ))
    return 1
}

# Returns 1 when zmod no longer manages Wi-Fi. Each branch sets "act" to the repair, if any;
# it runs only when wifi.sh/fix_config.sh are not busy.
check_once() {
    [ -d /sys/class/net/$IF ] || return 0
    load_state
    act=""

    pid=$(pidof wpa_supplicant | cut -d' ' -f1)
    if [ -z "$pid" ]; then
        act="restart wpa_supplicant is not running"
    else
        [ "$pid" != "$wpa_pid" ] && reset_counters
        wpa_pid=$pid
        wst=$(wpa_cli -i $IF status 2>/dev/null | sed -n 's/^wpa_state=//p')
        addr=$(ip addr show dev $IF 2>/dev/null | sed -n 's/.*inet \([0-9.]*\).*/\1/p' | head -1)
        gw=$(ip route 2>/dev/null | sed -n "s/^default via \([0-9.]*\) dev $IF.*/\1/p" | head -1)

        if [ "$wst" != COMPLETED ]; then
            assoc_bad=$((assoc_bad + 1)); gw_bad=0; dhcp_bad=0; gw_seen=0; gw_mute=0
            if [ $assoc_bad -ge 4 ]; then
                act="restart not associated for $assoc_bad min (wpa_state=${wst:-none})"
            elif [ $assoc_bad -eq 2 ]; then
                act="reassoc not associated for 2 min (wpa_state=${wst:-none})"
            fi
        elif [ -z "$addr" ]; then
            [ $assoc_bad -ge 2 ] && log "associated again after $assoc_bad min"
            assoc_bad=0
            dhcp_bad=$((dhcp_bad + 1)); gw_bad=0; gw_seen=0; gw_mute=0
            if [ $dhcp_bad -ge 10 ]; then
                act="restart no IPv4 address for $dhcp_bad min"
            else
                case $dhcp_bad in 1|3|7) act="dhcp associated, no IPv4 address (minute $dhcp_bad)" ;; esac
            fi
        else
            [ $assoc_bad -ge 2 ] && log "associated again after $assoc_bad min"
            [ $dhcp_bad -gt 0 ] && log "got IPv4 address $addr after $dhcp_bad min"
            assoc_bad=0; dhcp_bad=0
            # no default route (DHCP without a gateway): nothing to probe
            if [ -n "$gw" ] && gw_alive "$gw"; then
                [ $gw_bad -gt 0 ] && log "gateway $gw answers again after $gw_bad min"
                [ $last_restart -gt 0 ] && log "network works after the restart"
                gw_bad=0; gap=$GAP_MIN; last_restart=0
            elif [ -n "$gw" ] && [ $gw_seen = 1 ]; then
                gw_bad=$((gw_bad + 1))
                if [ $gw_bad -ge 6 ]; then
                    act="restart gateway $gw silent for $gw_bad min"
                elif [ $gw_bad -eq 3 ]; then
                    act="reassoc gateway $gw silent for 3 min"
                elif [ $gw_bad -eq 1 ]; then
                    log "gateway $gw silent (ping and arping)"
                fi
            fi
        fi
    fi

    if [ -n "$act" ]; then
        zmod_manages_wifi || return 1
        zmod_busy && act=""
    fi
    case "$act" in
        restart*) full_restart "${act#restart }" ;;
        reassoc*) reassociate "${act#reassoc }" ;;
        dhcp*)
            log "${act#dhcp }: DHCP"
            $ZSHELL/wifi_reconnect.sh $IF CONNECTED >/dev/null 2>&1
            ;;
    esac
    save_state
}

case "$1" in
    start)
        # a stale pidfile may name a reused PID: trust it only if it is really us
        p=$(cat $PIDFILE 2>/dev/null)
        [ -n "$p" ] && tr '\0' ' ' < /proc/$p/cmdline 2>/dev/null | grep -q "wifi_watchdog.sh run" && exit 0
        rm -f $PIDFILE
        start-stop-daemon -S -q -b -m -p $PIDFILE -N 10 -a /bin/sh -- $ZSHELL/wifi_watchdog.sh run
        ;;
    once)
        check_once
        ;;
    run)
        trap 'rm -f $PIDFILE' EXIT
        rm -f "$STATE"
        up=$(uptime_s)
        [ "${up:-0}" -lt $FIRST_DELAY ] && sleep $((FIRST_DELAY - ${up:-0}))
        log "started"
        while :; do
            # save_variables rewrites variables.cfg in place: re-check before giving up
            check_once || { sleep 5; zmod_manages_wifi || break; }
            sleep $INTERVAL
        done
        log "stopped: zmod no longer manages Wi-Fi"
        ;;
    *)
        echo "Use $0 start|run|once"
        exit 1
        ;;
esac

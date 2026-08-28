#!/bin/sh
# (C) 2024-2026 ghzserg https://github.com/ghzserg/zmod

source /usr/data/zmod/zmod/.shell/0.sh

if ! [ $# -eq 1 ]; then echo "Use $0 on|off|test"; exit 1; fi

native_wifi_off()
{
    echo "Test native_wifi_off"
    if  grep -q "wifi = 1" /opt/config/mod_data/variables.cfg && \
        grep -q '"wifiHotspotStatus" : false' "$FFCONFIG" && \
        grep -q '"isManual" : false' "$FFCONFIG" && \
        grep -q '"isUdhcpc" : true' "$FFCONFIG" && \
        grep -q '"ethernetStatus" : false' "$FFCONFIG" && \
        grep -q "disabled=1" ${WPA_CONFIG}; then
            killall firmwareExe
            if grep -q '"wifiStationStatus" : true' "$FFCONFIG"; then
                echo "Z-Mod disabled wifiStationStatus on native screen"
                sed -i 's/"wifiStationStatus" : true/"wifiStationStatus" : false/' "$FFCONFIG"
                echo _REBOOT >/tmp/printer
                sync
                sleep 5
                /usr/data/zmod/zmod/.shell/zremote.sh reboot
            fi
    fi
    return 0
}

native_wifi_on()
{
    if [ ${C5PRO} -eq 1 ]; then exit; fi
    echo "Test native_wifi_on"
    if  grep -q "wifi = 1" /opt/config/mod_data/variables.cfg && \
        grep -q '"wifiHotspotStatus" : false' "$FFCONFIG" && \
        grep -q '"isManual" : false' "$FFCONFIG" && \
        grep -q '"isUdhcpc" : true' "$FFCONFIG" && \
        grep -q '"ethernetStatus" : false' "$FFCONFIG" && \
        grep -q "disabled=1" ${WPA_CONFIG}; then
            echo "Z-Mod enabled wifiStationStatus on native screen"
            killall firmwareExe
            grep -q '"wifiStationStatus" : false' "$FFCONFIG" && sed -i 's/"wifiStationStatus" : false/"wifiStationStatus" : true/' "$FFCONFIG"
    fi
    return 0
}

display_off()
{
    if [ ${C5PRO} -eq 1 ]; then exit; fi
    set -x
    if [ $1 = "test" ] && grep -q display_off.cfg /opt/config/printer.cfg; then
        killall firmwareExe helix-watchdog helix-screen helix-splash
        sleep 1
        if grep -q "guppy = 1" /opt/config/mod_data/variables.cfg || grep -q "helix = 1" /opt/config/mod_data/variables.cfg ; then
            /usr/data/zmod/zmod/.shell/zguppy.sh up
        else
            xzcat /usr/data/zmod/zmod/.shell/screen_off.raw.xz > /dev/fb0
        fi
        echo '/usr/data/zmod/zmod/.shell/automount.sh' > /proc/sys/kernel/hotplug
        native_wifi_off
    fi

    if [ $1 = "on" ]; then
        sed -i 's|\[include ./mod/display_off.cfg\]|\[include ./mod/mod.cfg\]|' /opt/config/printer.cfg
        sync
        native_wifi_on
        /usr/data/zmod/zmod/.shell/zremote.sh reboot
    fi

    if [ $1 = "off" ] || [ $1 = "guppy" ] || [ $1 = "helix" ]; then
        sed -i 's|\[include ./mod/mod.cfg\]|\[include ./mod/display_off.cfg\]|' /opt/config/printer.cfg
        sync
        killall firmwareExe guppyscreen console_log helix-watchdog helix-screen helix-splash
        [ -f /ZMOD ] && /usr/data/zmod/zmod/.shell/root/console_log --save --${ZLANG} || chroot ${MOD} /usr/data/zmod/zmod/.shell/root/console_log --save --${ZLANG}

        if [ $1 = "off" ]; then
            xzcat /usr/data/zmod/zmod/.shell/screen_off.raw.xz > /dev/fb0
        else
            /usr/data/zmod/zmod/.shell/zguppy.sh up
        fi

        echo '/usr/data/zmod/zmod/.shell/automount.sh' > /proc/sys/kernel/hotplug
        native_wifi_off
    fi

    sync
    echo 3 > /proc/sys/vm/drop_caches
}

mv ${MOD_CONF}/mod_data/log/display_off.4.log ${MOD_CONF}/mod_data/log/display_off.5.log 2>/dev/null
mv ${MOD_CONF}/mod_data/log/display_off.3.log ${MOD_CONF}/mod_data/log/display_off.4.log 2>/dev/null
mv ${MOD_CONF}/mod_data/log/display_off.2.log ${MOD_CONF}/mod_data/log/display_off.3.log 2>/dev/null
mv ${MOD_CONF}/mod_data/log/display_off.1.log ${MOD_CONF}/mod_data/log/display_off.2.log 2>/dev/null
mv ${MOD_CONF}/mod_data/log/display_off.log ${MOD_CONF}/mod_data/log/display_off.1.log 2>/dev/null
display_off "$1" &>${MOD_CONF}/mod_data/log/display_off.log

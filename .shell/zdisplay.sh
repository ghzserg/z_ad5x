#!/bin/sh
# (C) 2024-2026 ghzserg https://github.com/ghzserg/zmod

source /opt/config/mod/.shell/0.sh

if ! [ $# -eq 1 ]; then echo "Use $0 on|off|test"; exit 1; fi

wifi_off()
{
    echo "Test wifi_off"
    if  grep -q "wifi = 1" /opt/config/mod_data/variables.cfg && \
        grep -q '"wifiHotspotStatus" : false' "$FFCONFIG" && \
        grep -q '"isManual" : false' "$FFCONFIG" && \
        grep -q '"isUdhcpc" : true' "$FFCONFIG" && \
        grep -q '"ethernetStatus" : false' "$FFCONFIG" && \
        grep -q "disabled=1" ${WPA_CONFIG}; then
            echo "Z-Mod disabled wifiStationStatus on native screen"
            killall firmwareExe
            grep -q '"wifiStationStatus" : true' "$FFCONFIG" && sed -i 's/"wifiStationStatus" : true/"wifiStationStatus" : false/' "$FFCONFIG"
    fi
    return 0
}

wifi_on()
{
    echo "Test wifi_on"
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

if [ $1 = "test" ] && grep -q display_off.cfg /opt/config/printer.cfg; then
    killall firmwareExe helix-watchdog helix-screen helix-splash
    sleep 1
    if grep -q "guppy = 1" /opt/config/mod_data/variables.cfg || grep -q "helix = 1" /opt/config/mod_data/variables.cfg ; then
        /opt/config/mod/.shell/zguppy.sh up
    else
        xzcat /opt/config/mod/.shell/screen_off.raw.xz > /dev/fb0
    fi
    echo '/opt/config/mod/.shell/automount.sh' > /proc/sys/kernel/hotplug
    wifi_off
fi

if [ $1 = "on" ]; then
    sed -i 's|\[include ./mod/display_off.cfg\]|\[include ./mod/mod.cfg\]|' /opt/config/printer.cfg
    sync
    wifi_on
    /opt/config/mod/.shell/zremote.sh reboot
fi

if [ $1 = "off" ] || [ $1 = "guppy" ] || [ $1 = "helix" ]; then
    sed -i 's|\[include ./mod/mod.cfg\]|\[include ./mod/display_off.cfg\]|' /opt/config/printer.cfg
    sync
    killall firmwareExe guppyscreen console_log helix-watchdog helix-screen helix-splash
    [ -f /ZMOD ] && /opt/config/mod/.shell/root/console_log --save --${ZLANG} || chroot ${MOD} /opt/config/mod/.shell/root/console_log --save --${ZLANG}

    if [ $1 = "off" ]; then
        xzcat /opt/config/mod/.shell/screen_off.raw.xz > /dev/fb0
    else
        /opt/config/mod/.shell/zguppy.sh up
    fi

    echo '/opt/config/mod/.shell/automount.sh' > /proc/sys/kernel/hotplug
    wifi_off
fi

sync
echo 3 > /proc/sys/vm/drop_caches

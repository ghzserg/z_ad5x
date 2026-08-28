#!/bin/sh
# (C) 2024-2026 ghzserg https://github.com/ghzserg/zmod

source /usr/data/zmod/zmod/.shell/0.sh

case "$2" in
    CONNECTED)
        echo "connection established"
        echo "$(date): Wi-Fi connected, starting DHCP on $1" >>${MOD_CONF}/mod_data/log/wifi.log
        killall udhcpc >>${MOD_CONF}/mod_data/log/wifi.log 2>&1
        ip addr flush dev "$1" >>${MOD_CONF}/mod_data/log/wifi.log 2>&1
        udhcpc -i "$1" -b -R -T 3 -t 5 >>${MOD_CONF}/mod_data/log/wifi.log 2>&1
        ifconfig "$1" >>${MOD_CONF}/mod_data/log/wifi.log 2>&1
        ;;
    DISCONNECTED)
        echo "connection lost"
        echo "$(date): Wi-Fi disconnected on $1" >>${MOD_CONF}/mod_data/log/wifi.log
        killall udhcpc >>${MOD_CONF}/mod_data/log/wifi.log 2>&1
        ;;
esac

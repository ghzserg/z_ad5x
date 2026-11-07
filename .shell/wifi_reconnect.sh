#!/bin/sh
# (C) 2024-2026 ghzserg https://github.com/ghzserg/zmod

source /usr/data/zmod/zmod/.shell/0.sh

LOCK=/tmp/wifi_reconnect.lock
n=0
until mkdir $LOCK 2>/dev/null; do
    n=$((n+1)); [ $n -ge 30 ] && rmdir $LOCK
    sleep 1
done
trap 'rmdir $LOCK' EXIT

case "$2" in
    CONNECTED)
        [ "$3" = "check" ] && pidof udhcpc >/dev/null && exit 0
        echo "connection established"
        echo "$(date): Wi-Fi connected, starting DHCP on $1" >>${MOD_CONF}/mod_data/log/wifi.log
        killall udhcpc >>${MOD_CONF}/mod_data/log/wifi.log 2>&1
        ip addr flush dev "$1" >>${MOD_CONF}/mod_data/log/wifi.log 2>&1
        udhcpc -i "$1" -b -T 3 -t 5 >>${MOD_CONF}/mod_data/log/wifi.log 2>&1
        ifconfig "$1" >>${MOD_CONF}/mod_data/log/wifi.log 2>&1
        ;;
    DISCONNECTED)
        echo "connection lost"
        echo "$(date): Wi-Fi disconnected on $1" >>${MOD_CONF}/mod_data/log/wifi.log
        killall udhcpc >>${MOD_CONF}/mod_data/log/wifi.log 2>&1
        ;;
esac

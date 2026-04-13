#!/bin/sh

ip=$(ip addr | grep inet | grep wlan0 | awk -F" " '{print $2}'| sed -e 's/\/.*$//')
if [ "$ip" == "" ]; then
    ip=$(ip addr | grep inet | grep eth0 | awk -F" " '{print $2}'| sed -e 's/\/.*$//')
fi

if [ "$1" == 1 ]; then
    echo "SHOW_MSG TITLE=IP MSG='$ip'" >/tmp/printer
else
    echo "IP: $ip"
fi

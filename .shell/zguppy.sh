#!/bin/sh
# (C) 2024-2026 ghzserg https://github.com/ghzserg/zmod

source /usr/data/zmod/zmod/.shell/0.sh

unset LD_PRELOAD

up()
{
    umount /media 2>/dev/null
    echo '/usr/data/zmod/zmod/.shell/automount.sh' > /proc/sys/kernel/hotplug
    if [ -f /ZMOD ]; then
        /etc/init.d/S80guppyscreen start
    else
        chroot ${MOD} /etc/init.d/S80guppyscreen start &
        sleep 15
    fi
    echo '/usr/data/zmod/zmod/.shell/automount.sh' > /proc/sys/kernel/hotplug
    umount /media 2>/dev/null
}

stop()
{
    if [ -f /ZMOD ]; then
        /etc/init.d/S80guppyscreen stop
    else
        chroot ${MOD} /etc/init.d/S80guppyscreen stop &
        sleep 15
    fi
}

case "$1" in
    up)
        up
        ;;
    stop)
        stop
        ;;
    *)
        echo "Usage: $0 {stop|up}"
        exit 1
esac
sync
echo 3 > /proc/sys/vm/drop_caches
exit $?

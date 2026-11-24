#!/bin/sh
# Set the same timezone in the main system and chroot.

. /usr/data/zmod/zmod/.shell/0.sh

if [ -f /ZMOD ]; then
    /usr/data/zmod/zmod/.shell/zremote.sh /bin/sh /usr/data/zmod/zmod/.shell/set_timezone.sh "$@"
    exit $?
fi

[ "$#" -eq 1 ] || { echo "Usage: set_timezone.sh Europe/Moscow" >&2; exit 1; }
zone=$1

case "$zone" in
    ''|/*|*/|*..*|*'//'*) echo "Invalid timezone: $zone" >&2; exit 1 ;;
esac

[ -f "${MOD}/usr/share/zoneinfo/$zone" ] || {
    echo "Timezone not found: $zone" >&2
    exit 1
}

ln -sf "${MOD}/usr/share/zoneinfo/$zone" /etc/localtime || exit 1
rm -f "${MOD}/etc/localtime" || exit 1
cat /etc/localtime > "${MOD}/etc/localtime" || exit 1

echo "Timezone set to $zone in the main system and chroot"

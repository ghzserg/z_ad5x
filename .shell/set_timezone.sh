#!/bin/sh
# Use the same timezone in the main system and in chroot.

. /usr/data/zmod/zmod/.shell/0.sh

if [ -f /ZMOD ]; then
    /usr/data/zmod/zmod/.shell/zremote.sh /bin/sh /usr/data/zmod/zmod/.shell/set_timezone.sh "$@"
    exit $?
fi

ZONE_FILE="${MOD_CONF}/mod_data/timezone"

if [ "$1" = "--restore" ]; then
    [ -s "$ZONE_FILE" ] || exit 0
    zone=$(cat "$ZONE_FILE")
else
    [ "$#" -eq 1 ] || { echo "Usage: set_timezone.sh Europe/Moscow" >&2; exit 1; }
    zone=$1
fi

case "$zone" in
    ''|/*|*/|*..*|*'//'*) echo "Invalid timezone: $zone" >&2; exit 1 ;;
esac

[ -f "${MOD}/usr/share/zoneinfo/$zone" ] || {
    echo "Timezone not found: $zone" >&2
    exit 1
}

# The main system is the source of /etc/localtime for chroot.
ln -sf "${MOD}/usr/share/zoneinfo/$zone" /etc/localtime || exit 1
rm -f "${MOD}/etc/localtime" || exit 1
cat /etc/localtime > "${MOD}/etc/localtime" || exit 1

if [ "$1" != "--restore" ]; then
    printf '%s\n' "$zone" > "$ZONE_FILE" || exit 1
fi

echo "Timezone set to $zone in the main system and chroot"

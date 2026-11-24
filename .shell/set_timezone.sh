#!/bin/sh
# Set the same timezone in the main system and chroot.

. /usr/data/zmod/zmod/.shell/0.sh

message() {
    [ "$ZLANG" = "ru" ] && echo "$2" || echo "$1"
}

error() {
    message "$1" "$2" >&2
    exit 1
}

if [ -f /ZMOD ]; then
    /usr/data/zmod/zmod/.shell/zremote.sh /bin/sh /usr/data/zmod/zmod/.shell/set_timezone.sh "$@"
    exit $?
fi

[ "$#" -eq 1 ] || error "Usage: set_timezone.sh Europe/Moscow" "Использование: set_timezone.sh Europe/Moscow"
zone=$1

case "$zone" in
    ''|/*|*/|*..*|*'//'*) error "Invalid timezone: $zone" "Неверный часовой пояс: $zone" ;;
esac

[ -f "${MOD}/usr/share/zoneinfo/$zone" ] || error "Timezone not found: $zone" "Часовой пояс не найден: $zone"

ln -sf "${MOD}/usr/share/zoneinfo/$zone" /etc/localtime || error "Failed to set system timezone" "Не удалось изменить часовой пояс системы"
rm -f "${MOD}/etc/localtime" || error "Failed to update chroot timezone" "Не удалось изменить часовой пояс chroot"
cat /etc/localtime > "${MOD}/etc/localtime" || error "Failed to update chroot timezone" "Не удалось изменить часовой пояс chroot"

message "Timezone set to $zone in the main system and chroot" "Часовой пояс $zone установлен в основной системе и chroot"

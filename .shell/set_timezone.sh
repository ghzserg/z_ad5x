#!/bin/sh
# Единый часовой пояс основной системы и окружения Z-Mod.

. /usr/data/zmod/zmod/.shell/0.sh

ZONE_FILE="${MOD_CONF}/mod_data/timezone"
HOST_LOCALTIME=/etc/localtime
CHROOT_LOCALTIME="${MOD}/etc/localtime"

error() {
    echo "SET_TIMEZONE: $*" >&2
    exit 1
}

[ "$#" -eq 1 ] || error "Укажите зону, например Europe/Moscow"
zone=$1

if [ "$zone" = "--restore" ]; then
    [ -f /ZMOD ] && error "Восстановление выполняется в основной системе"
    [ -s "$ZONE_FILE" ] || exit 0
    IFS= read -r zone < "$ZONE_FILE"
elif [ -f /ZMOD ]; then
    # В chroot передаём запрос в основную систему через штатный zremote.
    /usr/data/zmod/zmod/.shell/zremote.sh /bin/sh /usr/data/zmod/zmod/.shell/set_timezone.sh "$zone"
    exit $?
fi

case "$zone" in
    ''|/*|*/|*..*|*'//'*) error "Недопустимая временная зона: $zone" ;;
esac
printf '%s\n' "$zone" | grep -Eq '^[A-Za-z0-9_./+-]+$' || error "Недопустимая временная зона: $zone"

# Берём данные часового пояса из chroot: на заводской системе zoneinfo может не быть.
# Проверяем файл до каких-либо изменений системных настроек.
tmp_host="/etc/.localtime.$$"
tmp_chroot="${MOD}/etc/.localtime.$$"
tmp_zone="${ZONE_FILE}.$$"
trap 'rm -f "$tmp_host" "$tmp_chroot" "$tmp_zone"' 0
trap 'exit 1' 1 2 3 15

chroot "$MOD" /bin/cat "/usr/share/zoneinfo/$zone" > "$tmp_host" || error "Зона не найдена: $zone"
[ -s "$tmp_host" ] || error "Пустые данные часового пояса: $zone"
cp "$tmp_host" "$tmp_chroot" || error "Не удалось подготовить часовой пояс в chroot"

if [ "$1" != "--restore" ]; then
    printf '%s\n' "$zone" > "$tmp_zone" || error "Не удалось сохранить часовой пояс"
fi

mv -f "$tmp_chroot" "$CHROOT_LOCALTIME" || error "Не удалось обновить часовой пояс chroot"
mv -f "$tmp_host" "$HOST_LOCALTIME" || error "Не удалось обновить часовой пояс системы"

if [ "$1" != "--restore" ]; then
    mv -f "$tmp_zone" "$ZONE_FILE" || error "Не удалось сохранить выбор пользователя"
fi

echo "SET_TIMEZONE: установлен $zone в системе и chroot"

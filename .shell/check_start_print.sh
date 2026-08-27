#!/bin/sh
# (C) 2024-2026 ghzserg https://github.com/ghzserg/zmod

FILE_NAME=${1}
if [ -z "${FILE_NAME}" ]; then
    [ ${ZLANG} == 'ru' ] && echo "RESPOND PREFIX=\"!!\" MSG=\"Не задано имя файла\"">/tmp/printer || echo "RESPOND PREFIX=\"!!\" MSG=\"Filename not found\"">/tmp/printer
    exit 1
elif [ ! -f "${FILE_NAME}" ]; then
    [ ${ZLANG} == 'ru' ] && echo "RESPOND PREFIX=\"!!\" MSG=\"Файл "${FILE_NAME}" не найден\"">/tmp/printer || echo "RESPOND PREFIX=\"!!\" MSG=\"File "${FILE_NAME}" not found\"">/tmp/printer
    exit 2
fi

source /usr/data/zmod/zmod/.shell/0.sh

if ! awk '
    /^END_PRINT/   { end_found = 1 }
    /^START_PRINT/ { start_found = 1 }
    END { exit !(end_found && start_found) }
' "${FILE_NAME}"; then
    [ ${ZLANG} == 'ru' ] && echo 'RESPOND PREFIX="!!" MSG="Неверный стартовый или конечный код. Макрос START_PRINT или END_PRINT не найден в файле печати. При работе без родного экрана он ДОЛЖЕН быть. Подробнее: https://wiki.zmod.link/ru/FAQ/"' >/tmp/printer || echo 'Invalid start or end code. The START_PRINT or END_PRINT macro was not found in the print file. It MUST BE present when working without a native screen. More details: https://wiki.zmod.link/FAQ/' >/tmp/printer
fi

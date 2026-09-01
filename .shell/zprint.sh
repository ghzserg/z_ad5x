#!/bin/sh
# (C) 2024-2026 ghzserg https://github.com/ghzserg/zmod
# "lanCode"
# "printerSerialNumber"
# Adventurer5M.json

source /usr/data/zmod/zmod/.shell/0.sh

# Проверка аргументов в зависимости от команды
if [ "$1" = "PRINT" ]; then
    if [ $# -ne 2 ]; then
        [ ${ZLANG} != 'ru' ] && echo "Use $0 PRINT FILE" || echo "Используйте $0 PRINT FILE"
        exit 1
    fi
elif [ "$1" = "PAUSE" ] || [ "$1" = "RESUME" ] || [ "$1" = "CANCEL" ] || [ "$1" = "CLOSE" ]; then
    if [ $# -ne 1 ]; then
        [ ${ZLANG} != 'ru' ] && echo "Use $0 PAUSE | RESUME | CANCEL" || echo "Используйте $0 PAUSE | RESUME | CANCEL | CLOSE"
        exit 1
    fi
else
    [ ${ZLANG} != 'ru' ] && echo "Use $0 PRINT FILE | CLOSE | PAUSE | RESUME | CANCEL" || echo "Используйте $0 PRINT FILE | CLOSE | PAUSE | RESUME | CANCEL"
    exit 1
fi

if [ -f /ZMOD ]; then
    CCURL="/usr/bin/curl"
else
    if [ ${AD5X} -eq 1 ]; then
        export LD_LIBRARY_PATH=/usr/prog/qt-4.8.6/lib:$LD_LIBRARY_PATH
        export LD_LIBRARY_PATH=/usr/prog/openssl-1.0.2d/lib:$LD_LIBRARY_PATH
        export LD_LIBRARY_PATH=/usr/prog/curl-7.55.1-https/lib:$LD_LIBRARY_PATH
        export LD_LIBRARY_PATH=/usr/prog/ffmpeg-4.0.2/lib:$LD_LIBRARY_PATH
        export LD_LIBRARY_PATH=/usr/prog/x264/lib:$LD_LIBRARY_PATH
        export LD_LIBRARY_PATH=/usr/prog/libffi-3.4.4/lib:$LD_LIBRARY_PATH
        export LD_LIBRARY_PATH=/usr/prog/opencv-4.2.0_mips/lib:$LD_LIBRARY_PATH
        export LD_LIBRARY_PATH=/usr/prog/libzip-1.10.1/lib:$LD_LIBRARY_PATH
        export LD_LIBRARY_PATH=/usr/prog/nim/lib:$LD_LIBRARY_PATH
        export LD_LIBRARY_PATH=/usr/prog/Python-3.8.2/lib:$LD_LIBRARY_PATH
    fi
    if [ ${C5PRO} -eq 1 ]; then
        export LD_LIBRARY_PATH=/usr/prog/libffi-3.4.4/lib:$LD_LIBRARY_PATH
        export LD_LIBRARY_PATH=/usr/prog/curl-7.55.1/lib:$LD_LIBRARY_PATH
        export LD_LIBRARY_PATH=/usr/prog/ffmpeg-402/lib:$LD_LIBRARY_PATH
        export LD_LIBRARY_PATH=/usr/prog/x264/lib:$LD_LIBRARY_PATH
        export LD_LIBRARY_PATH=/usr/prog/libffi-3.4.4/lib:$LD_LIBRARY_PATH
        export LD_LIBRARY_PATH=/usr/prog/libsodium/lib:$LD_LIBRARY_PATH
        export LD_LIBRARY_PATH=/usr/prog/opencv-4.2/lib:$LD_LIBRARY_PATH
        export LD_LIBRARY_PATH=/usr/prog/mjpg-streamer:$LD_LIBRARY_PATH
        export LD_LIBRARY_PATH=/usr/prog/nim/lib:$LD_LIBRARY_PATH
        export LD_LIBRARY_PATH=/usr/prog/libzip-1.10.1/lib:$LD_LIBRARY_PATH
        export LD_LIBRARY_PATH=/usr/prog/Python-3.8.2/lib:$LD_LIBRARY_PATH
        export LD_LIBRARY_PATH=/usr/prog/openssl-1.0.2d/lib:$LD_LIBRARY_PATH
    fi
    CCURL="${CURL}"
fi

ip=$(ip addr | grep inet | grep wlan0 | awk -F" " '{print $2}'| sed -e 's/\/.*$//')
if [ "$ip" == "" ]; then
    ip=$(ip addr | grep inet | grep eth0 | awk -F" " '{print $2}'| sed -e 's/\/.*$//')
fi

if [ ${AD5X} -eq 1 ] || [ ${AD5M} -eq 1 ]; then
    serialNumber=$(cat ${FFCONFIG} | grep "printerSerialNumber"| cut  -d ":" -f2| awk '{print $1}' | sed 's|[",]||g')
    checkCode=$(cat ${FFCONFIG} | grep "lanCode"| cut  -d ":" -f2| awk '{print $1}' | sed 's|[",]||g')
else # C5PRO
    serialNumber=$(cat ${FFCONFIG}/general.json | grep "serialNumber"| cut  -d ":" -f2| awk '{print $1}' | sed 's|[",]||g')
    checkCode=$(cat ${FFCONFIG}/network.json | grep "lanModeCode"| cut  -d ":" -f2| awk '{print $1}' | sed 's|[",]||g')
fi

if [ "$1" == "CLOSE" ]; then
    ${CCURL} -m 60 -s \
        http://$ip:8898/control \
        -H 'Content-Type: application/json' \
        -d "{\"serialNumber\":\"$serialNumber\",\"checkCode\":\"$checkCode\",\"payload\":{\"cmd\":\"stateCtrl_cmd\",\"args\":{\"action\":\"setClearPlatform\"}}}" || \
    if [ ${ZLANG} != 'ru' ]; then
        echo "No response from printer at $ip. Printer setup required. On printer screen: 'Settings' -> 'WiFi icon' -> 'Network mode' -> toggle 'Local network only'"
    else
        echo "Нет ответа от принтера с IP $ip. Необходимо настроить принтер. На экране принтера: \"Настройки\" -> \"Иконка WiFi\" -> \"Сетевой режим\" -> включить ползунок \"Только локальные сети\""
    fi
elif [ "$1" == "PAUSE" ]; then
    ${CCURL} -m 60 -s \
        http://$ip:8898/control \
        -H 'Accept: */*' \
        -H 'Content-Type: application/json' \
        -d "{\"serialNumber\":\"$serialNumber\",\"checkCode\":\"$checkCode\",\"payload\":{\"cmd\":\"jobCtl_cmd\",\"args\":{\"jobID\":\"\",\"action\":\"pause\"}}}" || \
    if [ ${ZLANG} != 'ru' ]; then
        echo "No response from printer at $ip. Printer setup required. On printer screen: 'Settings' -> 'WiFi icon' -> 'Network mode' -> toggle 'Local network only'"
    else
        echo "Нет ответа от принтера с IP $ip. Необходимо настроить принтер. На экране принтера: \"Настройки\" -> \"Иконка WiFi\" -> \"Сетевой режим\" -> включить ползунок \"Только локальные сети\""
    fi
elif [ "$1" == "RESUME" ]; then
    ${CCURL} -m 60 -s \
        http://$ip:8898/control \
        -H 'Accept: */*' \
        -H 'Content-Type: application/json' \
        -d "{\"serialNumber\":\"$serialNumber\",\"checkCode\":\"$checkCode\",\"payload\":{\"cmd\":\"jobCtl_cmd\",\"args\":{\"jobID\":\"\",\"action\":\"continue\"}}}" || \
    if [ ${ZLANG} != 'ru' ]; then
        echo "No response from printer at $ip. Printer setup required. On printer screen: 'Settings' -> 'WiFi icon' -> 'Network mode' -> toggle 'Local network only'"
    else
        echo "Нет ответа от принтера с IP $ip. Необходимо настроить принтер. На экране принтера: \"Настройки\" -> \"Иконка WiFi\" -> \"Сетевой режим\" -> включить ползунок \"Только локальные сети\""
    fi
elif [ "$1" == "CANCEL" ]; then
    ${CCURL} -m 60 -s \
        http://$ip:8898/control \
        -H 'Accept: */*' \
        -H 'Content-Type: application/json' \
        -d "{\"serialNumber\":\"$serialNumber\",\"checkCode\":\"$checkCode\",\"payload\":{\"cmd\":\"jobCtl_cmd\",\"args\":{\"jobID\":\"\",\"action\":\"cancel\"}}}" || \
    if [ ${ZLANG} != 'ru' ]; then
        echo "No response from printer at $ip. Printer setup required. On printer screen: 'Settings' -> 'WiFi icon' -> 'Network mode' -> toggle 'Local network only'"
    else
        echo "Нет ответа от принтера с IP $ip. Необходимо настроить принтер. На экране принтера: \"Настройки\" -> \"Иконка WiFi\" -> \"Сетевой режим\" -> включить ползунок \"Только локальные сети\""
    fi
elif [ "$1" == "PRINT" ]; then
    if ! [ -f "${DATA_GCODES}/$2" ]; then
        if [ ${ZLANG} != 'ru' ]; then
            echo "RESPOND TYPE=error MSG=\"File $2 not found.\"" >/tmp/printer
        else
            echo "RESPOND TYPE=error MSG=\"Файл $2 не найден.\"" >/tmp/printer
        fi
        echo "CANCEL_PRINT" >/tmp/printer
        exit 1
    fi

    ${CCURL} -m 60 -s \
        http://$ip:8898/printGcode \
        -H 'Content-Type: application/json' \
        -d "{\"serialNumber\":\"$serialNumber\",\"checkCode\":\"$checkCode\",\"fileName\":\"$2\",\"levelingBeforePrint\":true}" || \
    if [ ${ZLANG} != 'ru' ]; then
        echo "No response from printer at $ip. Printer setup required. On printer screen: 'Settings' -> 'WiFi icon' -> 'Network mode' -> toggle 'Local network only'"
    else
        echo "Нет ответа от принтера с IP $ip. Необходимо настроить принтер. На экране принтера: \"Настройки\" -> \"Иконка WiFi\" -> \"Сетевой режим\" -> включить ползунок \"Только локальные сети\""
    fi
else
    [ ${ZLANG} != 'ru' ] && echo "Use $0 PRINT|CLOSE FILE | PAUSE | RESUME | CANCEL" || echo "Используйте $0 PRINT|CLOSE FILE | PAUSE | RESUME | CANCEL"
    exit 1
fi

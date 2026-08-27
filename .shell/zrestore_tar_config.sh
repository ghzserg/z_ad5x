#!/bin/sh
# (C) 2024-2026 ghzserg https://github.com/ghzserg/zmod

source /usr/data/zmod/zmod/.shell/0.sh

unset LD_PRELOAD

if ! [ -f "/opt/config/mod_data/config.tar.gz" ]; then
    if [ ${ZLANG} != 'ru' ]; then
        echo "Для восстановления конфига скопировать в 'Конфигурация' -> 'mod_data' -> config.tar.gz и вызвать RESTORE_TAR_CONFIG"
    else
        echo "To restore the config, copy to 'Configuration' -> 'mod_data' -> config.tar.gz and call RESTORE_TAR_CONFIG"
    fi
else
    gunzip /opt/config/mod_data/config.tar.gz
    tar -xvf /opt/config/mod_data/config.tar -C /
    /usr/data/zmod/zmod/.shell/zclear.sh
    echo REBOOT >/tmp/printer
fi

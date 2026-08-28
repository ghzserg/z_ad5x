#!/bin/sh
# (C) 2024-2026 ghzserg https://github.com/ghzserg/zmod

source /usr/data/zmod/zmod/.shell/0.sh

/usr/data/zmod/zmod/.shell/root/S70httpd stop
if grep -q "guppy = 1" /opt/config/mod_data/variables.cfg; then
    /usr/data/zmod/zmod/.shell/root/S80guppyscreen stop
fi
if grep -q "hellix = 1" /opt/config/mod_data/variables.cfg; then
    /usr/data/zmod/zmod/.shell/root/S80hellixscreen stop
fi
/usr/data/zmod/zmod/.shell/root/S65moonraker stop
if [ ${AD5M} -eq 1 ]; then
    if grep -q "klipper13 = 1" /opt/config/mod_data/variables.cfg; then
        /usr/data/zmod/zmod/.shell/root/S60klipper stop
    fi
fi

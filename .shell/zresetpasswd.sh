#!/bin/sh
# (C) 2024-2026 ghzserg https://github.com/ghzserg/zmod

if [ -f /ZMOD ]; then
    /usr/data/zmod/zmod/.shell/zremote.sh /usr/data/zmod/zmod/.shell/zresetpasswd.sh
else
    yes root | passwd
    echo "New password: root"
fi

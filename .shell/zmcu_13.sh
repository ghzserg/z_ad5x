#!/bin/sh
# (C) 2024-2026 ghzserg https://github.com/ghzserg/zmod

cd "$1"
start-stop-daemon -S -b -x /usr/data/zmod/zmod/.shell/update_mcu.sh -- mainboard

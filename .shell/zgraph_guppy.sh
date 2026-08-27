#!/bin/sh
# (C) 2024-2026 ghzserg https://github.com/ghzserg/zmod

source /usr/data/zmod/zmod/.shell/0.sh

unset LD_PRELOAD

if [ -f /ZMOD ]; then
    /usr/data/zmod/zmod/.shell/root/zshaper/graph_belts.py $@
else
    chroot ${MOD} /usr/data/zmod/zmod/.shell/root/zshaper/graph_belts.py $@
fi

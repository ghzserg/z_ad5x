#!/bin/sh
# (C) 2024-2026 ghzserg https://github.com/ghzserg/zmod

source /usr/data/zmod/zmod/.shell/0.sh

unset LD_PRELOAD

if [ -f /ZMOD ]; then
    /usr/data/zmod/zmod/.shell/root/zshaper_guppy.sh $@
else
    if [ ${AD5M} -eq 1 ]; then
        chroot ${MOD} /usr/data/zmod/zmod/.shell/root/zshaper_guppy.sh $@
    fi
    if [ ${AD5X} -eq 1 ]; then
        export PATH=$PATH:/usr/prog/Python-3.8.2/bin
        export LD_LIBRARY_PATH=/usr/prog/Python-3.8.2/lib:$LD_LIBRARY_PATH
        export LD_LIBRARY_PATH=/usr/prog/openssl-1.0.2d/lib:$LD_LIBRARY_PATH
        export LD_LIBRARY_PATH=/usr/prog/libffi-3.4.4/lib:$LD_LIBRARY_PATH
        /usr/data/zmod/zmod/.shell/root/zshaper_guppy.sh $@ --json

        unset LD_LIBRARY_PATH
        export PATH='/bin:/sbin:/usr/bin:/usr/sbin'
        chroot ${MOD} /usr/data/zmod/zmod/.shell/root/zshaper_guppy.sh $@ --json-in
    fi
fi

#!/bin/sh
# (C) 2026 ghzserg https://github.com/ghzserg/zmod

source /usr/data/zmod/zmod/.shell/0.sh

if [ ${C5PRO} -eq 1 ] || [ ${AD5X} -eq 1 ]; then
    export LD_LIBRARY_PATH=/usr/prog/openssl-1.0.2d/lib:$LD_LIBRARY_PATH
    export LD_LIBRARY_PATH=/usr/prog/Python-3.8.2/lib:$LD_LIBRARY_PATH
fi

$PYTHON /usr/data/zmod/zmod/.shell/3mf2gcode.py $DATA_GCODES

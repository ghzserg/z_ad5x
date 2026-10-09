#!/bin/sh

fix_firmwareExe()
{
    [ "$FILE_MD5" = "$1" ] && \
    printf '\x00\x10' | dd of=/usr/prog/PROGRAM/software/firmwareExe bs=1 seek=$2 conv=notrunc

}

FILE_MD5=$(md5sum /usr/prog/PROGRAM/software/firmwareExe | cut -d' ' -f1)

fix_firmwareExe "53002874d76d1b381e45d4b533884408" 1314894 # 3.1.6

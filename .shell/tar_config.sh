#!/bin/sh
# (C) 2024-2026 ghzserg https://github.com/ghzserg/zmod

source /usr/data/zmod/zmod/.shell/0.sh

df -h >/tmp/df.txt
dmesg >/tmp/dmesg.txt
ps >/tmp/ps.txt

rm -f /opt/config/mod_data/*.tar /opt/config/mod_data/*.tar.gz 2>/dev/null >/dev/null
if [ ${AD5X} -eq 1 ]; then
    tar -cf /opt/config/mod_data/config.tar --exclude logo --exclude save --exclude database --exclude shapers --exclude ssh.key --exclude .git --exclude .shell --exclude notify.txt --exclude printer_data --exclude config.tar.gz --exclude config.tar /opt/config/ /usr/prog/config/ /usr/data/logs/ /usr/prog/app_startup.sh /tmp/*.txt
fi
if [ ${AD5M} -eq 1 ]; then
    tar -cf /opt/config/mod_data/config.tar --exclude logo --exclude save --exclude database --exclude shapers --exclude ssh.key --exclude .git --exclude .shell --exclude notify.txt --exclude printer_data --exclude config.tar.gz --exclude config.tar /opt/config/ /data/logFiles/ /tmp/*.txt
fi
gzip /opt/config/mod_data/config.tar

VER=$(cat ${VER_FULL})

mv /opt/config/mod_data/config.tar.gz /opt/config/mod_data/config_${VER}.tar.gz
echo "config_${VER}.tar.gz"

#!/bin/sh
# (C) 2024-2026 ghzserg https://github.com/ghzserg/zmod

VER_FULL="/usr/data/zmod/zmod/version_5x.txt"
DATA=/usr/data
DATA_GCODES=/usr/data/gcodes
MOD=${DATA}/.mod/.zmod
AD5M=0
AD5X=1
C5PRO=0
KEY_TYPE="ecdsa"
KLIPPER_DIR="/usr/prog/klipper"
TS_LIB="/usr/prog/tslib-1.12/etc"
VIDEO="video3"
V4l2="chroot ${MOD} v4l2-ctl"
LOG_FILES="/usr/data/logs"
MOD_CONF="/usr/data/config"
PYTHON="/usr/prog/Python-3.8.2/bin/python3"
PYTHON_DIR="/usr/prog/Python-3.8.2/lib/python3.8"
CURL="/usr/prog/curl-7.55.1-https/bin/curl"
PROGRAM_DIR="/usr/prog/PROGRAM/"
GLINES=50000
UPDATE_DIR="/usr/data/update/"
FFCONFIG='/usr/prog/config/Adventurer5M.json'
WPA_CONFIG="/usr/prog/wifi/wpa_supplicant.conf"
ZLANG="en"
if grep -q "language: en" ${MOD_CONF}/mod_data/lang.cfg; then ZLANG="en"
elif grep -q "language: ru" ${MOD_CONF}/mod_data/lang.cfg; then ZLANG="ru"
elif grep -q "language: de" ${MOD_CONF}/mod_data/lang.cfg; then ZLANG="de"
elif grep -q "language: fr" ${MOD_CONF}/mod_data/lang.cfg; then ZLANG="fr"
elif grep -q "language: it" ${MOD_CONF}/mod_data/lang.cfg; then ZLANG="it"
elif grep -q "language: es" ${MOD_CONF}/mod_data/lang.cfg; then ZLANG="es"
elif grep -q "language: zh" ${MOD_CONF}/mod_data/lang.cfg; then ZLANG="zh"
elif grep -q "language: ja" ${MOD_CONF}/mod_data/lang.cfg; then ZLANG="ja"
elif grep -q "language: ko" ${MOD_CONF}/mod_data/lang.cfg; then ZLANG="ko"
elif grep -q "language: pt" ${MOD_CONF}/mod_data/lang.cfg; then ZLANG="pt"
elif grep -q "language: tr" ${MOD_CONF}/mod_data/lang.cfg; then ZLANG="tr"
elif grep -q "language: cs" ${MOD_CONF}/mod_data/lang.cfg; then ZLANG="cs"
fi

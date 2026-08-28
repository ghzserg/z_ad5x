#!/bin/sh
# (C) 2024-2026 ghzserg https://github.com/ghzserg/zmod

source /usr/data/zmod/zmod/.shell/0.sh

if  [ "$1" == 1 ]; then
    rm -rf ${LOG_FILES}/*
    rm -rf /opt/config/mod_data/log/*
    rm -rf ${UPDATE_DIR}/*
    find /opt/config/ -name '*.pyc' -exec rm {} \;
    find /opt/config/ -name '*.tar' -exec rm {} \;
    find /opt/config/ -name '*.zip' -exec rm {} \;
    find /opt/config/ -name '*.tar.gz' -exec rm {} \;
    find /opt/config/ -name '*.tgz' -exec rm {} \;
    find ${DATA_GCODES}/timelapse -type f -name '*.mp4' -exec rm {} \;
    find ${DATA_GCODES}/timelapse -type f -name '*.jpg' -exec rm {} \;
    sync
fi

if  [ "$2" == 1 ]; then
    find ${DATA_GCODES}/ -type f -not -regex "${DATA}/\.mod/.*" -not -regex "${LOG_FILES}/.*" -exec rm {} \;
    sync
    find ${DATA_GCODES}/ -type d -not -regex "${DATA}/\.mod.*"  -not -path "${DATA}/" -not -path "${LOG_FILES}/" -exec rm -r {} \;
    sync
fi

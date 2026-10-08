#!/bin/sh

set -x

unset LD_LIBRARY_PATH
unset LD_PRELOAD

source /usr/data/zmod/zmod/.shell/0.sh

# Fix firmwareExe video
if [ ${C5PRO} -eq 1 ] && ! grep -q 'START=off' ${MOD_CONF}/mod_data/camera.conf; then
    mv /dev/video0 /dev/video67

    FILE_MD5=$(md5sum /usr/prog/PROGRAM/software/firmwareExe | cut -d' ' -f1)
    # 1.9.9 Pro
    [ "$FILE_MD5" = "2b92736aba576885378d5684d3370072" ] && \
    printf '\x00\x00\x00\x00' | dd of=/usr/prog/PROGRAM/software/firmwareExe bs=1 seek=$((0x0063C33C)) conv=notrunc
    # 1.9.9
    [ "$FILE_MD5" = "50bce9af77fb537e2170087102785d4a" ] && \
    printf '\x00\x00\x00\x00' | dd of=/usr/prog/PROGRAM/software/firmwareExe bs=1 seek=6536157 conv=notrunc
    exit
fi

CHECH_ARCH=`uname -m`
if [ "${CHECH_ARCH}" == "armv7l" ]; then
    CONFIG_DIR="/opt/config"
else if [ "${CHECH_ARCH}" == "mips" ]; then
    CONFIG_DIR="/usr/data/config"
fi
fi

app_startup_mcu()
{

    CONTROL_DIR=${PROGRAM_DIR}control/
    cd ${CONTROL_DIR}
    if [ ${AD5X} -eq 1 ]; then
        CONTROL_VERSION=`ls -d [0-9]*/ | sort -Vr | head -n 1`
    fi
    if [ ${AD5M} -eq 1 ]; then
        CONTROL_VERSION=`ls -d [0-9]*/ | sort -t '.' -k1,1n -k2,2n -k3,3n -r | head -n 1`
    fi

    if grep -q "klipper13 = 1" ${MOD_CONF}/mod_data/variables.cfg; then
        echo "Klipper 13"
        KLIPPER13=1
    else
        echo "Родной Klipper"
        KLIPPER13=0
    fi

    CONTRIL_FLAG=${CONTROL_DIR}${CONTROL_VERSION}Update
    CONTRIL_M=${CONTROL_DIR}${CONTROL_VERSION}UpdateM

    if  [ -f "${CONTRIL_M}" ] || [ -f ${CONTRIL_FLAG} ]; then
        [ ${KLIPPER13} -eq 1 ] && mount -o bind /usr/data/zmod/zmod/.shell/update_mcu.sh ${CONTROL_DIR}${CONTROL_VERSION}run.sh
        if [ ${AD5X} -eq 1 ]; then
            cd ${CONTROL_DIR}${CONTROL_VERSION}
            ./run.sh
            reboot -f
        fi
    else
        [ ${KLIPPER13} -eq 1 ] && mount -o bind /usr/data/zmod/zmod/.shell/klipper13.sh ${KLIPPER_DIR}/start.sh
    fi
}

mv ${CONFIG_DIR}/mod_data/log/app_startup_mcu.4.log ${CONFIG_DIR}/mod_data/log/app_startup_mcu.5.log 2>/dev/null
mv ${CONFIG_DIR}/mod_data/log/app_startup_mcu.3.log ${CONFIG_DIR}/mod_data/log/app_startup_mcu.4.log 2>/dev/null
mv ${CONFIG_DIR}/mod_data/log/app_startup_mcu.2.log ${CONFIG_DIR}/mod_data/log/app_startup_mcu.3.log 2>/dev/null
mv ${CONFIG_DIR}/mod_data/log/app_startup_mcu.1.log ${CONFIG_DIR}/mod_data/log/app_startup_mcu.2.log 2>/dev/null
mv ${CONFIG_DIR}/mod_data/log/app_startup_mcu.log ${CONFIG_DIR}/mod_data/log/app_startup_mcu.1.log 2>/dev/null

app_startup_mcu &>${CONFIG_DIR}/mod_data/log/app_startup_mcu.log

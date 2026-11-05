#!/bin/sh
# (C) 2024-2026 ghzserg https://github.com/ghzserg/zmod
# Z-Mod: разовая загрузка eMMC на 50 МГц (HS52, без HS200/DDR) для AD5M / AD5M Pro.
# Запускается после полного старта системы.
# Постоянный bootcmd никогда не прописывается: каждая загрузка на 50 МГц разовая.
# Повторный тест: удалить все файлы из $DIR.

source /usr/data/zmod/zmod/.shell/0.sh

DIR=${MOD_CONF}/mod_data/emmc
LOG_DIR=${MOD_CONF}/mod_data/log/emmc
LOG=${LOG_DIR}/emmc.log
NODE=/proc/device-tree/soc@3000000/sdmmc@4020000
IOS=/sys/kernel/debug/mmc0/ios
TEST_FILE=/data/.emmc_test.bin
TEST_MB=128
MAX_FAILS=3

STOCK_BOOTCMD='run setargs_mmc boot_dsp0 boot_uImage'
ARMED_BOOTCMD='setenv bootcmd run setargs_mmc boot_dsp0 boot_uImage;saveenv;run setargs_mmc boot_dsp0 boot_zmod'
BOOT_ZMOD='fdt rm /soc@3000000/sdmmc@4020000 mmc-hs200-1_8v;fdt rm /soc@3000000/sdmmc@4020000 mmc-ddr-1_8v;fdt set /soc@3000000/sdmmc@4020000 max-frequency <0x2faf080>;run boot_uImage'
BOOT_UIMAGE='part list mmc 0;fatload mmc 0:1 0x43000000 uImage;fatload mmc 0:1 0x44864e70 sunxi.dtb;fdt resize;bootm 0x43000000 - 0x44864e70'

# log "русский текст" "english text"
log() {
    if [ "${ZLANG}" != "ru" ]; then
        echo "$(date '+%d.%m.%Y %H:%M:%S') $2" >> "$LOG"
    else
        echo "$(date '+%Y-%m-%d %H:%M:%S') $1" >> "$LOG"
    fi
}

rotate_log() {
    mkdir -p ${LOG_DIR}
    mv ${LOG_DIR}/emmc.4.log ${LOG_DIR}/emmc.5.log 2>/dev/null
    mv ${LOG_DIR}/emmc.3.log ${LOG_DIR}/emmc.4.log 2>/dev/null
    mv ${LOG_DIR}/emmc.2.log ${LOG_DIR}/emmc.3.log 2>/dev/null
    mv ${LOG_DIR}/emmc.1.log ${LOG_DIR}/emmc.2.log 2>/dev/null
    mv ${LOG_DIR}/emmc.log   ${LOG_DIR}/emmc.1.log 2>/dev/null
    >${LOG}
}

getenv() {
    fw_printenv "$1" 2>/dev/null | sed "s/^$1=//"
}

read_file() {
    if [ -f "$1" ]; then
        cat "$1"
    fi
}

set_state() {
    echo "$1" > "$DIR/state"
    sync
}

set_fails() {
    echo "$1" > "$DIR/fails"
    sync
}

arm() {
    fw_setenv bootcmd "$ARMED_BOOTCMD"
    if [ "$(getenv bootcmd)" = "$ARMED_BOOTCMD" ]; then
        touch "$DIR/armed"
        sync
        log "разовая загрузка 50 МГц включена" "one-shot 50 MHz boot armed"
    else
        log "ОШИБКА: не удалось записать bootcmd" "ERROR: failed to write bootcmd"
    fi
}

fail() {
    set_state fail
    rm -f "$DIR/armed"
    sync
    if [ "$(getenv bootcmd)" != "$STOCK_BOOTCMD" ]; then
        fw_setenv bootcmd "$STOCK_BOOTCMD"
    fi
    log "FAIL: $1. Попытки загрузки на 50 МГц прекращены" "FAIL: $2. 50 MHz boot attempts stopped"
}

drop_caches() {
    sync
    echo 3 > /proc/sys/vm/drop_caches
}

mmc_errors() {
    dmesg | grep -ci 'mmc0.*\(err\|timeout\)\|I/O error'
}

# Тест чтения и записи. 0 - успех, 1 - ошибка, 2 - тест невозможен
emmc_test() {
    free=$(df -k /data | awk 'NR==2 {print $4}')
    if [ -z "$free" ]; then
        log "тест: не удалось определить свободное место в /data" "test: cannot determine free space in /data"
        return 2
    fi
    if [ "$free" -lt $((TEST_MB * 1024 * 2)) ]; then
        log "тест: мало места в /data (${free} КБ)" "test: not enough space in /data (${free} KB)"
        return 2
    fi

    # Чтение: два прохода с устройства с очисткой кэша, хеши должны совпасть
    drop_caches
    t0=$(date +%s)
    r1=$(dd if=/dev/mmcblk0 bs=1M count=$TEST_MB 2>/dev/null | sha256sum | cut -d' ' -f1)
    t1=$(date +%s)
    drop_caches
    r2=$(dd if=/dev/mmcblk0 bs=1M count=$TEST_MB 2>/dev/null | sha256sum | cut -d' ' -f1)
    if [ -z "$r1" ]; then
        log "тест: чтение не выполнено" "test: read failed"
        return 1
    fi
    if [ "$r1" != "$r2" ]; then
        log "тест: чтение нестабильно ($r1 / $r2)" "test: unstable read ($r1 / $r2)"
        return 1
    fi
    log "тест: чтение ${TEST_MB} МБ за $((t1 - t0)) с" "test: read ${TEST_MB} MB in $((t1 - t0)) s"

    # Запись: хеш считается при генерации, затем файл читается после очистки кэша
    t0=$(date +%s)
    w1=$(dd if=/dev/urandom bs=1M count=$TEST_MB 2>/dev/null | tee "$TEST_FILE" | sha256sum | cut -d' ' -f1)
    sync
    t1=$(date +%s)
    drop_caches
    w2=$(sha256sum "$TEST_FILE" 2>/dev/null | cut -d' ' -f1)
    rm -f "$TEST_FILE"
    sync
    if [ -z "$w2" ]; then
        log "тест: записанный файл не прочитан" "test: written file could not be read"
        return 1
    fi
    if [ "$w1" != "$w2" ]; then
        log "тест: данные после записи не совпали ($w1 / $w2)" "test: data mismatch after write ($w1 / $w2)"
        return 1
    fi
    log "тест: запись ${TEST_MB} МБ за $((t1 - t0)) с" "test: write ${TEST_MB} MB in $((t1 - t0)) s"

    if [ "$(mmc_errors)" != "0" ]; then
        log "тест: ошибки mmc в dmesg после теста" "test: mmc errors in dmesg after test"
        return 1
    fi
    return 0
}

# ---------- основная часть ----------

mkdir -p "$DIR"

# Один запуск на загрузку
boot_id=$(cat /proc/sys/kernel/random/boot_id)
if [ "$(read_file "$DIR/boot_id")" = "$boot_id" ]; then
    exit 0
fi
echo "$boot_id" > "$DIR/boot_id"
rotate_log

state=$(read_file "$DIR/state")
fails=$(read_file "$DIR/fails")
if [ -z "$fails" ]; then
    fails=0
fi

if [ "$state" = "fail" ]; then
    exit 0
fi

# Проверка платформы и стокового загрузчика
if [ "${AD5M}" != "1" ]; then
    log "не AD5M, выход" "not AD5M, exit"
    exit 0
fi
if [ ! -f "$NODE/max-frequency" ]; then
    log "нет узла $NODE, выход" "node $NODE not found, exit"
    exit 0
fi
if [ "$(getenv boot_uImage)" != "$BOOT_UIMAGE" ]; then
    log "boot_uImage не стоковый, выход" "boot_uImage is not stock, exit"
    exit 0
fi
bootcmd=$(getenv bootcmd)
if [ "$bootcmd" != "$STOCK_BOOTCMD" ]; then
    if [ "$bootcmd" != "$ARMED_BOOTCMD" ]; then
        log "неизвестный bootcmd, выход: $bootcmd" "unknown bootcmd, exit: $bootcmd"
        exit 0
    fi
fi

# boot_zmod
if [ "$(getenv boot_zmod)" != "$BOOT_ZMOD" ]; then
    fw_setenv boot_zmod "$BOOT_ZMOD"
    if [ "$(getenv boot_zmod)" != "$BOOT_ZMOD" ]; then
        log "ОШИБКА: не удалось записать boot_zmod" "ERROR: failed to write boot_zmod"
        exit 1
    fi
    log "boot_zmod записан" "boot_zmod written"
fi

# Текущее состояние загрузки
if [ ! -r "$IOS" ]; then
    mount -t debugfs none /sys/kernel/debug 2>/dev/null
fi
mf=$(hexdump -ve '1/1 "%02x"' "$NODE/max-frequency")
clk=$(awk '/^clock:/ {print $2}' "$IOS" 2>/dev/null)
timing=$(awk '/^timing spec:/ {print $3}' "$IOS" 2>/dev/null)
errors=$(mmc_errors)
log "загрузка: dtb=$mf clock=$clk timing=$timing ошибки=$errors state=$state fails=$fails" "boot: dtb=$mf clock=$clk timing=$timing errors=$errors state=$state fails=$fails"

if [ "$mf" = "02faf080" ]; then
    # Загрузились на 50 МГц
    rm -f "$DIR/armed"
    sync

    if [ "$clk" != "50000000" ]; then
        fail "частота $clk вместо 50000000 (чип не поддерживает HS52)" "clock $clk instead of 50000000 (chip does not support HS52)"
        exit 0
    fi
    if [ "$errors" != "0" ]; then
        fail "ошибки mmc в dmesg: $errors" "mmc errors in dmesg: $errors"
        exit 0
    fi

    if [ "$state" = "ok" ]; then
        set_fails 0
        arm
    else
        # trial или файлы удалены для повторного теста
        emmc_test
        result=$?
        if [ "$result" = "0" ]; then
            set_state ok
            set_fails 0
            log "тест пройден" "test passed"
            arm
        elif [ "$result" = "2" ]; then
            set_state trial
            log "тест отложен до следующей загрузки" "test postponed to next boot"
            arm
        else
            fail "тест чтения/записи не пройден" "read/write test failed"
        fi
    fi
else
    # Загрузились на 25 МГц
    if [ -z "$state" ]; then
        set_state trial
        set_fails 0
        log "первый запуск, тестовая загрузка при следующей перезагрузке" "first run, test boot on next reboot"
        arm
    elif [ -f "$DIR/armed" ]; then
        fails=$((fails + 1))
        set_fails $fails
        log "загрузка на 50 МГц не дошла до системы ($fails из $MAX_FAILS)" "50 MHz boot did not reach the system ($fails of $MAX_FAILS)"
        if [ "$fails" -ge "$MAX_FAILS" ]; then
            fail "$MAX_FAILS неудачных загрузок подряд" "$MAX_FAILS failed boots in a row"
        else
            arm
        fi
    else
        log "разовая загрузка не была включена, включаю" "one-shot boot was not armed, arming"
        arm
    fi
fi

exit 0

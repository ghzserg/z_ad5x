#!/bin/sh
# (C) 2024-2026 ghzserg https://github.com/ghzserg/zmod
# eMMC 50 МГц (HS52) для AD5M: только разовая загрузка, постоянный bootcmd не прописывается
# Повторный тест: удалить все файлы из $DIR. Отключить: создать $DIR/disable.txt. DDR52: создать $DIR/ddr.txt

source /usr/data/zmod/zmod/.shell/0.sh

[ ${AD5M} -eq 0 ] && exit

DIR=${MOD_CONF}/mod_data/emmc
LOG_DIR=${MOD_CONF}/mod_data/log/emmc
LOG=${LOG_DIR}/emmc.log
NODE=/proc/device-tree/soc@3000000/sdmmc@4020000
IOS=/sys/kernel/debug/mmc0/ios
TEST_FILE=/data/.emmc_test.bin
TEST_MB=128
MAX_FAILS=3
VERSION=2

STOCK_BOOTCMD='run setargs_mmc boot_dsp0 boot_uImage'
ARMED_BOOTCMD='setenv bootcmd run setargs_mmc boot_dsp0 boot_uImage;saveenv;run setargs_mmc boot_dsp0 boot_zmod'
EMMC_FDT='fdt rm /soc@3000000/sdmmc@4020000 mmc-hs200-1_8v;fdt rm /soc@3000000/sdmmc@4020000 mmc-ddr-1_8v;fdt set /soc@3000000/sdmmc@4020000 max-frequency <0x2faf080>;setenv bootargs ${bootargs} zmod_emmc_50'
BOOT_ZMOD_A="${EMMC_FDT};run boot_uImage"
BOOT_ZMOD_B="part list mmc 0;fatload mmc 0:1 0x43000000 uImage;fatload mmc 0:1 0x44864e70 sunxi.dtb;fdt addr 0x44864e70;fdt resize;${EMMC_FDT};bootm 0x43000000 - 0x44864e70"
EMMC_FDT_DDR='fdt rm /soc@3000000/sdmmc@4020000 mmc-hs200-1_8v;fdt set /soc@3000000/sdmmc@4020000 max-frequency <0x2faf080>;setenv bootargs ${bootargs} zmod_emmc_ddr'
BOOT_ZMOD_A_DDR="${EMMC_FDT_DDR};run boot_uImage"
BOOT_ZMOD_B_DDR="part list mmc 0;fatload mmc 0:1 0x43000000 uImage;fatload mmc 0:1 0x44864e70 sunxi.dtb;fdt addr 0x44864e70;fdt resize;${EMMC_FDT_DDR};bootm 0x43000000 - 0x44864e70"
BOOT_UIMAGE='part list mmc 0;fatload mmc 0:1 0x43000000 uImage;fatload mmc 0:1 0x44864e70 sunxi.dtb;fdt resize;bootm 0x43000000 - 0x44864e70'

# log "русский текст" "english text"
log() {
    if [ "${ZLANG}" == "ru" ]; then
        echo "$1" >> "$LOG"
    else
        echo "$2" >> "$LOG"
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
    echo "$1" > "$DIR/state.txt"
    sync
}

set_fails() {
    echo "$1" > "$DIR/fails.txt"
    sync
}

arm() {
    fw_setenv bootcmd "$ARMED_BOOTCMD"
    if [ "$(getenv bootcmd)" = "$ARMED_BOOTCMD" ]; then
        touch "$DIR/armed.txt"
        sync
        log "разовая загрузка 50 МГц включена (сейчас ${mhz} МГц)" "one-shot 50 MHz boot armed (now ${mhz} MHz)"
    else
        log "ОШИБКА: не удалось записать bootcmd" "ERROR: failed to write bootcmd"
    fi
}

disarm() {
    rm -f "$DIR/armed.txt"
    sync
    if [ "$(getenv bootcmd)" = "$ARMED_BOOTCMD" ]; then
        fw_setenv bootcmd "$STOCK_BOOTCMD"
    fi
}

fail() {
    set_state fail
    rm -f "$DIR/armed.txt"
    sync
    if [ "$(getenv bootcmd)" != "$STOCK_BOOTCMD" ]; then
        fw_setenv bootcmd "$STOCK_BOOTCMD"
    fi
    log "FAIL: $1. Попытки загрузки на 50 МГц прекращены" "FAIL: $2. 50 MHz boot attempts stopped"
}

ddr_off() {
    rm -f "$DIR/ddr.txt"
    fw_setenv boot_zmod "$BOOT_ZMOD_STD"
    state=trial
    set_state trial
    set_fails 0
    log "DDR52 не работает: $1. ddr.txt удалён, обычный режим" "DDR52 does not work: $2. ddr.txt removed, normal mode"
    arm_trial
}

has_space() {
    free=$(df -k /data | awk 'NR==2 {print $4}')
    if [ -z "$free" ]; then
        log "тест: не удалось определить свободное место в /data" "test: cannot determine free space in /data"
        return 1
    fi
    if [ "$free" -lt $((TEST_MB * 1024 * 2)) ]; then
        log "тест: мало места в /data (${free} КБ)" "test: not enough space in /data (${free} KB)"
        return 1
    fi
    return 0
}

arm_trial() {
    if [ "$state" = "ok" ] || has_space; then
        arm
    else
        disarm
        log "разовая загрузка 50 МГц не включена: тест невозможен" "one-shot 50 MHz boot not armed: test not possible"
    fi
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
    if ! has_space; then
        return 2
    fi

    t0=$(date +%s)
    w1=$(dd if=/dev/urandom bs=1M count=$TEST_MB 2>/dev/null | tee "$TEST_FILE" | sha256sum | cut -d' ' -f1)
    sync
    t1=$(date +%s)
    drop_caches
    w2=$(sha256sum "$TEST_FILE" 2>/dev/null | cut -d' ' -f1)
    if [ -z "$w2" ]; then
        log "тест: записанный файл не прочитан" "test: written file could not be read"
        rm -f "$TEST_FILE"
        return 1
    fi
    if [ "$w1" != "$w2" ]; then
        log "тест: данные после записи не совпали ($w1 / $w2)" "test: data mismatch after write ($w1 / $w2)"
        rm -f "$TEST_FILE"
        return 1
    fi
    log "тест: запись ${TEST_MB} МБ за $((t1 - t0)) с" "test: write ${TEST_MB} MB in $((t1 - t0)) s"

    drop_caches
    t0=$(date +%s)
    r1=$(dd if="$TEST_FILE" bs=1M 2>/dev/null | sha256sum | cut -d' ' -f1)
    t1=$(date +%s)
    rm -f "$TEST_FILE"
    sync
    if [ "$r1" != "$w1" ]; then
        log "тест: чтение нестабильно ($w1 / $r1)" "test: unstable read ($w1 / $r1)"
        return 1
    fi
    log "тест: чтение ${TEST_MB} МБ за $((t1 - t0)) с" "test: read ${TEST_MB} MB in $((t1 - t0)) s"

    if [ "$(mmc_errors)" != "0" ]; then
        log "тест: ошибки mmc в dmesg после теста" "test: mmc errors in dmesg after test"
        return 1
    fi
    return 0
}

mkdir -p "$DIR"

# Файлы первой версии
rm -f "$DIR/state" "$DIR/fails" "$DIR/armed" "$DIR/boot_id"

if [ -f "$DIR/disable.txt" ]; then
    rm -f "$DIR/armed.txt"
    if [ "$(getenv bootcmd)" = "$ARMED_BOOTCMD" ]; then
        fw_setenv bootcmd "$STOCK_BOOTCMD"
        log "disable.txt: разовая загрузка 50 МГц отключена" "disable.txt: one-shot 50 MHz boot disabled"
    fi
    sync
    exit 0
fi

boot_id=$(cat /proc/sys/kernel/random/boot_id)
if [ "$(read_file "$DIR/boot_id.txt")" = "$boot_id" ]; then
    exit 0
fi
echo "$boot_id" > "$DIR/boot_id.txt"
rotate_log

version=$(read_file "$DIR/version.txt")
if [ "${version:-0}" -lt "$VERSION" ]; then
    if [ -f "$DIR/state.txt" ]; then
        log "алгоритм обновлён (версия ${version:-0} -> $VERSION), тест заново" "algorithm updated (version ${version:-0} -> $VERSION), retesting"
    fi
    rm -f "$DIR/state.txt" "$DIR/fails.txt" "$DIR/armed.txt"
    echo "$VERSION" > "$DIR/version.txt"
    sync
fi

state=$(read_file "$DIR/state.txt")
fails=$(read_file "$DIR/fails.txt")
if [ -z "$fails" ]; then
    fails=0
fi

mem=$(awk '/^MemTotal:/ {print int($2 / 1024)}' /proc/meminfo)
if [ "$mem" -gt 160 ]; then
    method=A
    BOOT_ZMOD_STD="$BOOT_ZMOD_A"
    BOOT_ZMOD_DDR="$BOOT_ZMOD_A_DDR"
else
    method=B
    BOOT_ZMOD_STD="$BOOT_ZMOD_B"
    BOOT_ZMOD_DDR="$BOOT_ZMOD_B_DDR"
fi
BOOT_ZMOD="$BOOT_ZMOD_STD"
MARK=zmod_emmc_50
if [ -f "$DIR/ddr.txt" ]; then
    BOOT_ZMOD="$BOOT_ZMOD_DDR"
    MARK=zmod_emmc_ddr
fi

if [ "$state" = "fail" ]; then
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

if [ "$(getenv boot_zmod)" != "$BOOT_ZMOD" ]; then
    fw_setenv boot_zmod "$BOOT_ZMOD"
    if [ "$(getenv boot_zmod)" != "$BOOT_ZMOD" ]; then
        log "ОШИБКА: не удалось записать boot_zmod" "ERROR: failed to write boot_zmod"
        exit 1
    fi
    log "boot_zmod записан" "boot_zmod written"
fi

if [ ! -r "$IOS" ]; then
    mount -t debugfs none /sys/kernel/debug 2>/dev/null
fi
mf=$(hexdump -ve '1/1 "%02x"' "$NODE/max-frequency")
clk=$(awk '/^clock:/ {print $2}' "$IOS" 2>/dev/null)
timing=$(awk '/^timing spec:/ {print $3}' "$IOS" 2>/dev/null)
errors=$(mmc_errors)
mhz=$(( ${clk:-0} / 1000000 ))
marker=0
if grep -q "$MARK" /proc/cmdline; then
    marker=1
fi
any_marker=0
if grep -q 'zmod_emmc_' /proc/cmdline; then
    any_marker=1
fi
if [ "$bootcmd" = "$ARMED_BOOTCMD" ]; then
    bc=armed
else
    bc=stock
fi
log "загрузка: частота ${mhz} МГц, dtb=$mf timing=$timing ошибки=$errors память=${mem} МБ метод=$method ddr=$MARK boot_zmod=$marker bootcmd=$bc state=$state fails=$fails" "boot: clock ${mhz} MHz, dtb=$mf timing=$timing errors=$errors mem=${mem} MB method=$method ddr=$MARK boot_zmod=$marker bootcmd=$bc state=$state fails=$fails"

if [ "$mf" = "02faf080" ]; then
    rm -f "$DIR/armed.txt"
    sync

    if [ -f "$DIR/ddr.txt" ]; then
        if [ "$marker" = "1" ]; then
            if [ "$timing" != "8" ]; then
                ddr_off "режим timing=$timing вместо 8" "timing=$timing instead of 8"
                exit 0
            fi
            if [ "$errors" != "0" ]; then
                ddr_off "ошибки mmc: $errors" "mmc errors: $errors"
                exit 0
            fi
        fi
    fi

    if [ -z "$clk" ]; then
        fail "не удалось прочитать $IOS (debugfs)" "cannot read $IOS (debugfs)"
        exit 0
    fi
    if [ "$clk" != "50000000" ]; then
        fail "частота ${mhz} МГц вместо 50 МГц (чип не поддерживает HS52)" "clock ${mhz} MHz instead of 50 MHz (chip does not support HS52)"
        exit 0
    fi
    if [ "$errors" != "0" ]; then
        fail "ошибки mmc в dmesg: $errors" "mmc errors in dmesg: $errors"
        exit 0
    fi

    if [ "$state" = "ok" ] && [ "$marker" = "1" ]; then
        set_fails 0
        arm
    elif [ "$marker" != "1" ]; then
        set_state trial
        set_fails 0
        log "загрузка не через текущий boot_zmod, тест при следующей перезагрузке" "boot not via current boot_zmod, test on next reboot"
        arm_trial
    else
        emmc_test
        result=$?
        if [ "$result" = "0" ]; then
            set_state ok
            set_fails 0
            log "тест пройден" "test passed"
            arm
        elif [ "$result" = "2" ]; then
            set_state trial
            log "тест невозможен, разовая загрузка 50 МГц не включена" "test not possible, one-shot 50 MHz boot not armed"
        elif [ -f "$DIR/ddr.txt" ]; then
            ddr_off "тест чтения/записи не пройден" "read/write test failed"
        else
            fail "тест чтения/записи не пройден" "read/write test failed"
        fi
    fi
else
    if [ "$any_marker" = "1" ]; then
        fail "boot_zmod выполнен, но dtb не изменён (U-Boot не применил fdt, метод $method)" "boot_zmod ran but dtb was not patched (U-Boot did not apply fdt, method $method)"
        exit 0
    fi
    if [ -z "$state" ]; then
        set_state trial
        set_fails 0
        log "первый запуск, тестовая загрузка при следующей перезагрузке" "first run, test boot on next reboot"
        arm_trial
    elif [ -f "$DIR/armed.txt" ] && [ -f "$DIR/ddr.txt" ]; then
        ddr_off "загрузка не дошла до системы" "boot did not reach the system"
    elif [ -f "$DIR/armed.txt" ]; then
        fails=$((fails + 1))
        set_fails $fails
        log "загрузка на 50 МГц не дошла до системы ($fails из $MAX_FAILS), сейчас ${mhz} МГц" "50 MHz boot did not reach the system ($fails of $MAX_FAILS), now ${mhz} MHz"
        if [ "$fails" -ge "$MAX_FAILS" ]; then
            fail "$MAX_FAILS неудачных загрузок подряд" "$MAX_FAILS failed boots in a row"
        else
            arm_trial
        fi
    else
        log "разовая загрузка не была включена, включаю" "one-shot boot was not armed, arming"
        arm_trial
    fi
fi

exit 0

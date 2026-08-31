#!/bin/sh
# (C) 2024-2026 ghzserg https://github.com/ghzserg/zmod

set -x

unset LD_LIBRARY_PATH
unset LD_PRELOAD

check_link()
{
    a=$(readlink "$1" 2>/dev/null)
    if [ "$a" != "$2" ]; then
        /bin/echo -n "$1 - Incorrect link ($a!=$2): "
        rm -f "$1" 2>/dev/null
        ln -s "$2" "$1" 2>/dev/null && echo "Исправлено"  || echo "Ошибка исправления"
    fi
}

# Активация мода для AD5X и C5PRO
enable_zmod_ad5x_c5pro()
{
    # Удаляем старую ссылку
    grep -q '/usr/data/config/mod/.shell/fix_config.sh start' /usr/prog/klipper/start.sh && sed -i '/fix_config.sh/d' /usr/prog/klipper/start.sh
    grep -q '/usr/data/config/mod/.shell/app_startup_mcu.sh' /usr/prog/app_startup.sh && sed -i '/app_startup_mcu.sh/d' /usr/prog/app_startup.sh
    grep -q '/usr/data/config/mod/.shell/prepare.sh' /usr/prog/app_startup.sh && sed -i '/prepare.sh/d' /usr/prog/app_startup.sh

    grep -q '/usr/data/zmod/zmod/.shell/fix_config.sh start' /usr/prog/klipper/start.sh || sed -i '2 i\/usr/data/zmod/zmod/.shell/fix_config.sh start' /usr/prog/klipper/start.sh
    grep -q "mount --bind /bin/echo /usr/bin/cmd_pwm" /usr/prog/app_startup.sh || sed -i '\#mount /usr/prog/etc /etc#a\mount --bind /bin/echo /usr/bin/cmd_pwm' /usr/prog/app_startup.sh

    # Активируем мод
    if ! grep -q prepare.sh /usr/prog/app_startup.sh; then
        echo "Aktivate Z-Mod"

        cat /usr/prog/app_startup.sh >/tmp/startup.sh

        awk '{ print }
        END {
          if (NR > 0 && $0 !~ /\/usr\/data\/zmod\/zmod\/\.shell\/prepare\.sh/) {
            print "/usr/data/zmod/zmod/.shell/prepare.sh"
          }
        }' /tmp/startup.sh >/usr/prog/app_startup.sh
        sync
    fi
}

enable_zmod_ad5m()
{
    check_link /bin/dropbearkey /usr/data/zmod/zmod/.shell/eabi/dropbear
    check_link /bin/dropbear /usr/data/zmod/zmod/.shell/eabi/dropbear
    check_link /bin/dbclient /usr/data/zmod/zmod/.shell/eabi/dropbear
    check_link /bin/scp /usr/data/zmod/zmod/.shell/eabi/dropbear
    check_link /bin/ssh /usr/data/zmod/zmod/.shell/eabi/dropbear

    check_link /etc/init.d/S00fix /usr/data/zmod/zmod/.shell/fix_config.sh
    check_link /etc/init.d/S60dropbear /usr/data/zmod/zmod/.shell/S60dropbear
    check_link /etc/init.d/S98zssh /usr/data/zmod/zmod/.shell/S98zssh
    check_link /etc/init.d/S99camera /usr/data/zmod/zmod/.shell/S99camera
    check_link /etc/init.d/S99moon /usr/data/zmod/zmod/.shell/S99moon
    check_link /etc/init.d/K99moon /usr/data/zmod/zmod/.shell/S99moon
    check_link /etc/init.d/prepare.sh /usr/data/zmod/zmod/.shell/prepare.sh
}

# Если у нас еще принтер не перешел на новые каталоги
if ! [ -f /usr/data/zmod/zmod/.shell/0.sh ]; then
    if [ -f /opt/config/mod/.shell/0.sh ]; then
        source /opt/config/mod/.shell/0.sh
    else if [ -f /usr/data/config/mod/.shell/0.sh ]; then
        source /usr/data/config/mod/.shell/0.sh
    fi
    fi
    mkdir -p /usr/data/zmod/
    if [ ${AD5M} -eq 1 ]; then
        mv /opt/config/base/klipper/ /usr/data/zmod/
        mv /opt/config/base/moonraker/ /usr/data/zmod/

        enable_zmod_ad5m
        sync

        mv /opt/config/mod/ /usr/data/zmod/zmod/
        sync && sleep 10 && reboot
        exit 0
    fi
    if [ ${C5PRO} -eq 1 ] || [ ${AD5X} -eq 1 ] ; then
        mv /usr/data/config/base/klipper/ /usr/data/zmod/
        mv /usr/data/config/base/moonraker/ /usr/data/zmod/

        enable_zmod_ad5x_c5pro
        sync
        mv /usr/data/config/mod/ /usr/data/zmod/zmod/ 
        sync && sleep 10 && reboot
        exit 0
    fi
fi

source /usr/data/zmod/zmod/.shell/0.sh
mkdir -p /usr/data/zmod/klipper/ /usr/data/zmod/moonraker/ ${MOD_CONF}/mod

if [ ${C5PRO} -eq 1 ] && grep -q 'START=on' ${MOD_CONF}/mod_data/camera.conf; then
    mv /dev/video0 /dev/video67
fi

# Разблокировка
china_razbl()
{
    grep -q "$1" /etc/hosts && sed -i "/$1/d" /etc/hosts
}

# Блокировка
china_block()
{
    grep -q "$1" /etc/hosts || sed -i "2 i\127.0.0.1 $1" /etc/hosts
}


restore_base()
{
    grep -q '^\[include mod.user.cfg' ${MOD_CONF}/printer.cfg && sed -i '/include mod.user.cfg/d' ${MOD_CONF}/printer.cfg
    grep -q '^\[include ./mod/mod.cfg' ${MOD_CONF}/printer.cfg && sed -i '/mod.cfg/d' ${MOD_CONF}/printer.cfg
    grep -q '^\[include ./mod/klipper11.cfg' ${MOD_CONF}/printer.cfg && sed -i '/klipper11.cfg/d' ${MOD_CONF}/printer.cfg
    grep -q '^\[include ./mod/klipper13.cfg' ${MOD_CONF}/printer.cfg && sed -i '/klipper13.cfg/d' ${MOD_CONF}/printer.cfg
    grep -q '^\[include ./mod_data/plugins.cfg' ${MOD_CONF}/printer.cfg && sed -i '/plugins.cfg/d' ${MOD_CONF}/printer.cfg
    grep -q '^\[include ./mod_data/user.cfg' ${MOD_CONF}/printer.cfg && sed -i '/user.cfg/d' ${MOD_CONF}/printer.cfg
    grep -q '^\[include ./mod/switch_sensor.cfg' ${MOD_CONF}/printer.cfg && sed -i '/switch_sensor.cfg/d' ${MOD_CONF}/printer.cfg
    grep -q '^\[include ./mod/motion_sensor.cfg' ${MOD_CONF}/printer.cfg && sed -i '/motion_sensor.cfg/d' ${MOD_CONF}/printer.cfg
    grep -q '^\[include ./mod/switch_sensor_display_off.cfg' ${MOD_CONF}/printer.cfg && sed -i '/switch_sensor_display_off.cfg/d' ${MOD_CONF}/printer.cfg
    grep -q '^\[include ./mod/display_off.cfg' ${MOD_CONF}/printer.cfg && sed -i '/display_off.cfg/d' ${MOD_CONF}/printer.cfg

    if [ ${AD5M} -eq 1 ]; then
        #logo
        mount /dev/mmcblk0p1 /lost+found
        [ -f /lost+found/boot.bmp ] && cp /lost+found/boot.bmp /lost+found/bootlogo.bmp && rm -f /lost+found/boot.bmp
        umount /lost+found

        china_razbl api.cloud.flashforge.com
        china_razbl api.fdmcloud.flashforge.com
        china_razbl cloud.sz3dp.com
        china_razbl hz.sz3dp.com
        china_razbl printer2.polar3d.com
        china_razbl qvs.qiniuapi.com
        china_razbl update.cn.sz3dp.com
        china_razbl update.sz3dp.com
        china_razbl cloud.sz3dp.com
        china_razbl polar3d.com

        grep -q zmod ${KLIPPER_DIR}/klippy/extras/spi_temperature.py && cp /usr/data/zmod/zmod/.shell/spi_temperature.py.orig ${KLIPPER_DIR}/klippy/extras/spi_temperature.py
        grep -q zmod /opt/klipper/start.sh && cp /usr/data/zmod/zmod/.shell/start.sh.orig /opt/klipper/start.sh
    fi
    if [ ${C5PRO} -eq 1 ] || [ ${AD5X} -eq 1 ]; then
        [ -f /usr/prog/logo.jpeg ] && rm -f /usr/prog/logo.jpeg
        sed -i '\|mount --bind /bin/echo /usr/bin/cmd_pwm|d' /usr/prog/app_startup.sh
        sed -i '\|/usr/data/zmod/zmod/.shell/app_startup_mcu.sh|d' /usr/prog/app_startup.sh
    fi
    if [ ${C5PRO} -eq 1 ]; then
        rm -f ${KLIPPER_DIR}/klippy/extras/zmod_color.py
    fi
    if [ ${AD5X} -eq 1 ]; then
        grep -q zmod ${KLIPPER_DIR}/klippy/extras/virtual_sdcard.py && cp /usr/data/zmod/zmod/.shell/virtual_sdcard.py.orig ${KLIPPER_DIR}/klippy/extras/virtual_sdcard.py

        rm -f ${KLIPPER_DIR}/klippy/extras/zmod_color.py
        rm -f ${KLIPPER_DIR}/klippy/extras/zmod_tenz.py
        rm -f ${KLIPPER_DIR}/klippy/extras/zmod_ifs.py
        rm -f ${KLIPPER_DIR}/klippy/extras/zmod_ifs_switch_sensor.py
        rm -f ${KLIPPER_DIR}/klippy/extras/zmod_ifs_motion_sensor.py
    fi
    grep -q _output_callback_gcode ${KLIPPER_DIR}/klippy/webhooks.py && cp /usr/data/zmod/zmod/.shell/webhooks.py.orig ${KLIPPER_DIR}/klippy/webhooks.py
    grep -q ZLOAD_VARIABLE ${KLIPPER_DIR}/klippy/extras/save_variables.py && cp /usr/data/zmod/zmod/.shell/save_variables.py.orig ${KLIPPER_DIR}/klippy/extras/save_variables.py
    grep -q receive_time ${KLIPPER_DIR}/klippy/extras/buttons.py && cp /usr/data/zmod/zmod/.shell/buttons.py.orig ${KLIPPER_DIR}/klippy/extras/buttons.py
    rm -f ${KLIPPER_DIR}/klippy/extras/zmod.py
    rm -f ${KLIPPER_DIR}/klippy/extras/ens160.py

    rm -f /etc/profile.d/path.sh

    F="${KLIPPER_DIR}/klippy/toolhead.py"
    grep -q "LOOKAHEAD_FLUSH_TIME = 0.5" $F || sed -i 's|^LOOKAHEAD_FLUSH_TIME.*|LOOKAHEAD_FLUSH_TIME = 0.5|' $F

    F="${KLIPPER_DIR}/klippy/mcu.py"
    grep -q "TRSYNC_TIMEOUT = 0.025" $F || sed -i 's|^TRSYNC_TIMEOUT = .*|TRSYNC_TIMEOUT = 0.025|' $F

    if [ -L ${KLIPPER_DIR}/klippy/extras/load_cell_tare.py ] || [ -f ${KLIPPER_DIR}/klippy/extras/load_cell_tare.py ]; then
        rm -f ${KLIPPER_DIR}/klippy/extras/load_cell_tare.py
    fi

    # Удаляем controller_fan driver_fan
    if [ ${C5PRO} -eq 0 ] && grep -q '^\[controller_fan driver_fan' ${MOD_CONF}/printer.base.cfg; then
        cd ${MOD_CONF}
        sed -e '/^\[controller_fan driver_fan/,/^\[/d' printer.base.cfg >printer.base.tmp
        diff -u printer.base.cfg printer.base.tmp | grep -v "printer.base.cfg" |grep "^-" | cut -b 2- >heater_bed.txt
        sed -i '$d' heater_bed.txt
        num=$(wc -l heater_bed.txt|cut  -d " " -f1)
        num=$(($num-1))
        sed -e "/^\[controller_fan driver_fan/,+${num}d;" printer.base.cfg >printer.base.tmp
        mv printer.base.tmp printer.base.cfg
        rm -f heater_bed.txt
    fi

    # Возвращаем fan_generic internal_fan
    if [ ${AD5M} -eq 1 ]; then
        if ! grep -q '^\[fan_generic internal_fan' ${MOD_CONF}/printer.base.cfg; then
            echo "
[fan_generic internal_fan]
pin:PB8
" >>${MOD_CONF}/printer.base.cfg
        fi

        # Возвращаем fan_generic external_fan
        if ! grep -q '^\[fan_generic external_fan' ${MOD_CONF}/printer.base.cfg; then
            echo "
[fan_generic external_fan]
pin:PB6
" >>${MOD_CONF}/printer.base.cfg
        fi
    fi

    # Возвращаем fan_generic pcb_fan

    if [ ${AD5X} -eq 1 ]; then PIN="PA5"; fi
    if [ ${AD5M} -eq 1 ]; then PIN="PB7"; fi
    if [ ${C5PRO} -eq 0 ] && ! grep -q '^\[fan_generic pcb_fan' ${MOD_CONF}/printer.base.cfg; then
        echo "
[fan_generic pcb_fan]
pin:${PIN}
" >>${MOD_CONF}/printer.base.cfg
    fi

    if [ ${AD5M} -eq 1 ]; then
        # Возвращаем gcode_button check_level_pin
        if ! grep -q '^\[gcode_button check_level_pin' ${MOD_CONF}/printer.base.cfg; then
            echo '
[gcode_button check_level_pin]
pin: !PE0
press_gcode:
    M105
' >>${MOD_CONF}/printer.base.cfg
        fi

        if grep -q "motion_sensor = 1" ${MOD_CONF}/mod_data/variables.cfg; then
            # Возвращаем filament_motion_sensor e0_sensor
            if ! grep -q '^\[filament_motion_sensor e0_sensor' ${MOD_CONF}/printer.base.cfg; then
                echo '
[filament_motion_sensor e0_sensor]
detection_length: 8
extruder: extruder
switch_pin: !PB14
pause_on_runout: True
runout_gcode:
  RESPOND TYPE=command MSG="!! Кончился или остановился филамент"
' >>${MOD_CONF}/printer.base.cfg
            fi
        else
            # Возвращаем filament_switch_sensor e0_sensor
            if ! grep -q '^\[filament_switch_sensor e0_sensor' ${MOD_CONF}/printer.base.cfg; then
                echo '
[filament_switch_sensor e0_sensor]
pause_on_runout: False
switch_pin: !PB14
event_delay: 1.0

' >>${MOD_CONF}/printer.base.cfg
            fi
        fi # end motion_sensor

        # Возвращаем weightValue
        if ! grep -q '^\[temperature_sensor weightValue' ${MOD_CONF}/printer.base.cfg; then
            echo '[temperature_sensor weightValue]
sensor_type: MAX31856
sensor_pin: PD5
#spi_bus: spi4
spi_speed: 1000000
spi_software_sclk_pin: PD6
spi_software_mosi_pin: PD7
spi_software_miso_pin: PD8
min_temp: 0
max_temp: 2048
gcode_id: W

' >>${MOD_CONF}/printer.base.cfg
        fi

        # Возвращаем tvocValue
        if ! grep -q '^\[temperature_sensor tvocValue' ${MOD_CONF}/printer.base.cfg; then
        echo '[temperature_sensor tvocValue]
sensor_type: MAX31865
sensor_pin: PD4
#spi_bus: spi4
#cs_pin: PD0
spi_speed: 500000
spi_software_sclk_pin: PE3
spi_software_mosi_pin: PE4
spi_software_miso_pin: PE5
min_temp: 0
max_temp: 2048
gcode_id: V

' >>${MOD_CONF}/printer.base.cfg
        fi
    fi # End AD5M

    grep -q '^minimum_cruise_ratio' ${MOD_CONF}/printer.base.cfg && sed -i 's|^minimum_cruise_ratio.*|max_accel_to_decel:5000|' ${MOD_CONF}/printer.base.cfg
}

fix_config()
{
    echo "START fix_config"
    date
    echo 15 > /proc/sys/vm/swappiness

    if [ ${C5PRO} -eq 1 ] || [ ${AD5X} -eq 1 ]; then
        /usr/data/zmod/zmod/.shell/serial/serial_start.sh
        if [ -L /etc/dropbear \
             -a "$(readlink /etc/dropbear)" = "/var/run/dropbear" ]
        then
                if rm -f /etc/dropbear >/dev/null 2>&1; then
                        mkdir -p /etc/dropbear
                else
                        mkdir -p "$(readlink /etc/dropbear)"
                fi
        fi
        /etc/init.d/S50dropbear restart
    fi

    fstrim ${DATA} -v
    if [ ${AD5M} -eq 1 ]; then fstrim / -v; fi
    if [ ${C5PRO} -eq 1 ] || [ ${AD5X} -eq 1 ]; then fstrim /usr/prog -v; fi

    [ -f /etc/profile.d/path.sh ] || echo "export PATH=\"$PATH:/opt/bin/:/opt/sbin/\"" >/etc/profile.d/path.sh

    mkdir -p ${MOD_CONF}/mod_data/database/
    [ -f ${MOD_CONF}/mod_data/user.cfg ] || echo "" >${MOD_CONF}/mod_data/user.cfg

    [ -f ${MOD_CONF}/mod_data/plugins.cfg ] || echo "" >${MOD_CONF}/mod_data/plugins.cfg
    [ -f ${MOD_CONF}/mod_data/plugins.moonraker.conf ] || echo "" >${MOD_CONF}/mod_data/plugins.moonraker.conf
    [ -f ${MOD_CONF}/mod_data/extra_plugins.moonraker.conf ] || echo "" >${MOD_CONF}/mod_data/extra_plugins.moonraker.conf
    grep -q bambufy ${MOD_CONF}/mod_data/plugins.cfg && echo "[include ../mod/extra_plugins.moonraker.conf]" >${MOD_CONF}/mod_data/extra_plugins.moonraker.conf

    [ -d ${MOD_CONF}/mod_data/plugins ] || mkdir -p ${MOD_CONF}/mod_data/plugins
    [ -f ${MOD_CONF}/mod_data/variables.cfg ] || echo "[Variables]" >${MOD_CONF}/mod_data/variables.cfg

    # logo
    if [ ${C5PRO} -eq 1 ] || [ ${AD5X} -eq 1 ]; then
        if ! [ -f ${MOD_CONF}/mod_data/logo/logo.jpeg ]; then
            mkdir -p ${MOD_CONF}/mod_data/logo/
            cp /usr/data/zmod/zmod/.shell/logo/logo.jpeg ${MOD_CONF}/mod_data/logo/
        else
            logo_cur=$(md5sum ${MOD_CONF}/mod_data/logo/logo.jpeg| awk '{print $1}')
            if [ "$logo_cur" == "d03570f4f638bb0333fa747a9661c7ff" ]; then
                cp /usr/data/zmod/zmod/.shell/logo/logo.jpeg ${MOD_CONF}/mod_data/logo/
            fi
        fi
        current_logo=$(md5sum /usr/prog/logo.jpeg| awk '{print $1}')
        mod_data_logo=$(md5sum ${MOD_CONF}/mod_data/logo/logo.jpeg | awk '{print $1}')
        [ "${current_logo}" != "${mod_data_logo}" ] && cp ${MOD_CONF}/mod_data/logo/logo.jpeg /usr/prog/logo.jpeg

        # Color
        [ -f ${MOD_CONF}/mod_data/color.json ] && rm -f ${MOD_CONF}/mod_data/color.json

        mkdir -p ${MOD_CONF}/mod_data/color/
        for lang in ru en de fr it es pt zh ja ko cs tr; do
          [ -f "${MOD_CONF}/mod_data/color/${lang}.json" ] || cp "/usr/data/zmod/zmod/.shell/color/${lang}.json" "${MOD_CONF}/mod_data/color/"
        done

        md5=$(md5sum ${MOD_CONF}/mod_data/cmd_pwm 2>/dev/null |awk '{print $1}')
        if [ "$md5" != "bb0a72766632c11bd83ae68a8da94688" ]; then
            umount /usr/bin/cmd_pwm
            cp /usr/bin/cmd_pwm ${MOD_CONF}/mod_data/cmd_pwm
            mount --bind /bin/echo /usr/bin/cmd_pwm
        fi
        grep -q "mount --bind /bin/echo /usr/bin/cmd_pwm" /usr/prog/app_startup.sh || sed -i '\#mount /usr/prog/etc /etc#a\mount --bind /bin/echo /usr/bin/cmd_pwm' /usr/prog/app_startup.sh
        grep -q "/usr/data/zmod/zmod/.shell/app_startup_mcu.sh" /usr/prog/app_startup.sh || sed -i '\#mount --bind /bin/echo /usr/bin/cmd_pwm#a\/usr/data/zmod/zmod/.shell/app_startup_mcu.sh' /usr/prog/app_startup.sh
    fi
    if [ ${AD5M} -eq 1 ]; then

        if ! [ -f ${MOD_CONF}/mod_data/logo/bootlogo.bmp ]; then
            mkdir -p ${MOD_CONF}/mod_data/logo/
            cp /usr/data/zmod/zmod/.shell/logo/bootlogo.bmp ${MOD_CONF}/mod_data/logo/
        else
            logo_cur=$(md5sum ${MOD_CONF}/mod_data/logo/bootlogo.bmp| awk '{print $1}')
            if [ "$logo_cur" == "d237114952a89448d13b8051c4f3dd93" ]; then
                cp /usr/data/zmod/zmod/.shell/logo/bootlogo.bmp ${MOD_CONF}/mod_data/logo/
            fi
        fi

        mount /dev/mmcblk0p1 /lost+found

        [ -f /lost+found/boot.bmp ] || cp /lost+found/bootlogo.bmp /lost+found/boot.bmp
        logo_save=$(md5sum /lost+found/boot.bmp| awk '{print $1}')
        if [ "$logo_save" != "a927ccad137533d0c239b03a20815e56" ]; then
            mod_data_logo_save=$(md5sum "${MOD_CONF}/mod_data/logo/boot.bmp"| awk '{print $1}')
            [ "$mod_data_logo_save" == "a927ccad137533d0c239b03a20815e56" ] && cp "${MOD_CONF}/mod_data/logo/boot.bmp" /lost+found/boot.bmp
        fi

        current_logo=$(md5sum /lost+found/bootlogo.bmp| awk '{print $1}')
        mod_data_logo=$(md5sum ${MOD_CONF}/mod_data/logo/bootlogo.bmp | awk '{print $1}')
        [ "${current_logo}" != "${mod_data_logo}" ] && cp ${MOD_CONF}/mod_data/logo/bootlogo.bmp /lost+found/bootlogo.bmp

        umount /lost+found
    fi

    echo "[zmod]
    language: ${ZLANG}" >${MOD_CONF}/mod_data/lang.cfg

    check_link ${MOD_CONF}/mod/shell.cfg /usr/data/zmod/zmod/shell.cfg
    check_link ${MOD_CONF}/mod/moonraker.conf  /usr/data/zmod/zmod/moonraker.conf
    check_link ${MOD_CONF}/mod/extra_plugins.moonraker.conf  /usr/data/zmod/zmod/extra_plugins.moonraker.conf
    check_link ${MOD_CONF}/mod/KAMP /usr/data/zmod/zmod/KAMP

    check_link ${MOD_CONF}/mod/base.cfg /usr/data/zmod/zmod/translate/${ZLANG}/base.cfg
    check_link ${MOD_CONF}/mod/base_mod.cfg /usr/data/zmod/zmod/translate/${ZLANG}/base_mod.cfg
    check_link ${MOD_CONF}/mod/base_display_off.cfg /usr/data/zmod/zmod/translate/${ZLANG}/base_display_off.cfg
    check_link ${MOD_CONF}/mod/client.cfg /usr/data/zmod/zmod/translate/${ZLANG}/base_client.cfg
    check_link ${MOD_CONF}/mod/base_klipper13.cfg /usr/data/zmod/zmod/translate/${ZLANG}/base_klipper13.cfg

    [ -f ${MOD_CONF}/.theme/custom.css ] || cp -a /usr/data/zmod/zmod/.shell/.theme ${MOD_CONF}/mod_data/
    check_link ${MOD_CONF}/.theme mod_data/.theme

    if [ ${AD5M} -eq 1 ]; then
        check_link ${MOD_CONF}/mod/switch_sensor.cfg /usr/data/zmod/zmod/translate/${ZLANG}/ff5m_switch_sensor.cfg
        check_link ${MOD_CONF}/mod/klipper13.cfg /usr/data/zmod/zmod/translate/${ZLANG}/ff5m_klipper13.cfg
        check_link ${MOD_CONF}/mod/ff5m_klipper11.cfg /usr/data/zmod/zmod/translate/${ZLANG}/ff5m_klipper11.cfg
        grep -q '^MACHINE=Adventurer5MPro$' /opt/auto_run.sh && check_link ${MOD_CONF}/mod/klipper11.cfg /usr/data/zmod/zmod/translate/${ZLANG}/ff5m_klipper11_pro.cfg || check_link ${MOD_CONF}/mod/klipper11.cfg /usr/data/zmod/zmod/translate/${ZLANG}/ff5m_klipper11.cfg
        check_link ${MOD_CONF}/mod/display_off.cfg /usr/data/zmod/zmod/translate/${ZLANG}/ff5m_display_off.cfg
        check_link ${MOD_CONF}/mod/generic.cfg /usr/data/zmod/zmod/translate/${ZLANG}/ff5m_generic.cfg
        check_link ${MOD_CONF}/mod/mod.cfg /usr/data/zmod/zmod/translate/${ZLANG}/ff5m_mod.cfg
        check_link ${MOD_CONF}/mod/ff5m_config_native.cfg /usr/data/zmod/zmod/translate/${ZLANG}/ff5m_config_native.cfg
        check_link ${MOD_CONF}/mod/ff5m_config_off.cfg /usr/data/zmod/zmod/translate/${ZLANG}/ff5m_config_off.cfg
        check_link ${MOD_CONF}/mod/motion_sensor.cfg /usr/data/zmod/zmod/translate/${ZLANG}/ff5m_motion_sensor.cfg
        check_link ${MOD_CONF}/mod/switch_sensor_display_off.cfg /usr/data/zmod/zmod/translate/${ZLANG}/ff5m_switch_sensor_display_off.cfg
    fi
    if [ ${AD5X} -eq 1 ]; then
        check_link ${MOD_CONF}/mod/generic.cfg /usr/data/zmod/zmod/translate/${ZLANG}/ad5x_generic.cfg
        check_link ${MOD_CONF}/mod/mod.cfg /usr/data/zmod/zmod/translate/${ZLANG}/ad5x_mod.cfg
        check_link ${MOD_CONF}/mod/klipper13.cfg /usr/data/zmod/zmod/translate/${ZLANG}/ad5x_klipper13.cfg
        check_link ${MOD_CONF}/mod/display_off.cfg /usr/data/zmod/zmod/translate/${ZLANG}/ad5x_display_off.cfg
        check_link ${MOD_CONF}/mod/ad5x_config_native.cfg /usr/data/zmod/zmod/translate/${ZLANG}/ad5x_config_native.cfg
        check_link ${MOD_CONF}/mod/ad5x_config_off.cfg /usr/data/zmod/zmod/translate/${ZLANG}/ad5x_config_off.cfg

        # В Версии 1.0.7 перенесли конфиг в /usr/prog/config/
        [ -d /usr/prog/config/mod ] && rm -rf /usr/prog/config/mod
        [ -d /usr/prog/config/mod_data ] && rm -rf /usr/prog/config/mod_data
        [ -d /usr/prog/config/save ] && rm -rf /usr/prog/config/save
        [ -f /usr/prog/config/Adventurer5M.json ] && check_link ${MOD_CONF}/Adventurer5M.json /usr/prog/config/Adventurer5M.json
        [ -f /usr/prog/config/PowerOff ] && check_link ${MOD_CONF}/PowerOff /usr/prog/config/PowerOff
        [ -f /usr/prog/config/fileSlotId.json ] && check_link ${MOD_CONF}/fileSlotId.json /usr/prog/config/fileSlotId.json
    fi
    if [ ${C5PRO} -eq 1 ]; then
        check_link ${MOD_CONF}/mod/generic.cfg /usr/data/zmod/zmod/translate/${ZLANG}/c5pro_generic.cfg
        check_link ${MOD_CONF}/mod/mod.cfg /usr/data/zmod/zmod/translate/${ZLANG}/c5pro_mod.cfg
        check_link ${MOD_CONF}/mod/klipper13.cfg /usr/data/zmod/zmod/translate/${ZLANG}/c5pro_klipper13.cfg
        check_link ${MOD_CONF}/mod/display_off.cfg /usr/data/zmod/zmod/translate/${ZLANG}/c5pro_display_off.cfg
        check_link ${MOD_CONF}/mod/c5pro_config_native.cfg /usr/data/zmod/zmod/translate/${ZLANG}/c5pro_config_native.cfg
        check_link ${MOD_CONF}/mod/c5pro_config_off.cfg /usr/data/zmod/zmod/translate/${ZLANG}/c5pro_config_off.cfg
    fi


    if ! [ -f ${MOD_CONF}/mod_data/user.moonraker.conf ]; then
        echo "#Enter user config here
[authorization]
trusted_clients:
  0.0.0.0/0

cors_domains:
  *.zmod.link:*
" >${MOD_CONF}/mod_data/user.moonraker.conf;
    fi

    # Защита от самонадеянных, кто выключает SWAP при 128 мегабайтах оперативной памяти
    if [ ${AD5M} -eq 1 ] && grep -q "use_swap = 0" ${MOD_CONF}/mod_data/variables.cfg; then
        MEM=$(cat /proc/meminfo | grep MemTotal| awk '{print $2}')
        MEM=$(($MEM/1024))
        [ "$MEM" -le 128 ] && sed -i "s/use_swap = 0/use_swap = 1/" ${MOD_CONF}/mod_data/variables.cfg
    fi

    [ -f ${MOD_CONF}/mod_data/nozzle.cfg ] || echo "">${MOD_CONF}/mod_data/nozzle.cfg

    if [ ${AD5M} -eq 1 ]; then
        [ -f /etc/init.d/S50sshd ] && rm -f /etc/init.d/S50sshd
        [ -f /etc/init.d/S55date ] && rm -f /etc/init.d/S55date
        [ -f /bin/dropbearmulti ] && rm -f /bin/dropbearmulti
        [ -L /etc/init.d/S98camera ] && rm -f /etc/init.d/S98camera
        [ -f /etc/init.d/S98camera ] && rm -f /etc/init.d/S98camera

        enable_zmod_ad5m
    fi

    mkdir -p ${LOG_FILES}
    check_link ${LOG_FILES}/zmod ${MOD_CONF}/mod_data/log/

    rm -f /usr/bin/audio /usr/bin/audio_midi.sh /usr/lib/python3.7/site-packages/audio.py
    [ -d ${PYTHON_DIR}/site-packages/mido ] && rm -rf ${PYTHON_DIR}/site-packages/mido
    [ -d ${PYTHON_DIR}/site-packages/mido-1.3.3.dist-info ] && rm -rf ${PYTHON_DIR}/site-packages/mido-1.3.3.dist-info
    check_link ${PYTHON_DIR}/site-packages/mido /usr/data/zmod/zmod/.shell/root/mido/
    check_link ${PYTHON_DIR}/site-packages/mido-1.3.3.dist-info /usr/data/zmod/zmod/.shell/root/mido-1.3.3.dist-info/

    NEED_REBOOT=0
    PRINTER_BASE_ORIG="${MOD_CONF}/printer.base.cfg"
    PRINTER_CFG_ORIG="${MOD_CONF}/printer.cfg"
    PRINTER_BASE="/tmp/printer.base.cfg"
    PRINTER_CFG="/tmp/printer.cfg"

    cp ${PRINTER_BASE_ORIG} ${PRINTER_BASE}
    cp ${PRINTER_CFG_ORIG} ${PRINTER_CFG}
    cat ${PRINTER_BASE}
    cat ${PRINTER_CFG}

    if ! [ -f ${MOD_CONF}/mod_data/power_off.sh ]; then
        echo "#!/bin/sh
unset LD_PRELOAD

#${CURL} -k https://mail.ru" >${MOD_CONF}/mod_data/power_off.sh
    fi
    chmod +x ${MOD_CONF}/mod_data/power_off.sh

    if ! [ -f ${MOD_CONF}/mod_data/power_on.sh ]; then
        echo "#!/bin/sh
#Enter Poweron code here" >${MOD_CONF}/mod_data/power_on.sh
    fi
    chmod +x ${MOD_CONF}/mod_data/power_on.sh

    # Rem стукач
    if grep -q "china_cloud = 0" ${MOD_CONF}/mod_data/variables.cfg; then
        if [ ${AD5M} -eq 1 ]; then
            china_block api.cloud.flashforge.com
            china_block api.fdmcloud.flashforge.com
            china_block cloud.sz3dp.com
            china_block hz.sz3dp.com
            china_block printer2.polar3d.com
            china_block qvs.qiniuapi.com
            china_block update.cn.sz3dp.com
            china_block update.sz3dp.com
            china_block cloud.sz3dp.com
            china_block polar3d.com
        fi
        if [ ${C5PRO} -eq 1 ] || [ ${AD5X} -eq 1 ]; then
            mount --bind /usr/data/zmod/zmod/.shell/hosts /etc/hosts
        fi
    else
        if [ ${AD5M} -eq 1 ]; then
            china_razbl api.cloud.flashforge.com
            china_razbl api.fdmcloud.flashforge.com
            china_razbl cloud.sz3dp.com
            china_razbl hz.sz3dp.com
            china_razbl printer2.polar3d.com
            china_razbl qvs.qiniuapi.com
            china_razbl update.cn.sz3dp.com
            china_razbl update.sz3dp.com
            china_razbl cloud.sz3dp.com
            china_razbl polar3d.com
        fi
    fi

    grep -q "zmod 1.1" ${KLIPPER_DIR}/klippy/webhooks.py || cp /usr/data/zmod/zmod/.shell/webhooks.py ${KLIPPER_DIR}/klippy/webhooks.py
    grep -q ZLOAD_VARIABLE ${KLIPPER_DIR}/klippy/extras/save_variables.py || cp /usr/data/zmod/zmod/.shell/save_variables.py ${KLIPPER_DIR}/klippy/extras/save_variables.py
    if [ ${AD5M} -eq 1 ]; then
        grep -q "Zcontrol 1.25" ${KLIPPER_DIR}/klippy/extras/spi_temperature.py || cp /usr/data/zmod/zmod/.shell/spi_temperature.py ${KLIPPER_DIR}/klippy/extras/spi_temperature.py
        grep -q "zmod 1.0" /opt/klipper/start.sh || cp /usr/data/zmod/zmod/.shell/start.sh /opt/klipper/start.sh
    fi
    if [ ${C5PRO} -eq 1 ]; then
        check_link ${KLIPPER_DIR}/klippy/extras/zmod_color.py /usr/data/zmod/zmod/.shell/zmod_color.py
    fi
    if [ ${AD5X} -eq 1 ]; then
        grep -q "zmod 1.12" ${KLIPPER_DIR}/klippy/extras/virtual_sdcard.py || cp /usr/data/zmod/zmod/.shell/virtual_sdcard.py ${KLIPPER_DIR}/klippy/extras/virtual_sdcard.py
        check_link ${KLIPPER_DIR}/klippy/extras/zmod_color.py /usr/data/zmod/zmod/.shell/zmod_color.py
        check_link ${KLIPPER_DIR}/klippy/extras/zmod_tenz.py /usr/data/zmod/zmod/.shell/zmod_tenz.py
        check_link ${KLIPPER_DIR}/klippy/extras/zmod_ifs.py /usr/data/zmod/zmod/.shell/zmod_ifs.py
        check_link ${KLIPPER_DIR}/klippy/extras/zmod_ifs_switch_sensor.py /usr/data/zmod/zmod/.shell/zmod_ifs_switch_sensor.py
        check_link ${KLIPPER_DIR}/klippy/extras/zmod_ifs_motion_sensor.py /usr/data/zmod/zmod/.shell/zmod_ifs_motion_sensor.py
        check_link /opt/config/rw /usr/prog/config/
    fi

    check_link ${KLIPPER_DIR}/klippy/extras/zmod.py /usr/data/zmod/zmod/.shell/zmod.py
    check_link ${KLIPPER_DIR}/klippy/extras/ens160.py /usr/data/zmod/zmod/.shell/ens160.py

    if [ ${AD5M} -eq 1 ]; then
        # Fix possible ordering issue if a callback blocks in button handler#6440
        grep -q receive_time ${KLIPPER_DIR}/klippy/extras/buttons.py || cp /usr/data/zmod/zmod/.shell/buttons.py ${KLIPPER_DIR}/klippy/extras/buttons.py
    fi

    grep -q zmod_1.0 ${KLIPPER_DIR}/klippy/extras/gcode_shell_command.py || cp /usr/data/zmod/zmod/.shell/gcode_shell_command.py ${KLIPPER_DIR}/klippy/extras/gcode_shell_command.py
    if [ -L ${KLIPPER_DIR}/klippy/extras/load_cell_tare.py ] || [ -f ${KLIPPER_DIR}/klippy/extras/load_cell_tare.py ]; then
        rm -f ${KLIPPER_DIR}/klippy/extras/load_cell_tare.py
    fi

    [ "$(tail -c1 ${PRINTER_BASE})" != "" ] && echo >> ${PRINTER_BASE} && NEED_REBOOT=1
    if [ "$(tail -n2 "$PRINTER_BASE" | wc -l)" -lt 2 ] || [ "$(tail -n2 "$PRINTER_BASE" | grep -vc '^$')" -ne 0 ]; then
        echo >> "$PRINTER_BASE"
        NEED_REBOOT=1
    fi

    # Удаление check_md5.cfg
    grep -q '^\[include check_md5.cfg\]' ${PRINTER_CFG} && sed -i '/^\[include check_md5.cfg\]/d' ${PRINTER_CFG} && NEED_REBOOT=1

    # Удаление display_off.cfg если есть mod.cfg
    grep -q '^\[include ./mod/mod.cfg\]' ${PRINTER_CFG} && grep -q '^\[include ./mod/display_off.cfg\]' ${PRINTER_CFG} && sed -i '/^\[include .\/mod\/display_off.cfg\]/d' ${PRINTER_CFG} && NEED_REBOOT=1

    # Удаление 2+ mod_data/user.cfg
    cnt=$(grep '^\[include ./mod_data/user.cfg\]' ${PRINTER_CFG} |wc -l)
    [ "$cnt" -gt 1 ] && sed -i '/^\[include .\/mod_data\/user.cfg\]/d' ${PRINTER_CFG} && NEED_REBOOT=1

    # Удаление 2+ mod_data/plugins.cfg
    cnt=$(grep '^\[include ./mod_data/plugins.cfg\]' ${PRINTER_CFG} |wc -l)
    [ "$cnt" -gt 1 ] && sed -i '/^\[include .\/mod_data\/plugins.cfg\]/d' ${PRINTER_CFG} && NEED_REBOOT=1

    # Удаление 2+ mod.cfg
    cnt=$(grep '^\[include ./mod/mod.cfg\]' ${PRINTER_CFG} |wc -l)
    [ "$cnt" -gt 1 ] && sed -i '/^\[include .\/mod\/mod.cfg\]/d' ${PRINTER_CFG} && NEED_REBOOT=1

    # Удаление 2+ klipper13.cfg
    cnt=$(grep '^\[include ./mod/klipper13.cfg\]' ${PRINTER_CFG} |wc -l)
    [ "$cnt" -gt 1 ] && sed -i '/^\[include .\/mod\/klipper13.cfg\]/d' ${PRINTER_CFG} && NEED_REBOOT=1

    # Удаление 2+ klipper11.cfg
    cnt=$(grep '^\[include ./mod/klipper11.cfg\]' ${PRINTER_CFG} |wc -l)
    [ "$cnt" -gt 1 ] && sed -i '/^\[include .\/mod\/klipper11.cfg\]/d' ${PRINTER_CFG} && NEED_REBOOT=1

    # Добавление mod.cfg
    if ! grep -q '^\[include ./mod/mod.cfg\]' ${PRINTER_CFG} && ! grep -q '^\[include ./mod/display_off.cfg\]' ${PRINTER_CFG}; then
        [ ${C5PRO} -eq 1 ] && sed -i '/^\[include printer\.motor\.cfg\]/a [include ./mod/mod.cfg]' ${PRINTER_CFG} && NEED_REBOOT=1
        [ ${C5PRO} -eq 0 ] && sed -i '2 i\[include ./mod/mod.cfg]' ${PRINTER_CFG} && NEED_REBOOT=1
    fi

    # Замена mod.user.cfg на user.cfg
    grep -q '^\[include mod.user.cfg\]' ${PRINTER_CFG} && sed -i 's|^\[include mod.user.cfg\]|\[include ./mod_data/user.cfg\]|' ${PRINTER_CFG} && NEED_REBOOT=1

    # Добавление user.cfg
    ! grep -q '^\[include \./mod_data/user\.cfg\]' ${PRINTER_CFG} && sed -i '/^\[include \.\/mod\/mod\.cfg\]/a [include ./mod_data/user.cfg]' ${PRINTER_CFG} && NEED_REBOOT=1
    ! grep -q '^\[include \./mod_data/user\.cfg\]' ${PRINTER_CFG} && sed -i '/^\[include \.\/mod\/display_off\.cfg\]/a [include ./mod_data/user.cfg]' ${PRINTER_CFG} && NEED_REBOOT=1

    # Добавление plugins.cfg перед user.cfg
    ! grep -q '^\[include ./mod_data/plugins.cfg\]' ${PRINTER_CFG} && awk 'BEGIN { found_user = 0; inserted = 0; }
/\[include \.\/mod_data\/user\.cfg\]/ {
    if (!inserted) print "[include ./mod_data/plugins.cfg]";
    print $0;
    next;
}
/\[include \.\/mod_data\/plugins\.cfg\]/ {
    inserted = 1;
}
{
    print $0;
}' ${PRINTER_CFG} > ${PRINTER_CFG}.tmp && mv ${PRINTER_CFG}.tmp ${PRINTER_CFG} && NEED_REBOOT=1

    # Заменяем mod.cfg на display_off.cfg и обратно
    if grep -q "display_off = 1" ${MOD_CONF}/mod_data/variables.cfg; then
        grep -q '^\[include ./mod_data/mod.cfg\]' ${PRINTER_CFG} && sed -i 's|\[include ./mod/mod.cfg\]|\[include ./mod/display_off.cfg\]|' ${PRINTER_CFG} && NEED_REBOOT=1
    else
        grep -q '^\[include ./mod/display_off.cfg\]' ${PRINTER_CFG} && sed -i 's|\[include ./mod/display_off.cfg\]|\[include ./mod/mod.cfg\]|' ${PRINTER_CFG} && NEED_REBOOT=1
    fi

    # Перенос heater_bed из printer.base.cfg в printer.cfg
    if ! grep -q '^\[heater_bed' ${PRINTER_CFG}; then
        NEED_REBOOT=1
        cd ${MOD_CONF}

        if grep -q '^\[heater_bed' ${PRINTER_BASE}; then
            sed -e '/^\[heater_bed/,/^\[/d' ${PRINTER_BASE} >printer.base.tmp
            diff -u ${PRINTER_BASE} printer.base.tmp | grep -v "printer.base.cfg" |grep "^-" | cut -b 2- >heater_bed.txt
            sed -i '$d' heater_bed.txt
            num=$(wc -l heater_bed.txt|cut  -d " " -f1)
            num=$(($num-1))
            sed -e "/^\[heater_bed/,+${num}d;" ${PRINTER_BASE} >printer.base.tmp
            cat printer.base.tmp >${PRINTER_BASE}
            rm -f printer.base.tmp
        else
            [ ${AD5M} -eq 1 ] && echo "[heater_bed]
heater_pin: PB9
sensor_type: Generic 3950
sensor_pin: PC3
pullup_resistor: 4700
control: pid
pid_Kp: 32.79
pid_Ki: 4.970
pid_Kd: 54.118
#control: watermark
#max_power: 1.0
min_temp: -100
max_temp: 130

" >heater_bed.txt
            [ ${AD5X} -eq 1 ] && echo "[heater_bed]
heater_pin: PB9
sensor_type: Generic 3950
sensor_pin: PA0
pullup_resistor: 4700
control: pid
pid_Kp: 32.79
pid_Ki: 4.970
pid_Kd: 54.118
#control: watermark
max_power: 0.4
min_temp: -100
max_temp: 130

" >heater_bed.txt
            fi

            num=$(cat -n ${PRINTER_CFG} |grep ./mod_data/user.cfg| awk '{print $1}')
            head -n $num ${PRINTER_CFG} >printer.tmp
            echo "" >>printer.tmp
            cat heater_bed.txt >>printer.tmp
            num=$(($num+1))
            tail -n +$num ${PRINTER_CFG} >>printer.tmp
            cat printer.tmp >${PRINTER_CFG}
            rm heater_bed.txt || echo "Not heater_bed.txt"
    fi

    [ ${C5PRO} -eq 1 ] && grep '/usr/data/gcodes$' ${PRINTER_BASE} && sed -i 's|path: /usr/data/gcodes$|path: /usr/data/gcodes/|' ${PRINTER_BASE} && NEED_REBOOT=1

    if grep -q '^\[heater_bed' ${PRINTER_BASE}; then
        NEED_REBOOT=1
        cd ${MOD_CONF}

        sed -e '/^\[heater_bed/,/^\[/d' ${PRINTER_BASE} >printer.base.tmp
        diff -u ${PRINTER_BASE} printer.base.tmp | grep -v "printer.base.cfg" |grep "^-" | cut -b 2- >heater_bed.txt
        sed -i '$d' heater_bed.txt
        num=$(wc -l heater_bed.txt|cut  -d " " -f1)
        num=$(($num-1))
        sed -e "/^\[heater_bed/,+${num}d;" ${PRINTER_BASE} >printer.base.tmp
        cat printer.base.tmp >${PRINTER_BASE}
        rm -f heater_bed.txt printer.base.tmp
    fi

    # Удаляем temperature_sensor weightValue
    if grep -q '^\[temperature_sensor weightValue' ${PRINTER_BASE}; then
        NEED_REBOOT=1
        cd ${MOD_CONF}

        sed -e '/^\[temperature_sensor weightValue/,/^\[/d' ${PRINTER_BASE} >printer.base.tmp
        diff -u ${PRINTER_BASE} printer.base.tmp | grep -v "printer.base.cfg" |grep "^-" | cut -b 2- >heater_bed.txt
        sed -i '$d' heater_bed.txt
        num=$(wc -l heater_bed.txt|cut  -d " " -f1)
        num=$(($num-1))
        sed -e "/^\[temperature_sensor weightValue/,+${num}d;" ${PRINTER_BASE} >printer.base.tmp
        cat printer.base.tmp >${PRINTER_BASE}
        rm -f heater_bed.txt printer.base.tmp
    fi

    # Удаляем temperature_sensor tvocValue
    if grep -q '^\[temperature_sensor tvocValue' ${PRINTER_BASE}; then
        NEED_REBOOT=1
        cd ${MOD_CONF}

        sed -e '/^\[temperature_sensor tvocValue/,/^\[/d' ${PRINTER_BASE} >printer.base.tmp
        diff -u ${PRINTER_BASE} printer.base.tmp | grep -v "printer.base.cfg" |grep "^-" | cut -b 2- >heater_bed.txt
        sed -i '$d' heater_bed.txt
        num=$(wc -l heater_bed.txt|cut  -d " " -f1)
        num=$(($num-1))
        sed -e "/^\[temperature_sensor tvocValue/,+${num}d;" ${PRINTER_BASE} >printer.base.tmp
        cat printer.base.tmp >${PRINTER_BASE}
        rm -f heater_bed.txt printer.base.tmp
    fi

    # Удаляем fan_generic pcb_fan
    if [ ${C5PRO} -eq 0 ] && grep -q '^\[fan_generic pcb_fan' ${PRINTER_BASE}; then
        NEED_REBOOT=1
        cd ${MOD_CONF}

        sed -e '/^\[fan_generic pcb_fan/,/^\[/d' ${PRINTER_BASE} >printer.base.tmp
        diff -u ${PRINTER_BASE} printer.base.tmp | grep -v "printer.base.cfg" |grep "^-" | cut -b 2- >heater_bed.txt
        sed -i '$d' heater_bed.txt
        num=$(wc -l heater_bed.txt|cut  -d " " -f1)
        num=$(($num-1))
        sed -e "/^\[fan_generic pcb_fan/,+${num}d;" ${PRINTER_BASE} >printer.base.tmp
        cat printer.base.tmp >${PRINTER_BASE}
        rm -f heater_bed.txt printer.base.tmp
    fi

    # Удаляем fan_generic external_fan
    if grep -q '^\[fan_generic external_fan' ${PRINTER_BASE}; then
        NEED_REBOOT=1
        cd ${MOD_CONF}

        sed -e '/^\[fan_generic external_fan/,/^\[/d' ${PRINTER_BASE} >printer.base.tmp
        diff -u ${PRINTER_BASE} printer.base.tmp | grep -v "printer.base.cfg" |grep "^-" | cut -b 2- >heater_bed.txt
        sed -i '$d' heater_bed.txt
        num=$(wc -l heater_bed.txt|cut  -d " " -f1)
        num=$(($num-1))
        sed -e "/^\[fan_generic external_fan/,+${num}d;" ${PRINTER_BASE} >printer.base.tmp
        cat printer.base.tmp >${PRINTER_BASE}
        rm -f heater_bed.txt printer.base.tmp
    fi

    # Удаляем fan_generic internal_fan
    if grep -q '^\[fan_generic internal_fan' ${PRINTER_BASE}; then
        NEED_REBOOT=1
        cd ${MOD_CONF}

        sed -e '/^\[fan_generic internal_fan/,/^\[/d' ${PRINTER_BASE} >printer.base.tmp
        diff -u ${PRINTER_BASE} printer.base.tmp | grep -v "printer.base.cfg" |grep "^-" | cut -b 2- >heater_bed.txt
        sed -i '$d' heater_bed.txt
        num=$(wc -l heater_bed.txt|cut  -d " " -f1)
        num=$(($num-1))
        sed -e "/^\[fan_generic internal_fan/,+${num}d;" ${PRINTER_BASE} >printer.base.tmp
        cat printer.base.tmp >${PRINTER_BASE}
        rm -f heater_bed.txt printer.base.tmp
    fi

    # Удаляем controller_fan pcb_fan
    if [ ${C5PRO} -eq 0 ] && grep -q '^\[controller_fan pcb_fan' ${PRINTER_BASE}; then
        NEED_REBOOT=1
        cd ${MOD_CONF}

        sed -e '/^\[controller_fan pcb_fan/,/^\[/d' ${PRINTER_BASE} >printer.base.tmp
        diff -u ${PRINTER_BASE} printer.base.tmp | grep -v "printer.base.cfg" |grep "^-" | cut -b 2- >heater_bed.txt
        sed -i '$d' heater_bed.txt
        num=$(wc -l heater_bed.txt|cut  -d " " -f1)
        num=$(($num-1))
        sed -e "/^\[controller_fan pcb_fan/,+${num}d;" ${PRINTER_BASE} >printer.base.tmp
        cat printer.base.tmp >${PRINTER_BASE}
        rm -f heater_bed.txt printer.base.tmp
    fi

    if [ ${AD5M} -eq 1 ]; then
        # Возвращаем gcode_button check_level_pin
        if ! grep -q '^\[gcode_button check_level_pin' ${PRINTER_BASE}; then
            NEED_REBOOT=1
            cd ${MOD_CONF}

            echo '
[gcode_button check_level_pin]
pin: !PE0
press_gcode:
    M105
' >>${PRINTER_BASE}
        fi

        # Удаляем filament_switch_sensor e0_sensor
        if grep -q '^\[filament_switch_sensor e0_sensor' ${PRINTER_BASE}; then
            NEED_REBOOT=1
            cd ${MOD_CONF}

            ! grep -q "motion_sensor" ${MOD_CONF}/mod_data/variables.cfg && sed -i '2 i\motion_sensor = 0' ${MOD_CONF}/mod_data/variables.cfg
            #sed -i "s/^motion_sensor.*/motion_sensor = 0/" ${MOD_CONF}/mod_data/variables.cfg

            sed -e '/^\[filament_switch_sensor e0_sensor/,/^\[/d' ${PRINTER_BASE} >printer.base.tmp
            diff -u ${PRINTER_BASE} printer.base.tmp | grep -v "printer.base.cfg" |grep "^-" | cut -b 2- >heater_bed.txt
            sed -i '$d' heater_bed.txt
            num=$(wc -l heater_bed.txt|cut  -d " " -f1)
            num=$(($num-1))
            sed -e "/^\[filament_switch_sensor e0_sensor/,+${num}d;" ${PRINTER_BASE} >printer.base.tmp
            cat printer.base.tmp >${PRINTER_BASE}
            rm -f heater_bed.txt printer.base.tmp
        fi

        # Удаляем filament_motion_sensor e0_sensor
        if grep -q '^\[filament_motion_sensor e0_sensor' ${PRINTER_BASE}; then
            NEED_REBOOT=1
            cd ${MOD_CONF}

            ! grep -q "motion_sensor" ${MOD_CONF}/mod_data/variables.cfg && sed -i '2 i\motion_sensor = 1' ${MOD_CONF}/mod_data/variables.cfg
            sed -i "s/^motion_sensor.*/motion_sensor = 1/" ${MOD_CONF}/mod_data/variables.cfg

            sed -e '/^\[filament_motion_sensor e0_sensor/,/^\[/d' ${PRINTER_BASE} >printer.base.tmp
            diff -u ${PRINTER_BASE} printer.base.tmp | grep -v "printer.base.cfg" |grep "^-" | cut -b 2- >heater_bed.txt
            sed -i '$d' heater_bed.txt
            num=$(wc -l heater_bed.txt|cut  -d " " -f1)
            num=$(($num-1))
            sed -e "/^\[filament_motion_sensor e0_sensor/,+${num}d;" ${PRINTER_BASE} >printer.base.tmp
            cat printer.base.tmp >${PRINTER_BASE}
            rm -f heater_bed.txt printer.base.tmp
        fi
    fi

    # Добавляем controller_fan driver_fan
    if [ ${AD5X} -eq 1 ]; then PIN="PA5"; fi
    if [ ${AD5M} -eq 1 ]; then PIN="PB7"; fi
    if [ ${C5PRO} -eq 0 ] && grep -q '^\[controller_fan driver_fan' ${PRINTER_BASE}; then
        if ! grep -A1 '^\[controller_fan driver_fan' ${PRINTER_BASE} | grep -q "pin:${PIN}"; then
            # Удаляем controller_fan driver_fan
            cd ${MOD_CONF}
            sed -e '/^\[controller_fan driver_fan/,/^\[/d' ${PRINTER_BASE} >printer.base.tmp
            diff -u printer.base.cfg printer.base.tmp | grep -v "printer.base.cfg" |grep "^-" | cut -b 2- >heater_bed.txt
            sed -i '$d' heater_bed.txt
            num=$(wc -l heater_bed.txt|cut  -d " " -f1)
            num=$(($num-1))
            sed -e "/^\[controller_fan driver_fan/,+${num}d;" ${PRINTER_BASE} >printer.base.tmp
            cat printer.base.tmp >${PRINTER_BASE}
            rm -f heater_bed.txt printer.base.tmp
        fi
    fi
    if [ ${C5PRO} -eq 0 ] && ! grep -q '^\[controller_fan driver_fan' ${PRINTER_BASE}; then
        NEED_REBOOT=1
        cd ${MOD_CONF}

        echo "
[controller_fan driver_fan]
pin:${PIN}
fan_speed: 1.0
idle_timeout: 30
stepper: stepper_x, stepper_y, stepper_z
" >>${PRINTER_BASE}
    fi

    # klipper13 FIX
    if grep -q "klipper13 = 1" ${MOD_CONF}/mod_data/variables.cfg || [ ${C5PRO} -eq 1 ]|| [ ${AD5X} -eq 1 ]; then
        if grep -q '^max_accel_to_decel' ${PRINTER_BASE}; then
            NEED_REBOOT=1
            sed -i 's|^max_accel_to_decel.*|minimum_cruise_ratio: 0.5|' ${PRINTER_BASE}
        fi
    else
        if grep -q '^minimum_cruise_ratio' ${PRINTER_BASE}; then
            NEED_REBOOT=1
            sed -i 's|^minimum_cruise_ratio.*|max_accel_to_decel:5000|' ${PRINTER_BASE}
        fi
    fi

    if grep -q "klipper13 = 1" ${MOD_CONF}/mod_data/variables.cfg; then
        if ! grep -q '^\[include ./mod/klipper13.cfg\]' ${PRINTER_CFG}; then
            NEED_REBOOT=1
            [ ${C5PRO} -eq 0 ] && sed -i '/\[include printer\.base\.cfg\]/a [include ./mod/klipper13.cfg]' ${PRINTER_CFG}
            [ ${C5PRO} -eq 1 ] && sed -i '/\[include printer\.motor\.cfg\]/a [include ./mod/klipper13.cfg]' ${PRINTER_CFG}
        fi
    else
        if grep -q '^\[include ./mod/klipper13.cfg\]' ${PRINTER_CFG}; then
            NEED_REBOOT=1
            sed -i '/^\[include \.\/mod\/klipper13\.cfg\]$/d' ${PRINTER_CFG}
        fi
    fi

    if [ ${AD5M} -eq 1 ]; then
        if ! { head -n 2 ${PRINTER_CFG} | tail -n 1 | grep -qE '^\[include \.\/mod\/klipper1[13]\.cfg\]$'; }; then
            sed -i '\|\[include \./mod/klipper11\.cfg\]|d' "${PRINTER_CFG}"
            sed -i '\|\[include \./mod/klipper13\.cfg\]|d' "${PRINTER_CFG}"
            NEED_REBOOT=1
        fi
        if grep -q "klipper13 = 1" ${MOD_CONF}/mod_data/variables.cfg; then
            grep -q '^\[include ./mod/klipper11.cfg\]' ${PRINTER_CFG} && sed -i '/^\[include \.\/mod\/klipper11\.cfg\]$/d' ${PRINTER_CFG} && NEED_REBOOT=1
        else
            grep -q '^\[include ./mod/klipper11.cfg\]' ${PRINTER_CFG} || sed -i '/\[include printer\.base\.cfg\]/a [include ./mod/klipper11.cfg]' ${PRINTER_CFG} && NEED_REBOOT=1
        fi

        ! grep -q "motion_sensor" ${MOD_CONF}/mod_data/variables.cfg && sed -i '2 i\motion_sensor = 0' ${MOD_CONF}/mod_data/variables.cfg

        # Режим с экраном
        if grep -q '^\[include ./mod/mod.cfg\]' ${PRINTER_CFG}; then
            grep -q '^\[include ./mod/switch_sensor_display_off.cfg\]' ${PRINTER_CFG} && sed -i '/^\[include .\/mod\/switch_sensor_display_off.cfg\]/d' ${PRINTER_CFG} && NEED_REBOOT=1
            if grep -q "motion_sensor = 1" ${MOD_CONF}/mod_data/variables.cfg; then
                ! grep -q '^\[include ./mod/motion_sensor.cfg\]'       ${PRINTER_CFG} && sed -i '/^\[include \.\/mod\/mod\.cfg\]/a [include ./mod/motion_sensor.cfg]' ${PRINTER_CFG} && NEED_REBOOT=1
                  grep -q '^\[include ./mod/switch_sensor.cfg\]'       ${PRINTER_CFG} && sed -i '/^\[include .\/mod\/switch_sensor.cfg\]/d' ${PRINTER_CFG} && NEED_REBOOT=1
            else
                ! grep -q '^\[include ./mod/switch_sensor.cfg\]'       ${PRINTER_CFG} && sed -i '/^\[include \.\/mod\/mod\.cfg\]/a [include ./mod/switch_sensor.cfg]' ${PRINTER_CFG} && NEED_REBOOT=1
                  grep -q '^\[include ./mod/motion_sensor.cfg\]'       ${PRINTER_CFG} && sed -i '/^\[include .\/mod\/motion_sensor.cfg\]/d' ${PRINTER_CFG} && NEED_REBOOT=1
            fi
        fi

        # Режим без экрана
        if grep -q '^\[include ./mod/display_off.cfg\]' ${PRINTER_CFG}; then
            grep -q '^\[include ./mod/switch_sensor.cfg\]'                   ${PRINTER_CFG} && sed -i '/^\[include .\/mod\/switch_sensor.cfg\]/d' ${PRINTER_CFG} && NEED_REBOOT=1
            if grep -q "motion_sensor = 1" ${MOD_CONF}/mod_data/variables.cfg; then
                ! grep -q '^\[include ./mod/motion_sensor.cfg\]' ${PRINTER_CFG} && sed -i '/^\[include \.\/mod\/display_off\.cfg\]/a [include ./mod/motion_sensor.cfg]' ${PRINTER_CFG} && NEED_REBOOT=1
                  grep -q '^\[include ./mod/switch_sensor_display_off.cfg\]' ${PRINTER_CFG} && sed -i '/^\[include .\/mod\/switch_sensor_display_off.cfg\]/d' ${PRINTER_CFG} && NEED_REBOOT=1
            else
                ! grep -q '^\[include ./mod/switch_sensor_display_off.cfg\]' ${PRINTER_CFG} && sed -i '/^\[include \.\/mod\/display_off\.cfg\]/a [include ./mod/switch_sensor_display_off.cfg]' ${PRINTER_CFG} && NEED_REBOOT=1
                  grep -q '^\[include ./mod/motion_sensor.cfg\]'             ${PRINTER_CFG} && sed -i '/^\[include .\/mod\/motion_sensor.cfg\]/d' ${PRINTER_CFG} && NEED_REBOOT=1
            fi
        fi
    fi

    [ "$(tail -c1 ${PRINTER_BASE})" != "" ] && echo >> ${PRINTER_BASE} && NEED_REBOOT=1
    if [ "$(tail -n2 "$PRINTER_BASE" | wc -l)" -lt 2 ] || [ "$(tail -n2 "$PRINTER_BASE" | grep -vc '^$')" -ne 0 ]; then
        echo >> "$PRINTER_BASE"
        NEED_REBOOT=1
    fi
    awk 'NF {last = NR} {lines[NR] = $0} END {for (i=1; i<=last; i++) print lines[i]}' ${PRINTER_CFG} >${PRINTER_CFG}.save
    if ! diff ${PRINTER_CFG} ${PRINTER_CFG}.save; then
        mv ${PRINTER_CFG}.save ${PRINTER_CFG}
        NEED_REBOOT=1
    else
        rm ${PRINTER_CFG}.save
    fi

    if [ -f ${MOD_CONF}/mod_data/mesh_data.cfg ]; then
        FIND_STR=$(cat ${MOD_CONF}/mod_data/mesh_data.cfg |grep bed_mesh|sed 's/\[/\\[/g; s/\]/\\]/g')
        if ! grep "$FIND_STR" ${PRINTER_CFG}; then
            NEED_REBOOT=1
            cat ${MOD_CONF}/mod_data/mesh_data.cfg >>${PRINTER_CFG}
        fi
        rm -f ${MOD_CONF}/mod_data/mesh_data.cfg
    fi

    if grep -q "update_manager zmod" ${MOD_CONF}/mod_data/user.moonraker.conf; then
        awk '
          /^\[update_manager zmod\]$/ { in_section = 1; next }
          /^\[/ && in_section { in_section = 0 }
          !in_section
        ' ${MOD_CONF}/mod_data/user.moonraker.conf > ${MOD_CONF}/mod_data/user.moonraker.conf.tmp && \
        mv ${MOD_CONF}/mod_data/user.moonraker.conf.tmp ${MOD_CONF}/mod_data/user.moonraker.conf
    fi

    if [ ${NEED_REBOOT} -eq 1 ]; then
        if [ ${AD5M} -eq 1 ]; then
            echo "Kill firmwareExe"
            sync
            killall firmwareExe
            sync
        fi
        sync
        diff -u ${PRINTER_BASE_ORIG} ${PRINTER_BASE}
        diff -u ${PRINTER_CFG_ORIG} ${PRINTER_CFG}
        cat ${PRINTER_BASE} >${PRINTER_BASE_ORIG}
        sync
        cat ${PRINTER_CFG} >${PRINTER_CFG_ORIG}
        sync
    else
        diff -u ${PRINTER_BASE_ORIG} ${PRINTER_BASE}
        diff -u ${PRINTER_CFG_ORIG} ${PRINTER_CFG}
    fi

    if [ ${AD5X} -eq 1 ] || [ ${C5PRO} -eq 1 ]; then enable_zmod_ad5x_c5pro; fi

    echo "END fix_config"

    if [ "$1" == "start" ] && [ ${AD5M} -eq 1 ]; then
        /usr/data/zmod/zmod/.shell/app_startup_mcu.sh
    fi
    sync
}

mkdir -p ${MOD_CONF}/mod_data/log/

mv ${MOD_CONF}/mod_data/log/fix_config.4.log ${MOD_CONF}/mod_data/log/fix_config.5.log 2>/dev/null
mv ${MOD_CONF}/mod_data/log/fix_config.3.log ${MOD_CONF}/mod_data/log/fix_config.4.log 2>/dev/null
mv ${MOD_CONF}/mod_data/log/fix_config.2.log ${MOD_CONF}/mod_data/log/fix_config.3.log 2>/dev/null
mv ${MOD_CONF}/mod_data/log/fix_config.1.log ${MOD_CONF}/mod_data/log/fix_config.2.log 2>/dev/null
mv ${MOD_CONF}/mod_data/log/fix_config.log   ${MOD_CONF}/mod_data/log/fix_config.1.log 2>/dev/null

if [ -f ${MOD_CONF}/mod/SKIP_ZMOD ] || [ -f ${MOD_CONF}/mod/REMOVE ] || [ -f ${MOD_CONF}/mod/FULL_REMOVE ]; then
    restore_base &>${MOD_CONF}/mod_data/log/fix_config.log
else
    fix_config "$1" &>${MOD_CONF}/mod_data/log/fix_config.log
    /usr/data/zmod/zmod/.shell/wifi.sh &
fi

sync

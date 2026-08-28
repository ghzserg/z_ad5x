#!/bin/sh
# (C) 2024-2026 ghzserg https://github.com/ghzserg/zmod

source /usr/data/zmod/zmod/.shell/0.sh

set -x


start_moonraker() {
    /usr/data/zmod/zmod/.shell/root/S65moonraker start
    /usr/data/zmod/zmod/.shell/root/S70httpd start
}

start_klipper() {
    if [ ${AD5M} -eq 1 ]; then
        if grep -q "klipper13 = 1" /opt/config/mod_data/variables.cfg; then
            /usr/data/zmod/zmod/.shell/root/S60klipper start
        fi
    fi
}

get_origin_from_config() {
  local config_file="$1"
  local section="[update_manager $2]"

  awk -v section="$section" '
    BEGIN { in_section = 0 }
    /^\[.*\]$/ {
      if ($0 == section) {
        in_section = 1
      } else if (in_section) {
        exit
      }
      next
    }
    in_section && /^origin[[:space:]]*:/ {
      gsub(/^[[:space:]]*origin[[:space:]]*:[[:space:]]*/, "")
      gsub(/[[:space:]]+$/, "")
      print
      exit
    }
  ' "$config_file"
}

get_branch_from_config() {
  local config_file="$1"
  local section_name="$2"
  local section="[update_manager $section_name]"

  awk -v section="$section" '
    BEGIN { in_section = 0 }
    /^\[.*\]$/ {
      if ($0 == section) {
        in_section = 1
      } else if (in_section) {
        exit
      }
      next
    }
    in_section && (/^primary_branch[[:space:]]*:/ || /^branch[[:space:]]*:/) {
      sub(/^[^:]*:[[:space:]]*/, "")
      gsub(/[[:space:]]+$/, "")
      print
      exit
    }
  ' "$config_file"
}

update_plugins() {
    grep '/root/printer_data/config/mod_data/plugins/' "$1" | sed 's|/$||' | sed 's|.*/||' | \
    while read a; do
        echo "Plugin $a"
        if ! [ -f "${MOD_CONF}/mod_data/plugins/$a/.git/config" ]; then
            url=$(get_origin_from_config "$1" "$a")
            branch=$(get_branch_from_config "$1" "$a")
            if [ "$url" != "" ] && [ "$branch" != "" ]; then
                echo "Инициализирую репозиторий"
                mkdir -p "${MOD_CONF}/mod_data/plugins/$a/"
                sqlite3 /opt/config/mod_data/database/moonraker-sql.db \
                "DELETE FROM namespace_store WHERE namespace = 'update_manager' AND key = '$a'; \
                 INSERT INTO namespace_store (namespace, key, value) VALUES ('update_manager', '$a', '{\"last_config_hash\":\"?\",\"last_refresh_time\":0.0,\"is_valid\":false,\"pip_version_info\":null,\"repo_valid\":false,\"git_owner\":\"none\",\"git_repo_name\":\"$a\",\"git_remote\":\"origin\",\"git_branch\":\"$branch\",\"current_version\":\"0.0.0.0\",\"upstream_version\":\"0.0.0.0\",\"current_commit\":\"?\",\"upstream_commit\":\"?\",\"rollback_commit\":\"?\",\"rollback_branch\":\"$branch\",\"rollback_version\":\"0.0.0.0\",\"upstream_url\":\"$url\",\"recovery_url\":\"$url\",\"branches\":[\"$branch\"],\"head_detached\":false,\"git_messages\":[],\"commits_behind\":[],\"cbh_count\":0,\"diverged\":false,\"corrupt\":true,\"modified_files\":[],\"untracked_files\":[],\"pinned_commit_valid\":true}');"
            else
                echo "Не найден url=$url или branch=$branh для $a. Пропускаю."
            fi
        else
            echo "Репозиторий $a уже  существует, пропускаю."
        fi
    done
}


check_link()
{
    a=$(readlink "$1" 2>/dev/null)
    if [ "$a" != "$2" ]; then
        /bin/echo -n "$1 - Incorrect link ($a!=$2): "
        rm -f "$1" 2>/dev/null
        ln -s "$2" "$1" 2>/dev/null && echo "Исправлено"  || echo "Ошибка исправления"
    fi
}

prepare_chroot()
{
    echo ZMOD >/ZMOD
    [ ${AD5M} -eq 1 ] && mv /tmp/localtime /etc/localtime

    if [ ${AD5X} -eq 1 ]; then
        [ -f /opt/config/mod_data/filament.json ] || echo "{}" >/opt/config/mod_data/filament.json
    fi

    mv /tmp/pointercal /etc/pointercal
    mv /tmp/ts.conf /etc/ts.conf

    [ -d /root/guppyscreen ] || mkdir -p /root/guppyscreen
    rm -f /root/guppyscreen/guppyscreen
    cp /usr/data/zmod/zmod/.shell/root/guppyscreen /root/guppyscreen/guppyscreen

    [ -d /var/run/ ] || mkdir -p /var/run/

    rmdir /opt/config/base 2>/dev/null

    [ -d /etc/init.d/ ] || mkdir -p /etc/init.d/

    check_link /etc/init.d/S98zssh /usr/data/zmod/zmod/.shell/S98zssh
    [ -L /etc/init.d/S98camera ] && rm -f /etc/init.d/S98camera
    check_link /etc/init.d/S99camera /usr/data/zmod/zmod/.shell/root/S99camera
    check_link /etc/init.d/S60klipper /usr/data/zmod/zmod/.shell/root/S60klipper

    [ -d /srv/helixscreen/ ] || mkdir -p /srv/helixscreen/
    if ! [ -f /srv/helixscreen/release_info.json ]; then
        if [ ${AD5M} -eq 1 ]; then
            echo '{"project_name":"helixscreen","project_owner":"prestonbrown","version":"v0.0.1","asset_name":"helixscreen-ad5m.zip"}' >/srv/helixscreen/release_info.json
        fi
        if [ ${AD5X} -eq 1 ]; then
            echo '{"project_name":"helixscreen","project_owner":"prestonbrown","version":"v0.0.1","asset_name":"helixscreen-ad5x.zip"}' >/srv/helixscreen/release_info.json
        fi
    else
        sed -i 's/ghzserg/prestonbrown/' /srv/helixscreen/release_info.json
    fi

    [ ${AD5M} -eq 1 ] && check_link /root/klipper-env/klippy /usr/data/zmod/klipper/klippy
    if [ -f /usr/data/zmod/klipper/klippy/klippy.py ]; then
        check_link /usr/data/zmod/klipper/klippy/extras/gcode_shell_command.py /usr/data/zmod/zmod/.shell/gcode_shell_command.py
        check_link /usr/data/zmod/klipper/klippy/extras/zmod.py /usr/data/zmod/zmod/.shell/zmod.py
        check_link /usr/data/zmod/klipper/klippy/extras/ens160.py /usr/data/zmod/zmod/.shell/ens160.py

        if [ ${AD5M} -eq 1 ]; then
            check_link /usr/data/zmod/klipper/klippy/chelper/c_helper.so /usr/data/zmod/klipper/mcu/ff5m/c_helper.so
            check_link /usr/data/zmod/klipper/klippy/extras/ens160.py /usr/data/zmod/zmod/.shell/ens160.py
            #check_link /usr/data/zmod/klipper/klippy/extras/flashforge_loadcell.py /usr/data/zmod/zmod/.shell/flashforge_loadcell.py
            [ -L /usr/data/zmod/klipper/klippy/extras/flashforge_loadcell.py ] && rm -f /usr/data/zmod/klipper/klippy/extras/flashforge_loadcell.py
        fi
        if [ ${AD5X} -eq 1 ]; then
            check_link /usr/data/zmod/klipper/klippy/chelper/c_helper.so /usr/data/zmod/klipper/mcu/ad5x/c_helper.so
            check_link /usr/data/zmod/klipper/klippy/extras/zmod_color.py /usr/data/zmod/zmod/.shell/zmod_color.py
            check_link /usr/data/zmod/klipper/klippy/extras/zmod_ifs_motion_sensor.py /usr/data/zmod/zmod/.shell/zmod_ifs_motion_sensor.py
            check_link /usr/data/zmod/klipper/klippy/extras/zmod_ifs_switch_sensor.py /usr/data/zmod/zmod/.shell/zmod_ifs_switch_sensor.py
            check_link /usr/data/zmod/klipper/klippy/extras/zmod_ifs.py /usr/data/zmod/zmod/.shell/zmod_ifs.py
            check_link /usr/data/zmod/klipper/klippy/extras/zmod_tenz.py /usr/data/zmod/zmod/.shell/zmod_tenz.py
            if [ -f /usr/data/zmod/klipper/klippy/extras/aio_executor.py ]; then
                check_link /usr/data/zmod/klipper/klippy/extras/virtual_sdcard.py /usr/data/zmod/zmod/.shell/virtual_sdcard_13.py
            else
                check_link /usr/data/zmod/klipper/klippy/extras/virtual_sdcard.py /usr/data/zmod/zmod/.shell/virtual_sdcard.py
            fi
        fi
    fi

    check_link /root/moonraker-env/moonraker /usr/data/zmod/moonraker
    check_link /etc/init.d/S80helixscreen /usr/data/zmod/zmod/.shell/root/S80helixscreen
    check_link /etc/init.d/S80guppyscreen /usr/data/zmod/zmod/.shell/root/S80guppyscreen
    check_link /etc/init.d/S65moonraker /usr/data/zmod/zmod/.shell/root/S65moonraker
    check_link /etc/init.d/S70httpd /usr/data/zmod/zmod/.shell/root/S70httpd

    [ -L /etc/init.d/S35tslib ] && rm -f /etc/init.d/S35tslib

    [ -L /usr/lib/python3.12/site-packages/mido ] || ln -s /usr/data/zmod/zmod/.shell/root/mido/ /usr/lib/python3.12/site-packages/
    [ -L /usr/lib/python3.12/site-packages/mido-1.3.3.dist-info ] || ln -s /usr/data/zmod/zmod/.shell/root/mido-1.3.3.dist-info/ /usr/lib/python3.12/site-packages/
    if [ ${AD5M} -eq 1 ]; then
        [ -L /root/klipper-env/lib/python3.12/site-packages/numpy ] || ln -s /usr/lib/python3.12/site-packages/numpy /root/klipper-env/lib/python3.12/site-packages/
    fi

    if ! [ -L /bin/sudo ]; then
        rm -f /bin/sudo
        ln -s /usr/data/zmod/zmod/.shell/root/sudo /bin/sudo
    fi

    if ! [ -L /bin/systemctl ]; then
        rm -f /bin/systemctl
        ln -s /usr/data/zmod/zmod/.shell/root/sudo /bin/systemctl
    fi

    check_link /usr/bin/audio /usr/data/zmod/zmod/.shell/root/audio/audio
    check_link /usr/bin/audio_midi.sh /usr/data/zmod/zmod/.shell/root/audio/audio_midi.sh
    check_link /usr/bin/audio.py /usr/data/zmod/zmod/.shell/root/audio/audio.py

    CUR_DIR=$(pwd)
        cd /usr/data/zmod/zmod/.shell/midi/
        for i in *.mid; do
            [ -f "/opt/config/mod_data/midi/$i" ] || cp "/usr/data/zmod/zmod/.shell/midi/$i" /opt/config/mod_data/midi/
        done
    cd ${CUR_DIR}

    if [ -f /opt/config/mod_data/plugins/g28_tenz/update.sh ] && ! [ -f /opt/config/mod_data/plugins/g28_tenz/zstop.cfg ]; then
        cd /opt/config/mod_data/plugins/g28_tenz/
        ./update.sh
        cd ${CUR_DIR}
    fi

    #[ -L /bin/boot_eboard_mcu ] || ln -s /usr/data/zmod/zmod/.shell/root/mcu/boot_eboard_mcu /bin/boot_eboard_mcu
    check_link /bin/backlight /usr/data/zmod/zmod/.shell/root/backlight

    # fix ssh keys
    mkdir -p /root/.ssh/ /.ssh/
    grep -q "zmod.link ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIJSFHaPS7Ms0PPIEE+E7T0eOZcCP4HZtUv7JJmCDDd9l" /root/.ssh/known_hosts || echo "zmod.link ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIJSFHaPS7Ms0PPIEE+E7T0eOZcCP4HZtUv7JJmCDDd9l" >>/root/.ssh/known_hosts
    grep -q "zmod.link ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIJSFHaPS7Ms0PPIEE+E7T0eOZcCP4HZtUv7JJmCDDd9l" /.ssh/known_hosts || echo "zmod.link ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIJSFHaPS7Ms0PPIEE+E7T0eOZcCP4HZtUv7JJmCDDd9l" >>/.ssh/known_hosts

    rm -rf /root/moonraker-env/lib/python3.12/site-packages/uvloop*  || echo "uvloop уже убит"
    if [ ${AD5M} -eq 1 ]; then
        rm -rf /root/moonraker-env/lib/python3.12/site-packages/msgspec* || echo "msgspec уже убит"
    fi
    if [ ${AD5X} -eq 1 ]; then
        sed -i '/127.0.0.1 /d' /.ssh/known_hosts
        sed -i '/127.0.0.1 /d' /root/.ssh/known_hosts
    fi

    if ! [ -f /root/printer_data/moonraker.secrets ]; then
        if [ -f /opt/config/mod_data/notify.txt ]; then
            cp /opt/config/mod_data/notify.txt /root/printer_data/moonraker.secrets
        else
            echo "[notify]
url: tgram://{bottoken}/{ChatID}
name: {printer_name}
" >/root/printer_data/moonraker.secrets
        fi
    fi
}

/usr/data/zmod/zmod/.shell/znice.sh

if [ ${AD5M} -eq 1 ]; then
    SWAP="$1"
    echo "SWAP=$SWAP"

    if [ "$SWAP" == "/root/swap" ] && ! grep -q "use_swap = 0" /opt/config/mod_data/variables.cfg; then
        if ! swapon $SWAP; then
            dd if=/dev/zero of=$SWAP bs=1024 count=131072
            mkswap $SWAP
            swapon $SWAP || echo "SWAP не включен!"
        fi
    fi
fi

prepare_chroot

if grep -q display_off.cfg /opt/config/printer.cfg && grep -q "save_restore = 1" /opt/config/mod_data/variables.cfg; then
    /usr/data/zmod/zmod/.shell/root/console_log --save --${ZLANG}
else
    /usr/data/zmod/zmod/.shell/root/console_log --not-save --${ZLANG}
fi

rm -f /root/guppyscreen/guppyconfig.json
ln -s /opt/config/mod_data/guppyconfig.json /root/guppyscreen/guppyconfig.json
[ -s /opt/config/mod_data/guppyconfig.json ] || rm -f /opt/config/mod_data/guppyconfig.json

if [ "$3" == "Adventurer5M" ]; then
    [ -f /opt/config/mod_data/guppyconfig.json ] || cp /usr/data/zmod/zmod/guppyconfig_${ZLANG}.json /opt/config/mod_data/guppyconfig.json
else if [ "$3" == "Adventurer5MPro" ]; then
    [ -f /opt/config/mod_data/guppyconfig.json ] || cp /usr/data/zmod/zmod/guppyconfig_${ZLANG}_pro.json /opt/config/mod_data/guppyconfig.json
else if [ "$3" == "AD5X" ]; then
    [ -f /opt/config/mod_data/guppyconfig.json ] || cp /usr/data/zmod/zmod/guppyconfig_${ZLANG}_5x.json /opt/config/mod_data/guppyconfig.json
fi
fi
fi

VER="$3 $2"
grep -q VERSION_CODENAME /etc/os-release || echo "VERSION_CODENAME=\"${VER}\"" >>/etc/os-release
grep -q "VERSION_CODENAME=\"${VER}\"" /etc/os-release || sed -i "s|VERSION_CODENAME=.*|VERSION_CODENAME=\"${VER}\"|" /etc/os-release

V1=$(cat /etc/os-release|grep PRETTY_NAME| cut  -d '"' -f2| awk '{print $1" "$2}')
V2=$(cat ${VER_FULL})

grep -q PRETTY_NAME /etc/os-release || echo "VERSION_CODENAME=\"${V1} -> ${V2}\"" >>/etc/os-release
grep -q "PRETTY_NAME=\"${V1} -> ${V2}\"" /etc/os-release || sed -i "s|PRETTY_NAME=.*|PRETTY_NAME=\"${V1} -> ${V2}\"|" /etc/os-release

mkdir -p ${DATA_GCODES}/tmp

KLIPPER=0
if [ -f /usr/data/zmod/klipper/klippy/klippy.py ]; then
    start_klipper
    KLIPPER=1
fi

# Очищаем данные о старых обновлениях
sqlite3 /opt/config/mod_data/database/moonraker-sql.db "DELETE FROM namespace_store WHERE namespace = 'update_manager';"

# Создаем каталоги под плагины
update_plugins /opt/config/moonraker.conf
grep -q "extra_plugins.moonraker.conf" ${MOD_CONF}/mod_data/extra_plugins.moonraker.conf && update_plugins /usr/data/zmod/zmod/extra_plugins.moonraker.conf
update_plugins /opt/config/mod_data/user.moonraker.conf

if ! [ -f /usr/data/zmod/klipper/klippy/klippy.py ]; then
    branch="main"
    url="https://github.com/ghzserg/zmod_klipper.git"
    a="klippy"
    sqlite3 /opt/config/mod_data/database/moonraker-sql.db \
    "DELETE FROM namespace_store WHERE namespace = 'update_manager' AND key = '$a'; \
     INSERT INTO namespace_store (namespace, key, value) VALUES ('update_manager', '$a', '{\"last_config_hash\":\"?\",\"last_refresh_time\":0.0,\"is_valid\":false,\"pip_version_info\":null,\"repo_valid\":false,\"git_owner\":\"none\",\"git_repo_name\":\"$a\",\"git_remote\":\"origin\",\"git_branch\":\"$branch\",\"current_version\":\"0.0.0.0\",\"upstream_version\":\"0.0.0.0\",\"current_commit\":\"?\",\"upstream_commit\":\"?\",\"rollback_commit\":\"?\",\"rollback_branch\":\"$branch\",\"rollback_version\":\"0.0.0.0\",\"upstream_url\":\"$url\",\"recovery_url\":\"$url\",\"branches\":[\"$branch\"],\"head_detached\":false,\"git_messages\":[],\"commits_behind\":[],\"cbh_count\":0,\"diverged\":false,\"corrupt\":true,\"modified_files\":[],\"untracked_files\":[],\"pinned_commit_valid\":true}');"
else
    CUR_DIR=$(pwd)
    cd /usr/data/zmod/klipper
    if [ ${AD5X} -eq 1 ]; then
        git update-index --skip-worktree klippy/extras/virtual_sdcard.py
    else
        git update-index --no-skip-worktree klippy/extras/virtual_sdcard.py
    fi
    cd ${CUR_DIR}
fi

if ! [ -f /usr/data/zmod/moonraker/moonraker.py ]; then
    branch="main"
    url="https://github.com/ghzserg/zmod_moonraker.git"
    a="moon"
    sqlite3 /opt/config/mod_data/database/moonraker-sql.db \
    "DELETE FROM namespace_store WHERE namespace = 'update_manager' AND key = '$a'; \
     INSERT INTO namespace_store (namespace, key, value) VALUES ('update_manager', '$a', '{\"last_config_hash\":\"?\",\"last_refresh_time\":0.0,\"is_valid\":false,\"pip_version_info\":null,\"repo_valid\":false,\"git_owner\":\"none\",\"git_repo_name\":\"$a\",\"git_remote\":\"origin\",\"git_branch\":\"$branch\",\"current_version\":\"0.0.0.0\",\"upstream_version\":\"0.0.0.0\",\"current_commit\":\"?\",\"upstream_commit\":\"?\",\"rollback_commit\":\"?\",\"rollback_branch\":\"$branch\",\"rollback_version\":\"0.0.0.0\",\"upstream_url\":\"$url\",\"recovery_url\":\"$url\",\"branches\":[\"$branch\"],\"head_detached\":false,\"git_messages\":[],\"commits_behind\":[],\"cbh_count\":0,\"diverged\":false,\"corrupt\":true,\"modified_files\":[],\"untracked_files\":[],\"pinned_commit_valid\":true}');"
fi

if grep -q mainsail-crew /root/mainsail/release_info.json; then
    echo '{"project_name":"mainsail","project_owner":"ghzserg","version":"v1.0.0"}' >/root/mainsail/release_info.json
    sqlite3 /opt/config/mod_data/database/moonraker-sql.db "DELETE FROM namespace_store WHERE namespace = 'update_manager' AND key = 'mainsail';"
fi

if grep -q fluidd-core /root/fluidd/release_info.json; then
    echo '{"project_name":"fluidd","project_owner":"ghzserg","version":"v1.0.0"}' >/root/fluidd/release_info.json
    sqlite3 /opt/config/mod_data/database/moonraker-sql.db "DELETE FROM namespace_store WHERE namespace = 'update_manager' AND key = 'fluidd';"
fi

# Rem tmp TIMELapse
[ -d /root/printer_data/gcodes/timelapse/tmp ] && rm -rf /root/printer_data/gcodes/timelapse/tmp/*

MOONRAKER=0
if [ -f /usr/data/zmod/moonraker/moonraker.py ]; then
    start_moonraker
    MOONRAKER=1
fi

date -s "2026-01-01 00:00:00"

# Пробуем синхронизировать время
ntpd -dd -n -q -p pool.ntp.org || \
ntpd -dd -n -q -p ru.pool.ntp.org || \
ntpd -dd -n -q -p ntp1.vniiftri.ru || \
ntpd -dd -n -q -p ntp2.vniiftri.ru || \
ntpd -dd -n -q -p ntp3.vniiftri.ru || \
ntpd -dd -n -q -p ntp4.vniiftri.ru || \
ntpd -dd -n -q -p ntp5.vniiftri.ru || \
ntpd -dd -n -q -p ntp.sstf.nsk.ru || \
ntpd -dd -n -q -p timesstf.sstf.nsk.ru || \
ntpd -dd -n -q -p ntp.kam.vniiftri.net

test_file()
{
    DIR="/opt/config/mod_data/save"
    DT=$(date '+%Y%m%d_%H%M')

    mkdir -p $DIR

    if ! [ -f "$DIR/$1" ] || ! diff -q /opt/config/$1 "$DIR/$1"; then
        cp /opt/config/$1 "$DIR/$1"
        cp /opt/config/$1 "$DIR/$1.$DT.cfg"
    fi
}

test_file printer.base.cfg
test_file printer.cfg

sleep 15
cd /usr/data/zmod/zmod/
git log | head -3|grep Date >/opt/config/mod_data/date.txt
echo "ZSSH_RELOAD" >/tmp/printer

# 10 минут пробуем получить время
for i in `seq 0 50`; do 
    ntpd -dd -n -q -p pool.ntp.org && break
    ntpd -dd -n -q -p ru.pool.ntp.org && break
    ntpd -dd -n -q -p ntp1.vniiftri.ru && break
    ntpd -dd -n -q -p ntp2.vniiftri.ru && break
    ntpd -dd -n -q -p ntp3.vniiftri.ru && break
    ntpd -dd -n -q -p ntp4.vniiftri.ru && break
    ntpd -dd -n -q -p ntp5.vniiftri.ru && break
    ntpd -dd -n -q -p ntp.sstf.nsk.ru && break
    ntpd -dd -n -q -p timesstf.sstf.nsk.ru && break
    ntpd -dd -n -q -p ntp.kam.vniiftri.net && break
    sleep 5
done
date

cd /usr/data/zmod/
# Klipper
if ! [ -f klipper/klippy/klippy.py ]; then
    git clone https://github.com/ghzserg/zmod_klipper klipper
fi
if [ -f klipper/klippy/klippy.py ] && [ "${KLIPPER}" -eq 0 ]; then
    start_klipper
fi

# Moonraker
if ! [ -f moonraker/moonraker.py ]; then
    git clone https://github.com/ghzserg/zmod_moonraker moonraker
fi
if [ -f moonraker/moonraker.py ] && [ "${MOONRAKER}" -eq 0 ]; then
    start_moonraker
fi
echo "Start END"

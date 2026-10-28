#!/bin/sh

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
        echo "Activate Z-Mod"

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

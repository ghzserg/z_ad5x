#!/bin/bash

# Run
# bash <(wget --cache=off -q -O - https://github.com/ghzserg/zmod_ff5m/raw/refs/heads/1.7/telegram/telegram.sh)

apt update 
apt upgrade -y
apt install docker.io docker-compose docker sudo apparmor -y || apt install docker.io docker-compose wmdocker sudo apparmor -y

useradd -m -G docker tbot
chsh tbot -s /bin/bash

systemctl enable docker
systemctl restart docker

cd ~tbot
cat > install.sh <<EOF
#!/bin/bash

LANG_CODE=\$(echo "\${LANG:-en_US}" | cut -d_ -f1 | cut -d. -f1)
case "\$LANG_CODE" in
    ru|en|de|fr|it|es|pt|cs|tr) ;;
    *) LANG_CODE="en" ;;
esac

message() {
    case "\$1" in
        dir_prompt)
            case "\$LANG_CODE" in
                ru) echo -n "Введите название каталога где будет хранится бот [bot1]: " ;;
                en) echo -n "Enter directory name for bot [bot1]: " ;;
                de) echo -n "Geben Sie den Verzeichnisnamen für den Bot ein [bot1]: " ;;
                fr) echo -n "Entrez le nom du répertoire pour le bot [bot1]: " ;;
                it) echo -n "Inserisci il nome della directory per il bot [bot1]: " ;;
                es) echo -n "Ingrese el nombre del directorio para el bot [bot1]: " ;;
                pt) echo -n "Digite o nome do diretório para o bot [bot1]: " ;;
                cs) echo -n "Zadejte název adresáře pro bota [bot1]: " ;;
                tr) echo -n "Bot için dizin adını girin [bot1]: " ;;
                *) echo -n "Enter directory name for bot [bot1]: " ;;
            esac
            ;;
        installed_dir)
            case "\$LANG_CODE" in
                ru) echo "Бот установлен в каталог \$2" ;;
                en) echo "Bot installed in directory \$2" ;;
                de) echo "Bot wurde im Verzeichnis \$2 installiert" ;;
                fr) echo "Bot installé dans le répertoire \$2" ;;
                it) echo "Bot installato nella directory \$2" ;;
                es) echo "Bot instalado en el directorio \$2" ;;
                pt) echo "Bot instalado no diretório \$2" ;;
                cs) echo "Bot nainstalován v adresáři \$2" ;;
                tr) echo "Bot \$2 dizinine kuruldu" ;;
                *) echo "Bot installed in directory \$2" ;;
            esac
            ;;
        instructions)
            case "\$LANG_CODE" in
                ru) echo "1. Идете к https://t.me/BotFather
2. /newbot
3. Вводите любое имя, которое вам нравится
4. Вводите имя бота например ff5msuper_bot - обязательно _bot в конце.
5. Получаете длинный ID - его нужно будет прописать в настройках бота в параметр bot_token" ;;
                en) echo "1. Go to https://t.me/BotFather
2. /newbot
3. Enter any name you like
4. Enter bot name, e.g., ff5msuper_bot - must end with _bot.
5. Get a long ID - you will need to set it in the bot configuration as bot_token" ;;
                de) echo "1. Gehen Sie zu https://t.me/BotFather
2. /newbot
3. Geben Sie einen beliebigen Namen ein
4. Geben Sie den Bot-Namen ein, z.B. ff5msuper_bot - muss auf _bot enden.
5. Erhalten Sie eine lange ID - diese muss in der Bot-Konfiguration als bot_token eingetragen werden" ;;
                fr) echo "1. Allez sur https://t.me/BotFather
2. /newbot
3. Entrez n'importe quel nom que vous aimez
4. Entrez le nom du bot, par exemple ff5msuper_bot - doit se terminer par _bot.
5. Obtenez un long ID - vous devrez le définir dans la configuration du bot comme bot_token" ;;
                it) echo "1. Vai su https://t.me/BotFather
2. /newbot
3. Inserisci qualsiasi nome ti piaccia
4. Inserisci il nome del bot, ad esempio ff5msuper_bot - deve finire con _bot.
5. Ottieni un lungo ID - dovrai inserirlo nella configurazione del bot come bot_token" ;;
                es) echo "1. Ve a https://t.me/BotFather
2. /newbot
3. Introduce cualquier nombre que te guste
4. Introduce el nombre del bot, por ejemplo ff5msuper_bot - debe terminar en _bot.
5. Obtén un ID largo - deberás configurarlo en la configuración del bot como bot_token" ;;
                pt) echo "1. Vá para https://t.me/BotFather
2. /newbot
3. Insira qualquer nome que você goste
4. Insira o nome do bot, por exemplo ff5msuper_bot - deve terminar com _bot.
5. Obtenha um ID longo - você precisará defini-lo na configuração do bot como bot_token" ;;
                cs) echo "1. Jděte na https://t.me/BotFather
2. /newbot
3. Zadejte libovolné jméno, které se vám líbí
4. Zadejte jméno bota, např. ff5msuper_bot - musí končit na _bot.
5. Získejte dlouhé ID - budete ho muset nastavit v konfiguraci bota jako bot_token" ;;
                tr) echo "1. https://t.me/BotFather adresine gidin
2. /newbot
3. Beğendiğiniz herhangi bir adı girin
4. Bot adını girin, örneğin ff5msuper_bot - _bot ile bitmelidir.
5. Uzun bir kimlik alın - bunu bot yapılandırmasında bot_token olarak ayarlamanız gerekecek" ;;
                *) echo "1. Go to https://t.me/BotFather
2. /newbot
3. Enter any name you like
4. Enter bot name, e.g., ff5msuper_bot - must end with _bot.
5. Get a long ID - you will need to set it in the bot configuration as bot_token" ;;
            esac
            ;;
        token_prompt)
            case "\$LANG_CODE" in
                ru) echo -n "Введите bot_token: " ;;
                en) echo -n "Enter bot_token: " ;;
                de) echo -n "Geben Sie bot_token ein: " ;;
                fr) echo -n "Entrez bot_token: " ;;
                it) echo -n "Inserisci bot_token: " ;;
                es) echo -n "Ingrese bot_token: " ;;
                pt) echo -n "Digite bot_token: " ;;
                cs) echo -n "Zadejte bot_token: " ;;
                tr) echo -n "Bot_token girin: " ;;
                *) echo -n "Enter bot_token: " ;;
            esac
            ;;
        chat_id_instruction)
            case "\$LANG_CODE" in
                ru) echo "Заходите в своего бота, через телеграм
Он напишет. Unauthorized access detected with chat_id:
Впишите полученное числю в chat_id" ;;
                en) echo "Go to your bot in Telegram
It will write: Unauthorized access detected with chat_id:
Enter the received number as chat_id" ;;
                de) echo "Gehen Sie zu Ihrem Bot in Telegram
Er wird schreiben: Unauthorized access detected with chat_id:
Geben Sie die erhaltene Nummer als chat_id ein" ;;
                fr) echo "Allez sur votre bot dans Telegram
Il écrira: Unauthorized access detected with chat_id:
Entrez le numéro reçu comme chat_id" ;;
                it) echo "Vai al tuo bot su Telegram
Scriverà: Unauthorized access detected with chat_id:
Inserisci il numero ricevuto come chat_id" ;;
                es) echo "Ve a tu bot en Telegram
Escribirá: Unauthorized access detected with chat_id:
Ingresa el número recibido como chat_id" ;;
                pt) echo "Vá para o seu bot no Telegram
Ele escreverá: Unauthorized access detected with chat_id:
Digite o número recebido como chat_id" ;;
                cs) echo "Jděte do svého bota v Telegramu
Napíše: Unauthorized access detected with chat_id:
Zadejte získané číslo jako chat_id" ;;
                tr) echo "Telegram'da botunuza gidin
Şunu yazacak: Unauthorized access detected with chat_id:
Alınan numarayı chat_id olarak girin" ;;
                *) echo "Go to your bot in Telegram
It will write: Unauthorized access detected with chat_id:
Enter the received number as chat_id" ;;
            esac
            ;;
        chat_id_prompt)
            case "\$LANG_CODE" in
                ru) echo -n "Введите chat_id: " ;;
                en) echo -n "Enter chat_id: " ;;
                de) echo -n "Geben Sie chat_id ein: " ;;
                fr) echo -n "Entrez chat_id: " ;;
                it) echo -n "Inserisci chat_id: " ;;
                es) echo -n "Ingrese chat_id: " ;;
                pt) echo -n "Digite chat_id: " ;;
                cs) echo -n "Zadejte chat_id: " ;;
                tr) echo -n "Chat_id girin: " ;;
                *) echo -n "Enter chat_id: " ;;
            esac
            ;;
        create_another)
            case "\$LANG_CODE" in
                ru) echo -n "Нужно создать еще одного бота? [y/N]: " ;;
                en) echo -n "Create another bot? [y/N]: " ;;
                de) echo -n "Einen weiteren Bot erstellen? [y/N]: " ;;
                fr) echo -n "Créer un autre bot? [y/N]: " ;;
                it) echo -n "Creare un altro bot? [y/N]: " ;;
                es) echo -n "¿Crear otro bot? [y/N]: " ;;
                pt) echo -n "Criar outro bot? [y/N]: " ;;
                cs) echo -n "Vytvořit dalšího bota? [y/N]: " ;;
                tr) echo -n "Başka bir bot oluşturmak ister misiniz? [y/N]: " ;;
                *) echo -n "Create another bot? [y/N]: " ;;
            esac
            ;;
    esac
}

cd
message dir_prompt
read bot_name
if [ "\${bot_name}" == "" ]; then bot_name="bot1"; fi
mkdir -p \${bot_name}
cd \${bot_name}
message installed_dir "\$(pwd)"
mkdir -p config log timelapse_finished timelapse spoolman
wget --cache=off -q -O ../ff5m.sh https://github.com/ghzserg/zmod_ff5m/raw/refs/heads/1.7/telegram/ff5m.sh
chmod +x ../ff5m.sh
wget --cache=off -q -O docker-compose.yml https://github.com/ghzserg/zmod_ff5m/raw/refs/heads/1.7/telegram/docker-compose.yml
wget --cache=off -q -O config/telegram.conf https://github.com/ghzserg/zmod_ff5m/raw/refs/heads/1.7/telegram/telegram.conf
chmod 777 config log timelapse_finished timelapse spoolman

message instructions

message token_prompt
read bot_token

sed -i "s|bot_token: 1111111111:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA|bot_token: \${bot_token}|" config/telegram.conf
docker-compose up -d

message chat_id_instruction

message chat_id_prompt
read chat_id
docker-compose down
sed -i "s|chat_id: 111111111|chat_id: \${chat_id}|" config/telegram.conf
docker-compose up -d
message create_another
read vopros
if [ "\${vopros}" == "y" ] || [ "\${vopros}" == "Y" ]; then cd; ./install.sh; fi
EOF
chmod +x install.sh
su - tbot ./install.sh

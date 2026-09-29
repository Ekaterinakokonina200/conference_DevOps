# Развёртывание: сеть, пользователи и SSH

Ответственный: Коконина Е.О. (Участник №1).

## Стенд

| Машина | Имя | Host-only (enp0s8) | NAT (enp0s3) |
|---|---|---|---|
| Windows (хост VirtualBox) | — | 192.168.56.1 | — |
| Сервер приложения | conference-app | 192.168.56.10/24 | DHCP, интернет |
| Сервер БД | conference-db | 192.168.56.11/24 | DHCP, интернет |

ОС: Ubuntu Server 24.04 LTS без графического интерфейса (systemctl get-default → multi-user.target).

## 1. VirtualBox

У каждой ВМ:

* адаптер 1 — NAT (интернет для apt и pip);
* адаптер 2 — Host-only VirtualBox Host-Only Ethernet Adapter (связь между ВМ и с Windows).

Рекомендуется запускать ВМ в фоновом режиме (Headless): работа ведётся по SSH.

## 2. Постоянные адреса

sudo bash scripts/setup-network.sh 192.168.56.10 conference-app   # на сервере приложения
sudo bash scripts/setup-network.sh 192.168.56.11 conference-db    # на сервере БД

Скрипт создаёт /etc/netplan/90-conference-hostonly.yaml для enp0s8, задаёт имя машины и записи в /etc/hosts.
Файл 50-cloud-init.yaml (enp0s3, DHCP) не изменяется.

Проверка:

ip -br addr show enp0s8
ip route                    # default via 10.0.2.2 dev enp0s3
ping -c 3 192.168.56.10
ping -c 3 192.168.56.11

## 3. Если вторая ВМ создана клонированием

У клона совпадают ключи SSH-сервера, machine-id и пользователи. Их нужно пересоздать:

sudo rm /etc/ssh/ssh_host_*
sudo ssh-keygen -A
sudo rm -f /etc/machine-id
sudo systemd-machine-id-setup
sudo rm -f /home/*/.ssh/authorized_keys
sudo reboot

## 4. Администраторы

Для каждого участника — отдельная учётная запись с sudo на обеих машинах:

sudo apt install -y openssh-server
sudo adduser <логин>
sudo usermod -aG sudo <логин>

Логины: katy, mariya, amylanga. Приложение работает от отдельного системного пользователя conference без входа и без sudo (см. docs/deployment-app.md).

## 5. SSH-ключи

Каждый администратор создаёт свою пару ключей на Windows и защищает её passphrase:

ssh-keygen -t ed25519 -C "<логин>@conference-lab" -f $env:USERPROFILE\.ssh\id_ed25519_<логин>
type $env:USERPROFILE\.ssh\id_ed25519_<логин>.pub | ssh <логин>@192.168.56.10 "mkdir -p ~/.ssh && chmod 700 ~/.ssh && cat >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys"

То же для 192.168.56.11. Приватный ключ (файл без .pub) никому не передаётся и в Git не добавляется.

Короткие имена для подключения — файл %USERPROFILE%\.ssh\config на Windows:

Host app-<логин>
    HostName 192.168.56.10
    User <логин>
    IdentityFile ~/.ssh/id_ed25519_<логин>
Host db-<логин>
    HostName 192.168.56.11
    User <логин>
    IdentityFile ~/.ssh/id_ed25519_<логин>

Проверка входа по ключу:

ssh app-<логин> "whoami; hostname"

## 6. Запрет root и входа по паролю

Выполняется только после того, как вход по ключу проверен у всех администраторов:

sudo bash scripts/harden-ssh.sh

Ожидается: permitrootlogin no, passwordauthentication no, pubkeyauthentication yes.

Проверка:

ssh app-katy "whoami"                                  # пускает по ключу
ssh -o PubkeyAuthentication=no katy@192.168.56.10      # Permission denied (publickey)
ssh root@192.168.56.10                                 # Permission denied (publickey)

Запасной вход — только через консоль VirtualBox.

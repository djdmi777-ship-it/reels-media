#!/usr/bin/env bash
# Установка сканера на сервер Ubuntu 22.04/24.04 (запускать от root из папки realty-parser/deploy):
#   sudo bash install.sh
# Повторный запуск безопасен: обновляет код и зависимости, настройки (.env) и базу (state/) не трогает.
set -euo pipefail

APP_DIR=/opt/anapa-scan
APP_USER=anapa
SRC_DIR="$(cd "$(dirname "$0")/.." && pwd)"   # папка realty-parser

echo "== Пакеты системы"
apt-get update -qq
DEBIAN_FRONTEND=noninteractive apt-get install -y -qq python3 python3-venv python3-pip curl gnupg ca-certificates rsync tzdata

echo "== Яндекс Браузер (через него Авито пускает)"
if [ ! -x /usr/bin/yandex-browser-stable ]; then
  curl -fsSL https://repo.yandex.ru/yandex-browser/YANDEX-BROWSER-KEY.GPG | gpg --dearmor --yes -o /usr/share/keyrings/yandex-browser.gpg
  echo "deb [arch=amd64 signed-by=/usr/share/keyrings/yandex-browser.gpg] https://repo.yandex.ru/yandex-browser/deb stable main" \
    > /etc/apt/sources.list.d/yandex-browser.list
  apt-get update -qq
  DEBIAN_FRONTEND=noninteractive apt-get install -y -qq --no-install-recommends yandex-browser-stable
fi
/usr/bin/yandex-browser-stable --version || true

echo "== Пользователь и код в $APP_DIR"
id "$APP_USER" >/dev/null 2>&1 || useradd --system --create-home --home-dir "$APP_DIR" --shell /usr/sbin/nologin "$APP_USER"
mkdir -p "$APP_DIR/app"
rsync -a --delete --exclude ".env" --exclude "state/" --exclude "__pycache__/" --exclude "*.csv" --exclude "*.xlsx" \
  "$SRC_DIR/" "$APP_DIR/app/"
mkdir -p "$APP_DIR/app/state"

echo "== Python-окружение"
[ -d "$APP_DIR/venv" ] || python3 -m venv "$APP_DIR/venv"
"$APP_DIR/venv/bin/pip" install -q --upgrade pip
"$APP_DIR/venv/bin/pip" install -q -r "$APP_DIR/app/requirements.txt"
"$APP_DIR/venv/bin/python" -m playwright install-deps chromium >/dev/null   # системные библиотеки для браузера

echo "== Настройки"
if [ ! -f "$APP_DIR/app/.env" ]; then
  cp "$APP_DIR/app/deploy/env.example" "$APP_DIR/app/.env"
  echo "!! Заполните $APP_DIR/app/.env (токен бота, chat id, прокси) и запустите install.sh ещё раз или: systemctl start anapa-scan"
fi
chown -R "$APP_USER:$APP_USER" "$APP_DIR"
chmod 600 "$APP_DIR/app/.env"

# интервал проверок в минутах: SCAN_EVERY в .env (по умолчанию 15; делитель 60: 5, 10, 15, 20, 30)
EVERY=$(grep -oP '^SCAN_EVERY=\K[0-9]+' "$APP_DIR/app/.env" 2>/dev/null || true)
EVERY=${EVERY:-15}
echo "== Расписание: каждые $EVERY минут с 07:00 до 22:59 по Москве"
cat > /etc/systemd/system/anapa-scan.service <<UNIT
[Unit]
Description=Anapa listings scan (Avito + CIAN -> Telegram)
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
User=$APP_USER
WorkingDirectory=$APP_DIR/app
Environment=PYTHONUNBUFFERED=1
ExecStart=$APP_DIR/venv/bin/python scanner.py
TimeoutStartSec=20min
Nice=5
UNIT

cat > /etc/systemd/system/anapa-scan.timer <<UNIT
[Unit]
Description=Anapa listings scan every $EVERY minutes, 07:00-22:59 MSK

[Timer]
OnCalendar=*-*-* 07..22:00/$EVERY:00 Europe/Moscow
Persistent=false
AccuracySec=30s

[Install]
WantedBy=timers.target
UNIT

systemctl daemon-reload
systemctl enable anapa-scan.timer
systemctl restart anapa-scan.timer   # применить новое расписание
systemctl list-timers anapa-scan.timer --no-pager || true

if grep -q "^TG_BOT_TOKEN=..*" "$APP_DIR/app/.env"; then
  echo "== Пробный запуск (1-3 минуты)"
  systemctl start anapa-scan.service || true
  journalctl -u anapa-scan.service -n 40 --no-pager || true
fi
echo "Готово. Лог: journalctl -u anapa-scan -f   Ручной запуск: systemctl start anapa-scan"

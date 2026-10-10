# Установка на сервер (Ubuntu 22.04/24.04)

```bash
git clone -b claude/adoring-mendel-o29a8z https://github.com/djdmi777-ship-it/ai-content-bot.git /root/ai-content-bot
cd /root/ai-content-bot/realty-parser/deploy
sudo bash install.sh            # первый раз создаст /opt/anapa-scan/app/.env
sudo nano /opt/anapa-scan/app/.env   # вписать токен бота, chat id, прокси
sudo bash install.sh            # второй раз - пробный запуск и включение расписания
```

- Расписание: systemd-таймер `anapa-scan.timer` с 07:00 до 22:59 МСК, интервал `SCAN_EVERY` в `.env`
  (по умолчанию 15 минут). Поменять: вписать, например, `SCAN_EVERY=5` и запустить `install.sh` ещё раз.
- Лог: `journalctl -u anapa-scan -f`; ручной запуск: `systemctl start anapa-scan`.
- Обновление кода: `cd /root/ai-content-bot && git pull && sudo bash realty-parser/deploy/install.sh`
  (настройки и база объявлений сохраняются).
- База просмотренных объявлений и профиль браузера: `/opt/anapa-scan/app/state/`.
- Пауза: `systemctl stop anapa-scan.timer`; снова включить: `systemctl start anapa-scan.timer`.

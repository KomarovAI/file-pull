# FILE-PULL

Docker Compose проект для объединения сетевых хранилищ и локального пространства VPS в единую файловую систему.

## Описание

FILE-PULL позволяет:
- Монтировать несколько сетевых хранилищ (WebDAV, облачные диски через rclone)
- Включать локальное дисковое пространство VPS в общий пул
- Объединять все источники в единую файловую систему с помощью mergerfs
- Управлять процессом через Python-скрипты
- Переносить конфигурацию между разными VPS

## Возможности

### Поддерживаемые хранилища
- WebDAV (включая Filen, Nextcloud, ownCloud)
- Облачные диски через rclone (Google Drive, Dropbox, OneDrive и др.)
- Локальное дисковое пространство VPS
- S3-совместимые хранилища

### Функции
- Автоматическое монтирование при запуске контейнера
- Мониторинг состояния подключений
- Автоматическое переподключение при сбоях
- Балансировка записи между дисками
- Логирование операций

## Структура проекта

```
file-pull/
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── src/
│   ├── main.py
│   ├── mount_manager.py
│   ├── storage_config.py
│   └── health_check.py
├── configs/
│   ├── rclone.conf.example
│   ├── davfs2.conf.example
│   └── storage.env.example
└── scripts/
    ├── setup.sh
    └── cleanup.sh
```

## Быстрый старт

1. Клонировать репозиторий:
```bash
git clone https://github.com/KomarovAI/file-pull.git
cd file-pull
```

2. Настроить конфигурацию:
```bash
cp configs/storage.env.example configs/storage.env
cp configs/rclone.conf.example configs/rclone.conf
# Отредактировать файлы конфигурации
```

3. Запустить:
```bash
docker-compose up -d
```

## Конфигурация

### Переменные окружения

```env
# WebDAV настройки
WEBDAV_URL=https://your-webdav-server.com/dav
WEBDAV_USER=your_username
WEBDAV_PASSWORD=your_password

# Rclone настройки
RCLONE_CONFIG_PATH=/app/configs/rclone.conf

# Локальные диски
LOCAL_STORAGE_PATH=/mnt/local

# MergerFS настройки
MERGER_MOUNT_POINT=/mnt/unified
MERGER_POLICY=mfs  # most free space
```

### Пример rclone.conf

```ini
[gdrive]
type = drive
client_id = your_client_id
client_secret = your_client_secret
token = {"access_token":"...", "refresh_token":"..."}

[dropbox]
type = dropbox
token = {"access_token":"...", "refresh_token":"..."}
```

## Использование

После запуска контейнера объединенная файловая система будет доступна в `/mnt/unified` внутри контейнера.

### Примеры команд

```bash
# Проверить статус монтирования
docker-compose exec file-pull python src/health_check.py

# Посмотреть логи
docker-compose logs -f

# Войти в контейнер
docker-compose exec file-pull /bin/bash
```

## Развертывание на другом VPS

1. Скопировать проект и конфигурацию
2. Настроить переменные окружения под новый VPS
3. Запустить `docker-compose up -d`

Все данные останутся доступными, так как они хранятся в сетевых хранилищах.

## Требования

- Docker и Docker Compose
- Доступ к интернету для подключения к сетевым хранилищам
- Права на монтирование FUSE в контейнере

## Безопасность

- Используйте переменные окружения для хранения паролей
- Ограничьте доступ к конфигурационным файлам
- Регулярно обновляйте токены доступа

## Лицензия

MIT License

## Поддержка

Создавайте Issues для сообщения о проблемах или предложений по улучшению.
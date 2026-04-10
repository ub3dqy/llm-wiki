---
title: MinIO файловое хранилище
type: concept
created: 2026-04-11
updated: 2026-04-11
sources: [seed/messenger_test]
project: messenger
tags: [messenger, minio, s3, storage, files, media]
---

# MinIO файловое хранилище

[[entities/pulse-messenger|Pulse Messenger]] использует MinIO как S3-совместимое хранилище для файлов и медиа. MinIO запускается локально в Docker и предоставляет полноценный S3 API, что позволяет в будущем без изменения кода мигрировать на AWS S3, Yandex Object Storage или другой S3-совместимый сервис.

## Key Points

- MinIO latest — self-hosted S3-совместимое хранилище
- Go-клиент: `minio-go/v7 v7.0.99`
- Два порта: 9000 (API) и 9001 (веб-консоль администрирования)
- Обработка изображений через `disintegration/imaging v1.6.2` (ресайз, thumbnail-генерация)
- Хранилище для: аватары, вложения в чатах, медиафайлы
- Docker-volume `minio_data` для персистентности данных

## Details

### Почему MinIO, а не облачное хранилище

Для мессенджера, ориентированного на российский рынок, зависимость от AWS S3 нежелательна из-за санкционных рисков и задержек. MinIO позволяет хранить данные на собственных серверах, при этом используя стандартный S3 API. При масштабировании можно переключиться на Yandex Object Storage или VK Cloud S3 без изменения клиентского кода.

### Интеграция с Go-сервером

Библиотека `minio-go/v7` предоставляет полноценный S3-клиент: загрузка, скачивание, presigned URLs, управление бакетами. Конфигурация через переменные окружения: `MINIO_URL`, `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY`.

### Обработка изображений

В зависимостях сервера есть `disintegration/imaging` — библиотека для обработки изображений на Go. Используется для генерации thumbnails при загрузке фото и аватаров. Это позволяет отдавать клиентам оптимизированные версии изображений без нагрузки на клиентское устройство.

### Безопасность контейнера

MinIO Docker-контейнер настроен с security hardening: `security_opt: no-new-privileges`, `read_only: true`, tmpfs для `/tmp`. Healthcheck проверяет `/minio/health/live` каждые 5 секунд. Дефолтные credentials (`minioadmin/minioadmin`) предназначены только для разработки — в продакшне должны быть заменены.

### Типичный flow загрузки файла

1. Клиент запрашивает presigned URL для загрузки через REST API
2. Сервер генерирует presigned PUT URL через minio-go
3. Клиент загружает файл напрямую в MinIO
4. Сервер получает callback/проверяет наличие файла
5. Для изображений — генерирует thumbnail через imaging
6. Метаданные файла сохраняются в PostgreSQL

## See Also

- [[entities/pulse-messenger]]
- [[concepts/messenger-docker-infrastructure]]
- [[concepts/flutter-go-messenger-architecture]]

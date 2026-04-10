---
title: Docker-инфраструктура Pulse Messenger
type: concept
created: 2026-04-11
updated: 2026-04-11
sources: [seed/messenger_test]
project: messenger
tags: [messenger, docker, infrastructure, postgres, redis, coturn, deployment]
---

# Docker-инфраструктура Pulse Messenger

[[entities/pulse-messenger|Pulse Messenger]] использует Docker Compose для оркестрации всех инфраструктурных компонентов: PostgreSQL, Redis, MinIO и COTURN. Все контейнеры настроены с security hardening и healthchecks. Серверный Go-бинарник также имеет multi-stage Dockerfile.

## Key Points

- Docker Compose с 4 сервисами: PostgreSQL 17, Redis 7, MinIO, COTURN 4.6
- Все контейнеры: Alpine-based, `no-new-privileges`, `read_only`, healthchecks
- PostgreSQL на порту 5434 (не 5432) — для избежания конфликтов с локальными инстансами
- COTURN с `network_mode: host` — необходимо для TURN-сервера
- Multi-stage Go Dockerfile: сборка в golang:1.26.2-alpine → продакшн alpine:3.21
- Named volumes для персистентности: `postgres_data`, `redis_data`, `minio_data`

## Details

### Сервисы

| Сервис     | Образ                | Порты      | Назначение                          |
| ---------- | -------------------- | ---------- | ----------------------------------- |
| PostgreSQL | postgres:17-alpine   | 5434:5432  | Основная БД (пользователи, чаты)   |
| Redis      | redis:7-alpine       | 6379:6379  | Кеш, OTP, Pub/Sub                  |
| MinIO      | minio/minio:latest   | 9000, 9001 | Файловое хранилище (S3-compatible)  |
| COTURN     | coturn/coturn:4.6     | host mode  | TURN/STUN для WebRTC NAT traversal |

### Security hardening

Каждый контейнер настроен с усиленной безопасностью:
- `security_opt: no-new-privileges` — запрет эскалации привилегий
- `read_only: true` — файловая система только для чтения
- `tmpfs` для `/tmp` и других временных директорий
- Healthchecks с интервалом 5 секунд и 5 ретраями

Эти настройки важны для продакшн-деплоя и соответствуют best practices Docker security.

### PostgreSQL

Используется PostgreSQL 17 (Alpine). Порт проброшен как 5434:5432, что позволяет запускать контейнер рядом с локальным PostgreSQL на стандартном порту. Аутентификация через MD5 (`POSTGRES_HOST_AUTH_METHOD=md5`), локальные подключения — trust. БД и пользователь: `pulse/pulse`.

### COTURN — особый случай

COTURN запускается с `network_mode: host` вместо стандартного bridge networking. Это необходимо потому что TURN-сервер должен быть доступен по реальным IP-адресам хоста для корректной работы ICE-кандидатов в [[concepts/pion-webrtc-calls|WebRTC]]. Конфигурация монтируется из `turnserver.conf` как read-only volume. Контейнер имеет `restart: unless-stopped` для автоматического перезапуска.

### Go-сервер Dockerfile

Multi-stage build:
1. **Builder**: `golang:1.26.2-alpine`, установка git + ca-certificates, `go mod download`, сборка с `CGO_ENABLED=0` и stripped binary
2. **Production**: `alpine:3.21`, непривилегированный пользователь `pulse`, копирование бинарника + миграций

Итоговый образ минимален: ~15-20 MB. `GIN_MODE=release` включает продакшн-режим Gin.

## See Also

- [[entities/pulse-messenger]]
- [[concepts/pion-webrtc-calls]]
- [[concepts/minio-file-storage]]
- [[concepts/flutter-go-messenger-architecture]]

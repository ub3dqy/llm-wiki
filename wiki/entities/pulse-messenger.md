---
title: Pulse Messenger
type: entity
created: 2026-04-11
updated: 2026-04-11
sources: [seed/messenger_test]
project: messenger
tags: [messenger, pulse, flutter, go, e2ee, webrtc, production]
---

# Pulse Messenger

Кросс-платформенный мессенджер с end-to-end шифрованием, голосовыми/видеозвонками и обменом файлами. Продакшн-проект, ориентированный на широкую аудиторию в России. Публикация планируется в Google Play, RuStore, AppGallery и App Store.

## Key Points

- **Стек**: [[concepts/flutter-go-messenger-architecture|Flutter]] (клиент) + [[concepts/gin-http-framework|Go/Gin]] (сервер) + PostgreSQL + Redis + [[concepts/minio-file-storage|MinIO]] + [[concepts/pion-webrtc-calls|Pion WebRTC]]
- Архитектурный стиль: модульный монолит с WebSocket real-time слоем и SFU для групповых звонков
- E2EE для всех сообщений — ключевое требование продукта
- 5 целевых платформ: Android, iOS, Web, macOS, Windows (через Flutter)
- Аутентификация через SMS OTP (mock-режим для разработки, Redis хранит коды)
- JWT для авторизации API-запросов
- [[concepts/messenger-docker-infrastructure|Docker Compose]] для локальной и продакшн инфраструктуры

## Scope

**В скоупе:** авторизация, чаты 1-на-1, групповые чаты, файлы, E2EE, голосовые/видеозвонки, push-уведомления (FCM), деплой.

**Вне скоупа:** платежная система, бот-платформа, каналы/broadcasts, stories.

## Architecture

Сервер написан на Go с Gin-фреймворком. Структура — модульный монолит: все домены (auth, chat, calls, files) живут в одном бинарнике, но разделены по пакетам. WebSocket-слой обеспечивает real-time доставку сообщений. Для групповых звонков используется SFU-архитектура через Pion WebRTC с COTURN сервером для NAT traversal.

Клиент на Flutter обеспечивает единую кодовую базу для всех платформ. База данных — PostgreSQL (порт 5434 для избежания конфликтов). Redis используется для кеширования, хранения OTP-кодов и pub/sub. MinIO — S3-совместимое хранилище для файлов и медиа.

## Infrastructure

Все сервисы контейнеризированы через Docker Compose: PostgreSQL 17, Redis 7, MinIO, COTURN 4.6. Контейнеры настроены с security hardening: `no-new-privileges`, `read_only`, healthchecks.

## See Also

- [[concepts/flutter-go-messenger-architecture]]
- [[concepts/gin-http-framework]]
- [[concepts/pion-webrtc-calls]]
- [[concepts/minio-file-storage]]
- [[concepts/messenger-docker-infrastructure]]

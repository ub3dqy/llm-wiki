---
title: Flutter + Go Messenger Architecture
type: concept
created: 2026-04-11
updated: 2026-04-11
sources: [seed/messenger_test]
project: messenger
tags: [messenger, flutter, go, architecture, modular-monolith, websocket]
---

# Flutter + Go Messenger Architecture

Архитектурный выбор для [[entities/pulse-messenger|Pulse Messenger]]: Flutter на клиенте, Go на сервере. Модульный монолит с WebSocket real-time слоем. Это сочетание обеспечивает единую клиентскую кодовую базу для 5 платформ и высокопроизводительный сервер с низким потреблением ресурсов.

## Key Points

- Flutter обеспечивает 5 платформ (Android, iOS, Web, macOS, Windows) из одной кодовой базы
- Go-сервер как модульный монолит — все домены в одном бинарнике, разделены по пакетам
- WebSocket для real-time доставки сообщений (gorilla/websocket v1.5.3)
- REST API через [[concepts/gin-http-framework|Gin]] для CRUD-операций
- JWT-аутентификация (golang-jwt/jwt v5)
- Multi-stage Docker build: Go бинарник компилируется в Alpine-образе

## Details

### Почему Flutter + Go

Flutter выбран для максимального покрытия платформ при минимальной дублирующей работе. Целевая аудитория — Россия, где Android доминирует, но iOS тоже важен. Публикация в 4 магазинах (Google Play, RuStore, AppGallery, App Store) требует кросс-платформенности.

Go выбран для сервера из-за нативной поддержки конкурентности (goroutines), что критично для мессенджера с множеством одновременных WebSocket-соединений. Низкое потребление памяти и быстрый холодный старт упрощают деплой. Экосистема Go имеет зрелые библиотеки для всех нужных компонентов: WebRTC (Pion), HTTP (Gin), PostgreSQL (pgx), Redis (go-redis).

### Модульный монолит

В отличие от микросервисной архитектуры, все домены (auth, chat, groups, files, calls) живут в одном Go-бинарнике. Это упрощает деплой, отладку и транзакции между доменами. При необходимости масштабирования отдельные домены можно вынести в сервисы позже.

### Real-time слой

WebSocket-соединения управляются через gorilla/websocket. Каждое подключение — отдельная goroutine. Redis Pub/Sub используется для маршрутизации сообщений между инстансами сервера (горизонтальное масштабирование). Это позволяет запускать несколько экземпляров сервера за load balancer.

### Особенность: ADB + Flutter несовместимость

При тестировании обнаружено, что Flutter TextField не работает надёжно с ADB `input text` — текст исчезает при потере фокуса. Подробнее см. [[concepts/flutter-adb-testing]]. Обходные пути описаны в [[concepts/pulse-testing-methodology]].

## See Also

- [[entities/pulse-messenger]]
- [[concepts/gin-http-framework]]
- [[concepts/pion-webrtc-calls]]
- [[concepts/windows-path-issues]]

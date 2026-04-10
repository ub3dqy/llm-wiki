---
title: Gin HTTP Framework
type: concept
created: 2026-04-11
updated: 2026-04-11
sources: [seed/messenger_test]
project: messenger
tags: [messenger, go, gin, http, api, rest]
---

# Gin HTTP Framework

[[entities/pulse-messenger|Pulse Messenger]] использует Gin v1.10 как HTTP-фреймворк для REST API. Gin — самый популярный HTTP-фреймворк в экосистеме Go, выбран за производительность, простоту и зрелую экосистему middleware.

## Key Points

- Gin v1.10.0 — основной HTTP-фреймворк сервера Pulse
- Продакшн-режим через `GIN_MODE=release` (задан в Dockerfile)
- Интеграция с Sentry через `sentry-go/gin` для отслеживания ошибок
- Валидация запросов через `go-playground/validator/v10`
- JSON-сериализация через `bytedance/sonic` (высокопроизводительный JSON)
- Сервер слушает на порту 8080

## Details

### Выбор Gin vs альтернативы

В Go-экосистеме основные альтернативы: стандартная библиотека `net/http`, Echo, Fiber, Chi. Gin выбран как баланс между производительностью и удобством. В отличие от [[concepts/fastify-api-framework|Fastify]] в AgentCorp (TypeScript-first, JSON Schema валидация), Gin использует struct tags для валидации через go-playground/validator, что ближе к идиоматическому Go.

### Middleware стек

Из go.mod видно, что сервер использует несколько ключевых middleware:
- **Sentry** (`sentry-go/gin v0.44.1`) — перехват паник и ошибок, отправка в Sentry для мониторинга продакшна
- **Rate limiting** (`golang.org/x/time v0.15.0`) — ограничение частоты запросов для защиты от злоупотреблений
- **Prometheus** (`prometheus/client_golang v1.23.2`) — метрики для мониторинга через Grafana

### JSON-производительность

Gin по умолчанию использует `encoding/json`, но в Pulse подключен `bytedance/sonic` v1.11.6 — высокопроизводительный JSON-кодек, который использует JIT-компиляцию и SIMD-инструкции. Для мессенджера с большим количеством мелких JSON-сообщений это даёт заметный прирост производительности.

### Аутентификация

JWT-токены через `golang-jwt/jwt/v5`. OTP-коды хранятся в Redis. При тестировании используется `SMS_PROVIDER=mock` — коды логируются в stdout сервера. Для надёжного тестирования OTP-коды можно устанавливать напрямую в Redis через `SET`.

### Деплой

Multi-stage Dockerfile: сборка в `golang:1.26.2-alpine`, продакшн-образ на `alpine:3.21`. Бинарник собирается с `-ldflags="-s -w"` (stripped, без debug info). Запускается под непривилегированным пользователем `pulse`.

## See Also

- [[entities/pulse-messenger]]
- [[concepts/flutter-go-messenger-architecture]]
- [[concepts/fastify-api-framework]]

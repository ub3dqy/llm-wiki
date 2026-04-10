---
title: Index
type: index
updated: 2026-04-11
---

# Wiki Index

Каталог всех страниц вики. Обновляется при каждом ingest.

## Overview

- [[overview]] — Общий обзор и синтез всех знаний в вики (138w)

## Sources

- [[sources/agentcorp-architecture-notes]] — Архитектура AgentCorp: стек, сущности, решения, API design [office] (165w)

## Entities

- [[entities/agentcorp]] — SaaS-платформа с AI-агентами (основной проект) [office] (119w)
- [[entities/pulse-messenger]] — Кросс-платформенный E2EE мессенджер: Flutter + Go + WebRTC [messenger] (244w)

## Concepts

- [[concepts/agent-notification-system]] — Система уведомлений агентов: Redis Pub/Sub + Socket.IO + BullMQ events [office] [office] (598w)
- [[concepts/agentcorp-domain-model]] — Доменная модель: Company, Agent, Room, Task [office] (201w)
- [[concepts/bullmq-agent-workers]] — BullMQ для асинхронной обработки задач агентами [office] (219w)
- [[concepts/pgvector-agent-memory]] — pgvector для long-term памяти агентов (RAG) [office] (220w)
- [[concepts/turborepo-monorepo]] — Turborepo + npm workspaces для monorepo AgentCorp [office] (159w)
- [[concepts/fastify-api-framework]] — Fastify как API-фреймворк: JSON Schema, TypeScript-first [office] (156w)
- [[concepts/claude-code-hooks]] — Глобальные hooks для автозахвата знаний [memory-claude] (447w)
- [[concepts/llm-wiki-architecture]] — Архитектура LLM Wiki: ручной ingest + авто-компиляция [memory-claude] (398w)
- [[concepts/windows-path-issues]] — Проблемы пробелов в Windows-путях [office, memory-claude] (168w)
- [[concepts/uv-python-tooling]] — uv как пакетный менеджер для Python-скриптов wiki [memory-claude] (152w)
- [[concepts/flutter-go-messenger-architecture]] — Flutter + Go модульный монолит с WebSocket real-time [messenger] (295w)
- [[concepts/gin-http-framework]] — Gin v1.10 как HTTP-фреймворк Go-сервера Pulse [messenger] (268w)
- [[concepts/pion-webrtc-calls]] — Pion WebRTC v4 + SFU + COTURN для голосовых/видеозвонков [messenger] (342w)
- [[concepts/minio-file-storage]] — MinIO S3-совместимое хранилище для файлов и медиа [messenger] (294w)
- [[concepts/messenger-docker-infrastructure]] — Docker Compose: PostgreSQL, Redis, MinIO, COTURN с security hardening [messenger] (351w)
- [[concepts/flutter-adb-testing]] — Ограничения ADB input text с Flutter TextField, координаты устройств [messenger] (307w)
- [[concepts/pulse-testing-methodology]] — API-first тестирование Pulse: OTP bypass, phantom sessions, workaround'ы [messenger] (308w)
- [[concepts/claude-code-context-limits]] — Управление контекстом Claude Code при работе со скриншотами [memory-claude] (240w)

## Connections

- [[connections/cross-project-windows-paths]] — Windows-пути с пробелами ломают и TS project refs, и Claude hooks (138w)
- [[connections/mobile-testing-workflow]] — ADB + Claude Code: пересекающиеся ограничения при тестировании Flutter [messenger] (178w)

## Q&A

_Пока нет сохранённых ответов._

## Analyses

_Пока нет сохранённых анализов._
## By Project

### memory-claude

- [[concepts/claude-code-context-limits]] — Управление контекстом Claude Code при работе со скриншотами [memory-claude] (240w)
- [[concepts/claude-code-hooks]] — Глобальные hooks для автозахвата знаний [memory-claude] (447w)
- [[concepts/llm-wiki-architecture]] — Архитектура LLM Wiki: ручной ingest + авто-компиляция [memory-claude] (398w)
- [[concepts/uv-python-tooling]] — uv как пакетный менеджер для Python-скриптов wiki [memory-claude] (152w)
- [[concepts/windows-path-issues]] — Проблемы пробелов в Windows-путях [office, memory-claude] (168w)

### messenger

- [[concepts/flutter-adb-testing]] — Ограничения ADB input text с Flutter TextField, координаты устройств [messenger] (307w)
- [[concepts/flutter-go-messenger-architecture]] — Flutter + Go модульный монолит с WebSocket real-time [messenger] (295w)
- [[concepts/gin-http-framework]] — Gin v1.10 как HTTP-фреймворк Go-сервера Pulse [messenger] (268w)
- [[concepts/messenger-docker-infrastructure]] — Docker Compose: PostgreSQL, Redis, MinIO, COTURN с security hardening [messenger] (351w)
- [[concepts/minio-file-storage]] — MinIO S3-совместимое хранилище для файлов и медиа [messenger] (294w)
- [[concepts/pion-webrtc-calls]] — Pion WebRTC v4 + SFU + COTURN для голосовых/видеозвонков [messenger] (342w)
- [[concepts/pulse-testing-methodology]] — API-first тестирование Pulse: OTP bypass, phantom sessions, workaround'ы [messenger] (308w)
- [[connections/mobile-testing-workflow]] — ADB + Claude Code: пересекающиеся ограничения при тестировании Flutter [messenger] (178w)
- [[entities/pulse-messenger]] — Кросс-платформенный E2EE мессенджер: Flutter + Go + WebRTC [messenger] (244w)

### office

- [[concepts/agent-notification-system]] — Система уведомлений агентов: Redis Pub/Sub + Socket.IO + BullMQ events [office] [office] (598w)
- [[concepts/agentcorp-domain-model]] — Доменная модель: Company, Agent, Room, Task [office] (201w)
- [[concepts/bullmq-agent-workers]] — BullMQ для асинхронной обработки задач агентами [office] (219w)
- [[concepts/fastify-api-framework]] — Fastify как API-фреймворк: JSON Schema, TypeScript-first [office] (156w)
- [[concepts/pgvector-agent-memory]] — pgvector для long-term памяти агентов (RAG) [office] (220w)
- [[concepts/turborepo-monorepo]] — Turborepo + npm workspaces для monorepo AgentCorp [office] (159w)
- [[concepts/windows-path-issues]] — Проблемы пробелов в Windows-путях [office, memory-claude] (168w)
- [[entities/agentcorp]] — SaaS-платформа с AI-агентами (основной проект) [office] (119w)
- [[sources/agentcorp-architecture-notes]] — Архитектура AgentCorp: стек, сущности, решения, API design [office] (165w)

### (untagged)

- [[connections/cross-project-windows-paths]] — Windows-пути с пробелами ломают и TS project refs, и Claude hooks (138w)
- [[overview]] — Общий обзор и синтез всех знаний в вики (138w)

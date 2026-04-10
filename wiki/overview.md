---
title: Overview
type: overview
created: 2026-04-10
updated: 2026-04-10
sources: [raw/agentcorp-architecture-notes.md, daily/2026-04-10.md]
tags: [overview]
---

# Overview

Высокоуровневый синтез всех знаний в вики. Обновляется по мере добавления новых источников.

## Проекты

### [[entities/agentcorp|AgentCorp]] (Office)

SaaS-платформа с AI-агентами. Основной проект в работе.

- **Архитектура**: [[concepts/turborepo-monorepo|Turborepo monorepo]] → `apps/web` (Next.js 14) + `apps/api` ([[concepts/fastify-api-framework|Fastify]])
- **Домен**: 4 сущности — Company, Agent, Room, Task — см. [[concepts/agentcorp-domain-model]]
- **AI**: Claude API + [[concepts/pgvector-agent-memory|pgvector]] для long-term памяти агентов
- **Async**: [[concepts/bullmq-agent-workers|BullMQ]] — каждый агент как worker
- **Infra**: PostgreSQL, Redis, MinIO, Docker Compose

## Инструментарий

### [[concepts/llm-wiki-architecture|LLM Wiki]]

Эта wiki — глобальная база знаний для всех проектов. Два канала ввода: ручной ingest из `raw/` и автокомпиляция из Claude Code сессий (`daily/`).

### [[concepts/claude-code-hooks|Claude Code Hooks]]

Глобальные hooks для автоматического захвата знаний из каждой сессии. Работают в CLI и VS Code extension.

## Известные грабли

- [[concepts/windows-path-issues|Пробелы в Windows-путях]] ломают TS project references и hook-скрипты — [[connections/cross-project-windows-paths|cross-project impact]]

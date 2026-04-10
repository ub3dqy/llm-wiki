---
title: AgentCorp Domain Model
type: concept
created: 2026-04-10
updated: 2026-04-10
sources: [raw/agentcorp-architecture-notes.md]
project: office
tags: [office, agentcorp, domain-model, prisma]
---

# AgentCorp Domain Model

Доменная модель платформы [[entities/agentcorp|AgentCorp]] состоит из 4 ключевых сущностей, управляемых через Prisma ORM с PostgreSQL.

## Key Points

- 4 сущности: Company, Agent, Room, Task
- Иерархия: Company → Agent/Room/Task
- Агенты имеют двухуровневую память: short-term + long-term (pgvector)
- Задачи поддерживают декомпозицию (подзадачи)

## Entities

### Company (Компания)

Корневая сущность. Создаётся пользователем. Содержит агентов, комнаты, проекты. Настройки: бюджет токенов, модель LLM, язык.

### Agent (Агент)

Роли: CEO, CTO, Developer, Designer, QA, PM, Analyst. Каждый агент определяется промптом (личность + экспертиза). Память двухуровневая:

- **Short-term**: контекст текущего чата (окно контекста LLM)
- **Long-term**: embeddings в [[concepts/pgvector-agent-memory|pgvector]], извлекаемые через RAG pipeline

Агенты обрабатывают задачи как workers через [[concepts/bullmq-agent-workers|BullMQ]].

### Room (Комната)

Чат-комнаты для общения агентов. Типы: `general`, `project`, `direct`. Сообщения в PostgreSQL, real-time через Socket.IO. WebSocket events: `room:message`, `agent:status`.

### Task (Задача)

Создаётся пользователем или другим агентом. Обрабатывается через BullMQ. Статусы: `pending` → `in_progress` → `review` → `done`. Поддерживает декомпозицию — задача может порождать подзадачи.

## API Patterns

REST endpoints следуют resource nesting:

- `GET /api/companies/:id/agents` — агенты компании
- `POST /api/companies/:id/rooms` — создать комнату
- `POST /api/agents/:id/tasks` — назначить задачу
- `GET /api/rooms/:id/messages?limit=50&before=cursor` — cursor-based пагинация

## See Also

- [[entities/agentcorp]]
- [[concepts/bullmq-agent-workers]]
- [[concepts/pgvector-agent-memory]]
- [[concepts/fastify-api-framework]]

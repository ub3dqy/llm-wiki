---
title: AgentCorp
type: entity
created: 2026-04-10
updated: 2026-04-10
sources: [raw/agentcorp-architecture-notes.md]
project: office
tags: [office, agentcorp, saas, ai-agents]
---

# AgentCorp

SaaS-платформа, где пользователь создаёт виртуальную компанию из AI-агентов. Каждый агент имеет роль, личность, память и взаимодействует с другими агентами через чат-комнаты.

## Key Points

- Тип продукта: B2C SaaS с AI-first архитектурой
- Основная LLM: Claude API (Anthropic)
- Пользователь создаёт компанию → добавляет агентов с ролями → агенты общаются и выполняют задачи
- Доменная модель: Company → Agent, Room, Task — см. [[concepts/agentcorp-domain-model]]

## Tech Stack

- Frontend: Next.js 14 App Router, Tailwind + shadcn/ui, Socket.IO client
- Backend: [[concepts/fastify-api-framework|Fastify]], Socket.IO, [[concepts/bullmq-agent-workers|BullMQ]], Prisma
- AI/ML: Claude API, [[concepts/pgvector-agent-memory|pgvector]], RAG pipeline
- Infra: PostgreSQL, Redis, MinIO, Docker Compose, [[concepts/turborepo-monorepo|Turborepo]]

## Architecture

Подробная архитектура описана в [[sources/agentcorp-architecture-notes]].

## See Also

- [[sources/agentcorp-architecture-notes]]
- [[concepts/agentcorp-domain-model]]
- [[concepts/bullmq-agent-workers]]
- [[concepts/pgvector-agent-memory]]

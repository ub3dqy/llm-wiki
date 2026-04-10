---
title: "AgentCorp — Архитектурные заметки"
type: source
created: 2026-04-10
updated: 2026-04-10
sources: [raw/agentcorp-architecture-notes.md]
project: office
tags: [office, agentcorp, architecture, overview]
---

# AgentCorp — Архитектурные заметки (Source Summary)

Подробный документ с архитектурой SaaS-платформы AgentCorp, где пользователь создаёт виртуальную компанию из AI-агентов.

## Key Points

- Стек: Next.js 14 + [[concepts/fastify-api-framework|Fastify]] + Socket.IO + BullMQ + Prisma + PostgreSQL + Redis + MinIO
- 4 доменных сущности: Company, Agent, Room, Task — см. [[concepts/agentcorp-domain-model]]
- AI: Claude API как основная LLM, pgvector для памяти агентов — см. [[concepts/pgvector-agent-memory]]
- Асинхронная обработка через [[concepts/bullmq-agent-workers|BullMQ]] — каждый агент = worker
- Монорепо через [[concepts/turborepo-monorepo|Turborepo]] + npm workspaces
- REST API с cursor-based пагинацией + WebSocket events для real-time

## Architecture Decisions

| Решение  | Альтернатива             | Обоснование                                                 |
| -------- | ------------------------ | ----------------------------------------------------------- |
| BullMQ   | Прямые вызовы Claude API | Retry, rate limiting, приоритизация, мониторинг             |
| pgvector | Pinecone/Weaviate        | Экономия инфры, достаточная производительность для масштаба |
| MinIO    | AWS S3                   | Локальная разработка, S3-совместимый — легко переключить    |

## See Also

- [[concepts/agentcorp-domain-model]]
- [[concepts/bullmq-agent-workers]]
- [[concepts/pgvector-agent-memory]]
- [[concepts/fastify-api-framework]]
- [[concepts/turborepo-monorepo]]
- [[entities/agentcorp]]

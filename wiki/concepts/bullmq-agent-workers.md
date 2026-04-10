---
title: BullMQ Agent Workers
type: concept
created: 2026-04-10
updated: 2026-04-10
sources: [raw/agentcorp-architecture-notes.md]
project: office
tags: [office, agentcorp, bullmq, redis, async, queue]
---

# BullMQ Agent Workers

В [[entities/agentcorp|AgentCorp]] каждый AI-агент реализован как BullMQ worker. Это ключевое архитектурное решение — агенты работают асинхронно через очереди, а не через прямые синхронные вызовы Claude API.

## Key Points

- Каждый агент = отдельный BullMQ worker с собственным concurrency
- Backend: Redis (shared с кэшированием)
- Преимущества: retry при ошибках API, rate limiting, приоритизация, мониторинг очередей
- Пользователь не ждёт ответа в реальном времени — результат приходит через WebSocket

## Details

### Почему не прямые вызовы Claude API

Прямой вызов Claude API из request handler означает: пользователь висит на HTTP-запросе пока агент думает (10-30 секунд). При ошибке API — пользователь получает 500. При rate limit — потерянный запрос.

BullMQ решает все эти проблемы:

- **Retry**: автоматический повтор при 429/500 от Claude API с exponential backoff
- **Rate limiting**: глобальный лимит на запросы к API, предотвращает блокировку аккаунта
- **Приоритизация**: CEO-агент может быть приоритетнее QA-агента
- **Мониторинг**: dashboard для отслеживания состояния очередей и задач
- **Concurrency**: каждый агент имеет настраиваемый параллелизм

### Поток данных

1. Пользователь или агент создаёт Task (через REST API)
2. Task помещается в BullMQ queue
3. Worker (агент) забирает Task из очереди
4. Worker вызывает Claude API с контекстом из [[concepts/pgvector-agent-memory|памяти агента]]
5. Результат сохраняется в PostgreSQL
6. WebSocket event `task:update` уведомляет клиент

## See Also

- [[concepts/agentcorp-domain-model]]
- [[concepts/pgvector-agent-memory]]
- [[entities/agentcorp]]

---
title: pgvector Agent Memory
type: concept
created: 2026-04-10
updated: 2026-04-10
sources: [raw/agentcorp-architecture-notes.md]
project: office
tags: [office, agentcorp, pgvector, embeddings, rag, memory]
---

# pgvector Agent Memory

Каждый агент в [[entities/agentcorp|AgentCorp]] имеет двухуровневую память. Long-term память реализована через pgvector — расширение PostgreSQL для хранения и поиска по vector embeddings.

## Key Points

- Short-term: контекст текущего чата (окно контекста Claude API)
- Long-term: embeddings в pgvector, извлекаемые через RAG pipeline
- Выбор pgvector вместо отдельной vector DB (Pinecone/Weaviate) — экономия инфраструктуры
- Масштаб: тысячи, не миллионы векторов на компанию — pgvector справляется

## Details

### Архитектура памяти

Двухуровневая система памяти агентов:

1. **Short-term memory** — последние N сообщений из чат-комнаты (Room). Загружаются напрямую в контекст Claude API при каждом вызове. Ограничены окном контекста модели.

2. **Long-term memory** — все значимые факты, решения, контекст из прошлых разговоров. Хранятся как vector embeddings в pgvector. При генерации ответа агент выполняет RAG-запрос: embedding текущего вопроса → similarity search по pgvector → top-K результатов добавляются в контекст.

### Почему pgvector а не отдельная vector DB

Ключевой trade-off: **инфраструктурная простота vs. масштабируемость**.

PostgreSQL уже используется как основная БД для всех данных AgentCorp. Добавление pgvector — это `CREATE EXTENSION vector`, а не развёртывание отдельного сервиса. Для масштаба платформы (тысячи векторов на компанию, десятки компаний) производительности достаточно.

При росте до сотен тысяч компаний с миллионами векторов — миграция на Pinecone или Weaviate с минимальными изменениями в коде (абстракция на уровне repository layer).

## See Also

- [[concepts/agentcorp-domain-model]]
- [[concepts/bullmq-agent-workers]]
- [[entities/agentcorp]]

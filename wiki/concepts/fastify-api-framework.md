---
title: Fastify API Framework
type: concept
created: 2026-04-10
updated: 2026-04-10
sources: [daily/2026-04-10.md]
project: office
tags: [office, fastify, api, typescript]
---

# Fastify API Framework

Fastify выбран как API-фреймворк для `apps/api` в проекте AgentCorp вместо Express.

## Key Points

- Встроенная валидация через JSON Schema — не нужны дополнительные библиотеки
- Лучшая производительность по сравнению с Express
- TypeScript-first подход — типы из коробки
- Используется в monorepo на базе [[concepts/turborepo-monorepo|Turborepo]]

## Details

Основные причины выбора Fastify: встроенная валидация запросов через JSON Schema (не нужен отдельный Zod/Joi middleware), значительно лучшая производительность по сравнению с Express, и нативная поддержка TypeScript.

В контексте AgentCorp API-сервер (`apps/api`) является частью [[concepts/turborepo-monorepo|Turborepo monorepo]] и будет использовать Prisma с PostgreSQL для работы с данными. В планах — подключение Docker Compose для локальной разработки (postgres, redis, minio).

## See Also

- [[concepts/turborepo-monorepo]]
- [[concepts/windows-path-issues]]

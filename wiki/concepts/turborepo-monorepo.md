---
title: Turborepo Monorepo
type: concept
created: 2026-04-10
updated: 2026-04-10
sources: [daily/2026-04-10.md]
project: office
tags: [office, monorepo, turborepo, npm-workspaces]
---

# Turborepo Monorepo

Turborepo — инструмент для управления monorepo, выбранный для проекта AgentCorp (Office). Используется в связке с npm workspaces для организации SaaS-платформы с AI-агентами.

## Key Points

- Структура: `apps/web` (Next.js 14), `apps/api` ([[concepts/fastify-api-framework|Fastify]]), `packages/shared`
- Менеджер зависимостей: npm workspaces (не pnpm) — нативная поддержка в Next.js, меньше конфигурации
- Shared-пакеты: `@agentcorp/ui` (shadcn), `@agentcorp/config` (ESLint/TS), `@agentcorp/types`
- Pipeline в `turbo.json`: build → lint → typecheck → test

## Details

Выбор npm workspaces вместо pnpm обусловлен совместимостью с Turborepo из коробки и нативной поддержкой в Next.js. Это снижает количество необходимой конфигурации при сохранении всех преимуществ monorepo-подхода.

Важная деталь pipeline-конфигурации: символ `^` в `^build` означает "сначала выполнить build зависимых пакетов". Без `^` tasks будут запущены параллельно, что может привести к ошибкам, если один пакет зависит от build-артефактов другого.

TypeScript project references в monorepo требуют осторожности на Windows — пути с пробелами ломают `tsconfig.json`. Рекомендуется использовать relative paths без пробелов или symlinks. См. [[concepts/windows-path-issues]].

## See Also

- [[concepts/fastify-api-framework]]
- [[concepts/windows-path-issues]]

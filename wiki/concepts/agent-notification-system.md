---
title: Agent Notification System
type: concept
created: 2026-04-11
updated: 2026-04-11
sources: [conversation, raw/agentcorp-architecture-notes.md]
project: office
tags: [office, agentcorp, notifications, websocket, bullmq, socket-io, redis]
---

# Agent Notification System

Архитектура системы уведомлений для AI-агентов в [[entities/agentcorp|AgentCorp]]. Уведомления позволяют агентам "знать" о событиях, произошедших пока они не работали, и реагировать на них при следующем запуске. Построена поверх существующего стека: BullMQ + Socket.IO + PostgreSQL.

## Key Points

- Новая Prisma-модель `Notification` с типами: task, mention, system, collaboration
- 3-слойная архитектура: Producers → NotificationService → Consumers
- Уведомления инжектятся в prompt агента как контекст при старте задачи
- Real-time доставка через существующий Socket.IO (event `notification:new`)
- Critical-уведомления через отдельную BullMQ очередь `notifications:critical`
- Не требует нового инфра-компонента — всё на Redis + PostgreSQL

## Details

### Типы уведомлений

| Тип               | Пример                                          | Приоритет |
| ----------------- | ----------------------------------------------- | --------- |
| **task**          | Задача назначена / завершена / требует review   | high      |
| **mention**       | Агент упомянут в Room-сообщении (`@CTO`)        | medium    |
| **system**        | Rate limit, ошибка API, бюджет токенов исчерпан | critical  |
| **collaboration** | Агент просит помощь у другого агента            | medium    |

### Prisma-модель

```prisma
model Notification {
  id            String           @id @default(cuid())
  type          NotificationType // task | mention | system | collaboration
  priority      Priority         // critical | high | medium | low
  payload       Json             // произвольные данные (taskId, roomId, message...)
  agentId       String           // получатель
  agent         Agent            @relation(fields: [agentId], references: [id])
  sourceAgentId String?          // кто инициировал (null для system)
  companyId     String           // scope компании
  company       Company          @relation(fields: [companyId], references: [id])
  readAt        DateTime?        // null = непрочитано
  createdAt     DateTime         @default(now())

  @@index([agentId, readAt])     // быстрый query непрочитанных
  @@index([companyId, createdAt])
}
```

### Архитектура (3 слоя)

**Producers** (источники):

- BullMQ worker: при завершении/провале task генерирует notification
- Room message parser: @mention в тексте сообщения (`@CTO`, `@Designer`)
- System monitor: rate limit, ошибки API, бюджет токенов

**NotificationService** (ядро, Fastify):

- `create()` — сохраняет в PostgreSQL + emit Socket.IO event
- `markRead()` / `readAll()` — обновление readAt
- `getUnread(agentId)` — для инъекции в контекст агента
- `dispatch()` — решает: обработать немедленно или в очередь

**Consumers**:

- Frontend: Socket.IO `notification:new` → UI badge/toast
- Agent Worker: подтягивает unread при старте задачи как доп. контекст в prompt
- BullMQ очередь `notifications:critical`: немедленная реакция на critical events

### Уведомления как контекст агента

Ключевая идея: при старте обработки Task worker вызывает `getUnread(agentId)` и инжектит результат в system prompt. Агент "видит" что произошло:

- "CTO запросил ревью задачи X"
- "Designer завершил макет Y"
- "Бюджет токенов компании на 80%"

После обработки уведомления помечаются как прочитанные.

### Поток данных

1. Событие (BullMQ job completed / агент решил уведомить / @mention в Room)
2. `NotificationService.create()` — INSERT в PostgreSQL
3. Socket.IO emit `notification:new` подписчикам (frontend real-time)
4. При старте следующей задачи — worker подтягивает unread в prompt

### API Endpoints

```
GET    /api/agents/:id/notifications?unread=true&limit=20
POST   /api/agents/:id/notifications/:nid/read
POST   /api/agents/:id/notifications/read-all
DELETE /api/agents/:id/notifications/:nid
```

Следует паттерну resource nesting из [[concepts/agentcorp-domain-model|доменной модели]].

### Ключевые компоненты

| Компонент             | Расположение      | Назначение                                     |
| --------------------- | ----------------- | ---------------------------------------------- |
| `NotificationService` | `packages/shared` | CRUD уведомлений, dispatch logic               |
| BullMQ event listener | `apps/api`        | Генерация уведомлений при `completed`/`failed` |
| Socket.IO handler     | `apps/api`        | Push `notification:new` подписчикам            |
| REST endpoints        | `apps/api`        | CRUD + read/read-all                           |
| NotificationPanel     | `apps/web`        | UI с badge-счётчиком и списком                 |

### Что НЕ нужно

- Отдельный микросервис — уведомления часть core domain
- Kafka/RabbitMQ — Redis + BullMQ достаточно для масштаба
- Push-уведомления (FCM/APNs) — web SaaS, WebSocket достаточно
- Email-дайджесты — можно добавить позже как отдельный consumer, не меняя ядро

### Фазировка

NotificationService стоит заложить вместе с BullMQ workers (Agent Runtime), чтобы избежать рефакторинга обработчиков задач позже.

## See Also

- [[concepts/bullmq-agent-workers]]
- [[concepts/agentcorp-domain-model]]
- [[concepts/pgvector-agent-memory]]
- [[concepts/fastify-api-framework]]
- [[entities/agentcorp]]

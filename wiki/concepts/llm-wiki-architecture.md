---
title: LLM Wiki Architecture
type: concept
created: 2026-04-10
updated: 2026-04-11
sources: [daily/2026-04-10.md, daily/2026-04-11.md]
project: memory-claude
tags: [knowledge-management, wiki, llm, architecture, key-insight]
---

# LLM Wiki Architecture

Архитектура глобальной базы знаний, объединяющая ручной ingest (Karpathy's LLM Wiki), автоматическую компиляцию из сессий (coleam00/claude-memory-compiler), и **реактивный инжект знаний** через 6 Claude Code хуков.

## Key Points

- Два входных канала: ручной ingest (`raw/` → `wiki/sources/`) и авто-захват (`daily/` → `wiki/concepts/`)
- Третий канал: `/wiki-save` скилл для мгновенного сохранения из любого проекта
- 6 хуков обеспечивают полный цикл: захват → компиляция → инжект → напоминание
- Реактивный инжект: UserPromptSubmit подгружает статьи по теме конкретного промпта
- Обогащённый index с `[project] (Nw)` аннотациями и секцией By Project
- seed.py для ретроспективного наполнения wiki из существующих проектов

## Details

### Три волны развития

**Волна 1 (базовая):** Объединение Karpathy + coleam00. Три хука (SessionStart, SessionEnd, PreCompact), flush.py + compile.py через Agent SDK, lint с 7 проверками.

**Волна 1.5 (стабилизация):** Concurrency control (file locks, debounce), index-guided compile/query (вместо full dump), обогащённый index, проектный контекст в SessionStart, секция Recent Changes.

**Волна 2 (реактивная):** UserPromptSubmit (точечный инжект), PostToolUse async (real-time захват), Stop hook (напоминание), seed.py, wiki_cli.py, /wiki-save скилл.

### Полный цикл знаний

```
Захват:  SessionEnd → flush.py → daily/ (конец сессии)
         PreCompact → flush.py → daily/ (перед сжатием)
         PostToolUse → micro-entry → daily/ (git commit, test run)
         /wiki-save → wiki/ (мгновенный, из любого проекта)

Компиляция: compile.py → daily/ → wiki/concepts/, wiki/connections/
            rebuild_index.py → index.md с [project] (Nw) + By Project
            Авто-триггер после 18:00

Инжект:  SessionStart → wiki index + проектные статьи + recent changes
         UserPromptSubmit → статьи по ключевым словам промпта

Напоминание: Stop hook → systemMessage при архитектурных решениях
```

### Масштабирование

| Статей | Стратегия | Статус |
|---|---|---|
| 0-50 | Полный index в SessionStart | Текущий |
| 50-500 | Index + UserPromptSubmit точечный инжект | Текущий |
| 500-2000 | Категорийные под-индексы | Запланировано |
| 2000+ | Гибридный RAG (embeddings + index) | Будущее |

### Скрипты

| Скрипт | Назначение |
|---|---|
| `flush.py` | Оценка ценности разговора через Agent SDK → daily log |
| `compile.py` | Компиляция daily → wiki статьи через Agent SDK |
| `query.py` | Поиск по wiki с опциональным file-back в qa/ |
| `lint.py` | 7 health checks (broken links, orphans, stale, sparse, contradictions) |
| `rebuild_index.py` | Обогащение index [project] (Nw) + By Project секция |
| `seed.py` | Ретроспективное наполнение wiki из проекта |
| `wiki_cli.py` | Unified CLI (status, compile, query, lint, rebuild, seed) |

## See Also

- [[concepts/claude-code-hooks]]
- [[concepts/uv-python-tooling]]
- [[concepts/windows-path-issues]]

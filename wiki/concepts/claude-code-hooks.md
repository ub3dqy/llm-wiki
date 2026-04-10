---
title: Claude Code Hooks
type: concept
created: 2026-04-10
updated: 2026-04-11
sources: [daily/2026-04-10.md, daily/2026-04-11.md]
project: memory-claude
tags: [claude-code, hooks, automation, knowledge-capture, key-insight]
---

# Claude Code Hooks

Механизм хуков Claude Code позволяет выполнять произвольные скрипты при определённых событиях сессии. В LLM Wiki используется **6 хуков** для автоматического захвата и инжекта знаний.

## Key Points

- **6 хуков**: SessionStart, SessionEnd, PreCompact, UserPromptSubmit, PostToolUse (async), Stop
- Хуки настраиваются глобально в `~/.claude/settings.json` — работают для всех проектов
- Одинаково работают в CLI, VS Code и JetBrains
- `additionalContext` поддерживается только в SessionStart, UserPromptSubmit, PostToolUse (не в PreCompact/PostCompact/Stop)
- Concurrency control: file locks + debounce для предотвращения каскадного спавна

## Details

### Все 6 хуков

| Хук | Когда | Что делает | additionalContext |
|---|---|---|---|
| **SessionStart** | Начало сессии | Инжектит wiki index + проектный контекст + recent changes | Да |
| **SessionEnd** | Конец сессии | Захват transcript → flush.py → daily log | Нет (observability) |
| **PreCompact** | Перед сжатием | Захват transcript → flush.py (safety net) | Нет |
| **UserPromptSubmit** | Перед каждым промптом | Поиск wiki-статей по ключевым словам промпта → инжект | Да |
| **PostToolUse** | После Bash (async) | Захват git commit, test run как micro-entries в daily log | Да (не используем) |
| **Stop** | После каждого ответа | Напоминание о /wiki-save при архитектурных решениях | Нет (systemMessage) |

### SessionStart — проектный контекст

Читает `cwd` из stdin, определяет проект, и формирует контекст:
1. Wiki-first инструкции (MANDATORY)
2. Проектные статьи (если проект распознан по тегу `project:`)
3. Recent Wiki Changes (последние 48 часов)
4. Полный wiki index
5. Последний daily log

Бюджет: ~7K из 10K символов. Лимит `additionalContext` — 10,000 символов.

### UserPromptSubmit — точечный инжект

Парсит текст промпта пользователя, извлекает ключевые слова, ищет совпадения с wiki-статьями по title/tags/slug. Инжектит top-3 статьи (max 4000 символов) через `additionalContext`. Timeout: 5 секунд, без API-вызовов.

### Concurrency и защита от каскадов

Без ограничений, завершение множества сессий одновременно порождает сотни node.exe (каждый flush.py → Agent SDK → bundled claude.exe). Решение:
- **File locks** в flush.py: максимум 2 одновременных flush-процесса
- **Debounce** в session-end.py и pre-compact.py: минимум 10 секунд между спавнами
- **Stale lock cleanup**: locks старше 120 секунд автоматически удаляются
- **Recursion guard**: переменная `CLAUDE_INVOKED_BY` предотвращает бесконечный цикл

### Проверенные ограничения hook output

| Хук | hookSpecificOutput + additionalContext | systemMessage | decision: block |
|---|---|---|---|
| SessionStart | Да | — | — |
| SessionEnd | Нет | — | — |
| PreCompact | **Нет** (валидация отклоняет) | Да | Нет |
| PostCompact | **Нет** | Да | Нет |
| UserPromptSubmit | Да | Да | Да (exit 2) |
| PostToolUse | Да | Да | Feedback only |
| Stop | **Нет** | Да | Да |

## See Also

- [[concepts/llm-wiki-architecture]]
- [[concepts/uv-python-tooling]]
- [[concepts/windows-path-issues]]

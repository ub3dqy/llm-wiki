---
title: Claude Code Hooks
type: concept
created: 2026-04-10
updated: 2026-04-10
sources: [daily/2026-04-10.md]
project: memory-claude
tags: [claude-code, hooks, automation, knowledge-capture]
---

# Claude Code Hooks

Механизм хуков Claude Code позволяет выполнять произвольные скрипты при определённых событиях сессии. Используется для автоматического захвата знаний в [[concepts/llm-wiki-architecture|LLM Wiki]].

## Key Points

- Три типа хуков: `SessionStart`, `SessionEnd`, `PreCompact`
- `SessionStart` возвращает `additionalContext` через JSON stdout — до 10K символов
- `SessionEnd` и `PreCompact` получают `transcript_path` через stdin
- Хуки настраиваются глобально в `~/.claude/settings.json` — работают для всех проектов
- Одинаково работают в CLI и VS Code extension

## Details

Хуки настроены глобально и обеспечивают автоматический захват знаний из каждой сессии Claude Code. `SessionStart` инжектит контекст wiki (индекс + последние записи daily log) в начало каждой сессии, давая Claude актуальный контекст базы знаний.

`SessionEnd` и `PreCompact` запускают `flush.py` в фоне после завершения сессии или перед компактификацией контекста. Скрипт использует [[concepts/uv-python-tooling|Claude Agent SDK]] для оценки ценности разговора и при необходимости сохраняет структурированное резюме в `daily/`.

Критически важен recursion guard: без проверки переменной `CLAUDE_INVOKED_BY` возникает бесконечный цикл — `flush.py` вызывает Agent SDK, который запускает Claude Code, что триггерит hook, который снова вызывает `flush.py`. При настройке хуков с путями, содержащими пробелы, необходимо использовать escaped quotes. См. [[concepts/windows-path-issues]].

## See Also

- [[concepts/llm-wiki-architecture]]
- [[concepts/uv-python-tooling]]
- [[concepts/windows-path-issues]]

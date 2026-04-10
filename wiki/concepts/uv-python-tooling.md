---
title: uv Python Tooling
type: concept
created: 2026-04-10
updated: 2026-04-10
sources: [daily/2026-04-10.md]
project: memory-claude
tags: [python, uv, tooling, claude-agent-sdk]
---

# uv Python Tooling

uv — быстрый Python-пакетный менеджер, используемый для управления зависимостями скриптов [[concepts/llm-wiki-architecture|LLM Wiki]].

## Key Points

- Используется как пакетный менеджер и runner (`uv run python scripts/...`)
- Автоматически выбирает подходящую версию Python из установленных
- `claude-agent-sdk` требует Python >=3.12 — uv обеспечивает это автоматически
- Выбран вместо Node.js для скриптов wiki — Python лучше подходит для данных задач

## Details

uv обеспечивает быструю установку зависимостей и управление виртуальными окружениями. Ключевое преимущество — автоматический выбор подходящей версии Python, что критически важно для `claude-agent-sdk`, требующего Python 3.12+.

В LLM Wiki uv управляет четырьмя основными скриптами: `flush.py` (извлечение инсайтов из сессий), `compile.py` (компиляция daily logs в wiki-статьи), `query.py` (поиск по базе знаний), `lint.py` (проверка здоровья wiki). Все скрипты запускаются через `uv run python scripts/<name>.py`. Конфигурация зависимостей хранится в `pyproject.toml`.

Решение использовать Python-стек вместо Node.js было осознанным — Python лучше интегрируется с claude-agent-sdk и ML/NLP-экосистемой.

## See Also

- [[concepts/llm-wiki-architecture]]
- [[concepts/claude-code-hooks]]

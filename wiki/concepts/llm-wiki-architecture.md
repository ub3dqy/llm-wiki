---
title: LLM Wiki Architecture
type: concept
created: 2026-04-10
updated: 2026-04-10
sources: [daily/2026-04-10.md]
project: memory-claude
tags: [knowledge-management, wiki, llm, architecture, key-insight]
---

# LLM Wiki Architecture

Архитектура глобальной базы знаний, объединяющая два подхода: ручной ingest (паттерн Andrej Karpathy's LLM Wiki) и автоматическую компиляцию из сессий (coleam00/claude-memory-compiler).

## Key Points

- Два входных канала: ручной ingest (`raw/` → `wiki/sources/`) и авто-захват (`daily/` → `wiki/concepts/`)
- Единая `wiki/` директория — оба канала пишут в одно место
- Расположение: отдельное git-репо, не внутри проектов
- Автоматизация через [[concepts/claude-code-hooks|Claude Code Hooks]] — глобальные для всех проектов
- Python-стек: [[concepts/uv-python-tooling|uv]] + claude-agent-sdk

## Details

Ключевое архитектурное решение — объединение двух паттернов управления знаниями в единую систему. Karpathy's LLM Wiki предлагает ручной ingest внешних документов с созданием структурированных summary-страниц. Memory Compiler добавляет автоматический захват инсайтов из рабочих сессий через хуки Claude Code.

Вики расположена в отдельном git-репозитории (`E:\Project\memory claude\memory claude\`), а не внутри конкретных проектов. Это позволяет накапливать знания кросс-проектно — хуки настроены глобально и захватывают знания из любого проекта. Каждая запись в wiki помечается тегом `project:` для отслеживания происхождения.

Скрипты (`flush.py`, `compile.py`, `query.py`, `lint.py`) написаны на Python с использованием uv как пакетного менеджера и claude-agent-sdk для LLM-вызовов. Решено не портировать на Node.js — Python-стек лучше подходит для данного типа задач.

## See Also

- [[concepts/claude-code-hooks]]
- [[concepts/uv-python-tooling]]

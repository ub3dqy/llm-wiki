---
title: Windows Path Issues — Cross-Project Impact
type: connection
created: 2026-04-10
updated: 2026-04-10
sources: [daily/2026-04-10.md]
connects: [concepts/windows-path-issues, concepts/turborepo-monorepo, concepts/claude-code-hooks]
tags: [windows, cross-cutting, troubleshooting]
---

# Windows Path Issues — Cross-Project Impact

Неочевидная связь: проблема пробелов в Windows-путях проявляется одинаково в двух независимых контекстах — TypeScript monorepo и Claude Code hooks — с разными симптомами, но общей причиной.

## Connection

В один день (2026-04-10) зафиксированы две независимые проблемы с пробелами в путях:

1. **[[concepts/turborepo-monorepo]]**: TypeScript project references не резолвят пути с пробелами → ошибки сборки
2. **[[concepts/claude-code-hooks]]**: пути к скриптам в `settings.json` требуют escaped quotes → хуки не запускаются

Обе проблемы имеют общий корень: Unix-ориентированный тулинг некорректно обрабатывает пробелы в Windows-путях. Это паттерн, который стоит учитывать при выборе расположения любого проекта на Windows.

## Implication

При создании новых проектов или конфигурационных файлов на Windows следует избегать пробелов в путях. Для существующих путей с пробелами — использовать symlinks или escaped quotes в зависимости от инструмента.

## See Also

- [[concepts/windows-path-issues]]
- [[concepts/turborepo-monorepo]]
- [[concepts/claude-code-hooks]]

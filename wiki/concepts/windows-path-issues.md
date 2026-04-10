---
title: Windows Path Issues
type: concept
created: 2026-04-10
updated: 2026-04-10
sources: [daily/2026-04-10.md]
project: office, memory-claude
tags: [windows, paths, troubleshooting]
---

# Windows Path Issues

Проблемы с путями, содержащими пробелы, на Windows — повторяющийся паттерн, затрагивающий различные инструменты разработки.

## Key Points

- TypeScript project references в `tsconfig.json` ломаются при наличии пробелов в пути
- Решение для TS: использовать relative paths без пробелов или symlinks
- [[concepts/claude-code-hooks|Claude Code Hooks]]: пути с пробелами нужно оборачивать в escaped quotes (`\"path with spaces\"`)
- Проблема затрагивает минимум два проекта: [[concepts/turborepo-monorepo|AgentCorp monorepo]] и [[concepts/llm-wiki-architecture|LLM Wiki]]

## Details

Пробелы в путях Windows — частый источник проблем при работе с инструментами разработки, изначально созданными для Unix-подобных систем. В контексте TypeScript monorepo project references не могут корректно резолвить пути с пробелами, что приводит к ошибкам сборки.

Аналогичная проблема возникает при настройке глобальных Claude Code хуков — при указании пути к скрипту в `settings.json` необходимо использовать escaped double quotes для путей с пробелами. Это важно учитывать, т.к. wiki-репозиторий расположен по пути с пробелами (`E:\Project\memory claude\memory claude\`).

Общая рекомендация: по возможности избегать пробелов в путях проектов, или использовать symlinks как workaround.

## See Also

- [[concepts/turborepo-monorepo]]
- [[concepts/claude-code-hooks]]

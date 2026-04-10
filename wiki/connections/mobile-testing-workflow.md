---
title: Mobile Testing Workflow — ADB + Claude Code
type: connection
created: 2026-04-11
updated: 2026-04-11
sources: [daily/2026-04-11.md]
project: messenger
tags: [messenger, testing, adb, claude-code, connection]
---

# Mobile Testing Workflow — ADB + Claude Code

Связь между [[concepts/flutter-adb-testing|ограничениями Flutter ADB]] и [[concepts/claude-code-context-limits|лимитами контекста Claude Code]] — обе проблемы проявляются при одном workflow: тестирование мобильного приложения через ADB со скриншотами в Claude Code.

## Connection

Тестирование [[entities/pulse-messenger|Pulse Messenger]] на физических устройствах через ADB с помощью Claude Code выявило два пересекающихся ограничения:

1. **ADB + Flutter несовместимость** → невозможно вводить текст через `adb shell input text` → приходится делать больше скриншотов для диагностики
2. **Скриншоты переполняют контекст** → сессия Claude Code блокируется → теряется прогресс тестирования

Эти проблемы усиливают друг друга: невозможность автоматизировать ввод текста увеличивает количество ручных действий и скриншотов, что быстрее забивает контекст. Решение — комбинированный подход:

- **API-first тестирование**: [[concepts/pulse-testing-methodology|авторизация и создание чатов через REST API]], устройства — только для проверки UI
- **Превентивный `/compact`**: каждые 5-8 скриншотов
- **Сохранение промежуточных результатов в файл**: координаты, баги, статусы — в текстовый файл для устойчивости к compaction

Этот паттерн вероятно применим к любому Flutter-приложению, тестируемому через ADB в Claude Code, не только к Pulse.

## See Also

- [[concepts/flutter-adb-testing]]
- [[concepts/claude-code-context-limits]]
- [[concepts/pulse-testing-methodology]]
- [[entities/pulse-messenger]]

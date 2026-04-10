---
title: Claude Code Context Limits
type: concept
created: 2026-04-11
updated: 2026-04-11
sources: [daily/2026-04-11.md]
project: memory-claude
tags: [claude-code, context, screenshots, compact, key-insight]
---

# Claude Code Context Limits

Стратегии управления контекстным окном Claude Code при работе с большим количеством изображений (скриншотов ADB). Обнаружено при тестировании [[entities/pulse-messenger|Pulse Messenger]].

## Key Points

- **Ошибка "exceeds dimension limit for many-image requests (2000px)"** полностью блокирует сессию — Claude не может сгенерировать ни один ответ
- **Превентивный `/compact` обязателен**: не ждать ошибку, а делать `/compact` каждые 5-8 скриншотов
- **Continuation summary** — эффективный механизм восстановления после переполнения контекста
- При восстановлении через summary сохраняются все ключевые данные: координаты UI, состояние устройств, карта багов, план тестирования

## Details

### Проблема

При тестировании мобильных приложений через ADB каждый скриншот (`adb exec-out screencap -p`) добавляется в контекст как изображение. После накопления достаточного количества изображений Claude Code выдаёт ошибку dimension limit, после чего **полностью блокируется** — невозможно ни ответить на вопрос, ни выполнить инструмент. Сессия фактически "мертва" до выполнения `/compact`.

### Стратегия управления

1. **Превентивный `/compact`**: выполнять каждые 5-8 скриншотов, не дожидаясь ошибки
2. **Сохранение результатов в файл**: при длительном тестировании записывать промежуточные результаты (координаты, баги, статусы) в текстовый файл, чтобы не терять данные при compaction
3. **Continuation summary**: при переполнении использовать `/compact` + продолжение — summary механизм сохраняет контекст тестирования

### Связь с PreCompact hook

[[concepts/claude-code-hooks|Claude Code hooks]] включают PreCompact hook для автозахвата знаний перед compaction. Обнаружена проблема валидации: `hookEventName: "PreCompact"` использует `hookSpecificOutput`, но валидная JSON-схема ожидает только `PreToolUse`, `UserPromptSubmit`, `PostToolUse` как hookEventName для hookSpecificOutput. Для PreCompact нужно использовать `systemMessage` вместо `hookSpecificOutput`.

## See Also

- [[concepts/claude-code-hooks]]
- [[concepts/flutter-adb-testing]]
- [[concepts/llm-wiki-architecture]]

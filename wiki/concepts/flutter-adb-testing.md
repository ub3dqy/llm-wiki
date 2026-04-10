---
title: Flutter ADB Testing Limitations
type: concept
created: 2026-04-11
updated: 2026-04-11
sources: [daily/2026-04-11.md]
project: messenger
tags: [messenger, flutter, adb, testing, android, key-insight]
---

# Flutter ADB Testing Limitations

Набор проблем и ограничений при автоматизированном тестировании Flutter-приложений через ADB на физических Android-устройствах. Обнаружены при тестировании [[entities/pulse-messenger|Pulse Messenger]] на OnePlus и Samsung.

## Key Points

- **ADB `input text` не работает с Flutter TextField** — текст исчезает при потере фокуса. Это блокирует любое ADB-автоматизированное UI-тестирование полей ввода во Flutter
- Символ `+` в номере телефона может не пройти через ADB input (URL-encoding проблемы)
- Координаты UI-элементов различаются между устройствами — пропорциональный пересчёт даёт лишь приблизительный результат
- Тап по чекбоксу ненадёжен при открытой клавиатуре — нужно сначала скрыть клавиатуру (Back)
- Samsung Android 13 специфичные проблемы: hiddenapi denied для BackEvent, FlutterRenderer width=zero

## Details

### Несовместимость ADB input text и Flutter TextField

Ключевая проблема: при использовании `adb shell input text` для ввода текста в Flutter TextField, введённый текст **исчезает при потере фокуса полем**. Это означает, что автоматизированный ввод текста через стандартные ADB-команды невозможен для Flutter-приложений. Проблема подтверждена как минимум на Samsung (Android 13), но может затрагивать и другие устройства.

Возможные альтернативы для исследования: `adb shell ime` (переключение метода ввода), Appium (фреймворк для мобильной автоматизации). До нахождения решения — обходной путь через прямые API-вызовы к серверу, минуя Flutter UI. См. [[concepts/pulse-testing-methodology]].

### Пересчёт координат между устройствами

При тестировании на нескольких устройствах с разными разрешениями координаты UI-элементов нужно пересчитывать. Пропорциональный пересчёт (например, OnePlus 1440x3216 → Samsung 720x1600) даёт **приблизительное** значение, но не точное. Чекбокс на OnePlus (y≈2050) пересчитывается на Samsung как y≈1020 по пропорции, но реальная координата оказалась y=900.

Подтверждённые координаты нижних табов (Чаты/Обновления/Контакты/Звонки/Профиль) на OnePlus (1440x3216): y≈3100-3150, x распределены равномерно (144, 432, 720, 1008, 1296).

### Samsung-специфичные проблемы

На Samsung Android 13 обнаружены дополнительные проблемы:
- **S1-1**: холодный запуск занимает 19 секунд (Medium severity)
- **S1-2**: `hiddenapi denied` для BackEvent — системное ограничение Samsung (Medium)
- **S1-3**: FlutterRenderer Width is zero при инициализации (Low)

## See Also

- [[entities/pulse-messenger]]
- [[concepts/flutter-go-messenger-architecture]]
- [[concepts/pulse-testing-methodology]]

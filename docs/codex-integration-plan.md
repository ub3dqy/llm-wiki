# План: Интеграция LLM Wiki с OpenAI Codex CLI (v3.2 — финальный)

> **Этот план прошёл четыре раунда аудита Codex CLI агентом** и исправлен по результатам сверки с официальной документацией OpenAI.
> - **v1 → v2**: 8 критических ошибок (stdin format, tool_name, AGENTS.md, Windows, async, matcher, version check)
> - **v2 → v3**: 8 уточнений (полные schemas, формулировки, cwd, nullable, skills, generated schemas)
> - **v3 → v3.1**: 3 финальные правки (matcher default, Stop реализация, совместимость disclaimer)
> - **v3.1 → v3.2**: 3 правки (schema-команда, WSL-блокер, README checklist)

## Контекст

У нас есть работающая LLM Wiki с 6 хуками для Claude Code (24 статьи, 3 проекта). Цель — добавить поддержку Codex CLI, чтобы **оба агента** читали и писали в одну wiki.

### Источники (официальные)

- **Hooks – Codex**: https://developers.openai.com/docs/codex/hooks — lifecycle hooks, config, event semantics
- **AGENTS.md – Codex**: https://developers.openai.com/docs/codex/agents-md — global/project instruction layering
- **Advanced Configuration**: https://developers.openai.com/docs/codex/advanced-configuration — config.toml, project root
- **CLI – Codex**: https://developers.openai.com/docs/codex/cli — installation, Windows status
- **Agent Skills**: https://developers.openai.com/docs/codex/skills — skill invocation
- **openai/codex repo**: https://github.com/openai/codex — generated schemas, issues
- **paulboutin/AI-Wiki-knowledge**: https://github.com/paulboutin/AI-Wiki-knowledge — production wiki для Codex
- **Наша wiki**: https://github.com/ub3dqy/llm-wiki

---

## КРИТИЧЕСКИЙ БЛОКЕР: Hooks отключены на Windows

Официальная документация Codex CLI прямо указывает:

> "Hooks are under active development. Windows support temporarily disabled."

**Следствие:** Все хуки должны запускаться **через WSL**, не нативно в Windows. Пути должны быть linux-style (`/mnt/e/Project/...`), uv и python должны быть доступны в WSL-среде.

### Варианты решения

1. **WSL (рекомендуемый)**: Запускать Codex CLI из WSL, хуки работают нативно в Linux
2. **Ожидание**: Подождать пока OpenAI включит hooks на Windows
3. **Нативный Windows**: Попробовать — возможно работает несмотря на docs, но без гарантий

### Текущее состояние WSL (проверено)

- `wsl -l -v` показывает только `docker-desktop` — нет полноценного Linux-дистрибутива
- **Нужно установить** Ubuntu/Debian в WSL: `wsl --install -d Ubuntu`
- Затем внутри WSL: установить `codex`, `uv`, Python 3.12+
- Пути к wiki: `/mnt/e/Project/memory claude/memory claude/`

Это **предварительный блокер** — без WSL-дистрибутива Codex hooks не заработают.

---

## Исправленная сравнительная таблица

| Аспект | Claude Code | Codex CLI (исправлено) |
|---|---|---|
| Конфиг хуков | `~/.claude/settings.json` | `~/.codex/hooks.json` |
| Глобальный конфиг | `~/.claude/settings.json` | `~/.codex/config.toml` |
| Инструкции проекта | `CLAUDE.md` | `AGENTS.md` |
| **Глобальные инструкции** | `~/.claude/CLAUDE.md` | **`~/.codex/AGENTS.md`** (ЕСТЬ!) |
| Feature flag | Не нужен | `[features] codex_hooks = true` |
| SessionStart | Да | Да, `additionalContext` |
| SessionEnd | Да | **Нет** — используется `Stop` |
| PreCompact | Да | **Нет** (issue #17148) |
| Stop | systemMessage only | Да, с `transcript_path` |
| UserPromptSubmit | Да, `additionalContext` | Да, `additionalContext` |
| PostToolUse | async поддерживается | **Только sync, только Bash** |
| Hook types | command, http, prompt, agent | Документирован только **command** (для production опираемся на него) |
| **Stdin format** | top-level fields | **top-level fields** (НЕ вложенный hook_event!) |
| **tool_name** | `"Bash"` | **`"Bash"`** (НЕ "local_shell"!) |
| **tool_input.command** | строка | **строка** (НЕ массив!) |
| Windows hooks | Да | **Нет** (temporarily disabled) |

---

## Архитектура: одна wiki, два агента

```
LLM Wiki (Obsidian vault)
├── hooks/
│   ├── claude/                 ← хуки Claude Code
│   ├── codex/                  ← хуки Codex CLI (новые)
│   ├── hook_utils.py           ← общий модуль
│   ├── shared_context.py       ← общая логика build_context
│   └── shared_wiki_search.py   ← общая логика поиска статей
├── scripts/                    ← общие скрипты
├── wiki/                       ← общая wiki
├── daily/                      ← общие daily logs
└── codex-hooks.example.json    ← пример для ~/.codex/hooks.json
```

---

## Шаг 1: Включить hooks в Codex CLI

```toml
# ~/.codex/config.toml
[features]
codex_hooks = true
```

**Проверка** (НЕ через `codex --version`!):
```bash
codex features list
# или проверить содержимое ~/.codex/config.toml
```

---

## Шаг 2: Глобальный AGENTS.md

**Исправление:** У Codex ЕСТЬ глобальный AGENTS.md (в отличие от того, что было в исходном плане).

Путь: `~/.codex/AGENTS.md` (или `$CODEX_HOME/AGENTS.md`)

```markdown
# Global Instructions

## Knowledge Base (LLM Wiki) — MANDATORY

You have a global knowledge base (LLM Wiki).
Wiki location: `/mnt/e/Project/memory claude/memory claude/`

### RULE: Wiki-first

BEFORE starting any task, you MUST:
1. Scan the wiki index — are there articles related to the current task?
2. If yes — Read those articles BEFORE writing code
3. Use wiki knowledge as your foundation

DO NOT:
- Ignore the wiki when relevant articles exist
- Reinvent solutions already documented
- Contradict wiki decisions without explaining why
```

**Динамический контекст** (wiki index, project articles, recent changes) по-прежнему инжектируется через SessionStart hook — AGENTS.md содержит только статические правила.

---

## Шаг 3: Исправленный stdin format для хуков

### Ключевое исправление: все поля top-level, НЕ вложенные

Ниже приведены **полные** payload schemas по generated schemas из openai/codex repo. Тестовые JSON'ы в секции "Верификация" — сокращённые иллюстрации; для production smoke tests используйте полные версии.

**SessionStart stdin (полная schema):**
```json
{
  "session_id": "thread-uuid",
  "cwd": "/path/to/project",
  "transcript_path": "/path/to/transcript.jsonl",
  "hook_event_name": "SessionStart",
  "model": "o4-mini",
  "permission_mode": "suggest",
  "source": "startup"
}
```
Обязательные поля по schema: `session_id`, `cwd`, `transcript_path`, `hook_event_name`, `model`, `permission_mode`, `source`.

**UserPromptSubmit stdin (полная schema):**
```json
{
  "session_id": "thread-uuid",
  "cwd": "/path/to/project",
  "transcript_path": "/path/to/transcript.jsonl",
  "hook_event_name": "UserPromptSubmit",
  "model": "o4-mini",
  "permission_mode": "suggest",
  "prompt": "how does pgvector work?",
  "turn_id": "turn-3"
}
```
Обязательные: `session_id`, `cwd`, `transcript_path`, `hook_event_name`, `model`, `permission_mode`, `prompt`, `turn_id`.

**PostToolUse stdin (полная schema):**
```json
{
  "session_id": "thread-uuid",
  "cwd": "/path/to/project",
  "transcript_path": "/path/to/transcript.jsonl",
  "hook_event_name": "PostToolUse",
  "model": "o4-mini",
  "permission_mode": "suggest",
  "tool_name": "Bash",
  "tool_input": {
    "command": "git commit -m \"fix auth\""
  },
  "tool_response": "...",
  "tool_use_id": "call-abc123",
  "turn_id": "turn-4"
}
```
Обязательные: `session_id`, `cwd`, `transcript_path`, `hook_event_name`, `model`, `permission_mode`, `tool_name`, `tool_input`, `tool_response`, `tool_use_id`, `turn_id`.

**Stop stdin (полная schema):**
```json
{
  "session_id": "thread-uuid",
  "cwd": "/path/to/project",
  "transcript_path": "/path/to/transcript.jsonl",
  "hook_event_name": "Stop",
  "model": "o4-mini",
  "permission_mode": "suggest",
  "stop_hook_active": false,
  "last_assistant_message": "Done. I've updated the config.",
  "turn_id": "turn-5"
}
```
Обязательные: `session_id`, `cwd`, `transcript_path`, `hook_event_name`, `model`, `permission_mode`, `stop_hook_active`, `last_assistant_message`, `turn_id`.

> **Примечание:** Для точного wire format смотрите generated schemas в official repo:
> GitHub: `openai/codex` → `codex-rs/hooks/schema/generated/`
> **Важно:** команда `codex app-server generate-json-schema` генерирует app-server protocol schemas, а НЕ hook payload schemas.

### Практическая совместимость с Claude Code

Для полей, которые используют наши хуки (`cwd`, `transcript_path`, `prompt`, `tool_name`, `tool_input.command`), Codex использует top-level payload, который **практически совпадает** с текущим форматом Claude Code хуков. Это позволяет переиспользовать парсинг-логику без изменений для SessionStart, UserPromptSubmit и PostToolUse.

> **Оговорка:** Это практическое совпадение для конкретных полей, а не формальное утверждение о полном равенстве wire contract'ов двух систем. Официальная документация OpenAI описывает именно Codex payload; совпадение с Claude Code — эмпирическое наблюдение, не гарантированный контракт.

Дополнительные поля Codex (`model`, `permission_mode`, `turn_id`, `tool_use_id`, `tool_response`) наши хуки могут безопасно игнорировать — они нужны только для advanced use cases.

Различия:
- `source` (SessionStart): Claude = `startup|resume|clear|compact`, Codex = `startup|resume|clear` (clear version-sensitive — проверить на установленной версии)
- `stop_hook_active` (Stop): есть в Codex, Claude Code использует аналогичное поле
- Нет SessionEnd / PreCompact в Codex

---

## Шаг 4: hooks/codex/ — минимальные обёртки

SessionStart и UserPromptSubmit могут быть **тонкими обёртками** вокруг shared-логики — их stdin/output контракт практически совпадает с Claude Code. Stop требует **отдельной реализации** из-за его turn-scoped семантики (matcher не используется, `stop_hook_active` — обязательное поле, plain text stdout невалиден — ожидается JSON).

### hooks/codex/session-start.py (обёртка)

```python
"""Codex SessionStart: reuse shared context logic."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from shared_context import build_context_and_output

if __name__ == "__main__":
    build_context_and_output()
```

### hooks/codex/user-prompt-wiki.py (обёртка)

```python
"""Codex UserPromptSubmit: reuse shared wiki search logic."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from shared_wiki_search import find_and_inject_articles

if __name__ == "__main__":
    find_and_inject_articles()
```

### hooks/codex/stop.py (отдельная реализация)

```python
"""Codex Stop: capture transcript (analog of Claude SessionEnd).

CRITICAL differences from Claude SessionEnd:
- Stop fires after EVERY response, not just at session end → strict debounce (60s)
- stop_hook_active field must be checked to avoid re-trigger loops
- Matcher is NOT used for Stop events
- Exit 0 expects JSON on stdout; plain text is invalid
- MIN_TURNS higher (6 vs 4) because Stop fires much more frequently
"""
# Dedicated implementation — uses shared utilities (hook_utils.py)
# but NOT a thin wrapper around Claude session-end.py
# Key params:
# - DEBOUNCE_SEC = 60
# - MIN_TURNS = 6
# - Check stop_hook_active before processing
# - Spawn flush.py as background process (same as Claude)
```

### hooks/codex/post-tool-capture.py (обёртка)

```python
"""Codex PostToolUse: capture Bash commands.

NOTE:
- tool_name is "Bash" (NOT "local_shell")
- tool_input.command is a string (NOT an array)
- Codex does NOT support async: true — this hook is SYNC
- Only Bash tools are intercepted (not Write, MCP, WebSearch)
- Same tool_name and tool_input format as Claude Code
"""
# Can reuse Claude post-tool-capture.py logic directly
```

---

## Шаг 5: Вынести общую логику в shared-модули

### hooks/shared_context.py

Извлечь из `hooks/session-start.py`:

```python
def build_context(cwd: str = "", wiki_root: Path = None) -> str
def build_context_and_output() -> None  # parse stdin + build + print JSON
```

### hooks/shared_wiki_search.py

Извлечь из `hooks/user-prompt-wiki.py`:

```python
def find_relevant_articles(prompt: str, wiki_dir: Path = None) -> list
def find_and_inject_articles() -> None  # parse stdin + search + print JSON
```

### hooks/hook_utils.py — дополнить

```python
def get_transcript_path(hook_input: dict) -> str:
    """Extract transcript_path — top-level in both Claude Code and Codex."""
    return hook_input.get("transcript_path", "")

def get_prompt(hook_input: dict) -> str:
    """Extract prompt — top-level in both Claude Code and Codex."""
    return hook_input.get("prompt", "")
```

---

## Шаг 6: Глобальная конфигурация Codex hooks

### `~/.codex/hooks.json`

```json
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "startup|resume",
        "hooks": [
          {
            "type": "command",
            "command": "uv run --directory /mnt/e/Project/memory\\ claude/memory\\ claude python hooks/codex/session-start.py",
            "statusMessage": "Loading wiki context",
            "timeout": 15
          }
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "uv run --directory /mnt/e/Project/memory\\ claude/memory\\ claude python hooks/codex/stop.py",
            "timeout": 10
          }
        ]
      }
    ],
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "uv run --directory /mnt/e/Project/memory\\ claude/memory\\ claude python hooks/codex/user-prompt-wiki.py",
            "statusMessage": "Wiki lookup",
            "timeout": 5
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "uv run --directory /mnt/e/Project/memory\\ claude/memory\\ claude python hooks/codex/post-tool-capture.py",
            "timeout": 3
          }
        ]
      }
    ]
  }
}
```

**Важно:**
- Пути через WSL: `/mnt/e/...` (не `E:/...`)
- matcher PostToolUse: `"Bash"` (не `"local_shell"`)
- Нет `async: true` — все хуки синхронные
- SessionStart matcher: базовый `startup|resume` (по official docs). Опционально добавить `clear` после проверки на установленной версии — generated schema его допускает, но docs пока не документируют

---

## Шаг 7: Обновить hook_utils.py — автодетект transcript формата

```python
def extract_conversation_context(transcript_path: Path, ...) -> tuple[str, int]:
    """Extract conversation. Auto-detects JSONL vs JSON array format."""
    text = transcript_path.read_text(encoding="utf-8")
    
    # Defensive: auto-detect format
    stripped = text.strip()
    if stripped.startswith("["):
        # JSON array format
        entries = json.loads(stripped)
    else:
        # JSONL format (one JSON per line)
        entries = []
        for line in text.splitlines():
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    
    # ... rest unchanged
```

---

## Порядок реализации

```
[1] Включить codex_hooks в config.toml
[2] Создать ~/.codex/AGENTS.md (глобальные wiki-first инструкции)
[3] Создать shared_context.py + shared_wiki_search.py
[4] Обновить hook_utils.py (автодетект transcript, universal helpers)
[5] Создать hooks/codex/ (4 файла — тонкие обёртки)
[6] Рефакторить Claude Code хуки → импорт из shared-модулей
[7] Создать ~/.codex/hooks.json
[8] Создать codex-hooks.example.json в репо
[9] Обновить README.md
[10] Тестирование (в WSL!) + commit + push
```

---

## Файлы для создания/изменения

| Файл | Действие | Описание |
|---|---|---|
| `~/.codex/config.toml` | Modify | `codex_hooks = true` |
| `~/.codex/AGENTS.md` | Create | Глобальные wiki-first инструкции |
| `hooks/shared_context.py` | Create | Общая логика build_context |
| `hooks/shared_wiki_search.py` | Create | Общая логика поиска статей |
| `hooks/hook_utils.py` | Modify | Автодетект transcript, universal helpers |
| `hooks/codex/session-start.py` | Create | Обёртка → shared_context |
| `hooks/codex/stop.py` | Create | Аналог SessionEnd (debounce 60s) |
| `hooks/codex/user-prompt-wiki.py` | Create | Обёртка → shared_wiki_search |
| `hooks/codex/post-tool-capture.py` | Create | Bash capture (sync, timeout 3s) |
| `hooks/session-start.py` | Modify | Рефакторинг → shared_context |
| `hooks/user-prompt-wiki.py` | Modify | Рефакторинг → shared_wiki_search |
| `~/.codex/hooks.json` | Create | Глобальная конфигурация хуков |
| `codex-hooks.example.json` | Create | Пример для репо |
| `README.md` | Modify | Секция Codex CLI setup |

---

## Верификация

### Тест 1: Feature flag
```bash
codex features list
# Ожидаем: codex_hooks = true
```

### Тест 2: SessionStart (из WSL, полный payload)
```bash
echo '{"session_id":"test-001","cwd":"/mnt/e/Project/game app/messenger_test","transcript_path":"/tmp/test.jsonl","hook_event_name":"SessionStart","model":"o4-mini","permission_mode":"suggest","source":"startup"}' | \
  uv run --directory /mnt/e/Project/memory\ claude/memory\ claude python hooks/codex/session-start.py
# Ожидаем: JSON с additionalContext, секция Project: messenger
```

### Тест 3: UserPromptSubmit (полный payload)
```bash
echo '{"session_id":"test-001","cwd":"/mnt/e/Project","transcript_path":"/tmp/test.jsonl","hook_event_name":"UserPromptSubmit","model":"o4-mini","permission_mode":"suggest","prompt":"как работает pgvector?","turn_id":"turn-1"}' | \
  uv run --directory /mnt/e/Project/memory\ claude/memory\ claude python hooks/codex/user-prompt-wiki.py
# Ожидаем: JSON с additionalContext содержащим pgvector статью
```

### Тест 4: PostToolUse (полный payload)
```bash
echo '{"session_id":"test-001","cwd":"/mnt/e/Project/office","transcript_path":"/tmp/test.jsonl","hook_event_name":"PostToolUse","model":"o4-mini","permission_mode":"suggest","tool_name":"Bash","tool_input":{"command":"git commit -m fix"},"tool_response":"[master abc123] fix","tool_use_id":"call-001","turn_id":"turn-2"}' | \
  uv run --directory /mnt/e/Project/memory\ claude/memory\ claude python hooks/codex/post-tool-capture.py
# Ожидаем: micro-entry в daily log
```

### Тест 5: Реальная сессия Codex (WSL)
```bash
codex  # Из WSL в любом проекте
# Проверить wiki context инжектирован
```

### Тест 6: Cross-agent flow
```
1. Создать статью в Claude Code (/wiki-save)
2. Открыть Codex в том же проекте
3. Спросить по теме статьи — должна инжектироваться через UserPromptSubmit
```

---

## Важные замечания из аудита

### cwd проекта vs рабочая директория процесса

Официальная документация указывает: "commands run with the session cwd as their working directory". Но при использовании `uv run --directory /path/to/wiki` рабочая директория хука меняется на wiki root. Поэтому **всё что относится к проекту пользователя** (project name, project articles) нужно извлекать из stdin поля `cwd`, а не из `Path.cwd()`. Наши хуки уже делают это правильно.

### transcript_path может быть null

Официальная schema указывает `transcript_path: string | null`. Все хуки должны обрабатывать `null` / отсутствие этого поля без ошибок. Наши хуки уже проверяют пустоту.

### Skills в Codex ≠ slash commands

Codex skills вызываются через `$skill-name` или неявно по описанию, а не через `/skill-name`. Наш `/wiki-save` — это Claude Code skill; для Codex нужен отдельный механизм (custom instructions в AGENTS.md или описание задачи).

### Generated schemas — source of truth

Для точного wire format смотрите generated schemas в official repo:
- GitHub: `openai/codex` → `codex-rs/hooks/schema/generated/`

**Важно:** команда `codex app-server generate-json-schema` генерирует app-server protocol schemas, а НЕ hook payload schemas. Для hook schemas опирайтесь на файлы в `codex-rs/hooks/schema/generated/` и official docs.

---

## Риски

| Риск | Митигация |
|---|---|
| **Hooks disabled on Windows** | Запускать Codex из WSL |
| Stop fires after every response | Debounce 60 сек + MIN_TURNS 6 |
| PostToolUse sync блокирует Codex | Timeout 3 сек, только file I/O |
| PostToolUse ловит только Bash (не Write, MCP, WebSearch) | Для полной картины — Stop + transcript |
| Transcript format не гарантирован документально | Defensive автодетект JSON vs JSONL |
| concurrent hooks modify same files | File locking на daily log и state. Docs: matching hooks run concurrently |
| Формат stdin может измениться между версиями | Сгенерировать schema: `openai/codex repo: codex-rs/hooks/schema/generated/` |
| SessionStart `clear` matcher version-sensitive | Docs = startup+resume. Schema = +clear. Проверить на установленной версии |

---

## История исправлений

### v1 → v2 (критические ошибки, найдены в первом аудите)

| # | Ошибка | Было | Стало |
|---|---|---|---|
| 1 | stdin format | Вложенный `hook_event.*` | **Top-level fields** |
| 2 | tool_name | `"local_shell"` | **`"Bash"`** |
| 3 | tool_input.command | Массив `["git", "commit"]` | **Строка `"git commit"`** |
| 4 | Global AGENTS.md | "Нет глобального аналога" | **`~/.codex/AGENTS.md` ЕСТЬ** |
| 5 | Windows hooks | Нативные Windows пути | **WSL пути `/mnt/e/...`** |
| 6 | async: true | "Пропускается с warning" | **Не документировано, не использовать** |
| 7 | Version check | `codex --version` | **`codex features list`** |
| 8 | SessionStart matcher | `"startup\|resume"` | **`"startup\|resume\|clear"`** |

### v2 → v3 (уточнения, найдены во втором аудите)

| # | Уточнение | Было в v2 | Стало в v3 |
|---|---|---|---|
| 9 | Payload schemas неполные | Только ключевые поля | **Полные schemas** с `model`, `permission_mode`, `turn_id`, `tool_use_id`, `tool_response` |
| 10 | "Формат одинаковый" | Утверждение без оговорок | **"Практически совпадает"** — эмпирическое наблюдение, не гарантированный контракт |
| 11 | "Только command hooks" | Категоричная формулировка | **"Документирован только command"** — для production опираемся на него |
| 12 | SessionStart `clear` | Без оговорок | **Version-sensitive** — docs = startup+resume, schema = +clear |
| 13 | cwd vs working dir | Не упоминалось | **Добавлено** — использовать stdin `cwd`, не `Path.cwd()` |
| 14 | transcript_path nullable | Не упоминалось | **Добавлено** — schema допускает `null` |
| 15 | Skills ≠ slash commands | `/wiki-save` для Codex | **Уточнено** — Codex: `$skill-name`, не `/skill-name` |
| 16 | Generated schemas | Не упоминалось | **Добавлена команда** `openai/codex repo: codex-rs/hooks/schema/generated/` |

### v3 финальные правки (третий раунд аудита)

| # | Правка | Что изменено |
|---|---|---|
| 17 | SessionStart matcher | Базовый `startup\|resume` в примере hooks.json. `clear` — опция после проверки версии |
| 18 | Stop — отдельная реализация | Убрана формулировка "симлинки для всех хуков". Stop явно выделен как отдельная реализация из-за turn-scoped семантики |
| 19 | Совместимость формулировка | Добавлена оговорка: практическое совпадение, не формальное равенство wire contract'ов |

### v3.1 → v3.2 (четвёртый раунд — замечания из Codex pre-implementation review)

| # | Правка | Что изменено |
|---|---|---|
| 20 | Schema-команда | `codex app-server generate-json-schema` генерирует app-server schemas, НЕ hook schemas. Исправлено на `codex-rs/hooks/schema/generated/` |
| 21 | WSL-блокер | Добавлен как предварительный блокер: только docker-desktop в WSL, нужен полноценный дистрибутив |
| 22 | README maintenance checklist | Исправлена schema-команда в README.md |

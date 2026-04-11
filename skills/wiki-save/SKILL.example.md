---
name: wiki-save
description: >
  Instantly save knowledge to the LLM Wiki. Creates or updates a wiki article
  for the given topic, updates index.md and log.md. Use when the user says:
  /wiki-save, save to wiki, add to wiki, document this, remember this in wiki.
user-invocable: true
argument-hint: <topic or concept to save>
---

# Skill: Wiki Save

Save a topic or concept to the global LLM Wiki immediately — no waiting for session end or compilation.

## Wiki Location

- **Root:** `/path/to/llm-wiki/`
- **Articles:** `/path/to/llm-wiki/wiki/`
- **Index:** `/path/to/llm-wiki/index.md`
- **Log:** `/path/to/llm-wiki/log.md`

## Article directories

| Type | Directory | When to use |
|---|---|---|
| `concept` | `wiki/concepts/` | Ideas, patterns, architectures, technologies |
| `entity` | `wiki/entities/` | People, organizations, tools (with identity) |
| `connection` | `wiki/connections/` | Non-obvious relationships between 2+ concepts |
| `source` | `wiki/sources/` | Summaries of ingested source documents |
| `qa` | `wiki/qa/` | Filed Q&A answers |

## Your Task

The user invoked `/wiki-save $ARGUMENTS`.

If no topic is given, ask: "What topic should I create/update a wiki article for?"

### Step 1: Check existing articles

Read the wiki index at `/path/to/llm-wiki/index.md`.
Check if an article for this topic already exists.

### Step 2: Create or update

**If article exists:**
1. Read the existing article
2. Use Edit to add new information without destroying existing content
3. Update the `updated` field in frontmatter to today's date

**If article is new:**
1. Determine type: concept (most common), entity, connection, or qa
2. Create the file with a slugified filename (lowercase, hyphens, max 80 chars)
3. Use complete YAML frontmatter (see format below)

### Step 3: Determine project tag

Infer the project name from the current working directory context.
If unclear, ask the user.

### Article Format (MANDATORY)

```yaml
---
title: <descriptive title>
type: concept | entity | source | connection | qa
created: <YYYY-MM-DD>
updated: <YYYY-MM-DD>
sources: [<source reference>]
project: <project-name>
tags: [<relevant>, <tags>]
---
```

Content structure:
- `# Title` — matches frontmatter title
- `## Key Points` — 3-5 bullet points
- `## Details` — 2+ paragraphs with technical depth
- `## See Also` — `[[wikilinks]]` to 2+ related articles from the index

Use `[[section/slug]]` format for ALL cross-references (e.g., `[[concepts/redis-caching]]`).

### Step 4: Update index.md

Add a new line under the appropriate section header in `/path/to/llm-wiki/index.md`.
Format: `- [[section/slug]] — Brief one-line description`

If the article already exists in the index, leave the line as is.

### Step 5: Append to log.md

Append to `/path/to/llm-wiki/log.md`:

```
## [<ISO timestamp>] wiki-save | <topic>
- Article: [[section/slug]]
- Action: created | updated
- Project: <project-name>
```

### Step 6: Confirm

Tell the user: "Saved to wiki: [[section/slug]] — <brief description>"

## Language

Write article content in the language of the topic or user input.
Meta fields (type, tags) use lowercase English.

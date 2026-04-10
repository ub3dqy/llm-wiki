# LLM Wiki — Schema

This is the schema file for the LLM Wiki. It defines the structure, conventions, and workflows that the LLM follows when maintaining this wiki.

## Directory Structure

```
.
├── CLAUDE.md          # This file — schema and conventions
├── index.md           # Content index — catalog of all wiki pages
├── log.md             # Chronological log of all operations
├── raw/               # Immutable source documents
│   ├── assets/        # Downloaded images and media
│   └── ...            # Articles, papers, notes (markdown, PDF, etc.)
├── wiki/              # LLM-maintained wiki pages
│   ├── overview.md    # High-level overview and synthesis
│   ├── sources/       # Source summaries (one per ingested source)
│   ├── entities/      # Entity pages (people, organizations, tools, etc.)
│   ├── concepts/      # Concept pages (ideas, theories, patterns)
│   └── analyses/      # Query results filed as wiki pages
```

## Page Format

Every wiki page uses this structure:

```markdown
---
title: Page Title
type: source | entity | concept | analysis | overview
created: YYYY-MM-DD
updated: YYYY-MM-DD
sources: [list of source filenames that informed this page]
tags: [relevant tags]
---

# Page Title

Content here. Use [[wikilinks]] for cross-references to other pages.

## See Also
- [[Related Page 1]]
- [[Related Page 2]]
```

## Conventions

- **Language**: Wiki content follows the language of the source material. Meta-files (index, log) are in Russian unless the user specifies otherwise.
- **Wikilinks**: Always use `[[Page Name]]` syntax for internal links (Obsidian-compatible).
- **One concept per page**: Don't merge unrelated topics. Split when a section grows large.
- **Source attribution**: Every claim should be traceable to a source via the `sources` frontmatter field.
- **Contradictions**: When sources disagree, note it explicitly with a `> [!warning] Contradiction` callout.
- **Updates over rewrites**: When new information arrives, update existing pages rather than creating duplicates.

## Workflows

### Ingest (adding a new source)

1. Read the source document from `raw/`.
2. Discuss key takeaways with the user.
3. Create a summary page in `wiki/sources/` with frontmatter.
4. Update `wiki/overview.md` if the source changes the big picture.
5. Create or update relevant entity pages in `wiki/entities/`.
6. Create or update relevant concept pages in `wiki/concepts/`.
7. Add cross-references (`[[wikilinks]]`) across all touched pages.
8. Update `index.md` with new/changed pages.
9. Append an entry to `log.md`.

### Query (answering a question)

1. Read `index.md` to find relevant pages.
2. Read the relevant wiki pages.
3. Synthesize an answer with `[[wikilink]]` citations.
4. If the answer is substantial, offer to file it as a new page in `wiki/analyses/`.
5. If filed, update `index.md` and append to `log.md`.

### Lint (health check)

1. Scan all wiki pages for:
   - Contradictions between pages
   - Stale claims superseded by newer sources
   - Orphan pages (no inbound links)
   - Mentioned but missing pages (red links)
   - Missing cross-references
   - Data gaps worth investigating
2. Report findings to the user.
3. Fix issues with user approval.
4. Append a lint entry to `log.md`.

## Tags Taxonomy

Use lowercase, hyphenated tags. Common categories:

- Domain tags: specific to your topic (define as you go)
- Meta tags: `#needs-review`, `#contradiction`, `#stub`, `#key-insight`

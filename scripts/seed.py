"""Seed: populate wiki from an existing project's key files.

Scans project structure (package.json, README, configs, src/ tree)
and uses Claude Agent SDK to create starter wiki articles.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

# Propagate recursion guard
os.environ["CLAUDE_INVOKED_BY"] = "seed"

# Add scripts/ to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import (
    CONCEPTS_DIR,
    CONNECTIONS_DIR,
    ENTITIES_DIR,
    INDEX_FILE,
    LOG_FILE,
    SCHEMA_FILE,
    WIKI_DIR,
    now_iso,
)
from utils import read_wiki_index

ROOT_DIR = Path(__file__).resolve().parent.parent

# Files to look for when scanning a project
SCAN_FILES = [
    "package.json",
    "pyproject.toml",
    "Cargo.toml",
    "go.mod",
    "README.md",
    "CLAUDE.md",
    "docker-compose.yml",
    "docker-compose.yaml",
    "Dockerfile",
    "tsconfig.json",
    "next.config.js",
    "next.config.mjs",
    "next.config.ts",
    "vite.config.ts",
    "prisma/schema.prisma",
    ".env.example",
    "turbo.json",
    "nx.json",
]

MAX_FILE_SIZE = 10_000  # chars per file to include


def scan_project(project_dir: str) -> dict:
    """Scan a project directory for key files and structure."""
    root = Path(project_dir)
    if not root.exists():
        print(f"Error: {project_dir} does not exist")
        sys.exit(1)

    name = root.name
    found_files: dict[str, str] = {}

    # Scan for key files (root + 1 level deep for monorepos)
    scan_dirs = [root]
    for child in root.iterdir():
        if child.is_dir() and not child.name.startswith("."):
            scan_dirs.append(child)

    for scan_dir in scan_dirs:
        for filename in SCAN_FILES:
            filepath = scan_dir / filename
            if filepath.exists():
                rel = str(filepath.relative_to(root)).replace("\\", "/")
                try:
                    content = filepath.read_text(encoding="utf-8")
                    if len(content) > MAX_FILE_SIZE:
                        content = content[:MAX_FILE_SIZE] + "\n\n...(truncated)"
                    found_files[rel] = content
                except (OSError, UnicodeDecodeError):
                    pass

    # Scan src/ structure (just directory names, max 3 levels)
    src_tree: list[str] = []
    for src_dir_name in ["src", "app", "apps", "packages", "lib"]:
        src_dir = root / src_dir_name
        if src_dir.exists():
            for p in sorted(src_dir.rglob("*")):
                if p.is_dir():
                    rel = p.relative_to(root)
                    depth = len(rel.parts)
                    if depth <= 3:
                        src_tree.append(str(rel).replace("\\", "/"))

    return {
        "name": name,
        "path": str(root),
        "files": found_files,
        "src_tree": src_tree[:50],  # cap at 50 dirs
    }


async def seed_wiki(project_info: dict, project_name: str) -> None:
    """Use Agent SDK to create wiki articles from project scan."""
    from claude_agent_sdk import ClaudeAgentOptions, query

    schema = SCHEMA_FILE.read_text(encoding="utf-8") if SCHEMA_FILE.exists() else "(no schema)"
    wiki_index = read_wiki_index()

    # Build context from scanned files
    files_context = ""
    for filename, content in project_info["files"].items():
        files_context += f"\n### {filename}\n```\n{content}\n```\n"

    tree_context = ""
    if project_info["src_tree"]:
        tree_context = (
            "\n### Directory Structure\n```\n" + "\n".join(project_info["src_tree"]) + "\n```\n"
        )

    timestamp = now_iso()

    prompt = f"""You are a knowledge base seeder. Analyze the project files below and create
starter wiki articles for this project.

## Schema (CLAUDE.md)

{schema}

## Current Wiki Index

{wiki_index}

## Project: {project_name}

Path: {project_info["path"]}

## Project Files

{files_context}

{tree_context}

## Your Task

Create wiki articles for this project following the schema:

1. **Create 1 entity article** in `wiki/entities/` for the project itself
   - Name, purpose, tech stack, key features
   - Use project tag: `project: {project_name}`

2. **Create 3-7 concept articles** in `wiki/concepts/` for key technologies
   - Only for technologies actually used (found in config files)
   - Each with YAML frontmatter, Key Points, Details, See Also
   - Use project tag: `project: {project_name}`

3. **Check existing articles** — Read the index first. If an article already exists
   for a technology (e.g., fastify, bullmq), UPDATE it with project-specific info
   rather than creating a duplicate.

4. **Update index.md** at `{INDEX_FILE}` — add new entries

5. **Append to log.md** at `{LOG_FILE}`:
   ```
   ## [{timestamp}] seed | {project_name}
   - Source: project scan of {project_info["path"]}
   - Articles created: [[...]]
   - Articles updated: [[...]]
   ```

### File paths:
- Entity articles: {ENTITIES_DIR}
- Concept articles: {CONCEPTS_DIR}
- Connection articles: {CONNECTIONS_DIR}
- Index: {INDEX_FILE}
- Log: {LOG_FILE}

### Quality:
- Every article: complete YAML frontmatter with project tag
- Every article: 200+ words
- Every article: 2+ [[wikilinks]] to related articles
- Don't create articles for trivial/obvious things (e.g., "JavaScript", "Git")
- Focus on architectural decisions, patterns, and project-specific configurations
"""

    cost = 0.0
    try:
        async for message in query(
            prompt=prompt,
            options=ClaudeAgentOptions(
                cwd=str(ROOT_DIR),
                system_prompt={"type": "preset", "preset": "claude_code"},
                allowed_tools=["Read", "Write", "Edit", "Glob", "Grep"],
                permission_mode="acceptEdits",
                max_turns=30,
            ),
        ):
            if hasattr(message, "total_cost_usd"):
                cost = message.total_cost_usd or 0.0
    except Exception as e:
        print(f"Error: {e}")
        return

    print(f"Seed complete. Cost: ${cost:.4f}")

    # Rebuild index with annotations
    try:
        from rebuild_index import rebuild_and_write_index

        rebuild_and_write_index()
        print("Index enriched with project tags and word counts.")
    except Exception:
        pass


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed wiki from an existing project")
    parser.add_argument("project_dir", help="Path to the project to seed from")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be scanned")
    parser.add_argument("--project-name", help="Override project name (default: directory name)")
    args = parser.parse_args()

    project_info = scan_project(args.project_dir)
    project_name = args.project_name or project_info["name"]

    print(f"Project: {project_name}")
    print(f"Path: {project_info['path']}")
    print(f"Found {len(project_info['files'])} key files:")
    for f in project_info["files"]:
        print(f"  - {f}")
    if project_info["src_tree"]:
        print(f"Source dirs: {len(project_info['src_tree'])}")
    print(f"Estimated cost: ~$0.10-0.30")

    if args.dry_run:
        return

    print("\nSeeding wiki...")
    asyncio.run(seed_wiki(project_info, project_name))


if __name__ == "__main__":
    main()

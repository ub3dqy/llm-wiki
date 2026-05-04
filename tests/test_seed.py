from __future__ import annotations

import asyncio

import seed as seed_module


def test_seed_wiki_returns_false_manual_backend(monkeypatch, capsys) -> None:
    monkeypatch.setattr(seed_module, "WIKI_AGENT_BACKEND", "manual")

    ok = asyncio.run(
        seed_module.seed_wiki(
            {"files": {}, "src_tree": [], "path": "/workspace/example"},
            "example",
        )
    )

    assert ok is False
    assert "WIKI_AGENT_BACKEND=claude" in capsys.readouterr().out

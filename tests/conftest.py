"""Pytest fixtures and configuration for LLM Wiki tests.

Per pyproject.toml [tool.pytest.ini_options] pythonpath = ["scripts"],
test modules can `from utils import X` directly without sys.path hacks.

Fixtures for first PR live inside test_utils.py. Shared fixtures can migrate
here in Tier 4.1 when more test modules are added.
"""

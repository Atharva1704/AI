"""CLI orchestrator for a LangChain + Groq GitHub PR reviewer.

Uses existing `tools.py` wrappers for all GitHub access. No GitHub write occurs
unless the user explicitly types PUBLISH in the CLI.

Run from the project root:
python src/agent.py
"""

<!-- Purpose: Help AI coding agents be immediately productive in this repository. Keep this file short and concrete. -->
# Copilot instructions for arxiv-agent

Purpose
- Short: this repository is an "arxiv-agent" — an AI agent to download and structure papers and data from arXiv. See `README.md` for the one-line project description.

What to do first (must-do before code changes)
- Open and read `README.md` to confirm scope (already present).
- Run a workspace search for common project files to detect language and tools: `pyproject.toml`, `requirements.txt`, `setup.py`, `package.json`, `src/`, `app/`, `main.py`.
- If new files appear, prefer to update these instructions rather than assume a language/framework.

Big-picture guidance for changes
- Focus changes around the core goal: downloading and structuring arXiv papers and metadata. Typical components you'll touch: network/download layer (fetching arXiv PDFs/metadata), parsing/extraction layer, storage/serialization (JSON/DB), and a CLI or agent orchestration layer.
- Keep I/O and heavy computation separate from orchestration so the agent can be tested in isolation.

Project-specific patterns & checks (discoverable/current)
- At present the repo only contains `README.md`. When code exists, prefer small, testable edits and add a brief integration test that simulates a single-paper download and parse.
- Look for and follow existing file-level conventions (module names, entrypoints like `main.py` or `cli.py`) rather than adding new top-level commands.

Developer workflows (how an AI should help)
- If build/test files are present, prefer the project's native tooling (pytest, npm, poetry, etc.). If none are present, suggest adding a minimal `requirements.txt` and a simple pytest-based test harness.
- For debugging, search for an entrypoint (e.g., `if __name__ == "__main__"`) and add a `--dry-run` mode to avoid heavy network I/O during tests.

Integration & external dependencies
- Expect integrations with arXiv APIs, HTTP clients, and common parsing libraries (PDF/HTML). Verify and pin versions in the repo manifest you find.

Assumptions and how to correct them
- Assumption: this is an evolving project with minimal files currently. If you find language-specific manifests (e.g., `pyproject.toml`, `package.json`), update instructions and prefer that toolchain.

If you modify these instructions
- Merge (don't overwrite) any existing `.github/copilot-instructions.md` or `AGENT.md` — preserve prior guidance. Keep the file concise.

When in doubt
- Add small, well-scoped commits with tests/examples. Leave a short note in the PR describing why the change helps the agent (e.g., adds a dry-run flag, isolates network calls, or adds a minimal test fixture).

Feedback
- I added this initial guidance because the repo currently only contains `README.md`. Tell me what parts of the codebase I should read next or paste the key files you want the instructions to reference and I'll update this file.

# Contributing to NinjArmy

Thanks for your interest in contributing! NinjArmy is a local-first platform for orchestrating teams of AI coding agents, and we'd love your help making it better. Whether you're fixing a bug, adding a feature, or creating a new agent role — you're in the right place.

---

## Getting Started

### 1. Fork & clone

```bash
git clone https://github.com/<your-username>/ninjarmy.git
cd ninjarmy
```

### 2. Install in editable mode

Requires Python 3.10+.

```bash
pip install -e .
```

### 3. Set up your API key

Copy the example env file and add your Anthropic API key:

```bash
cp .env.example .env
# then edit .env and set ANTHROPIC_API_KEY=your-key-here
```

### 4. Verify it works

```bash
ninjarmy --version
ninjarmy boot
```

---

## Project Structure

```
ninjarmy/
  agents/       # Agent role definitions (agents.yaml) and schema
  cli/          # CLI entry points (boot, server, terminate)
  core/         # Manager, agent logic, tools, registry
  server/       # FastAPI web server + WebSocket events
  state/        # Persistent state (SQLite, task board)
  tui/          # Textual terminal UI
tests/          # Test suite (pytest)
```

---

## Making Changes

### Branch naming

Create a branch off `main` for your work:

```bash
git checkout -b feature/my-new-thing
# or
git checkout -b fix/broken-thing
```

### Commit style

Keep commits focused and use clear messages:

```
feat: add agent timeout config option
fix: prevent task board race condition on Windows
docs: update quickstart in README
```

---

## Tests

Tests will live in the `tests/` directory and use [pytest](https://pytest.org). As of now there are no tests created yet

```bash
pip install pytest
pytest
```

If you're adding a new feature or fixing a bug, please include a test.

---

## Adding a New Agent Role

Agent roles are defined in [ninjarmy/agents/agents.yaml](ninjarmy/agents/agents.yaml). Each role needs a name and a `prompt` that defines the agent's personality and behavior.

```yaml
roles:
  your-role-name:
    prompt: |
      You are a [description]. Your job is to [responsibility].
      [Any specific behavior guidelines...]
      Do only what was asked. Do not create documentation, reports, or extra files unless explicitly requested.
      When using tools, minimize commentary between calls. Act directly.
```

A few tips for writing good agent prompts:
- Be specific about what the agent focuses on and what it ignores
- End with the standard "Do only what was asked..." lines — this keeps agents from going off-script and wasting user's tokens
- Test your role by hiring it with `/hire your-role-name` in the TUI

---

## Submitting a PR

1. Push your branch and open a pull request against `main`
2. Give it a clear title and description — what does it do and why?
3. If it fixes an issue, reference it: `Closes #123`

---

## Questions?

Open a [GitHub Discussion](https://github.com/bodecoop/ninjarmy/discussions) or file an issue.

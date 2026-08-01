# Contributing to Aegis

Thanks for your interest in contributing to Aegis. This document explains how to
set up your environment, the standards we follow, and how to submit changes.

## Ways to Contribute

- Report bugs and request features via [GitHub Issues](https://github.com/AegisStack/aegis-core/issues).
- Improve documentation.
- Submit bug fixes and new features via pull requests.
- Add examples or integrations.

If you plan to work on something substantial, please open an issue first so we
can discuss the approach before you invest significant time.

## Project Structure

- `aegis/` — the Python SDK (policy engine, wrappers, sinks, integrations).
- `tests/` — SDK test suite.
- `examples/` — runnable usage examples (including `examples/policies/` sample policies).
- `aegis-dashboard/backend/` — FastAPI backend.
- `aegis-dashboard/frontend/` — Next.js frontend.
- `docs/` — guides and reference.

## Development Setup

See [docs/RUNNING_LOCALLY.md](docs/RUNNING_LOCALLY.md) for full setup
instructions. In short:

**SDK:**

```bash
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -e ".[dev]"
pytest
```

**Dashboard:** follow the dashboard section of
[docs/RUNNING_LOCALLY.md](docs/RUNNING_LOCALLY.md).

## Development Workflow

1. Fork the repository and create a branch from `main`:

   ```bash
   git checkout -b feature/short-description
   ```

2. Make your change, including tests and documentation updates.
3. Run the checks below and make sure they pass.
4. Commit with a clear message (see [Commit Messages](#commit-messages)).
5. Push your branch and open a pull request against `main`.

## Linting

The same linters run in three places — pick whichever fits your workflow:

- **On commit (recommended):** install the git hook once and it lints only the
  files you've staged, scoped to the package they belong to.

  ```bash
  pip install pre-commit
  pre-commit install
  # run manually against everything at any time:
  pre-commit run --all-files
  ```

- **On demand:** if you have `make` installed:

  ```bash
  make lint          # lint every package (check-only, same as CI)
  make format        # auto-fix Python formatting
  make lint-frontend # or lint-sdk / lint-backend for a single package
  ```

- **In CI:** [`.github/workflows/lint.yml`](.github/workflows/lint.yml) runs on
  every pull request against `main`. Each package's linters run only when that
  package changed.

## Coding Standards

### Python (SDK and backend)

We use the tools configured in `pyproject.toml`:

```bash
black aegis tests          # format (line length 100)
ruff check aegis tests     # lint
mypy aegis                 # type check (enforced in CI and pre-commit)
```

> Note: `mypy` runs in CI and as a pre-commit hook. It type-checks the whole
> `aegis` package (type-checking cannot be scoped to staged files, since a
> staged file's types depend on files you did not stage). Install the dev extra
> (`pip install -e ".[dev]"`) so the type stubs (`types-PyYAML`,
> `types-requests`) are available.

- All public functions must have type annotations (`disallow_untyped_defs` is on).
- Keep changes consistent with the surrounding code style.
- Add or update tests for any behavior change.

### Frontend (TypeScript / Next.js)

From `aegis-dashboard/frontend/`:

```bash
npm run lint
npm run type-check
npm test
```

### Emoji-Free Output

Keep source code, console/log output, and documentation free of decorative
emojis. Use plain text status markers (for example, `[ok]`, `[skip]`, `Error:`)
in program output. Functional UI icons in the frontend are fine.

## Testing

All contributions should keep the test suites green.

```bash
# SDK
pytest

# Frontend
cd aegis-dashboard/frontend && npm test

# Backend (requires the database running — see RUNNING_LOCALLY.md)
cd aegis-dashboard/backend && pytest
```

Please add tests that cover new code paths and edge cases.

## Commit Messages

Write clear, imperative commit messages:

```
Add regex operator support to policy engine

Longer explanation of what changed and why, if needed.
```

We loosely follow [Conventional Commits](https://www.conventionalcommits.org/)
prefixes (`feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`) — use them
where they help clarify intent, but they are not strictly required.

## Pull Requests

Before opening a PR, please confirm:

- [ ] Tests pass locally.
- [ ] New code has tests.
- [ ] Formatting and linting pass (`black`, `ruff`; `npm run lint` and `npm run type-check` for frontend).
- [ ] Documentation is updated where relevant.
- [ ] The PR description explains the change and links any related issue.

Keep pull requests focused. Smaller, single-purpose PRs are easier to review and
merge quickly. A maintainer will review your PR and may request changes before
merging.

## Reporting Bugs

When filing a bug report, please include:

- What you expected to happen and what actually happened.
- Steps to reproduce (a minimal code sample is ideal).
- Your environment (OS, Python/Node versions, Aegis version).
- Relevant logs or error output.

# Contributing to weather-decoder

Thanks for taking the time to contribute! This document describes how to
report issues, propose changes, and develop locally.

By participating in this project, you agree to follow the
[Code of Conduct](CODE_OF_CONDUCT.md). Keep discussion respectful,
constructive, and focused on the work.

## Ways to contribute

- **Report a bug** by opening an [issue](https://github.com/6639835/metar-taf-decoder/issues/new/choose)
  with a minimal reproducible example.
- **Request a feature** by opening an issue describing the use case.
- **Improve documentation**, examples, or test coverage.
- **Submit a pull request** for bug fixes or new functionality.

For non-trivial changes, please open an issue first so the design can be
discussed before you invest significant time.

## Development setup

This project uses a `src/` layout and standard Python tooling.

```bash
# Clone and create a virtual environment
git clone https://github.com/6639835/metar-taf-decoder.git
cd metar-taf-decoder
python -m venv .venv
source .venv/bin/activate    # Windows: .venv\Scripts\activate

# Install the package and dev dependencies
pip install -r requirements-dev.txt

# (Optional) install pre-commit hooks
pre-commit install
```

## Workflow

1. Fork the repository and create a feature branch from `main`.
2. Make your changes, keeping commits focused and well-described.
3. Add or update tests for the behaviour you change.
4. Run the full local check suite (see below) and make sure it passes.
5. Open a pull request describing the change and linking any related issues.

We follow [Conventional Commits](https://www.conventionalcommits.org/) for
commit messages where possible (`feat:`, `fix:`, `docs:`, `refactor:`,
`test:`, `chore:` ...). This keeps the history easy to scan and helps with
release-note generation.

## Running checks locally

Before pushing, please run:

```bash
ruff format --check .   # formatting
ruff check .            # lint
mypy                    # type-check
pytest                  # tests
```

Coverage is collected automatically by pytest's configuration; aim to keep
it from regressing.

## Pull request expectations

- Keep PRs as small and focused as practical.
- Update `CHANGELOG.md` under the `[Unreleased]` section when the change is
  user-visible.
- Update documentation (README or docstrings) when behaviour changes.
- All CI jobs (CI, Code Quality, Security) must pass before merge.

## Reporting security issues

Please **do not** open public issues for security vulnerabilities. See
[SECURITY.md](SECURITY.md) for the private reporting process.

## License

By contributing, you agree that your contributions will be licensed under the
[MIT License](LICENSE).

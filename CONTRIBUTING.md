# Contributing

Thank you for your interest in contributing to Disk Organiser. We welcome
bug reports, improvements, documentation fixes and tests.

## How to contribute

1. Fork the repository and create a topic branch for your change.
2. Run tests and linters locally, add or update tests for any behaviour change.
3. Open a pull request against the `main` branch describing the change.

## Development workflow

- Use feature branches named `feature/<short-description>` or
  `fix/<short-description>`.
- Keep commits focused and use descriptive commit messages.

## Running tests

Install dependencies and run the test-suite:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r backend/requirements.txt
pytest -q backend/tests
```

## Style and quality

- Follow existing project conventions. Keep changes minimal and well-tested.
- Ensure documentation is updated for user-facing changes.

## Submitting pull requests

- Target the `main` branch and provide a clear description of the change and
  why it is needed.
- Link any related issues and include reproduction steps when filing bugfixes.

## License for contributions

By submitting a pull request you agree that your contributions will be
licensed under the project's MIT License.

## Reporting security issues

If you discover a security vulnerability, please open a confidential issue or
contact the maintainers directly rather than posting it publicly.

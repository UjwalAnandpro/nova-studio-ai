# Contributing to Nova Studio AI

We love help and contributions from the community! Follow these steps to submit bug fixes, feature requests or improvements.

## Code of Conduct

By participating, you agree to uphold our [Code of Conduct](CODE_OF_CONDUCT.md).

## Getting Started

1. Fork this repository on GitHub.
2. Clone your fork locally:
   ```bash
   git clone https://github.com/<your-username>/nova-studio-ai.git
   cd nova-studio-ai
   ```
3. Set up a virtual environment and install dependencies:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Or venv\Scripts\activate on Windows
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   ```
4. Create a descriptive feature branch:
   ```bash
   git checkout -b feature/my-amazing-feature
   ```

## Development Guidelines

- **Formatting**: We use `black` for formatting. Run it on your files before committing:
  ```bash
  black .
  ```
- **Linting**: Ensure code follows standard pylint guidelines.
- **Testing**: Add unit tests under `tests/` for any new logic. Verify tests pass:
  ```bash
  python -m unittest discover tests
  ```

## Submitting Pull Requests

- Keep pull requests small and focused.
- Fill out the PR description template clearly detailing what problem it solves.
- Verify GitHub Action builds pass.

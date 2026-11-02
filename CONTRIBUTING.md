# Contributing and understanding TripPlanner

This class project follows specification → approval → implementation/test plan → defined and validated pytest cases → implementation. Preserve that order for new features. Start from the approved scope in [SPEC.md](SPEC.md) and the current [PLAN.md](PLAN.md); historical guides retain earlier checkpoints.

Use Python 3.14 and Node 24 for the currently tested development setup. Create a virtual environment, activate it, and install `requirements-dev.txt`. Run `python -m pytest -q` and `python release_checks.py`. Node executes actual JavaScript tests; it is not a production app dependency. The GitHub workflow runs the checks on Linux and Windows after the repository is uploaded; local preparation is not evidence that hosted CI has run.

Keep Windows build tools in `.venv-windows`, separate from the web environment. Follow [the Windows download guide](docs/windows-download.md). A successful build must be followed by actual extracted-app checks. Android is still a separate delivery.

Never commit your saved SQLite collection, `.env`, signing secrets, browser profile, virtual environments, caches, `.tmp`, or build outputs. The ignore rules are a precaution, not a repair for secrets already committed elsewhere. Review files before your first push. No account credentials belong in source or issue reports.

Preserve frozen historical test fixtures and immutable v1/v2 snapshots. New photo, theme, and native-container changes must not alter recommendation scores or saved trip hashes. Keep exact money arithmetic, CSRF, truthful gaps, external Maps behavior, and licensed photo credits.

Describe AI honestly as rule-based personalization and a greedy scheduler. Do not add claims of trained models, live prices, universal coverage, or verified platform support without corresponding work and evidence.

Original-code licensing is recorded in [CODE_LICENSE.md](CODE_LICENSE.md). Photographs and dependencies retain separate licenses. No publishing, billing, store submission, or credentials are needed to run this local project.

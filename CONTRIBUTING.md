# Contributing

Thank you for improving Professional Kanban. Parser examples, forecast edge cases,
cross-platform packaging corrections, and clearer stakeholder language are
especially useful.

## Set up

Requirements: Git and Python 3.11–3.14. The runtime and test suite use only the
Python standard library.

```bash
git clone https://github.com/ProKanban/professional-kanban-skill.git
cd professional-kanban-skill
python3 -m unittest discover -v
```

Optional platform checks require current GitHub and Claude CLIs:

```bash
gh skill publish --dry-run
claude plugin validate .
```

## Make a change

1. Open or reference an issue when behavior or compatibility will change.
2. Add a focused failing test before changing runtime behavior.
3. Implement the smallest complete fix and keep dependencies out of the packaged
   skill.
4. Run the full suite and the relevant sample command.
5. Update the changelog, README, reference docs, evals, and license mapping when
   the user-facing contract changes.

Use redacted, minimal fixtures. Never commit customer delivery data, credentials,
names, URLs, or identifiers. Synthetic fixture dates should make boundary behavior
obvious. Do not delete genuine outliers merely to make a forecast look smoother.

## Validate

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -v
python3 -m compileall -q skills/professional-kanban/scripts
python3 scripts/build_release.py
gh skill publish --dry-run
claude plugin validate .
```

Run tests on every supported Python version available to you. CI is authoritative
for the full 3.11, 3.12, 3.13, and 3.14 matrix. Generated `dist/` artifacts are not
committed.

## Pull requests

Keep commits reviewable and explain the observable problem, not just the internal
change. A pull request should include reproduction evidence, tests, compatibility
impact, documentation impact, and licensing/provenance review. By contributing,
you agree that your contribution is distributed under the license assigned to its
path in `REUSE.toml`.

Please follow the [Code of Conduct](https://www.contributor-covenant.org/version/2/1/code_of_conduct/)
in project interactions. The repository does not currently include a separately
maintained local copy; report conduct concerns privately to the project maintainers
through GitHub.

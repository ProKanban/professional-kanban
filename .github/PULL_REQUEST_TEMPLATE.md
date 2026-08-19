## Problem and outcome

<!-- What user-visible problem does this solve? Include a minimal reproduction. -->

## Verification

- [ ] I added or updated a test/eval that fails without this change.
- [ ] `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -v` passes.
- [ ] I ran the relevant sample command on a supported Python version.
- [ ] OpenAI/Claude validation still passes, or this change does not affect packaging.
- [ ] Release archives remain deterministic, or this change does not affect them.

## Compatibility and trust

- [ ] I documented user-facing or breaking behavior in `CHANGELOG.md`.
- [ ] I considered ChatGPT, Codex, Claude.ai/Desktop, and Claude Code behavior.
- [ ] I updated README/references/evals where the contract changed.
- [ ] New files have the correct SPDX/`REUSE.toml` license assignment.
- [ ] Third-party material has exact provenance and a known compatible license.
- [ ] Fixtures and examples contain no customer data, credentials, or personal data.

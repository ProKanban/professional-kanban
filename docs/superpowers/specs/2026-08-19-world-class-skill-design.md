# Professional Kanban World-Class Skill Design

**Date:** 2026-08-19  
**Status:** Awaiting specification review  
**Target branch:** `feat/world-class-skill`

## Objective

Turn the Professional Kanban skill into a trustworthy, portable, and fast-to-install distribution for ChatGPT, Codex, Claude, and Claude Code. The result must preserve the strong Kanban guidance in v1.0.0 while fixing every confirmed correctness, portability, documentation, provenance, and release-engineering issue from the adversarial review.

The release target is v1.1.0. It is complete only when every reproduced audit defect has a regression test, the packaged skill works from arbitrary installation locations, both vendor plugin packages validate, release archives are deterministic, and the repository documents the remaining GitHub owner settings that cannot be encoded in a branch.

## Guiding Decisions

1. Maintain exactly one canonical copy of the skill under `skills/professional-kanban/`.
2. Treat bundled scripts and references as paths relative to the loaded skill directory. Never hardcode a user home directory or host-specific cache path.
3. Prefer rejecting ambiguous or statistically unsupported input over silently producing a precise-looking answer.
4. Keep the runtime dependency-free: Python 3.11 or newer, standard library only.
5. Use test-first development for every behavior change.
6. Package the same canonical skill for every supported host; platform manifests are thin metadata layers, not forks of the instructions.
7. Separate branch-verifiable release quality from GitHub owner controls. CI and release documentation enforce everything possible in code; tag rulesets and immutable releases remain an explicit repository-owner checklist.

## Repository Architecture

The repository will use this layout:

```text
.
├── .codex-plugin/plugin.json
├── .claude-plugin/plugin.json
├── .claude-plugin/marketplace.json
├── .agents/plugins/marketplace.json
├── .github/
│   ├── ISSUE_TEMPLATE/
│   ├── workflows/ci.yml
│   ├── workflows/release.yml
│   └── pull_request_template.md
├── docs/
│   ├── RELEASING.md
│   └── superpowers/
├── evals/cases.json
├── LICENSES/
├── scripts/build_release.py
├── skills/professional-kanban/
│   ├── SKILL.md
│   ├── LICENSE
│   ├── agents/openai.yaml
│   ├── assets/
│   ├── references/
│   └── scripts/
├── tests/
├── CHANGELOG.md
├── CONTRIBUTING.md
├── LICENSE
├── README.md
├── REUSE.toml
├── SECURITY.md
└── THIRD_PARTY_NOTICES.md
```

The current `professional-kanban/` directory will move to `skills/professional-kanban/`. Direct installation by skill name remains compatible because Agent Skills discovery searches `skills/*/SKILL.md`. Existing v1.0.0 installations are immutable and unaffected. Release archives will still contain a single top-level `professional-kanban/` directory so ChatGPT and Claude upload workflows receive the expected bundle shape.

`.codex-plugin/plugin.json` is the OpenAI plugin entry point. `.claude-plugin/plugin.json` is the Claude plugin entry point. Each references `./skills/` and contains only supported fields. The repo-local marketplace files expose the plugin for local validation and testing; public marketplace submission remains a documented release operation because it requires publisher credentials and external approval.

## Portable Resource Resolution

`SKILL.md` will instruct the host to resolve scripts relative to the directory containing the active `SKILL.md`. It will give host-specific examples only where a stable host variable exists:

- Claude Code: `${CLAUDE_SKILL_DIR}/scripts`
- Other Agent Skills hosts: locate the active skill root and execute `scripts/<name>.py` from it
- Human CLI use: invoke the checked-out path shown in the README

No instruction will assume `~/.claude`, `$HOME/.agents`, the current working directory, or a platform-specific path separator. The README will use `gh skill install` for local Claude Code and Codex installation, while upload and plugin paths retain all bundled resources for desktop and hosted use.

## Data Parsing Contract

### Dates

ISO `YYYY-MM-DD` is the default and recommended format. Unambiguous textual formats remain accepted. Numeric slash or dash dates where both the day and month are at most 12 are ambiguous and must fail with an actionable error unless the user supplies `--date-order mdy` or `--date-order dmy`.

All CLI date options use strict ISO parsing. Invalid `--from`, `--to`, `--as-of`, `--start`, and `--by` values fail immediately. A historical window with `from > to` fails immediately.

### Columns

Column detection uses normalized exact aliases first. A fallback may match complete normalized tokens such as `story_finished_on`, but must not match arbitrary substrings. In particular, `Country` and `Account` must never match `count`, and `Completed Date` must not independently become both a completion date and generic period column.

When multiple equally plausible columns exist, the loader fails and lists the candidates instead of choosing silently. Extra unrelated columns remain ignored.

### Input shapes

Completion rows remain the preferred throughput input. Period/count input is represented directly as dated counts rather than expanding each count into repeated dates. This preserves leading, interior, and trailing zero periods and prevents memory growth proportional to the count value.

The loader infers weekly data from explicit weekly headers. Daily completion data defaults to daily sampling. A conflicting explicit `--unit` fails with an explanation rather than silently changing the meaning of the data.

Cycle-time-column input accepts only positive finite numbers. `NaN`, infinities, zero, and negative durations are rejected with row information. Historical date-window flags are rejected when the input has no finish-date column and therefore cannot be filtered honestly.

## Forecasting Contract

### Argument validation

- `--items` is a positive integer.
- `--split` is finite and greater than zero.
- `--trials` is a positive integer.
- Confidence levels and percentiles are finite and strictly between 0 and 100.
- Workday specifications must contain at least one valid weekday.
- `--days` is a positive count of calendar days.
- Daily and weekly horizon options cannot be mixed.

Invalid arguments exit with a concise message and no traceback.

### Horizons

A daily `--days N` horizon covers exactly `start` through `start + N - 1` calendar days. Therefore a one-day weekend horizon contains zero Monday-to-Friday work periods.

Weekly sampling uses a new `--weeks N` horizon. A day- or date-based horizon that is not an exact number of seven-day weekly periods is rejected when the source unit is weekly. The tool does not prorate weekly throughput because the historical input cannot justify the within-week distribution.

### Simulations

The lower bound for “X% chance of N items or more” is the largest observed simulated outcome for which at least X% of trials are at or above N. Exact probability boundaries must therefore choose the useful valid bound rather than the preceding outcome.

The `when` simulation cap is calculated from the split-adjusted effective item count and observed positive throughput. Every trial records whether it completed. If any requested confidence percentile depends on truncated trials, the command fails with an explanation and recommends inspecting the data or reducing the forecast size. It never labels a capped unfinished trial as complete.

Seeds continue to provide repeatable results. Output always states the sampling unit, historical window, number of trials, horizon definition, and scope-growth multiplier when used.

## Cycle-Time and Aging Contract

WIP items with starts after `--as-of` are rejected with item and row information. Missing starts remain excluded and disclosed; completed rows remain excluded and disclosed.

The tool always calculates the 50th and 70th percentile internally for aging signals, even if the user requests a different display table. The requested SLE percentile is likewise always present.

Risk language is calculated empirically. For an item at age A below the SLE, the reported conditional breach rate is the fraction of completed historical items that took longer than the SLE among those that reached at least age A. If the comparison population is too small, the output says the evidence is thin rather than manufacturing a percentage. A custom SLE therefore changes the risk statement correctly.

## Skill Instruction Quality

The frontmatter description will be shortened and front-loaded with the most discriminating triggers. It will cover Kanban delivery forecasting, flow metrics, SLEs, throughput, and work-item aging without claiming unrelated timing tasks such as file copies or package delivery. Negative boundaries will direct unrelated project scheduling, personal productivity, logistics, and generic arithmetic away from the skill.

The body will retain the one-item versus many-item fork, honest probability language, actionable aging emphasis, data-quality guidance, and stakeholder phrasing. Script flags will be documented per script rather than described as universally available.

`agents/openai.yaml` will provide a display name, concise description, brand color, and three representative starter prompts. It will not declare tool dependencies because the skill is self-contained.

## Installation and README Experience

The first README screen will contain:

1. One-sentence value proposition.
2. A 30-second example prompt and abbreviated output.
3. Pinned `gh skill install` commands for Claude Code and Codex.
4. Upload instructions for ChatGPT and Claude desktop/web using the release ZIP.
5. Plugin/marketplace instructions for managed installation.

A platform matrix will distinguish ChatGPT, Codex, Claude desktop/web, and Claude Code. It will document availability/admin caveats without saying a host categorically cannot load skills. Separate sections will cover update, uninstall, local development, supported CSV shapes, Python support, privacy, troubleshooting, and licensing.

Python support is 3.11 through 3.14. Runtime remains standard-library only.

## Tests and Evaluations

The test suite uses `unittest` so contributor setup remains dependency-free. Unit tests cover parsing, percentile boundaries, throughput construction, period calculations, simulation completion tracking, and empirical aging risk. CLI integration tests invoke each command in subprocesses and assert exit codes, output, and absence of tracebacks.

Regression fixtures cover every confirmed audit defect:

- ambiguous US/UK dates
- `Country` and `Account` false count matches
- leading and trailing zero periods
- weekly data with an invalid partial-week horizon
- weekend one-day horizons
- zero and negative split values
- invalid confidence and percentile values
- zero trials
- capped unfinished forecasts
- future WIP starts
- custom SLE risk language
- custom display percentiles
- invalid filter dates
- cycle-time columns combined with unusable window filters
- non-finite cycle times
- exact lower-confidence boundaries
- flags advertised to the wrong command

`evals/cases.json` contains positive, neighboring, and negative trigger prompts plus expected routing and safety behaviors. CI validates its schema and verifies that every named behavior is represented in `SKILL.md`. Model-based quality evaluation remains a release review step because CI has no vendor credentials.

## Release Engineering

`scripts/build_release.py` constructs both `professional-kanban.zip` and `professional-kanban.skill` from the canonical skill. It sorts paths, normalizes timestamps, permissions, and archive roots, excludes caches, and writes SHA-256 checksums. Running it twice on an unchanged tree must produce identical bytes.

CI runs on Python 3.11, 3.12, 3.13, and 3.14. It performs tests, bytecode compilation, JSON/YAML/frontmatter validation, OpenAI plugin validation, Claude plugin validation when the CLI is available, `gh skill publish --dry-run`, deterministic-build comparison, archive-content comparison, and clean install smoke tests.

The release workflow runs only for semantic-version tags, rebuilds artifacts in CI, verifies the version matches both manifests and the changelog, generates checksums, and attaches the artifacts to the GitHub release. Actions will be pinned to immutable commit SHAs.

`docs/RELEASING.md` requires an annotated signed tag, protected `v*` tag rules, immutable GitHub releases, successful CI, artifact attestation, marketplace validation, and fresh ChatGPT/Claude upload smoke tests. Settings that require repository-owner access are clearly marked as owner actions rather than falsely presented as branch-enforced guarantees.

## Licensing and Provenance

The repository retains its license split:

- Python scripts: MIT
- Skill instructions, references, and repository documentation: CC BY-SA 4.0
- Synthetic examples: CC0-1.0

`LICENSES/` contains the complete license texts. `REUSE.toml` maps paths to SPDX identifiers, and Python files carry SPDX headers. The packaged skill retains a concise `LICENSE` file and the SKILL frontmatter includes `license: See LICENSE`.

`THIRD_PARTY_NOTICES.md` identifies exact source titles, versions, authors, URLs, and known licenses. It describes the public provenance of the Pocket Guide material without inventing a license notice or private permission that is not in the repository record. ProKanban and PKT trademark exclusions remain explicit.

## Community and Maintenance

`CONTRIBUTING.md` defines setup, TDD expectations, test commands, supported Python versions, fixture hygiene, commit guidance, and the release-validation command. `SECURITY.md` defines supported versions and a private disclosure route using GitHub Security Advisories. Issue forms separate parser defects, forecast defects, and documentation requests. The PR template requires tests, compatibility impact, licensing review, and reproducible-build confirmation.

`CHANGELOG.md` follows Keep a Changelog and records all v1.1.0 breaking behavior, especially ambiguous-date rejection, strict validation, weekly horizons, Python 3.11 minimum, and the canonical path move.

## Acceptance Criteria

The implementation is accepted only when all of the following are true:

1. Every audit reproduction is represented by a test that failed before its fix and now passes.
2. The entire test suite passes on Python 3.11 through 3.14 in CI configuration and on the local available interpreter.
3. Sample SLE, aging, how-many, and when commands succeed with coherent output.
4. Arbitrary-directory installations can locate and run bundled scripts without a Claude-specific home path.
5. OpenAI and Claude plugin validators pass without errors.
6. `gh skill publish --dry-run` has no skill-metadata warnings attributable to repository files.
7. Two clean builds produce identical ZIP, `.skill`, and checksum bytes.
8. Each archive contains one `professional-kanban/` root and exactly the canonical distributable files.
9. A clean GitHub skill installation succeeds from the branch layout.
10. README commands are exercised as smoke tests where they do not require an interactive account.
11. The working tree contains no caches or generated artifacts after verification.
12. A final adversarial review reports no unresolved critical or major defects. Legal conclusions and external marketplace approval remain outside the score.

## Non-Goals

- No hosted service, MCP server, telemetry, database, or network dependency.
- No graphical application or custom ChatGPT UI.
- No changes to Kanban doctrine beyond corrections required for statistical honesty and source clarity.
- No external marketplace submission, GitHub ruleset mutation, immutable-release setting change, or release publication from the feature branch.
- No promise that a model will invoke the skill perfectly; trigger quality is evaluated and documented, not represented as deterministic.

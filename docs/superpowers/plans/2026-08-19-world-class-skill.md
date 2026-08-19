# Professional Kanban World-Class Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a v1.1.0-ready Professional Kanban skill whose calculations, packaging, documentation, licensing, and release process meet the approved cross-platform quality bar.

**Architecture:** Keep one canonical Agent Skills package under `skills/professional-kanban/`; expose it through OpenAI and Claude manifests; keep all calculations in dependency-free Python modules; use strict parsing and explicit result objects so invalid or truncated data cannot become confident prose. Build upload artifacts deterministically from the canonical directory and validate every supported installation route in tests and CI.

**Tech Stack:** Python 3.11–3.14 standard library, `unittest`, JSON/YAML metadata, GitHub Actions, GitHub CLI skill commands, Claude Code plugin validation.

**Spec:** `docs/superpowers/specs/2026-08-19-world-class-skill-design.md`

## Global Constraints

- Runtime support is Python 3.11 through 3.14 with no third-party packages.
- ISO `YYYY-MM-DD` is the default date format; ambiguous numeric dates require `--date-order`.
- Invalid, ambiguous, or statistically unsupported inputs fail clearly and never produce a forecast.
- The canonical skill exists only at `skills/professional-kanban/`.
- Upload artifacts contain exactly one top-level `professional-kanban/` directory.
- User home directories and host-specific installation roots are never hardcoded.
- Documentation is CC BY-SA 4.0, scripts are MIT, and synthetic assets are CC0-1.0.
- No external marketplace submission or repository-settings mutation is performed from this branch.

---

### Task 1: Canonical package layout and executable test harness

**Files:**
- Move: `professional-kanban/` → `skills/professional-kanban/`
- Create: `tests/__init__.py`
- Create: `tests/support.py`
- Create: `tests/test_package_layout.py`
- Modify: `.gitignore`

**Interfaces:**
- Produces: `SKILL_ROOT: pathlib.Path`, `SCRIPTS_ROOT: pathlib.Path`, and `run_cli(script, *args)` for all later tests.
- Preserves: `gh skill install ... professional-kanban` discovery by the `skills/*/SKILL.md` convention.

- [ ] **Step 1: Write the failing layout test**

```python
class PackageLayoutTests(unittest.TestCase):
    def test_canonical_skill_has_required_resources(self):
        self.assertTrue((SKILL_ROOT / "SKILL.md").is_file())
        self.assertTrue((SKILL_ROOT / "scripts" / "monte_carlo.py").is_file())
        self.assertFalse((REPO_ROOT / "professional-kanban").exists())
```

- [ ] **Step 2: Run the layout test and verify it fails because the old path still exists**

Run: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_package_layout -v`

- [ ] **Step 3: Move the skill, add reusable subprocess/import helpers, and ignore Python/build artifacts**

`tests/support.py` must insert `skills/professional-kanban/scripts` into `sys.path` and run commands with `PYTHONDONTWRITEBYTECODE=1` so verification leaves the tree clean.

- [ ] **Step 4: Run the layout test and baseline sample commands**

Run: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_package_layout -v`

- [ ] **Step 5: Commit**

```bash
git add .gitignore skills tests
git commit -m "refactor: establish canonical skill package"
```

### Task 2: Strict date and column parsing

**Files:**
- Modify: `skills/professional-kanban/scripts/flowlib.py`
- Modify: `skills/professional-kanban/scripts/cycle_time.py`
- Modify: `skills/professional-kanban/scripts/monte_carlo.py`
- Create: `tests/fixtures/ambiguous-dates.csv`
- Create: `tests/fixtures/completed-with-country.csv`
- Create: `tests/test_flowlib.py`
- Create: `tests/test_parsing_cli.py`

**Interfaces:**
- Produces: `parse_date(value, date_order=None, strict_iso=False) -> date | None`.
- Produces: `find_column(headers, candidates, *, exclude=()) -> str | None`, raising `ValueError` for equally plausible matches.
- Consumes: `run_cli` from Task 1.

- [ ] **Step 1: Add failing unit tests for ambiguous dates and false substring matches**

```python
def test_ambiguous_numeric_date_requires_order(self):
    with self.assertRaisesRegex(ValueError, "ambiguous date"):
        flowlib.parse_date("05/01/2026")

def test_explicit_mdy_resolves_ambiguous_date(self):
    self.assertEqual(flowlib.parse_date("05/01/2026", "mdy"), date(2026, 5, 1))

def test_country_does_not_match_count(self):
    headers = {"country": "Country", "completeddate": "Completed Date"}
    self.assertIsNone(flowlib.find_column(headers, flowlib.COUNT_NAMES))
```

- [ ] **Step 2: Run the focused tests and verify the current parser fails them for the audited reasons**

Run: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_flowlib -v`

- [ ] **Step 3: Implement date-order-aware parsing and token-boundary column matching**

The parser must reject only genuinely ambiguous numeric dates, preserve ISO/text formats, and include the rejected value in its message. CLI option dates use `strict_iso=True`. Column matching must prefer normalized exact aliases and match fallback aliases only at token boundaries derived from the original header.

- [ ] **Step 4: Add failing CLI tests for invalid filter dates, reversed windows, and ambiguous CSV rows**

```python
def test_invalid_window_date_is_not_silently_ignored(self):
    result = run_cli("monte_carlo.py", "how-many", "--input", sample, "--days", "30", "--from", "nonsense")
    self.assertEqual(result.returncode, 2)
    self.assertIn("--from must use YYYY-MM-DD", result.stderr)
```

- [ ] **Step 5: Wire `--date-order {mdy,dmy}` through both commands and convert parse failures into concise parser errors**

- [ ] **Step 6: Run focused and full tests**

Run: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_flowlib tests.test_parsing_cli -v`

- [ ] **Step 7: Commit**

```bash
git add skills/professional-kanban/scripts tests
git commit -m "fix: make date and column parsing unambiguous"
```

### Task 3: Lossless throughput series and honest horizons

**Files:**
- Modify: `skills/professional-kanban/scripts/flowlib.py`
- Modify: `skills/professional-kanban/scripts/monte_carlo.py`
- Create: `tests/fixtures/weekly-with-zero-edges.csv`
- Create: `tests/test_throughput.py`
- Create: `tests/test_horizons.py`

**Interfaces:**
- Produces: a `ThroughputHistory` dataclass with `series`, `first`, `last`, `item_count`, `source`, and `unit`.
- Produces: `working_periods_between(start, end, unit, workdays) -> int` with inclusive calendar semantics.
- Adds: `--weeks` for weekly how-many forecasts.

- [ ] **Step 1: Add a failing test proving explicit zero periods and boundaries survive loading**

```python
def test_period_counts_preserve_zero_edges(self):
    history = monte_carlo.load_throughput(fixture, None, "mon-fri", None, None, None)
    self.assertEqual(history.series, [0, 5, 0])
    self.assertEqual((history.first, history.last), (date(2026, 6, 1), date(2026, 6, 15)))
    self.assertEqual(history.unit, "week")
```

- [ ] **Step 2: Run the focused test and verify the current `[5]` result**

- [ ] **Step 3: Implement direct period/count aggregation without repeated-date expansion**

Reject negative/non-finite counts and duplicate periods with conflicting values. Fill missing periods between explicit boundaries with zeros. Infer `week` from weekly aliases and `day` otherwise.

- [ ] **Step 4: Add failing tests for weekend one-day horizons and partial weekly horizons**

```python
def test_one_calendar_day_on_saturday_has_no_weekday_periods(self):
    self.assertEqual(working_periods_between(date(2026, 8, 22), date(2026, 8, 22), "day", weekdays), 0)

def test_weekly_history_rejects_days_horizon(self):
    result = run_cli("monte_carlo.py", "how-many", "--input", weekly, "--days", "1")
    self.assertEqual(result.returncode, 2)
    self.assertIn("use --weeks", result.stderr)
```

- [ ] **Step 5: Implement exact daily horizons and explicit weekly horizons**

`--days N` ends at `start + N - 1`. Weekly inputs require `--weeks N`; `--by` is accepted only when the inclusive interval is a whole number of seven-day periods.

- [ ] **Step 6: Run focused and full tests, then commit**

```bash
git add skills/professional-kanban/scripts tests
git commit -m "fix: preserve throughput periods and forecast horizons"
```

### Task 4: Validated and completion-aware Monte Carlo

**Files:**
- Modify: `skills/professional-kanban/scripts/flowlib.py`
- Modify: `skills/professional-kanban/scripts/monte_carlo.py`
- Create: `tests/test_monte_carlo.py`
- Create: `tests/test_monte_carlo_cli.py`

**Interfaces:**
- Produces: `lower_bound(values, confidence) -> int`.
- Produces: `SimulationRun(periods: int, completed: bool)` from `sim_when`.
- Produces: reusable argparse validators for positive integers and finite percentages/multipliers.

- [ ] **Step 1: Add failing tests for exact lower-bound behavior and completion state**

```python
def test_lower_bound_uses_largest_value_meeting_confidence(self):
    self.assertEqual(flowlib.lower_bound([0] * 15 + [1] * 85, 85), 1)

def test_sim_when_marks_capped_trial_unfinished(self):
    run = monte_carlo.sim_when([1], 100_000, 1, random.Random(7), 200)[0]
    self.assertFalse(run.completed)
    self.assertEqual(run.periods, 200)
```

- [ ] **Step 2: Verify both tests fail against v1.0.0 behavior**

- [ ] **Step 3: Implement the confidence-bound selector and completion-aware result**

- [ ] **Step 4: Add failing CLI tests for zero/negative split, zero trials, invalid confidence, non-positive items, and capped simulations**

Each case must assert exit code 2, a specific actionable message, and no `Traceback`.

- [ ] **Step 5: Add strict validators and calculate the cap from effective scope and observed positive throughput**

If a confidence result would include an unfinished trial, stop without publishing a completion date.

- [ ] **Step 6: Run all Monte Carlo tests and sample forecasts**

Run: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_monte_carlo tests.test_monte_carlo_cli -v`

- [ ] **Step 7: Commit**

```bash
git add skills/professional-kanban/scripts tests
git commit -m "fix: validate and bound Monte Carlo forecasts"
```

### Task 5: Reliable cycle-time and aging signals

**Files:**
- Modify: `skills/professional-kanban/scripts/cycle_time.py`
- Create: `tests/fixtures/future-wip.csv`
- Create: `tests/fixtures/non-finite-cycle-times.csv`
- Create: `tests/test_cycle_time.py`
- Create: `tests/test_cycle_time_cli.py`

**Interfaces:**
- Produces: `conditional_breach_rate(values, age, sle_days) -> tuple[int, int]` returning breach and comparison counts.
- Ensures: internal 50th/70th/SLE thresholds independent of displayed percentiles.

- [ ] **Step 1: Add failing tests for future WIP dates, non-finite durations, and unusable window filters**

```python
def test_future_wip_start_is_rejected(self):
    with self.assertRaisesRegex(ValueError, "after the as-of date"):
        cycle_time.load_wip(fixture, date(2026, 8, 1))

def test_nan_cycle_time_is_rejected(self):
    result = run_cli("cycle_time.py", "sle", "--input", fixture)
    self.assertEqual(result.returncode, 2)
    self.assertIn("finite positive number", result.stderr)
```

- [ ] **Step 2: Verify the audited negative-age and NaN behaviors fail the new expectations**

- [ ] **Step 3: Implement strict duration/WIP validation and reject unfilterable cycle-time-only windows**

- [ ] **Step 4: Add failing tests for custom percentile tables and empirical custom-SLE language**

The test fixture must make the 95th-percentile conditional breach rate visibly different from 50%.

- [ ] **Step 5: Implement hidden threshold calculation and empirical risk messaging**

Use completed items with duration at least the current age as the comparison population. If fewer than five comparable items exist, report thin evidence without a percentage.

- [ ] **Step 6: Run aging tests and sample aging command, then commit**

```bash
git add skills/professional-kanban/scripts tests
git commit -m "fix: make aging signals data-driven"
```

### Task 6: Cross-platform skill and plugin metadata

**Files:**
- Modify: `skills/professional-kanban/SKILL.md`
- Create: `skills/professional-kanban/agents/openai.yaml`
- Create: `.codex-plugin/plugin.json`
- Create: `.claude-plugin/plugin.json`
- Create: `.agents/plugins/marketplace.json`
- Create: `.claude-plugin/marketplace.json`
- Create: `evals/cases.json`
- Create: `tests/test_skill_metadata.py`
- Create: `tests/test_evals.py`

**Interfaces:**
- Produces: one discoverable `professional-kanban` skill and two valid plugin manifests at version `1.1.0`.
- Produces: positive, neighboring, and negative invocation cases with stable IDs and expected behavior strings.

- [ ] **Step 1: Add failing metadata tests**

Tests assert one canonical `SKILL.md`, `license: See LICENSE`, a description no longer than 1024 characters, no `~/.claude` path, per-command flags, required manifest fields, valid relative paths, three or fewer starter prompts, and no unsupported MCP/app declarations.

- [ ] **Step 2: Verify metadata tests fail on the current layout/content**

- [ ] **Step 3: Rewrite the trigger description and script instructions, then create OpenAI metadata**

The description must explicitly exclude logistics, personal scheduling, file-transfer timing, and generic arithmetic. Script instructions resolve resources from the active skill root and use `${CLAUDE_SKILL_DIR}` only as a Claude Code example.

- [ ] **Step 4: Create both manifests and repo-local marketplace entries using current official schemas**

OpenAI and Claude manifests use the same name/version/description/author/repository values and reference `./skills/`. Marketplace sources resolve to the repository plugin root and declare productivity categorization without product gating.

- [ ] **Step 5: Add evaluation cases and schema tests**

Every case includes `id`, `prompt`, `should_trigger`, and `expected_behaviors`. At least eight positive and eight negative/neighboring cases are required.

- [ ] **Step 6: Run local skill/plugin validators and focused tests, then commit**

```bash
git add .agents .claude-plugin .codex-plugin evals skills/professional-kanban tests
git commit -m "feat: package skill for OpenAI and Claude"
```

### Task 7: Licensing, contributor, and product documentation

**Files:**
- Modify: `README.md`
- Modify: `LICENSE`
- Modify: `skills/professional-kanban/LICENSE`
- Modify: `skills/professional-kanban/references/data-prep.md`
- Create: `LICENSES/MIT.txt`
- Create: `LICENSES/CC-BY-SA-4.0.txt`
- Create: `LICENSES/CC0-1.0.txt`
- Create: `REUSE.toml`
- Create: `THIRD_PARTY_NOTICES.md`
- Create: `CHANGELOG.md`
- Create: `CONTRIBUTING.md`
- Create: `SECURITY.md`
- Create: `.github/ISSUE_TEMPLATE/parser.yml`
- Create: `.github/ISSUE_TEMPLATE/forecast.yml`
- Create: `.github/ISSUE_TEMPLATE/documentation.yml`
- Create: `.github/pull_request_template.md`
- Create: `tests/test_documentation.py`

**Interfaces:**
- Produces: executable install/update/uninstall commands and a complete distribution/provenance contract.

- [ ] **Step 1: Add failing documentation tests for obsolete claims and required install/security/provenance sections**

Tests reject “tools don't load skills,” raw `cp` installation, Python 3.8, missing update/uninstall commands, missing privacy language, missing source versions, and inconsistent supported input/flag descriptions.

- [ ] **Step 2: Verify the current README and references fail the tests**

- [ ] **Step 3: Rewrite the README around a 30-second prompt, platform matrix, pinned installs, upload path, updates, uninstall, privacy, troubleshooting, and contributor entry points**

- [ ] **Step 4: Add SPDX/REUSE license material and exact third-party notices**

Do not claim an unpublished permission or public license for either Pocket Guide. State the observable author/publisher provenance and preserve attribution/trademark limitations.

- [ ] **Step 5: Add contributor, security, changelog, issue, and PR workflows**

- [ ] **Step 6: Run documentation tests, link/path checks, and `git diff --check`, then commit**

```bash
git add README.md LICENSE LICENSES REUSE.toml THIRD_PARTY_NOTICES.md CHANGELOG.md CONTRIBUTING.md SECURITY.md .github skills tests
git commit -m "docs: publish complete install and trust guidance"
```

### Task 8: Deterministic builds, CI, and release controls

**Files:**
- Create: `scripts/build_release.py`
- Create: `tests/test_release_build.py`
- Create: `.github/workflows/ci.yml`
- Create: `.github/workflows/release.yml`
- Create: `docs/RELEASING.md`

**Interfaces:**
- Produces: `dist/professional-kanban.zip`, `dist/professional-kanban.skill`, and `dist/SHA256SUMS`.
- Produces: `build_archive(source, target) -> str` returning a SHA-256 digest.

- [ ] **Step 1: Add failing release-build tests**

```python
def test_two_builds_are_byte_identical(self):
    first = build_into(self.tempdir / "one")
    second = build_into(self.tempdir / "two")
    self.assertEqual(first.zip.read_bytes(), second.zip.read_bytes())
    self.assertEqual(first.skill.read_bytes(), second.skill.read_bytes())

def test_archive_has_single_clean_skill_root(self):
    with zipfile.ZipFile(archive) as bundle:
        self.assertTrue(all(name.startswith("professional-kanban/") for name in bundle.namelist()))
        self.assertFalse(any("__pycache__" in name for name in bundle.namelist()))
```

- [ ] **Step 2: Verify the build module is absent and tests fail**

- [ ] **Step 3: Implement deterministic ZIP construction**

Sort paths; use the ZIP epoch timestamp; normalize files to mode `0644`; use fixed compression settings; write POSIX separators; exclude caches and editor files; generate both extensions from identical content; write stable sorted checksums.

- [ ] **Step 4: Add pinned CI and release workflows plus the owner-controlled release checklist**

CI runs the full test suite on Python 3.11–3.14, compiles source without writing into the tree, validates JSON/frontmatter/plugins, runs `gh skill publish --dry-run` when the preview extension is available, compares two builds, inspects archives, and confirms a clean worktree. Release runs only on `v*` tags, checks manifest/changelog versions, builds once, attests artifacts, and uploads them.

- [ ] **Step 5: Run build tests, build twice, compare checksums, and inspect both archives**

- [ ] **Step 6: Run all locally available validators and the complete suite**

Run: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -v`

- [ ] **Step 7: Commit**

```bash
git add scripts tests .github/workflows docs/RELEASING.md
git commit -m "ci: make skill releases reproducible"
```

### Task 9: Full-story verification and adversarial closeout

**Files:**
- Modify only files implicated by verification failures.

**Interfaces:**
- Consumes: all earlier tasks.
- Produces: evidence for every acceptance criterion and a clean branch ready for review.

- [ ] **Step 1: Run the complete tests on the local interpreter**

Run: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -v`

- [ ] **Step 2: Run sample SLE, aging, daily how-many, weekly how-many, and when forecasts**

- [ ] **Step 3: Run plugin, skill, JSON, frontmatter, compilation, documentation, and packaged-install validation**

- [ ] **Step 4: Reproduce every original adversarial probe and confirm safe behavior**

- [ ] **Step 5: Build twice from a clean tree and compare every artifact byte-for-byte**

- [ ] **Step 6: Inspect `git diff`, commit history, status, and generated artifact exclusions**

- [ ] **Step 7: Request an independent code review and resolve every critical or major finding**

- [ ] **Step 8: Commit any verified closeout fixes and prepare the final scorecard**

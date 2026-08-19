# Changelog

All notable changes are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project uses
[Semantic Versioning](https://semver.org/).

## [Unreleased]

## [1.1.0] - 2026-08-19

### Added

- One canonical `skills/professional-kanban/` package for Agent Skills hosts.
- OpenAI and Claude plugin manifests and marketplace catalogs.
- OpenAI UI metadata plus positive and negative trigger evaluations.
- Exact weekly horizons with `--weeks`, strict `--date-order`, and deterministic
  start-date support for how-many forecasts.
- Empirical conditional risk for aging work.
- Python 3.11–3.14 test coverage and deterministic release packaging.

### Changed

- **Breaking:** Python 3.11 is now the minimum supported runtime.
- **Breaking:** ambiguous numeric dates now require `--date-order mdy` or
  `--date-order dmy`; CLI date flags require ISO `YYYY-MM-DD`.
- **Breaking:** period/count input is preserved directly, including zero periods,
  instead of being expanded into repeated completion rows.
- **Breaking:** weekly input rejects partial-week daily/date horizons.
- **Breaking:** invalid scope, confidence, percentile, trial, date-window, and
  workday values fail instead of being silently accepted.
- **Breaking:** the skill moved from `professional-kanban/` to the standard
  `skills/professional-kanban/` path.
- Forecast bounds now use exact at-or-above probabilities and never label capped,
  unfinished trials as completed.
- Column fallback matching uses token boundaries and no longer mistakes headers
  such as `Country` or `Account` for throughput counts.

### Fixed

- Leading and trailing zero-throughput periods are retained.
- Daily horizons cover exactly the stated number of calendar days.
- WIP starts after the analysis date, non-finite cycle times, reversed windows,
  and unusable cycle-time-only filters are rejected with actionable errors.
- Aging always computes its internal p50, p70, and SLE thresholds even when the
  displayed percentile table is customized.

[Unreleased]: https://github.com/ProKanban/professional-kanban-skill/compare/v1.1.0...HEAD
[1.1.0]: https://github.com/ProKanban/professional-kanban-skill/compare/v1.0.0...v1.1.0

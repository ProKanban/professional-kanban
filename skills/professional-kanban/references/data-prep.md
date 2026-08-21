# Data preparation

Read this when a user's export will not load, when you need to decide which
historical window to use, or when there is little or no data.

## Contents

- Accepted file shapes
- Column detection
- Exports from Jira, Azure DevOps, Trello, GitHub
- Choosing the historical window
- Thin data and no data
- What counts as invalid data
- Common data problems and what they mean

## Accepted file shapes

The scripts read CSV or TSV with a header row. Three shapes work.

**Shape A — one row per finished item, with dates.** The most common export, and
the most useful because it supports both throughput and cycle time.

```csv
key,started,finished
ENG-1041,2026-07-02,2026-07-09
ENG-1042,2026-07-03,2026-07-11
```

**Shape B — one row per period, with a count.** Enough for Monte Carlo, not enough
for cycle time or SLE.

```csv
week,count
2026-06-01,9
2026-06-08,12
```

**Shape C — one row per item, with a cycle time already calculated.** Enough for
SLE and right-sizing, not enough for Monte Carlo.

```csv
key,cycle_time
ENG-1041,8
ENG-1042,9
```

Extra columns are ignored, so an unmodified export is usually fine to pass
straight in.

For `cycle_time.py aging`, the WIP file needs a started column, and optionally an
item name/key and a state/status column:

```csv
key,status,started
ENG-2003,In Progress,2026-07-20
ENG-2004,Blocked,2026-07-06
```

## Column detection

Headers are matched case-insensitively after spaces, underscores, and hyphens are
normalized. Exact aliases are preferred; fallback matching uses complete normalized
tokens, so `Story Finished On` matches `finished` while unrelated headers such as
`Country` and `Account` do not match `count`. If equally plausible columns exist,
rename the intended one instead of relying on column order.

| Role | Recognised names |
|---|---|
| Finished | finished, completed, done, closed, resolved, end date, completion date, delivery date |
| Started | started, start, begin, in progress, activated, committed, commitment date |
| Count | count, throughput, items, item count, delivered |
| Cycle time | cycle time, flow time, lead time, days, duration, elapsed |
| Period | date, week, week ending, period, day, month |
| Item name | item, name, id, key, title, ticket, summary, issue, card |
| State | state, status, column, stage, step |

ISO and written-month dates are parsed directly, and ISO timestamps are trimmed to
their date part. Numeric dates where both the first and second component are 12 or
less are ambiguous: `04/05/2026` fails until `--date-order mdy` or
`--date-order dmy` is supplied. Prefer ISO `YYYY-MM-DD` whenever possible. CLI date
options are always strict ISO. If a file will not load, the error prints the headers
it actually saw—rename the relevant column and rerun rather than reformatting the
whole file.

For period/count files, zero counts are real observations and remain in the sample.
Missing periods between the first and last observation are also represented as zero.
Use a `week` or `week ending` header for weekly data; weekly forecasts use
`--weeks`, while daily completion data uses `--days` or `--by`.

## Exports from common tools

**Jira.** Export the filtered issue list as CSV. The useful columns are `Created`,
`Resolved`, and any status-change timestamp. `Created` is almost never the started
point — an item can sit in a backlog for months. Prefer a "moved to In Progress"
date if the export has one; if not, say explicitly that cycle time is being measured
from creation and that it will overstate the numbers.

**Azure DevOps.** `Activated Date` is usually the started point and `Closed Date` the
finished point. `Created Date` has the same backlog problem as Jira.

**Trello / Monday / Asana.** Usually only a completion date is available, which
supports Monte Carlo but not cycle time. That is fine — throughput is the more
valuable of the two for the questions people ask most.

**GitHub.** PR merge dates work as completion dates. Opened-to-merged is a real
cycle time as long as everyone understands that "started" means "PR opened", which
excludes the work done before the PR existed.

Whichever is used: the started and finished points must match the team's Definition
of Workflow. If the DoW is unknown, ask what "started" means for them before
calculating anything. The numbers are only as meaningful as that definition.

## Choosing the historical window

The core assumption of Monte Carlo is that the future roughly resembles the past
you have data for. Choose the window deliberately with `--from` and `--to`:

- **More data helps only while it still reflects the current process, team, and
  policies.** Past that point you are mixing in a system that no longer exists.
- **Cut the window at a known break** — a reorganization, a major workflow change, a
  team that halved or doubled. Data from before the break describes a different
  system.
- **Holiday periods** are a judgement call. If the forecast horizon includes a
  similar shutdown, leaving them in is realistic. If it does not, they will drag
  the forecast pessimistic.
- A rolling window of the last 8–12 weeks is a reasonable default when nothing
  specific argues otherwise.

Run the forecast on two windows when the choice is genuinely unclear and show both.
The difference between them is itself information about how stable the system is.

## Thin data and no data

**You need less data than most people assume.** About 10 data points to start, and
around 20 to be fairly confident. The scripts warn when the input falls below these.

With nothing at all, in this order:

1. **Collect some.** A couple of weeks of throughput is usually enough to begin.
2. **Borrow it.** Use a similar recent effort by a similar team through a similar
   workflow, and label it as borrowed.
3. **Guess and refine.** Make the guess explicit, forecast with it, and replace it
   as real data arrives.

Never let missing data become a reason to fall back on story points or an average.
A labelled guess that gets refined beats a confident number with nothing behind it.

## What counts as invalid data

**Do not clean outliers.** An item that took 60 days when the 85th percentile is 12
is the process telling you where it hurts. That is signal, and removing it makes the
forecast optimistic in exactly the way that gets teams in trouble.

Remove or correct data only when it is genuinely invalid:

- A ticket nobody closed, marked done months after the work finished
- A period when the workflow was not yet defined
- Duplicates, or test and template items that never represented real work
- Items with a finish date before their start date—the scripts exclude these and
  report the skipped-row count; correct the source record when possible

Already-calculated cycle-time input must contain positive finite numbers. Zero,
negative values, `NaN`, and infinities are rejected. `--from` / `--to` cannot be
used with cycle-time-only input because there is no finish date to filter honestly.

Do not transform, normalize, or fit throughput to a known distribution. Sample the
raw data.

## Common data problems and what they mean

| What you see | What it usually means |
|---|---|
| Many items with cycle time of exactly 1 day | Started and finished are being stamped at the same moment; the started point is probably wrong |
| A long tail of very old items | Real, and worth discussing. Do not trim it — it is the aging problem made visible |
| Throughput of zero for long stretches | Either the team was not working, or items are not being marked finished. Ask which |
| Cycle times measured in the hundreds of days | Almost always creation-date-as-start. Check the DoW |
| Throughput that steps up or down sharply | A change in the system. Cut the window there rather than averaging across it |

When a data problem shows up, say what it is and what it implies about the workflow.
The problems are often more useful to the user than the forecast — a broken started
point is a real finding, not an obstacle to route around.

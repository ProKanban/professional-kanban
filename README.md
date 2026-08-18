# Professional Kanban — an AI skill

A drop-in skill that stops AI assistants from inventing Kanban.

Ask a general-purpose AI about cycle time, WIP, or "when will it be done?" and it
answers from whatever it absorbed off the internet — mostly velocity, story points,
burndown charts, and averages. All four are wrong for forecasting, and the answers
look confident anyway.

This skill fixes that. It reasons from the Kanban Guide and the ProKanban.org pocket
guides, and it runs real Monte Carlo simulations and percentile calculations on your
own delivery data instead of doing the arithmetic in prose.

*Compiled by Liz Rettig, Professional Kanban Trainer (PKT), ProKanban.org.*

---

## What it does

- **Routes the question correctly.** One item means cycle time percentiles; many
  items means Monte Carlo on throughput. Getting this fork wrong is the source of
  most bad delivery forecasts.
- **Calculates rather than guesses.** Bundled scripts run 10,000-trial simulations
  and nearest-rank percentiles against your CSV exports.
- **Flags aging work.** Compares in-progress items against the 50th, 70th, and SLE
  thresholds and says which ones need a conversation today.
- **Keeps the language honest.** Every forecast comes out as a range plus a
  probability — "85% chance of 31 items or more" — never a bare date.

## Install

**Claude (web, desktop, or mobile)** — download `professional-kanban.skill`
from the [latest release](../../releases/latest) and use the *Save skill* button.

**Claude Code** — clone this repo into your skills directory:

```bash
git clone https://github.com/ProKanban/professional-kanban-skill.git
cp -r professional-kanban-skill/professional-kanban ~/.claude/skills/
```

That installs the skill at **user scope**: it loads in every project on your
machine, and a user-scope skill takes precedence over a same-named project
skill. If you'd rather scope it to a single project, copy it to
`.claude/skills/professional-kanban/` inside that project instead.

**ChatGPT, Cursor, Copilot, or anything else** — these tools don't load skills, but
`professional-kanban/SKILL.md` still works as a plain context file. Paste it into a
Project's instructions, a Custom GPT's configuration, `.cursorrules`, or
`.github/copilot-instructions.md`.

## Using the scripts

Python 3.8+, standard library only. No pandas, no install step.

```bash
cd professional-kanban/scripts

# Multiple-item forecasts
python3 monte_carlo.py how-many --input done.csv --days 30
python3 monte_carlo.py how-many --input done.csv --by 2026-10-15
python3 monte_carlo.py when     --input done.csv --items 50
python3 monte_carlo.py when     --input done.csv --items 50 --split 1.3   # 30% scope growth

# Single-item forecasting and aging
python3 cycle_time.py sle   --input done.csv
python3 cycle_time.py aging --input done.csv --wip in-progress.csv
```

Try them against the sample data in `professional-kanban/assets/` before pointing
them at your own export.

Useful flags: `--from` / `--to` to choose the historical window, `--unit week`,
`--workdays all`, `--confidence 50,70,85,95`, `--seed` for reproducible output.

## Your data

Column names are detected automatically from common Jira, Azure DevOps, Trello, and
spreadsheet exports. Three shapes work:

| Shape | Columns | Supports |
|---|---|---|
| One row per finished item | `started`, `finished` | Everything |
| One row per period | `week`, `count` | Monte Carlo only |
| One row per item | `cycle_time` | SLE and right-sizing only |

Extra columns are ignored, so an unmodified export usually works as-is. See
`professional-kanban/references/data-prep.md` for export-specific notes, how to
choose a historical window, and what to do when data is thin.

One warning worth repeating: **`Created` is almost never your started point.** An
item can sit in a backlog for months. Measuring from creation will overstate your
cycle times, sometimes by an order of magnitude.

## Sources

Nothing here is invented.

- **The Kanban Guide** (May 2025), Orderly Disruption Limited and Daniel S. Vacanti,
  Inc. — licensed CC BY-SA 4.0. Source of the definition of Kanban, the Definition
  of Workflow, the four flow metrics, and the SLE definition.
- **Kanban Pocket Guide** — ProKanban.org. Work item age, percentiles as
  intervention triggers, right-sizing.
- **Flow Forecasting Pocket Guide** — ProKanban.org. Monte Carlo rules, how much
  data you need, the language of forecasting.

Going deeper: the pocket guides above, and *Actionable Agile Metrics for
Predictability* Volumes I and II.

## License

Two licenses, split by material type — see [LICENSE](LICENSE) for the full terms
and the required attribution notice.

- **Documentation** (`SKILL.md`, `references/`, this README) — CC BY-SA 4.0.
  The Kanban Guide is CC BY-SA 4.0, so derivative work carries ShareAlike: adapt
  and redistribute freely, including commercially, but credit the sources and
  license your adaptation the same way.
- **Scripts** (`scripts/`) — MIT, so they can be embedded in other tools without
  ShareAlike obligations.
- **Sample data** (`assets/`) — synthetic, CC0. Use it in training material freely.

The ProKanban.org name and the PKT certification marks are not covered.

## Contributing

Issues and pull requests welcome — particularly reports of exports that fail to
parse, since column-name coverage only improves by seeing real ones.

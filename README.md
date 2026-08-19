# Professional Kanban

Turn delivery-history CSVs into honest flow signals, SLEs, and probabilistic
forecasts in ChatGPT, Codex, Claude, or Claude Code.

No story points. No average-based promises. No service account, telemetry, or
hosted dependency. The bundled Python tools calculate from your data and the skill
teaches the assistant how to explain the result without turning a forecast into a
commitment.

> **Ask:** “Here are my completed-items and in-progress CSVs. Which work needs
> attention today, and how many items can we finish in the next 30 days?”
>
> **Get:** “ENG-2004, ENG-2003, and ENG-2002 are past the 14-day SLE—swarm,
> split, or unblock these first. Based on raw historical throughput, there is an
> 85% chance of completing **33 items or more** in the next 30 calendar days.”

Compiled by Liz Rettig, Professional Kanban Trainer (PKT), ProKanban.org.

## Install in 30 seconds

Download the three release assets from the
[latest release](https://github.com/ProKanban/professional-kanban-skill/releases/latest):

- `professional-kanban.skill` for ChatGPT
- `professional-kanban.zip` for Claude.ai or the Chat tab in Claude Desktop
- `SHA256SUMS` to verify both downloads before installation

### ChatGPT

Open **Plugins > Skills > Create > Upload from your computer**, upload
`professional-kanban.skill`, and start a new chat. Personal Skills are currently
available on eligible Business, Enterprise, Healthcare, and Edu accounts; workspace
admins can control uploads. A Personal Skill installed on desktop does not
automatically sync to web/mobile, so upload it on each surface where you need it.
See OpenAI's [current Skills guide](https://help.openai.com/en/articles/20001066).

### Claude.ai / Claude Desktop

Enable code execution, open **Customize > Skills**, choose **+ Create skill >
Upload a skill**, and upload `professional-kanban.zip`. The same custom skill is
available in Claude.ai and the Chat tab of Claude Desktop. Team and Enterprise
owners can provision the ZIP organization-wide. See Anthropic's
[current Skills guide](https://support.claude.com/en/articles/12512180-use-skills-in-claude).

### Claude Code

For automatic marketplace updates, run these commands inside Claude Code:

```text
/plugin marketplace add ProKanban/professional-kanban-skill
/plugin install professional-kanban@prokanban
/reload-plugins
```

Or install the standalone skill at user scope with GitHub CLI (preview):

```bash
gh skill install ProKanban/professional-kanban-skill professional-kanban@v1.1.0 \
  --agent claude-code --scope user
```

### Codex

Install the standalone skill at user scope with GitHub CLI (preview):

```bash
gh skill install ProKanban/professional-kanban-skill professional-kanban@v1.1.0 \
  --agent codex --scope user
```

You can also ask `$skill-installer` in Codex to install
`ProKanban/professional-kanban-skill`. Once the plugin is accepted into OpenAI's
public directory, ChatGPT and Codex users can search for **Professional Kanban** in
the Plugins browser; the release upload and direct skill install do not depend on
that listing.

`gh skill` is a GitHub CLI preview and may change. It needs a current authenticated
GitHub CLI. The ZIP/`.skill` upload and Claude marketplace routes are independent.

## Platform support

| Host | Best installation | Automatic activation | Runs bundled calculations |
|---|---|---:|---:|
| ChatGPT web/desktop | Upload `.skill` | Yes | Yes, with Skills/code execution enabled |
| Claude.ai / Claude Desktop Chat | Upload `.zip` | Yes | Yes, with code execution enabled |
| Claude Code / Desktop Code | Claude plugin marketplace | Yes, or `/professional-kanban:professional-kanban` | Yes, with local Python |
| Codex CLI / desktop / IDE | `gh skill install` or `$skill-installer` | Yes, or `$professional-kanban` | Yes, with local Python |
| Agent Skills-compatible hosts | Install `skills/professional-kanban/` | Host-dependent | Yes, if Python execution is available |

The skill follows the open [Agent Skills specification](https://agentskills.io/)
and has separate OpenAI and Claude plugin manifests. There is one canonical skill
directory—platform packages do not fork the instructions or calculations.

## What it does

- Routes one-item questions to cycle-time percentiles and many-item questions to
  Monte Carlo on throughput.
- Flags aging WIP before it becomes late completed work.
- Preserves zero-throughput periods and samples the raw history instead of fitting
  a convenient distribution.
- Expresses every result as a range plus a probability: “85% chance of 33 items or
  more,” never a naked date or single-number promise.
- Detects common Jira, Azure DevOps, Trello, GitHub, and spreadsheet column names.
- Rejects ambiguous dates, invalid confidence levels, incomplete simulations, and
  inputs that cannot support the requested analysis.

## Use it

Attach completed-item data and ask naturally:

- “Which in-progress items need attention today?”
- “What is our 85th-percentile SLE?”
- “How many items can we finish in the next 30 days?”
- “When are these 50 remaining items likely to finish?”
- “Our backlog usually grows 25% during delivery. Include that in the forecast.”

The assistant selects and runs the bundled calculation. For direct CLI use,
**Python 3.11–3.14** is supported and no third-party package is required:

```bash
SKILL_DIR="skills/professional-kanban"

python3 "$SKILL_DIR/scripts/monte_carlo.py" how-many \
  --input done.csv --days 30 --start 2026-08-19 --seed 42
python3 "$SKILL_DIR/scripts/monte_carlo.py" how-many \
  --input weekly.csv --weeks 6
python3 "$SKILL_DIR/scripts/monte_carlo.py" when \
  --input done.csv --items 50 --split 1.25 --seed 42

python3 "$SKILL_DIR/scripts/cycle_time.py" sle --input done.csv
python3 "$SKILL_DIR/scripts/cycle_time.py" aging \
  --input done.csv --wip in-progress.csv --as-of 2026-08-19
```

Use `--help` on either script for the complete, command-specific flag list. The
example files are in `skills/professional-kanban/assets/`.

## Your data

The scripts read CSV or TSV with a header row. Extra columns are ignored.

| Shape | Required columns | Supports |
|---|---|---|
| One row per finished item | a completion date; start date optional | Throughput forecasts; cycle time when start exists |
| One row per period | period/date plus count | Throughput forecasts |
| One row per item | positive finite cycle time | SLE and right-sizing |
| One row per WIP item | start date; item/state optional | Aging analysis |

ISO dates such as `2026-08-19` are the safest choice. Ambiguous numeric dates such
as `04/05/2026` are rejected until you choose `--date-order mdy` or
`--date-order dmy`. CLI dates (`--from`, `--to`, `--start`, `--by`, `--as-of`) are
strict `YYYY-MM-DD`.

One warning worth repeating: **`Created` is almost never your started point.** An
item can sit in a backlog for months. Measuring from creation can radically
overstate cycle time. The selected start and finish points must match the team's
Definition of Workflow.

See [data preparation](skills/professional-kanban/references/data-prep.md) for the
accepted aliases, export notes, historical-window guidance, and thin-data options.

## Privacy and security

The repository contains no MCP server, hosted service, analytics, telemetry,
credential handling, or runtime package installer. **No network** request is made
by the bundled scripts. They read only the CSV paths you provide and print results
to standard output; they do not mutate the input files.

Your host still controls where attachments and model conversations are processed.
Review ChatGPT or Claude workspace data controls before using sensitive delivery
data. As with any externally downloaded skill, inspect the release and verify its
checksum before installing it:

```bash
shasum -a 256 -c SHA256SUMS
```

## Update or uninstall

For Claude Code marketplace installs:

```text
/plugin marketplace update prokanban
/plugin uninstall professional-kanban@prokanban
```

For standalone `gh skill` installs, run `gh skill update professional-kanban`.
Pinned installs intentionally stay on their pinned version; reinstall with a newer
tag to upgrade. To remove a standalone skill, delete its `professional-kanban/`
directory from the host's user or project skills folder. ChatGPT and Claude upload
installs can be disabled, replaced, or deleted from their Skills settings.

## Troubleshooting

**The skill does not activate.** Start a new chat/session after installing. Mention
it explicitly with `@Professional Kanban`, `$professional-kanban`, or
`/professional-kanban:professional-kanban`, depending on the host. Check that code
execution/Skills are enabled by the workspace admin.

**The CSV reports an ambiguous date.** Prefer ISO dates, or rerun with
`--date-order mdy` / `--date-order dmy` after confirming the source convention.

**A column is not detected.** Compare its header with the aliases in
[data preparation](skills/professional-kanban/references/data-prep.md). Open a
parser issue with a redacted header row and five representative rows.

**A weekly forecast rejects `--days` or `--by`.** Weekly counts only justify whole
weekly periods. Use `--weeks N`; do not prorate a weekly observation into assumed
daily values.

**The forecast says the evidence is thin or cannot complete all trials.** This is a
data/scope finding, not an internal error. Use a representative recent history,
confirm that some periods have positive throughput, and reduce or split the scope
before rerunning.

**Claude says `/plugin` is unknown.** Upgrade Claude Code, restart it, and retry.
You can always use the direct ZIP or standalone skill route instead.

## Contributing

Parser samples, adversarial edge cases, and documentation corrections are welcome.
Read [CONTRIBUTING.md](CONTRIBUTING.md) before opening a pull request. Security
reports belong in [SECURITY.md](SECURITY.md), not a public issue.

## Sources and license

The instructional material is grounded in the May 2025 *Kanban Guide* and the
ProKanban.org pocket guides. Exact authors, URLs, known licenses, and the boundary
between quoted/derived and original material are recorded in
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

- Scripts, tests, and packaging automation: MIT
- Skill instructions, references, and repository documentation: CC BY-SA 4.0
- Synthetic sample data: CC0-1.0

See [LICENSE](LICENSE), the complete texts in `LICENSES/`, and machine-readable
path mappings in `REUSE.toml`. These licenses grant copyright permissions only;
they do not grant rights in the ProKanban.org name, logo, or PKT certification
marks.

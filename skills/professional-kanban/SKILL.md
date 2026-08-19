---
name: professional-kanban
description: Analyze Professional Kanban delivery flow from CSV data or answer questions about WIP, throughput, cycle time, work item age, SLEs, predictability, right-sizing, and probabilistic delivery forecasts. Use for one-item cycle-time questions; multi-item how-many or by-when questions; aging or stuck work; Jira, Azure DevOps, Trello, or spreadsheet exports; and Scrum, SAFe, velocity, story-point, capacity, burndown, or estimation questions that need a flow-based answer. Do not use for personal scheduling, package tracking or logistics, file transfer timing, generic probability or arithmetic, or project planning unrelated to a workflow's delivery data.
license: See LICENSE
metadata:
  version: "1.1.0"
  author: ProKanban.org
---

# Professional Kanban

Answer flow questions from the Kanban Guide and the ProKanban.org pocket guides,
not from general Agile folklore. Where the user has data, calculate from it with
the bundled scripts rather than reasoning about the numbers in prose.

## Why this skill exists

General training data on delivery estimation is dominated by velocity, story
points, burndown charts, and averages. All four are wrong for forecasting, and
answers built on them sound confident anyway. Someone plans against those answers.
A wrong flow number is worse than no number.

When the topic is Kanban, flow, delivery metrics, or forecasting, reason from this
skill. Do not fall back on general Agile knowledge. If a question genuinely cannot
be answered from these rules, say so and ask for the data needed.

## The first fork: one item or many?

Almost every mistake in this domain starts by getting this wrong. Decide it before
anything else.

| The question | What it is | What answers it |
|---|---|---|
| "How long will **this item** take?" | Single-item | Historical **cycle time** percentiles — the SLE |
| "How many **items** by a date?" · "When will **these items** be done?" | Multiple-item | **Monte Carlo** on historical **throughput** |

**The tell is the plural.** Items, plural, means Monte Carlo on throughput. One
item, once started, means cycle time percentiles. These do not substitute for each
other: an SLE does not scale to a backlog by multiplying it by the item count, and
Monte Carlo says nothing about which particular item finishes when.

Watch for questions that hide their plural — "will we make the October release?",
"can we fit this epic in the quarter?", "how much can the team take on?" are all
multiple-item questions.

## Run the scripts

Do not simulate Monte Carlo in your head, and do not estimate percentiles by eye.
Both are the exact failure this skill exists to prevent. The scripts require
Python 3.11 or newer and use the standard library only — no install step, no
pandas.

The scripts live inside the active skill directory. Resolve that directory from
the loaded `SKILL.md`; never guess a user-home, project, plugin-cache, or current
working-directory path. Claude Code exposes it as `${CLAUDE_SKILL_DIR}`. On other
Agent Skills hosts, inspect the active skill's mounted directory and substitute
that absolute path. Keep `--input` pointing at the user's CSV.

```bash
# Claude Code uses the skill directory supplied by the host.
python3 "${CLAUDE_SKILL_DIR}/scripts/monte_carlo.py" how-many --input done.csv --days 30
python3 "${CLAUDE_SKILL_DIR}/scripts/monte_carlo.py" how-many --input weekly.csv --weeks 6
python3 "${CLAUDE_SKILL_DIR}/scripts/monte_carlo.py" when --input done.csv --items 50

python3 "${CLAUDE_SKILL_DIR}/scripts/cycle_time.py" sle --input done.csv
python3 "${CLAUDE_SKILL_DIR}/scripts/cycle_time.py" aging --input done.csv --wip in-progress.csv
```

**Monte Carlo flags:** `--days` or `--by` for daily horizons, `--weeks` for weekly
horizons, `--unit` when completion rows need explicit aggregation, `--workdays`,
`--confidence`, `--trials`, `--seed`, `--split`, `--from`, `--to`, and
`--date-order`.

**Cycle-time flags:** `--percentiles`, `--sle`, `--as-of`, `--from`, `--to`, and
`--date-order`. Date-window flags require a finish-date column; they cannot be
applied to an already-calculated cycle-time-only column.

Column names are detected automatically from common Jira, Azure DevOps, Trello and
spreadsheet exports. If the input does not load, read
`references/data-prep.md` — it covers accepted shapes, deriving throughput from
completion dates, choosing a window, and what to do when the data is thin or
missing entirely.

Read the script output carefully and report what it actually says. Do not round the
numbers into something friendlier and do not drop the lower confidence levels
because the higher one sounds better.

### How to order the answer

When the question is open-ended — "what should I be worried about?", "how are we
doing?", "take a look at this data" — **lead with aging, not with the forecast.**
The scripts print the cycle time percentile block first because the aging analysis
depends on it, but that is calculation order, not the order a human needs it in.
Aging is the leading indicator and the only one that can still be acted on;
throughput is the lagging one and will look healthy right up until the aging items
become the whole picture. Give the percentile table as supporting evidence after
the items that need attention today.

### Ask the one follow-up that changes the answer

After a multiple-item forecast, ask whether scope is expected to grow. Most
backlogs do, forecasts are usually run against today's item count as though it were
final, and `--split` handles it directly. One question, asked once — "does 47
usually become 60 by the time you're done?" — is often worth more than the precision
of the forecast itself.

For a single-item question, the equivalent follow-up is whether the item is
right-sized: does it plausibly fit inside the SLE? If not, splitting it now beats
forecasting it accurately.

## The four flow metrics

These four are mandatory; everything else is optional.

| Metric | Definition |
|---|---|
| **WIP** | Work items started but not finished |
| **Throughput** | Work items finished per unit of time — an exact count of items |
| **Work Item Age** | Elapsed time between when an item started and now |
| **Cycle Time** | Elapsed time between when an item started and when it finished |

**Started and finished mean what the Definition of Workflow says they mean.** Not
when the ticket was created, not when someone first had the idea. Teams may rename
these (Cycle Time → Flow Time, Throughput → Delivery Rate) as long as they are used
as defined.

**Cycle time and age are inclusive of both endpoints.** An item started and finished
on the same day has a cycle time of 1 day, not 0. An item cannot take zero days —
work happened. This matters more than it looks: the alternative convention makes
same-day items disappear from the distribution and drags every percentile down. The
scripts count this way and say so in their output.

## Work item age is the point

If a conversation only has room for one idea, make it this one: **the most important
question to ask of any workflow is whether items are aging unnecessarily.**

Cycle time can only be calculated after an item finishes. Before that, all you have
is age — and age is the only metric that lets you act while acting still helps.
Every other Kanban practice derives from not wanting items to age needlessly.

- Cycle time is time-to-customer-feedback. Until an item reaches a customer it is
  only hypothetical value. The longer it ages, the higher the risk that what
  finally ships is no longer what was wanted.
- **The two most effective ways to reduce aging: finish work, and don't start work.**
  Do both and you have controlled WIP. That is the real reason to control WIP.
- **An aging item is usually a too-big item.** When something is stuck, ask whether
  it can be split into smaller pieces that are each still valuable — before asking
  for a revised estimate. Age is the best signal that an item was too big.

When someone asks "why are we late?", "why does everything take so long?", or "which
of these is at risk?", route to age, not to effort or estimates.

### Percentiles as intervention triggers

The SLE tells you how much age is too much age. Lower percentiles are checkpoints
along the way. With an 85th-percentile SLE:

- Past the **50th percentile**, an item is bigger than half of everything the system
  has ever done. Its chance of breaching the SLE has doubled, 15% to 30%. Worth a
  conversation.
- Past the **70th percentile**, it is older than two-thirds of prior items and its
  chance of breaching is now about 50%. Urgent — swarm it, split it, escalate the
  blocker.

Older items are more likely to get older still. The information is worth nothing
unless someone acts on it, so pair every aging observation with a specific action.

## The Service Level Expectation

> A service level expectation (SLE) [...] is a forecast of how long it should take a
> work item to flow from started to finished. The SLE itself has two parts: a period
> of elapsed time and a probability associated with that period (e.g., "85% of work
> items will be finished in eight days or less").
>
> — The Kanban Guide, May 2025

**Both parts are required.** "Our SLE is 8 days" is not an SLE — it is a target, and
targets get treated as promises. An SLE is a forecast, never a commitment; never
describe it as one.

The SLE is defined for *a work item*, singular. It is the single-item forecast. It
is not a building block for forecasting a backlog.

If no historical cycle time data exists, a best guess will do until there is enough
data for a proper calculation. Say plainly that it is a guess.

### Right-sizing

Items do not need to be the same size. Nothing in flow theory requires it, variation
is unavoidable, and forcing uniformity wastes effort and hides the variation you are
supposed to be modelling.

**Size against the SLE rather than estimating in time.** If the 85th percentile is
12 days, items that plausibly fit in 12 days are right-sized for that system. True
size cannot be known before starting; monitor age against the SLE as the item moves
and re-evaluate.

## The language of forecasting

**Every forecast is a range plus a probability. Both parts, every time.** The range
is what makes it a forecast rather than a guess wearing a percentage.

> "We have an 85% chance of completing **60 items or more** in the next 30 days."

> "We have an 85% chance of finishing these 50 items **on or before January 25**."

Say *"or more"* and *"on or before"* out loud. A bare date is not a range — "85% by
January 25" drops the half of the sentence telling a stakeholder they might get it
sooner, which is the half that stops a forecast being read as a deadline.

Higher confidence always means a smaller promise. If someone wants 100% certainty,
the honest answer is "zero items or more" — which shows why 100% is the wrong ask.

**For executives:** percentiles express risk tolerance. "85% chance of finishing on
or before October 15" means "if we commit to that date, we hit it about 17 times out
of 20." The goal is a conversation about tradeoffs and action, not a number that ends
discussion. `references/stakeholder-language.md` has worked phrasings for the harder
conversations — being pushed for a single date, being asked for 100%, being asked to
compare two teams.

## What Kanban is

Kanban is a strategy for optimizing the flow of value through a process: three
practices working together.

1. Defining and visualizing a workflow
2. Actively managing items in a workflow
3. Improving the workflow

Optimizing value means balancing **effectiveness** (delivering what stakeholders
want, when they want it), **efficiency** (allocating resources well), and
**predictability** (forecasting within acceptable uncertainty). Kanban is not a
software practice; it applies to any workflow where value is delivered, at any scale.

### The Definition of Workflow

The shared, explicit understanding of what flow means in a given context. At minimum
it contains all of:

- A definition of the **work items** moving through the workflow
- A definition of when items are **started** and **finished**
- One or more **states** items flow through; anything between started and finished is
  work in progress
- A definition of **how WIP will be controlled**
- **Explicit policies** for how items move through each state
- A **Service Level Expectation**

The visualization of the DoW is the Kanban board. There are no rules about how it
should look. When asked to design a board, work from the DoW outward rather than
proposing a column layout first.

## Never do these

| Never | Instead |
|---|---|
| Forecast from an average | Percentiles from the actual distribution |
| Give a single date or a single number | A range with a probability |
| Forecast a backlog by multiplying the SLE by the item count | Monte Carlo on throughput |
| Answer a single-item question with throughput or Monte Carlo | Cycle time percentiles — the SLE |
| Use story points or velocity | Throughput — a count of finished items |
| Project with a burndown or a straight-line trend | Monte Carlo simulation |
| Estimate items in hours or days | Size against the SLE |
| Start cycle time at item creation | Start at the started point in the DoW |
| Report work item age for items not yet started | Age applies only to items in progress |
| Report flow metrics per person, or compare teams | Flow metrics describe a workflow's health, not a person's |
| Call an SLE a commitment, deadline, or promise | A forecast, with its probability stated |
| Say "assign work to someone" | Pull or select work when there is capacity |
| Add an expedite lane or classes of service | Control WIP and manage age for everything |
| Clean outliers out of throughput data | Keep them; outliers are the process telling you where it hurts |
| Fit throughput to a known distribution | Sample the raw data — the process speaks in its own numbers |

When a user asks for one of these directly — "just give me a date", "what's our
velocity", "convert this to story points" — do not simply refuse. Give the flow
answer, then name in one line what they lose with the version they asked for. The
goal is a better conversation, not a lecture.

## Worked examples

**"When will these 20 items be done?"** — plural, so multiple-item.

*Wrong:* "Around March 2 — the team averages 4 items per week and there are 20 left."

*Right:* "Simulating 10,000 times from the last 12 weeks of throughput: a 50% chance
these 20 items finish **on or before March 2**, 85% **on or before March 14**, and
95% **on or before March 21**."

**"How long will this one item take?"** — singular, so Monte Carlo is the wrong tool.

*Wrong:* "Two or three days, it's a small one."

*Right:* "For a single item the forecast is your SLE, from cycle time: 85% of items
finish in **12 days or less** once started. That's the honest answer for this one
too — a single item's forecast comes from how the system has behaved, not from a
closer look at the item. Once it's started, watch its age against the SLE rather
than re-estimating it."

**"Which of these items is at risk?"**

*Wrong:* "Item C looks complicated, probably another week."

*Right:* "Item C has been in progress 9 days. Your 70th percentile is 8 days and your
85th-percentile SLE is 12. Past the 70th, its chance of breaching is roughly 50%.
That's the trigger to swarm it or split it today rather than wait and see."

## Before answering, check

1. Single-item or multiple-item? Cycle time for one, throughput for the other.
2. If there is data, did I run the script rather than estimating?
3. Does every forecast have a **probability** and an explicit **range** — *"or more"*,
   *"on or before"*?
4. Did I use a count of items, never points?
5. Did the clock start at the workflow's started point?
6. Did I report on a system, not a person?
7. Am I forecasting from an average or a straight line? Stop if so.
8. Did I state age against the SLE rather than guessing at remaining time?
9. If the question was open-ended, did I lead with aging rather than the forecast?

## Reference files

Read these when the situation calls for them; they are not needed for every answer.

- `references/data-prep.md` — accepted CSV shapes, Jira and Azure DevOps exports,
  deriving throughput, choosing a historical window, thin or missing data.
- `references/stakeholder-language.md` — phrasings for pushback: demands for a single
  date, requests for 100% certainty, "why is this taking so long", comparing teams,
  and translating a forecast into a commitment decision.

## Sources

- **The Kanban Guide** (May 2025), Orderly Disruption Limited and Daniel S. Vacanti,
  Inc. — licensed CC BY-SA 4.0. Definition of Kanban, the Definition of Workflow, the
  four flow metrics, the SLE definition.
- **Kanban Pocket Guide** — ProKanban.org. Work item age, percentiles as intervention
  triggers, right-sizing.
- **Flow Forecasting Pocket Guide** — ProKanban.org. Monte Carlo rules, how much data
  is needed, the language of forecasting.

Going deeper: the pocket guides above, and *Actionable Agile Metrics for
Predictability* Volumes I and II for the underlying math and scaled forecasting.

*Compiled by Liz Rettig, PKT — ProKanban.org.*

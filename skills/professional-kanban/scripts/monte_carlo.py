#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 ProKanban.org
# SPDX-License-Identifier: MIT

"""Monte Carlo forecasting from historical throughput.

Answers multiple-item questions only:
  how-many  "How many items will we finish by <date>?"
  when      "When will these <N> items be done?"

Both sample the team's raw historical throughput with replacement, run many
trials, and report the distribution. Never reports a single run.

Usage
-----
  python3 monte_carlo.py how-many --input done.csv --days 30
  python3 monte_carlo.py how-many --input done.csv --by 2026-10-15
  python3 monte_carlo.py when --input done.csv --items 50
  python3 monte_carlo.py when --input done.csv --items 50 --start 2026-09-01

Input
-----
Either shape works:
  (a) one row per completed item, with a completion-date column
      (finished / completed / done / closed / resolved ...)
  (b) one row per period, with a date/week column and a count column
      (count / throughput / items ...)

Options
-------
  --unit day|week      sampling unit (inferred where the input declares it)
  --workdays all       which days the system runs (default: all; e.g. "mon-fri";
                       non-working-day finishes count on the next working day)
  --trials 10000       number of simulated runs
  --from / --to        limit the historical window (YYYY-MM-DD)
  --split N            when only: scope-growth multiplier
  --confidence 50,70,85,95   percentiles to report
"""

import argparse
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_CEILING
import math
import random
import sys
from datetime import timedelta

import flowlib as fl


@dataclass(frozen=True)
class ThroughputHistory:
    series: list[int]
    first: object
    last: object
    item_count: int
    source: str
    unit: str


@dataclass(frozen=True)
class SimulationRun:
    periods: int
    completed: bool


def positive_integer(option):
    """Build an argparse validator for a positive integer option."""
    def parse(value):
        try:
            number = int(value)
        except (TypeError, ValueError) as exc:
            raise argparse.ArgumentTypeError("%s must be a positive integer" % option) from exc
        if number <= 0:
            raise argparse.ArgumentTypeError("%s must be a positive integer" % option)
        return number
    return parse


def positive_finite(option):
    """Build an argparse validator for a finite number greater than zero."""
    def parse(value):
        try:
            number = Decimal(value)
        except (InvalidOperation, TypeError, ValueError) as exc:
            raise argparse.ArgumentTypeError(
                "%s must be a finite number greater than zero" % option
            ) from exc
        if not number.is_finite() or number <= 0:
            raise argparse.ArgumentTypeError(
                "%s must be a finite number greater than zero" % option
            )
        return number
    return parse


def parse_confidences(value):
    """Parse a comma-separated list of open-interval confidence levels."""
    try:
        values = [float(part.strip()) for part in value.split(",") if part.strip()]
    except ValueError as exc:
        raise ValueError(
            "--confidence values must be finite numbers between 0 and 100"
        ) from exc
    if not values or any(not math.isfinite(item) or not 0 < item < 100 for item in values):
        raise ValueError("--confidence values must be finite numbers between 0 and 100")
    return sorted(set(values))


def _period_unit(column_name):
    normalized = fl.normalise(column_name)
    if "week" in normalized:
        return "week"
    if "month" in normalized:
        raise ValueError("Monthly period/count data is not supported; provide daily or weekly data.")
    return "day"


def _load_period_counts(rows, period_col, count_col, date_order, window_from, window_to,
                        requested_unit, workdays):
    inferred_unit = _period_unit(period_col)
    if requested_unit and requested_unit != inferred_unit:
        unit_label = "weekly" if inferred_unit == "week" else "daily"
        raise ValueError(
            "The '%s' header is a %s period column; remove --unit or use --unit %s."
            % (period_col, unit_label, inferred_unit)
        )

    counts = {}
    for row_number, row in enumerate(rows, 2):
        try:
            period = fl.parse_date(row.get(period_col), date_order=date_order)
        except ValueError as exc:
            raise ValueError("Row %d: %s" % (row_number, exc)) from exc
        raw = (row.get(count_col) or "").strip()
        if period is None or not raw:
            raise ValueError("Row %d needs a valid period and count." % row_number)
        try:
            number = float(raw)
        except ValueError as exc:
            raise ValueError("Row %d count must be a non-negative integer." % row_number) from exc
        if not math.isfinite(number) or number < 0 or not number.is_integer():
            raise ValueError("Row %d count must be a non-negative integer." % row_number)
        if period in counts:
            raise ValueError("Duplicate period %s in rows of '%s'." % (period, period_col))
        counts[period] = int(number)

    filtered = {
        period: count
        for period, count in counts.items()
        if (window_from is None or period >= window_from)
        and (window_to is None or period <= window_to)
    }
    if not filtered:
        raise ValueError("No throughput periods inside the chosen window.")

    if inferred_unit == "week":
        weekdays = {period.weekday() for period in counts}
        if len(weekdays) != 1:
            raise ValueError(
                "Weekly period labels must use the same weekday; found an irregular cadence."
            )
        anchor_weekday = next(iter(weekdays))
        first = min(filtered)
        if window_from is not None:
            first = window_from + timedelta(
                days=(anchor_weekday - window_from.weekday()) % 7
            )
        last = max(filtered)
        if window_to is not None:
            last = window_to - timedelta(
                days=(window_to.weekday() - anchor_weekday) % 7
            )
    else:
        non_working = [
            period
            for period, count in filtered.items()
            if count > 0 and not fl.is_workday(period, workdays)
        ]
        if non_working:
            raise ValueError(
                "Positive throughput appears on non-working date %s; include that day in "
                "--workdays or correct the period data." % min(non_working).isoformat()
            )
        first = window_from or min(filtered)
        last = window_to or max(filtered)
    if first > last:
        raise ValueError("Historical window contains no complete periods on the observed cadence.")

    series = []
    period = first
    step = timedelta(days=7 if inferred_unit == "week" else 1)
    while period <= last:
        if inferred_unit == "week" or fl.is_workday(period, workdays):
            series.append(filtered.get(period, 0))
        if period == last:
            break
        period += step
    if not series:
        raise ValueError("Historical window contains no working periods.")

    return ThroughputHistory(
        series=series,
        first=first,
        last=last,
        item_count=sum(series),
        source="period + count columns (%s, %s)" % (period_col, count_col),
        unit=inferred_unit,
    )


def load_throughput(path, unit, workdays, window_from, window_to, date_order=None):
    rows, headers = fl.read_rows(path)
    if not rows:
        raise SystemExit("No data rows in %s" % path)

    count_col = fl.find_column(headers, fl.COUNT_NAMES)
    finish_col = fl.find_column(headers, fl.FINISHED_NAMES)
    period_col = fl.find_column(headers, fl.PERIOD_NAMES)

    # Shape (b): a period column plus an explicit count column.
    if count_col and period_col and count_col != period_col:
        return _load_period_counts(
            rows,
            period_col,
            count_col,
            date_order,
            window_from,
            window_to,
            unit,
            workdays,
        )
    # Shape (a): one row per finished item.
    elif finish_col:
        dates = []
        for row_number, row in enumerate(rows, 2):
            try:
                completed = fl.parse_date(row.get(finish_col), date_order=date_order)
            except ValueError as exc:
                raise ValueError("Row %d: %s" % (row_number, exc)) from exc
            if completed is not None:
                dates.append(completed)
        source = "completion dates in column '%s'" % finish_col
    else:
        raise SystemExit(
            "Could not find a completion-date column or a period+count pair.\n"
            "Headers seen: %s" % ", ".join(headers.values())
        )

    if window_from:
        dates = [d for d in dates if d >= window_from]
    if window_to:
        dates = [d for d in dates if d <= window_to]
    if not dates:
        raise SystemExit("No completed items inside the chosen window.")

    resolved_unit = unit or "day"
    if resolved_unit == "week":
        series, first, last = fl.weekly_throughput(dates, window_from, window_to)
    else:
        series, first, last = fl.daily_throughput(dates, workdays, window_from, window_to)

    if not series:
        raise SystemExit("Historical window contains no working periods.")
    return ThroughputHistory(series, first, last, len(dates), source, resolved_unit)


def warn_about_data(series, unit, out):
    n = len(series)
    if n < 10:
        out.append(
            "  ! Only %d %ss of history. That is below the ~10 points needed to start; "
            "treat this as directional and re-forecast as data arrives." % (n, unit)
        )
    elif n < 20:
        out.append(
            "  ~ %d %ss of history. Enough to forecast, short of the ~20 that makes it "
            "comfortable. Re-forecast as more data arrives." % (n, unit)
        )
    if sum(series) == 0:
        raise SystemExit("Every period in the window shows zero throughput; nothing to sample.")


def sim_how_many(series, periods, trials, rng):
    return [sum(rng.choice(series) for _ in range(periods)) for _ in range(trials)]


def sim_when(series, items, trials, rng, cap):
    results = []
    for _ in range(trials):
        remaining, periods = items, 0
        while remaining > 0 and periods < cap:
            remaining -= rng.choice(series)
            periods += 1
        results.append(SimulationRun(periods=periods, completed=remaining <= 0))
    return results


def unsupported_confidences(runs, confidences):
    """Return requested nearest-rank percentiles that depend on censored trials."""
    completed = sum(run.completed for run in runs)
    total = len(runs)
    return [
        confidence
        for confidence in confidences
        if math.ceil(confidence / 100.0 * total) > completed
    ]


def article(n):
    """'an 85% chance' but 'a 50% chance' — small thing, but the skill's output
    gets read aloud in stand-ups."""
    text = ("%g" % n)
    return "an" if text[0] == "8" or text[:2] in ("11", "18") else "a"


def periods_to_date(start, periods, unit, workdays):
    """Walk `periods` sampling units forward from `start` and return the date."""
    if unit == "week":
        return start + timedelta(days=7 * periods - 1)
    day = fl.next_workday(start, workdays)
    counted = 0
    while True:
        if fl.is_workday(day, workdays):
            counted += 1
            if counted >= periods:
                return day
        day += timedelta(days=1)


def working_periods_between(start, end, unit, workdays):
    if unit == "week":
        return max(0, ((end - start).days // 7) + 1)
    count, day = 0, start
    while day <= end:
        if fl.is_workday(day, workdays):
            count += 1
        if day == end:
            break
        day += timedelta(days=1)
    return count


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("mode", choices=["how-many", "when"])
    p.add_argument("--input", "-i", required=True, help="CSV of historical completions")
    p.add_argument("--days", type=positive_integer("--days"),
                   help="how-many: forecast horizon in calendar days")
    p.add_argument("--weeks", type=positive_integer("--weeks"),
                   help="how-many: forecast horizon in whole weeks")
    p.add_argument("--by", help="how-many: forecast horizon as a date (YYYY-MM-DD)")
    p.add_argument("--items", type=positive_integer("--items"),
                   help="when: number of items remaining")
    p.add_argument("--split", type=positive_finite("--split"), default=None,
                   help="when: multiply remaining items (e.g. 1.3 for 30%% expected scope growth)")
    p.add_argument("--start", help="forecast start date (default: today)")
    p.add_argument("--unit", choices=["day", "week"], default=None,
                   help="sampling unit (normally inferred from the input)")
    p.add_argument("--workdays", default="all",
                   help="days the system runs (default: all; e.g. mon-fri)")
    p.add_argument("--trials", type=positive_integer("--trials"), default=10000)
    p.add_argument("--from", dest="window_from", help="earliest history to use (YYYY-MM-DD)")
    p.add_argument("--to", dest="window_to", help="latest history to use (YYYY-MM-DD)")
    p.add_argument("--confidence", default="50,70,85,95")
    p.add_argument("--seed", type=int, default=None, help="fix the RNG for reproducible output")
    p.add_argument("--date-order", choices=["mdy", "dmy"],
                   help="interpret ambiguous numeric CSV dates as month/day or day/month")
    args = p.parse_args()

    if args.mode == "how-many":
        if args.items is not None or args.split is not None:
            p.error("--items and --split are only valid with when")
        horizons = sum(value is not None for value in (args.days, args.weeks, args.by))
        if horizons != 1:
            p.error("choose exactly one of --days, --weeks, or --by for how-many")
    else:
        if any(value is not None for value in (args.days, args.weeks, args.by)):
            p.error("--days, --weeks, and --by are only valid with how-many")
        if args.items is None:
            p.error("when needs --items")

    try:
        workdays = fl.parse_workdays(args.workdays)
    except (OSError, ValueError) as exc:
        p.error(str(exc))
    try:
        window_from = fl.parse_date(args.window_from, strict_iso=True) if args.window_from else None
    except ValueError:
        p.error("--from must use YYYY-MM-DD; got %r" % args.window_from)
    try:
        window_to = fl.parse_date(args.window_to, strict_iso=True) if args.window_to else None
    except ValueError:
        p.error("--to must use YYYY-MM-DD; got %r" % args.window_to)
    if window_from and window_to and window_from > window_to:
        p.error("--from must be on or before --to")
    try:
        confidences = parse_confidences(args.confidence)
    except ValueError as exc:
        p.error(str(exc))
    rng = random.Random(args.seed)

    try:
        history = load_throughput(
            args.input, args.unit, workdays, window_from, window_to, args.date_order
        )
    except (OSError, ValueError) as exc:
        p.error(str(exc))

    series = history.series
    first = history.first
    last = history.last
    total = history.item_count
    source = history.source
    unit = history.unit

    out = []
    out.append("Historical data")
    out.append("  Source:  %s" % source)
    out.append("  Window:  %s to %s" % (first.isoformat(), last.isoformat()))
    out.append("  Items completed: %d over %d %ss (%d %ss with zero)"
               % (total, len(series), unit, sum(1 for v in series if v == 0), unit))
    if sum(series) != total:
        out.append("  ! Only %d of those %d items are in the sample; %d fall outside "
                   "the sampled %ss." % (sum(series), total, total - sum(series), unit))
    out.append("  Throughput per %s: min %d, median %g, max %d"
               % (unit, min(series), fl.percentile(series, 50), max(series)))
    warn_about_data(series, unit, out)
    out.append("")

    if args.mode == "how-many":
        try:
            start = fl.parse_date(args.start, strict_iso=True) if args.start else fl.today()
        except ValueError:
            p.error("--start must use YYYY-MM-DD; got %r" % args.start)
        if args.by:
            try:
                end = fl.parse_date(args.by, strict_iso=True)
            except ValueError:
                p.error("--by must use YYYY-MM-DD; got %r" % args.by)
            if end < start:
                p.error("--by must be on or after the forecast start")
            calendar_days = (end - start).days + 1
            if unit == "week":
                if calendar_days % 7:
                    p.error("Weekly history needs a whole-week horizon; use --weeks.")
                periods = calendar_days // 7
            else:
                periods = working_periods_between(start, end, unit, workdays)
            horizon = "on or before %s (%d working %ss)" % (end.isoformat(), periods, unit)
        elif args.weeks is not None:
            if unit != "week":
                p.error("--weeks requires weekly history or --unit week; use --days for daily history.")
            periods = args.weeks
            try:
                end = start + timedelta(days=7 * args.weeks - 1)
            except OverflowError:
                p.error("forecast date exceeds Python's supported range")
            horizon = "in the next %d week%s (%d working weeks)" % (
                args.weeks, "" if args.weeks == 1 else "s", periods
            )
        elif args.days is not None:
            if unit == "week":
                p.error("Weekly history cannot support a partial-week --days horizon; use --weeks.")
            try:
                end = start + timedelta(days=args.days - 1)
            except OverflowError:
                p.error("forecast date exceeds Python's supported range")
            periods = working_periods_between(start, end, unit, workdays)
            horizon = "in the next %d day%s" % (args.days, "" if args.days == 1 else "s")
            if len(workdays) < 7:
                horizon += " (%d working days)" % periods
        else:
            raise SystemExit("how-many needs --days, --weeks, or --by")

        results = sim_how_many(series, periods, args.trials, rng)
        out.append("Forecast: how many items %s" % horizon)
        out.append("  %d trials sampled from raw historical throughput" % args.trials)
        out.append("")
        for c in sorted(confidences, reverse=True):
            n = fl.lower_bound(results, c)
            out.append("  %2g%% chance of completing %d items or more" % (c, n))
        out.append("")
        headline = 85.0 if 85.0 in confidences else max(confidences)
        out.append("  Say it out loud as: \"We have %s %g%% chance of completing %d items "
                   "or more %s.\"" % (article(headline), headline,
                                      fl.lower_bound(results, headline), horizon))
        out.append("  Higher confidence is always a smaller or equal number.")

    else:
        items = args.items
        split = args.split if args.split is not None else Decimal("1")
        if split > Decimal(sys.maxsize) / Decimal(items):
            p.error("--items multiplied by --split is too large")
        effective_decimal = Decimal(items) * split
        if not effective_decimal.is_finite() or effective_decimal > Decimal(sys.maxsize):
            p.error("--items multiplied by --split is too large")
        effective = int(effective_decimal.to_integral_value(rounding=ROUND_CEILING))
        try:
            start = fl.parse_date(args.start, strict_iso=True) if args.start else fl.today()
        except ValueError:
            p.error("--start must use YYYY-MM-DD; got %r" % args.start)
        if unit == "day":
            try:
                start = fl.next_workday(start, workdays)
            except OverflowError:
                p.error("forecast date exceeds Python's supported range")

        mean_throughput = sum(series) / float(len(series))
        cap = min(100_000, max(200, int(math.ceil(effective / mean_throughput)) * 20))
        if effective > max(series) * cap:
            p.error(
                "forecast cannot complete within the simulation safety limit; "
                "reduce the scope or provide a more representative history"
            )
        runs = sim_when(series, effective, args.trials, rng, cap)
        unsupported = unsupported_confidences(runs, confidences)
        if unsupported:
            p.error(
                "forecast cannot support requested confidence level(s) %s within the simulation "
                "safety limit; reduce the scope or inspect zero-throughput periods"
                % ",".join("%g" % value for value in unsupported)
            )
        results = [run.periods for run in runs]

        out.append("Forecast: when will %d items be done" % items)
        if split != 1:
            out.append("  Scope adjustment: x%.2f applied, simulating %d item%s"
                       % (split, effective, "" if effective == 1 else "s"))
        out.append("  Starting %s, %d trials sampled from raw historical throughput"
                   % (start.isoformat(), args.trials))
        censored = sum(not run.completed for run in runs)
        if censored:
            out.append(
                "  %d trial%s exceeded the safety horizon; requested percentiles remain "
                "statistically supported" % (censored, "" if censored == 1 else "s")
            )
        out.append("")
        try:
            dated_results = {
                c: (
                    fl.percentile(results, c),
                    periods_to_date(
                        start, fl.percentile(results, c), unit, workdays
                    ),
                )
                for c in confidences
            }
        except OverflowError:
            p.error("forecast date exceeds Python's supported range")
        for c in sorted(confidences):
            periods, when = dated_results[c]
            out.append("  %2g%% chance of finishing on or before %s  (%d working %ss)"
                       % (c, when.isoformat(), periods, unit))
        out.append("")
        top = 85.0 if 85.0 in confidences else max(confidences)
        when = dated_results[top][1]
        out.append("  Say it out loud as: \"We have %s %g%% chance of finishing these %d items "
                   "on or before %s.\"" % (article(top), top, items, when.isoformat()))
        out.append("  \"On or before\" is not decoration. Dropping it turns a forecast into a deadline.")

    out.append("")
    out.append("  This is a forecast, not a commitment. Re-run it when scope, the team, or "
               "the workflow changes.")
    print("\n".join(out))


if __name__ == "__main__":
    sys.exit(main())

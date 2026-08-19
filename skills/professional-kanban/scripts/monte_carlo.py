#!/usr/bin/env python3
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
  --unit day|week      sampling unit (default: day)
  --workdays mon-fri   which days the system runs (default: mon-fri; use "all")
  --trials 10000       number of simulated runs
  --from / --to        limit the historical window (YYYY-MM-DD)
  --split N            split each remaining item into N (scope-growth check)
  --confidence 50,70,85,95   percentiles to report
"""

import argparse
from dataclasses import dataclass
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

    first = window_from or min(filtered)
    last = window_to or max(filtered)
    if first > last:
        raise ValueError("Historical window starts after it ends.")

    series = []
    period = first
    step = timedelta(days=7 if inferred_unit == "week" else 1)
    while period <= last:
        if inferred_unit == "week" or fl.is_workday(period, workdays):
            series.append(filtered.get(period, 0))
        period += step
    if not series:
        raise ValueError("Historical window contains no working periods.")

    return ThroughputHistory(
        series=series,
        first=first,
        last=last,
        item_count=sum(filtered.values()),
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
        results.append(periods)
    return results


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
        day += timedelta(days=1)
    return count


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("mode", choices=["how-many", "when"])
    p.add_argument("--input", "-i", required=True, help="CSV of historical completions")
    p.add_argument("--days", type=int, help="how-many: forecast horizon in calendar days")
    p.add_argument("--weeks", type=int, help="how-many: forecast horizon in whole weeks")
    p.add_argument("--by", help="how-many: forecast horizon as a date (YYYY-MM-DD)")
    p.add_argument("--items", type=int, help="when: number of items remaining")
    p.add_argument("--split", type=float, default=1.0,
                   help="when: multiply remaining items (e.g. 1.3 for 30%% expected scope growth)")
    p.add_argument("--start", help="forecast start date (default: today)")
    p.add_argument("--unit", choices=["day", "week"], default=None,
                   help="sampling unit (normally inferred from the input)")
    p.add_argument("--workdays", default="mon-fri")
    p.add_argument("--trials", type=int, default=10000)
    p.add_argument("--from", dest="window_from", help="earliest history to use (YYYY-MM-DD)")
    p.add_argument("--to", dest="window_to", help="latest history to use (YYYY-MM-DD)")
    p.add_argument("--confidence", default="50,70,85,95")
    p.add_argument("--seed", type=int, default=None, help="fix the RNG for reproducible output")
    p.add_argument("--date-order", choices=["mdy", "dmy"],
                   help="interpret ambiguous numeric CSV dates as month/day or day/month")
    args = p.parse_args()

    workdays = fl.parse_workdays(args.workdays)
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
    confidences = [float(c) for c in args.confidence.split(",") if c.strip()]
    rng = random.Random(args.seed)

    try:
        history = load_throughput(
            args.input, args.unit, workdays, window_from, window_to, args.date_order
        )
    except ValueError as exc:
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
            end = start + timedelta(days=7 * args.weeks - 1)
            horizon = "in the next %d week%s (%d working weeks)" % (
                args.weeks, "" if args.weeks == 1 else "s", periods
            )
        elif args.days is not None:
            if unit == "week":
                p.error("Weekly history cannot support a partial-week --days horizon; use --weeks.")
            end = start + timedelta(days=args.days - 1)
            periods = working_periods_between(start, end, unit, workdays)
            horizon = "in the next %d day%s (%d working days)" % (
                args.days, "" if args.days == 1 else "s", periods
            )
        else:
            raise SystemExit("how-many needs --days, --weeks, or --by")

        results = sim_how_many(series, periods, args.trials, rng)
        out.append("Forecast: how many items %s" % horizon)
        out.append("  %d trials sampled from raw historical throughput" % args.trials)
        out.append("")
        for c in sorted(confidences, reverse=True):
            n = fl.lower_percentile(results, c)
            out.append("  %2g%% chance of completing %d items or more" % (c, n))
        out.append("")
        headline = 85.0 if 85.0 in confidences else max(confidences)
        out.append("  Say it out loud as: \"We have %s %g%% chance of completing %d items "
                   "or more %s.\"" % (article(headline), headline,
                                      fl.lower_percentile(results, headline), horizon))
        out.append("  Higher confidence is always a smaller number. 100% confidence would be "
                   "\"zero items or more\", which is why 100% is the wrong ask.")

    else:
        if not args.items:
            raise SystemExit("when needs --items")
        items = args.items
        effective = int(round(items * args.split))
        try:
            start = fl.parse_date(args.start, strict_iso=True) if args.start else fl.today()
        except ValueError:
            p.error("--start must use YYYY-MM-DD; got %r" % args.start)
        start = fl.next_workday(start, workdays)

        cap = max(200, int(items / max(0.05, sum(series) / float(len(series)))) * 20)
        results = sim_when(series, effective, args.trials, rng, cap)

        out.append("Forecast: when will %d items be done" % items)
        if args.split != 1.0:
            out.append("  Scope adjustment: x%.2f applied, simulating %d items" % (args.split, effective))
        out.append("  Starting %s, %d trials sampled from raw historical throughput"
                   % (start.isoformat(), args.trials))
        out.append("")
        for c in sorted(confidences):
            periods = fl.percentile(results, c)
            when = periods_to_date(start, periods, unit, workdays)
            out.append("  %2g%% chance of finishing on or before %s  (%d working %ss)"
                       % (c, when.isoformat(), periods, unit))
        out.append("")
        top = 85.0 if 85.0 in confidences else max(confidences)
        when = periods_to_date(start, fl.percentile(results, top), unit, workdays)
        out.append("  Say it out loud as: \"We have %s %g%% chance of finishing these %d items "
                   "on or before %s.\"" % (article(top), top, items, when.isoformat()))
        out.append("  \"On or before\" is not decoration. Dropping it turns a forecast into a deadline.")

    out.append("")
    out.append("  This is a forecast, not a commitment. Re-run it when scope, the team, or "
               "the workflow changes.")
    print("\n".join(out))


if __name__ == "__main__":
    sys.exit(main())

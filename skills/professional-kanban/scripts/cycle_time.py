#!/usr/bin/env python3
"""Cycle time percentiles, SLE, and work item aging.

Answers single-item questions only:
  sle     Calculate cycle time percentiles and state the SLE properly.
  aging   Compare in-progress items against those percentiles and flag
          which ones need a conversation today.

Usage
-----
  python3 cycle_time.py sle --input done.csv
  python3 cycle_time.py sle --input done.csv --percentiles 50,70,85,95
  python3 cycle_time.py aging --input done.csv --wip wip.csv
  python3 cycle_time.py aging --input done.csv --wip wip.csv --as-of 2026-08-14

Input for `sle` (--input), any of:
  (a) started + finished date columns  -> cycle time is calculated
  (b) a cycle time column (cycle_time / flow_time / lead_time / days)

Input for `aging` (--wip):
  in-progress items with a started date column, and optionally a name/id
  column and a state column.

Cycle time is inclusive of both endpoints: started and finished on the same
day is 1 day, not 0. An item cannot take zero days.
"""

import argparse
import sys
from datetime import timedelta

import flowlib as fl

NAME_NAMES = ["item", "name", "id", "key", "title", "ticket", "summary", "issue", "card"]
STATE_NAMES = ["state", "status", "column", "stage", "step"]
DEFAULT_PCTS = [50, 70, 85, 95]


def load_cycle_times(path, window_from, window_to, date_order=None):
    rows, headers = fl.read_rows(path)
    start_col = fl.find_column(headers, fl.STARTED_NAMES)
    finish_col = fl.find_column(headers, fl.FINISHED_NAMES)
    ct_col = fl.find_column(headers, fl.CYCLETIME_NAMES)

    values, finishes, skipped = [], [], 0

    if start_col and finish_col:
        for row_number, row in enumerate(rows, 2):
            try:
                s = fl.parse_date(row.get(start_col), date_order=date_order)
                f = fl.parse_date(row.get(finish_col), date_order=date_order)
            except ValueError as exc:
                raise ValueError("Row %d: %s" % (row_number, exc)) from exc
            if s is None or f is None:
                skipped += 1
                continue
            if f < s:
                skipped += 1
                continue
            if window_from and f < window_from:
                continue
            if window_to and f > window_to:
                continue
            values.append((f - s).days + 1)
            finishes.append(f)
        source = "calculated from '%s' to '%s' (inclusive of both days)" % (start_col, finish_col)
    elif ct_col:
        for row in rows:
            raw = (row.get(ct_col) or "").strip()
            if not raw:
                skipped += 1
                continue
            try:
                v = float(raw)
            except ValueError:
                skipped += 1
                continue
            if v <= 0:
                skipped += 1
                continue
            values.append(v)
        source = "cycle time column '%s'" % ct_col
    else:
        raise SystemExit(
            "Need either started+finished date columns or a cycle time column.\n"
            "Headers seen: %s" % ", ".join(headers.values())
        )

    if not values:
        raise SystemExit("No usable cycle times found in %s" % path)
    return values, finishes, skipped, source


def load_wip(path, as_of, date_order=None):
    rows, headers = fl.read_rows(path)
    start_col = fl.find_column(headers, fl.STARTED_NAMES)
    if not start_col:
        raise SystemExit(
            "The WIP file needs a started-date column.\n"
            "Headers seen: %s" % ", ".join(headers.values())
        )
    finish_col = fl.find_column(headers, fl.FINISHED_NAMES)
    name_col = fl.find_column(headers, NAME_NAMES)
    state_col = fl.find_column(headers, STATE_NAMES)

    items, not_started, already_done = [], 0, 0
    for i, row in enumerate(rows, 1):
        try:
            started = fl.parse_date(row.get(start_col), date_order=date_order)
            finished = (
                fl.parse_date(row.get(finish_col), date_order=date_order)
                if finish_col
                else None
            )
        except ValueError as exc:
            raise ValueError("Row %d: %s" % (i + 1, exc)) from exc
        if started is None:
            not_started += 1  # Age applies only to items in progress.
            continue
        if finished is not None:
            already_done += 1
            continue
        items.append({
            "name": (row.get(name_col) or "").strip() if name_col else "Item %d" % i,
            "state": (row.get(state_col) or "").strip() if state_col else "",
            "started": started,
            "age": (as_of - started).days + 1,
        })
    return items, not_started, already_done


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("mode", choices=["sle", "aging"])
    p.add_argument("--input", "-i", required=True, help="CSV of finished items")
    p.add_argument("--wip", help="aging: CSV of items currently in progress")
    p.add_argument("--as-of", help="aging: date to age against (default: today)")
    p.add_argument("--percentiles", default="50,70,85,95")
    p.add_argument("--sle", type=float, default=85.0, help="which percentile is the SLE (default 85)")
    p.add_argument("--from", dest="window_from", help="earliest finish date to include")
    p.add_argument("--to", dest="window_to", help="latest finish date to include")
    p.add_argument("--date-order", choices=["mdy", "dmy"],
                   help="interpret ambiguous numeric CSV dates as month/day or day/month")
    args = p.parse_args()

    pcts = sorted(float(x) for x in args.percentiles.split(",") if x.strip())
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
        values, finishes, skipped, source = load_cycle_times(
            args.input, window_from, window_to, args.date_order
        )
    except ValueError as exc:
        p.error(str(exc))
    table = {c: fl.percentile(values, c) for c in pcts}
    if args.sle not in table:
        table[args.sle] = fl.percentile(values, args.sle)
    sle_days = table[args.sle]

    out = []
    out.append("Cycle time")
    out.append("  Source:  %s" % source)
    if finishes:
        out.append("  Window:  %s to %s" % (min(finishes).isoformat(), max(finishes).isoformat()))
    out.append("  Items:   %d%s" % (len(values), (" (%d rows skipped)" % skipped) if skipped else ""))
    if len(values) < 10:
        out.append("  ! Fewer than 10 items. Percentiles will move a lot as data arrives; "
                   "use this as a best guess and recalculate soon.")
    out.append("")
    out.append("  Percentile   Days")
    for c in sorted(table):
        marker = "   <- SLE" if c == args.sle else ""
        out.append("  %6gth   %8g%s" % (c, table[c], marker))
    out.append("")
    out.append("  SLE: %g%% of work items finish in %g days or less, once started."
               % (args.sle, sle_days))
    out.append("  Both halves are required. \"Our SLE is %g days\" on its own is a target, "
               "and targets get read as promises." % sle_days)
    out.append("  Right-sizing: items that plausibly fit in %g days are right-sized for this "
               "system. Do not estimate in hours." % sle_days)

    if args.mode == "sle":
        print("\n".join(out))
        return

    if not args.wip:
        raise SystemExit("aging needs --wip pointing at your in-progress items")

    try:
        as_of = fl.parse_date(args.as_of, strict_iso=True) if args.as_of else fl.today()
    except ValueError:
        p.error("--as-of must use YYYY-MM-DD; got %r" % args.as_of)
    try:
        items, not_started, already_done = load_wip(args.wip, as_of, args.date_order)
    except ValueError as exc:
        p.error(str(exc))

    lower = [c for c in sorted(table) if c < args.sle]
    p50 = table.get(50)
    p70 = table.get(70)

    out.append("")
    out.append("Work item age as of %s" % as_of.isoformat())
    out.append("  WIP: %d items in progress" % len(items))
    if not_started:
        out.append("  %d row(s) had no start date and were excluded. Age applies only to "
                   "items in progress." % not_started)
    if already_done:
        out.append("  %d row(s) were already finished and were excluded." % already_done)
    if not items:
        out.append("  Nothing in progress to age.")
        print("\n".join(out))
        return

    out.append("")
    out.append("  %-28s %-14s %5s   %s" % ("Item", "State", "Age", "Signal"))
    for item in sorted(items, key=lambda i: -i["age"]):
        age = item["age"]
        if age > sle_days:
            signal = "PAST THE SLE - it is now in the slowest %g%% of everything this system has done" % (100 - args.sle)
        elif p70 is not None and age > p70:
            signal = "past the 70th - roughly a 50% chance of breaching the SLE. Swarm it, split it, or escalate today"
        elif p50 is not None and age > p50:
            signal = "past the 50th - older than half of all prior items. Worth a conversation"
        else:
            signal = "within normal range"
        out.append("  %-28s %-14s %4dd   %s"
                   % (item["name"][:28], item["state"][:14], age, signal))

    breaching = [i for i in items if i["age"] > sle_days]
    urgent = [i for i in items if p70 is not None and p70 < i["age"] <= sle_days]
    out.append("")
    out.append("  %d past the SLE, %d past the 70th percentile." % (len(breaching), len(urgent)))
    out.append("  Older items are more likely to get older still. The two things that reduce "
               "aging are finishing work and not starting work.")
    out.append("  An aging item is usually a too-big item. Ask whether it can be split into "
               "pieces that are each still valuable, before asking for a new estimate.")
    print("\n".join(out))


if __name__ == "__main__":
    sys.exit(main())

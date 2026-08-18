"""Shared helpers for the Professional Kanban scripts.

Standard library only, so the scripts run anywhere Python 3.8+ is installed.
No pandas, no numpy, no install step.
"""

import csv
import math
import re
from datetime import date, datetime, timedelta

# Column names we recognise, in priority order. Matching is case-insensitive
# and ignores spaces, underscores and hyphens.
FINISHED_NAMES = [
    "finished", "finisheddate", "completed", "completeddate", "done", "donedate",
    "closed", "closeddate", "enddate", "end", "resolutiondate", "resolved",
    "finishdate", "completiondate", "deliverydate",
]
STARTED_NAMES = [
    "started", "starteddate", "start", "startdate", "begin", "begandate",
    "inprogress", "inprogressdate", "activated", "commitmentdate", "committed",
]
COUNT_NAMES = ["count", "throughput", "items", "itemcount", "completed", "delivered", "numitems"]
CYCLETIME_NAMES = ["cycletime", "flowtime", "leadtime", "days", "duration", "elapsed", "age"]
PERIOD_NAMES = ["date", "week", "weekending", "period", "day", "month"]

DATE_FORMATS = [
    "%Y-%m-%d", "%Y/%m/%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y", "%m-%d-%Y",
    "%d %b %Y", "%d %B %Y", "%b %d %Y", "%B %d %Y", "%d-%b-%Y", "%Y%m%d",
    "%m/%d/%y", "%d/%m/%y",
]


def normalise(name):
    return re.sub(r"[^a-z0-9]", "", (name or "").lower())


def parse_date(value):
    """Parse a date from a string. Returns a date, or None if unparseable."""
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    # Trim an ISO timestamp down to its date part.
    text = re.split(r"[T ]", text)[0] if re.match(r"^\d{4}-\d{2}-\d{2}", text) else text
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def read_rows(path):
    """Read a CSV (or TSV) into a list of dicts keyed by normalised header."""
    with open(path, newline="", encoding="utf-8-sig") as handle:
        sample = handle.read(4096)
        handle.seek(0)
        delimiter = "\t" if sample.count("\t") > sample.count(",") else ","
        reader = csv.DictReader(handle, delimiter=delimiter)
        if not reader.fieldnames:
            raise ValueError("No header row found in %s" % path)
        headers = {normalise(h): h for h in reader.fieldnames if h}
        rows = [dict(r) for r in reader]
    return rows, headers


def find_column(headers, candidates):
    """Return the original header name for the first candidate that matches."""
    for candidate in candidates:
        if candidate in headers:
            return headers[candidate]
    # Fall back to a substring match (e.g. "story_finished_on").
    for candidate in candidates:
        for norm, original in headers.items():
            if candidate in norm:
                return original
    return None


def percentile(values, pct):
    """Nearest-rank percentile.

    Returns the smallest observed value at or below which at least `pct` of
    the data falls. This is the right choice for flow work: the answer is
    always a value the system actually produced, never an interpolated
    number that never happened.
    """
    if not values:
        raise ValueError("Cannot take a percentile of an empty data set")
    ordered = sorted(values)
    rank = max(1, math.ceil(pct / 100.0 * len(ordered)))
    return ordered[min(rank, len(ordered)) - 1]


def lower_percentile(values, confidence):
    """The 'X or more' end of a distribution.

    An 85% chance of 'N items or more' is the 15th percentile of simulated
    outcomes: 85% of trials landed at or above it.
    """
    return percentile(values, 100 - confidence)


def is_workday(day, workdays):
    return day.weekday() in workdays


def parse_workdays(spec):
    """'mon-fri' -> {0,1,2,3,4}; 'all' -> every day; 'mon,tue,wed' also works."""
    names = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
    spec = (spec or "mon-fri").strip().lower()
    if spec in ("all", "every", "7", "everyday"):
        return set(range(7))
    if "-" in spec and "," not in spec:
        start, end = spec.split("-", 1)
        try:
            i, j = names.index(start[:3]), names.index(end[:3])
        except ValueError:
            raise ValueError("Could not read workdays: %s" % spec)
        return set(range(i, j + 1)) if i <= j else set(range(i, 7)) | set(range(0, j + 1))
    out = set()
    for part in spec.split(","):
        part = part.strip()[:3]
        if part in names:
            out.add(names.index(part))
    if not out:
        raise ValueError("Could not read workdays: %s" % spec)
    return out


def daily_throughput(finish_dates, workdays, start=None, end=None):
    """Turn a list of completion dates into a per-day count series.

    Days with zero completions are included on purpose: they are real
    observations of the system, and dropping them inflates the forecast.
    Non-working days are excluded entirely rather than counted as zeros.
    """
    if not finish_dates:
        raise ValueError("No completion dates found")
    first = start or min(finish_dates)
    last = end or max(finish_dates)
    counts = {}
    for d in finish_dates:
        if first <= d <= last:
            counts[d] = counts.get(d, 0) + 1
    series, day = [], first
    while day <= last:
        if is_workday(day, workdays):
            series.append(counts.get(day, 0))
        day += timedelta(days=1)
    return series, first, last


def weekly_throughput(finish_dates, start=None, end=None):
    """Per-week counts, weeks running Monday to Sunday."""
    if not finish_dates:
        raise ValueError("No completion dates found")
    first = (start or min(finish_dates))
    first -= timedelta(days=first.weekday())
    last = end or max(finish_dates)
    counts = {}
    for d in finish_dates:
        week = d - timedelta(days=d.weekday())
        if week >= first:
            counts[week] = counts.get(week, 0) + 1
    series, week = [], first
    while week <= last:
        series.append(counts.get(week, 0))
        week += timedelta(days=7)
    return series, first, last


def next_workday(day, workdays):
    while not is_workday(day, workdays):
        day += timedelta(days=1)
    return day


def fmt_date(d):
    return d.strftime("%A %d %B %Y").replace(" 0", " ")


def today():
    return date.today()

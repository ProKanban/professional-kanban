"""Shared helpers for the Professional Kanban scripts.

Standard library only, so the scripts run anywhere Python 3.11+ is installed.
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
    "%d %b %Y", "%d %B %Y", "%b %d %Y", "%B %d %Y", "%d-%b-%Y", "%Y%m%d",
]


def normalise(name):
    return re.sub(r"[^a-z0-9]", "", (name or "").lower())


def parse_date(value, date_order=None, strict_iso=False):
    """Parse a date, rejecting ambiguous numeric day/month ordering.

    ISO dates are always accepted. Numeric dates with the year last are
    inferred only when one component is greater than 12; otherwise callers
    must choose ``mdy`` or ``dmy`` explicitly.
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    if not text:
        return None
    if date_order not in (None, "mdy", "dmy"):
        raise ValueError("date order must be 'mdy' or 'dmy'")

    # Trim an ISO timestamp down to its date part.
    text = re.split(r"[T ]", text)[0] if re.match(r"^\d{4}-\d{2}-\d{2}", text) else text
    if strict_iso:
        try:
            return datetime.strptime(text, "%Y-%m-%d").date()
        except ValueError as exc:
            raise ValueError("date must use YYYY-MM-DD: %s" % text) from exc

    iso_match = re.fullmatch(r"\d{4}([-／/])\d{1,2}\1\d{1,2}", text)
    if iso_match:
        separator = iso_match.group(1)
        try:
            return datetime.strptime(text, f"%Y{separator}%m{separator}%d").date()
        except ValueError:
            return None

    numeric = re.fullmatch(r"(\d{1,2})([/-])(\d{1,2})\2(\d{2}|\d{4})", text)
    if numeric:
        first, separator, second, year = numeric.groups()
        first_number, second_number = int(first), int(second)
        order = date_order
        if order is None:
            if first_number <= 12 and second_number <= 12:
                raise ValueError(
                    "ambiguous date '%s'; use --date-order mdy or --date-order dmy" % text
                )
            if first_number > 12 and second_number <= 12:
                order = "dmy"
            elif second_number > 12 and first_number <= 12:
                order = "mdy"
            else:
                return None
        year_format = "%y" if len(year) == 2 else "%Y"
        format_string = (
            f"%m{separator}%d{separator}{year_format}"
            if order == "mdy"
            else f"%d{separator}%m{separator}{year_format}"
        )
        try:
            return datetime.strptime(text, format_string).date()
        except ValueError:
            return None

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


def _contains_candidate_token(original, candidate):
    """Return whether a normalized candidate spans complete header tokens."""
    tokens = re.findall(r"[a-z0-9]+", (original or "").lower())
    for start in range(len(tokens)):
        combined = ""
        for token in tokens[start:]:
            combined += token
            if combined == candidate:
                return True
            if len(combined) >= len(candidate):
                break
    return False


def find_column(headers, candidates, *, exclude=()):
    """Return an exact or token-boundary column match in candidate order."""
    excluded = set(exclude)
    for candidate in candidates:
        if candidate in headers and headers[candidate] not in excluded:
            return headers[candidate]
    # Fall back to complete tokens (e.g. "story_finished_on"), never arbitrary
    # substrings such as count in Country or Account.
    for candidate in candidates:
        matches = [
            original
            for original in headers.values()
            if original not in excluded
            and not (
                candidates is COUNT_NAMES
                and candidate in ("completed", "delivered")
                and len(re.findall(r"[a-z0-9]+", original.lower())) > 1
            )
            and _contains_candidate_token(original, candidate)
        ]
        if len(matches) > 1:
            raise ValueError(
                "Multiple columns match '%s': %s" % (candidate, ", ".join(matches))
            )
        if matches:
            return matches[0]
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


def lower_bound(values, confidence):
    """Largest observed outcome met or exceeded by ``confidence`` percent."""
    if not values:
        raise ValueError("Cannot take a confidence bound of an empty data set")
    if not math.isfinite(confidence) or not 0 < confidence < 100:
        raise ValueError("Confidence must be a finite number between 0 and 100")
    ordered = sorted(values)
    required = confidence / 100.0
    answer = ordered[0]
    for candidate in sorted(set(ordered)):
        proportion_at_or_above = sum(value >= candidate for value in ordered) / len(ordered)
        if proportion_at_or_above >= required:
            answer = candidate
        else:
            break
    return answer


def lower_percentile(values, confidence):
    """Backward-compatible alias for :func:`lower_bound`."""
    return lower_bound(values, confidence)


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

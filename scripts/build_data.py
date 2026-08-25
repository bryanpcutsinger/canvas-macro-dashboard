#!/usr/bin/env python3
"""Build docs/data/dashboard.json from FRED.

Design: stale-but-labeled beats broken. Each indicator is pulled and validated
independently. If one fails, its block is carried forward unchanged from the
previous dashboard.json with status "stale", the page keeps working, and the
workflow's final step fails the job (which triggers a GitHub failure email).

Run:  FRED_API_KEY=... python3 scripts/build_data.py
"""

import json
import os
import sys
import tempfile
from datetime import date, datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import fred_client as fred
from series_config import (FETCH_START, HISTORY_START, INDICATORS,
                           MAX_OBS_AGE_DAYS, PLAUSIBLE_RANGE,
                           SERIES_EXPECTATIONS)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_PATH = os.path.join(REPO_ROOT, "docs", "data", "dashboard.json")
PROVENANCE_PATH = os.path.join(REPO_ROOT, "logs", "provenance.jsonl")

GDP_CROSSCHECK_TOLERANCE_PP = 0.15   # BEA headline vs. our pca(GDPC1)
YOY_CROSSCHECK_TOLERANCE_PP = 0.05   # our YoY vs. FRED units=pc1

_provenance_lines = []
_run_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------- transforms

def yoy(obs):
    """12-month percent change computed from monthly index levels."""
    by_month = {d[:7]: v for d, v in obs}
    out = []
    for d, v in obs:
        year, month = int(d[:4]), int(d[5:7])
        prior = f"{year - 1:04d}-{month:02d}"
        if prior in by_month and by_month[prior] != 0:
            out.append((d, 100.0 * (v / by_month[prior] - 1.0)))
    return out


def annualized_qoq(obs):
    """Compounded annual rate of change from quarterly levels (FRED 'pca')."""
    out = []
    for i in range(1, len(obs)):
        prev, cur = obs[i - 1][1], obs[i][1]
        if prev > 0:
            out.append((obs[i][0], 100.0 * ((cur / prev) ** 4 - 1.0)))
    return out


def recession_ranges(obs):
    """Contiguous runs of USREC == 1 as [{start, end, ongoing}]."""
    ranges, start, prev_date = [], None, None
    for d, v in obs:
        if v == 1 and start is None:
            start = d
        elif v == 0 and start is not None:
            ranges.append({"start": start, "end": prev_date, "ongoing": False})
            start = None
        prev_date = d
    if start is not None:
        ranges.append({"start": start, "end": prev_date, "ongoing": True})
    return ranges


# ------------------------------------------------------------------- helpers

def month_label(d):
    return datetime.strptime(d, "%Y-%m-%d").strftime("%B %Y")


def month_abbr(d):
    return datetime.strptime(d, "%Y-%m-%d").strftime("%b")


def quarter_label(d):
    dt = datetime.strptime(d, "%Y-%m-%d")
    return f"Q{(dt.month - 1) // 3 + 1} {dt.year}"


def direction(change):
    if abs(change) < 0.005:
        return "flat"
    return "up" if change > 0 else "down"


def points(obs, ndigits=2):
    return [{"d": d, "v": round(v, ndigits)} for d, v in obs]


def since(obs, start):
    return [(d, v) for d, v in obs if d >= start]


def fetch_checked(series_id, start, cadence, **extra):
    """Fetch metadata + observations; assert metadata; log provenance."""
    meta = fred.series_meta(series_id)
    expected = SERIES_EXPECTATIONS[series_id]
    for field, want in expected.items():
        got = meta[field]
        if got != want:
            raise fred.FredError(
                f"{series_id}: metadata changed — {field} is {got!r}, expected {want!r}")
    obs = fred.observations(series_id, start, **extra)

    latest = obs[-1][0]
    age_days = (date.today() - datetime.strptime(latest, "%Y-%m-%d").date()).days
    lag_warning = None
    if age_days > MAX_OBS_AGE_DAYS[cadence]:
        lag_warning = f"{series_id}: latest observation {latest} is {age_days} days old"

    _provenance_lines.append({
        "run_utc": _run_utc,
        "series_id": series_id,
        "title": meta["title"],
        "units": meta["units"],
        "frequency": meta["frequency"],
        "seasonal_adjustment": meta["seasonal_adjustment"],
        "series_last_updated": meta["last_updated"],
        "observation_count": len(obs),
        "latest_obs_date": latest,
        "request": fred.redacted_url("series/observations",
                                     {"series_id": series_id,
                                      "observation_start": start, **extra}),
        "lag_warning": lag_warning,
    })
    return meta, obs, lag_warning


def source_block(series_id, meta, transformation, origin):
    return {
        "series_id": series_id,
        "title": meta["title"],
        "units": meta["units"],
        "frequency": meta["frequency"],
        "seasonal_adjustment": meta["seasonal_adjustment"],
        "origin": origin,
        "transformation": transformation,
        "fred_url": f"https://fred.stlouisfed.org/series/{series_id}",
        "series_last_updated": meta["last_updated"],
        "fetched_at_utc": _run_utc,
    }


def check_plausible(key, value):
    lo, hi = PLAUSIBLE_RANGE[key]
    if not (lo <= value <= hi):
        raise fred.FredError(
            f"{key}: latest value {value} outside plausible range [{lo}, {hi}]")


# ------------------------------------------------------------ indicator builds

def build_unemployment(copy):
    meta, obs, lag = fetch_checked("UNRATE", FETCH_START, "monthly")
    history = since(obs, HISTORY_START)
    (last_d, last_v), (prev_d, prev_v) = history[-1], history[-2]
    change = last_v - prev_v
    check_plausible("unemployment", last_v)
    return {
        **copy,
        "value": round(last_v, 2),
        "value_display": f"{last_v:.1f}%",
        "units": "percent of labor force",
        "as_of": last_d,
        "period_label": month_label(last_d),
        "change": round(change, 2),
        "change_units": "pp",
        "change_label": f"vs. {month_abbr(prev_d)}",
        "direction": direction(change),
        "status": "ok",
        "source": source_block("UNRATE", meta, "level, as published", copy["origin"]),
        "spark": points(history[-25:]),
        "history": points(history),
        "history_cadence": "monthly",
    }, ([lag] if lag else [])


def build_gdp(copy):
    meta, obs, lag = fetch_checked("A191RL1Q225SBEA", FETCH_START, "quarterly")
    # Independent cross-check: recompute the growth rate from real GDP levels.
    _, levels, _ = fetch_checked("GDPC1", "2023-01-01", "quarterly")
    computed = dict(annualized_qoq(levels))
    for d, published in obs[-8:]:
        if d in computed and abs(computed[d] - published) > GDP_CROSSCHECK_TOLERANCE_PP:
            raise fred.FredError(
                f"GDP cross-check failed at {d}: published {published}, "
                f"computed from GDPC1 {computed[d]:.2f}")
    history = since(obs, HISTORY_START)
    (last_d, last_v), (prev_d, prev_v) = history[-1], history[-2]
    change = last_v - prev_v
    check_plausible("gdp_growth", last_v)
    return {
        **copy,
        "value": round(last_v, 2),
        "value_display": f"{last_v:.1f}%",
        "units": "percent, annualized quarterly rate",
        "as_of": last_d,
        "period_label": quarter_label(last_d),
        "change": round(change, 2),
        "change_units": "pp",
        "change_label": f"vs. {quarter_label(prev_d).split()[0]}",
        "direction": direction(change),
        "status": "ok",
        "source": source_block("A191RL1Q225SBEA", meta,
                               "BEA headline growth rate, cross-checked against "
                               "the compounded annual rate computed from GDPC1 levels",
                               copy["origin"]),
        "spark": points(history[-9:]),
        "history": points(history),
        "history_cadence": "quarterly",
    }, ([lag] if lag else [])


def _build_inflation(copy, series_id, key):
    meta, obs, lag = fetch_checked(series_id, FETCH_START, "monthly")
    rates = yoy(obs)
    # Independent cross-check against FRED's own YoY transformation.
    check_start = rates[-13][0]
    fred_yoy = fred.observations(series_id, check_start, units="pc1")
    fred_by_date = dict(fred_yoy)
    for d, ours in rates[-12:]:
        if d in fred_by_date and abs(ours - fred_by_date[d]) > YOY_CROSSCHECK_TOLERANCE_PP:
            raise fred.FredError(
                f"{series_id} YoY cross-check failed at {d}: "
                f"computed {ours:.3f}, FRED pc1 {fred_by_date[d]:.3f}")
    history = since(rates, HISTORY_START)
    (last_d, last_v), (prev_d, prev_v) = history[-1], history[-2]
    change = last_v - prev_v
    check_plausible(key, last_v)
    return {
        **copy,
        "value": round(last_v, 2),
        "value_display": f"{last_v:.1f}%",
        "units": "percent change vs. year ago",
        "as_of": last_d,
        "period_label": month_label(last_d),
        "change": round(change, 2),
        "change_units": "pp",
        "change_label": f"vs. {month_abbr(prev_d)}",
        "direction": direction(change),
        "status": "ok",
        "source": source_block(
            series_id, meta,
            "12-month percent change computed from index levels, "
            "cross-checked against FRED's pc1 transformation",
            copy["origin"]),
        "spark": points(history[-25:]),
        "history": points(history),
        "history_cadence": "monthly",
    }, ([lag] if lag else [])


def build_cpi(copy):
    return _build_inflation(copy, "CPIAUCNS", "cpi_inflation")


def build_pce(copy):
    return _build_inflation(copy, "PCEPI", "pce_inflation")


def build_fed_funds(copy):
    monthly_meta, monthly, lag_m = fetch_checked("FEDFUNDS", FETCH_START, "monthly")
    daily_start = (date.today() - timedelta(days=450)).isoformat()
    daily_meta, daily, lag_d = fetch_checked("DFF", daily_start, "daily")
    last_d, last_v = daily[-1]
    # Change vs. one year ago: nearest daily observation on or before that date.
    year_ago = (datetime.strptime(last_d, "%Y-%m-%d").date()
                - timedelta(days=365)).isoformat()
    base = [pair for pair in daily if pair[0] <= year_ago]
    base_d, base_v = base[-1] if base else daily[0]
    change = last_v - base_v
    check_plausible("fed_funds", last_v)
    history = since(monthly, HISTORY_START)
    warnings = [w for w in (lag_m, lag_d) if w]
    return {
        **copy,
        "value": round(last_v, 2),
        "value_display": f"{last_v:.2f}%",
        "units": "percent, effective rate",
        "as_of": last_d,
        "period_label": datetime.strptime(last_d, "%Y-%m-%d").strftime("%b %-d, %Y"),
        "change": round(change, 2),
        "change_units": "pp",
        "change_label": "vs. a year ago",
        "direction": direction(change),
        "status": "ok",
        "source": source_block(
            "DFF", daily_meta,
            "latest daily effective rate; the trend line shows the monthly "
            f"average (FEDFUNDS, last updated {monthly_meta['last_updated']})",
            copy["origin"]),
        "spark": points(history[-25:]),
        "history": points(history),
        "history_cadence": "monthly",
    }, warnings


BUILDERS = {
    "unemployment": build_unemployment,
    "gdp_growth": build_gdp,
    "cpi_inflation": build_cpi,
    "pce_inflation": build_pce,
    "fed_funds": build_fed_funds,
}


# ------------------------------------------------------------------ assembly

def load_previous():
    try:
        with open(OUTPUT_PATH) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def main():
    previous = load_previous()
    prev_indicators = {}
    if previous:
        prev_indicators = {ind["key"]: ind for ind in previous.get("indicators", [])}

    indicators, warnings = [], []

    for copy in INDICATORS:
        key = copy["key"]
        try:
            block, block_warnings = BUILDERS[key](copy)
            indicators.append(block)
            warnings.extend(block_warnings)
            print(f"ok      {key}: {block['value_display']} as of {block['as_of']}")
        except Exception as err:
            message = f"{key}: {err}"
            _provenance_lines.append({
                "run_utc": _run_utc, "series_id": key, "outcome": f"error: {err}"})
            if key in prev_indicators:
                stale = dict(prev_indicators[key])
                stale["status"] = "stale"
                indicators.append(stale)
                warnings.append(f"stale carry-forward — {message}")
                print(f"STALE   {message}", file=sys.stderr)
            else:
                # First run must be clean: no previous data to fall back on.
                print(f"FATAL   {message}", file=sys.stderr)
                raise

    try:
        _, usrec, _ = fetch_checked("USREC", HISTORY_START, "monthly")
        recessions = recession_ranges(usrec)
    except Exception as err:
        if previous and "recessions" in previous:
            recessions = previous["recessions"]
            warnings.append(f"recessions: stale carry-forward — {err}")
        else:
            raise

    output = {
        "schema_version": 1,
        "generated_at_utc": _run_utc,
        "build_status": "ok" if not any("stale" in w for w in warnings) else "partial",
        "warnings": warnings,
        "recessions": recessions,
        "indicators": indicators,
    }

    # Atomic write: never leave a half-written file for Pages to serve.
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(OUTPUT_PATH), suffix=".tmp")
    with os.fdopen(fd, "w") as f:
        json.dump(output, f, separators=(",", ":"))
    os.replace(tmp, OUTPUT_PATH)

    os.makedirs(os.path.dirname(PROVENANCE_PATH), exist_ok=True)
    with open(PROVENANCE_PATH, "a") as f:
        for line in _provenance_lines:
            f.write(json.dumps(line) + "\n")

    size_kb = os.path.getsize(OUTPUT_PATH) / 1024
    print(f"\nwrote {OUTPUT_PATH} ({size_kb:.0f} KB), "
          f"build_status={output['build_status']}")
    for w in warnings:
        print(f"warning: {w}", file=sys.stderr)


if __name__ == "__main__":
    main()

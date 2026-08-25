"""Series definitions and expected FRED metadata.

The `expect` block is asserted against the live FRED metadata on every run
(values captured from the FRED API on 2026-08-25). If BLS/BEA rebase an index
or FRED renames a series, the run fails that series loudly instead of silently
changing what students see.

CPI uses the NSA index (CPIAUCNS) because the BLS headline 12-month inflation
figure — the number reported in the news — is not seasonally adjusted.
"""

HISTORY_START = "1965-01-01"   # charts start here (covers the Great Inflation)
FETCH_START = "1964-01-01"     # one extra year so YoY exists at 1965-01

SERIES_EXPECTATIONS = {
    "UNRATE": {
        "units": "Percent",
        "frequency": "Monthly",
        "seasonal_adjustment": "Seasonally Adjusted",
    },
    "A191RL1Q225SBEA": {
        "units": "Percent Change from Preceding Period",
        "frequency": "Quarterly",
        "seasonal_adjustment": "Seasonally Adjusted Annual Rate",
    },
    "GDPC1": {
        "units": "Billions of Chained 2017 Dollars",
        "frequency": "Quarterly",
        "seasonal_adjustment": "Seasonally Adjusted Annual Rate",
    },
    "CPIAUCNS": {
        "units": "Index 1982-1984=100",
        "frequency": "Monthly",
        "seasonal_adjustment": "Not Seasonally Adjusted",
    },
    "PCEPI": {
        "units": "Index 2017=100",
        "frequency": "Monthly",
        "seasonal_adjustment": "Seasonally Adjusted",
    },
    "FEDFUNDS": {
        "units": "Percent",
        "frequency": "Monthly",
        "seasonal_adjustment": "Not Seasonally Adjusted",
    },
    "DFF": {
        "units": "Percent",
        "frequency": "Daily, 7-Day",
        "seasonal_adjustment": "Not Seasonally Adjusted",
    },
    "USREC": {
        "units": "+1 or 0",
        "frequency": "Monthly",
        "seasonal_adjustment": "Not Seasonally Adjusted",
    },
}

# Sanity ranges for the latest displayed value (percent). A value outside the
# range fails the series — a unit change or API glitch, not a real reading.
PLAUSIBLE_RANGE = {
    "unemployment": (1.0, 30.0),
    "gdp_growth": (-40.0, 40.0),
    "cpi_inflation": (-20.0, 30.0),
    "pce_inflation": (-20.0, 30.0),
    "fed_funds": (0.0, 25.0),
}

# Days since the latest observation before we log a data-lag warning.
# Generous: observation dates are period-start (a quarterly value dated
# Apr 1 is normal until late October).
MAX_OBS_AGE_DAYS = {"monthly": 100, "quarterly": 215, "daily": 12}

INDICATORS = [
    {
        "key": "unemployment",
        "label": "Unemployment rate",
        "plain_language": "The share of the labor force that is not working and is looking for work.",
        "origin": "BLS via FRED",
    },
    {
        "key": "gdp_growth",
        "label": "Real GDP growth",
        "plain_language": "How fast the economy's total output grew last quarter, at an annual rate, adjusted for inflation.",
        "origin": "BEA via FRED",
    },
    {
        "key": "cpi_inflation",
        "label": "CPI inflation",
        "plain_language": "Consumer prices vs. one year ago, measured by the Consumer Price Index — the inflation number in the news.",
        "origin": "BLS via FRED",
    },
    {
        "key": "pce_inflation",
        "label": "PCE inflation",
        "plain_language": "Consumer prices vs. one year ago, measured by the PCE price index — the Fed's preferred gauge.",
        "origin": "BEA via FRED",
    },
    {
        "key": "fed_funds",
        "label": "Federal funds rate",
        "plain_language": "The interest rate banks charge each other overnight — the Fed's main policy lever.",
        "origin": "Federal Reserve via FRED",
    },
]

# Canvas Macro Dashboard

A self-updating dashboard of U.S. macroeconomic data, built for embedding in
Canvas course pages. Students see current data every time they open the course.

**Live site:** https://bryanpcutsinger.github.io/canvas-macro-dashboard/

| Indicator | FRED series | Shown as |
|---|---|---|
| Unemployment rate | UNRATE | percent of labor force |
| Real GDP growth | A191RL1Q225SBEA | annualized quarterly rate |
| CPI inflation | CPIAUCNS | 12-month change (NSA — matches the headline number) |
| PCE inflation | PCEPI | 12-month change (the Fed's target measure) |
| Federal funds rate | DFF (tile) + FEDFUNDS (trend line) | effective rate |
| Recession dates | USREC | NBER dates (in the data file; not currently displayed) |

The page shows one card per indicator: the current value, the change from the
prior period, and a two-year trend line that reads out past values on hover
(or with the arrow keys).

## How it works

1. A GitHub Actions workflow runs twice each weekday (after the 8:30 a.m. ET
   data releases, and again in the afternoon).
2. `scripts/build_data.py` pulls each series from the FRED API, **asserts that
   the series metadata still matches expectations**, computes the
   transformations, **cross-checks them against FRED's own transformations**,
   and writes `docs/data/dashboard.json` plus a provenance line per series in
   `logs/provenance.jsonl`.
3. The workflow commits the new data and deploys `docs/` to GitHub Pages.
4. The page (`docs/index.html`) is fully static — plain HTML/CSS/JS, no
   frameworks, no build step, no API keys in the browser.

If a series fails to update, its last good data is carried forward and labeled
stale, the site still deploys, and the workflow fails so GitHub emails a
notification. If the data is more than 4 days old for any reason, the page
itself shows a yellow warning banner — students and instructor both see it.

## One-time setup

1. **Create two repository secrets** (Settings → Secrets and variables →
   Actions → New repository secret):
   - `FRED_API_KEY` — your FRED API key.
   - `PAT_PUSH` — a fine-grained personal access token (Settings → Developer
     settings → Fine-grained tokens): repository access = only this repo,
     permissions = Contents: Read and write. Pick the longest expiration
     offered and note the date. Why: GitHub disables cron workflows in public
     repos after 60 days without repository activity, and commits made with a
     real user token unambiguously count as activity.
2. **Enable Pages:** Settings → Pages → Source = **GitHub Actions**.
3. **Turn on failure emails:** github.com → your profile → Settings →
   Notifications → Actions → check "Only notify for failed workflows".
4. **Run it once:** Actions → "Update dashboard data" → Run workflow. Confirm
   the live site renders.
5. **Embed in Canvas:** copy the contents of `canvas-embed.html` into the
   Canvas Rich Content Editor's HTML view (`</>` button). Save, reopen, and
   confirm the iframe survived.

## Maintenance runbook

- **Yellow banner on the page / failure email:** open Actions, look at the
  latest "Update dashboard data" run. Most failures are transient (FRED down);
  click "Re-run all jobs".
- **"Scheduled workflow disabled" email from GitHub:** open Actions, select
  the workflow, click "Enable workflow".
- **PAT expired** (pushes start failing): create a new fine-grained token
  (step 1 above) and update the `PAT_PUSH` secret.
- **A series' metadata changed** (rebasing, renamed series): the run fails
  with a clear message. Update the expected values in
  `scripts/series_config.py` to the new metadata once you have confirmed the
  change is legitimate.

## Local development

```
FRED_API_KEY=... python3 scripts/build_data.py   # rebuild docs/data/dashboard.json
python3 -m unittest discover -s tests            # run the tests
python3 -m http.server -d docs 8000              # preview at localhost:8000
```

Standard library only — nothing to install.

# Canvas Macro Dashboard — Build Plan

**Status:** built and locally verified (2026-08-25); awaiting Bryan's OK to create the GitHub repo and push. This file is the visible trail for multi-session work.
**Decided with Bryan:** 5 indicators (unemployment, real GDP growth, CPI + PCE inflation, fed funds); one shared dashboard for micro + macro; **tiles only** (2026-08-25: Bryan dropped the full charts section as too busy) — each tile's two-year sparkline reads out past values on hover/keyboard. The pipeline still emits full history and recession ranges in dashboard.json, so charts can come back cheaply if wanted. Also 2026-08-25: Bryan dropped the on-page Sources & methods section — the page is a pure header dashboard (cards + one footer line); full provenance stays in README.md, logs/provenance.jsonl, and dashboard.json's source blocks.
**Plan synthesized from a blind dual consult (deep-reasoner + Codex) on 2026-08-25.**

## Architecture

GitHub Actions (cron, weekdays) → `python3 scripts/build_data.py` pulls FRED with
`FRED_API_KEY` (Actions secret) → writes `docs/data/dashboard.json` + provenance log →
commits → deploys `docs/` to GitHub Pages via `upload-pages-artifact`/`deploy-pages` →
Canvas embeds the Pages URL in a fixed-height iframe.

Page is fully static. No client-side keys. No third-party JS (hand-rolled SVG charts).
Python is stdlib-only (no pip installs locally or in CI).

## Series (verified against FRED metadata at every run)

| Indicator | Series | Transform | Display |
|---|---|---|---|
| Unemployment | UNRATE (M, SA) | level | % of labor force |
| Real GDP growth | A191RL1Q225SBEA (Q, SAAR) | none (BEA headline) | % annualized; cross-checked vs pca(GDPC1) within 0.15 pp |
| CPI inflation | CPIAUCNS (M, NSA) | YoY from index | matches BLS headline 12-month figure (which is NSA) |
| PCE inflation | PCEPI (M, SA) | YoY from index | Fed's target measure |
| Fed funds | DFF (D) | level (tile), monthly avg (chart) | effective rate |
| Recessions | USREC (M, 0/1) | contiguous ranges | gray shading |

YoY computed locally from index levels, then cross-checked against FRED `units=pc1`;
mismatch > 0.05 pp fails the series (stale-carry-forward). History starts 1965
(covers Great Inflation + Volcker; PCEPI starts 1959 so OK).

## Failure design (stale-but-labeled beats broken)

- Each series pulled independently; on any failure, carry forward the previous JSON
  block with `status: "stale"` and a warning; always write the file; workflow's last
  step fails the job if `build_status != "ok"` → GitHub failure email.
- Page shows a yellow staleness banner if `generated_at_utc` > 4 days old — the
  guaranteed detector regardless of what breaks upstream.
- Keepalive: GitHub disables cron workflows in public repos after 60 days without
  activity; whether bot commits reset the timer is undocumented. Commits are pushed
  with a fine-grained PAT (Bryan creates it; scope: this repo, Contents read/write)
  so activity is unambiguous. Fallback to GITHUB_TOKEN if the PAT secret is absent.
- Pages source must be set to "GitHub Actions" (not deploy-from-branch).

## Cron

Two UTC runs, weekdays, off the top of the hour (GitHub delays :00 jobs):
`20 14 * * 1-5` (clears 8:30 ET releases in EST and EDT) and `20 21 * * 1-5`
(same-day revisions + that day's DFF). Plus `workflow_dispatch` for manual runs.

## Repo layout

```
.github/workflows/update-data.yml
scripts/series_config.py   # series list: id, expected metadata, transform, copy
scripts/fred_client.py     # stdlib urllib: retries, timeout, key from env
scripts/build_data.py      # fetch → assert metadata → transform → validate → write
tests/test_transforms.py   # stdlib unittest
docs/                      # Pages site: index.html, styles.css, app.js, charts.js,
                           # .nojekyll, data/dashboard.json (generated)
logs/provenance.jsonl      # append-only, one line per series per run, key redacted
canvas-embed.html          # snippet Bryan pastes into the Canvas RCE HTML editor
README.md                  # setup steps (PAT, secret, Pages) + maintenance runbook
```

## Remaining steps

- [x] Build all files
- [x] Run pipeline locally with real FRED pull; verify metadata assertions + pc1 cross-check
- [x] Preview at 375px and desktop; screenshot
- [ ] Bryan: approve git init/commit, `gh repo create` (public — required for free Pages), push
- [ ] Bryan: create fine-grained PAT + add `FRED_API_KEY` and `PAT_PUSH` secrets
- [ ] Set Pages source to GitHub Actions; run workflow once manually
- [ ] Confirm on first run: the `!docs/data/**` push-paths negation works, and
      the `PAT_PUSH || github.token` checkout fallback behaves as expected
- [ ] Paste embed snippet into a Canvas page; check on phone + Canvas mobile app

## Open items surfaced to Bryan

- CPI uses the NSA series (matches the number in the news); switch to CPIAUCSL (SA) on request.
- Possible later additions: core CPI/PCE, fed funds target range overlay, micro-course page.

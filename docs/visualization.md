# Person 5: Interactive NBA half-court and shot chart

This change is confined to Shot Explorer, `charts.py`, the local
`visualization/` component, and visualization checks. The Streamlit framework,
sidebar filters, ETL, data contract, backend helpers, training, saved model,
and other tabs retain their existing responsibilities. No runtime dependency
or external frontend asset is added.

## Coordinates and court

`docs/data-contract.md` and `etl/pipeline.py` specify that original `LOC_X` and
`LOC_Y` are tenths of a foot. Rendering divides each by ten, without translation,
mirroring, clipping to a new location, or geometric reclassification of source
zones. The actual season's left-corner labels have negative X and right-corner
labels have positive X. Distance from `(0, 0)` agrees with the recorded whole-foot
shot distance, within its rounding tolerance. Positive Y points toward midcourt.
Existing `x_ft`/`y_ft` are a fallback if original columns are absent. Any disagreement
with original coordinates is counted and originals take precedence.

Geometry follows the [NBA official court and equipment rules](https://official.nba.com/rule-no-1-court-dimensions-equipment/)
and its linked court diagram. Dimensions in feet relative to the basket center:

| Marking | Geometry |
| --- | --- |
| Half-court boundary | X -25 to 25; Y -5.25 to 41.75 (50 × 47) |
| Paint | X ±8; free-throw line Y 13.75 |
| Free-throw circle | Radius 6; back half dashed |
| Three-point arc | Radius 23.75; corner lines X ±22 meet the same circle |
| Restricted area | Radius 4; short parallel lines extend to the backboard |
| Backboard | X ±3; Y -1.25 (15 inches behind rim center) |
| Basket | Center (0, 0); radius 0.75 |

SVG uses `viewBox="-27 -43.75 54 51"`, `preserveAspectRatio="xMidYMid meet"`,
and one Y-axis inversion. Canvas markers and pointer hit testing use the same
uniform transform. ResizeObserver redraws markers at the actual container width
and device pixel ratio. SVG lines, with a dark halo, sit above markers and cells.
All mapped shots are rendered; opacity adjusts to density instead of sampling.

Invalid coordinates are not plotted. Beyond-half-court and other out-of-bounds
shots keep their original positions and remain in source-zone totals. The
coverage caption separates mapped, out-of-court, and invalid-coordinate counts.
The inspected local dataset has 218,701 attempts, 218,266 mapped attempts,
435 outside the displayed boundary, and no invalid coordinates. Two source
Above the Break 3 shots lie just beyond the exact half-court boundary, in addition
to 433 source Backcourt attempts. Source labels are preserved.

## Aggregation and selection

Pointy-top hexagons have a 2-foot radius and a fixed axial grid anchored at the
basket. Filters never move the grid. Every mapped attempt belongs to exactly
one cell. Cells are visually clipped at the court boundary; their attempts are
not moved. Source-zone selection uses the original NBA label, while cell
selection narrows the inspector to attempts in that cell.

Scatter, attempts heatmap, FG% heatmap, and expected-points heatmap consume the
same sidebar-filtered packet and current source-zone filter. Shot selection is
persistent, with a highlighted location and full details. Hexbin selection has
an outline and persistent statistics. Clear selection resets the shot, cell,
and source-zone choice. New sidebar-filter data clears stale selections using
a hash of every packet row. Source-zone cards retain league FG% comparisons
under the same sidebar quarter and shot type.

FG% is made / attempts × 100. Zero made shots is a real 0%; an empty cell has
no rate and a distinct hatch. Counts use a data-dependent linear scale, FG%
uses a fixed 0–100% scale, and expected points uses a fixed 0–3 points/attempt
scale. The legend is outside the court. Counts below the visible minimum-sample
control are dimmed and hatched, with “sampel belum mencukupi”. Thresholds describe
display confidence and do not remove records. FG% gets a 95% Wilson interval;
model probabilities and expected points do not receive this binomial interval.

## Prediction coverage

There is **no per-shot probability column** in the inspected Parquet. The live
expected-points mode therefore displays an explicit unavailable state. It does
not retrain the model, call an API, infer probability from outcomes, or substitute
observed FG%. The separate Shot Prediction tab continues to work as before.

The adapter accepts these fractional 0–1 columns: `predicted_probability`,
`make_probability`, `shot_probability`, `predicted_make_probability`. Explicit
percentage columns `predicted_probability_pct` and `make_probability_pct` are
divided by 100. Other column names require `probability_column` together with
`probability_scale=1` or `100`. Scale is never guessed from the observed maximum.
Invalid values are excluded and counted; a genuine zero probability is valid.

Per-shot expected points is probability × shot value, restricted to a 2- or
3-point value. A cell's expected points is the mean of these products over
attempts with valid inputs, with coverage reported explicitly. Mean probability
uses its own valid probability count. The expected-points minimum sample uses
the count with both valid probability and shot value. Estimates exclude free
throws, later possessions, defenders, and other unavailable tactical context.

## Interaction and checks

Tooltips use text nodes, bounded placement, and restrained precision. Mouse
hover, touch selection, keyboard focus, and persistent selected-shot details
expose the same data. Tab focuses the scatter surface or occupied-cell grid;
arrow keys browse shots/cells, Enter/Space selects, Escape clears. Empty cells
can be inspected by pointer. The inspector announces selections with a live
region. Narrow layouts stack the inspector below the court.

Run the existing suite plus visualization checks from the repository root:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
node --check visualization/chart.js
node --test visualization/math.test.js
```

For a full-season JavaScript conservation check, export
`prepare_chart_data(pd.read_parquet('data/shots.parquet'))` to JSON under `data/`
and set the `SHOT_PACKET` environment variable to that file before the Node test.
This additionally checks mapped counts and makes for all source-zone filters.

Optional browser verification requires Playwright as a development tool, an
installed Chromium browser, and the running app. It is not an app dependency:

```powershell
$env:PLAYWRIGHT_BROWSERS_PATH = Join-Path (Get-Location) 'data/browser'
.\.venv\Scripts\python.exe visualization/check_browser.py
```

The browser check exercises desktop, tablet, 390px touch, and 320px layouts,
tooltip viewport bounds, selection/reset, sample threshold, sidebar filtering,
keyboard controls, unavailable predictions, and empty/error recovery. To test
available expected points it scores actual Trae Young attempts with the existing
saved model, sends that packet to its isolated browser test session, and checks
the resulting mean. It never changes Parquet or the saved model. Screenshots
are stored in ignored `data/visualization-checks/`.

Verified locally: 36 Python tests passed; 6 JavaScript tests passed including
full-season conservation; browser checks passed for interactions, actual sidebar
filters, responsive geometry, touch, available/unavailable prediction coverage,
and empty/error states. The Python suite reports one existing
`SettingWithCopyWarning` from `etl/pipeline.py`; the visualization does not change
that pipeline.

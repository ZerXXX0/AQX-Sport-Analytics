# ClutchIQ

Smarter shot selection through NBA analytics. Streamlit application using real NBA shot and play-by-play records, zone comparisons, configurable clutch analysis, and an evaluated logistic regression model.

## Reproduce

Python 3.11+ recommended. From this directory:

```powershell
python -m pip install -r requirements.txt
python build.py --source "../nba_data-main/datasets" --season 2023
python -m pytest -q
python -m streamlit run app.py
```

For this workspace, dependencies are also installed in the sibling `python_packages` directory. Set `$env:PYTHONPATH = '../python_packages'` before the commands, or launch using `powershell -ExecutionPolicy Bypass -File run.ps1`.

Download `shotdetail_2023.tar.xz` and `nbastats_2023.tar.xz` from https://github.com/shufinskiy/nba_data/tree/main/datasets. Place both in the source directory. The pipeline reads archive members without extracting arbitrary paths. No NBA API key or environment secrets are required.

## Architecture

- `core.py`: archive ingestion, cleaning, score reconstruction, metrics, chronological splits, model training.
- `build.py`: reproducible processing and artifact creation.
- `charts.py`: interactive half-court chart in feet.
- `app.py`: overview, shot explorer, clutch, comparisons, predictions, methodology.
- `test_clutchiq.py`: explicit statistical fixtures, actual data invariants, inference, chronological partition isolation, Streamlit interaction checks.
- `data/manifest.json`: actual processed coverage and quality counts.
- `artifacts/evaluation.json`: actual validation/test metrics and coefficients.

## Definitions and limitations

One row represents an eligible field-goal attempt. Shot IDs join play-by-play event IDs within a game. Exact duplicate event rows are removed; ambiguous event keys are excluded from score context. Unmatched attempts remain in ordinary shooting analysis and are excluded from clutch comparisons. Pre-event scores come from away-home scores carried forward within chronologically ordered games and shifted one event. Initial score is assumed 0–0. Source score corrections and chronology require caution.

Clutch: period >=4, remaining time <=300 seconds, absolute pre-shot margin <=5. Both thresholds can be adjusted. Overtime uses its own period clock. FG% = makes/attempts. eFG% = (makes + .5*3PM)/attempts. Observed points per attempt includes only made field-goal points. Model expected points = make probability times user-specified shot value. No free throws or subsequent possessions are included.

Shot coordinates are divided by ten to convert into feet, with the basket at the origin. Beyond-half-court shots can lie outside the displayed half court but remain in the metrics. A zone comparison uses the league under the same quarter/type filters. Wilson intervals describe binomial make-rate uncertainty; 30 attempts is only a display threshold.

The first approximately 70% of dates train the model, the next 15% validate it, and the last 15% form the held-out test set. Games and dates do not cross partitions. Training-only imputation and standardization precede logistic regression. The reference model uses training make frequency. No shot-result labels, descriptions, post-shot score, or future statistics are predictors. Coefficients are standardized associations, not causal effects. Coordinates and entered shot value in the simulator are user inputs; physically inconsistent combinations should be avoided.

No defender tracking or shot clock is available in the inspected schemas. Estimates are not tactical guarantees or causal recommendations. Data is historical; the application does not provide live NBA results. One season and regular-season games only are implemented.

## Source and publication

Data compilation: shufinskiy/nba_data, from NBA and other sources described by its maintainer. The upstream repository includes Apache-2.0; this does not independently establish all rights to third-party data. Credit both maintainer and original sources. Raw/processed data and model binaries are ignored by Git; regenerate them using the documented command. Deployment must run the build pipeline before launching the app or provision the generated artifacts separately. Public deployment and Devpost submission remain owner actions.

Team contribution plan is in `docs/team-plan.md`. No commits are attributed to team members automatically.

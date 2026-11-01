# Five-member contribution plan

Each member reviews and implements their own changes. These are planned commit units, not a fabricated contribution history. The initial working implementation is currently uncommitted.

1. Data: load archives; normalize schema; audit duplicate/unmatched events; export Parquet/manifest; test cleaning.
2. Analytics: shooting metrics; pre-shot scores; clutch classification; zone/player comparison; statistical boundary tests.
3. Visualization: court geometry; shot chart/tooltips; zone comparisons; clutch chart; accessibility and empty states.
4. Modeling: chronological split; baseline training; evaluation/calibration; saved inference; model tests/documentation.
5. App/submission: app setup; overview/explorer integration; clutch/model integration; deployment verification; README/screenshots/Devpost materials.

Use branches feat/data-pipeline, feat/analytics, feat/visualizations, feat/shot-model, feat/streamlit-app. Review pull requests before merging. Integrate a runnable version early. Keep data and secrets out of Git.

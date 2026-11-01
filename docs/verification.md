# Verified local build

Processed NBA 2023/24 regular season from local archives: 218,701 eligible attempts, 1,230 games, October 24 2023 through April 14 2024. Three attempts lack score context. Exact duplicate play-by-play rows were removed; no conflicting event keys remained after exact deduplication. Default clutch definition identifies 7,232 attempts.

Chronological partition: 150,817 training shots (845 games); 31,560 validation shots (179 games); 36,324 test shots (206 games). Validation begins February 25 2024 and test begins March 20 2024.

Held-out logistic regression: ROC-AUC 0.640605, Brier 0.234763, log loss 0.661911. Constant reference: ROC-AUC 0.5, Brier 0.249247, log loss 0.691640. Prediction remains limited and imperfectly calibrated; inspect the plotted calibration curve.

Four pytest tests passed, including explicit metric/clutch fixtures, real data invariants, model inference, date partition isolation, and Streamlit interaction checks for team/player filters and the prediction form. HTTP health check returned 200/ok. Overview and Shot Explorer were inspected in the in-app browser at a narrow viewport. Full responsive, accessibility, cross-browser, and production hosting audits have not been completed.

Local URL: http://127.0.0.1:8502 . Not deployed publicly and not submitted to Devpost. No GitHub commits or team member identities have been created.

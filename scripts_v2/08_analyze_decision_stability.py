import os
import sys
from pathlib import Path

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")

PROJECT = Path(__file__).resolve().parents[1]
DEPS = PROJECT / ".python_deps"
if DEPS.exists():
    sys.path.insert(0, str(DEPS))

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from utils_v2 import PROJECT, load_config, require_audit_first, write_json, write_text


OUT_DIR = PROJECT / "data_model/v2/decision_stability"
AUDIT_DIR = PROJECT / "outputs/v2/audit"
TABLE_DIR = PROJECT / "outputs/v2/tables"

MODEL_SCORE = {
    "M_A_physics_score": "M_A_physics_score",
    "M_B_logistic_l2": "M_B_logistic_l2_prob",
    "M_C_logistic_l2_block_year": "M_C_logistic_l2_block_year_prob",
}


def top_set(df, score_col, q=0.9):
    cutoff = df[score_col].quantile(q)
    return set(df.loc[df[score_col] >= cutoff, "segment_id"])


def jaccard(a, b):
    if not a and not b:
        return np.nan
    return len(a & b) / len(a | b)


def main():
    require_audit_first()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    config = load_config()
    label = config["models"]["label"]

    pred = pd.read_parquet(PROJECT / "data_model/v2/fits/model_ladder_predictions.parquet")
    holdout = pred[pred["is_holdout_year"].eq(1)].copy()
    years = sorted(holdout["year"].unique())

    top_rows = []
    set_index = {}
    for year in years:
        sub = holdout[holdout["year"].eq(year)]
        for model, score_col in MODEL_SCORE.items():
            s = top_set(sub, score_col)
            set_index[(model, year)] = s
            top_rows.append(
                {
                    "model": model,
                    "year": int(year),
                    "top_decile_segments": len(s),
                    "positive_exposures_in_top_decile": int(sub[sub["segment_id"].isin(s)][label].sum()),
                    "top_decile_precision": float(sub[sub["segment_id"].isin(s)][label].mean()),
                }
            )
    top_summary = pd.DataFrame(top_rows)
    top_summary.to_csv(TABLE_DIR / "v2_top_decile_summary_by_year.csv", index=False)

    pair_rows = []
    models = list(MODEL_SCORE)
    for year in years:
        sub = holdout[holdout["year"].eq(year)]
        for i, a in enumerate(models):
            for b in models[i + 1 :]:
                pair_rows.append(
                    {
                        "year": int(year),
                        "model_a": a,
                        "model_b": b,
                        "top_decile_jaccard": jaccard(set_index[(a, year)], set_index[(b, year)]),
                        "spearman_rank_correlation": float(spearmanr(sub[MODEL_SCORE[a]], sub[MODEL_SCORE[b]], nan_policy="omit").correlation),
                    }
                )
    pairwise = pd.DataFrame(pair_rows)
    pairwise.to_csv(TABLE_DIR / "v2_pairwise_rank_stability.csv", index=False)

    stable_rows = []
    for model, score_col in MODEL_SCORE.items():
        stable = set.intersection(*(set_index[(model, y)] for y in years))
        mean_scores = holdout[holdout["segment_id"].isin(stable)].groupby("segment_id")[score_col].mean().reset_index(name="mean_holdout_score")
        labels = holdout[holdout["segment_id"].isin(stable)].groupby("segment_id")[label].max().reset_index(name="any_holdout_exposure")
        out = mean_scores.merge(labels, on="segment_id", how="left").sort_values("mean_holdout_score", ascending=False)
        out.insert(0, "model", model)
        stable_rows.append(out)
    stable_priority = pd.concat(stable_rows, ignore_index=True) if stable_rows else pd.DataFrame()
    stable_priority.to_csv(OUT_DIR / "stable_top_decile_segments_2022_2023.csv", index=False)

    summary = {
        "holdout_years": [int(y) for y in years],
        "models": models,
        "posterior_rank_probability_status": "not_available_stan_mcmc_not_completed",
    }
    write_json(AUDIT_DIR / "DECISION_STABILITY_QA.json", summary)
    md = "# Decision Stability QA\n\n"
    md += f"- Holdout years: `{summary['holdout_years']}`\n"
    md += f"- Models: `{models}`\n"
    md += "- Posterior rank probability: not available because Stan MCMC has not completed.\n\n"
    md += "## Top-Decile Summary\n\n"
    md += top_summary.to_markdown(index=False)
    md += "\n\n## Pairwise Rank Stability\n\n"
    md += pairwise.to_markdown(index=False)
    md += "\n"
    write_text(AUDIT_DIR / "DECISION_STABILITY_QA.md", md)
    print(f"[done] {TABLE_DIR / 'v2_pairwise_rank_stability.csv'}")


if __name__ == "__main__":
    main()

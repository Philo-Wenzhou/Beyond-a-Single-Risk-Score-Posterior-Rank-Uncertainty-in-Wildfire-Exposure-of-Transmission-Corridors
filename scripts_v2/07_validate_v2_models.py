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
from sklearn.metrics import average_precision_score, roc_auc_score

from utils_v2 import PROJECT, load_config, require_audit_first, write_json, write_text


OUT_DIR = PROJECT / "data_model/v2/validation"
AUDIT_DIR = PROJECT / "outputs/v2/audit"
TABLE_DIR = PROJECT / "outputs/v2/tables"

MODEL_SCORE = {
    "M_A_physics_score": "M_A_physics_score",
    "M_B_logistic_l2": "M_B_logistic_l2_prob",
    "M_C_logistic_l2_block_year": "M_C_logistic_l2_block_year_prob",
}


def score_metrics(df, label, score_col):
    y = df[label].astype(int).to_numpy()
    s = df[score_col].to_numpy()
    cutoff = np.nanquantile(s, 0.9)
    return {
        "roc_auc": float(roc_auc_score(y, s)) if len(np.unique(y)) == 2 else np.nan,
        "pr_auc": float(average_precision_score(y, s)) if len(np.unique(y)) == 2 else np.nan,
        "top_decile_precision": float(np.mean(y[s >= cutoff])),
    }


def block_bootstrap(df, label, a_col, b_col, n_boot=1000, seed=20260708):
    rng = np.random.default_rng(seed)
    blocks = np.array(sorted(df["block_50km_id"].astype(str).unique()))
    rows = []
    for i in range(n_boot):
        draw = rng.choice(blocks, size=len(blocks), replace=True)
        sample = pd.concat([df[df["block_50km_id"].astype(str).eq(b)] for b in draw], ignore_index=True)
        if sample[label].nunique() < 2:
            continue
        ma = score_metrics(sample, label, a_col)
        mb = score_metrics(sample, label, b_col)
        rows.append(
            {
                "bootstrap_id": i,
                "delta_roc_auc": mb["roc_auc"] - ma["roc_auc"],
                "delta_pr_auc": mb["pr_auc"] - ma["pr_auc"],
                "delta_top_decile_precision": mb["top_decile_precision"] - ma["top_decile_precision"],
            }
        )
    return pd.DataFrame(rows)


def summarize_bootstrap(boot, comparator):
    rows = []
    for metric in ["delta_roc_auc", "delta_pr_auc", "delta_top_decile_precision"]:
        vals = boot[metric].dropna()
        rows.append(
            {
                "comparison": f"{comparator} minus M_A_physics_score",
                "metric": metric,
                "mean": float(vals.mean()),
                "ci025": float(vals.quantile(0.025)),
                "ci975": float(vals.quantile(0.975)),
                "n_boot": int(vals.size),
            }
        )
    return rows


def main():
    require_audit_first()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    config = load_config()
    label = config["models"]["label"]

    pred = pd.read_parquet(PROJECT / "data_model/v2/fits/model_ladder_predictions.parquet")
    holdout = pred[pred["is_holdout_year"].eq(1)].copy()
    metric_rows = []
    for model, score_col in MODEL_SCORE.items():
        for split_name, split_df in [("holdout_2022_2023", holdout)]:
            row = {"model": model, "split": split_name, "n": int(len(split_df)), "prevalence": float(split_df[label].mean())}
            row.update(score_metrics(split_df, label, score_col))
            metric_rows.append(row)
    metrics = pd.DataFrame(metric_rows)
    metrics.to_csv(TABLE_DIR / "v2_holdout_validation_metrics.csv", index=False)

    boot_rows = []
    boot_files = {}
    for comparator, score_col in [
        ("M_B_logistic_l2", MODEL_SCORE["M_B_logistic_l2"]),
        ("M_C_logistic_l2_block_year", MODEL_SCORE["M_C_logistic_l2_block_year"]),
    ]:
        boot = block_bootstrap(holdout, label, MODEL_SCORE["M_A_physics_score"], score_col)
        out_name = f"block_bootstrap_{comparator}_minus_M_A.csv"
        boot.to_csv(OUT_DIR / out_name, index=False)
        boot_files[comparator] = str((OUT_DIR / out_name).relative_to(PROJECT))
        boot_rows.extend(summarize_bootstrap(boot, comparator))
    boot_summary = pd.DataFrame(boot_rows)
    boot_summary.to_csv(TABLE_DIR / "v2_block_bootstrap_metric_differences.csv", index=False)

    summary = {
        "holdout_rows": int(len(holdout)),
        "holdout_prevalence": float(holdout[label].mean()),
        "bootstrap_block": "block_50km_id",
        "bootstrap_files": boot_files,
    }
    write_json(AUDIT_DIR / "V2_VALIDATION_QA.json", summary)
    md = "# V2 Validation QA\n\n"
    md += f"- Holdout rows: {summary['holdout_rows']}\n"
    md += f"- Holdout prevalence: {summary['holdout_prevalence']:.6f}\n"
    md += "- Bootstrap resampling unit: 50 km spatial block.\n\n"
    md += "## Holdout Metrics\n\n"
    md += metrics.to_markdown(index=False)
    md += "\n\n## Paired Block-Bootstrap Differences\n\n"
    md += boot_summary.to_markdown(index=False)
    md += "\n"
    write_text(AUDIT_DIR / "V2_VALIDATION_QA.md", md)
    print(f"[done] {TABLE_DIR / 'v2_holdout_validation_metrics.csv'}")


if __name__ == "__main__":
    main()

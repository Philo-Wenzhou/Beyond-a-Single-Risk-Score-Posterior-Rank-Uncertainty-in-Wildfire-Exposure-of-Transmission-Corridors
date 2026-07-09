import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
DEPS = PROJECT / ".python_deps"
if DEPS.exists():
    sys.path.insert(0, str(DEPS))

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score


PHASE5 = PROJECT / "data/processed/phase5"
PHASE6 = PROJECT / "data/processed/phase6"
TABLE_DIR = PROJECT / "outputs/tables"
DOCS = PROJECT / "docs"
LABEL = "exogenous_fire_exposure"


def top_decile_capture(y, score):
    y = np.asarray(y, dtype=int)
    score = np.asarray(score, dtype=float)
    k = max(1, int(np.ceil(0.10 * len(score))))
    chosen = np.argsort(score)[-k:]
    return float(y[chosen].sum() / y.sum()), float(y[chosen].mean())


def segment_capture(df, score_col):
    seg = (
        df.groupby("segment_id", as_index=False)
        .agg(score=(score_col, "mean"), positives=(LABEL, "sum"))
        .sort_values("score", ascending=False)
    )
    k = max(1, int(np.ceil(0.10 * len(seg))))
    chosen = seg.head(k)
    return float(chosen["positives"].sum() / seg["positives"].sum()), float(chosen["positives"].sum() / k)


def stan_pilot_row():
    path = PHASE6 / "stan_mcmc_pilot/phase6_stan_row_posterior_predictions.parquet"
    row = pd.read_parquet(path)
    y = row[LABEL].to_numpy(dtype=int)
    p = row["posterior_mean"].to_numpy(dtype=float)
    row_capture, row_rate = top_decile_capture(y, p)
    seg_capture, seg_rate = segment_capture(row.rename(columns={"posterior_mean": "score"}), "score")
    return {
        "section": "main_comparison",
        "model_id": "stan_mcmc_pilot",
        "model_label": "Stan MCMC pilot",
        "model_family": "Bayesian MCMC",
        "roc_auc": roc_auc_score(y, p),
        "pr_auc": average_precision_score(y, p),
        "brier": brier_score_loss(y, p),
        "row_top10_capture_rate": row_capture,
        "row_top10_positive_rate": row_rate,
        "segment_top10_capture_rate": seg_capture,
        "segment_top10_positive_rate": seg_rate,
        "notes": "2 chains, 200 warmup, 200 sampling per chain; 400 posterior draws.",
    }


def load_main_comparison():
    metrics = pd.read_csv(PHASE6 / "phase6_model_comparison_metrics.csv")
    family = {
        "bayesian_laplace": "Bayesian Laplace",
        "deterministic_calibrated": "Deterministic score",
        "ml_logistic_l2": "Machine learning",
        "ml_random_forest_balanced": "Machine learning",
        "ml_extra_trees_balanced": "Machine learning",
        "ml_hist_gradient_boosting": "Machine learning",
    }
    labels = {
        "bayesian_laplace": "Bayesian Laplace",
        "deterministic_calibrated": "Deterministic calibrated",
        "ml_logistic_l2": "ML logistic L2",
        "ml_random_forest_balanced": "Balanced random forest",
        "ml_extra_trees_balanced": "Balanced extra trees",
        "ml_hist_gradient_boosting": "Histogram gradient boosting",
    }
    rows = []
    for rec in metrics.to_dict(orient="records"):
        rows.append(
            {
                "section": "main_comparison",
                "model_id": rec["model_id"],
                "model_label": labels.get(rec["model_id"], rec["label"]),
                "model_family": family.get(rec["model_id"], "Other"),
                "roc_auc": rec["roc_auc"],
                "pr_auc": rec["pr_auc"],
                "brier": rec["brier"],
                "row_top10_capture_rate": rec["top10_capture_rate"],
                "row_top10_positive_rate": rec["top10_positive_rate"],
                "segment_top10_capture_rate": rec["segment_top10_capture_rate"],
                "segment_top10_positive_rate": rec["segment_top10_positive_rate"],
                "notes": "Temporal holdout 2022-2023.",
            }
        )
    rows.append(stan_pilot_row())
    order = [
        "deterministic_calibrated",
        "bayesian_laplace",
        "stan_mcmc_pilot",
        "ml_logistic_l2",
        "ml_extra_trees_balanced",
        "ml_hist_gradient_boosting",
        "ml_random_forest_balanced",
    ]
    out = pd.DataFrame(rows)
    out["sort_order"] = out["model_id"].map({m: i for i, m in enumerate(order)})
    return out.sort_values("sort_order").drop(columns=["sort_order"])


def load_ablation():
    metrics = pd.read_csv(PHASE5 / "phase5_ablation_metrics.csv")
    out = metrics.rename(
        columns={
            "label": "model_label",
            "row_top10_capture_rate": "row_top10_capture_rate",
        }
    )
    out["section"] = "ablation"
    out["model_family"] = "Bayesian Laplace ablation"
    out["notes"] = "Feature-set ablation under 2022-2023 temporal holdout."
    keep = [
        "section",
        "model_id",
        "model_label",
        "model_family",
        "roc_auc",
        "pr_auc",
        "brier",
        "row_top10_capture_rate",
        "row_top10_positive_rate",
        "segment_top10_capture_rate",
        "segment_top10_positive_rate",
        "notes",
    ]
    return out[keep]


def fmt(x, digits=3):
    if pd.isna(x):
        return ""
    return f"{x:.{digits}f}"


def markdown_table(df):
    display = df.copy()
    for col in ["roc_auc", "pr_auc", "row_top10_capture_rate", "segment_top10_capture_rate"]:
        display[col] = display[col].map(lambda v: fmt(v, 3))
    display["brier"] = display["brier"].map(lambda v: fmt(v, 6))
    cols = [
        ("model_label", "Model"),
        ("model_family", "Family"),
        ("roc_auc", "ROC-AUC"),
        ("pr_auc", "PR-AUC"),
        ("brier", "Brier"),
        ("row_top10_capture_rate", "Row top-10% capture"),
        ("segment_top10_capture_rate", "Segment top-10% capture"),
    ]
    header = "| " + " | ".join(name for _, name in cols) + " |"
    sep = "| " + " | ".join(["---", "---"] + ["---:"] * (len(cols) - 2)) + " |"
    lines = [header, sep]
    for _, row in display.iterrows():
        lines.append("| " + " | ".join(str(row[col]) for col, _ in cols) + " |")
    return "\n".join(lines)


def main():
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    main_df = load_main_comparison()
    ablation_df = load_ablation()
    all_df = pd.concat([main_df, ablation_df], ignore_index=True)

    all_csv = TABLE_DIR / "manuscript_core_results.csv"
    all_md = TABLE_DIR / "manuscript_core_results.md"
    doc_md = DOCS / "manuscript_results_summary.md"
    all_df.to_csv(all_csv, index=False)

    md = [
        "# Manuscript Core Results",
        "",
        "Temporal holdout is 2022-2023. The target is exogenous wildfire exposure.",
        "",
        "## Main Model Comparison",
        "",
        markdown_table(main_df),
        "",
        "## Feature-Set Ablation",
        "",
        markdown_table(ablation_df),
        "",
        "## Interpretation",
        "",
        "- Bayesian Laplace and Stan MCMC pilot agree closely, supporting the Laplace prototype.",
        "- The calibrated deterministic score is weaker for rare-event PR-AUC and top-decile capture.",
        "- Tree-based ML baselines do not outperform the selected physics-informed linear core under temporal holdout.",
        "- The decision value of Bayesian modeling is posterior exceedance and posterior rank probability, not only point prediction.",
        "",
        "## Caution",
        "",
        "This is external exposure ranking for receptor assets. It is not line-caused ignition prediction, equipment failure prediction, or outage prediction.",
        "",
    ]
    text = "\n".join(md)
    all_md.write_text(text, encoding="utf-8")
    doc_md.write_text(text, encoding="utf-8")
    print(all_csv)
    print(all_md)
    print(doc_md)


if __name__ == "__main__":
    main()

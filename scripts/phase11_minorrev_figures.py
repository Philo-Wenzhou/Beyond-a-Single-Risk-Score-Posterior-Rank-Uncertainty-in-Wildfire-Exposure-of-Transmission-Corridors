import os
import sys
from pathlib import Path

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MPLBACKEND", "Agg")

PROJECT = Path(__file__).resolve().parents[1]
DEPS = PROJECT / ".python_deps"
if DEPS.exists():
    sys.path.insert(0, str(DEPS))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


OUT_DIR = PROJECT / "outputs/figures/sci_minorrev_20260708"
MANIFEST = OUT_DIR / "FIGURE_MANIFEST.csv"

MODEL_ORDER = ["deterministic_calibrated", "bayesian_laplace", "ml_logistic_l2"]
MODEL_LABEL = {
    "deterministic_calibrated": "Deterministic",
    "bayesian_laplace": "Bayesian Laplace",
    "ml_logistic_l2": "Logistic L2",
}
MODEL_COLOR = {
    "deterministic_calibrated": "#8A8A8A",
    "bayesian_laplace": "#4F8A5B",
    "ml_logistic_l2": "#4C78A8",
}


def set_style():
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 7.5,
            "axes.titlesize": 8.5,
            "axes.labelsize": 7.5,
            "xtick.labelsize": 7,
            "ytick.labelsize": 7,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.linewidth": 0.7,
            "figure.dpi": 150,
            "savefig.dpi": 400,
            "legend.frameon": False,
        }
    )


def save(fig, filename):
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / filename
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight", facecolor="white")
    fig.savefig(path.with_suffix(".pdf"), bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return path


def fig_holdout_metrics():
    df = pd.read_parquet(PROJECT / "data/processed/phase6/phase6_model_comparison_metrics.parquet")
    df = df.set_index("model_id").loc[MODEL_ORDER].reset_index()
    panels = [
        ("roc_auc", "ROC-AUC", (0.62, 0.67), "{:.3f}"),
        ("pr_auc", "PR-AUC", (0.02, 0.045), "{:.3f}"),
        ("segment_top10_capture_rate", "Segment top 10% capture", (0.08, 0.24), "{:.3f}"),
    ]
    fig, axes = plt.subplots(1, 3, figsize=(7.4, 2.2), sharey=True)
    y = np.arange(len(df))
    for ax, (col, title, xlim, fmt) in zip(axes, panels):
        colors = [MODEL_COLOR[m] for m in df["model_id"]]
        ax.barh(y, df[col], color=colors, height=0.52)
        for yi, value in zip(y, df[col]):
            ax.text(value, yi, " " + fmt.format(value), va="center", ha="left", fontsize=7)
        ax.set_title(title, pad=5)
        ax.set_xlim(*xlim)
        ax.grid(axis="x", color="#E1E1E1", linewidth=0.55)
        ax.set_xlabel("Holdout value")
        ax.set_yticks(y)
        if ax is axes[0]:
            ax.set_yticklabels([MODEL_LABEL[m] for m in df["model_id"]])
        else:
            ax.tick_params(axis="y", labelleft=False)
        ax.invert_yaxis()
    return fig


def fig_topk_capture():
    df = pd.read_csv(PROJECT / "outputs/tables/phase9_20260707_113214_topk_capture_curve.csv")
    df = df[df["model_id"].isin(MODEL_ORDER)].copy()
    fig, ax = plt.subplots(figsize=(4.9, 3.0))
    for model in MODEL_ORDER:
        sub = df[df["model_id"].eq(model)].sort_values("budget_percent")
        ax.plot(
            sub["budget_percent"],
            sub["capture_rate"],
            marker="o",
            markersize=3.5,
            linewidth=1.5,
            color=MODEL_COLOR[model],
            label=MODEL_LABEL[model],
        )
    ax.set_xlabel("Screening budget (% of holdout segment-years)")
    ax.set_ylabel("Captured exposure positives")
    ax.set_ylim(0, 0.55)
    ax.set_xlim(0, 31)
    ax.grid(color="#E1E1E1", linewidth=0.55)
    ax.legend(loc="lower right", fontsize=7.5)
    ax.set_title("Top-k capture under 2022-2023 temporal holdout", pad=5)
    return fig


def fig_brier_skill():
    df = pd.read_csv(PROJECT / "outputs/tables/phase9_20260707_113214_climatology_brier_skill.csv")
    df = df[df["model_id"].isin(MODEL_ORDER)].set_index("model_id").loc[MODEL_ORDER].reset_index()
    fig, ax = plt.subplots(figsize=(4.2, 2.4))
    y = np.arange(len(df))
    vals = df["brier_skill_vs_training_prevalence"]
    ax.barh(y, vals, color=[MODEL_COLOR[m] for m in df["model_id"]], height=0.52)
    ax.axvline(0, color="#333333", linestyle="--", linewidth=0.8)
    for yi, value in zip(y, vals):
        ax.text(value, yi, f" {value:.3f}", va="center", ha="left", fontsize=7)
    ax.set_yticks(y)
    ax.set_yticklabels([MODEL_LABEL[m] for m in df["model_id"]])
    ax.invert_yaxis()
    ax.set_xlabel("Brier skill vs training-prevalence baseline")
    ax.grid(axis="x", color="#E1E1E1", linewidth=0.55)
    ax.set_title("Rare-event probability baseline audit", pad=5)
    return fig


def fig_bootstrap():
    df = pd.read_csv(PROJECT / "outputs/tables/phase9_20260707_113214_bootstrap_metric_differences.csv")
    rows = []
    for _, row in df.iterrows():
        comparison = row["comparison"]
        short = comparison.replace("Bayesian Laplace minus ", "Bayesian - ")
        rows.extend(
            [
                {
                    "label": short + "\nPR-AUC",
                    "mean": row["delta_pr_auc_mean"],
                    "lo": row["delta_pr_auc_q025"],
                    "hi": row["delta_pr_auc_q975"],
                },
                {
                    "label": short + "\nCapture@10",
                    "mean": row["delta_top10_capture_mean"],
                    "lo": row["delta_top10_capture_q025"],
                    "hi": row["delta_top10_capture_q975"],
                },
            ]
        )
    plot = pd.DataFrame(rows)
    fig, ax = plt.subplots(figsize=(5.2, 2.9))
    y = np.arange(len(plot))
    for yi, row in plot.iterrows():
        xerr = [[row["mean"] - row["lo"]], [row["hi"] - row["mean"]]]
        ax.errorbar(row["mean"], yi, xerr=xerr, fmt="o", color="#4F8A5B", ecolor="#8A8A8A", capsize=2.5, markersize=3.8)
    ax.axvline(0, color="#333333", linestyle="--", linewidth=0.8)
    ax.set_yticks(y)
    ax.set_yticklabels(plot["label"])
    ax.invert_yaxis()
    ax.set_xlabel("Paired bootstrap difference")
    ax.grid(axis="x", color="#E1E1E1", linewidth=0.55)
    ax.set_title("Segment-cluster bootstrap differences", pad=5)
    return fig


def main():
    set_style()
    items = [
        ("minorrev_holdout_metrics", "fig_holdout_metrics.png", fig_holdout_metrics, "data/processed/phase6/phase6_model_comparison_metrics.parquet"),
        ("minorrev_topk_capture", "fig_topk_capture.png", fig_topk_capture, "outputs/tables/phase9_20260707_113214_topk_capture_curve.csv"),
        ("minorrev_brier_skill", "fig_brier_skill.png", fig_brier_skill, "outputs/tables/phase9_20260707_113214_climatology_brier_skill.csv"),
        ("minorrev_bootstrap", "fig_bootstrap.png", fig_bootstrap, "outputs/tables/phase9_20260707_113214_bootstrap_metric_differences.csv"),
    ]
    rows = []
    for fig_id, filename, fn, source in items:
        path = save(fn(), filename)
        rows.append({"figure_id": fig_id, "file": path.relative_to(PROJECT).as_posix(), "source": source})
        print(f"[done] {path}")
    pd.DataFrame(rows).to_csv(MANIFEST, index=False)
    print(f"[done] {MANIFEST}")


if __name__ == "__main__":
    main()

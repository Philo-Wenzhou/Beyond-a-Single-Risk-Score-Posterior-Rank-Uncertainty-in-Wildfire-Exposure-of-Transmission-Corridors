import json
import math
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
DEPS = PROJECT / ".python_deps"
if DEPS.exists():
    sys.path.insert(0, str(DEPS))

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score


TS = "20260707_113214"
LABEL = "exogenous_fire_exposure"
KEEP_MODELS = [
    "deterministic_calibrated",
    "bayesian_laplace",
    "ml_logistic_l2",
]
MODEL_LABELS = {
    "deterministic_calibrated": "Deterministic",
    "bayesian_laplace": "Bayesian Laplace",
    "ml_logistic_l2": "Logistic L2",
}
MODEL_COLORS = {
    "deterministic_calibrated": "#b57a2a",
    "bayesian_laplace": "#236b7a",
    "ml_logistic_l2": "#4d6f45",
}
STYLE = {
    "paper": "#fbfaf6",
    "text": "#24292c",
    "axis": "#596168",
    "grid": "#d8d5cd",
}

PHASE3 = PROJECT / "data/processed/phase3"
PHASE6 = PROJECT / "data/processed/phase6"
OUT_TABLES = PROJECT / "outputs/tables"
OUT_FIGS = PROJECT / "outputs/figures/phase9"
REV_DIR = PROJECT / "docs/revisions" / TS


def ensure_dirs():
    OUT_TABLES.mkdir(parents=True, exist_ok=True)
    OUT_FIGS.mkdir(parents=True, exist_ok=True)
    REV_DIR.mkdir(parents=True, exist_ok=True)


def read_phase3():
    p = PHASE3 / "segment_year_model_table.parquet"
    if p.exists():
        return pd.read_parquet(p)
    return pd.read_csv(PHASE3 / "segment_year_model_table.csv")


def read_predictions():
    p = PHASE6 / "phase6_ml_and_comparator_predictions.parquet"
    if p.exists():
        return pd.read_parquet(p)
    return pd.read_csv(PHASE6 / "phase6_ml_and_comparator_predictions.csv")


def set_style(ax):
    ax.set_facecolor(STYLE["paper"])
    ax.figure.set_facecolor(STYLE["paper"])
    ax.grid(True, axis="y", color=STYLE["grid"], linewidth=0.8, alpha=0.75)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(STYLE["axis"])
    ax.spines["bottom"].set_color(STYLE["axis"])
    ax.tick_params(colors=STYLE["text"], labelsize=9)
    ax.xaxis.label.set_color(STYLE["text"])
    ax.yaxis.label.set_color(STYLE["text"])
    ax.title.set_color(STYLE["text"])


def landfire_audit(df):
    cols = [
        "landfire_fbfm40",
        "landfire_canopy_cover_pct",
        "landfire_canopy_height_m",
        "landfire_canopy_base_height_m",
        "landfire_canopy_bulk_density",
    ]
    rows = []
    for col in cols:
        s = pd.to_numeric(df[col], errors="coerce")
        rows.append(
            {
                "variable": col,
                "n": int(s.notna().sum()),
                "missing": int(s.isna().sum()),
                "unique_values": int(s.nunique(dropna=True)),
                "raw_min": float(s.min()),
                "raw_p50": float(s.quantile(0.50)),
                "raw_p95": float(s.quantile(0.95)),
                "raw_p99": float(s.quantile(0.99)),
                "raw_max": float(s.max()),
            }
        )
    out = pd.DataFrame(rows)
    scale = {
        "landfire_fbfm40": ("categorical", 1.0, "FBFM40 is categorical; do not use as continuous."),
        "landfire_canopy_cover_pct": ("percent", 1.0, "Already percent-like in processed table."),
        "landfire_canopy_height_m": ("decoded_m", 0.1, "LF2024 CH raw values should be divided by 10 for meters."),
        "landfire_canopy_base_height_m": ("decoded_m", 0.1, "LF2024 CBH raw values should be divided by 10 for meters."),
        "landfire_canopy_bulk_density": ("decoded_kg_m3", 0.01, "LF2024 CBD raw values should be divided by 100."),
    }
    out["recommended_scale_type"] = out["variable"].map(lambda x: scale[x][0])
    out["recommended_multiplier"] = out["variable"].map(lambda x: scale[x][1])
    out["decoded_p50"] = out["raw_p50"] * out["recommended_multiplier"]
    out["decoded_p95"] = out["raw_p95"] * out["recommended_multiplier"]
    out["decoded_p99"] = out["raw_p99"] * out["recommended_multiplier"]
    out["decoded_max"] = out["raw_max"] * out["recommended_multiplier"]
    out["audit_note"] = out["variable"].map(lambda x: scale[x][2])
    out.to_csv(OUT_TABLES / f"phase9_{TS}_landfire_unit_audit.csv", index=False)

    plot = out[out["variable"].isin([
        "landfire_canopy_height_m",
        "landfire_canopy_base_height_m",
        "landfire_canopy_bulk_density",
    ])].copy()
    labels = ["Canopy height", "Canopy base height", "Canopy bulk density"]
    x = np.arange(len(plot))
    fig, ax = plt.subplots(figsize=(7.2, 4.2), dpi=220)
    ax.bar(x - 0.18, plot["raw_p95"], width=0.36, color="#9b8f7a", label="Raw p95")
    ax.bar(x + 0.18, plot["decoded_p95"], width=0.36, color="#236b7a", label="Decoded p95")
    set_style(ax)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=0)
    ax.set_ylabel("Value")
    ax.set_title("LANDFIRE unit audit: raw vs decoded p95")
    ax.legend(frameon=False, loc="upper right", fontsize=9)
    fig.tight_layout()
    fig.savefig(OUT_FIGS / f"phase9_{TS}_landfire_scaling_audit.png", bbox_inches="tight")
    fig.savefig(OUT_FIGS / f"phase9_{TS}_landfire_scaling_audit.pdf", bbox_inches="tight")
    plt.close(fig)
    return out


def training_prevalence_baselines():
    df = read_phase3()
    train = df["year"].between(2017, 2021)
    test = df["year"].between(2022, 2023)
    y_train = df.loc[train, LABEL].to_numpy(dtype=float)
    y_test = df.loc[test, LABEL].to_numpy(dtype=float)
    pi_train = float(y_train.mean())
    pi_test = float(y_test.mean())
    return {
        "train_rows": int(train.sum()),
        "train_positive_rows": int(y_train.sum()),
        "test_rows": int(test.sum()),
        "test_positive_rows": int(y_test.sum()),
        "pi_train": pi_train,
        "pi_test": pi_test,
        "training_prevalence_brier": float(np.mean((y_test - pi_train) ** 2)),
        "holdout_prevalence_brier": float(np.mean((y_test - pi_test) ** 2)),
    }


def climatology_and_metrics(pred):
    rows = []
    baselines = training_prevalence_baselines()
    first = pred[pred["model_id"] == KEEP_MODELS[0]]
    y = first[LABEL].to_numpy(dtype=int)
    for model_id, group in pred.groupby("model_id"):
        yy = group[LABEL].to_numpy(dtype=int)
        pp = group["probability"].to_numpy(dtype=float)
        brier = float(brier_score_loss(yy, pp))
        pr = float(average_precision_score(yy, pp))
        rows.append(
            {
                "model_id": model_id,
                "model_label": group["model_label"].iloc[0],
                "test_rows": int(len(group)),
                "test_positive_rows": int(yy.sum()),
                "train_positive_rows": baselines["train_positive_rows"],
                "train_rows": baselines["train_rows"],
                "training_prevalence": baselines["pi_train"],
                "holdout_prevalence": baselines["pi_test"],
                "roc_auc": float(roc_auc_score(yy, pp)),
                "pr_auc": pr,
                "pr_auc_div_holdout_prevalence": float(pr / baselines["pi_test"]),
                "brier": brier,
                "training_prevalence_brier": baselines["training_prevalence_brier"],
                "holdout_prevalence_brier": baselines["holdout_prevalence_brier"],
                "brier_skill_vs_training_prevalence": float(1 - brier / baselines["training_prevalence_brier"]),
                "brier_skill_vs_holdout_prevalence": float(1 - brier / baselines["holdout_prevalence_brier"]),
            }
        )
    out = pd.DataFrame(rows).sort_values("pr_auc", ascending=False)
    out.to_csv(OUT_TABLES / f"phase9_{TS}_climatology_brier_skill.csv", index=False)

    keep = out[out["model_id"].isin(KEEP_MODELS)].copy()
    keep["short"] = keep["model_id"].map(MODEL_LABELS)
    keep = keep.sort_values("brier_skill_vs_training_prevalence")
    fig, ax = plt.subplots(figsize=(7.2, 4.0), dpi=220)
    colors = [MODEL_COLORS[m] for m in keep["model_id"]]
    ax.barh(keep["short"], keep["brier_skill_vs_training_prevalence"], color=colors)
    ax.axvline(0, color="#24292c", linewidth=1)
    set_style(ax)
    ax.set_xlabel("Brier skill score vs training-prevalence constant")
    ax.set_title("Rare-event probability baseline check")
    ax.set_xlim(0, max(keep["brier_skill_vs_training_prevalence"]) * 1.18)
    fig.tight_layout()
    fig.savefig(OUT_FIGS / f"phase9_{TS}_brier_skill_baseline.png", bbox_inches="tight")
    fig.savefig(OUT_FIGS / f"phase9_{TS}_brier_skill_baseline.pdf", bbox_inches="tight")
    plt.close(fig)
    return out


def topk_capture(pred):
    budgets = [0.01, 0.02, 0.05, 0.10, 0.20, 0.30]
    rows = []
    for model_id in KEEP_MODELS:
        group = pred[pred["model_id"] == model_id].copy()
        group = group.sort_values("probability", ascending=False).reset_index(drop=True)
        positives = float(group[LABEL].sum())
        n = len(group)
        for b in budgets:
            k = max(1, int(math.ceil(b * n)))
            chosen = group.head(k)
            capture = float(chosen[LABEL].sum() / positives)
            rows.append(
                {
                    "model_id": model_id,
                    "model_label": MODEL_LABELS[model_id],
                    "budget_fraction": b,
                    "budget_percent": 100 * b,
                    "selected_rows": k,
                    "capture_rate": capture,
                    "selected_positive_rate": float(chosen[LABEL].mean()),
                    "lift_over_random": float(capture / b),
                }
            )
    out = pd.DataFrame(rows)
    out.to_csv(OUT_TABLES / f"phase9_{TS}_topk_capture_curve.csv", index=False)

    fig, ax = plt.subplots(figsize=(7.4, 4.6), dpi=220)
    for model_id in KEEP_MODELS:
        g = out[out["model_id"] == model_id]
        ax.plot(
            g["budget_percent"],
            100 * g["capture_rate"],
            marker="o",
            linewidth=2.2,
            color=MODEL_COLORS[model_id],
            label=MODEL_LABELS[model_id],
        )
    ax.plot([1, 30], [1, 30], linestyle="--", linewidth=1.2, color="#8b8378", label="Random ranking")
    set_style(ax)
    ax.set_xlabel("Inspection / triage budget (% highest-ranked rows)")
    ax.set_ylabel("Captured holdout positives (%)")
    ax.set_title("Top-k capture under 2022-2023 temporal holdout")
    ax.set_xlim(0.5, 30.8)
    ax.set_ylim(0, max(100 * out["capture_rate"].max() * 1.08, 35))
    ax.legend(frameon=False, loc="upper left", fontsize=9)
    fig.tight_layout()
    fig.savefig(OUT_FIGS / f"phase9_{TS}_topk_capture_curve.png", bbox_inches="tight")
    fig.savefig(OUT_FIGS / f"phase9_{TS}_topk_capture_curve.pdf", bbox_inches="tight")
    plt.close(fig)
    return out


def clustered_bootstrap(pred, n_boot=120, seed=20260707):
    rng = np.random.default_rng(seed)
    base = pred[pred["model_id"].isin(KEEP_MODELS)].copy()
    pivot = base.pivot_table(
        index=["segment_id", "year", LABEL],
        columns="model_id",
        values="probability",
        aggfunc="first",
    ).reset_index()
    segment_groups = {sid: g.drop(columns=["segment_id"]).copy() for sid, g in pivot.groupby("segment_id", sort=False)}
    segments = np.array(list(segment_groups.keys()))
    rows = []
    pairs = [
        ("bayesian_laplace", "deterministic_calibrated"),
        ("bayesian_laplace", "ml_logistic_l2"),
    ]
    for b in range(n_boot):
        sample_ids = rng.choice(segments, size=len(segments), replace=True)
        pieces = []
        for sid in sample_ids:
            pieces.append(segment_groups[sid])
        boot = pd.concat(pieces, ignore_index=True)
        y = boot[LABEL].to_numpy(dtype=int)
        if y.sum() == 0 or y.sum() == len(y):
            continue
        k = max(1, int(math.ceil(0.10 * len(y))))
        metrics = {}
        for model_id in KEEP_MODELS:
            p = boot[model_id].to_numpy(dtype=float)
            order = np.argsort(-p)[:k]
            metrics[(model_id, "pr_auc")] = average_precision_score(y, p)
            metrics[(model_id, "top10_capture")] = y[order].sum() / y.sum()
        for a, c in pairs:
            rows.append(
                {
                    "bootstrap": b,
                    "comparison": f"{MODEL_LABELS[a]} minus {MODEL_LABELS[c]}",
                    "delta_pr_auc": metrics[(a, "pr_auc")] - metrics[(c, "pr_auc")],
                    "delta_top10_capture": metrics[(a, "top10_capture")] - metrics[(c, "top10_capture")],
                }
            )
    draws = pd.DataFrame(rows)
    draws.to_csv(OUT_TABLES / f"phase9_{TS}_cluster_bootstrap_draws.csv", index=False)
    summary = (
        draws.groupby("comparison")
        .agg(
            delta_pr_auc_mean=("delta_pr_auc", "mean"),
            delta_pr_auc_q025=("delta_pr_auc", lambda s: s.quantile(0.025)),
            delta_pr_auc_q975=("delta_pr_auc", lambda s: s.quantile(0.975)),
            delta_top10_capture_mean=("delta_top10_capture", "mean"),
            delta_top10_capture_q025=("delta_top10_capture", lambda s: s.quantile(0.025)),
            delta_top10_capture_q975=("delta_top10_capture", lambda s: s.quantile(0.975)),
            n_boot=("bootstrap", "nunique"),
        )
        .reset_index()
    )
    summary.to_csv(OUT_TABLES / f"phase9_{TS}_bootstrap_metric_differences.csv", index=False)

    fig, ax = plt.subplots(figsize=(7.2, 4.0), dpi=220)
    ypos = np.arange(len(summary))
    means = summary["delta_top10_capture_mean"].to_numpy()
    lo = summary["delta_top10_capture_q025"].to_numpy()
    hi = summary["delta_top10_capture_q975"].to_numpy()
    ax.errorbar(
        means,
        ypos,
        xerr=np.vstack([means - lo, hi - means]),
        fmt="o",
        color="#236b7a",
        ecolor="#6d7f86",
        elinewidth=1.6,
        capsize=3,
    )
    ax.axvline(0, color="#24292c", linewidth=1)
    ax.set_yticks(ypos)
    ax.set_yticklabels(summary["comparison"])
    set_style(ax)
    ax.set_xlabel("Delta top-10% capture (cluster bootstrap by segment)")
    ax.set_title("Preliminary paired uncertainty check")
    fig.tight_layout()
    fig.savefig(OUT_FIGS / f"phase9_{TS}_metric_difference_bootstrap.png", bbox_inches="tight")
    fig.savefig(OUT_FIGS / f"phase9_{TS}_metric_difference_bootstrap.pdf", bbox_inches="tight")
    plt.close(fig)
    return summary


def write_revision_docs(landfire, metrics, topk, boot, df):
    holdout = metrics.iloc[0]
    mixed = int(((df[LABEL] == 1) & (df["electrical_power_fire_overlap"] == 1)).sum())
    docs = {
        "00": (
            "INDEX",
            f"""# Revision batch {TS}

This batch completes the requested analysis-plot-TeX pass for the EarthArXiv
minor revision draft.

## Generated evidence

- `outputs/tables/phase9_{TS}_landfire_unit_audit.csv`
- `outputs/tables/phase9_{TS}_climatology_brier_skill.csv`
- `outputs/tables/phase9_{TS}_topk_capture_curve.csv`
- `outputs/tables/phase9_{TS}_bootstrap_metric_differences.csv`
- `outputs/figures/phase9/phase9_{TS}_topk_capture_curve.png`
- `outputs/figures/phase9/phase9_{TS}_brier_skill_baseline.png`
- `outputs/figures/phase9/phase9_{TS}_landfire_scaling_audit.png`
- `outputs/figures/phase9/phase9_{TS}_metric_difference_bootstrap.png`

## Manuscript targets

- Retrospective external wildfire exposure ranking only.
- Posterior top-decile rank probability is primary; posterior exceedance is secondary.
- Brier scores are interpreted relative to the rare-event climatology baseline.
- LANDFIRE unit and categorical-support issues are explicitly flagged.
""",
        ),
        "06": (
            "landfire_unit_audit",
            f"""# LANDFIRE Unit and Support Audit

The processed table currently stores LF2024 canopy height/base-height/bulk-density
as raw raster-coded values rather than decoded physical units.

Key audit decisions:

- Canopy height should be reported after raw / 10.
- Canopy base height should be reported after raw / 10.
- Canopy bulk density should be reported after raw / 100.
- FBFM40 is categorical and should not be treated as a continuous predictor.

The selected Bayesian/L2 feature core does not include FBFM40, but Phase 5
M1/M3/M4 ablation models currently do. Those ablations should be treated as
diagnostic until FBFM40 is encoded categorically or removed.

The selected core uses z-scored CH, CBH, and CBD terms, so constant unit
rescaling would not change the linear standardized fit. It does change physical
interpretation, plotting labels, and any non-linear or threshold interpretation.
""",
        ),
        "07": (
            "label_and_overlap_audit",
            f"""# Label and Overlap Audit

The main label remains external/exogenous exposure:

`y_exo = 1` when a segment buffer intersects a CAL FIRE perimeter whose
perimeter-level cause is not Electrical Power (`CAUSE != 11`).

Electrical-power overlap is retained only as a diagnostic label. It is not an
ignition-probability label, not an outage label, and not a responsibility label.

Observed label counts in the segment-year table:

- all-fire exposure positives: {int(df['all_fire_exposure'].sum())}
- exogenous exposure positives: {int(df[LABEL].sum())}
- strict exogenous positives: {int(df['strict_exogenous_fire_exposure'].sum())}
- electrical-power overlap positives: {int(df['electrical_power_fire_overlap'].sum())}
- rows with both exogenous and electrical-power overlap: {mixed}
""",
        ),
        "08": (
            "climatology_brier_skill",
            f"""# Climatology and Brier Skill Audit

The 2022-2023 holdout contains {int(holdout['test_rows'])} rows and
{int(holdout['test_positive_rows'])} positives, with prevalence
{holdout['holdout_prevalence']:.6f}.

The training-prevalence constant Brier score on the holdout is
`{holdout['training_prevalence_brier']:.6f}`. The holdout-prevalence constant
reference, which is only available in hindsight, is
`{holdout['holdout_prevalence_brier']:.6f}`.

All probability models have Brier scores close to, and slightly worse than, this
rare-event climatology baseline. Therefore the manuscript should not claim
general calibration superiority. PR-AUC should be read relative to the low
prevalence baseline, and Bayesian value should be framed as posterior rank and
threshold decision support.
""",
        ),
        "09": (
            "topk_capture_analysis",
            f"""# Top-k Capture Analysis

The top-k curve compares the fraction of holdout positives captured when only
the highest-ranked 1, 2, 5, 10, 20, or 30 percent of rows are selected.

At the 10 percent budget:

{topk[topk['budget_fraction'].eq(0.10)][['model_label','capture_rate','selected_positive_rate','lift_over_random']].to_markdown(index=False)}

This supports a bounded decision claim: Bayesian Laplace and L2 logistic
concentrate positives similarly and both exceed the deterministic comparator in
this temporal holdout. It does not support a claim that Bayesian point
prediction dominates L2 logistic.
""",
        ),
        "10": (
            "dependence_uncertainty_audit",
            f"""# Dependence and Uncertainty Audit

A preliminary paired bootstrap resampled segment IDs to account for repeated
segment-years. This is not a replacement for spatial block validation.

{boot.to_markdown(index=False)}

Required follow-up validation:

- spatial block validation;
- year/block split sensitivity;
- buffer-radius sensitivity;
- time-matched LANDFIRE sensitivity;
- full Stan diagnostics and posterior predictive checks.
""",
        ),
    }
    for seq, (slug, body) in docs.items():
        (REV_DIR / f"{seq}_{TS}_{slug}.md").write_text(body, encoding="utf-8")

    summary = {
        "timestamp": TS,
        "holdout_prevalence": float(holdout["holdout_prevalence"]),
        "holdout_rows": int(holdout["test_rows"]),
        "holdout_positives": int(holdout["test_positive_rows"]),
        "mixed_exogenous_electrical_rows": mixed,
        "tables": [str(p) for p in sorted(OUT_TABLES.glob(f"phase9_{TS}_*.csv"))],
        "figures": [str(p) for p in sorted(OUT_FIGS.glob(f"phase9_{TS}_*.png"))],
    }
    (OUT_TABLES / f"phase9_{TS}_revision_qa_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )


def main():
    ensure_dirs()
    df = read_phase3()
    pred = read_predictions()
    landfire = landfire_audit(df)
    metrics = climatology_and_metrics(pred)
    topk = topk_capture(pred)
    boot = clustered_bootstrap(pred)
    write_revision_docs(landfire, metrics, topk, boot, df)
    print(json.dumps({
        "timestamp": TS,
        "revision_dir": str(REV_DIR),
        "fig_dir": str(OUT_FIGS),
        "table_dir": str(OUT_TABLES),
    }, indent=2))


if __name__ == "__main__":
    main()

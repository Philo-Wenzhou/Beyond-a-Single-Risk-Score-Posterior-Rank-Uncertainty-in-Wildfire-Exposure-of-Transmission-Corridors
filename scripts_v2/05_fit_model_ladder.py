import os
import sys
from pathlib import Path

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")

PROJECT = Path(__file__).resolve().parents[1]
DEPS = PROJECT / ".python_deps"
if DEPS.exists():
    sys.path.insert(0, str(DEPS))

import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score

from utils_v2 import PROJECT, load_config, require_audit_first, write_json, write_text


OUT_DIR = PROJECT / "data_model/v2/fits"
AUDIT_DIR = PROJECT / "outputs/v2/audit"
TABLE_DIR = PROJECT / "outputs/v2/tables"


def numeric_features(df):
    z_cols = sorted(c for c in df.columns if c.startswith("z_"))
    physics = [
        "v2_phys_dryness_process_index",
        "v2_phys_fuel_structure_index",
        "v2_phys_dryness_x_fuel",
    ]
    return physics + z_cols


def train_medians(df, cols, train_mask):
    rows = []
    med = {}
    for col in cols:
        value = df.loc[train_mask, col].median(skipna=True)
        if not np.isfinite(value):
            value = 0.0
        med[col] = float(value)
        rows.append({"feature": col, "train_median_impute": float(value)})
    return med, pd.DataFrame(rows)


def make_numeric_matrix(df, cols, med):
    return df[cols].fillna(med).to_numpy(dtype="float64")


def make_design(df, numeric_cols, med, categorical_cols=None, train_columns=None):
    x_num = pd.DataFrame(make_numeric_matrix(df, numeric_cols, med), columns=numeric_cols, index=df.index)
    if not categorical_cols:
        return x_num, list(x_num.columns)
    cats = pd.get_dummies(df[categorical_cols].astype("string"), columns=categorical_cols, dummy_na=False)
    if train_columns is not None:
        cats = cats.reindex(columns=train_columns, fill_value=0)
    return pd.concat([x_num, cats], axis=1), list(x_num.columns) + list(cats.columns)


def fit_logistic(x_train, y_train):
    model = LogisticRegression(
        penalty="l2",
        C=1.0,
        solver="lbfgs",
        max_iter=2000,
        class_weight="balanced",
        n_jobs=1,
        random_state=20260708,
    )
    model.fit(x_train, y_train)
    return model


def metric_row(name, split, y, score):
    out = {"model": name, "split": split, "n": int(len(y)), "prevalence": float(np.mean(y))}
    if len(np.unique(y)) < 2:
        out.update({"roc_auc": np.nan, "pr_auc": np.nan, "brier": np.nan, "top_decile_precision": np.nan})
        return out
    cutoff = np.nanquantile(score, 0.9)
    out["roc_auc"] = float(roc_auc_score(y, score))
    out["pr_auc"] = float(average_precision_score(y, score))
    out["brier"] = float(brier_score_loss(y, np.clip(score, 1e-6, 1 - 1e-6)))
    out["top_decile_precision"] = float(np.mean(y[score >= cutoff]))
    return out


def main():
    require_audit_first()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    config = load_config()
    label = config["models"]["label"]

    df = pd.read_parquet(PROJECT / "data_intermediate/v2/model_table/segment_year_v2.parquet")
    train_mask = df["is_train_year"].eq(1)
    holdout_mask = df["is_holdout_year"].eq(1)
    y = df[label].astype(int).to_numpy()

    num_cols = numeric_features(df)
    med, imputer = train_medians(df, num_cols, train_mask)
    imputer.to_csv(TABLE_DIR / "v2_model_ladder_train_median_imputer.csv", index=False)

    physics_cols = [
        "v2_phys_dryness_process_index",
        "v2_phys_fuel_structure_index",
        "v2_phys_dryness_x_fuel",
    ]
    phys = df[physics_cols].fillna({c: med[c] for c in physics_cols})
    ma_raw = phys["v2_phys_dryness_process_index"] + phys["v2_phys_fuel_structure_index"] + phys["v2_phys_dryness_x_fuel"]
    ma_min = ma_raw[train_mask].min()
    ma_max = ma_raw[train_mask].max()
    ma_score = ((ma_raw - ma_min) / (ma_max - ma_min)).clip(0, 1).to_numpy()

    xb, b_cols = make_design(df, num_cols, med)
    mb = fit_logistic(xb.loc[train_mask], y[train_mask])
    mb_prob = mb.predict_proba(xb)[:, 1]

    xc_train, c_cols = make_design(
        df.loc[train_mask],
        num_cols,
        med,
        categorical_cols=["block_50km_id", "year"],
    )
    xc_all, _ = make_design(
        df,
        num_cols,
        med,
        categorical_cols=["block_50km_id", "year"],
        train_columns=[c for c in c_cols if c not in num_cols],
    )
    mc = fit_logistic(xc_train, y[train_mask])
    mc_prob = mc.predict_proba(xc_all)[:, 1]

    pred = df[["segment_id", "year", label, "is_train_year", "is_holdout_year", "block_25km_id", "block_50km_id"]].copy()
    pred["M_A_physics_score"] = ma_score
    pred["M_B_logistic_l2_prob"] = mb_prob
    pred["M_C_logistic_l2_block_year_prob"] = mc_prob
    pred.to_parquet(OUT_DIR / "model_ladder_predictions.parquet", index=False)
    pred.to_csv(OUT_DIR / "model_ladder_predictions.csv", index=False)

    coef_rows = []
    for model_name, model, cols in [("M_B_logistic_l2", mb, b_cols), ("M_C_logistic_l2_block_year", mc, c_cols)]:
        coef_rows.append({"model": model_name, "term": "(intercept)", "coefficient": float(model.intercept_[0])})
        coef_rows.extend({"model": model_name, "term": c, "coefficient": float(v)} for c, v in zip(cols, model.coef_[0]))
    pd.DataFrame(coef_rows).to_csv(TABLE_DIR / "v2_model_ladder_coefficients.csv", index=False)
    joblib.dump({"M_B": mb, "M_C": mc, "numeric_features": num_cols, "imputer": med, "M_C_columns": c_cols}, OUT_DIR / "model_ladder_sklearn.joblib")

    metrics = []
    for model_name, score_col in [
        ("M_A_physics_score", "M_A_physics_score"),
        ("M_B_logistic_l2", "M_B_logistic_l2_prob"),
        ("M_C_logistic_l2_block_year", "M_C_logistic_l2_block_year_prob"),
    ]:
        for split, mask in [("train_2017_2021", train_mask.to_numpy()), ("holdout_2022_2023", holdout_mask.to_numpy())]:
            metrics.append(metric_row(model_name, split, y[mask], pred.loc[mask, score_col].to_numpy()))
    metrics_df = pd.DataFrame(metrics)
    metrics_df.to_csv(TABLE_DIR / "v2_model_ladder_metrics.csv", index=False)

    summary = {
        "models_fit": ["M_A_physics_score", "M_B_logistic_l2", "M_C_logistic_l2_block_year"],
        "train_rows": int(train_mask.sum()),
        "holdout_rows": int(holdout_mask.sum()),
        "holdout_prevalence": float(df.loc[holdout_mask, label].mean()),
        "numeric_feature_count": len(num_cols),
        "m_c_design_columns": len(c_cols),
        "ranking_metrics_file": "outputs/v2/tables/v2_model_ladder_metrics.csv",
    }
    write_json(AUDIT_DIR / "MODEL_LADDER_QA.json", summary)
    md = "# Model Ladder QA\n\n"
    md += f"- Models fit: `{summary['models_fit']}`\n"
    md += f"- Train rows: {summary['train_rows']}\n"
    md += f"- Holdout rows: {summary['holdout_rows']}\n"
    md += f"- Holdout prevalence: {summary['holdout_prevalence']:.6f}\n"
    md += f"- Numeric features: {summary['numeric_feature_count']}\n"
    md += f"- M-C design columns: {summary['m_c_design_columns']}\n\n"
    md += "## Metrics\n\n"
    md += metrics_df.to_markdown(index=False)
    md += "\n"
    write_text(AUDIT_DIR / "MODEL_LADDER_QA.md", md)
    print(f"[done] {OUT_DIR / 'model_ladder_predictions.parquet'}")


if __name__ == "__main__":
    main()

"""
ASCENT Phase 3C — ML Prediction Model (Fixed)

CHANGE FROM PREVIOUS VERSION:
Uses ALL 6 rounds of data (not just Round 1).
This gives ~5,100 training samples instead of 1,092.
Adds round_number as a feature so the model learns
the round-to-round decay pattern alongside other factors.

FEATURES (12 total):
1.  prev_year_r1_score: last year's Round 1 closing score
    (anchor for the year level)
2.  prev_year_same_round: last year's score for this exact round
    (most direct comparison)
3.  avg_3yr_same_round: 3-year average for this round
4.  round_number: 1-6 (encodes which round this is)
5.  round_ratio_expected: historical avg ratio for this round
6.  gate_shift: GATE qualifying cutoff change year-over-year
7.  nirf_rank_sort: NIT quality signal (1-31)
8.  seat_count: seats in this category
9.  category_encoded: UR=0, OBC=1, EWS=2, SC=3, ST=4
10. branch_encoded: CSE=0, AI=1, DS=2 etc.
11. n_years_data: how many years of history available
12. score_level: score normalised (prev_score / 1000)

TARGET: min_score (closing score) for this round

TRAINING: 2021-2025 all rounds (~5100 samples)
TEST:     2026 all rounds (~1868 samples, held-out)
"""

import asyncio
import json
import math
import os
import sys
import pickle
import warnings
from collections import defaultdict

warnings.filterwarnings("ignore")

sys.path.insert(0,
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)

import numpy as np
from sklearn.linear_model import Ridge
from sklearn.ensemble import (
    RandomForestRegressor,
    GradientBoostingRegressor
)
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error
)
from motor.motor_asyncio import AsyncIOMotorClient

MONGODB_URL   = "mongodb://localhost:27017"
DATABASE_NAME = "ascent_db"

TRAIN_YEARS  = [2021, 2022, 2023, 2024, 2025]
TEST_YEAR    = 2026

PROCESSED_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "processed"
)
MODEL_FILE   = os.path.join(PROCESSED_DIR, "phase3_model.pkl")
RESULTS_FILE = os.path.join(PROCESSED_DIR,
                             "phase3_model_results.json")

BASELINE_MAE_R1 = 39.8  # from Phase 3B/3C previous run

ROUND_ORDER = {
    "Round 1":             1,
    "Round 2":             2,
    "Round 3":             3,
    "Special Round 1":     4,
    "Special Round 2":     5,
    "National Spot Round": 6,
}

CATEGORY_ENC = {
    "UR": 0, "OBC": 1, "EWS": 2, "SC": 3, "ST": 4
}
BRANCH_ENC = {
    "CSE": 0, "AI": 1, "DS": 2, "IS": 3,
    "IT":  4, "CY": 5, "SE": 6, "MC": 7
}

FEATURE_NAMES = [
    "prev_year_r1_score",
    "prev_year_same_round",
    "avg_3yr_same_round",
    "round_number",
    "round_ratio_expected",
    "gate_shift",
    "nirf_rank_sort",
    "seat_count",
    "category_enc",
    "branch_enc",
    "n_years_data",
    "score_level",
]


# ── Load data ─────────────────────────────────────────────

async def load_data(db):
    """Load all records, NIT metadata, GATE difficulty."""

    # All cutoff records across all rounds
    all_records = await db["ccmt_cutoffs"].find(
        {}, {"_id": 0,
             "year": 1, "round": 1,
             "institute_code": 1, "branch_code": 1,
             "category": 1, "min_score": 1}
    ).to_list(50000)

    # NIT metadata
    nits = await db["nits"].find(
        {}, {"_id": 0,
             "nit_code": 1, "nirf_rank_sort": 1,
             "mtech_programs": 1}
    ).to_list(100)

    # GATE difficulty
    gate_docs = await db["gate_difficulty"].find(
        {}, {"_id": 0}
    ).to_list(100)

    # Seat matrix
    seat_docs = await db["seat_matrix"].find(
        {}, {"_id": 0}
    ).to_list(5000)

    # Build nested lookup:
    # scores[year][round][nit][branch][cat] = min_score
    scores = defaultdict(
        lambda: defaultdict(
            lambda: defaultdict(
                lambda: defaultdict(dict)
            )
        )
    )
    for r in all_records:
        y   = r["year"]
        rnd = r["round"]
        nit = r["institute_code"]
        br  = r["branch_code"]
        cat = r["category"]
        s   = r["min_score"]
        if s and s > 0:
            existing = scores[y][rnd][nit][br].get(cat)
            if existing is None or s < existing:
                scores[y][rnd][nit][br][cat] = s

    # NIRF rank sort
    nirf = {n["nit_code"]: n.get("nirf_rank_sort", 20)
            for n in nits}

    # GATE qualifying cutoff by year
    gate = {}
    for g in gate_docs:
        yr = g.get("year")
        if yr:
            gate[yr] = g.get("qualifying_cutoff_general", 29.0)

    # Seats
    seats = defaultdict(lambda: defaultdict(dict))
    for s in seat_docs:
        nit = s.get("nit_code", "")
        br  = s.get("branch_code", "")
        for cat in ["UR", "OBC", "SC", "ST", "EWS"]:
            val = s.get(f"seats_{cat}", 0) or 0
            if val > 0:
                seats[nit][br][cat] = val

    # Count records by year
    print(f"Records loaded by year:")
    for y in TRAIN_YEARS + [TEST_YEAR]:
        total = sum(
            len(cats)
            for rnd in scores[y].values()
            for nit in rnd.values()
            for cats in nit.values()
        )
        tag = " (TEST)" if y == TEST_YEAR else " (TRAIN)"
        print(f"  {y}{tag}: {total} records")

    # Compute historical round ratios from training data
    # ratio[round] = avg(round_score / R1_score) across all
    # training years for matching combinations
    ratio_data = defaultdict(list)
    for y in TRAIN_YEARS:
        r1_data = scores[y].get("Round 1", {})
        for rnd_name, rnd_num in ROUND_ORDER.items():
            if rnd_num == 1:
                continue
            rnd_data = scores[y].get(rnd_name, {})
            for nit in rnd_data:
                for br in rnd_data[nit]:
                    for cat, rnd_score in \
                            rnd_data[nit][br].items():
                        r1_score = r1_data.get(nit, {}) \
                                        .get(br, {}) \
                                        .get(cat)
                        if r1_score and r1_score > 0:
                            ratio_data[rnd_name].append(
                                rnd_score / r1_score
                            )

    avg_ratios = {}
    print(f"\nLearned round ratios from 2021-2025:")
    for rnd_name, ratios in ratio_data.items():
        if ratios:
            avg_ratios[rnd_name] = sum(ratios) / len(ratios)
            print(f"  {rnd_name:<25}: "
                  f"{avg_ratios[rnd_name]:.4f}")
    avg_ratios["Round 1"] = 1.0

    return scores, nirf, gate, seats, avg_ratios


# ── Feature engineering ───────────────────────────────────

def build_feature_vector(nit, branch, cat, rnd_name,
                          predict_year, scores, nirf,
                          gate, seats, avg_ratios) -> dict:
    """
    Build one feature vector for a single
    (nit, branch, category, round, year) combination.
    Returns None if insufficient history.
    """
    rnd_num = ROUND_ORDER.get(rnd_name, 1)

    # Collect history for this combination + this round
    same_round_history = {}
    for y in TRAIN_YEARS:
        s = scores[y].get(rnd_name, {}) \
                     .get(nit, {}) \
                     .get(branch, {}) \
                     .get(cat)
        if s and s > 0:
            same_round_history[y] = s

    # Need at least 1 year of same-round history
    if len(same_round_history) < 1:
        return None

    # Feature 1: Previous year Round 1 score
    # (year anchor — most important signal)
    prev_r1 = scores.get(predict_year - 1, {}) \
                    .get("Round 1", {}) \
                    .get(nit, {}) \
                    .get(branch, {}) \
                    .get(cat)
    if prev_r1 is None:
        # Try 2 years back
        prev_r1 = scores.get(predict_year - 2, {}) \
                        .get("Round 1", {}) \
                        .get(nit, {}) \
                        .get(branch, {}) \
                        .get(cat)
    if prev_r1 is None:
        return None

    # Feature 2: Previous year same round score
    prev_same = same_round_history.get(predict_year - 1)
    if prev_same is None:
        # Use most recent available
        sorted_yrs = sorted(same_round_history.keys())
        prev_same  = same_round_history[sorted_yrs[-1]]

    # Feature 3: 3-year average for same round
    recent_scores = [
        same_round_history[y]
        for y in sorted(same_round_history.keys())[-3:]
    ]
    avg_3yr = sum(recent_scores) / len(recent_scores)

    # Feature 4: Round number (1-6)
    rnd_num_feat = rnd_num

    # Feature 5: Expected round ratio
    ratio = avg_ratios.get(rnd_name, 1.0)

    # Feature 6: GATE qualifying cutoff shift
    gate_prev    = gate.get(predict_year - 1, 29.0)
    gate_current = gate.get(predict_year, 29.0)
    gate_shift   = gate_current - gate_prev

    # Feature 7: NIRF rank sort
    nirf_rank = nirf.get(nit, 20)

    # Feature 8: Seat count
    seat_count = seats[nit][branch].get(cat, 5)
    seat_count = max(seat_count, 1)

    # Feature 9: Category encoded
    cat_enc = CATEGORY_ENC.get(cat, 0)

    # Feature 10: Branch encoded
    br_enc = BRANCH_ENC.get(branch, 0)

    # Feature 11: Years of data
    n_years = len(same_round_history)

    # Feature 12: Score level (normalised)
    score_level = prev_r1 / 1000.0

    return {
        "prev_year_r1_score":    prev_r1,
        "prev_year_same_round":  prev_same,
        "avg_3yr_same_round":    avg_3yr,
        "round_number":          rnd_num_feat,
        "round_ratio_expected":  ratio,
        "gate_shift":            gate_shift,
        "nirf_rank_sort":        nirf_rank,
        "seat_count":            seat_count,
        "category_enc":          cat_enc,
        "branch_enc":            br_enc,
        "n_years_data":          n_years,
        "score_level":           score_level,
    }


def feat_to_array(feat: dict) -> np.ndarray:
    return np.array(
        [feat[k] for k in FEATURE_NAMES], dtype=float
    )


# ── Build datasets ────────────────────────────────────────

def build_dataset(predict_years, scores, nirf,
                  gate, seats, avg_ratios,
                  label=""):
    """Build X, y arrays for given years."""
    X_rows = []
    y_vals = []
    meta   = []

    for predict_year in predict_years:
        for rnd_name in ROUND_ORDER:
            rnd_data = scores[predict_year].get(rnd_name, {})
            for nit in rnd_data:
                for branch in rnd_data[nit]:
                    for cat, actual_score in \
                            rnd_data[nit][branch].items():
                        feat = build_feature_vector(
                            nit, branch, cat, rnd_name,
                            predict_year, scores, nirf,
                            gate, seats, avg_ratios
                        )
                        if feat is None:
                            continue
                        X_rows.append(feat_to_array(feat))
                        y_vals.append(actual_score)
                        meta.append((predict_year, rnd_name,
                                     nit, branch, cat))

    X = np.array(X_rows)
    y = np.array(y_vals)
    print(f"{label}: {len(X)} samples")
    return X, y, meta


# ── Cross-validation ──────────────────────────────────────

def cross_validate(X, y, meta):
    """Leave-one-year-out CV on training years."""
    print(f"\n{'='*55}")
    print("Cross-validation on training years 2022-2025")
    print("(Leave-one-year-out)")
    print(f"{'='*55}")

    years      = [m[0] for m in meta]
    cv_years   = [2022, 2023, 2024, 2025]
    cv_results = {}

    for test_yr in cv_years:
        tr_idx = [i for i, y_ in enumerate(years)
                  if y_ != test_yr]
        te_idx = [i for i, y_ in enumerate(years)
                  if y_ == test_yr]
        if not te_idx:
            continue

        X_tr = X[tr_idx]; y_tr = y[tr_idx]
        X_te = X[te_idx]; y_te = y[te_idx]

        sc       = StandardScaler()
        X_tr_sc  = sc.fit_transform(X_tr)
        X_te_sc  = sc.transform(X_te)

        ridge = Ridge(alpha=10.0)
        ridge.fit(X_tr_sc, y_tr)
        preds = ridge.predict(X_te_sc)

        mae  = mean_absolute_error(y_te, preds)
        bl   = mean_absolute_error(
            y_te, X_te[:, 0]  # prev_year_r1 as baseline
        )
        tag  = "✅ BETTER" if mae < bl else "⚠️  WORSE"

        cv_results[test_yr] = {
            "ridge_mae": round(mae, 1),
            "baseline_mae": round(bl, 1),
            "n": len(te_idx)
        }
        print(f"  {test_yr}: Ridge={mae:.1f} | "
              f"Baseline={bl:.1f} | N={len(te_idx)} | {tag}")

    avg_r = sum(v["ridge_mae"]
                for v in cv_results.values()) / len(cv_results)
    avg_b = sum(v["baseline_mae"]
                for v in cv_results.values()) / len(cv_results)
    print(f"\n  Avg Ridge MAE    : {avg_r:.1f}")
    print(f"  Avg Baseline MAE : {avg_b:.1f}")
    return cv_results


# ── Train ─────────────────────────────────────────────────

def train_models(X_train, y_train):
    print(f"\n{'='*55}")
    print("Training models on 2021-2025 (all rounds)")
    print(f"{'='*55}")

    scaler  = StandardScaler()
    X_sc    = scaler.fit_transform(X_train)
    models  = {}

    # Ridge Regression
    ridge = Ridge(alpha=10.0)
    ridge.fit(X_sc, y_train)
    models["Ridge Regression"] = (ridge, scaler)
    coefs = sorted(
        zip(FEATURE_NAMES, ridge.coef_),
        key=lambda x: abs(x[1]), reverse=True
    )
    print(f"  ✅ Ridge — top features: "
          f"{[(n, round(c,1)) for n,c in coefs[:3]]}")

    # Random Forest
    rf = RandomForestRegressor(
        n_estimators=300,
        max_depth=8,
        min_samples_leaf=3,
        random_state=42,
        n_jobs=-1
    )
    rf.fit(X_train, y_train)
    models["Random Forest"] = (rf, None)
    fi = sorted(
        zip(FEATURE_NAMES, rf.feature_importances_),
        key=lambda x: x[1], reverse=True
    )
    print(f"  ✅ Random Forest — top features: "
          f"{[(n, round(c,3)) for n,c in fi[:3]]}")

    # Gradient Boosting
    gb = GradientBoostingRegressor(
        n_estimators=300,
        max_depth=4,
        learning_rate=0.05,
        min_samples_leaf=3,
        random_state=42
    )
    gb.fit(X_train, y_train)
    models["Gradient Boosting"] = (gb, None)
    print(f"  ✅ Gradient Boosting trained")

    return models


# ── Evaluate ──────────────────────────────────────────────

def evaluate(models, X_test, y_test, meta_test):
    print(f"\n{'='*55}")
    print("FINAL EVALUATION ON 2026 TEST SET")
    print("(All rounds, held-out)")
    print(f"{'='*55}")

    results  = {}
    bl_preds = X_test[:, 0]  # prev_year_r1_score
    bl_mae   = mean_absolute_error(y_test, bl_preds)
    bl_rmse  = math.sqrt(mean_squared_error(y_test, bl_preds))
    results["Baseline (prev R1)"] = {
        "mae": round(bl_mae, 2),
        "rmse": round(bl_rmse, 2),
        "n": len(y_test)
    }
    print(f"\n  {'Baseline (prev R1)':<25} "
          f"MAE={bl_mae:>6.1f}  RMSE={bl_rmse:>6.1f}")

    best_mae   = bl_mae
    best_name  = "Baseline (prev R1)"
    all_preds  = []

    for name, (model, scaler) in models.items():
        if scaler:
            preds = model.predict(scaler.transform(X_test))
        else:
            preds = model.predict(X_test)
        all_preds.append(preds)

        mae  = mean_absolute_error(y_test, preds)
        rmse = math.sqrt(mean_squared_error(y_test, preds))
        diff = bl_mae - mae
        tag  = (f"✅ +{diff:.1f} better"
                if diff > 0 else f"⚠️  {-diff:.1f} worse")

        results[name] = {
            "mae": round(mae, 2),
            "rmse": round(rmse, 2),
            "vs_baseline": round(diff, 2)
        }
        print(f"  {name:<25} "
              f"MAE={mae:>6.1f}  RMSE={rmse:>6.1f}  {tag}")

        if mae < best_mae:
            best_mae  = mae
            best_name = name

    # Ensemble
    ens_preds = np.mean(all_preds, axis=0)
    ens_mae   = mean_absolute_error(y_test, ens_preds)
    ens_rmse  = math.sqrt(mean_squared_error(y_test, ens_preds))
    ens_diff  = bl_mae - ens_mae
    ens_tag   = (f"✅ +{ens_diff:.1f} better"
                 if ens_diff > 0 else f"⚠️  {-ens_diff:.1f} worse")
    results["Ensemble"] = {
        "mae": round(ens_mae, 2),
        "rmse": round(ens_rmse, 2),
        "vs_baseline": round(ens_diff, 2)
    }
    print(f"  {'Ensemble (3 models)':<25} "
          f"MAE={ens_mae:>6.1f}  RMSE={ens_rmse:>6.1f}  {ens_tag}")

    if ens_mae < best_mae:
        best_mae  = ens_mae
        best_name = "Ensemble"

    # Per-round breakdown
    print(f"\n  Per-round MAE breakdown:")
    rounds = [m[1] for m in meta_test]
    for rnd_name in ROUND_ORDER:
        idx = [i for i, r in enumerate(rounds)
               if r == rnd_name]
        if not idx:
            continue
        y_rnd  = y_test[idx]
        bl_rnd = bl_preds[idx]
        en_rnd = ens_preds[idx]
        bl_m   = mean_absolute_error(y_rnd, bl_rnd)
        en_m   = mean_absolute_error(y_rnd, en_rnd)
        tag    = "✅" if en_m < bl_m else "⚠️ "
        print(f"    {rnd_name:<25} "
              f"Baseline={bl_m:.1f}  Ensemble={en_m:.1f}  {tag}")

    return results, best_name, best_mae


# ── Main ──────────────────────────────────────────────────

async def run():
    print("=" * 60)
    print("ASCENT Phase 3C — ML Model (Fixed: All Rounds)")
    print(f"Training: {TRAIN_YEARS} (all 6 rounds)")
    print(f"Test:     {TEST_YEAR} (held-out)")
    print("=" * 60)

    client = AsyncIOMotorClient(MONGODB_URL)
    db     = client[DATABASE_NAME]

    scores, nirf, gate, seats, avg_ratios = \
        await load_data(db)
    client.close()

    print(f"\nBuilding datasets (all rounds)...")

    # Training: years 2022-2025 (leave 2021 as anchor)
    X_train, y_train, meta_train = build_dataset(
        [2022, 2023, 2024, 2025],
        scores, nirf, gate, seats, avg_ratios,
        "Training set"
    )

    # Test: 2026
    X_test, y_test, meta_test = build_dataset(
        [TEST_YEAR],
        scores, nirf, gate, seats, avg_ratios,
        "Test set (2026)"
    )

    if len(X_train) == 0 or len(X_test) == 0:
        print("❌ Empty dataset. Check data loading.")
        return

    print(f"\nTotal training samples: {len(X_train)}")
    print(f"Total test samples:     {len(X_test)}")
    print(f"Features per sample:    {X_train.shape[1]}")

    # Cross-validate
    cv_results = cross_validate(X_train, y_train, meta_train)

    # Train
    models = train_models(X_train, y_train)

    # Evaluate on 2026
    results, best_name, best_mae = evaluate(
        models, X_test, y_test, meta_test
    )

    # Save
    os.makedirs(PROCESSED_DIR, exist_ok=True)

    with open(MODEL_FILE, "wb") as f:
        pickle.dump({
            "models":        models,
            "best_model":    best_name,
            "feature_names": FEATURE_NAMES,
            "avg_ratios":    avg_ratios,
            "train_years":   TRAIN_YEARS,
            "test_year":     TEST_YEAR,
        }, f)

    with open(RESULTS_FILE, "w") as f:
        json.dump({
            "results": results,
            "cv":      {str(k): v
                        for k, v in cv_results.items()},
            "best_model":        best_name,
            "best_mae":          round(best_mae, 2),
            "baseline_mae_r1":   BASELINE_MAE_R1,
            "feature_names":     FEATURE_NAMES,
        }, f, indent=2)

    print(f"\n{'='*60}")
    print("PHASE 3C COMPLETE")
    print(f"{'='*60}")
    print(f"Best model: {best_name}")
    print(f"Best MAE (all rounds): {best_mae:.1f}")
    print(f"Baseline R1 MAE (Phase 3B): {BASELINE_MAE_R1}")

    if best_mae < BASELINE_MAE_R1:
        print(f"\n✅ Beats Phase 3B R1 baseline by "
              f"{BASELINE_MAE_R1 - best_mae:.1f} points")
    else:
        print(f"\nNote: This MAE covers all 6 rounds.")
        print(f"R1-only baseline was {BASELINE_MAE_R1}.")
        print(f"Cross-round MAE is expected to be higher")
        print(f"because later rounds have lower, noisier scores.")

    print(f"\nModel saved: {MODEL_FILE}")
    print(f"Results saved: {RESULTS_FILE}")
    print(f"{'='*60}")


if __name__ == "__main__":
    asyncio.run(run())
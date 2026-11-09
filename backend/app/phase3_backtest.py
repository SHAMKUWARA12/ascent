"""
ASCENT Phase 3B — Backtest Script

PURPOSE:
Tests 4 prediction methods on 2026 held-out data
to establish baseline error rates before building
the final ML model.

RESEARCH QUESTION BEING ANSWERED:
"Does a multi-criteria approach using GATE difficulty
data outperform simple single-criterion cutoff
comparison for CCMT admission prediction?"

DATA SPLIT:
Training years: 2021, 2022, 2023, 2024, 2025
Test year:      2026 (held-out, never used in training)

METHODS COMPARED:
1. Last year baseline (what all existing tools use)
2. Rolling 3-year average
3. Trend-adjusted prediction
4. GATE-difficulty adjusted prediction (novel)

ROUND-RATIO TEST:
Separately tests how accurately we can predict
R2-R6 once R1 of the same year is known.
This is the in-counselling prediction scenario.

OUTPUT:
Printed tables + JSON results saved to:
backend/data/processed/phase3_backtest_results.json
"""

import asyncio
import json
import math
import os
import sys
from collections import defaultdict

sys.path.insert(0,
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)

from motor.motor_asyncio import AsyncIOMotorClient

MONGODB_URL   = "mongodb://localhost:27017"
DATABASE_NAME = "ascent_db"

RESULTS_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "processed", "phase3_backtest_results.json"
)

TRAIN_YEARS = [2021, 2022, 2023, 2024, 2025]
TEST_YEAR   = 2026
TARGET_ROUND = "Round 1"

# Minimum years of training data required
# to make a prediction for a combination
MIN_YEARS_REQUIRED = 2


# ── Data loading ──────────────────────────────────────────

async def load_cutoff_data(db) -> dict:
    """
    Load all ccmt_cutoffs records into a nested dict:
    data[year][nit_code][branch_code][category] = min_score
    Only uses Round 1 scores (the primary closing score).
    """
    records = await db["ccmt_cutoffs"].find(
        {"round": TARGET_ROUND},
        {"_id": 0, "year": 1, "institute_code": 1,
         "branch_code": 1, "category": 1, "min_score": 1}
    ).to_list(length=50000)

    data = defaultdict(
        lambda: defaultdict(
            lambda: defaultdict(dict)
        )
    )

    for r in records:
        y    = r["year"]
        nit  = r["institute_code"]
        br   = r["branch_code"]
        cat  = r["category"]
        score = r["min_score"]

        if score and score > 0:
            # If multiple records per combination
            # (e.g. multiple groups), take the minimum
            existing = data[y][nit][br].get(cat)
            if existing is None or score < existing:
                data[y][nit][br][cat] = score

    print(f"Loaded cutoff data:")
    for y in TRAIN_YEARS + [TEST_YEAR]:
        count = sum(
            len(cats)
            for nit in data[y].values()
            for cats in nit.values()
        )
        tag = " (TEST)" if y == TEST_YEAR else " (TRAIN)"
        print(f"  {y}{tag}: {count} NIT+branch+category combinations")

    return data


async def load_gate_difficulty(db) -> dict:
    """
    Load GATE difficulty data into:
    gate[year][paper] = {
        qualifying_cutoff_general,
        difficulty_score
    }
    """
    records = await db["gate_difficulty"].find(
        {}, {"_id": 0}
    ).to_list(100)

    gate = {}
    for r in records:
        year  = r.get("year")
        paper = r.get("gate_paper", "CS")
        if year:
            gate[year] = {
                "qualifying_cutoff_general":
                    r.get("qualifying_cutoff_general", 29.0),
                "difficulty_score":
                    r.get("difficulty_score", 3.0),
            }

    print(f"\nGATE difficulty data loaded for years: "
          f"{sorted(gate.keys())}")
    return gate


# ── Prediction methods ────────────────────────────────────

def predict_last_year(nit, branch, cat, data, test_year) -> float:
    """Method 1: Use previous year's R1 closing score."""
    prev_year = test_year - 1
    return data[prev_year][nit][branch].get(cat)


def predict_rolling_average(nit, branch, cat, data,
                             test_year, n=3) -> float:
    """Method 2: Rolling n-year average."""
    scores = []
    for y in range(test_year - n, test_year):
        s = data[y][nit][branch].get(cat)
        if s:
            scores.append(s)
    if len(scores) < 1:
        return None
    return sum(scores) / len(scores)


def predict_trend_adjusted(nit, branch, cat, data,
                            test_year) -> float:
    """
    Method 3: Last year + average year-over-year change.
    Captures if scores are consistently rising/falling.
    """
    scores_by_year = {}
    for y in TRAIN_YEARS:
        s = data[y][nit][branch].get(cat)
        if s:
            scores_by_year[y] = s

    if len(scores_by_year) < MIN_YEARS_REQUIRED:
        return None

    sorted_years = sorted(scores_by_year.keys())

    # Compute year-over-year changes
    yoy_changes = []
    for i in range(1, len(sorted_years)):
        y_prev = sorted_years[i-1]
        y_curr = sorted_years[i]
        change = scores_by_year[y_curr] - scores_by_year[y_prev]
        yoy_changes.append(change)

    if not yoy_changes:
        return None

    # Use only last 3 changes for recent trend
    recent_changes = yoy_changes[-3:]
    avg_change     = sum(recent_changes) / len(recent_changes)

    last_year  = sorted_years[-1]
    last_score = scores_by_year[last_year]

    return last_score + avg_change


def predict_gate_adjusted(nit, branch, cat, data,
                           test_year, gate) -> float:
    """
    Method 4: Trend-adjusted prediction further modified
    by GATE difficulty shift between test year and
    previous year.

    Key insight:
    When GATE qualifying cutoff INCREASES (harder paper,
    fewer high-scorers), CCMT closing scores tend to
    DECREASE slightly.
    When qualifying cutoff DECREASES (easier paper,
    more high-scorers), CCMT closing scores tend to
    INCREASE slightly.

    This is ASCENT's original contribution — using
    official GATE qualifying cutoff data to improve
    CCMT cutoff prediction.
    """
    base_prediction = predict_trend_adjusted(
        nit, branch, cat, data, test_year
    )
    if base_prediction is None:
        return None

    # Get GATE qualifying cutoffs
    gate_test  = gate.get(test_year, {})
    gate_prev  = gate.get(test_year - 1, {})

    cutoff_test = gate_test.get("qualifying_cutoff_general", 29.0)
    cutoff_prev = gate_prev.get("qualifying_cutoff_general", 29.0)

    # Compute difficulty shift
    # Positive = test year was harder (fewer high-scorers)
    difficulty_shift = cutoff_test - cutoff_prev

    # Empirical adjustment factor
    # From historical data:
    # 2022→2023: cutoff went +7.5 → CCMT scores dropped ~15 pts
    # 2023→2024: cutoff went -4.9 → CCMT scores rose ~20 pts
    # Ratio: ~3-4 CCMT points per 1 qualifying cutoff point
    ADJUSTMENT_FACTOR = -3.0  # negative because inverse relationship

    adjustment       = difficulty_shift * ADJUSTMENT_FACTOR
    final_prediction = base_prediction + adjustment

    return final_prediction


# ── Evaluation ────────────────────────────────────────────

def compute_metrics(predictions: list) -> dict:
    """
    Compute MAE, RMSE, and coverage.
    predictions: list of (predicted, actual) tuples
    """
    if not predictions:
        return {"mae": None, "rmse": None,
                "coverage": 0, "n": 0}

    errors = [abs(p - a) for p, a in predictions]
    sq_err = [(p - a)**2 for p, a in predictions]

    mae  = sum(errors) / len(errors)
    rmse = math.sqrt(sum(sq_err) / len(sq_err))

    return {
        "mae":      round(mae, 2),
        "rmse":     round(rmse, 2),
        "n":        len(predictions),
        "coverage": None  # set by caller
    }


# ── Main backtest ─────────────────────────────────────────

async def run_backtest():
    client = AsyncIOMotorClient(MONGODB_URL)
    db     = client[DATABASE_NAME]

    print("=" * 60)
    print("ASCENT Phase 3B — Backtest")
    print(f"Training: {TRAIN_YEARS}")
    print(f"Test:     {TEST_YEAR} (held-out)")
    print("=" * 60)

    data  = await load_cutoff_data(db)
    gate  = await load_gate_difficulty(db)

    # Build the full set of test combinations
    # (all NIT+branch+category in 2026 R1 test set)
    test_combos = []
    for nit in data[TEST_YEAR]:
        for branch in data[TEST_YEAR][nit]:
            for cat, actual_score in \
                    data[TEST_YEAR][nit][branch].items():
                test_combos.append(
                    (nit, branch, cat, actual_score)
                )

    print(f"\nTest set: {len(test_combos)} combinations "
          f"(2026 R1)")

    # Count how many have enough training data
    trainable = sum(
        1 for nit, branch, cat, _ in test_combos
        if len([
            y for y in TRAIN_YEARS
            if data[y][nit][branch].get(cat)
        ]) >= MIN_YEARS_REQUIRED
    )
    print(f"Have >= {MIN_YEARS_REQUIRED} years training data: "
          f"{trainable} ({100*trainable//len(test_combos)}%)")

    # ── Run all 4 methods ─────────────────────────────────
    methods = {
        "Last Year (Baseline)":    [],
        "3-Year Average":          [],
        "Trend-Adjusted":          [],
        "GATE-Difficulty Adjusted (Novel)": [],
    }

    skipped = {m: 0 for m in methods}

    for nit, branch, cat, actual in test_combos:
        # Method 1
        p1 = predict_last_year(
            nit, branch, cat, data, TEST_YEAR
        )
        if p1:
            methods["Last Year (Baseline)"].append(
                (p1, actual)
            )
        else:
            skipped["Last Year (Baseline)"] += 1

        # Method 2
        p2 = predict_rolling_average(
            nit, branch, cat, data, TEST_YEAR
        )
        if p2:
            methods["3-Year Average"].append((p2, actual))
        else:
            skipped["3-Year Average"] += 1

        # Method 3
        p3 = predict_trend_adjusted(
            nit, branch, cat, data, TEST_YEAR
        )
        if p3:
            methods["Trend-Adjusted"].append((p3, actual))
        else:
            skipped["Trend-Adjusted"] += 1

        # Method 4
        p4 = predict_gate_adjusted(
            nit, branch, cat, data, TEST_YEAR, gate
        )
        if p4:
            methods["GATE-Difficulty Adjusted (Novel)"].append(
                (p4, actual)
            )
        else:
            skipped["GATE-Difficulty Adjusted (Novel)"] += 1

    # ── Print results table ───────────────────────────────
    print(f"\n{'='*60}")
    print("RESULTS — Pre-Counselling R1 Prediction (2026)")
    print(f"{'='*60}")
    print(f"{'Method':<35} {'MAE':>7} {'RMSE':>7} "
          f"{'N':>5} {'Coverage':>9}")
    print("-" * 60)

    results = {}
    for method_name, preds in methods.items():
        metrics = compute_metrics(preds)
        total   = len(test_combos)
        cov     = round(100 * len(preds) / total, 1)
        metrics["coverage"] = cov

        results[method_name] = metrics

        print(f"{method_name:<35} "
              f"{metrics['mae']:>7.1f} "
              f"{metrics['rmse']:>7.1f} "
              f"{len(preds):>5} "
              f"{cov:>8.1f}%")

    print("-" * 60)
    print(f"\n{'='*60}")

    # ── Round-ratio test ──────────────────────────────────
    # How well can we predict R2-R6 once R1 is known?
    print("\nIn-Counselling Round-Ratio Prediction")
    print("(Given 2026 R1, predict subsequent rounds)")
    print(f"{'='*60}")

    rounds_to_test = [
        "Round 2", "Round 3",
        "Special Round 1", "Special Round 2",
        "National Spot Round"
    ]

    # Load all 2026 round data
    all_2026 = await db["ccmt_cutoffs"].find(
        {"year": 2026},
        {"_id": 0, "round": 1, "institute_code": 1,
         "branch_code": 1, "category": 1, "min_score": 1}
    ).to_list(10000)

    # Build 2026 by-round lookup
    data_2026_byround = defaultdict(
        lambda: defaultdict(
            lambda: defaultdict(dict)
        )
    )
    for r in all_2026:
        rnd  = r["round"]
        nit  = r["institute_code"]
        br   = r["branch_code"]
        cat  = r["category"]
        s    = r["min_score"]
        if s and s > 0:
            existing = data_2026_byround[rnd][nit][br].get(cat)
            if existing is None or s < existing:
                data_2026_byround[rnd][nit][br][cat] = s

    # Compute historical ratios from training years
    # ratio[round] = average(round_score / R1_score)
    ratio_data = defaultdict(list)
    all_train = await db["ccmt_cutoffs"].find(
        {"year": {"$in": TRAIN_YEARS}},
        {"_id": 0, "year": 1, "round": 1,
         "institute_code": 1, "branch_code": 1,
         "category": 1, "min_score": 1}
    ).to_list(50000)

    # Build training data by round
    train_byround = defaultdict(
        lambda: defaultdict(
            lambda: defaultdict(
                lambda: defaultdict(dict)
            )
        )
    )
    for r in all_train:
        y   = r["year"]
        rnd = r["round"]
        nit = r["institute_code"]
        br  = r["branch_code"]
        cat = r["category"]
        s   = r["min_score"]
        if s and s > 0:
            train_byround[y][rnd][nit][br][cat] = s

    # Compute R1 for each training year+combination
    for y in TRAIN_YEARS:
        r1_data = train_byround[y].get("Round 1", {})
        for rnd in rounds_to_test:
            rnd_data = train_byround[y].get(rnd, {})
            for nit in rnd_data:
                for br in rnd_data[nit]:
                    for cat, rnd_score in \
                            rnd_data[nit][br].items():
                        r1_score = r1_data.get(nit, {}) \
                                        .get(br, {}) \
                                        .get(cat)
                        if r1_score and r1_score > 0:
                            ratio_data[rnd].append(
                                rnd_score / r1_score
                            )

    # Compute average ratios
    avg_ratios = {}
    for rnd, ratios in ratio_data.items():
        if ratios:
            avg_ratios[rnd] = sum(ratios) / len(ratios)

    print(f"\nLearned round-to-R1 ratios (from 2021-2025):")
    for rnd in rounds_to_test:
        ratio = avg_ratios.get(rnd)
        if ratio:
            print(f"  {rnd:<25}: {ratio:.4f} "
                  f"(avg {(1-ratio)*100:.1f}% below R1)")

    # Test ratio predictions on 2026
    print(f"\n{'Round':<25} {'MAE':>7} {'RMSE':>7} "
          f"{'N':>5} {'Coverage':>9}")
    print("-" * 55)

    round_ratio_results = {}
    for rnd in rounds_to_test:
        ratio = avg_ratios.get(rnd)
        if not ratio:
            print(f"{rnd:<25} {'N/A':>7}")
            continue

        preds = []
        # For each 2026 combination in this round
        rnd_data = data_2026_byround.get(rnd, {})
        for nit in rnd_data:
            for br in rnd_data[nit]:
                for cat, actual_score in \
                        rnd_data[nit][br].items():
                    # Get 2026 R1 score for this combo
                    r1_score = data_2026_byround.get(
                        "Round 1", {}
                    ).get(nit, {}).get(br, {}).get(cat)

                    if r1_score and r1_score > 0:
                        predicted = r1_score * ratio
                        preds.append((predicted, actual_score))

        if preds:
            m   = compute_metrics(preds)
            cov = round(
                100 * len(preds) /
                max(len(test_combos), 1), 1
            )
            round_ratio_results[rnd] = {**m, "coverage": cov}
            print(f"{rnd:<25} "
                  f"{m['mae']:>7.1f} "
                  f"{m['rmse']:>7.1f} "
                  f"{len(preds):>5} "
                  f"{cov:>8.1f}%")

    print("-" * 55)

    # ── Save results ──────────────────────────────────────
    all_results = {
        "pre_counselling_r1": results,
        "in_counselling_round_ratio": round_ratio_results,
        "avg_ratios": avg_ratios,
        "meta": {
            "train_years": TRAIN_YEARS,
            "test_year":   TEST_YEAR,
            "test_combos": len(test_combos),
            "min_years_required": MIN_YEARS_REQUIRED
        }
    }

    os.makedirs(os.path.dirname(RESULTS_FILE), exist_ok=True)
    with open(RESULTS_FILE, "w") as f:
        json.dump(all_results, f, indent=2)

    print(f"\n✅ Results saved to:")
    print(f"   data/processed/phase3_backtest_results.json")

    # ── Summary interpretation ────────────────────────────
    print(f"\n{'='*60}")
    print("INTERPRETATION")
    print(f"{'='*60}")

    baseline_mae = results["Last Year (Baseline)"]["mae"]
    novel_mae    = results[
        "GATE-Difficulty Adjusted (Novel)"
    ]["mae"]

    if baseline_mae and novel_mae:
        improvement = baseline_mae - novel_mae
        pct         = round(100 * improvement / baseline_mae, 1)
        if improvement > 0:
            print(f"✅ GATE-adjusted method BEATS baseline by "
                  f"{improvement:.1f} MAE points ({pct}%)")
            print(f"   This validates using GATE difficulty as a")
            print(f"   feature for CCMT cutoff prediction.")
        else:
            print(f"⚠️  GATE-adjusted method does NOT beat baseline")
            print(f"   Baseline MAE: {baseline_mae}")
            print(f"   Novel MAE:    {novel_mae}")
            print(f"   The adjustment factor may need tuning.")
            print(f"   This is still a valid research finding:")
            print(f"   simple methods work well for stable series.")

    # Round ratio summary
    r2_mae = round_ratio_results.get("Round 2", {}).get("mae")
    if r2_mae:
        print(f"\n✅ In-counselling (given R1) R2 prediction MAE:")
        print(f"   {r2_mae:.1f} points — "
              f"{'excellent' if r2_mae < 15 else 'good' if r2_mae < 30 else 'moderate'}")
        print(f"   This is the scenario where ASCENT adds")
        print(f"   the most value during live counselling.")

    print(f"\n{'='*60}")
    print("Phase 3B COMPLETE")
    print("Next: python app/phase3_model.py")
    print(f"{'='*60}")

    client.close()


if __name__ == "__main__":
    asyncio.run(run_backtest())
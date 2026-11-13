# Confirmatory script: pre-freeze acceptance tests (simulate mode only)

Script under test: `scripts/confirmatory_analysis.py`. Test driver: `scripts/confirmatory_script_tests.py`. Every outcome here is simulated; the outcome file was not opened (T5). Script SHA-256 at report time: `8d842b70db03e2b0aa223f827bf0a496cb971ca3ea03f0a7c56563be8c046aca`.

| Test | Result |
|---|---|
| T1 Bayesian null calibration | k = 6 of 100 null intervals exclude 0 -> CALIBRATION_CONTINGENCY: INACTIVE |
| T1b Permutation calibration | 2 of 50 with p < 0.05 -> ok (<= 5) |
| T2 Planted effect 0.25, M1 | PASS |
| T3 Planted effect, M2 d_lpick | PASS |
| T4 End-to-end simulate run | PASS |
| T5 Sealed-file isolation | PASS |
| T6 PC1 code path | PASS |

## T1 Bayesian null calibration

Setting: light (1000/1000, 4 chains), with the section 5.5 escalation; 100 null datasets (beta_gap = 0, sim seeds 1-100, P design, M1 as in confirmatory mode (`target_accept` 0.90, seed 2027), 7 fits in parallel, 4 chains each).

| Quantity | Value |
|---|---|
| Intervals excluding 0 (either direction) | **6 of 100** (positive 2, negative 4) |
| Coverage of the true value 0 | 0.94 |
| Contingency | **INACTIVE** (ACTIVE if k >= 10) |
| GLM mirror, rejections at nominal Wald z (information only) | 7 of 100 |
| GLM mirror, rejections with t(G-1) reference (nominal) | 7 of 100 |
| GLM mirror, rejections kappa-calibrated (kappa 1.20, t reference) | 5 of 100 |
| Mean / SD of Bayesian posterior median over datasets | -0.0115 / 0.0831 |
| Mean posterior SD (width/3.92) vs mean GLM two-way SE | 0.0900 vs 0.0773 |
| Fits failing the section 5.5 criteria (any of R-hat, ESS, divergences) | 0 of 100 (R-hat > 1.01: 0, ESS < 400: 0, any divergence: 0; max R-hat 1.010) |
| Timing | mean sampling time per fit 112s; mean per-dataset time 113s; wall 27.9 min |

## T1b Permutation calibration

First 50 null datasets (seeds 1-50), studentized Freedman-Lane test, 199 permutations each, `default_rng(sim_seed)`. **2 of 50** have two-sided p < 0.05 (P(>= 6 of 50) = 0.04 under nominal size). Mean time per test 7.4s; wall 1.2 min.

## T2 Planted effect 0.25, M1

Seeds 101-105, beta_gap = 0.25. Estimates (posterior medians): 0.272, 0.243, 0.301, 0.249, 0.280; mean 0.269. Intervals cover 0.25 in 5 of 5. Setting: light (1000/1000). **PASS**.

## T3 Planted effect, M2 d_lpick

Seeds 101-105, beta_gap = 0.25. Estimates (posterior medians): -0.280, -0.351, -0.282, -0.108, -0.217; mean -0.248. Target -0.20 +/- 0.08. **PASS**.

## T4 End-to-end simulate run

`--mode simulate --sim-seed 201 --sim-beta-gap 0.25 --light`: return code 0, runtime 39.6 min, problems: none. Outputs in `C:\Users\jm_pa\Documents\GitHub\Big data bowl 2027\data\processed\confirmatory_sim\201`. **PASS**.

| Table | rows x cols | NaN cells | empty cells |
|---|---|---|---|
| R1 | 19 x 10 | 0 | 0 |
| R2 | 18 x 4 | 0 | 2 |
| R3 | 18 x 2 | 0 | 0 |
| R4 | 52 x 5 | 0 | 51 |
| R5 | 15 x 9 | 0 | 16 |
| R6 | 7 x 2 | 0 | 0 |
| R7 | 17 x 5 | 0 | 8 |
| R8 | 19 x 7 | 0 | 0 |
| R9 | 11 x 2 | 0 | 0 |
| R10 | 46 x 2 | 0 | 0 |

## T5 Sealed-file isolation

Static: the outcome file name occurs on source lines [260], all inside `load_sealed_outcomes` (True). Dynamic: `open`, `Path.open/read_bytes/read_text`, `polars.read_parquet/scan_parquet`, `pandas.read_parquet` instrumented around a simulate build + outcome generation + PC1 (11 file-open calls recorded, none naming the outcome file: True); `load_sealed_outcomes` called twice on purpose in simulate mode (once with the guard flag forced True) and refused both times before any file access (2 calls, refusals: True, True). The guard parser refuses the current manifest (fields still open: ['SCRIPT_SHA256', 'CALIBRATION_CONTINGENCY', 'PERMUTATION_CALIBRATION', 'INPUT_SHA256 data/processed/engaged_outcomes_SEALED.parquet']) and accepts a complete synthetic manifest. Confirmatory mode was never executed. **PASS**.

## T6 PC1 code path

Synthetic table (n = 400,000) built from logit with pick -0.204, weight -0.214, dropback +0.577. Recovered: pick -0.1965, weight -0.2078, dropback 0.5731. Maximum absolute difference to an independent numpy IRLS + one-way cluster-sandwich implementation: 1.30e-17. Pass-rule boundary checks: [True, True, True, True, True]. **PASS**. PC1 on the real outcomes cannot be run before freeze.

## Changes after the 2026-11-07 amendment, and quick check

Implemented: Gram-Schmidt orthonormalisation of db1-db3 (computed over the primary set of each composite version, 3x3 transform stored with the constants, applied to all rows; correlation before/after logged to run_log.txt: db1-db2 0.920, db1-db3 0.881, db2-db3 0.995 before; all 0 after); `low_rank_modified_mass_matrix=True` in every `nutpie.sample` call (nutpie 0.16.11 emits a FutureWarning that this name is deprecated in favour of `adaptation='low_rank'`; same behaviour); the combine_tracking and combine_results hashes are required manifest lines; idata is saved for every Bayesian fit (light and full) as `.nc` (33 files written in the T4 run, all re-opened with xarray). `h5py` had to be installed into `.venv` for h5netcdf to work (not in requirements.txt: it needs `h5py` added).

Quick check on null seeds 1-4 (light, no escalation, new code): max R-hat 1.0046 / 1.0077 / 1.0043 / 1.0034 (all pass); min ESS of gap (bulk / tail) 4623/2918, 5933/3232, 7199/2822, 5654/2994; sampling about 70 s per fit. The GLM gap estimate is identical to the pre-change code on the same datasets (absolute differences 1e-15 to 3e-16).

After the change: T1 k = 6 of 100 again (same 2 positive / 4 negative; GLM rejections 7 / 7 / 5), 0 of 100 final fits fail the section 5.5 criteria (max R-hat 1.0098), 9 of 100 needed the escalation; wall 28 min instead of 103 min. T1b 2 of 50. T2/T3 pass in 199 s. T4 (`--light`, seed 201, CLI): 2,378 s, every table without NaN, 33 `.nc` files written and re-opened.

## Superseded: results before the amendment (script sha256 a7a32250...)

T1: k = 6 of 100, but 46 of 100 fits failed the R-hat rule after escalation (max 1.027); wall 6,197 s. T1b: 2 of 50. T2: mean 0.269, 5 of 5 covered; T3: mean -0.248. T4 (light, escalation on): 10,551 s. The "Findings" section earlier in this file described the R-hat problem that the amendment fixes; the numbers in the tables above this section come from the amended script.

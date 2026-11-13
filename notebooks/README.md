# Notebook: `bdb2027_trench_matchup.ipynb`

The public Kaggle notebook of the entry. It runs top to bottom from the competition CSVs, asserts the numbers it must reproduce, and prints a PASS line per assertion (54 on the local run, about 66 on a from-scratch run). It stops with an error if any number is off.

> **Repository history.** The published history was re-created at publication as two commits: the pre-registration freeze (tag `prereg-frozen`) and the completed analysis. The commit id recorded in the run manifest (R0, `deba6bc`) belongs to the original local history; the frozen state is verified by the file hashes in `reports/preregistration.md` section 13.1, which the tag reproduces.

> **Line endings and the frozen hashes.** The pre-registration manifest registered SHA-256 hashes of four files as they sat in the Windows checkout where the freeze was made (`scripts/confirmatory_analysis.py` and `src/bdb2027/traits.py` with CRLF, `src/bdb2027/paths.py` and `reports/preregistration.md` with LF). `.gitattributes` pins those endings, so a clone on any platform reproduces the registered hashes and the frozen script's guards pass. If you copy the files by other means, keep the line endings.

## What it reproduces

| Step | Content | Source of the code |
|---|---|---|
| 1 | CSV to Parquet, row counts of all nine tables | `bdb2027.convert` |
| 2 | Engaged pass-protection reps: 29,269 pairs, 8,271 engaged reps, 107 blockers, 129 rushers | `bdb2027.engaged_reps` |
| 3 | Combine trait qualification and the frozen composites (OL = {O3}, DL = {D1}) | `bdb2027.traits` (the calls of `scripts/trait_qualification.py`, without its file writes) |
| 4 | Pre-registered analysis sets: P = 7,214 reps / 69 blockers / 97 rushers / 1,201 dyads; PL = 17,795 reps | `scripts/confirmatory_analysis.py`, imported read-only |
| 5 | Positive control PC1 (pick -0.204, dropback 0.577) and the GLM mirror of M1 (gap -0.154, kappa CI [-0.308, 0.000]), M2 (gap -0.138) and S1 (c_B +0.143, c_R -0.064), asserted equal to the frozen run to 3 decimals | same, `AnalysisBase.prepare / attach_outcomes / pc1 / fit_model(bayes=False)` |
| 6 | Frozen Bayesian results (R2 convergence table, R3 headline, verdict label) | **loaded** from `reports/confirmatory_results.json` |
| 7 | Figures F1-F6 (F5 `f5_anatomy.py` has its own cell; its exploratory rows are X1-X3 of `reports/specification_log.md`, run after unsealing, not pre-registered) | `scripts/figures/*.py`, run unchanged |
| 8 | Package versions, input hashes against the pre-registration manifest (section 13.1), run times, one PASS line per assertion | |

## What is loaded from the frozen run, and why

The Bayesian multilevel models (PyMC with nutpie) are **not refitted** in the notebook; they need `pymc`, `nutpie` and `numba` and took 64 minutes on 32 CPUs. Their results are read from `reports/confirmatory_results.json`. To reproduce them locally:

```
python scripts/confirmatory_analysis.py --mode confirmatory
```

The script refuses to run unless its own SHA-256 is `8d842b70db03e2b0aa223f827bf0a496cb971ca3ea03f0a7c56563be8c046aca`, the input hashes and package versions equal the manifest of `reports/preregistration.md` section 13.1 (tag `prereg-frozen`), and no earlier `reports/confirmatory_results.md` exists (rerun with `--rerun-reason`). The notebook never calls the script's `main()` and never passes `--mode confirmatory`.

The GLM mirror in step 5 is not a substitute for the Bayesian inference: it is the pre-registered frequentist check (section 5.6) and is shown next to the frozen numbers so a reader can verify the pipeline from raw CSVs to the design matrix and the outcome join.

F4, F5 and F6 need small data products: `forest_data.csv` and `permutation_null.csv` of the frozen run, plus for F5 the exploratory tables `x1_fits.csv`, `x2_permutation_summary.csv`, `x3_glm_fits.csv` (copied from `reports/exploratory/tables/`, which the `*.csv` rule hides from a clone). They are committed in `notebooks/frozen_products/` and `notebooks/frozen_products/exploratory_tables/` (the repository's `.gitignore` re-includes them; the notebook rebuilds the frozen tables R1-R10 from the JSON, and stages everything under one folder; they are derived results, not competition data) and are byte-identical to the originals in `data/processed/confirmatory/` (the notebook checks this when the originals exist).

## Run locally

From the repository root, with the raw CSVs in `data/raw/` (not in git; CC BY-NC 4.0):

```
.venv\Scripts\python -m pip install -e .
.venv\Scripts\python -m jupyter nbconvert --to notebook --execute notebooks\bdb2027_trench_matchup.ipynb --output-dir data\notebook_outputs --ExecutePreprocessor.timeout=-1
```

Paths come from `bdb2027.paths`. Environment variables:

* `BDB_RAW_DIR`, `BDB_PROCESSED_DIR`: override the data folders. Parquet files that already exist in the processed folder are **reused**, never overwritten; this keeps the registered file hashes of `data/processed` intact. To exercise the conversion and the builders, point `BDB_PROCESSED_DIR` at an empty folder.
* `BDB_OUT_DIR`: where staged results and figure PNGs are written (default `data/notebook_outputs`; `/kaggle/working/notebook_outputs` on Kaggle). The repository's own `figures/` folder is not touched.
* `BDB_NB_REBUILD=1`: rebuild the Parquet files of the processed folder even if they exist. Refused when the processed folder is the repository's frozen `data/processed`.

## Run on Kaggle

1. `REPO_URL` at the top of the first code cell points at the public repository, https://github.com/Jopared/bdb2027-trench-matchup (the notebook clones it, optionally at `REPO_REF`, and runs `pip install -e . --no-deps`).
2. Notebook settings: **Internet ON** (needed for `git clone`; Kaggle requires it off for some competition submissions, so see the alternative below), add the competition data `nfl-big-data-bowl-2027` as input.
3. Alternative without internet: attach a Kaggle Dataset that contains a copy of the repository (anything under `/kaggle/input/<name>/` with `src/bdb2027` inside). The notebook finds it, copies it to `/kaggle/working/bdb2027-repo` and installs it from there.
4. The processed Parquet files are written to `/kaggle/working/processed` (about 460 MB). Required libraries are all in the standard Kaggle image: polars, pandas, numpy, scipy, statsmodels, matplotlib, pyarrow. No GPU.

## Expected runtime

* With existing Parquet files (author's machine, 32-thread CPU): about 20 seconds wall clock including kernel start.
* From the raw CSVs into an empty processed folder: about 1.5 minutes of work (CSV conversion 67 s, engaged-rep build 1 s, everything else under 15 s) plus kernel start and the content cross-check; the rebuilt Parquet files were byte-identical (same SHA-256) to the registered ones. Kaggle CPUs are slower, so allow 5-10 minutes.
* The step 6 Bayesian results are read, not computed.

## Licence

The code is released under the MIT licence (`LICENSE` at the repository root, "Big Data Bowl 2027 entry authors"), an OSI-approved licence that permits commercial use, as the competition rules require of winners. The competition data are CC BY-NC 4.0 and are not part of the repository or of the notebook output; the notebook prints aggregates and figures only.

Dependencies of the required path (polars, pandas, numpy, scipy, statsmodels, matplotlib, pyarrow) are permissively licensed (BSD, Apache-2.0 or similar). `pymc`, `nutpie` and `numba` (Apache-2.0 / BSD) are needed only to rerun the frozen Bayesian script, not by the notebook.

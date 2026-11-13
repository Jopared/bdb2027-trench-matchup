# Figure scripts

Run from the repo root with `.venv\Scripts\python scripts\figures\<script>.py`. All outputs go to `figures\` (PNG at 200 dpi plus the CSV of plotted values). Style and palette live in `_common.py` (dataviz reference palette, light mode). No script reads outcome columns, the sealed outcomes file, or anything under `data\processed\confirmatory\` or `reports\confirmatory*`.

| Script | Inputs | Outputs |
|---|---|---|
| `f1_engaged_rep.py` | `engaged_pairs.parquet` (open columns), `players.parquet`, `game_tracking_<season>.parquet` (lazy, filtered to one play and two players), `player_play.parquet` (only `nfl_id`, `lined_up_position`, to look for a QB; none exists) | `F1_engaged_rep.png/.csv` |
| `f3_combine_measured.py` | `combine_tracking.parquet`, `combine_traits.parquet`, `combine_results.parquet`, `players.parquet`, `bdb2027.traits` (helpers) | `F3_combine_measured.png/.csv` |
| `f4_forest.py [dir]` | results dir: `confirmatory_results.json`, `forest_data.csv`, `tables/R4.csv` | `F4.png/.csv` (real) or `sim_F4.*` (json `mode == "simulate"`) |
| `f5_surface.py [dir]` | results dir: `confirmatory_results.json` (mode only), `surface_S2s.csv` | `F5.*` / `sim_F5.*` |
| `f6_robustness.py [dir]` | results dir: `confirmatory_results.json`, `permutation_null.csv` | `F6.*` / `sim_F6.*` |

F4-F6 default to `data\processed\confirmatory_sim\201`; pass the real results directory as the single argument to render the real figures (no `sim_` prefix, no SIMULATED title).

## Deterministic selection rules

- **F1.** Eligible: `engaged_primary`, not `double_team`, and the blocker has no other engaged rusher on the play. Chosen: eligible pair whose `n_close_150` is closest to the eligible median (14); ties by ascending game_id, play_id, blocker id, rusher id.
- **F3 A (OL).** OL with registered O3 value, a mirror-drill rep and two PASS_RUSH_DROP reps; O3_value closest to the OL median; ties by nfl_id. The registered OL composite is the MIRROR drill (O3), so panel A1 shows the mirror rep (reversal segments highlighted, orange) and A2 the same player's two PASS_RUSH_DROP reps.
- **F3 B (DL).** DL with D1 value and a left and a right PASS_RUSH_DRILL rep (side by start point, as in `traits.start_side_rush`); D1_value closest to the DL median; ties by nfl_id. Whole-rep peak of the 3-frame smoothed speed is ringed.
- **F3 C (40).** OL/DL with two-run 40 acceleration shape (O4/D5) and official forty; both runs' own shapes within 0.30 s (removes one tracking outlier); same combine position; |forty difference| <= 0.01 s; pick the pair with the largest |shape difference| (ties: smaller forty gap, then ids). Curves aligned at the first frame with smoothed speed >= 2 yd/s.

## Real-run additions

- `f2_engine_is_real.py [confirmatory_results.json]`: panel A recomputes the coherence share from `engaged_pairs.parquet` joined to `engaged_outcomes_SEALED.parquet` (`pressure_allowed`, `rusher_time_to_pressure`; 1,000 play-cluster bootstrap, seed 2027); panel B reads `pc2.summary` and `placebo.beta_lpd_PL` from `reports\confirmatory_results.json`. Output `F2_engine_is_real.png/.csv`.
- F4-F6 accept either layout: `scripts\figures\f4_forest.py reports` (real: json in `reports\`, tables in `reports\confirmatory\tables\`, data products in `data\processed\confirmatory\`) or a single sim folder (default). Real outputs: `F4_forest`, `F5_surface`, `F6_robustness` (no SIMULATED label); sim outputs keep the `sim_F4/5/6` names. F4 uses per-term rows from `forest_data.csv` when present, otherwise parses `R4.csv`.

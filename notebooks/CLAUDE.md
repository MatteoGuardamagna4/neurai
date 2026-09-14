# notebooks/

`tribe_phase2.ipynb` is Phase II (brief §6, §10.1) and runs on **Google Colab with a GPU**; nothing else in the
repository needs it. It fetches this repository (private GitHub via a `GITHUB_TOKEN` Colab secret, a copy on
Drive, an uploaded zip, or `local`), validates the corpus with `neurotutorsim.corpus`, installs TRIBE v2 at a
pinned commit, verifies the checkpoint's SHA-256 against the Hub's LFS id, reproduces the official text demo
(decision gate 17), then predicts every stimulus and writes the brief's D3 prediction dataset to
`DRIVE_OUTPUT_DIR/<RUN_TAG>/`: vertex predictions, parcel summaries, network time courses, §6.5 metrics, controls,
metadata. **No figures, no contrasts, no RSA in the notebook** (user decision 2026-09-14: predictions only); those
are offline calls to `tribe.fixed_effects` / `tribe.rsa` on the saved tables and need no GPU.

Decisions baked in:

- **The stimulus is the file body** (all sections in order, headings excluded): the text the Phase I duration
  caliper was computed on. Section onsets are saved (`tribe_sections.csv`) so windows can be restricted later.
- **Timing is eq. 4 on whitespace tokens** at 220 wpm, with 180 and 260 as robustness arms; each arm is a
  `wpm<r>/` folder. Contexts come from the official `AddContextToWords` transform, so the encoder input matches
  the released pipeline except for the word timestamps, which are deterministic instead of TTS + WhisperX.
- **Text only, no TTS audio.** The model was trained with modality dropout 0.3, so an absent modality is
  in-distribution; the optional audio arm of §5.2 item 10 is not built.
- **Released configuration untouched** except batch size, worker count and the text encoder's precision (fp16
  on GPUs under 20 GB, recorded in `run_metadata.json`). `cache_n_layers` stays 20 because changing it changes
  the features the model was trained on; the feature cache is ~13 GB and lives on the runtime disk, not Drive.
- **Schaefer-200 / 7 networks on fsaverage5** from the CBIG repository at a pinned commit; area weights from
  nilearn's fsaverage5 area maps (eq. 7 main), equal weights as robustness (`level == "network_equal"`).
- **Append-only and resumable**: predictions are one file per stimulus; rerunning a tag skips what exists.
- `DRY_RUN = True` replaces the model with seeded noise to exercise the pipeline offline; outputs are quarantined
  under `DRYRUN_<tag>` and flagged in the metadata. It is a smoke test, never a result.

All arithmetic lives in `src/neurotutorsim/tribe.py` (tested offline); the notebook only orchestrates. Rebuild the
notebook by editing it directly; keep cell outputs cleared in git.

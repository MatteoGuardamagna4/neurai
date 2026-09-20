"""Re-aggregate saved TRIBE vertex predictions onto another Schaefer parcellation (brief §10.4: parcellation is
one of the multiverse dimensions; the main run used Schaefer-400, PLAN.md D12).

    uv run --with nibabel --with nilearn python scripts/reparcellate.py --parcels 200
    uv run --with nibabel --with nilearn python scripts/reparcellate.py --parcels 400 --validate

No GPU and no TRIBE model: this reads `<run>/wpm<speed>/tribe_vertex/*.parquet`, applies eq. 6-7 with the new
atlas and writes the same tables the notebook writes, into `<run>_s<parcels>/wpm<speed>/`. `--validate` rebuilds
the parcellation the run already used and checks it reproduces the notebook's parcel table and metrics, which is
what makes the comparison trustworthy: the same vertex predictions, a different map.

nibabel and nilearn are not project dependencies (the notebook runs on Colab, where both are installed); pass
them with `uv run --with` as above, so the analysis environment stays as it is.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from neurotutorsim import tribe  # noqa: E402

SCHAEFER_COMMIT = "d1454a611f7de10a3b36665e6fbb3fb6c770d140"  # as pinned in notebooks/tribe_phase2.ipynb
BASE = (f"https://raw.githubusercontent.com/ThomasYeoLab/CBIG/{SCHAEFER_COMMIT}/stable_projects/brain_parcellation/"
        "Schaefer2018_LocalGlobal/Parcellations/FreeSurfer5.3/fsaverage5/label/")
N_VERTICES = 20484


def sha256_of(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(chunk), b""):
            h.update(block)
    return h.hexdigest()


def build_parcellation(n_parcels: int, annot_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """The notebook's §6.4 cell: Schaefer annotations at the pinned commit plus fsaverage5 vertex areas."""
    import nibabel as nib
    from nilearn import datasets

    annot_dir.mkdir(parents=True, exist_ok=True)
    labels, names, area, provenance = {}, {}, {}, {}
    fsaverage = datasets.fetch_surf_fsaverage("fsaverage5")
    for hemi, fs in (("left", "lh"), ("right", "rh")):
        fname = f"{fs}.Schaefer2018_{n_parcels}Parcels_7Networks_order.annot"
        path = annot_dir / fname
        if not path.exists():
            urllib.request.urlretrieve(BASE + fname, path)
        lab, _ctab, nm = nib.freesurfer.read_annot(str(path))
        labels[hemi], names[hemi] = lab, nm
        src = fsaverage[f"area_{hemi}"]
        area[hemi] = nib.load(src).darrays[0].data if isinstance(src, (str, Path)) else np.asarray(src)
        provenance[hemi] = {"file": fname, "url": BASE + fname, "sha256": sha256_of(path)}
    parc = tribe.parcellation(labels, names, area)
    table = tribe.parcel_table(parc)
    if len(parc) != N_VERTICES or table.parcel_id.nunique() != n_parcels:
        raise RuntimeError(f"unexpected parcellation: {len(parc)} vertices, {table.parcel_id.nunique()} parcels")
    return parc, table, provenance


def summarize(vertex_dir: Path, parc: pd.DataFrame, table: pd.DataFrame, wpm: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Every stimulus of one reading speed through eq. 6-9, exactly as the notebook does it."""
    rows, patterns, ids = [], {}, []
    files = sorted(vertex_dir.glob("*.parquet"))
    for i, path in enumerate(files, 1):
        sid = path.stem
        unit_id, condition = sid.split("_", 2)[0] + "_" + sid.split("_")[1], sid.split("_", 2)[2]
        preds, _ = tribe.read_vertex(path)
        r, pattern = tribe.summarize_prediction(preds, parc, table, stimulus_id=sid, unit_id=unit_id,
                                                condition=condition, variant="primary", wpm=wpm)
        rows.append(r)
        patterns[sid] = pattern.astype(np.float32)
        ids.append(sid)
        if i % 10 == 0 or i == len(files):
            print(f"  {i}/{len(files)} stimuli", flush=True)
    parcel_ids = np.sort(table.parcel_id.to_numpy())
    return pd.concat(rows, ignore_index=True), pd.DataFrame(patterns, index=parcel_ids).T.reindex(ids)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", default="data/tribe/tribe_main", help="the TRIBE run holding tribe_vertex/")
    ap.add_argument("--parcels", type=int, default=200, choices=(200, 400))
    ap.add_argument("--wpm", type=int, default=220, help="reading speed to re-aggregate (the main specification)")
    ap.add_argument("--validate", action="store_true",
                    help="rebuild the run's own parcellation and compare with what the notebook wrote")
    args = ap.parse_args(argv)
    run = Path(args.run)
    vertex_dir = run / f"wpm{args.wpm}" / "tribe_vertex"
    if not vertex_dir.is_dir():
        raise SystemExit(f"no vertex predictions in {vertex_dir}")
    out = run if args.validate else Path(f"{run}_s{args.parcels}")
    started = time.time()
    parc, table, provenance = build_parcellation(args.parcels, (out if not args.validate else run) / "parcellation")

    if args.validate:
        ref = pd.read_csv(run / "parcels_schaefer400.csv")
        got = table.sort_values("parcel_id").reset_index(drop=True)
        ref = ref.sort_values("parcel_id").reset_index(drop=True)[got.columns]
        same_ids = (got["parcel_id"].to_numpy() == ref["parcel_id"].to_numpy()).all()
        same_names = (got["parcel_name"].to_numpy() == ref["parcel_name"].to_numpy()).all()
        same_area = np.allclose(got["area"], ref["area"], rtol=1e-9, atol=1e-6)
        same_n = (got["n_vertices"].to_numpy() == ref["n_vertices"].to_numpy()).all()
        print(f"parcel ids equal: {same_ids}; names equal: {same_names}; n_vertices equal: {same_n}; "
              f"areas equal: {same_area} (max |diff| {np.abs(got['area'] - ref['area']).max():.3g})")
        one = sorted(vertex_dir.glob("*.parquet"))[0]
        preds, _ = tribe.read_vertex(one)
        sid = one.stem
        r, _ = tribe.summarize_prediction(preds, parc, table, stimulus_id=sid, unit_id="x", condition="y",
                                          variant="primary", wpm=args.wpm)
        ref_m = pd.read_parquet(run / f"wpm{args.wpm}" / "tribe_metrics.parquet")
        ref_m = ref_m[ref_m.stimulus_id == sid]
        m = r.merge(ref_m, on=["stimulus_id", "level", "key", "metric"], suffixes=("_new", "_ref"))
        d = (m["value_new"] - m["value_ref"]).abs()
        print(f"{sid}: {len(m)} metric rows compared, max |diff| {d.max():.3g}, all within 1e-6: {bool(d.max() < 1e-6)}")
        return 0 if (same_ids and same_names and same_n and same_area and d.max() < 1e-6) else 1

    speed_dir = out / f"wpm{args.wpm}"
    speed_dir.mkdir(parents=True, exist_ok=True)
    metrics, patterns = summarize(vertex_dir, parc, table, args.wpm)
    metrics.to_parquet(speed_dir / "tribe_metrics.parquet", index=False)
    patterns.to_parquet(speed_dir / "tribe_patterns.parquet")
    table.to_csv(out / f"parcels_schaefer{args.parcels}.csv", index=False)
    parc.to_csv(out / f"parcellation_schaefer{args.parcels}_fsaverage5.csv", index=False)
    meta = {"source_run": str(run), "parcels": args.parcels, "wpm": args.wpm, "schaefer_commit": SCHAEFER_COMMIT,
            "annotations": provenance, "n_stimuli": int(metrics.stimulus_id.nunique()),
            "area_source": "nilearn fsaverage5 area maps (mm^2)", "seconds": round(time.time() - started, 1),
            "recorded_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    (out / "reparcellation.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(json.dumps({k: meta[k] for k in ("parcels", "wpm", "n_stimuli", "seconds")}), "->", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

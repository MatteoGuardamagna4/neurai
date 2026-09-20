"""Make deliverable D3 citable: a SHA-256 manifest of every TRIBE output, and a small bundle that rebuilds
every table and figure without the 8.1 GB of vertex predictions (PLAN.md D26).

    uv run python scripts/archive_tribe.py manifest        # write data/tribe/MANIFEST.sha256 (tracked in git)
    uv run python scripts/archive_tribe.py bundle          # write dist/neurotutorsim_tribe_d3_<date>.zip
    uv run python scripts/archive_tribe.py verify          # re-hash the tree against the manifest

Why two artefacts. `data/tribe` is gitignored and lives on one laptop plus a Drive folder, so Phase II is today
the one deliverable the repository cannot rebuild: the notebook needs a Colab GPU, ~8 h and a gated Llama licence.
The **manifest** is committed, so the exact bytes behind every published number are identified for ever, and a
later copy can be proved (or disproved) to be the same data. The **bundle** is what a reader actually needs: every
file `src/neurotutorsim/{analysis,report,plasticity,tribe}.py` opens, which is tens of MB and fits any repository
or Zenodo/OSF deposit. What the bundle leaves out is raw prediction mass, not evidence: the per-stimulus vertex
matrices (§6.3) and the 180 per-stimulus shuffled-control predictions, both of which the analysis only ever reads
through the aggregated tables that ARE included. Those stay covered by the manifest.

Uploading is yours: this script only builds the files. See README "Archiving Phase II (D3)".
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TRIBE = ROOT / "data" / "tribe"
MANIFEST = TRIBE / "MANIFEST.sha256"

# Everything the analysis layer opens, derived from the filenames in src/neurotutorsim/*.py and scripts/*.py.
# Directories are taken whole; names without a separator match any file with that name at any depth.
BUNDLE_NAMES = {
    "tribe_metrics.parquet",            # plasticity.load_z: the eq. 28 input, every level and metric
    "tribe_patterns.parquet",           # §6.7 RSA and eq. 34: the z_uc parcel patterns
    "tribe_metrics_network.csv",        # network-level metrics, readable without pyarrow
    "tribe_sections.csv",               # section onsets, for restricting the eq. 8 window
    "tribe_controls_shuffled.csv",      # §10.1/§10.3 shuffled-text controls, aggregated
    "tribe_metrics_text_controls.parquet",   # F2 reworded variants and F5 incorrect-but-fluent texts
    "tribe_patterns_text_controls.parquet",
    "semantic_coverage.csv",            # §5.4 coverage
    "run_metadata.json", "tribe_qc.json", "text_encoder.json", "tribe_run_log.jsonl",  # provenance (§4.3)
    "units.csv", "stimuli.csv",
}
BUNDLE_GLOBS = ("parcels_schaefer*.csv", "parcellation_schaefer*.csv")  # eq. 6-7 parcel and network maps
BUNDLE_DIRS = ("official_demo",)        # decision-gate-17 evidence: the official example's own prediction
EXCLUDE_DIRS = ("tribe_vertex",)        # §6.3 raw predictions: manifested, never bundled


def walk(root: Path):
    return sorted((p for p in root.rglob("*") if p.is_file() and p.name != MANIFEST.name),
                  key=lambda p: p.relative_to(root).as_posix())


def sha256(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(chunk), b""):
            h.update(block)
    return h.hexdigest()


def wanted(path: Path) -> bool:
    """Is this file part of the analysis-sufficient bundle?"""
    parts = path.relative_to(TRIBE).parts
    if any(d in parts for d in EXCLUDE_DIRS):
        return False
    if any(d in parts for d in BUNDLE_DIRS):
        return True
    return path.name in BUNDLE_NAMES or any(path.match(g) for g in BUNDLE_GLOBS)


def write_manifest() -> int:
    files = walk(TRIBE)
    if not files:
        print(f"nothing under {TRIBE}", file=sys.stderr)
        return 1
    lines = [f"# NeuroTutorSim deliverable D3 (brief §4.2, §6.3): SHA-256 of every TRIBE output.",
             f"# generated {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} over {len(files)} files, "
             f"{sum(p.stat().st_size for p in files) / 1e9:.2f} GB.",
             "# Verify with: uv run python scripts/archive_tribe.py verify",
             "# `bundle` marks the files carried by the citable zip; the rest are raw predictions the analysis",
             "# only reads through the aggregated tables.",
             "# sha256  size_bytes  in_bundle  path"]
    total_bundle = 0
    for p in files:
        size = p.stat().st_size
        inb = wanted(p)
        total_bundle += size if inb else 0
        lines.append(f"{sha256(p)}  {size}  {'bundle' if inb else '-'}  {p.relative_to(TRIBE).as_posix()}")
    MANIFEST.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"{MANIFEST.relative_to(ROOT)}: {len(files)} files, "
          f"{sum(p.stat().st_size for p in files) / 1e9:.2f} GB total, {total_bundle / 1e6:.1f} MB in the bundle")
    return 0


def read_manifest() -> dict[str, tuple[str, int]]:
    if not MANIFEST.exists():
        raise SystemExit(f"{MANIFEST} does not exist: run `archive_tribe.py manifest` first")
    out = {}
    for line in MANIFEST.read_text(encoding="utf-8").splitlines():
        if line and not line.startswith("#"):
            digest, size, _flag, rel = line.split("  ", 3)
            out[rel] = (digest, int(size))
    return out


def verify() -> int:
    recorded = read_manifest()
    present = {p.relative_to(TRIBE).as_posix(): p for p in walk(TRIBE)}
    missing = sorted(set(recorded) - set(present))
    added = sorted(set(present) - set(recorded))
    changed = [rel for rel, p in sorted(present.items())
               if rel in recorded and (p.stat().st_size != recorded[rel][1] or sha256(p) != recorded[rel][0])]
    for label, items in (("missing", missing), ("changed", changed), ("not in the manifest", added)):
        if items:
            print(f"{len(items)} {label}:", file=sys.stderr)
            for rel in items[:20]:
                print(f"  {rel}", file=sys.stderr)
            if len(items) > 20:
                print(f"  ... and {len(items) - 20} more", file=sys.stderr)
    if missing or changed:
        return 1
    print(f"verified {len(recorded)} files against {MANIFEST.name}" + (f" ({len(added)} new, not yet manifested)" if added else ""))
    return 0


def bundle(out_dir: Path) -> int:
    files = [p for p in walk(TRIBE) if wanted(p)]
    if not files:
        print("no bundle files found: is data/tribe populated?", file=sys.stderr)
        return 1
    if not MANIFEST.exists():
        write_manifest()
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"neurotutorsim_tribe_d3_{time.strftime('%Y%m%d')}.zip"
    readme = (
        "NeuroTutorSim - deliverable D3, analysis-sufficient bundle\n"
        "=========================================================\n\n"
        "Predicted cortical responses from TRIBE v2 for the 90 matched lesson stimuli (30 units x 3 instructional\n"
        "conditions) at 180 / 220 / 260 words per minute, their shuffled-text controls, the 210 reworded and\n"
        "incorrect-but-fluent text controls, and the Schaefer-400 and Schaefer-200 parcel and network maps.\n"
        "These are MODEL-PREDICTED responses for an average adult subject, not measurements from any person,\n"
        "and they describe immediate stimulus-evoked response only - never learning or plasticity.\n\n"
        "Unpack into `data/tribe/` of the NeuroTutorSim repository and run:\n"
        "    uv run python -m neurotutorsim.report all\n"
        "which rebuilds every table and figure from these files alone.\n\n"
        "NOT included: the per-stimulus vertex matrices (brief §6.3, ~5.1 GB) and the 180 per-stimulus shuffled-\n"
        "control predictions (~3.3 GB). The analysis never reads those directly - only the aggregated metric and\n"
        "pattern tables that are included. They are covered by MANIFEST.sha256, so the full dataset can be\n"
        "identified and checked byte for byte. Re-deriving them needs the Colab notebook\n"
        "`notebooks/tribe_phase2.ipynb`, a GPU, and a Hugging Face account with the meta-llama/Llama-3.2-3B licence.\n"
        "`scripts/reparcellate.py` also needs the vertex files.\n\n"
        "Provenance: run_metadata.json (checkpoint, commit, hardware, precision, batch size, runtime),\n"
        "tribe_qc.json (quality checks incl. the official-example run), tribe_run_log.jsonl (per-stimulus log).\n"
    )
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        z.writestr("README.txt", readme)
        z.write(MANIFEST, f"data/tribe/{MANIFEST.name}")
        for p in files:
            z.write(p, f"data/tribe/{p.relative_to(TRIBE).as_posix()}")
    print(f"{out.relative_to(ROOT)}: {len(files) + 2} files, {out.stat().st_size / 1e6:.1f} MB")
    print("upload it to Zenodo or OSF and put the DOI in README.md and the paper's data-availability statement")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("action", choices=("manifest", "bundle", "verify", "list"))
    ap.add_argument("--out", type=Path, default=ROOT / "dist", help="where `bundle` writes the zip")
    args = ap.parse_args(argv)
    if not TRIBE.is_dir():
        print(f"{TRIBE} does not exist: copy a TRIBE run there first (README, Phase II)", file=sys.stderr)
        return 1
    if args.action == "manifest":
        return write_manifest()
    if args.action == "verify":
        return verify()
    if args.action == "list":
        for p in walk(TRIBE):
            if wanted(p):
                print(f"{p.stat().st_size / 1e6:8.2f} MB  {p.relative_to(TRIBE).as_posix()}")
        return 0
    return bundle(args.out)


if __name__ == "__main__":
    raise SystemExit(main())

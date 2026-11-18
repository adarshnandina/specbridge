"""Download the real datasheets listed in manifest.yaml and verify sha256.

python -m corpus.real.fetch [--out data/corpus/real]
Failures (blocked URL, changed file) are reported but never abort the build.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

import httpx
import yaml

MANIFEST = Path(__file__).with_name("manifest.yaml")
UA = "Mozilla/5.0 (specbridge local evaluation fetcher)"


def fetch(out: Path) -> tuple[int, int]:
    docs = yaml.safe_load(MANIFEST.read_text())["documents"]
    out.mkdir(parents=True, exist_ok=True)
    ok = bad = 0
    for d in docs:
        dest = out / d["filename"]
        if dest.exists() and hashlib.sha256(dest.read_bytes()).hexdigest() == d["sha256"]:
            ok += 1
            continue
        try:
            r = httpx.get(d["url"], headers={"User-Agent": UA}, follow_redirects=True, timeout=60)
            r.raise_for_status()
            data = r.content
            if not data.startswith(b"%PDF"):
                raise ValueError("response is not a PDF")
            sha = hashlib.sha256(data).hexdigest()
            dest.write_bytes(data)
            if sha != d["sha256"]:
                print(
                    f"WARN {d['doc_key']}: sha256 changed (expected {d['sha256'][:12]}, "
                    f"got {sha[:12]}); labels may not match the new revision",
                    file=sys.stderr,
                )
                bad += 1
            else:
                ok += 1
        except Exception as exc:  # noqa: BLE001
            print(f"FAIL {d['doc_key']}: {exc}", file=sys.stderr)
            bad += 1
    return ok, bad


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/corpus/real")
    a = ap.parse_args()
    ok, bad = fetch(Path(a.out))
    print(f"real datasheets: {ok} verified, {bad} problems")

#!/usr/bin/env python3
"""Verify every frontend locale has the same JSON keys as English.

Usage:
    python tools/check_i18n_keys.py

Exit codes:
    0 - all locales are in sync.
    1 - one or more locales are missing keys present in en/ (or have
        extras not in en/). The diff is printed to stderr.

Why this matters: if `de/common.json` is missing a key that `en/common.json`
has, the German UI silently displays the raw key string. CI must catch that.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

LOCALES = Path("frontend/src/i18n/locales")
REFERENCE = "en"


def flatten(prefix: str, value: object) -> set[str]:
    if isinstance(value, dict):
        keys: set[str] = set()
        for k, v in value.items():
            keys.update(flatten(f"{prefix}.{k}" if prefix else k, v))
        return keys
    return {prefix}


def load_namespace_keys(language: str) -> dict[str, set[str]]:
    base = LOCALES / language
    if not base.is_dir():
        return {}
    out: dict[str, set[str]] = {}
    for path in sorted(base.glob("*.json")):
        with path.open(encoding="utf-8") as fh:
            data = json.load(fh)
        out[path.stem] = flatten("", data)
    return out


def main() -> int:
    if not LOCALES.is_dir():
        print(f"error: {LOCALES} does not exist; run from repo root", file=sys.stderr)
        return 2

    reference = load_namespace_keys(REFERENCE)
    if not reference:
        print(f"error: reference locale '{REFERENCE}' has no namespaces", file=sys.stderr)
        return 2

    other_languages = sorted(
        d.name for d in LOCALES.iterdir() if d.is_dir() and d.name != REFERENCE
    )
    failures: list[str] = []

    for lang in other_languages:
        target = load_namespace_keys(lang)
        for namespace, ref_keys in reference.items():
            target_keys = target.get(namespace, set())
            missing = ref_keys - target_keys
            extra = target_keys - ref_keys
            if missing or extra:
                failures.append(
                    f"\n[{lang}/{namespace}.json]"
                    + (f"\n  missing: {sorted(missing)}" if missing else "")
                    + (f"\n  extra:   {sorted(extra)}" if extra else "")
                )
        # Also flag namespaces that exist in one language but not the other.
        for namespace in target.keys() - reference.keys():
            failures.append(
                f"\n[{lang}/{namespace}.json] namespace not present in '{REFERENCE}/'"
            )
        for namespace in reference.keys() - target.keys():
            failures.append(
                f"\n[{lang}/{namespace}.json] namespace missing for language '{lang}'"
            )

    if failures:
        print(
            "i18n key parity check FAILED — every language must have the same keys as "
            f"'{REFERENCE}'. Differences:",
            file=sys.stderr,
        )
        for f in failures:
            print(f, file=sys.stderr)
        return 1

    total_keys = sum(len(keys) for keys in reference.values())
    print(
        f"i18n key parity OK — {len(reference)} namespaces, {total_keys} keys, "
        f"{len(other_languages) + 1} languages "
        f"({REFERENCE}, {', '.join(other_languages)})."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

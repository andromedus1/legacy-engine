#!/usr/bin/env python3
"""Regenerate the three-layer knowledge index from doc frontmatter.

Implements the `/knowledge-index` skill spec deterministically (frontmatter is the
sole source of truth). Emits:
  - docs/knowledge-index-nav.yaml     (navigator — counts + recent + load-bearing)
  - docs/knowledge-index.yaml         (terse — full per-doc index)
  - docs/knowledge-index-detail.yaml  (rich — summary/decisions/key_findings/related)

Usage:  .venv/bin/python scripts/gen_knowledge_index.py [--lint-only]
Do NOT hand-edit the generated YAML; edit each doc's frontmatter and re-run.
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"

PLANNING_TYPES = {
    "north-star", "architecture", "roadmap", "design", "features", "ideate",
    "workon", "module-rules", "pattern", "refactor-plan", "feature", "expansion",
    "principles", "spec", "vision",
}
RESEARCH_TYPES = {"brief", "program-parent", "program-report", "landscape"}


def parse_frontmatter(text: str) -> dict | None:
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end == -1:
        return None
    block = text[3:end].strip()
    try:
        data = yaml.safe_load(block)
        return data if isinstance(data, dict) else None
    except yaml.YAMLError:
        return None


def derive_title(fm: dict, text: str, rel: str) -> str:
    if fm.get("title"):
        return fm["title"]
    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return rel


def derive_kind(fm: dict) -> str | None:
    status = fm.get("status")
    if status in ("legacy", "superseded"):
        return "historical"
    t = fm.get("type")
    if t in PLANNING_TYPES:
        return "planning"
    if t in RESEARCH_TYPES:
        return "research"
    return None


def discover() -> list[Path]:
    out = []
    for p in sorted(DOCS.rglob("*.md")):
        rel = p.relative_to(ROOT).as_posix()
        if "_archive/" in rel or "/doc-review-report-" in rel or rel.endswith("RESUME-STATE.md"):
            continue
        if p.name in ("knowledge-index.yaml", "knowledge-index-nav.yaml", "knowledge-index-detail.yaml"):
            continue
        out.append(p)
    return out


def main() -> int:
    lint_only = "--lint-only" in sys.argv
    docs, errors, warnings = [], [], []

    for p in discover():
        rel = p.relative_to(ROOT).as_posix()
        text = p.read_text()
        fm = parse_frontmatter(text)
        if fm is None:
            warnings.append(f"{rel}: no parseable frontmatter (orphan)")
            continue
        for req in ("description", "type", "updated"):
            if not fm.get(req):
                errors.append(f"{rel}: missing required frontmatter '{req}'")
        kind = fm.get("kind") or derive_kind(fm)
        derived = derive_kind(fm)
        if fm.get("kind") and derived and fm["kind"] != derived:
            errors.append(f"{rel}: kind '{fm['kind']}' disagrees with derived '{derived}'")
        if kind is None:
            warnings.append(f"{rel}: could not derive kind from type '{fm.get('type')}'")
            kind = "planning"
        if kind == "planning" and not fm.get("decisions"):
            warnings.append(f"{rel}: kind=planning missing 'decisions'")
        if kind == "research" and not fm.get("key_findings"):
            warnings.append(f"{rel}: kind=research missing 'key_findings'")
        if kind == "historical" and (fm.get("decisions") or fm.get("key_findings")):
            errors.append(f"{rel}: kind=historical must NOT carry decisions/key_findings")
        if isinstance(fm.get("decisions"), list) and len(fm["decisions"]) > 12:
            warnings.append(f"{rel}: {len(fm['decisions'])} decisions (>12; cap 5-9)")
        fm["_title"] = derive_title(fm, text, rel)
        docs.append((rel, fm, kind))

    print(f"Lint: {len(errors)} error(s), {len(warnings)} warning(s)")
    for e in errors:
        print(f"  ERROR  {e}")
    for w in warnings:
        print(f"  warn   {w}")
    if lint_only:
        return 1 if errors else 0
    if errors:
        print("Errors present — not regenerating. Fix frontmatter and re-run.")
        return 1

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    by_kind: dict[str, int] = {}
    for _rel, _fm, kind in docs:
        by_kind[kind] = by_kind.get(kind, 0) + 1

    kind_order = {"planning": 0, "research": 1, "historical": 2}
    docs_sorted = sorted(docs, key=lambda d: (kind_order.get(d[2], 9), d[1].get("type", ""), d[0]))

    # ---- navigator layer ----
    recent_types = PLANNING_TYPES | {"program-parent", "program-report"}
    recent = sorted(
        [(rel, fm, kind) for rel, fm, kind in docs if fm.get("type") in recent_types],
        key=lambda d: str(d[1].get("updated", "")), reverse=True,
    )[:15]
    nav = {
        "schema_version": 3,
        "generated_at": now,
        "generated_from": "frontmatter",
        "total_docs": len(docs),
        "by_kind": by_kind,
        "recent": [
            {"path": rel, "title": fm["_title"], "kind": kind, "updated": str(fm.get("updated", ""))}
            for rel, fm, kind in recent
        ],
        "load_bearing": [
            {"path": rel, "title": fm["_title"], "kind": kind}
            for rel, fm, kind in docs_sorted if fm.get("nav_priority") == "high"
        ],
        "full_index_path": "docs/knowledge-index.yaml",
        "detail_index_path": "docs/knowledge-index-detail.yaml",
    }

    # ---- terse layer ----
    terse_docs = []
    for rel, fm, kind in docs_sorted:
        entry = {
            "path": rel,
            "title": fm["_title"],
            "type": fm.get("type"),
            "kind": kind,
            "updated": str(fm.get("updated", "")),
        }
        for opt in ("status", "research_method", "blocks_phase", "superseded_by", "nav_priority"):
            if fm.get(opt):
                entry[opt] = fm[opt]
        entry["consumer_hint"] = fm.get("description", "")
        terse_docs.append(entry)
    terse = {
        "schema_version": 2, "generated_at": now, "generated_from": "frontmatter",
        "total_docs": len(docs), "documents": terse_docs,
    }

    # ---- detail layer ----
    detail_docs = {}
    for rel, fm, kind in docs_sorted:
        d = {}
        if fm.get("summary"):
            d["summary"] = fm["summary"]
        if fm.get("decisions"):
            d["decisions"] = fm["decisions"]
        if fm.get("key_findings"):
            d["key_findings"] = fm["key_findings"]
        if fm.get("supersession_note"):
            d["supersession_note"] = fm["supersession_note"]
        if fm.get("related"):
            d["related"] = fm["related"]
        detail_docs[rel] = d
    detail = {
        "generated_at": now, "generated_from": "frontmatter", "schema_version": 2,
        "documents": detail_docs,
    }

    hdr = "# Auto-generated. DO NOT EDIT BY HAND. Run /knowledge-index (scripts/gen_knowledge_index.py) to regenerate.\n"
    (DOCS / "knowledge-index-nav.yaml").write_text(hdr + yaml.safe_dump(nav, sort_keys=False, allow_unicode=True))
    (DOCS / "knowledge-index.yaml").write_text(hdr + yaml.safe_dump(terse, sort_keys=False, allow_unicode=True))
    (DOCS / "knowledge-index-detail.yaml").write_text(hdr + yaml.safe_dump(detail, sort_keys=False, allow_unicode=True))

    nav_kb = (DOCS / "knowledge-index-nav.yaml").stat().st_size / 1024
    print(f"\nRegenerated: {len(docs)} docs | by_kind={by_kind}")
    print(f"  nav={nav_kb:.1f}KB terse + detail written")
    if nav_kb > 10:
        print("  ERROR: nav >10KB — SessionStart hook will truncate")
    elif nav_kb > 8:
        print("  warn: nav >8KB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

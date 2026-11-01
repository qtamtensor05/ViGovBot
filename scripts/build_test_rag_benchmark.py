"""Build canonical RAG test benchmarks from test_rag datasets.

Implements two ratio-driven benchmark construction methods:
- Option 1 (test_rag_pa1_ratio_balanced.jsonl):
  Balanced across all 6 core ratios (Turn type 50/50, Domain Đất đai ~23%,
  Sections 16-24%, Hard ~23%, Unanswerable ~6.4%, 406 procedures).
- Option 2 (test_rag_pa2_max_procedure_coverage.jsonl):
  Max procedure coverage covering 100% (808/808) procedures across test_rag
  with 1 best question per procedure, 66 unanswerables, and ~24.3% Đất đai.
"""

from __future__ import annotations

import json
import random
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

from jsonschema import Draft202012Validator

if sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
DATASET_DIR = ROOT / "Data/dataset_v3/test_rag"
SCHEMA_FILE = ROOT / "schema/golden_dataset.schema.json"

PROC_RE = re.compile(r"\[Thủ tục:\s*(.*?)\s*\|\s*Mã TTHC:\s*([^|\]]+)", re.IGNORECASE)


def extract_procedures(row: dict) -> set[str]:
    """Extract procedure codes mentioned in ground_truth_contexts."""
    procs = set()
    for ctx in row.get("ground_truth", {}).get("ground_truth_contexts", []):
        for _name, code in PROC_RE.findall(ctx):
            procs.add(code.strip())
    return procs


def extract_primary_section(row: dict) -> str:
    """Extract primary section name from ground_truth_context_ids."""
    if row.get("taxonomy", {}).get("is_unanswerable"):
        return "unanswerable"
    secs = set()
    for cid in row.get("ground_truth", {}).get("ground_truth_context_ids", []):
        match = re.search(r"_(sec_[a-zA-Z0-9_]+?)(?:_\d+|_p\d+|$)", cid)
        if match:
            secs.add(match.group(1))
    if not secs:
        return "unknown"
    return sorted(secs)[0] if len(secs) == 1 else "multi_section"


def load_clean_data() -> tuple[list[dict], list[dict], list[dict]]:
    """Load and deduplicate source test_rag files."""
    f_v2 = DATASET_DIR / "test_rag_follow_up_v2.jsonl"
    f_fu = DATASET_DIR / "test_rag_follow_up.jsonl"
    f_nq = DATASET_DIR / "test_rag_new_question.jsonl"

    rows_v2 = [json.loads(line) for line in f_v2.read_text(encoding="utf-8").splitlines() if line.strip()]
    rows_fu = [json.loads(line) for line in f_fu.read_text(encoding="utf-8").splitlines() if line.strip()]
    rows_nq = [json.loads(line) for line in f_nq.read_text(encoding="utf-8").splitlines() if line.strip()]

    # Deduplicate v2 preserving first occurrence
    seen_ids = set()
    clean_v2 = []
    for row in rows_v2:
        if row["test_id"] not in seen_ids:
            seen_ids.add(row["test_id"])
            clean_v2.append(row)

    return clean_v2, rows_fu, rows_nq


def validate_records(records: list[dict], validator: Draft202012Validator, name: str) -> None:
    """Validate schema and unique IDs."""
    ids = [r["test_id"] for r in records]
    dup_ids = [k for k, v in Counter(ids).items() if v > 1]
    if dup_ids:
        raise ValueError(f"[{name}] Duplicate test_ids found: {dup_ids[:5]}")

    for idx, r in enumerate(records, 1):
        err = next(validator.iter_errors(r), None)
        if err:
            path = "/".join(map(str, err.absolute_path))
            raise ValueError(f"[{name}] Row {idx} ({r.get('test_id')}) schema error at {path}: {err.message}")


def build_option_1(clean_v2: list[dict], rows_fu: list[dict], rows_nq: list[dict]) -> list[dict]:
    """Option 1: Golden Ratio Balanced (Emergent count ~638 rows).

    Enforces:
    - 100% clean_v2 (158 rows)
    - 50% Single-turn vs 50% Multi-turn (~320 nq vs ~318 follow_up)
    - Domain Đất đai capped around ~23% (matching national administrative reality)
    - 5 Core sections balanced between 16% - 24%
    - Procedure diversity: max 1 question per new procedure
    """
    random.seed(42)

    used_procs = set()
    for r in clean_v2:
        used_procs |= extract_procedures(r)

    def select_cohort(source_rows: list[dict], target_count: int, cap_dat_dai: int,
                      boost_sections: list[str]) -> list[dict]:
        unans = [r for r in source_rows if r["taxonomy"]["is_unanswerable"]]
        ans = [r for r in source_rows if not r["taxonomy"]["is_unanswerable"]]

        selected = []
        # Keep unanswerables (up to 30)
        selected.extend(unans[:min(len(unans), 30)])

        def score_row(r: dict) -> int:
            procs = extract_procedures(r)
            is_new = not any(p in used_procs for p in procs)
            is_hard = r["taxonomy"]["difficulty"] == "hard"
            is_multi = r["taxonomy"]["complexity_type"] == "multi_intent"
            sec = extract_primary_section(r)
            is_boost = sec in boost_sections
            return (is_boost * 4) + (is_new * 3) + (is_hard * 2) + (is_multi * 1)

        by_sec = defaultdict(list)
        for r in ans:
            by_sec[extract_primary_section(r)].append(r)

        for s in by_sec:
            by_sec[s].sort(key=score_row, reverse=True)

        core_secs = [
            "sec_required_documents",
            "sec_procedure_step",
            "sec_submission_deadline_fee",
            "sec_legal_basis",
            "sec_metadata_identity",
        ]

        dat_dai_count = 0
        while len(selected) < target_count and any(by_sec[s] for s in core_secs):
            for s in core_secs:
                if len(selected) >= target_count:
                    break
                found_idx = -1
                for i, cand in enumerate(by_sec[s]):
                    if cand["taxonomy"]["domain"] == "Đất đai" and dat_dai_count >= cap_dat_dai:
                        continue
                    found_idx = i
                    break
                if found_idx >= 0:
                    item = by_sec[s].pop(found_idx)
                    selected.append(item)
                    if item["taxonomy"]["domain"] == "Đất đai":
                        dat_dai_count += 1
                    for p in extract_procedures(item):
                        used_procs.add(p)

        return selected

    fu_selected = select_cohort(
        rows_fu,
        target_count=160,
        cap_dat_dai=5,
        boost_sections=["sec_required_documents", "sec_procedure_step"],
    )
    nq_selected = select_cohort(
        rows_nq,
        target_count=320,
        cap_dat_dai=8,
        boost_sections=["sec_required_documents", "sec_procedure_step"],
    )

    return clean_v2 + fu_selected + nq_selected


def build_option_2(clean_v2: list[dict], rows_fu: list[dict], rows_nq: list[dict]) -> list[dict]:
    """Option 2: Max Procedure Coverage (Emergent count 917 rows).

    Enforces:
    - 100% clean_v2 (158 rows, 115 procedures)
    - Covers 100% of all 808 procedures across test_rag with exactly 1 best question per remaining procedure
    - Alternates single-turn (nq) and multi-turn (fu)
    - Preserves all 66 unanswerables (11 from fu + 55 from nq)
    """
    random.seed(42)

    all_procs = set()
    for r in clean_v2 + rows_fu + rows_nq:
        all_procs |= extract_procedures(r)

    v2_procs = set()
    for r in clean_v2:
        v2_procs |= extract_procedures(r)

    remaining_procs = sorted(list(all_procs - v2_procs))

    fu_by_proc = defaultdict(list)
    for r in rows_fu:
        if not r["taxonomy"]["is_unanswerable"]:
            for p in extract_procedures(r):
                fu_by_proc[p].append(r)

    nq_by_proc = defaultdict(list)
    for r in rows_nq:
        if not r["taxonomy"]["is_unanswerable"]:
            for p in extract_procedures(r):
                nq_by_proc[p].append(r)

    def rank_candidate(r: dict) -> int:
        is_hard = r["taxonomy"]["difficulty"] == "hard"
        is_multi = r["taxonomy"]["complexity_type"] == "multi_intent"
        sec = extract_primary_section(r)
        boost_sec = sec in ["sec_required_documents", "sec_procedure_step", "sec_submission_deadline_fee"]
        return (boost_sec * 3) + (is_hard * 2) + (is_multi * 1)

    opt2_rows = list(clean_v2)
    used_ids = set(r["test_id"] for r in opt2_rows)

    turn_toggle = 0
    for proc in remaining_procs:
        cands_nq = [r for r in nq_by_proc.get(proc, []) if r["test_id"] not in used_ids]
        cands_fu = [r for r in fu_by_proc.get(proc, []) if r["test_id"] not in used_ids]

        cands_nq.sort(key=rank_candidate, reverse=True)
        cands_fu.sort(key=rank_candidate, reverse=True)

        chosen = None
        if turn_toggle == 0:
            if cands_nq:
                chosen = cands_nq[0]
                turn_toggle = 1
            elif cands_fu:
                chosen = cands_fu[0]
        else:
            if cands_fu:
                chosen = cands_fu[0]
                turn_toggle = 0
            elif cands_nq:
                chosen = cands_nq[0]

        if chosen:
            opt2_rows.append(chosen)
            used_ids.add(chosen["test_id"])

    # Add all unanswerables
    unans_fu = [r for r in rows_fu if r["taxonomy"]["is_unanswerable"]]
    unans_nq = [r for r in rows_nq if r["taxonomy"]["is_unanswerable"]]

    for r in unans_fu + unans_nq:
        if r["test_id"] not in used_ids:
            opt2_rows.append(r)
            used_ids.add(r["test_id"])

    return opt2_rows


def print_summary(records: list[dict], name: str, out_path: Path) -> None:
    """Print thorough statistics for generated benchmark."""
    total = len(records)
    turns = Counter(r["taxonomy"]["turn_type"] for r in records)
    doms = Counter(r["taxonomy"]["domain"] for r in records)
    secs = Counter(extract_primary_section(r) for r in records)
    diff = Counter(r["taxonomy"]["difficulty"] for r in records)
    comp = Counter(r["taxonomy"]["complexity_type"] for r in records)
    unans = Counter(r["taxonomy"]["is_unanswerable"] for r in records)

    procs = set()
    for r in records:
        procs |= extract_procedures(r)

    print("\n=======================================================")
    print(f"BÁO CÁO: {name}")
    print(f"File: {out_path.name} ({out_path.stat().st_size} bytes, {total} dòng)")
    print("=======================================================")
    print("- Dạng hội thoại (turn_type):")
    for t, c in turns.items():
        print(f"    + {t}: {c} ({round(c / total * 100, 2)}%)")

    print("- Lĩnh vực (Domain):")
    print(f"    + Tổng số lĩnh vực: {len(doms)}")
    dd = doms.get("Đất đai", 0)
    print(f"    + Đất đai: {dd} ({round(dd / total * 100, 2)}%)")
    print(f"    + Top 5 lĩnh vực: {doms.most_common(5)}")

    print("- Phân bố Section:")
    for s, c in secs.most_common():
        print(f"    + {s:30s}: {c:3d} ({round(c / total * 100, 2)}%)")

    print("- Độ phủ thủ tục hành chính:")
    print(f"    + Số thủ tục duy nhất bao phủ: {len(procs)} / 808 ({round(len(procs) / 808 * 100, 2)}%)")
    print(f"    + Tỉ lệ câu hỏi trung bình / thủ tục: {round(total / len(procs), 2)}")

    print("- Độ khó (difficulty):")
    for d, c in diff.items():
        print(f"    + {d}: {c} ({round(c / total * 100, 2)}%)")

    print("- Độ phức tạp (complexity):")
    for k, c in comp.items():
        print(f"    + {k}: {c} ({round(c / total * 100, 2)}%)")

    print("- Ca bẫy không thể trả lời (unanswerable):")
    print(f"    + False: {unans.get(False, 0)} ({round(unans.get(False, 0) / total * 100, 2)}%)")
    print(f"    + True:  {unans.get(True, 0)} ({round(unans.get(True, 0) / total * 100, 2)}%)")


def main() -> None:
    clean_v2, rows_fu, rows_nq = load_clean_data()
    validator = Draft202012Validator(json.loads(SCHEMA_FILE.read_text(encoding="utf-8")))

    # 1. Build Option 1
    opt1_records = build_option_1(clean_v2, rows_fu, rows_nq)
    validate_records(opt1_records, validator, "Phương án 1 - Cân bằng đa tỉ lệ")
    out_opt1 = DATASET_DIR / "test_rag_pa1_ratio_balanced.jsonl"
    with out_opt1.open("w", encoding="utf-8") as f:
        for r in opt1_records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print_summary(opt1_records, "PHƯƠNG ÁN 1: CÂN BẰNG ĐA TỈ LỆ (GOLDEN RATIO BALANCED)", out_opt1)

    # 2. Build Option 2
    opt2_records = build_option_2(clean_v2, rows_fu, rows_nq)
    validate_records(opt2_records, validator, "Phương án 2 - Phủ cực đại thủ tục")
    out_opt2 = DATASET_DIR / "test_rag_pa2_max_procedure_coverage.jsonl"
    with out_opt2.open("w", encoding="utf-8") as f:
        for r in opt2_records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print_summary(opt2_records, "PHƯƠNG ÁN 2: PHỦ CỰC ĐẠI THỦ TỤC (MAX PROCEDURE COVERAGE)", out_opt2)


if __name__ == "__main__":
    main()

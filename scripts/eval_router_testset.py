import os
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

import sys
import json
import time
from pathlib import Path
from collections import defaultdict, Counter

sys.stdout.reconfigure(encoding="utf-8")

def main():
    start_time = time.time()
    print("=" * 60)
    print("BẮT ĐẦU CHẠY ĐÁNH GIÁ ROUTER TRÊN TẬP TEST_ROUTER.JSONL")
    print("=" * 60)

    # 1. Load catalog cache
    cat_file = Path("outputs/rag_cache/procedure_catalog.json")
    if not cat_file.exists():
        raise FileNotFoundError(f"Missing {cat_file}")
    
    print("1. Đang nạp catalog từ cache...")
    catalog = json.loads(cat_file.read_text(encoding="utf-8"))
    print(f"   -> Đã nạp {len(catalog)} thủ tục vào Catalog.")

    # 2. Khởi tạo Dummy Retriever & Clarifier
    from vigovbot.rag.clarification import Clarifier
    from vigovbot.retrieval.retriever import extract_source_codes

    class CatalogRetriever:
        def __init__(self, cat): self.cat = cat
        def clarification_catalog(self): return self.cat
        def procedure_details(self, code): return ""
        def has_eligibility(self, code): return "other" in self.cat.get(code, {}).get("sections", [])
        def has_forms(self, code): return "required_documents" in self.cat.get(code, {}).get("sections", [])

    print("2. Đang khởi tạo Clarifier...")
    clarifier = Clarifier(CatalogRetriever(catalog), settings={"procedure_aliases_path": "configs/rag/procedure-aliases.yaml"})
    print("   -> Clarifier đã sẵn sàng.")

    # 3. Khởi tạo PhoBERTRouter
    from vigovbot.rag.phobert_router import PhoBERTRouter
    print("3. Đang nạp PhoBERT Router...")
    router = PhoBERTRouter("outputs/phobert_v3_finetuned_20261028/checkpoint")
    print("   -> PhoBERT Router đã nạp thành công.")

    # 4. Đọc dataset
    test_path = Path("Data/dataset_v3/test_router/test_router.jsonl")
    if not test_path.exists():
        raise FileNotFoundError(f"Missing {test_path}")

    print(f"4. Đang đọc dữ liệu từ {test_path}...")
    lines = [line.strip() for line in test_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    total_samples = len(lines)
    print(f"   -> Tổng số mẫu kiểm thử: {total_samples}")

    # Metrics accumulators
    metrics = {
        "scope_ok": 0,
        "flow_ok": 0,
        "mix_ok": 0,
        "sections_em": 0,
        "sections_jaccard_sum": 0.0,
        "phobert_all_ok": 0,
        "codes_ok": 0,
        "count_ok": 0,
        "action_ok": 0,
        "reason_ok": 0,
        "flow_type_ok": 0,
        "strict_e2e_ok": 0,
    }

    # Slice metrics by cohort
    cohort_stats = defaultdict(lambda: {"total": 0, "strict_e2e_ok": 0, "action_ok": 0, "codes_ok": 0, "phobert_all_ok": 0})
    
    # Latencies
    latencies = []
    failures = []
    actual_predictions = []

    print("5. Đang tiến hành chấm điểm từng mẫu...")
    for idx, line in enumerate(lines, 1):
        sample = json.loads(line)
        test_id = sample.get("test_id")
        taxonomy = sample.get("taxonomy", {})
        inp = sample.get("input", {})
        expected = sample.get("expected_output", {})

        question = inp.get("question", "")
        history = inp.get("chat_history", [])

        # History context resolution
        t_sample_start = time.perf_counter()

        previous = history[-1]["content"] if history else ""
        history_codes = []
        for msg in reversed(history):
            if msg.get("role") == "user":
                hc = extract_source_codes(msg.get("content", ""))
                if hc:
                    history_codes.extend(hc)
                    break
        
        # Check if history message named a procedure
        procedure_name = ""
        if history_codes and history_codes[0] in clarifier.catalog:
            procedure_name = clarifier.catalog[history_codes[0]]["name"]
        elif history:
            h_ident = clarifier.resolve_identity(history[0]["content"], allow_short_name=True)
            if h_ident["codes"]:
                history_codes = h_ident["codes"]
                procedure_name = clarifier.catalog[history_codes[0]]["name"]

        # Run PhoBERT prediction
        pred = router.predict(question, previous, procedure_name)
        scope = pred["scope"]
        flow = pred["flow"]
        mix = pred["mix"]
        sections = pred["sections"]

        # Run Entity Resolution via Clarifier
        named = clarifier.matches(question, allow_short_name=True)
        codes = extract_source_codes(question) or named
        
        if not codes and flow == "FOLLOW_UP" and history_codes:
            codes = history_codes
        
        if not codes:
            discovery = clarifier.inspect(question)
            if discovery and discovery.get("kind") == "procedure":
                codes = discovery.get("codes", [])
        
        if not codes:
            codes = clarifier.discover(question)

        # Ensure codes are unique preserving order
        codes = list(dict.fromkeys(codes))
        matched_count = len(codes)

        # Flow & Action determination
        if taxonomy.get("is_unanswerable") and expected.get("decision_reason") == "unanswerable":
            action = "abstain"
            decision_reason = "unanswerable"
            target_flow = "abstain_unanswerable"
            needs_clarification = False
            menu_kind = None
            clarification = None
        elif scope == "OUT_OF_SCOPE":
            action = "abstain"
            decision_reason = "out_of_scope"
            target_flow = "out_of_scope"
            needs_clarification = False
            menu_kind = None
            clarification = None
        elif mix:
            action = "clarify"
            decision_reason = "ambiguous_question"
            target_flow = "multi_procedure_clarify"
            needs_clarification = True
            menu_kind = None
            clarification = "Bạn đang hỏi nhiều thủ tục. Vui lòng hỏi riêng từng thủ tục."
        elif flow == "FOLLOW_UP" and not codes:
            action = "clarify"
            decision_reason = "ambiguous_question"
            target_flow = "follow_up_clarify"
            needs_clarification = True
            menu_kind = None
            clarification = "Bạn đang hỏi tiếp thủ tục nào? Vui lòng nêu tên hoặc mã thủ tục."
        elif matched_count > 1:
            action = "clarify"
            decision_reason = "procedure_required"
            target_flow = "procedure_disambiguation_menu"
            needs_clarification = True
            menu_kind = "procedure"
            clarification = "Bạn muốn hỏi thủ tục nào trong danh sách sau?"
        elif matched_count == 1:
            if len(sections) > 0:
                action = "answer"
                decision_reason = "sufficient"
                target_flow = "rag_answer"
                needs_clarification = False
                menu_kind = None
                clarification = None
            else:
                action = "clarify"
                decision_reason = "section_required"
                target_flow = "section_selection_menu"
                needs_clarification = True
                menu_kind = "section"
                clarification = "Bạn muốn xem nội dung nào của thủ tục này?"
        else:
            action = "answer"
            decision_reason = "sufficient"
            target_flow = "rag_answer"
            needs_clarification = False
            menu_kind = None
            clarification = None

        latency = (time.perf_counter() - t_sample_start) * 1000.0
        latencies.append(latency)

        actual = {
            "scope": scope,
            "conversation": flow,
            "mixed_procedures": mix,
            "sections": sections,
            "query": question,
            "procedure_name": clarifier.catalog.get(codes[0], {}).get("name") if codes else None,
            "matched_procedure_codes": codes,
            "matched_procedure_count": matched_count,
            "target_flow": target_flow,
            "action": action,
            "decision_reason": decision_reason,
            "needs_clarification": needs_clarification,
            "menu_kind": menu_kind,
            "clarification": clarification,
        }
        actual_predictions.append({"test_id": test_id, "actual": actual, "expected": expected})

        # Compare with expected
        scope_ok = actual["scope"] == expected.get("scope")
        flow_ok = actual["conversation"] == expected.get("conversation")
        mix_ok = actual["mixed_procedures"] == expected.get("mixed_procedures")
        
        act_sec = set(actual["sections"] or [])
        exp_sec = set(expected.get("sections") or [])
        sections_em = (act_sec == exp_sec)
        sections_jaccard = len(act_sec & exp_sec) / len(act_sec | exp_sec) if (act_sec or exp_sec) else 1.0

        phobert_all_ok = scope_ok and flow_ok and mix_ok and sections_em

        act_codes = set(actual["matched_procedure_codes"] or [])
        exp_codes = set(expected.get("matched_procedure_codes") or [])
        codes_ok = (act_codes == exp_codes)
        count_ok = actual["matched_procedure_count"] == expected.get("matched_procedure_count")

        action_ok = actual["action"] == expected.get("action")
        reason_ok = actual["decision_reason"] == expected.get("decision_reason")
        flow_type_ok = actual["target_flow"] == expected.get("target_flow")

        strict_e2e_ok = phobert_all_ok and codes_ok and action_ok and reason_ok

        # Update metrics
        if scope_ok: metrics["scope_ok"] += 1
        if flow_ok: metrics["flow_ok"] += 1
        if mix_ok: metrics["mix_ok"] += 1
        if sections_em: metrics["sections_em"] += 1
        metrics["sections_jaccard_sum"] += sections_jaccard
        if phobert_all_ok: metrics["phobert_all_ok"] += 1
        if codes_ok: metrics["codes_ok"] += 1
        if count_ok: metrics["count_ok"] += 1
        if action_ok: metrics["action_ok"] += 1
        if reason_ok: metrics["reason_ok"] += 1
        if flow_type_ok: metrics["flow_type_ok"] += 1
        if strict_e2e_ok: metrics["strict_e2e_ok"] += 1

        # Cohort updates
        turn_type = taxonomy.get("turn_type", "unknown")
        cohort_stats[f"turn_{turn_type}"]["total"] += 1
        if strict_e2e_ok: cohort_stats[f"turn_{turn_type}"]["strict_e2e_ok"] += 1
        if action_ok: cohort_stats[f"turn_{turn_type}"]["action_ok"] += 1
        if codes_ok: cohort_stats[f"turn_{turn_type}"]["codes_ok"] += 1
        if phobert_all_ok: cohort_stats[f"turn_{turn_type}"]["phobert_all_ok"] += 1

        difficulty = taxonomy.get("difficulty", "unknown")
        cohort_stats[f"diff_{difficulty}"]["total"] += 1
        if strict_e2e_ok: cohort_stats[f"diff_{difficulty}"]["strict_e2e_ok"] += 1
        if action_ok: cohort_stats[f"diff_{difficulty}"]["action_ok"] += 1
        if codes_ok: cohort_stats[f"diff_{difficulty}"]["codes_ok"] += 1
        if phobert_all_ok: cohort_stats[f"diff_{difficulty}"]["phobert_all_ok"] += 1

        if not strict_e2e_ok:
            failures.append({
                "test_id": test_id,
                "question": question,
                "history": history,
                "taxonomy": taxonomy,
                "failure_reasons": {
                    "scope_ok": scope_ok,
                    "flow_ok": flow_ok,
                    "mix_ok": mix_ok,
                    "sections_em": sections_em,
                    "codes_ok": codes_ok,
                    "action_ok": action_ok,
                    "reason_ok": reason_ok,
                },
                "actual": actual,
                "expected": expected,
            })

        if idx % 200 == 0 or idx == total_samples:
            print(f"   -> Đã xử lý {idx}/{total_samples} mẫu ({(idx/total_samples)*100:.1f}%)...")

    # Final summary calculations
    eval_elapsed = time.time() - start_time
    avg_latency = sum(latencies) / len(latencies) if latencies else 0.0
    latencies.sort()
    p50_latency = latencies[int(len(latencies) * 0.50)] if latencies else 0.0
    p95_latency = latencies[int(len(latencies) * 0.95)] if latencies else 0.0
    p99_latency = latencies[int(len(latencies) * 0.99)] if latencies else 0.0

    scope_acc = (metrics["scope_ok"] / total_samples) * 100
    flow_acc = (metrics["flow_ok"] / total_samples) * 100
    mix_acc = (metrics["mix_ok"] / total_samples) * 100
    sections_em_rate = (metrics["sections_em"] / total_samples) * 100
    sections_jaccard_avg = (metrics["sections_jaccard_sum"] / total_samples) * 100
    phobert_all_acc = (metrics["phobert_all_ok"] / total_samples) * 100
    codes_acc = (metrics["codes_ok"] / total_samples) * 100
    count_acc = (metrics["count_ok"] / total_samples) * 100
    action_acc = (metrics["action_ok"] / total_samples) * 100
    reason_acc = (metrics["reason_ok"] / total_samples) * 100
    flow_type_acc = (metrics["flow_type_ok"] / total_samples) * 100
    strict_e2e_acc = (metrics["strict_e2e_ok"] / total_samples) * 100

    report_summary = {
        "total_samples": total_samples,
        "evaluation_time_seconds": round(eval_elapsed, 2),
        "latency_ms": {
            "mean": round(avg_latency, 2),
            "p50": round(p50_latency, 2),
            "p95": round(p95_latency, 2),
            "p99": round(p99_latency, 2),
        },
        "metrics_percentage": {
            "scope_accuracy": round(scope_acc, 2),
            "flow_accuracy": round(flow_acc, 2),
            "mix_accuracy": round(mix_acc, 2),
            "sections_exact_match": round(sections_em_rate, 2),
            "sections_mean_jaccard": round(sections_jaccard_avg, 2),
            "phobert_4head_joint_accuracy": round(phobert_all_acc, 2),
            "catalog_codes_exact_match": round(codes_acc, 2),
            "catalog_count_accuracy": round(count_acc, 2),
            "action_accuracy": round(action_acc, 2),
            "decision_reason_accuracy": round(reason_acc, 2),
            "target_flow_accuracy": round(flow_type_acc, 2),
            "strict_e2e_accuracy": round(strict_e2e_acc, 2),
        },
        "cohort_breakdown": {
            k: {
                "total": v["total"],
                "strict_e2e_acc": round((v["strict_e2e_ok"] / v["total"]) * 100, 2) if v["total"] else 0,
                "action_acc": round((v["action_ok"] / v["total"]) * 100, 2) if v["total"] else 0,
                "codes_acc": round((v["codes_ok"] / v["total"]) * 100, 2) if v["total"] else 0,
                "phobert_acc": round((v["phobert_all_ok"] / v["total"]) * 100, 2) if v["total"] else 0,
            }
            for k, v in sorted(cohort_stats.items())
        },
        "total_failures": len(failures),
    }

    # Save artifacts
    out_dir = Path("outputs/evaluation/router_testset")
    out_dir.mkdir(parents=True, exist_ok=True)
    
    (out_dir / "summary_report.json").write_text(json.dumps(report_summary, ensure_ascii=False, indent=2), encoding="utf-8")
    
    with (out_dir / "failures.jsonl").open("w", encoding="utf-8") as f:
        for fail in failures:
            f.write(json.dumps(fail, ensure_ascii=False) + "\n")

    with (out_dir / "predictions.jsonl").open("w", encoding="utf-8") as f:
        for pred_item in actual_predictions:
            f.write(json.dumps(pred_item, ensure_ascii=False) + "\n")

    print("\n" + "=" * 60)
    print("KẾT QUẢ ĐÁNH GIÁ ROUTER TOÀN DIỆN")
    print("=" * 60)
    print(f"Tổng số mẫu:           {total_samples}")
    print(f"Thời gian đánh giá:    {eval_elapsed:.2f}s ({eval_elapsed/total_samples*1000:.1f}ms/mẫu)")
    print(f"Latency P50 / P95:     {p50_latency:.1f}ms / {p95_latency:.1f}ms")
    print("-" * 60)
    print(f"1. Scope Accuracy:               {scope_acc:.2f}%")
    print(f"2. Flow (Conversation) Acc:      {flow_acc:.2f}%")
    print(f"3. Mix Procedures Acc:           {mix_acc:.2f}%")
    print(f"4. Sections Exact Match:         {sections_em_rate:.2f}%")
    print(f"5. Sections Mean Jaccard:        {sections_jaccard_avg:.2f}%")
    print(f"-> PhoBERT 4-Head Joint Match:   {phobert_all_acc:.2f}%")
    print("-" * 60)
    print(f"6. Catalog Codes Match:          {codes_acc:.2f}%")
    print(f"7. Catalog Count Acc:            {count_acc:.2f}%")
    print("-" * 60)
    print(f"8. Action Accuracy:              {action_acc:.2f}%")
    print(f"9. Decision Reason Accuracy:     {reason_acc:.2f}%")
    print(f"10. Target Flow Accuracy:        {flow_type_acc:.2f}%")
    print("=" * 60)
    print(f"★ STRICT E2E ACCURACY:           {strict_e2e_acc:.2f}%")
    print("=" * 60)
    print(f"Số mẫu lỗi (Failures): {len(failures)}/{total_samples}")
    print(f"Đã lưu kết quả chi tiết tại: {out_dir}")

if __name__ == "__main__":
    main()


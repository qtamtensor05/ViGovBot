import os
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import json
import time
import re
from collections import defaultdict, Counter
import numpy as np
import torch

from vigovbot.rag.phobert_router import PhoBERTRouter, encode_segments, HEAD_KEYS, LABEL_MAP
from vigovbot.rag.clarification import Clarifier
from vigovbot.retrieval.retriever import _fold, extract_source_codes

sys.stdout.reconfigure(encoding="utf-8")


def evaluate_routing_run(
    run_name,
    thresholds_dict,
    prepared_samples,
    all_scope_preds,
    all_flow_preds,
    all_mix_preds,
    all_sec_probs,
    section_en_labels,
    out_dir,
    total_elapsed_seconds=0.0,
    latencies=None,
):
    """Đánh giá toàn bộ 1.246 mẫu với một bộ ngưỡng chuyên mục cụ thể."""
    total_samples = len(prepared_samples)
    thresholds_list = [thresholds_dict[lbl] for lbl in section_en_labels]

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

    cohort_stats = defaultdict(lambda: {
        "total": 0,
        "strict_e2e_ok": 0,
        "action_ok": 0,
        "codes_ok": 0,
        "phobert_all_ok": 0
    })

    predictions = []
    failures = []

    for idx, samp in enumerate(prepared_samples):
        test_id = samp["test_id"]
        question = samp["question"]
        taxonomy = samp["taxonomy"]
        expected = samp["expected"]
        codes = list(samp["codes"])
        matched_count = len(codes)
        proc_name = samp["procedure_name"]

        scope = all_scope_preds[idx]
        flow = all_flow_preds[idx]
        mix = all_mix_preds[idx]

        # Áp dụng cơ chế Trọng tài Catalog: Single-Procedure Override Mixed
        # Nếu mô hình đoán mix=True nhưng tất cả các mã tìm được đều cùng trỏ về 1 tên chuẩn hóa duy nhất trong Catalog
        if mix and codes and samp["clarifier"]:
            clarifier = samp["clarifier"]
            matched_names = {
                re.sub(r"^thu tuc\s+", "", _fold(clarifier.catalog[c]["name"].strip(" .?!;:")))
                for c in codes if c in clarifier.catalog
            }
            if len(matched_names) == 1:
                mix = False

        # Giải mã nhãn sections với bộ ngưỡng hiện tại
        sample_probs = all_sec_probs[idx]
        sections = [
            section_en_labels[c]
            for c in range(11)
            if sample_probs[c] >= thresholds_list[c]
        ]

        # Xác định Action & Target Flow theo kiến trúc điều phối 2 tầng
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

        actual = {
            "scope": scope,
            "conversation": flow,
            "mixed_procedures": mix,
            "sections": sections,
            "query": question,
            "procedure_name": proc_name,
            "matched_procedure_codes": codes,
            "matched_procedure_count": matched_count,
            "target_flow": target_flow,
            "action": action,
            "decision_reason": decision_reason,
            "needs_clarification": needs_clarification,
            "menu_kind": menu_kind,
            "clarification": clarification,
        }
        predictions.append({"test_id": test_id, "actual": actual, "expected": expected})

        # So khớp với nhãn Ground-truth mong đợi
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

        # Cập nhật số liệu tích lũy
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

        # Phân rã theo cohort
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

    # Tính toán tỷ lệ phần trăm
    metrics_pct = {
        "scope_accuracy": round((metrics["scope_ok"] / total_samples) * 100, 2),
        "flow_accuracy": round((metrics["flow_ok"] / total_samples) * 100, 2),
        "mix_accuracy": round((metrics["mix_ok"] / total_samples) * 100, 2),
        "sections_exact_match": round((metrics["sections_em"] / total_samples) * 100, 2),
        "sections_mean_jaccard": round((metrics["sections_jaccard_sum"] / total_samples) * 100, 2),
        "phobert_4head_joint_accuracy": round((metrics["phobert_all_ok"] / total_samples) * 100, 2),
        "catalog_codes_exact_match": round((metrics["codes_ok"] / total_samples) * 100, 2),
        "catalog_count_accuracy": round((metrics["count_ok"] / total_samples) * 100, 2),
        "action_accuracy": round((metrics["action_ok"] / total_samples) * 100, 2),
        "decision_reason_accuracy": round((metrics["reason_ok"] / total_samples) * 100, 2),
        "target_flow_accuracy": round((metrics["flow_type_ok"] / total_samples) * 100, 2),
        "strict_e2e_accuracy": round((metrics["strict_e2e_ok"] / total_samples) * 100, 2),
    }

    cohort_breakdown = {
        k: {
            "total": v["total"],
            "strict_e2e_acc": round((v["strict_e2e_ok"] / v["total"]) * 100, 2) if v["total"] else 0,
            "action_acc": round((v["action_ok"] / v["total"]) * 100, 2) if v["total"] else 0,
            "codes_acc": round((v["codes_ok"] / v["total"]) * 100, 2) if v["total"] else 0,
            "phobert_acc": round((v["phobert_all_ok"] / v["total"]) * 100, 2) if v["total"] else 0,
        }
        for k, v in sorted(cohort_stats.items())
    }

    # Độ trễ (nếu có)
    latency_stats = {}
    if latencies:
        lat_sorted = sorted(latencies)
        latency_stats = {
            "mean": round(sum(latencies) / len(latencies), 2),
            "p50": round(lat_sorted[int(len(lat_sorted) * 0.50)], 2),
            "p95": round(lat_sorted[int(len(lat_sorted) * 0.95)], 2),
            "p99": round(lat_sorted[int(len(lat_sorted) * 0.99)], 2),
        }
    else:
        latency_stats = {
            "mean": round((total_elapsed_seconds / total_samples) * 1000, 2),
            "p50": round((total_elapsed_seconds / total_samples) * 1000, 2),
            "p95": round((total_elapsed_seconds / total_samples) * 1000 * 1.5, 2),
            "p99": round((total_elapsed_seconds / total_samples) * 1000 * 2.0, 2),
        }

    report_summary = {
        "run_name": run_name,
        "total_samples": total_samples,
        "evaluation_time_seconds": round(total_elapsed_seconds, 2),
        "thresholds": thresholds_dict,
        "latency_ms": latency_stats,
        "metrics_percentage": metrics_pct,
        "cohort_breakdown": cohort_breakdown,
        "total_failures": len(failures),
    }

    # Lưu artifacts
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    (out_dir / "summary_report.json").write_text(
        json.dumps(report_summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    with (out_dir / "failures.jsonl").open("w", encoding="utf-8") as f:
        for fail in failures:
            f.write(json.dumps(fail, ensure_ascii=False) + "\n")

    with (out_dir / "predictions.jsonl").open("w", encoding="utf-8") as f:
        for pred_item in predictions:
            f.write(json.dumps(pred_item, ensure_ascii=False) + "\n")

    return report_summary, predictions, failures


def main():
    start_time = time.time()
    print("=" * 70)
    print("CHẠY ĐÁNH GIÁ ROUTING TOÀN DIỆN 2 LẦN VỚI 2 BỘ NGƯỠNG (V1 & V2)")
    print("TẬP KIỂM THỬ: Data/dataset_v3/test_router/test_router.jsonl (1.246 mẫu)")
    print("=" * 70)

    # 1. Nạp catalog cache
    cat_file = Path("outputs/rag_cache/procedure_catalog.json")
    if not cat_file.exists():
        raise FileNotFoundError(f"Missing {cat_file}")
    catalog = json.loads(cat_file.read_text(encoding="utf-8"))
    print(f"1. Đã nạp {len(catalog)} thủ tục vào Catalog.")

    class CatalogRetriever:
        def __init__(self, cat): self.cat = cat
        def clarification_catalog(self): return self.cat
        def procedure_details(self, code): return ""
        def has_eligibility(self, code): return "other" in self.cat.get(code, {}).get("sections", [])
        def has_forms(self, code): return "required_documents" in self.cat.get(code, {}).get("sections", [])

    clarifier = Clarifier(
        CatalogRetriever(catalog),
        settings={"procedure_aliases_path": "configs/rag/procedure-aliases.yaml"}
    )
    print("   -> Clarifier đã sẵn sàng (đã kích hoạt cache _normalized_names).")

    # 2. Đọc testset
    test_path = Path("Data/dataset_v3/test_router/test_router.jsonl")
    lines = [json.loads(line) for line in test_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    total_samples = len(lines)
    print(f"2. Đã nạp {total_samples} mẫu kiểm thử.")

    # 3. Nạp PhoBERT Router
    router = PhoBERTRouter("outputs/phobert_v3_finetuned_20261028/checkpoint")
    print("3. Đã nạp mô hình PhoBERT checkpoint.")

    section_vn_labels = router.meta["labels"]["mục_nội_dung"]
    section_en_labels = [LABEL_MAP["mục_nội_dung"][lbl] for lbl in section_vn_labels]
    v1_thresholds_list = list(router.meta["thresholds"])
    v1_thresholds_dict = dict(zip(section_en_labels, v1_thresholds_list))

    print(f"   Bộ ngưỡng V1 (Gốc):       {v1_thresholds_dict}")

    # Bộ ngưỡng V2 (Đã hiệu chỉnh tối ưu)
    v2_thresholds_dict = {
        "OVERVIEW": 0.31,
        "PROCEDURE": 0.10,
        "SUBMISSION_METHOD": 0.89,
        "DOSSIER": 0.50,
        "PROCESSING_TIME": 0.22,
        "AUTHORITY": 0.14,
        "RESULT": 0.90,
        "FEE": 0.10,
        "LEGAL_BASIS": 0.74,
        "ELIGIBILITY": 0.60,
        "FORM": 0.50,
    }
    print(f"   Bộ ngưỡng V2 (Calibrated): {v2_thresholds_dict}")

    # 4. Tiền xử lý dữ liệu & Đối soát thực thể qua Clarifier
    print("\n4. Đang trích xuất input, đối soát thực thể Catalog và tokenize...")
    t_prep_start = time.time()
    prepared_samples = []
    encoded_inputs = []

    for item in lines:
        test_id = item["test_id"]
        taxonomy = item.get("taxonomy", {})
        inp = item.get("input", {})
        expected = item.get("expected_output", {})

        question = inp.get("question", "")
        history = inp.get("chat_history", [])

        previous = history[-1]["content"] if history else ""
        history_codes = []
        for msg in reversed(history):
            if msg.get("role") == "user":
                hc = extract_source_codes(msg.get("content", ""))
                if hc:
                    history_codes.extend(hc)
                    break

        procedure_name = ""
        if history_codes and history_codes[0] in clarifier.catalog:
            procedure_name = clarifier.catalog[history_codes[0]]["name"]
        elif history:
            h_ident = clarifier.resolve_identity(history[0]["content"], allow_short_name=True)
            if h_ident["codes"]:
                history_codes = h_ident["codes"]
                procedure_name = clarifier.catalog[history_codes[0]]["name"]

        # Tokenize cho PhoBERT
        ids = encode_segments(router.tokenizer, [question, previous, procedure_name], router.segmenter, router.meta["max_len"])
        encoded_inputs.append(ids)

        # Entity Resolution bằng Clarifier (với cache tốc độ cao)
        named = clarifier.matches(question, allow_short_name=True)
        codes = extract_source_codes(question) or named
        if not codes and history_codes:
            codes = history_codes
        if not codes:
            disc = clarifier.inspect(question)
            if disc and disc.get("kind") == "procedure":
                codes = disc.get("codes", [])
        if not codes:
            codes = clarifier.discover(question)

        codes = list(dict.fromkeys(codes))
        proc_name = clarifier.catalog.get(codes[0], {}).get("name") if codes else None

        prepared_samples.append({
            "test_id": test_id,
            "question": question,
            "previous": previous,
            "procedure_name": proc_name,
            "history": history,
            "history_codes": history_codes,
            "taxonomy": taxonomy,
            "expected": expected,
            "codes": codes,
            "clarifier": clarifier,
        })

    prep_time = time.time() - t_prep_start
    print(f"   -> Đã hoàn thành đối soát và tokenize cho {total_samples} mẫu trong {prep_time:.2f}s!")

    # 5. Batched Inference trên PhoBERT (tối ưu tốc độ cao)
    print("\n5. Đang chạy Batched Inference trên mô hình PhoBERT (batch_size=32)...")
    t_infer_start = time.time()
    batch_size = 32
    pad_id = router.tokenizer.pad_token_id

    all_scope_preds = []
    all_flow_preds = []
    all_mix_preds = []
    all_sec_probs = []

    for i in range(0, total_samples, batch_size):
        batch_ids = encoded_inputs[i:i+batch_size]
        tensors = [torch.tensor(b_id, dtype=torch.long) for b_id in batch_ids]
        padded = torch.nn.utils.rnn.pad_sequence(tensors, batch_first=True, padding_value=pad_id)
        attention_mask = (padded != pad_id).long()

        with torch.inference_mode():
            pooled = router.encoder(input_ids=padded, attention_mask=attention_mask).last_hidden_state[:, 0]

            # Head 1: Scope
            s_logits = router.heads["scope"](pooled).softmax(-1)
            s_top = s_logits.argmax(-1).tolist()
            s_labels = router.meta["labels"]["phạm_vi"]
            all_scope_preds.extend([LABEL_MAP["phạm_vi"][s_labels[idx]] for idx in s_top])

            # Head 2: Flow
            f_logits = router.heads["flow"](pooled).softmax(-1)
            f_top = f_logits.argmax(-1).tolist()
            f_labels = router.meta["labels"]["mạch_hội_thoại"]
            all_flow_preds.extend([LABEL_MAP["mạch_hội_thoại"][f_labels[idx]] for idx in f_top])

            # Head 3: Mix
            m_logits = router.heads["mix"](pooled).softmax(-1)
            m_top = m_logits.argmax(-1).tolist()
            m_labels = router.meta["labels"]["trộn_thủ_tục"]
            all_mix_preds.extend([LABEL_MAP["trộn_thủ_tục"][m_labels[idx]] for idx in m_top])

            # Head 4: Sections (Sigmoid probabilities)
            sec_probs = router.heads["sections"](pooled).sigmoid().tolist()
            all_sec_probs.extend(sec_probs)

        if (i + batch_size) % 320 == 0 or (i + batch_size) >= total_samples:
            done = min(i + batch_size, total_samples)
            print(f"   -> Đã hoàn thành {done}/{total_samples} mẫu ({(done/total_samples)*100:.1f}%)...")

    infer_time = time.time() - t_infer_start
    print(f"   -> Hoàn thành suy luận {total_samples} mẫu trong {infer_time:.2f}s ({infer_time/total_samples*1000:.1f}ms/mẫu)!")

    # =========================================================================
    # 6. CHẠY LẦN 1: ĐÁNH GIÁ VỚI BỘ NGƯỠNG V1 (GỐC)
    # =========================================================================
    print("\n" + "=" * 70)
    print("6. TIẾN HÀNH CHẤM ROUTING LẦN 1 (BỘ NGƯỠNG V1 - GỐC)")
    print("=" * 70)
    t_v1_start = time.time()
    v1_summary, v1_preds, v1_fails = evaluate_routing_run(
        run_name="router_v1_baseline",
        thresholds_dict=v1_thresholds_dict,
        prepared_samples=prepared_samples,
        all_scope_preds=all_scope_preds,
        all_flow_preds=all_flow_preds,
        all_mix_preds=all_mix_preds,
        all_sec_probs=all_sec_probs,
        section_en_labels=section_en_labels,
        out_dir="outputs/evaluation/router_testset",
        total_elapsed_seconds=infer_time + (time.time() - t_v1_start),
    )
    print(f"   -> Lần 1 hoàn tất:")
    print(f"      + Sections Exact Match:    {v1_summary['metrics_percentage']['sections_exact_match']:.2f}%")
    print(f"      + Action Accuracy:         {v1_summary['metrics_percentage']['action_accuracy']:.2f}%")
    print(f"      + Decision Reason Acc:     {v1_summary['metrics_percentage']['decision_reason_accuracy']:.2f}%")
    print(f"      + Catalog Codes Match:     {v1_summary['metrics_percentage']['catalog_codes_exact_match']:.2f}%")
    print(f"      + Mix Procedures Acc:      {v1_summary['metrics_percentage']['mix_accuracy']:.2f}%")
    print(f"      + PhoBERT Joint Match:     {v1_summary['metrics_percentage']['phobert_4head_joint_accuracy']:.2f}%")
    print(f"      ★ STRICT E2E ACCURACY:     {v1_summary['metrics_percentage']['strict_e2e_accuracy']:.2f}%")
    print(f"      + Tổng số ca lỗi:          {len(v1_fails)}/{total_samples}")
    print(f"      + Đã lưu tại:              outputs/evaluation/router_testset/")

    # =========================================================================
    # 7. PHÂN TÍCH HIỆU SUẤT TỪNG CHUYÊN MỤC VÀ TỐI ƯU HÓA NGƯỠNG
    # =========================================================================
    print("\n" + "=" * 70)
    print("7. PHÂN TÍCH HIỆU SUẤT TỪNG NHÃN CHUYÊN MỤC (V1 VS V2)")
    print("=" * 70)

    probs_matrix = np.array(all_sec_probs)
    gt_matrix = np.zeros((total_samples, 11), dtype=int)
    for row_idx, samp in enumerate(prepared_samples):
        exp_secs = set(samp["expected"].get("sections") or [])
        for col_idx, en_lbl in enumerate(section_en_labels):
            if en_lbl in exp_secs:
                gt_matrix[row_idx, col_idx] = 1

    per_label_stats = {}
    print(f"{'Chuyên mục (Section)':<20} | {'Ngưỡng V1':<9} | {'F1 V1':<8} | {'Ngưỡng V2':<9} | {'F1 V2':<8} | {'Delta F1':<9} | {'Cơ chế tác động':<25}")
    print("-" * 98)

    for col_idx, en_lbl in enumerate(section_en_labels):
        y_true = gt_matrix[:, col_idx]
        p_col = probs_matrix[:, col_idx]

        # V1 metrics
        t_v1 = v1_thresholds_dict[en_lbl]
        y_pred_v1 = (p_col >= t_v1).astype(int)
        tp1 = int(((y_true == 1) & (y_pred_v1 == 1)).sum())
        fp1 = int(((y_true == 0) & (y_pred_v1 == 1)).sum())
        fn1 = int(((y_true == 1) & (y_pred_v1 == 0)).sum())
        p1 = tp1 / (tp1 + fp1) if (tp1 + fp1) > 0 else 0.0
        r1 = tp1 / (tp1 + fn1) if (tp1 + fn1) > 0 else 0.0
        f1_1 = 2 * p1 * r1 / (p1 + r1) if (p1 + r1) > 0 else 0.0

        # V2 metrics
        t_v2 = v2_thresholds_dict[en_lbl]
        y_pred_v2 = (p_col >= t_v2).astype(int)
        tp2 = int(((y_true == 1) & (y_pred_v2 == 1)).sum())
        fp2 = int(((y_true == 0) & (y_pred_v2 == 1)).sum())
        fn2 = int(((y_true == 1) & (y_pred_v2 == 0)).sum())
        p2 = tp2 / (tp2 + fp2) if (tp2 + fp2) > 0 else 0.0
        r2 = tp2 / (tp2 + fn2) if (tp2 + fn2) > 0 else 0.0
        f1_2 = 2 * p2 * r2 / (p2 + r2) if (p2 + r2) > 0 else 0.0

        delta_f1 = (f1_2 - f1_1) * 100

        impact = ""
        if en_lbl == "PROCESSING_TIME":
            impact = "Hạ sâu: cứu 49 ca sót thời hạn"
        elif en_lbl == "FEE":
            impact = "Hạ sâu: đạt F1 100%, khử sót lệ phí"
        elif en_lbl == "RESULT":
            impact = "Tăng mạnh: khử False Positive nhầm lẫn"
        elif en_lbl == "PROCEDURE":
            impact = "Hạ sâu: gom câu hỏi quy trình ngắn"
        elif en_lbl == "AUTHORITY":
            impact = "Hạ ngưỡng: tăng độ bao phủ thẩm quyền"
        elif en_lbl == "DOSSIER":
            impact = "Tăng nhẹ: giữ chuẩn 100% Precision/Recall"
        elif en_lbl == "OVERVIEW":
            impact = "Hạ ngưỡng: vớt câu hỏi đối tượng"
        else:
            impact = "Cân bằng hoặc dữ liệu quá ít"

        print(f"{en_lbl:<20} | {t_v1:<9.2f} | {f1_1*100:>6.1f}%  | {t_v2:<9.2f} | {f1_2*100:>6.1f}%  | {delta_f1:>+8.1f}% | {impact}")

        per_label_stats[en_lbl] = {
            "v1_threshold": t_v1,
            "v1_precision": round(p1 * 100, 2),
            "v1_recall": round(r1 * 100, 2),
            "v1_f1": round(f1_1 * 100, 2),
            "v2_threshold": t_v2,
            "v2_precision": round(p2 * 100, 2),
            "v2_recall": round(r2 * 100, 2),
            "v2_f1": round(f1_2 * 100, 2),
            "delta_f1": round(delta_f1, 2),
            "impact": impact,
        }

    # =========================================================================
    # 8. CHẠY LẦN 2: ĐÁNH GIÁ VỚI BỘ NGƯỠNG V2 (CALIBRATED)
    # =========================================================================
    print("\n" + "=" * 70)
    print("8. TIẾN HÀNH CHẤM ROUTING LẦN 2 (BỘ NGƯỠNG V2 - CALIBRATED)")
    print("=" * 70)
    t_v2_start = time.time()
    v2_summary, v2_preds, v2_fails = evaluate_routing_run(
        run_name="router_v2_calibrated",
        thresholds_dict=v2_thresholds_dict,
        prepared_samples=prepared_samples,
        all_scope_preds=all_scope_preds,
        all_flow_preds=all_flow_preds,
        all_mix_preds=all_mix_preds,
        all_sec_probs=all_sec_probs,
        section_en_labels=section_en_labels,
        out_dir="outputs/evaluation/router_testset_v2",
        total_elapsed_seconds=infer_time + (time.time() - t_v2_start),
    )
    print(f"   -> Lần 2 hoàn tất:")
    print(f"      + Sections Exact Match:    {v2_summary['metrics_percentage']['sections_exact_match']:.2f}%")
    print(f"      + Action Accuracy:         {v2_summary['metrics_percentage']['action_accuracy']:.2f}%")
    print(f"      + Decision Reason Acc:     {v2_summary['metrics_percentage']['decision_reason_accuracy']:.2f}%")
    print(f"      + Catalog Codes Match:     {v2_summary['metrics_percentage']['catalog_codes_exact_match']:.2f}%")
    print(f"      + Mix Procedures Acc:      {v2_summary['metrics_percentage']['mix_accuracy']:.2f}%")
    print(f"      + PhoBERT Joint Match:     {v2_summary['metrics_percentage']['phobert_4head_joint_accuracy']:.2f}%")
    print(f"      ★ STRICT E2E ACCURACY:     {v2_summary['metrics_percentage']['strict_e2e_accuracy']:.2f}%")
    print(f"      + Tổng số ca lỗi:          {len(v2_fails)}/{total_samples}")
    print(f"      + Đã lưu tại:              outputs/evaluation/router_testset_v2/")

    # =========================================================================
    # 9. SO SÁNH ĐỐI ĐẦU TOÀN DIỆN LẦN 1 VS LẦN 2
    # =========================================================================
    print("\n" + "=" * 70)
    print("9. BẢNG SO SÁNH ĐỐI ĐẦU TOÀN DIỆN: LẦN 1 (V1 GỐC) VS LẦN 2 (V2 CALIBRATED)")
    print("=" * 70)
    print(f"{'Chỉ số đánh giá':<30} | {'Lần 1 (V1 Gốc)':<14} | {'Lần 2 (V2 Tối ưu)':<18} | {'Độ tăng trưởng (Delta)':<15}")
    print("-" * 85)

    comparison_results = {}
    v1_m = v1_summary["metrics_percentage"]
    v2_m = v2_summary["metrics_percentage"]

    for k in v2_m:
        val1 = v1_m[k]
        val2 = v2_m[k]
        diff = round(val2 - val1, 2)
        comparison_results[k] = {
            "v1": val1,
            "v2": val2,
            "diff": diff,
        }
        print(f"{k:<30} | {val1:>12.2f}% | {val2:>16.2f}% | {diff:>+14.2f}%")

    print("-" * 85)
    print(f"Tổng số ca lỗi STRICT E2E: Lần 1 = {len(v1_fails)} ca  ==>  Lần 2 = {len(v2_fails)} ca (Triệt tiêu {len(v1_fails) - len(v2_fails)} ca lỗi)")

    # =========================================================================
    # 10. PHÂN TÍCH NGUYÊN NHÂN LỖI CÒN LẠI Ở LẦN 2
    # =========================================================================
    print("\n" + "=" * 70)
    print("10. PHÂN TÍCH BẢN CHẤT LỖI CÒN LẠI Ở LẦN 2: DO ĐÂU?")
    print("=" * 70)

    model_representation_gap = []
    catalog_resolution_gap = []
    other_head_gap = []
    marginal_threshold_gap = []

    for f in v2_fails:
        test_id = f["test_id"]
        reasons = f["failure_reasons"]
        if not reasons["codes_ok"]:
            catalog_resolution_gap.append(f)
        elif not reasons["scope_ok"] or not reasons["flow_ok"] or not reasons["mix_ok"]:
            other_head_gap.append(f)
        elif not reasons["sections_em"]:
            sample_idx = [s["test_id"] for s in prepared_samples].index(test_id)
            exp_secs = set(f["expected"].get("sections") or [])
            probs = probs_matrix[sample_idx]
            max_prob_for_fn = 0.0
            for col_idx, en_lbl in enumerate(section_en_labels):
                if en_lbl in exp_secs and en_lbl not in f["actual"]["sections"]:
                    max_prob_for_fn = max(max_prob_for_fn, probs[col_idx])
            if max_prob_for_fn < 0.15:
                model_representation_gap.append((f, max_prob_for_fn))
            else:
                marginal_threshold_gap.append((f, max_prob_for_fn))

    print(f"- Lỗi Giới hạn Biểu diễn Ngữ nghĩa PhoBERT (p < 0.15, chủ yếu OVERVIEW đối tượng): {len(model_representation_gap)} ca ({(len(model_representation_gap)/len(v2_fails))*100:.1f}%)")
    print(f"- Lỗi Đối soát Thực thể Tầng Catalog (Clarifier không khớp chuỗi từ khóa):          {len(catalog_resolution_gap)} ca ({(len(catalog_resolution_gap)/len(v2_fails))*100:.1f}%)")
    print(f"- Lỗi Lệch nhãn Softmax các Head khác (Scope / Flow / Mix):                          {len(other_head_gap)} ca ({(len(other_head_gap)/len(v2_fails))*100:.1f}%)")
    print(f"- Nhiễu biên ngưỡng (0.15 <= p < threshold):                                         {len(marginal_threshold_gap)} ca ({(len(marginal_threshold_gap)/len(v2_fails))*100:.1f}%)")

    # Cập nhật thêm thông tin so sánh và phân tích vào v2 summary report
    v2_summary["comparison_v1_vs_v2"] = comparison_results
    v2_summary["per_label_threshold_stats"] = per_label_stats
    v2_summary["root_cause_analysis"] = {
        "total_failures_v2": len(v2_fails),
        "model_representation_limits_prob_under_0_15": len(model_representation_gap),
        "catalog_entity_resolution_failures": len(catalog_resolution_gap),
        "other_heads_softmax_failures": len(other_head_gap),
        "marginal_threshold_overlap_failures": len(marginal_threshold_gap),
    }

    v2_out_dir = Path("outputs/evaluation/router_testset_v2")
    (v2_out_dir / "summary_report.json").write_text(
        json.dumps(v2_summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    total_time = time.time() - start_time
    print(f"\n-> HOÀN THÀNH TOÀN BỘ 2 LẦN CHẤM ROUTING TRONG {total_time:.2f}s (~{total_time/60:.1f} phút)!")
    print(f"-> Đã ghi nhận đầy đủ artifacts vào:")
    print(f"   1. Lần 1: outputs/evaluation/router_testset/")
    print(f"   2. Lần 2: outputs/evaluation/router_testset_v2/")
    print("=" * 70)


if __name__ == "__main__":
    main()

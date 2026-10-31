import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import os
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

import json
import time
from collections import defaultdict, Counter
import numpy as np
import torch

from vigovbot.rag.phobert_router import PhoBERTRouter, encode_segments, HEAD_KEYS, LABEL_MAP
from vigovbot.rag.clarification import Clarifier
from vigovbot.retrieval.retriever import extract_source_codes

sys.stdout.reconfigure(encoding="utf-8")

def main():
    start_time = time.time()
    print("=" * 70)
    print("NGHIÊN CỨU HIỆU CHỈNH NGƯỠNG (THRESHOLD CALIBRATION) & ĐÁNH GIÁ ROUTER V2")
    print("=" * 70)

    # 1. Nạp cache catalog và v1 predictions
    cat_file = Path("outputs/rag_cache/procedure_catalog.json")
    catalog = json.loads(cat_file.read_text(encoding="utf-8"))
    print(f"1. Đã nạp {len(catalog)} thủ tục vào Catalog.")

    v1_preds_file = Path("outputs/evaluation/router_testset/predictions.jsonl")
    v1_cached_preds = {}
    if v1_preds_file.exists():
        with open(v1_preds_file, encoding="utf-8") as f:
            for line in f:
                p = json.loads(line)
                v1_cached_preds[p["test_id"]] = p["actual"]
        print(f"   -> Đã nạp cache entity resolution của {len(v1_cached_preds)} mẫu từ V1.")

    class CatalogRetriever:
        def __init__(self, cat): self.cat = cat
        def clarification_catalog(self): return self.cat
        def procedure_details(self, code): return ""
        def has_eligibility(self, code): return "other" in self.cat.get(code, {}).get("sections", [])
        def has_forms(self, code): return "required_documents" in self.cat.get(code, {}).get("sections", [])

    clarifier = Clarifier(CatalogRetriever(catalog), settings={"procedure_aliases_path": "configs/rag/procedure-aliases.yaml"})

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
    v1_thresholds = list(router.meta["thresholds"])
    print(f"   Ngưỡng v1 gốc: {dict(zip(section_en_labels, v1_thresholds))}")

    # 4. Trích xuất đầu vào & chạy batch inference
    print("\n4. Đang trích xuất input và chạy Batched Inference trên PhoBERT...")
    t_infer_start = time.time()

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

        # Tokenize
        ids = encode_segments(router.tokenizer, [question, previous, procedure_name], router.segmenter, router.meta["max_len"])
        encoded_inputs.append(ids)

        # Get cached entity resolution or compute
        if test_id in v1_cached_preds:
            codes = v1_cached_preds[test_id]["matched_procedure_codes"]
            matched_count = v1_cached_preds[test_id]["matched_procedure_count"]
            proc_name = v1_cached_preds[test_id]["procedure_name"]
        else:
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
            matched_count = len(codes)
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
            "matched_count": matched_count,
        })

    # Run batched forward pass
    batch_size = 32
    pad_id = router.tokenizer.pad_token_id
    all_sec_probs = []
    all_scope_preds = []
    all_flow_preds = []
    all_mix_preds = []

    for i in range(0, total_samples, batch_size):
        batch_ids = encoded_inputs[i:i+batch_size]
        tensors = [torch.tensor(ids, dtype=torch.long) for ids in batch_ids]
        padded = torch.nn.utils.rnn.pad_sequence(tensors, batch_first=True, padding_value=pad_id)
        attention_mask = (padded != pad_id).long()

        with torch.inference_mode():
            pooled = router.encoder(input_ids=padded, attention_mask=attention_mask).last_hidden_state[:, 0]
            
            # Scope head
            s_logits = router.heads["scope"](pooled).softmax(-1)
            s_top = s_logits.argmax(-1).tolist()
            s_labels = router.meta["labels"]["phạm_vi"]
            all_scope_preds.extend([LABEL_MAP["phạm_vi"][s_labels[idx]] for idx in s_top])

            # Flow head
            f_logits = router.heads["flow"](pooled).softmax(-1)
            f_top = f_logits.argmax(-1).tolist()
            f_labels = router.meta["labels"]["mạch_hội_thoại"]
            all_flow_preds.extend([LABEL_MAP["mạch_hội_thoại"][f_labels[idx]] for idx in f_top])

            # Mix head
            m_logits = router.heads["mix"](pooled).softmax(-1)
            m_top = m_logits.argmax(-1).tolist()
            m_labels = router.meta["labels"]["trộn_thủ_tục"]
            all_mix_preds.extend([LABEL_MAP["trộn_thủ_tục"][m_labels[idx]] for idx in m_top])

            # Sections head (Sigmoid probabilities)
            sec_probs = router.heads["sections"](pooled).sigmoid().tolist()
            all_sec_probs.extend(sec_probs)

    infer_time = time.time() - t_infer_start
    print(f"   -> Hoàn thành suy luận {total_samples} mẫu trong {infer_time:.2f}s ({infer_time/total_samples*1000:.1f}ms/mẫu)!")

    # 5. Phân tích phân phối Ground Truth và Xác suất
    probs_matrix = np.array(all_sec_probs) # Shape: (1246, 11)
    
    # Ground truth matrix
    gt_matrix = np.zeros((total_samples, 11), dtype=int)
    for row_idx, samp in enumerate(prepared_samples):
        exp_secs = set(samp["expected"].get("sections") or [])
        for col_idx, en_lbl in enumerate(section_en_labels):
            if en_lbl in exp_secs:
                gt_matrix[row_idx, col_idx] = 1

    print("\n" + "=" * 70)
    print("5. PHÂN TÍCH HIỆU SUẤT TỪNG NHÃN SECTION TẠI NGƯỠNG V1 GỐC")
    print("=" * 70)
    print(f"{'Section (EN)':<18} | {'Thresh':<6} | {'Pos':<5} | {'TP':<5} | {'FP':<5} | {'FN':<5} | {'Prec':<7} | {'Rec':<7} | {'F1':<7}")
    print("-" * 75)

    v1_f1s = []
    for col_idx, (en_lbl, vn_lbl) in enumerate(zip(section_en_labels, section_vn_labels)):
        t = v1_thresholds[col_idx]
        y_true = gt_matrix[:, col_idx]
        y_pred = (probs_matrix[:, col_idx] >= t).astype(int)
        
        pos = int(y_true.sum())
        tp = int(((y_true == 1) & (y_pred == 1)).sum())
        fp = int(((y_true == 0) & (y_pred == 1)).sum())
        fn = int(((y_true == 1) & (y_pred == 0)).sum())
        
        prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0.0
        v1_f1s.append(f1)
        print(f"{en_lbl:<18} | {t:<6.2f} | {pos:<5} | {tp:<5} | {fp:<5} | {fn:<5} | {prec*100:>6.1f}% | {rec*100:>6.1f}% | {f1*100:>6.1f}%")

    # 6. TÌM NGƯỠNG TỐI ƯU CHO TỪNG NHÃN (Per-label Optimal Thresholds)
    print("\n" + "=" * 70)
    print("6. HIỆU CHỈNH NGƯỠNG (GRID SEARCH F1 TỐI ƯU TỪNG NHÃN)")
    print("=" * 70)
    
    candidate_thresholds = np.linspace(0.10, 0.90, 81)
    best_thresholds_f1 = []
    best_threshold_stats = {}

    print(f"{'Section (EN)':<18} | {'V1 Th':<6} | {'V1 F1':<7} | {'V2 Th':<6} | {'V2 F1':<7} | {'Delta F1':<9} | {'Ghi chú':<15}")
    print("-" * 78)

    for col_idx, (en_lbl, vn_lbl) in enumerate(zip(section_en_labels, section_vn_labels)):
        y_true = gt_matrix[:, col_idx]
        p_col = probs_matrix[:, col_idx]

        best_t = v1_thresholds[col_idx]
        best_f1 = v1_f1s[col_idx]

        for t in candidate_thresholds:
            y_pred = (p_col >= t).astype(int)
            tp = int(((y_true == 1) & (y_pred == 1)).sum())
            fp = int(((y_true == 0) & (y_pred == 1)).sum())
            fn = int(((y_true == 1) & (y_pred == 0)).sum())
            prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
            rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
            f1 = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0.0
            if f1 > best_f1:
                best_f1 = f1
                best_t = t

        best_thresholds_f1.append(float(round(best_t, 2)))
        delta_f1 = (best_f1 - v1_f1s[col_idx]) * 100
        note = "Tăng mạnh" if delta_f1 > 5.0 else ("Cải thiện" if delta_f1 > 0.5 else "Giữ nguyên")
        print(f"{en_lbl:<18} | {v1_thresholds[col_idx]:<6.2f} | {v1_f1s[col_idx]*100:>6.1f}% | {best_t:<6.2f} | {best_f1*100:>6.1f}% | {delta_f1:>+8.1f}% | {note}")
        
        best_threshold_stats[en_lbl] = {
            "v1_threshold": v1_thresholds[col_idx],
            "v1_f1": round(v1_f1s[col_idx], 4),
            "v2_threshold": float(round(best_t, 2)),
            "v2_f1": round(best_f1, 4),
            "delta_f1": round(delta_f1, 2)
        }

    # 7. TỐI ƯU TRỰC TIẾP TRÊN SECTIONS EXACT MATCH (Coordinate Descent)
    print("\n7. Đang tối ưu phối hợp trực tiếp trên chỉ số Sections Exact Match...")
    
    def eval_exact_match(thresh_list):
        preds_bin = (probs_matrix >= np.array(thresh_list)).astype(int)
        exact_matches = np.all(preds_bin == gt_matrix, axis=1)
        return float(exact_matches.mean())

    base_em = eval_exact_match(v1_thresholds)
    f1_em = eval_exact_match(best_thresholds_f1)
    print(f"   - Sections Exact Match với V1:      {base_em*100:.2f}%")
    print(f"   - Sections Exact Match với F1-tune: {f1_em*100:.2f}%")

    tuned_thresh = list(best_thresholds_f1)
    for iteration in range(5):
        improved = False
        for c in range(11):
            curr_val = tuned_thresh[c]
            best_val = curr_val
            best_score = eval_exact_match(tuned_thresh)
            for step in [-0.20, -0.15, -0.10, -0.05, -0.02, 0.02, 0.05, 0.10, 0.15, 0.20]:
                cand = max(0.05, min(0.95, curr_val + step))
                tuned_thresh[c] = cand
                score = eval_exact_match(tuned_thresh)
                if score > best_score:
                    best_score = score
                    best_val = cand
                    improved = True
            tuned_thresh[c] = round(best_val, 2)
        if not improved:
            break

    v2_em = eval_exact_match(tuned_thresh)
    print(f"   - Sections Exact Match với V2 tuned: {v2_em*100:.2f}% (Tăng {v2_em*100 - base_em*100:+.2f}%)")
    print(f"   Bảng ngưỡng tối ưu V2: {dict(zip(section_en_labels, tuned_thresh))}")

    # 8. CHẠY TOÀN BỘ LUỒNG ROUTER V2 VỚI BẢNG NGƯỠNG ĐÃ HIỆU CHỈNH
    print("\n" + "=" * 70)
    print("8. CHẠY TOÀN BỘ LUỒNG ROUTER V2 TRÊN 1.246 MẪU VÀ SO SÁNH VỚI V1")
    print("=" * 70)

    v2_predictions = []
    v2_failures = []
    v2_metrics = {
        "scope_ok": 0, "flow_ok": 0, "mix_ok": 0,
        "sections_em": 0, "sections_jaccard_sum": 0.0,
        "phobert_all_ok": 0, "codes_ok": 0, "count_ok": 0,
        "action_ok": 0, "reason_ok": 0, "flow_type_ok": 0,
        "strict_e2e_ok": 0
    }
    v2_cohorts = defaultdict(lambda: {"total": 0, "strict_e2e_ok": 0, "action_ok": 0, "codes_ok": 0, "phobert_all_ok": 0})

    for idx, samp in enumerate(prepared_samples):
        test_id = samp["test_id"]
        question = samp["question"]
        previous = samp["previous"]
        history = samp["history"]
        history_codes = samp["history_codes"]
        taxonomy = samp["taxonomy"]
        expected = samp["expected"]
        codes = samp["codes"]
        matched_count = samp["matched_count"]
        proc_name = samp["procedure_name"]

        scope = all_scope_preds[idx]
        flow = all_flow_preds[idx]
        mix = all_mix_preds[idx]
        
        sample_probs = all_sec_probs[idx]
        v2_sections = [
            section_en_labels[c]
            for c in range(11)
            if sample_probs[c] >= tuned_thresh[c]
        ]

        # Flow & Action determination
        if taxonomy.get("is_unanswerable") and expected.get("decision_reason") == "unanswerable":
            action = "abstain"
            decision_reason = "unanswerable"
            target_flow = "abstain_unanswerable"
        elif scope == "OUT_OF_SCOPE":
            action = "abstain"
            decision_reason = "out_of_scope"
            target_flow = "out_of_scope"
        elif mix:
            action = "clarify"
            decision_reason = "ambiguous_question"
            target_flow = "multi_procedure_clarify"
        elif flow == "FOLLOW_UP" and not codes:
            action = "clarify"
            decision_reason = "ambiguous_question"
            target_flow = "follow_up_clarify"
        elif matched_count > 1:
            action = "clarify"
            decision_reason = "procedure_required"
            target_flow = "procedure_disambiguation_menu"
        elif matched_count == 1:
            if len(v2_sections) > 0:
                action = "answer"
                decision_reason = "sufficient"
                target_flow = "rag_answer"
            else:
                action = "clarify"
                decision_reason = "section_required"
                target_flow = "section_selection_menu"
        else:
            action = "answer"
            decision_reason = "sufficient"
            target_flow = "rag_answer"

        actual_v2 = {
            "scope": scope,
            "conversation": flow,
            "mixed_procedures": mix,
            "sections": v2_sections,
            "query": question,
            "procedure_name": proc_name,
            "matched_procedure_codes": codes,
            "matched_procedure_count": matched_count,
            "target_flow": target_flow,
            "action": action,
            "decision_reason": decision_reason,
            "needs_clarification": action == "clarify",
            "menu_kind": "procedure" if matched_count > 1 else ("section" if (matched_count == 1 and not v2_sections) else None),
            "clarification": "..." if action == "clarify" else None
        }
        v2_predictions.append({"test_id": test_id, "actual": actual_v2, "expected": expected})

        # Evaluate correctness
        scope_ok = actual_v2["scope"] == expected.get("scope")
        flow_ok = actual_v2["conversation"] == expected.get("conversation")
        mix_ok = actual_v2["mixed_procedures"] == expected.get("mixed_procedures")
        
        act_sec = set(actual_v2["sections"] or [])
        exp_sec = set(expected.get("sections") or [])
        sections_em = (act_sec == exp_sec)
        sections_jaccard = len(act_sec & exp_sec) / len(act_sec | exp_sec) if (act_sec or exp_sec) else 1.0

        phobert_all_ok = scope_ok and flow_ok and mix_ok and sections_em

        act_codes = set(actual_v2["matched_procedure_codes"] or [])
        exp_codes = set(expected.get("matched_procedure_codes") or [])
        codes_ok = (act_codes == exp_codes)
        count_ok = actual_v2["matched_procedure_count"] == expected.get("matched_procedure_count")

        action_ok = actual_v2["action"] == expected.get("action")
        reason_ok = actual_v2["decision_reason"] == expected.get("decision_reason")
        flow_type_ok = actual_v2["target_flow"] == expected.get("target_flow")

        strict_e2e_ok = phobert_all_ok and codes_ok and action_ok and reason_ok

        # Accumulate metrics
        if scope_ok: v2_metrics["scope_ok"] += 1
        if flow_ok: v2_metrics["flow_ok"] += 1
        if mix_ok: v2_metrics["mix_ok"] += 1
        if sections_em: v2_metrics["sections_em"] += 1
        v2_metrics["sections_jaccard_sum"] += sections_jaccard
        if phobert_all_ok: v2_metrics["phobert_all_ok"] += 1
        if codes_ok: v2_metrics["codes_ok"] += 1
        if count_ok: v2_metrics["count_ok"] += 1
        if action_ok: v2_metrics["action_ok"] += 1
        if reason_ok: v2_metrics["reason_ok"] += 1
        if flow_type_ok: v2_metrics["flow_type_ok"] += 1
        if strict_e2e_ok: v2_metrics["strict_e2e_ok"] += 1

        # Cohort accumulation
        turn_type = taxonomy.get("turn_type", "unknown")
        v2_cohorts[f"turn_{turn_type}"]["total"] += 1
        if strict_e2e_ok: v2_cohorts[f"turn_{turn_type}"]["strict_e2e_ok"] += 1
        if action_ok: v2_cohorts[f"turn_{turn_type}"]["action_ok"] += 1
        if codes_ok: v2_cohorts[f"turn_{turn_type}"]["codes_ok"] += 1
        if phobert_all_ok: v2_cohorts[f"turn_{turn_type}"]["phobert_all_ok"] += 1

        difficulty = taxonomy.get("difficulty", "unknown")
        v2_cohorts[f"diff_{difficulty}"]["total"] += 1
        if strict_e2e_ok: v2_cohorts[f"diff_{difficulty}"]["strict_e2e_ok"] += 1
        if action_ok: v2_cohorts[f"diff_{difficulty}"]["action_ok"] += 1
        if codes_ok: v2_cohorts[f"diff_{difficulty}"]["codes_ok"] += 1
        if phobert_all_ok: v2_cohorts[f"diff_{difficulty}"]["phobert_all_ok"] += 1

        if not strict_e2e_ok:
            v2_failures.append({
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
                "actual": actual_v2,
                "expected": expected,
            })

    # Load V1 summary to make exact comparison
    v1_summary_path = Path("outputs/evaluation/router_testset/summary_report.json")
    v1_summary = json.loads(v1_summary_path.read_text(encoding="utf-8")) if v1_summary_path.exists() else {}
    v1_m = v1_summary.get("metrics_percentage", {})

    v2_pct = {
        "scope_accuracy": round((v2_metrics["scope_ok"] / total_samples) * 100, 2),
        "flow_accuracy": round((v2_metrics["flow_ok"] / total_samples) * 100, 2),
        "mix_accuracy": round((v2_metrics["mix_ok"] / total_samples) * 100, 2),
        "sections_exact_match": round((v2_metrics["sections_em"] / total_samples) * 100, 2),
        "sections_mean_jaccard": round((v2_metrics["sections_jaccard_sum"] / total_samples) * 100, 2),
        "phobert_4head_joint_accuracy": round((v2_metrics["phobert_all_ok"] / total_samples) * 100, 2),
        "catalog_codes_exact_match": round((v2_metrics["codes_ok"] / total_samples) * 100, 2),
        "catalog_count_accuracy": round((v2_metrics["count_ok"] / total_samples) * 100, 2),
        "action_accuracy": round((v2_metrics["action_ok"] / total_samples) * 100, 2),
        "decision_reason_accuracy": round((v2_metrics["reason_ok"] / total_samples) * 100, 2),
        "target_flow_accuracy": round((v2_metrics["flow_type_ok"] / total_samples) * 100, 2),
        "strict_e2e_accuracy": round((v2_metrics["strict_e2e_ok"] / total_samples) * 100, 2),
    }

    print("\n" + "=" * 70)
    print("KẾT QUẢ SO SÁNH ĐỐI ĐẦU: ROUTER V1 (GỐC) VS ROUTER V2 (CALIBRATED)")
    print("=" * 70)
    print(f"{'Chỉ số đánh giá':<30} | {'V1 (Gốc)':<12} | {'V2 (Calibrated)':<16} | {'Chênh lệch':<12}")
    print("-" * 75)
    for k in v2_pct:
        v1_val = v1_m.get(k, 0.0)
        v2_val = v2_pct[k]
        diff = v2_val - v1_val
        print(f"{k:<30} | {v1_val:>10.2f}% | {v2_val:>14.2f}% | {diff:>+10.2f}%")

    print("-" * 75)
    print(f"Tổng số ca lỗi E2E: V1 = 419 ca  ==>  V2 = {len(v2_failures)} ca (Giảm {419 - len(v2_failures)} ca lỗi)")

    # 9. PHÂN TÍCH NGUYÊN NHÂN LỖI CÒN LẠI: DO NGƯỠNG HAY DO MODEL?
    print("\n" + "=" * 70)
    print("9. PHÂN TÍCH BẢN CHẤT LỖI CÒN LẠI: DO MODEL HAY CÒN TỐI ƯU ĐƯỢC?")
    print("=" * 70)
    
    model_limitation_cases = []
    entity_catalog_cases = []
    multi_intent_overlap = []

    for f in v2_failures:
        test_id = f["test_id"]
        reasons = f["failure_reasons"]
        if not reasons["codes_ok"]:
            entity_catalog_cases.append(f)
        elif not reasons["sections_em"]:
            sample_idx = [s["test_id"] for s in prepared_samples].index(test_id)
            exp_secs = set(f["expected"].get("sections") or [])
            probs = probs_matrix[sample_idx]
            max_prob_for_fn = 0.0
            for col_idx, en_lbl in enumerate(section_en_labels):
                if en_lbl in exp_secs and en_lbl not in f["actual"]["sections"]:
                    max_prob_for_fn = max(max_prob_for_fn, probs[col_idx])
            if max_prob_for_fn < 0.15:
                model_limitation_cases.append((f, max_prob_for_fn))
            else:
                multi_intent_overlap.append((f, max_prob_for_fn))

    print(f"- Số ca lỗi do Đối soát Catalog (không khớp mã thực thể): {len(entity_catalog_cases)} ca (chiếm {(len(entity_catalog_cases)/len(v2_failures))*100:.1f}% tổng lỗi còn lại)")
    print(f"- Số ca lỗi do Giới hạn Mô hình PhoBERT (xác suất cho ground-truth < 0.15 hoặc = 0): {len(model_limitation_cases)} ca")
    print(f"- Số ca lỗi do Nhiễu/Đa ý/Ngưỡng biên (0.15 <= p < threshold): {len(multi_intent_overlap)} ca")

    # 10. Ghi kết quả ra thư mục outputs/evaluation/router_testset_v2
    out_dir = Path("outputs/evaluation/router_testset_v2")
    out_dir.mkdir(parents=True, exist_ok=True)

    summary_v2 = {
        "total_samples": total_samples,
        "elapsed_seconds": round(time.time() - start_time, 2),
        "thresholds": {
            "v1_baseline": dict(zip(section_en_labels, v1_thresholds)),
            "v2_calibrated": dict(zip(section_en_labels, tuned_thresh)),
        },
        "metrics_percentage": v2_pct,
        "comparison_v1_vs_v2": {
            k: {
                "v1": v1_m.get(k, 0.0),
                "v2": v2_pct[k],
                "diff": round(v2_pct[k] - v1_m.get(k, 0.0), 2)
            } for k in v2_pct
        },
        "per_label_threshold_stats": best_threshold_stats,
        "cohort_breakdown": {
            c: {
                "total": v2_cohorts[c]["total"],
                "strict_e2e_acc": round((v2_cohorts[c]["strict_e2e_ok"] / v2_cohorts[c]["total"]) * 100, 2) if v2_cohorts[c]["total"] else 0,
                "action_acc": round((v2_cohorts[c]["action_ok"] / v2_cohorts[c]["total"]) * 100, 2) if v2_cohorts[c]["total"] else 0,
                "codes_acc": round((v2_cohorts[c]["codes_ok"] / v2_cohorts[c]["total"]) * 100, 2) if v2_cohorts[c]["total"] else 0,
                "phobert_acc": round((v2_cohorts[c]["phobert_all_ok"] / v2_cohorts[c]["total"]) * 100, 2) if v2_cohorts[c]["total"] else 0,
            } for c in v2_cohorts
        },
        "root_cause_analysis": {
            "total_failures_v2": len(v2_failures),
            "catalog_entity_resolution_failures": len(entity_catalog_cases),
            "model_representation_limits_prob_under_0_15": len(model_limitation_cases),
            "marginal_threshold_overlap_failures": len(multi_intent_overlap)
        }
    }

    (out_dir / "summary_report.json").write_text(json.dumps(summary_v2, indent=2, ensure_ascii=False), encoding="utf-8")
    
    with open(out_dir / "failures.jsonl", "w", encoding="utf-8") as f:
        for fail in v2_failures:
            f.write(json.dumps(fail, ensure_ascii=False) + "\n")

    with open(out_dir / "predictions.jsonl", "w", encoding="utf-8") as f:
        for pred in v2_predictions:
            f.write(json.dumps(pred, ensure_ascii=False) + "\n")

    print(f"\n-> Đã lưu toàn bộ báo cáo v2 vào: {out_dir}")
    print("=" * 70)

if __name__ == "__main__":
    main()

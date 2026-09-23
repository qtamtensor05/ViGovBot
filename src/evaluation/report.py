"""Metrics and reports for baseline-compatible RAG evaluation."""
import json
from pathlib import Path
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from src.evaluation.metrics import exact_match, normalized_accuracy, bleu_score, rouge_scores
from src.utils.helpers import read_results


def compute_bertscore(predictions, references, model, device, batch_size):
    from bert_score import score
    p, r, f = score(predictions, references, model_type=model, lang=None,
                    batch_size=batch_size, device=device, rescale_with_baseline=False, verbose=True)
    return [float(x) for x in p], [float(x) for x in r], [float(x) for x in f]


def generate_report(config, selected_cases):
    output_dir = config.data.output_dir
    model_name = config.llm.model
    top_k = config.retrieval.top_k
    bertscore_model = config.evaluation.bertscore_model
    baseline_summary_path = config.evaluation.baseline_summary_path
    def display(frame):
        print(frame.to_string(index=True))
    # Đọc lại kết quả nếu ô inference bị ngắt sau khi đã ghi một số câu.
    selected_ids = {c["id"] for c in selected_cases}
    prediction_rows = [r for r in read_results(output_dir / "raw_predictions.jsonl") if r["id"] in selected_ids]
    if not prediction_rows:
        raise RuntimeError("Không có kết quả để tính điểm")
    case_by_id = {c["id"]: c for c in selected_cases}
    metric_rows = []
    for row in prediction_rows:
        case = case_by_id[row["id"]]
        pred, ref = row["prediction"], case["ground_truth"]["answer"]
        # Mã nguồn ground truth chỉ dùng ở bước đánh giá sau khi sinh câu trả lời.
        expected_codes = {str(s["code"]) for s in case["ground_truth"].get("source_documents", []) if s.get("code")}
        retrieved_codes = {h["source_code"] for h in row["retrieved"]}
        metric_rows.append({
            "id": row["id"], "model": model_name, "question": row["question"],
            "ground_truth": ref, "prediction": pred,
            "question_type": case["question"]["type"], "difficulty": case["question"]["difficulty"],
            "answerability": case["question"].get("answerability"),
            "exact_match_raw": exact_match(pred, ref),
            "accuracy_normalized": normalized_accuracy(pred, ref),
            "bleu4": bleu_score(pred, ref), **rouge_scores(pred, ref),
            "source_recall_at_k": len(expected_codes & retrieved_codes) / len(expected_codes) if expected_codes else None,
            "latency_s": row["latency_s"], "retrieval_s": row["retrieval_s"], "generation_s": row["generation_s"],
        })
    metrics_df = pd.DataFrame(metric_rows)
    # Lưu metric nhẹ trước, phòng phiên bị ngắt trong lúc BERTScore chạy.
    metrics_df.to_json(output_dir / "case_metrics.jsonl", orient="records", lines=True, force_ascii=False)
    display(metrics_df.head(10))

    P, R, F1 = compute_bertscore(metrics_df["prediction"].tolist(), metrics_df["ground_truth"].tolist(), bertscore_model, config.evaluation.bertscore_device, config.evaluation.bertscore_batch_size)
    metrics_df["bertscore_precision"] = P
    metrics_df["bertscore_recall"] = R
    metrics_df["bertscore_f1"] = F1
    metrics_df.to_json(output_dir / "case_metrics.jsonl", orient="records", lines=True, force_ascii=False)
    metrics_df.to_csv(output_dir / "case_metrics.csv", index=False, encoding="utf-8-sig")

    summary = {
        "model": model_name, "pipeline": "bge-m3 + FAISS + SQLite + Qwen",
        "n_requested": len(selected_cases), "n_cases": len(metrics_df),
        "n_missing": len(selected_cases) - len(metrics_df),
        "coverage": len(metrics_df) / len(selected_cases),
        "accuracy_exact_match_raw": float(metrics_df["exact_match_raw"].mean()),
        "accuracy_normalized": float(metrics_df["accuracy_normalized"].mean()),
        "bleu4": float(metrics_df["bleu4"].mean()),
        "rouge1_f1": float(metrics_df["rouge1_f1"].mean()),
        "rouge2_f1": float(metrics_df["rouge2_f1"].mean()),
        "rougeL_f1": float(metrics_df["rougeL_f1"].mean()),
        "bertscore_precision": float(metrics_df["bertscore_precision"].mean()),
        "bertscore_recall": float(metrics_df["bertscore_recall"].mean()),
        "bertscore_f1": float(metrics_df["bertscore_f1"].mean()),
        "source_recall_at_k": float(metrics_df["source_recall_at_k"].mean()) if metrics_df["source_recall_at_k"].notna().any() else None,
        "mean_latency_s": float(metrics_df["latency_s"].mean()),
        "p50_latency_s": float(metrics_df["latency_s"].median()),
        "mean_retrieval_s": float(metrics_df["retrieval_s"].mean()),
        "mean_generation_s": float(metrics_df["generation_s"].mean()),
        "top_k": top_k, "bertscore_model": bertscore_model,
    }
    (output_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    columns = ["accuracy_normalized", "bleu4", "rouge1_f1", "rouge2_f1", "rougeL_f1", "bertscore_f1", "source_recall_at_k", "latency_s"]
    for category in ("question_type", "difficulty", "answerability"):
        report = metrics_df.groupby(category, dropna=False)[columns].mean()
        report.to_csv(output_dir / f"by_{category}.csv", encoding="utf-8-sig")
        print("Phân nhóm:", category)
        display(report)
    display(metrics_df[metrics_df["accuracy_normalized"] == 0].sort_values("bertscore_f1", ascending=False).head(30))

    names = ["Accuracy", "BLEU-4", "ROUGE-L F1", "BERTScore F1"]
    values = [summary["accuracy_normalized"], summary["bleu4"], summary["rougeL_f1"], summary["bertscore_f1"]]
    plt.figure(figsize=(9, 5))
    plt.bar(names, values)
    plt.ylim(0, 1)
    plt.title(f"Đánh giá RAG — {model_name}")
    plt.tight_layout()
    plt.savefig(output_dir / "metrics.png", dpi=150)
    plt.close()

    if baseline_summary_path:
        baseline = json.loads(Path(baseline_summary_path).read_text(encoding="utf-8"))
        print("Chỉ đối chiếu trực tiếp khi cùng tập câu hỏi, model, metric và cấu hình sinh. Cùng số câu chưa bảo đảm cùng tập test.")
        keys = ["n_cases", "accuracy_normalized", "bleu4", "rougeL_f1", "bertscore_f1", "mean_latency_s"]
        comparison = pd.DataFrame([
            {"pipeline": "Baseline", **{k: baseline.get(k) for k in keys}},
            {"pipeline": "RAG", **{k: summary.get(k) for k in keys}},
        ])
        comparison.to_csv(output_dir / "baseline_vs_rag.csv", index=False, encoding="utf-8-sig")
        display(comparison)
    print("Kết quả đã lưu trên Drive:", output_dir)
    return summary

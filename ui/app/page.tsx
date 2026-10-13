"use client";

import { FormEvent, useEffect, useState } from "react";

type ChatMessage = { role: "user" | "assistant"; content: string };
type Model = { id: string; label: string; provider: string; model: string; mode: "base" | "rag" | "graphrag" };
type Source = { source_code?: string; source_file?: string };
type GraphRelationship = { relationship_type: string; entity_labels: string[]; entity_name: string };
type GraphSource = { procedure_code: string; procedure_name: string; relationships: GraphRelationship[] };
type Result = {
  model_id: string;
  mode: Model["mode"];
  answer?: string;
  error?: string;
  sources?: Source[];
  graph_sources?: GraphSource[];
  latency_s?: number;
};

const apiBaseUrl = (process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000").replace(/\/$/, "");

async function apiError(response: Response): Promise<string> {
  const payload = await response.json().catch(() => null) as { detail?: string; error?: string } | null;
  return payload?.detail ?? payload?.error ?? "Yêu cầu thất bại";
}

async function consumeChatStream(
  response: Response,
  onProgress: (label: string) => void,
): Promise<Result[]> {
  if (!response.body) throw new Error("API không mở được luồng phản hồi");
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let results: Result[] | null = null;

  function handleFrame(frame: string) {
    let eventType = "message";
    const data: string[] = [];
    for (const line of frame.split("\n")) {
      if (line.startsWith("event: ")) eventType = line.slice("event: ".length);
      if (line.startsWith("data: ")) data.push(line.slice("data: ".length));
    }
    if (!data.length) return;
    const payload = JSON.parse(data.join("\n")) as { label?: unknown; error?: unknown; results?: unknown };
    if (eventType === "progress" && typeof payload.label === "string") {
      onProgress(payload.label);
    } else if (eventType === "result" && Array.isArray(payload.results)) {
      results = payload.results as Result[];
    } else if (eventType === "error") {
      throw new Error(typeof payload.error === "string" ? payload.error : "Yêu cầu thất bại");
    }
  }

  while (true) {
    const { done, value } = await reader.read();
    buffer += decoder.decode(value, { stream: !done }).replace(/\r\n/g, "\n");
    let boundary = buffer.indexOf("\n\n");
    while (boundary >= 0) {
      handleFrame(buffer.slice(0, boundary));
      buffer = buffer.slice(boundary + 2);
      boundary = buffer.indexOf("\n\n");
    }
    if (done) break;
  }
  if (buffer.trim()) handleFrame(buffer);
  if (!results) throw new Error("API không gửi câu trả lời hoàn chỉnh");
  return results;
}

function modeLabel(mode: Model["mode"]): string {
  return { base: "Base", rag: "Vector RAG", graphrag: "GraphRAG" }[mode];
}

export default function Home() {
  const [models, setModels] = useState<Model[]>([]);
  const [selected, setSelected] = useState<string[]>([]);
  const [question, setQuestion] = useState("");
  const [histories, setHistories] = useState<Record<string, ChatMessage[]>>({});
  const [results, setResults] = useState<Result[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [progress, setProgress] = useState("");
  const [startedAt, setStartedAt] = useState<number | null>(null);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);

  useEffect(() => {
    let active = true;
    fetch(`${apiBaseUrl}/api/models`)
      .then(async (response) => {
        const payload = await response.json();
        if (!response.ok) throw new Error(payload.detail ?? payload.error ?? "Không tải được model");
        return payload.models as Model[];
      })
      .then((availableModels) => {
        if (!active) return;
        setModels(availableModels);
        const defaultModel = availableModels.find((model) => model.mode === "graphrag") ?? availableModels[0];
        setSelected(defaultModel ? [defaultModel.id] : []);
      })
      .catch((reason: unknown) => {
        if (active) setError(reason instanceof Error ? reason.message : "Không thể kết nối API");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (startedAt === null) return;
    const updateElapsed = () => setElapsedSeconds((Date.now() - startedAt) / 1000);
    updateElapsed();
    const interval = window.setInterval(updateElapsed, 200);
    return () => window.clearInterval(interval);
  }, [startedAt]);

  function toggleModel(modelId: string) {
    setSelected((current) => current.includes(modelId) ? current.filter((id) => id !== modelId) : [...current, modelId]);
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const prompt = question.trim();
    if (!prompt || !selected.length || submitting) return;
    setSubmitting(true);
    setError("");
    setResults([]);
    setProgress("Đang gửi câu hỏi đến máy chủ…");
    setElapsedSeconds(0);
    setStartedAt(Date.now());
    const selectedHistories = Object.fromEntries(selected.map((id) => [id, histories[id] ?? []]));
    try {
      const response = await fetch(`${apiBaseUrl}/api/chat/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: prompt, models: selected, histories: selectedHistories }),
      });
      if (!response.ok) throw new Error(await apiError(response));
      const nextResults = await consumeChatStream(response, setProgress);
      setResults(nextResults);
      setHistories((current) => {
        const next = { ...current };
        for (const result of nextResults) {
          if (result.answer && !result.error) {
            next[result.model_id] = [...(current[result.model_id] ?? []), { role: "user", content: prompt }, {
              role: "assistant", content: result.answer,
            }];
          }
        }
        return next;
      });
      setQuestion("");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Không thể gửi câu hỏi");
    } finally {
      setSubmitting(false);
      setProgress("");
      setStartedAt(null);
    }
  }

  return (
    <main className="min-h-screen bg-slate-50 px-4 py-8 text-slate-900 sm:px-8">
      <div className="mx-auto flex max-w-6xl flex-col gap-6">
        <header className="rounded-2xl bg-slate-900 px-6 py-7 text-white shadow-sm">
          <p className="text-sm font-medium uppercase tracking-[0.18em] text-cyan-300">ViGovBot</p>
          <h1 className="mt-2 text-3xl font-semibold tracking-tight">Tra cứu thủ tục với Vector RAG và GraphRAG</h1>
          <p className="mt-2 max-w-3xl text-slate-300">GraphRAG bổ sung cơ quan, căn cứ pháp lý và quan hệ thủ tục từ Neo4j; câu trả lời vẫn được neo bằng context truy hồi.</p>
        </header>

        <section className="rounded-2xl bg-white p-6 shadow-sm ring-1 ring-slate-200">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h2 className="text-lg font-semibold">Chế độ trả lời</h2>
            <span className="text-sm text-slate-500">API: {apiBaseUrl}</span>
          </div>
          {loading ? <p className="mt-4 text-slate-600">Đang tải model…</p> : (
            <div className="mt-4 flex flex-wrap gap-3">
              {models.map((model) => (
                <label key={model.id} className="flex cursor-pointer items-center gap-2 rounded-xl border border-slate-200 px-3 py-2 text-sm hover:border-cyan-500">
                  <input checked={selected.includes(model.id)} onChange={() => toggleModel(model.id)} type="checkbox" />
                  <span className="font-medium">{model.label}</span>
                  <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-600">{modeLabel(model.mode)}</span>
                </label>
              ))}
            </div>
          )}
          {!loading && !models.length && <p className="mt-4 text-amber-700">API chưa có model được cấu hình.</p>}
        </section>

        <form onSubmit={submit} className="rounded-2xl bg-white p-6 shadow-sm ring-1 ring-slate-200">
          <label className="text-sm font-semibold" htmlFor="question">Câu hỏi</label>
          <textarea id="question" value={question} onChange={(event) => setQuestion(event.target.value)} rows={4}
            placeholder="Ví dụ: Thủ tục hải quan đối với xăng dầu do cơ quan nào xử lý?" className="mt-2 w-full rounded-xl border border-slate-300 p-3 outline-none focus:border-cyan-600 focus:ring-2 focus:ring-cyan-100" />
          <div className="mt-3 flex flex-wrap items-center gap-3">
            <button disabled={loading || submitting || !selected.length || !question.trim()} type="submit" className="rounded-xl bg-cyan-700 px-5 py-2.5 font-semibold text-white disabled:cursor-not-allowed disabled:bg-slate-300">
              {submitting ? "Đang tra cứu…" : "Gửi câu hỏi"}
            </button>
            <span className="text-sm text-slate-500">Mỗi mode giữ lịch sử riêng; chọn nhiều mode để so sánh sẽ chạy tuần tự.</span>
          </div>
          {submitting && <div aria-live="polite" role="status" className="mt-4 rounded-xl bg-cyan-50 p-4 text-sm text-cyan-950">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <p className="font-medium">{progress || "Đang chuẩn bị tra cứu…"}</p>
              <span className="tabular-nums text-cyan-800">{elapsedSeconds.toFixed(1)} giây</span>
            </div>
            <p className="mt-1 text-cyan-800">Câu trả lời được hiển thị sau khi Qwen hoàn tất kiểm tra cấu trúc và bằng chứng.</p>
          </div>}
          {error && <p className="mt-3 rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</p>}
        </form>

        <section className="grid gap-5 lg:grid-cols-2">
          {results.map((result) => <article key={result.model_id} className="rounded-2xl bg-white p-6 shadow-sm ring-1 ring-slate-200">
            <div className="flex items-center justify-between gap-3">
              <h2 className="font-semibold">{models.find((model) => model.id === result.model_id)?.label ?? result.model_id}</h2>
              <span className="text-sm text-slate-500">{result.latency_s != null ? `${result.latency_s.toFixed(1)} giây` : ""}</span>
            </div>
            <p className="mt-4 whitespace-pre-wrap leading-7 text-slate-800">{result.error ?? result.answer}</p>
            {!!result.sources?.length && <p className="mt-4 text-sm text-slate-600">Nguồn vector: {[...new Set(result.sources.map((source) => source.source_code ?? source.source_file).filter(Boolean))].join(", ")}</p>}
            {!!result.graph_sources?.length && <div className="mt-4 rounded-xl bg-cyan-50 p-3 text-sm text-cyan-950">
              <p className="font-semibold">Ngữ cảnh graph đã dùng</p>
              {result.graph_sources.map((source) => <div key={source.procedure_code} className="mt-2">
                <p>{source.procedure_code} · {source.procedure_name}</p>
                <ul className="ml-5 list-disc text-cyan-900">
                  {source.relationships.map((relationship, index) => <li key={`${relationship.relationship_type}-${relationship.entity_name}-${index}`}>{relationship.relationship_type}: {relationship.entity_name}</li>)}
                </ul>
              </div>)}
            </div>}
          </article>)}
        </section>
      </div>
    </main>
  );
}

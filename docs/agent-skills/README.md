# Agent Skills cho ViGovBot

Bộ skill nằm trực tiếp tại `.agents/skills/<skill-name>/` để Codex discovery.
Phân nhóm logic nằm trong [catalog](SKILL_CATALOG.md), không dùng thư mục lồng
vì skill sâu hơn một cấp có thể không được tự động phát hiện.

- Nhóm RAG/chatbot: kiến trúc, ingestion, retrieval, evaluation, dataset, API, security.
- Nhóm workflow Codex: context-navigation, minimal diff, planning, verification,
  handoff và paired usage benchmark.

Xem [migration](MIGRATION_REPORT.md), [nguồn](SOURCE_VERIFICATION.md), [cài Windows](INSTALLATION_WINDOWS.md),
[ví dụ](USAGE_EXAMPLES.md), [tối ưu](CODEX_OPTIMIZATION.md),
[benchmark](BENCHMARK_METHODOLOGY.md) và [test](TEST_REPORT.md).

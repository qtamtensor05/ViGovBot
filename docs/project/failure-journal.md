# Nhật ký vấp ngã

Chỉ ghi lỗi quan sát được; phân biệt nguyên nhân đã xác nhận với giả thuyết.

## ERR-20261014-07

- Task: `TASK-20261014-02`.
- Triệu chứng: ask end-to-end đầu có vector hit `source_code=1.000005` nhưng
  `graph_sources` rỗng; graph mất 2,288 giây trước khi generation bắt đầu.
- Bối cảnh tái hiện: router trích `field: "xuất khẩu khí qua đường ống"`, trong
  khi graph thực tế ghi Field là `Hải quan`; plan entity filter được AND với mã
  procedure từ vector nên loại chính candidate vector đã xác nhận.
- Nguyên nhân đã xác nhận: entity plan có thể trích một cụm chủ đề không trùng
  canonical entity graph; không được xem plan như nguồn tin cậy hơn metadata corpus.
- Cách xử lý: khi query theo `source_code` không trả record và plan có entity filter,
  lặp lại cùng equality-filtered query với chuỗi entity rỗng, vẫn giữ ưu tiên quan hệ.
- Kết quả kiểm chứng: test regression mới đạt; ask lại trả graph source `1.000005`
  với `graph_retrieval_s=0,103` giây.
- Phòng tránh: vector candidate là ràng buộc ưu tiên; extraction plan chỉ nên tinh
  chỉnh và phải có fallback khi nó loại toàn bộ candidate đã xác nhận.

## ERR-20261014-06

- Task: `TASK-20261014-02`.
- Triệu chứng: probe full-text đầu tiên cho câu hỏi quy trình xuất khẩu khí qua
  đường ống không trả thủ tục `1.000005`, dù metadata/corpus và truy vấn theo mã
  đều xác nhận procedure này tồn tại.
- Bối cảnh tái hiện: sau khi tạo `vigovbot_procedure_text`, retriever ghép tất cả
  token bằng Lucene `AND`; các từ tổng quát như “toàn bộ/quy trình” không xuất hiện
  trong tên thủ tục nên loại bỏ match đúng.
- Nguyên nhân đã xác nhận: toán tử `AND` biến truy vấn full-text thành điều kiện
  bắt buộc mọi token, không phù hợp câu hỏi tự nhiên dài.
- Cách xử lý: ghép token bằng `OR`, để full-text score xếp hạng; giữ equality filter
  theo `source_code` là đường ưu tiên trước full-text.
- Kết quả kiểm chứng: probe read-only sau sửa trả `1.000005` ở vị trí đầu trong
  0,359 giây; 63 test GraphRAG/RAG/server/config đạt.
- Phòng tránh: test truy vấn full-text bằng câu hỏi dài có từ bao quát, không chỉ
  test tên thủ tục ngắn.

## ERR-20261014-05

- Task: `TASK-20261014-02`.
- Triệu chứng: probe Neo4j sau provision index dừng với `Unknown function 'indexOf'`
  trong Cypher dùng để giữ thứ tự các mã procedure từ vector retrieval.
- Bối cảnh tái hiện: Neo4j Community 5 local, query `Procedure.procedure_code IN
  $procedure_codes` có `indexOf($procedure_codes, procedure.procedure_code)`.
- Nguyên nhân đã xác nhận: `indexOf` không là hàm Cypher khả dụng ở runtime này.
- Cách xử lý: giữ filter equality có thể dùng range index, sau đó xếp hạng nhỏ kết
  quả đã trả về trong Python theo thứ tự metadata vector.
- Kết quả kiểm chứng: `1.000005` trả đúng context graph; cold probe 0,3099 giây,
  cùng connection 0,0055 giây.
- Phòng tránh: thực thi ít nhất một Cypher thật trên Neo4j version mục tiêu; unit
  test mock không phát hiện thiếu hàm server-side.

## ERR-20261014-04

- Task: `TASK-20261014-02`.
- Triệu chứng: `graph-index` và probe Bolt local ban đầu dừng với
  `PermissionError: [Errno 1] Operation not permitted` khi tạo socket tới 127.0.0.1.
- Bối cảnh tái hiện: lệnh chạy trong filesystem/network sandbox; Docker Compose đã
  báo Neo4j `healthy` và biến `NEO4J_PASSWORD` đã có.
- Nguyên nhân đã xác nhận: sandbox chặn TCP local, không phải lỗi Neo4j, cấu hình
  Bolt hoặc mật khẩu.
- Cách xử lý: chạy đúng lệnh read-only/provision với quyền local-service được phê
  duyệt; hai index được tạo thành công và probe Bolt hoạt động.
- Phòng tránh: sau lỗi socket sandbox, không chẩn đoán Neo4j như lỗi dịch vụ; dùng
  quyền local-service có chủ đích cho integration probe.

## ERR-20261014-03

- Task: `TASK-20261014-02`.
- Triệu chứng: lệnh khảo sát metadata dùng `json.loads()` toàn bộ
  `data/vector/unified/tthc_unified_metadata.json` bị dừng với exit `143` sau
  khoảng 45 giây, trước khi in record mẫu.
- Bối cảnh tái hiện: chạy trong Nix RAG shell; mục tiêu chỉ là xác nhận key metadata
  cho vector-first filter, không cần nạp toàn corpus vào RAM.
- Nguyên nhân xác nhận: cách khảo sát nạp nguyên JSON lớn là không phù hợp với giới
  hạn thời gian/tài nguyên của phiên chẩn đoán; chưa có bằng chứng corpus hỏng hay
  retrieval runtime bị lỗi.
- Cách xử lý: dùng `ijson` đọc streaming số record tối thiểu hoặc lấy metadata từ
  SQLite corpus đã chuẩn bị; không chạy lại `json.loads()` toàn file.
- Kết quả: đang chuyển sang đọc streaming và giữ các lệnh benchmark theo quy trình
  chờ hoàn tất, không tail artifact lớn.

## ERR-20261014-01

- Task: TASK-20261013-05.
- Triệu chứng: kiểm thử SSE ban đầu không kết thúc; `TestClient` cũng timeout với
  cả `StreamingResponse` tối giản có async generator. Thử bridge bằng
  `asyncio.to_thread` tiếp tục treo ở lời gọi iterator thứ hai trong runtime hiện có.
- Bối cảnh tái hiện: test FastAPI trực tiếp tiêu thụ body stream dưới `.venv` Nix;
  test tách riêng FastAPI/Starlette cũng timeout nên không quy lỗi cho Qwen, Neo4j
  hoặc queue nghiệp vụ.
- Nguyên nhân đã xác nhận: cơ chế test stream đồng bộ và bridge `to_thread` không
  hoạt động tin cậy trong tổ hợp runtime hiện hữu. Generator lazy còn đòi hỏi mock
  provider bao phủ đúng thời điểm body được tiêu thụ.
- Cách xử lý: FastAPI endpoint chuyển sang `asyncio.Queue`; worker dùng
  `loop.call_soon_threadsafe` phát event, ASGI async generator chỉ `await queue.get`.
  Test gọi endpoint/bộ đọc body trong cùng event loop và giữ mock suốt quá trình.
- Kết quả kiểm chứng: FastAPI SSE contract hoàn tất trong 0,229 giây với result
  mô phỏng; 9 test server/FastAPI sau cùng đều đạt. Không dùng `TestClient` làm
  oracle streaming trong môi trường này.
- Phòng tránh: kiểm thử stream phải dùng async queue/async generator, cùng event
  loop với body consumer, và không phụ thuộc `TestClient` nếu ngay route tối giản
  đã timeout trong environment đang chạy.

## ERR-20261013-10

- Task: TASK-20261013-04.
- Triệu chứng: `nix develop .#rag --command ./.venv/bin/vigovbot rag --config
  configs/rag-graph.yaml api --port 8000` dừng với `FileNotFoundError` cho
  `.../Data/vector/unified` trước khi FastAPI khởi động.
- Nguyên nhân đã xác nhận: cấu hình GraphRAG và một số cấu hình local cũ tham
  chiếu `Data/` viết hoa, khác với layout repository `data/` trên filesystem
  Linux phân biệt hoa/thường. Corpus `data/vector/unified` hiện có manifest và
  checksum nên không phải lỗi artifact legacy hay Neo4j.
- Cách thử sửa: chuẩn hóa các đường dẫn local sang `data/`, sau đó regression
  test cấu hình và khởi động API đến sau bước prepare corpus.
- Kết quả: đã sửa toàn bộ config local liên quan và thêm regression test. Sáu
  `ConfigTests` đạt; `verify_corpus()` với chính `configs/rag-graph.yaml` xác minh
  thành công manifest/checksum của corpus tại `data/vector/unified`.
- Phòng tránh: cấu hình chạy local phải dùng đúng case của đường dẫn repository;
  giữ regression test đọc config vận hành thực thay vì chỉ YAML giả lập.

## ERR-20261013-02

- Task: TASK-20261013-02.
- Triệu chứng: lần render Compose đầu tiên cảnh báo các biến nội bộ của shell script
  (`database_name`, `marker`, `dump_path`) chưa được đặt và thay bằng chuỗi rỗng.
- Nguyên nhân đã xác nhận: Docker Compose nội suy `${...}` trong `configs.content`
  trước khi shell trong init container thực thi.
- Xử lý: escape toàn bộ biến shell nội bộ thành `$${...}`; chỉ giữ
  `${NEO4J_PASSWORD:-...}` cho biến cấu hình do Docker Compose đọc.
- Kết quả: đã sửa source Compose; sau đó `docker compose up -d` chạy được tới init
  và phát hiện tiếp lỗi guard volume (ERR-20261013-03).
- Phòng tránh: với script nhúng trong Compose, luôn escape `$` dành cho shell bằng
  `$$` để Compose không thực hiện nội suy.

## ERR-20261013-03

- Task: TASK-20261013-02.
- Triệu chứng: `neo4j-init` dừng với thông báo volume data không rỗng và thiếu
  marker restore, ngay cả khi volume vừa được tạo.
- Nguyên nhân đã xác nhận: image/container Neo4j tạo sẵn hai thư mục rỗng
  `/data/databases` và `/data/transactions`; guard an toàn ban đầu coi chúng là
  dấu hiệu database đã tồn tại.
- Xử lý: cho phép duy nhất hai thư mục khởi tạo này khi rỗng, nhưng kiểm tra nội
  dung bên trong và vẫn từ chối ghi đè dữ liệu/database thực tế khi không có marker.
- Kết quả: đã sửa Compose; chưa chạy lại container sau bản vá guard cuối để xác
  nhận dump được restore.
- Phòng tránh: guard restore cần phân biệt metadata/thư mục bootstrap do image tạo
  với file database thực tế.

## ERR-20261013-04

- Task: TASK-20261013-02.
- Triệu chứng: container `neo4j` dừng ngay khi khởi động với lỗi
  `Unrecognized setting. No declared setting with name: PASSWORD`.
- Nguyên nhân đã xác nhận: mọi biến môi trường bắt đầu bằng `NEO4J_` (trừ biến
  Docker đặc biệt như `NEO4J_AUTH`) được image Neo4j diễn giải là cấu hình server;
  biến ứng dụng `NEO4J_PASSWORD` bị đổi thành setting `PASSWORD` không tồn tại.
- Xử lý: chỉ truyền mật khẩu vào `NEO4J_AUTH`; thay `NEO4J_dbms_default__database`
  bằng setting đúng `NEO4J_initial_dbms_default__database`; healthcheck chỉ probe
  cổng Bolt, không phụ thuộc password có trong dump.
- Kết quả: source Compose đã được sửa; cần recreate service `neo4j` để áp dụng.
- Phòng tránh: không truyền secret ứng dụng mang tiền tố `NEO4J_` vào container
  Neo4j trừ các biến Docker/setting đã được tài liệu Neo4j hỗ trợ.

## ERR-20261013-06

- Task: TASK-20261013-03.
- Triệu chứng: chạy nhóm test GraphRAG/server/pipeline bằng Python hệ thống thất bại
  ngay lúc import với `ModuleNotFoundError` cho `vigovbot` và `faiss`; test FastAPI
  bị skip vì dependency chưa cài.
- Nguyên nhân đã xác nhận: interpreter Nix hiện tại không phải virtual environment
  của project và không có editable package hay extra `test`/`rag`.
- Xử lý: `.venv` đã tồn tại nên không xóa; dùng `uv pip install --python .venv/bin/python
  -e ".[rag,test,dev]"`. Test FAISS tiếp tục cần chạy trong `nix develop .#rag` để
  nhận `LD_LIBRARY_PATH` của Nix.
- Kết quả: 29 test GraphRAG/server/FastAPI/pipeline/config mục tiêu đạt trong Nix
  shell. Không thay đổi mã ứng dụng để che lỗi dependency.
- Phòng tránh: chạy test package qua `.venv` hoặc `uv run` có đủ extra, không dùng
  interpreter Nix base trực tiếp.

## ERR-20261013-07

- Task: TASK-20261013-03.
- Triệu chứng: truy vấn GraphRAG read-only đầu tiên tạo cảnh báo Neo4j về `CALL`
  subquery không có scope clause và trả procedure ít liên quan do cùng khớp stopword.
- Nguyên nhân đã xác nhận: Cypher dùng cú pháp subquery cũ và sắp xếp theo tên thay
  vì số term khớp với truy vấn.
- Xử lý: dùng `CALL (procedure)`, lọc thêm stopword tiếng Việt và tính `match_count`
  để ưu tiên procedure khớp nhiều term nhất trước khi giới hạn kết quả.
- Kết quả: Python Neo4j driver truy vấn local graph thành công, kết quả đầu là thủ tục
  hải quan về khí cùng `HANDLED_BY`/`AUTHORIZED_BY`/`LEGAL_BASIS`; không còn cảnh báo.
- Phòng tránh: xác minh truy vấn GraphRAG thật trên schema dump, không chỉ dùng mock.

## ERR-20261013-08

- Task: TASK-20261013-03.
- Triệu chứng: Next.js production build ban đầu không tải được Geist từ Google Fonts;
  sau đó Turbopack bị chặn bind cổng nội bộ và webpack gặp lỗi parse TypeScript CLI.
- Nguyên nhân: scaffold phụ thuộc font tải lúc build; runner hạn chế tiến trình/cổng
  Turbopack; Next 16.4 CLI TypeScript checker lỗi parse dù `tsc --showConfig` hợp lệ.
- Xử lý: bỏ `next/font/google`, dùng system font; đổi build sang webpack và cấu hình
  `experimental.useTypeScriptCli: false` theo tài liệu Next.js local.
- Kết quả: `npm run lint` và `npm run build` hoàn tất production build.
- Phòng tránh: UI local không phụ thuộc font/CDN khi build; dùng compiler API khi
  Next CLI checker không tương thích môi trường hiện hành.

## ERR-20261013-09

- Task: TASK-20261013-03.
- Triệu chứng: full Python regression chạy 122 test còn 1 failure tại
  `test_rewrite_and_answer_receive_history`, kỳ vọng `response_format == "json"`.
- Nguyên nhân đã xác nhận ngoài phạm vi: test này chưa cập nhật sau khi baseline
  `HEAD` đã chuyển output structured sang `answer_schema(...)` object; `git blame`
  cho thấy assertion cũ hơn thay đổi pipeline và `git show HEAD` xác nhận logic đó
  đã tồn tại trước task GraphRAG.
- Xử lý: không sửa test/code không liên quan. Chạy riêng 29 test bị ảnh hưởng bởi
  GraphRAG/FastAPI/pipeline/config đều đạt.
- Phòng tránh: cập nhật assertion multi-turn trong một task bảo trì riêng, không
  trộn sửa regression baseline vào thay đổi kiến trúc GraphRAG.

## ERR-20261013-05

- Task: TASK-20261013-02.
- Triệu chứng: Neo4j Browser dùng direct Bolt `bolt://127.0.0.1:7687` vẫn báo
  WebSocket connection failure sau khi service đã `healthy` và log xác nhận Bolt
  lắng nghe cổng 7687.
- Giả thuyết advertised address đã được thêm nhưng không được xem là nguyên nhân đã
  xác nhận. Kiểm chứng tiếp theo cho thấy `cypher-shell` xác thực/thực thi `RETURN 1`
  qua Bolt thành công và host nhận `101 Switching Protocols` từ endpoint WebSocket.
- Kết luận hiện có: Neo4j server, publish cổng, Bolt, xác thực và WebSocket listener
  hoạt động; `readyState: 3` còn lại thuộc ngữ cảnh Browser/client hoặc chính sách
  trình duyệt. Chưa có lỗi DevTools để kết luận cụ thể hơn.
- Phòng tránh: mở giao diện Browser do container phục vụ tại HTTP local, không dùng
  trang Browser HTTPS bên ngoài để kết nối Bolt không mã hóa; chỉ suy luận nguyên
  nhân client sau khi lấy Console/Network detail.

## ERR-20261013-01

- Task: TASK-20261013-01.
- Triệu chứng: các lệnh Nix cần evaluate/build (`nix eval`) thất bại với lỗi
  `cannot connect to socket at '/nix/var/nix/daemon-socket/socket': Operation not permitted`.
- Nguyên nhân đã xác nhận: môi trường sandbox hiện tại không cho phép truy cập
  nix-daemon, nên không thể kiểm chứng `nix develop` hoặc evaluate nixpkgs.
- Xử lý: chỉ bổ sung `flake.nix` và tài liệu hướng dẫn; đánh dấu kiểm chứng Nix
  là pending/partial trong task journal.
- Phòng tránh: khi cần kiểm chứng Nix, chạy trong môi trường có nix-daemon hoạt
  động (hoặc single-user Nix) và có mạng để fetch nixpkgs/wheels.

## ERR-20261006-05

- Task: TASK-20261006-03.
- Triệu chứng: kiểm tra sau vòng viết lại đầu phát hiện 339 chuỗi câu hỏi single
  bị trùng, tương ứng 821 case dư ngoài bản đầu tiên.
- Nguyên nhân đã xác nhận: tổ hợp biến thể quay vòng theo nhóm toàn cục, trong khi
  cùng một tên thủ tục xuất hiện lại đúng chu kỳ nên nhận cùng cách diễn đạt.
- Xử lý: giữ bản đầu và thêm tiền tố hỏi trung tính khác nhau cho các bản trùng.
- Kết quả: 0 input single trùng; checksum và test đều đạt.
- Phòng tránh: kiểm tra uniqueness trên câu hoàn chỉnh sau mọi phép paraphrase,
  không chỉ kiểm tra số mẫu chuẩn hóa.

## ERR-20261006-04

- Task: TASK-20261006-03.
- Triệu chứng: `git show HEAD:.../cases.jsonl` thất bại vì file tồn tại trên đĩa
  nhưng không có trong HEAD.
- Nguyên nhân đã xác nhận: dataset này không được Git theo dõi; không còn snapshot
  cùng hash cũ trong repository sau khi ghi.
- Xử lý: kiểm tra invariant hiện tại, checksum, phạm vi gán của script và công bố
  giới hạn; không giả vờ đã có diff độc lập với bản gốc.
- Phòng tránh: trước lần biến đổi dataset lớn tiếp theo, lưu snapshot bất biến hoặc
  patch question-only có hash trong khu vực artifact được bảo toàn.

## ERR-20261006-03

- Task: TASK-20261006-03.
- Triệu chứng: lệnh kiểm thử đầu tiên từ thư mục dataset không tìm thấy
  `env\Scripts\python.exe`.
- Nguyên nhân đã xác nhận: đường dẫn tương đối được tính từ thư mục dataset thay
  vì gốc repository.
- Xử lý: dùng đường dẫn tuyệt đối tới Python của môi trường dự án.
- Kết quả: kiểm tra invariant, 3 unit test và test resume chạy thành công.
- Phòng tránh: khi đổi `workdir`, dùng đường dẫn Python tuyệt đối hoặc tính lại
  đường dẫn tương đối trước khi chạy.

## ERR-20261006-02

- Task: TASK-20261006-02.
- Triệu chứng: lần chạy đầu `build_review.py` dừng với `SyntaxError` tại phần sinh
  báo cáo Markdown.
- Nguyên nhân đã xác nhận: ghép biểu thức nối chuỗi vào giữa f-string ba dấu nháy
  làm chuỗi kết thúc sớm.
- Xử lý: tính trước chuỗi phân bố/tổng hợp, sau đó nội suy biến vào một f-string.
- Kết quả kiểm chứng: script chạy lại exit 0; AST parse thành công và các kiểm tra
  count/ID/CSV đều đạt.
- Phòng tránh: không trộn phép cộng chuỗi với f-string nhiều dòng; chuẩn bị phần
  động phức tạp trong biến riêng.

## ERR-20261006-01

- Task: TASK-20261006-02.
- Triệu chứng: PowerShell trong sandbox báo `Access is denied` khi đọc
  `outputs/result_qa` dù đường dẫn thuộc workspace.
- Nguyên nhân đã xác nhận trong phạm vi task: ACL của `outputs/` không cho tiến
  trình sandbox đọc; không phải artifact bị thiếu.
- Xử lý: xin quyền thao tác trực tiếp đúng workspace cho các lệnh đọc/ghi cần thiết.
- Kết quả kiểm chứng: kiểm kê được artifact, sinh và đọc lại ba đầu ra thành công.
- Phòng tránh: nếu lỗi ACL này tái diễn, không suy luận file không tồn tại; kiểm tra
  lại bằng quyền workspace trực tiếp, giữ phạm vi lệnh ở dataset/artifact liên quan.

## ERR-20261003-10

- Task: TASK-20261003-09.
- Triệu chứng: lệnh kiểm thử đầu tiên không import được `vigovbot`.
- Bối cảnh tái hiện: `python -m unittest tests.test_qa_v4` dùng Python hệ thống.
- Nguyên nhân đã xác nhận: package dùng layout `src/` và Python hệ thống không
  cài editable package; đây là lỗi môi trường đã từng được ghi nhận.
- Xử lý: chuyển sang `env\Scripts\python.exe`, là môi trường dự án hiện có.
- Kết quả kiểm chứng: chạy lại đạt 8 test QA v4; Ruff cũng đạt.
- Phòng tránh: dùng Python trong `env/` cho kiểm thử repository.

## ERR-20261003-09

- Task: TASK-20261003-07.
- Triệu chứng: lượt đầu `scripts/smoke_routing_live.py oil` nhận HTTP 500 từ
  Ollama ở lần gọi router; chưa có response JSON model để validate.
- Nguyên nhân: chưa xác định; không có body lỗi/log runner trong traceback nên
  không khẳng định do schema, bộ nhớ hay tải model.
- Kiểm tra: gọi riêng /api/chat cùng schema với prompt ngắn, nhận HTTP 200 và
  JSON hợp lệ. Chạy lại nhóm oil thành công 2/2, nhóm basic thành công 4/4.
- Kết quả: lỗi API không còn tái hiện trong các lượt sau; không thêm retry HTTP
  tự động và không coi lỗi API là JSON sai dẫn đến fallback.
- Phòng tránh: khi lỗi tái hiện cần lấy body lỗi và log Ollama đúng thời điểm,
  phân biệt lỗi dịch vụ với lỗi schema/validator.

## ERR-20261003-08

- Task: TASK-20261003-06.
- Bối cảnh: probe Qwen thật với câu hỏi tràn dầu và history giả về hộ chiếu.
- Triệu chứng: cả initial/retry trả follow_up, query và clarification không rỗng;
  validator báo Retrieval route requires query and no clarification; fallback.
- Tái hiện: `env\Scripts\python scripts\probe_oil_spill_routing.py --with-history`.
- Thử giải pháp: cùng prompt/history dùng schema anyOf ép các trường theo nhánh.
- Kết quả: JSON hợp lệ ngay lần đầu, clarification rỗng; nhãn follow_up vẫn
  chưa đúng ý nghĩa câu hỏi chuyển chủ đề. Chưa sửa production, chưa chứng minh
  schema giải quyết mọi trường hợp. Artifact oil_spill_routing_probe_history.json.
- Phòng tránh đề xuất: schema + ví dụ phân loại + retry cụ thể + telemetry web.

## ERR-20261003-07

- Task: TASK-20261003-05.
- Triệu chứng: script xác thực lỗi UnicodeEncodeError khi in tiếng Việt.
- Lệnh: `env\Scripts\python scripts\verify_routing_artifact.py outputs\qa_v4\local_smoke.jsonl`.
- Nguyên nhân: stdout Windows dùng cp1252 không biểu diễn được tiếng Việt.
- Sửa: cấu hình stdout UTF-8; chạy lại thành công, kiểm tra đủ 10 dòng.
- Phòng tránh: script chẩn đoán in Unicode cần cấu hình encoding rõ ràng.

## ERR-20261003-06

- Task: TASK-20261003-05.
- Triệu chứng: 3 lượt trong artifact Qwen thật trả câu fallback mặc định.
- Bằng chứng: `outputs/qa_v4/local_smoke.jsonl`, dòng 8–10; raw response model
  `qwen2.5:7b`, initial_error/retry_error cùng marker fallback được lưu đầy đủ.
- Nguyên nhân xác nhận: JSON đúng cú pháp nhưng follow_up chứa clarification
  không rỗng; `parse_route` báo `Retrieval route requires query and no clarification`.
- Cách kiểm tra: script verify_routing_artifact chạy lại validator trên cả
  initial_text và retry_text, tái hiện đủ 6 lỗi hợp đồng của ba lượt fallback.
- Kết quả: xác nhận lỗi; task điều tra chưa sửa prompt/schema của ứng dụng.
- Phòng tránh đề xuất: schema có ràng buộc theo nhánh hoặc prompt retry chứa
  lỗi cụ thể và ví dụ JSON sửa; cần kiểm chứng model thật trước khi áp dụng.

## ERR-20261003-05

- Task: TASK-20261003-04.
- Triệu chứng: nhánh web `Qwen 2.5 7B + RAG` trả lỗi `SQLite objects created in
  a thread can only be used in that same thread`.
- Bối cảnh tái hiện: `Retriever` được tạo trong thread khởi động server, sau đó
  `ThreadingHTTPServer` xử lý `/api/chat` bằng thread worker và gọi `search()`.
- Nguyên nhân đã xác nhận: `sqlite3.connect` dùng mặc định
  `check_same_thread=True`, không phù hợp với vòng đời tài nguyên web hiện tại.
- Xử lý: mở database read-only với `check_same_thread=False`; bổ sung khóa nội bộ
  quanh toàn bộ `search()` và `close()` để tuần tự hóa encoder, FAISS và SQLite.
- Kết quả: test hồi quy tạo Retriever ở thread chính rồi truy hồi trong thread
  worker thành công; tổng cộng 20 test server/cấu hình/RAG đều đạt.
- Phòng tránh: mọi tài nguyên được tạo trước `ThreadingHTTPServer.serve_forever()`
  phải có hợp đồng thread rõ ràng và test gọi từ worker thread.

## ERR-20261003-04

- Task: TASK-20261003-03.
- Triệu chứng: lần chạy test đầu báo không tìm thấy package `vigovbot`; khi thêm
  `PYTHONPATH=src`, Python mặc định tiếp tục thiếu `filelock` và `yaml`.
- Bối cảnh tái hiện: chạy test bằng `python` hệ thống thay vì môi trường dự án.
- Nguyên nhân đã xác nhận: Python 3.14 mặc định chưa cài package/dependency dự án;
  workspace dùng virtual environment tại `env/`, không phải `.venv/`.
- Xử lý: chạy lại bằng `env\Scripts\python`.
- Kết quả: 19 test liên quan server, cấu hình và pipeline đều thành công.
- Phòng tránh: kiểm tra virtual environment có sẵn và dùng Python của môi trường
  dự án trước khi kết luận thiếu dependency.

## ERR-20261003-03

- Task: TASK-20261003-02.
- Triệu chứng: hai module test RAG không import được, `ModuleNotFoundError: No
  module named 'faiss'`.
- Bối cảnh tái hiện: chạy `python -m unittest tests.test_rag_config_cli
  tests.test_rag_pipeline -v`; workspace không có `.venv`, lệnh dùng Python 3.14
  mặc định.
- Nguyên nhân đã xác nhận: môi trường Python hiện tại chưa cài dependency
  `faiss-cpu` thuộc nhóm `rag`/`test`.
- Xử lý: không cài dependency vì task chỉ sửa tài liệu; chuyển sang kiểm tra tĩnh
  liên kết và `git diff --check`.
- Kết quả: kiểm thử ứng dụng chưa chạy được; lỗi không phát sinh từ thay đổi mã
  nguồn vì task không sửa code.
- Phòng tránh: dùng môi trường đã cài `.[test,dev]` hoặc `.[rag]` khi cần chạy bộ
  test RAG; không coi lỗi thiếu dependency là regression của ứng dụng.

## ERR-20261003-01

- Task: TASK-20261003-01.
- Triệu chứng: PowerShell in lỗi Set-PSReadLineOption về virtual terminal và
  invalid handle trước output của lệnh đọc file.
- Bối cảnh: exec_command dùng login mặc định, nạp PowerShell profile.
- Nguyên nhân: profile bật prediction của PSReadLine trong phiên không có
  terminal tương tác phù hợp; thông báo chỉ tới profile dòng 12–13.
- Xử lý: các lệnh tiếp theo dùng `login: false`.
- Kiểm chứng: lệnh đọc tài liệu và liệt kê skill sau đó không còn lỗi profile.
- Phòng tránh: dùng PowerShell không nạp profile cho lệnh agent không tương tác;
  không chỉnh profile cá nhân ngoài phạm vi task.

## ERR-20261003-02

- Task: TASK-20261003-01.
- Triệu chứng: quick_validate.py thất bại với `ModuleNotFoundError: No module named 'yaml'`.
- Tái hiện: chạy validator bằng Python mặc định cho một trong hai skill mới.
- Nguyên nhân: Python mặc định không có PyYAML mà validator import.
- Xử lý: cài PyYAML bằng pip --target vào thư mục tạm riêng; đặt PYTHONPATH và
  PYTHONUTF8 trong process kiểm chứng rồi chạy lại validator.
- Kết quả: cả hai skill đều trả `Skill is valid!`, exit code 0.
- Phòng tránh: kiểm tra dependency của công cụ validator; dùng môi trường riêng,
  không thêm dependency tooling vào ứng dụng chỉ để kiểm tra Markdown.

## ERR-20261004-01 — TASK-20261004-01: generation sai hợp đồng

- Bằng chứng: ZIP thứ hai có 4 lỗi `Evidence status and action do not match`
  (000033, 000084, 000211, 000271), gây 7 lượt free-running bị chặn.
- Nguyên nhân xác nhận ở code: generation chỉ dùng JSON mode, không ràng buộc
  cặp evidence/action, không retry; runner không lưu raw generation lỗi.
  Artifact không đủ để biết chính xác trường thiếu/sai của từng lượt.
- Sửa: schema theo cặp, giữ validator, retry một lần có budget; lưu diagnostics
  và blocked_by_id. Kiểm thử tái hiện JSON thiếu/sai/cắt dở, sửa thành công hoặc
  vẫn lỗi đều đạt. Giữ việc chặn chuỗi đã lỗi để không làm sai free_running.

## ERR-20261004-02 — TASK-20261004-01: lỗi ngữ nghĩa trong mẫu mới

- 000142 suy diễn trạng thái cá nhân từ quy trình; 000141 bỏ một phần câu hỏi;
  các ca 000059/000263 out_of_scope sai, 000072/000180 chọn thủ tục khi mơ hồ.
- Biện pháp: điều chỉnh prompt và giữ câu hỏi gốc cùng query đã viết lại.
- Chưa xác nhận hiệu quả bằng model thật: localhost:11434 từ chối kết nối;
  không có log Colab để xác định nguyên nhân artifact chỉ chứa 23 lượt.
- Báo cáo chi tiết: colab-rag-2-assessment.md; cần smoke lại, không tuyên bố
  các lỗi nội dung đã hết từ kiểm thử mock hoặc action accuracy.

## ERR-20261004-03 — TASK-20261004-03

- Bối cảnh: kiểm tra artifact theo đường dẫn người dùng gọi output/result_qa và in dữ liệu tiếng Việt bằng Python.
- Triệu chứng: đường dẫn không tồn tại; PowerShell profile báo PSReadLine khi redirect; Python stdout cp1252 gây UnicodeEncodeError; một truy vấn rg dùng glob đường dẫn Windows không hợp lệ.
- Xác nhận/sửa: thư mục thực là outputs/result_qa; dùng login=false, PYTHONIOENCODING=utf-8 và tìm trên đường dẫn thư mục với glob file. Các lần đọc tiếp theo thành công, dữ liệu gốc không bị sửa.
- Tránh lặp: xác nhận tên thư mục và encoding trước khi đọc artifact Unicode.
- Lỗi artifact quan sát riêng: single_0445 StructuredAnswerError sau 2 lần sinh JSON; chưa sửa runtime, chi tiết và giả thuyết cắt token nằm trong báo cáo.

## ERR-20261005-01 — TASK-20261005-01

- Assert kiểm chứng ban đầu giả định comparison.csv luôn đủ 1.500 dòng, thất bại ở cover.
- Xác nhận: CSV chỉ chứa 1.113 dòng đã chạy; scores per_case chứa đủ 1.500 mục. Sửa mẫu số kiểm chứng theo loại artifact; kiểm chứng lại đạt. Không có dữ liệu đầu vào bị sửa.


## ERR-20261005-02 — TASK-20261005-02

- Script retrieval bổ sung ban đầu giả định mọi source_file có PDF tương ứng và mã chunk luôn khớp tên nguồn; dừng ở 1.014955_D.pdf (thiếu file) và unverified_a2801127764a (khác tên 2.009182739.pdf).
- Đã sửa: giữ trạng thái unverified_source_identity, loại khỏi mẫu số đo được; không tự đoán ánh xạ _D/-Xoa hoặc mã unverified. Chạy lại exit 0; multi đo 1.142 ca, cover 1.110 ca.
- Lỗi nội dung Gold phát hiện riêng: coverage_0381 có trường cơ quan ghi Không có thông tin nhưng trình tự PDF có hỗ trợ câu trả lời. Correctness/completeness để null chờ phân xử; không sửa Gold ngầm.

## ERR-20261007-01 — TASK-20261007-01

- Triệu chứng: `test_evaluation.py` lỗi `ModuleNotFoundError: No module named
  'sacrebleu'` dù đã cài toàn bộ `locks/rag-windows-py314.txt`.
- Bối cảnh tái hiện: chạy test đi kèm dataset bằng `.venv/Scripts/python.exe`;
  hai test khác đạt, `test_resume.py` cũng đạt.
- Nguyên nhân đã xác nhận: lockfile RAG/evaluation Windows hiện tại không chứa
  `sacrebleu`, trong khi evaluator của dataset import package này và
  `pyproject.toml` khai báo nó trong extra `evaluation`.
- Xử lý: cài bổ sung `sacrebleu>=2.4,<3` vào `.venv`, không sửa lockfile trong
  task thiết lập máy; chạy lại test để kiểm chứng.
- Phòng tránh: khi tái sinh lock cần kiểm tra dependency trực tiếp của
  `evaluation` và chạy test dataset trong clean environment.

## ERR-20261007-02 — TASK-20261007-03

- Triệu chứng: BERTScore CUDA tính xong 3 cặp trong 9,41 giây nhưng scorer lỗi
  `ValueError: not enough values to unpack (expected 4, got 2)` và chưa ghi output.
- Bối cảnh: `bert-score==0.3.13`, `transformers==5.17.0`, gọi `score(...,
  return_hash=True)` trong `qa_v4/scoring.py`.
- Nguyên nhân xác nhận: API runtime trả `((P, R, F), hashcode)`, còn code giả định
  dạng cũ `(P, R, F, hashcode)`.
- Xử lý: chuẩn hóa cả hai dạng trả về, thêm unit test mock và chạy lại score CUDA.
  Prediction RAG không bị sửa và không cần chạy lại model.
- Phòng tránh: test đường BERTScore nên mock đúng nhiều contract phiên bản và có
  ít nhất một smoke thật sau khi nâng dependency.

## ERR-20261007-03 — TASK-20261007-03

- Triệu chứng: hai lệnh PowerShell gộp dùng `Start-Process` để restart Ollama bị
  policy terminal từ chối trước khi tạo process.
- Xử lý: tách đặt biến user, dừng đúng process Ollama đã xác minh, rồi chạy
  `ollama serve` trực tiếp trong session 99804; readiness và log cấu hình đạt.
- Ảnh hưởng: không mất dữ liệu; lần bị từ chối không thực thi thay đổi. Ollama
  hiện chạy với parallel=2, max loaded=1, Flash Attention và KV q8_0.
# ERR-20261007-03 — TASK-20261007-05

- Triệu chứng: `python Data/qa_test/tthc_test_case_v1/validation/validate_package.py`
  dừng với `FileNotFoundError` tại `data/train.jsonl`.
- Bối cảnh tái hiện: bộ dữ liệu hiện đặt case/query RAG trong `data/rag/` và SFT
  trong `data/fintuning/`, trong khi validator và `checksums.sha256` vẫn ghi đường
  dẫn phẳng `data/{split}.jsonl`, `data/{split}_queries.jsonl`,
  `data/{split}_sft.jsonl`.
- Nguyên nhân đã xác nhận: layout artifact không khớp đường dẫn được mã hóa trong
  validator/checksum; lỗi xảy ra trước khi kiểm tra nội dung split.
- Cách xử lý: không di chuyển hoặc sửa gold; benchmark dùng tường minh
  `data/rag/test_queries.jsonl` và `data/rag/test.jsonl`, đồng thời sẽ kiểm tra
  hash/nội dung theo layout thực tế. Chưa sửa package nguồn trong lúc chuẩn bị run.
- Kết quả kiểm chứng: ba file test/query/SFT tại layout thực tế khớp SHA-256 khai
  báo; evaluator synthetic đạt và 28 test RAG/QA đạt. Validator gốc vẫn lỗi nếu
  chưa sửa layout, nên không dùng kết quả đó để tuyên bố package validation đạt.

# ERR-20261007-04 — TASK-20261007-05

- Triệu chứng: smoke concurrency 4 liên tục retry HEAD tới Hugging Face với
  `WinError 10013`, dù BGE-M3 đã có trong cache.
- Bối cảnh: lượt smoke chạy trong sandbox không có mạng sau lượt tải model bằng
  quyền mạng; thư viện vẫn thử kiểm tra các file cấu hình tùy chọn trên Hub.
- Nguyên nhân: sandbox chặn socket, không phải thiếu trọng số hoặc lỗi CUDA.
- Cách xử lý: dừng đúng session trước khi tạo prediction, xác nhận output chưa tồn
  tại, chạy lại với `HF_HUB_OFFLINE=1` và `TRANSFORMERS_OFFLINE=1`.
- Kết quả: smoke c4 đạt 8/8, exit 0, wall 24,52 giây; dùng cùng cách cho full run.

# ERR-20261007-05 — TASK-20261007-06

- Triệu chứng: evaluator bị người dùng ngắt tại `BLEU.corpus_score`; trước đó
  terminal in lặp cảnh báo khuyến nghị `effective_order` cho sentence BLEU.
- Tái hiện: 1.000 prediction, 995 thành công; evaluator lexical gốc thực tế hoàn
  tất khoảng 3,75 giây nhưng phát hàng trăm dòng cảnh báo.
- Nguyên nhân: không phải deadlock/corpus quá lớn; SacreBLEU logger cảnh báo ở mỗi
  `sentence_score` khi hợp đồng hiện tại cố ý dùng `effective_order=False`.
- Cách sửa: đặt riêng logger `sacrebleu` ở ERROR, giữ nguyên tham số metric; thêm
  thông báo phase/progress và option batch BERTScore.
- Kết quả: lexical full hoàn tất 3,70 giây, không còn warning flood; synthetic
  evaluator và py_compile đạt. Tránh đổi `effective_order` ngầm vì sẽ đổi điểm
  sentence BLEU của câu ngắn.

# ERR-20261007-06 — TASK-20261007-06

- Triệu chứng: BERTScore dừng trước khi nạp model với
  `LocalEntryNotFoundError`/`outgoing traffic has been disabled` cho
  `xlm-roberta-large`.
- Bối cảnh: cùng terminal trước đó đã đặt `HF_HUB_OFFLINE=1` và
  `TRANSFORMERS_OFFLINE=1` để chạy RAG bằng cache; model BERTScore chưa có cache.
- Nguyên nhân: chế độ offline còn hiệu lực trong process PowerShell, không phải
  lỗi CUDA, batch 32 hoặc evaluator.
- Cách xử lý: xóa hai biến môi trường khỏi session, cho phép tải model lần đầu;
  sau khi cache hoàn tất có thể dùng offline ở các lần sau.
- Kết quả kiểm chứng: nguyên nhân xác nhận trực tiếp từ traceback; người dùng tự
  chạy lại job dài theo yêu cầu trước, chưa có artifact BERTScore hoàn tất.


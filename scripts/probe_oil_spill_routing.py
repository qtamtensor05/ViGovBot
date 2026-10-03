"""Compare current router and schema-constrained routing on the reported question."""
import json
from pathlib import Path
import sys

from transformers import AutoTokenizer
from vigovbot.rag.config import load_config
from vigovbot.rag.pipeline import answer_question
from vigovbot.rag.routing import routing_messages, parse_route
from vigovbot.llm.llm_client import ollama_answer

QUESTION = 'Tôi đang tìm hiểu “Thủ tục thẩm định và phê duyệt kế hoạch ứng phó sự cố tràn dầu đối với cửa hàng bán lẻ xăng dầu trên đất liền, trên sông, trên biển và các cơ sở, dự án trên địa bàn xã không thuộc đối tượng kinh doanh, vận chuyển xăng dầu có nguy cơ xảy ra sự cố tràn dầu mức độ nhỏ (dung tích chứa dưới 50 m3)”. Nếu nộp bằng hình thức trực tuyến, thời hạn, phí và mô tả kèm theo trong bảng là gì?'


class EmptyRetriever:
    def search(self, query, top_k):
        return []


def schema(has_history=False):
    branches = []
    for scope, relation in [('in_scope', 'new_question'), ('in_scope', 'follow_up'),
                            ('in_scope', 'ambiguous'), ('out_of_scope', 'new_question')]:
        retrieval = scope == 'in_scope' and relation != 'ambiguous'
        clarify = scope == 'in_scope' and relation == 'ambiguous'
        branches.append({'type': 'object', 'additionalProperties': False,
                         'required': ['scope', 'relation', 'query', 'clarification'],
                         'properties': {'scope': {'const': scope}, 'relation': {'const': relation},
                                        'query': {'type': 'string', 'minLength': 1} if retrieval else {'const': ''},
                                        'clarification': {'type': 'string', 'minLength': 1} if clarify else {'const': ''}}})
    # This probe has no history; disallow follow_up at decoding time.
    return {'anyOf': [b for b in branches if has_history or b['properties']['relation']['const'] != 'follow_up']}


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    config = load_config('configs/inference.yaml')
    settings = config.inference_settings()
    tokenizer = AutoTokenizer.from_pretrained(config.llm.tokenizer, local_files_only=True)
    with_history = '--with-history' in sys.argv
    history = ([{'role': 'user', 'content': 'Tôi muốn tìm hiểu thủ tục cấp hộ chiếu.'},
                {'role': 'assistant', 'content': 'Bạn muốn tra cứu nội dung nào về thủ tục cấp hộ chiếu?'}]
               if with_history else [])
    current = answer_question(QUESTION, EmptyRetriever(), tokenizer, settings, history=history)
    messages, tokens = routing_messages(QUESTION, history, tokenizer, settings)
    text, raw, seconds = ollama_answer(messages, {**settings, 'response_format': schema(bool(history))})
    try:
        route, error = parse_route(text, history), None
    except ValueError as exc:
        route, error = None, str(exc)
    output = {'question': QUESTION, 'history': history, 'history_is_synthetic': with_history, 'current': current,
              'schema_trial': {'text': text, 'route': route, 'error': error,
                               'raw': raw, 'seconds': seconds, 'prompt_tokens': tokens},
              'scope': 'Routing only; empty retriever is deliberate, not a corpus search.'}
    path = Path('outputs/qa_v4/oil_spill_routing_probe_history.json' if with_history
                else 'outputs/qa_v4/oil_spill_routing_probe.json')
    path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'artifact': str(path), 'current_route': current['routing'],
                      'current_reason': current['decision_reason'],
                      'current_raw_routing': current['raw_routing'],
                      'schema_route': route, 'schema_error': error}, ensure_ascii=False))


if __name__ == '__main__':
    main()

import hashlib
import tempfile
import unittest
from pathlib import Path

from vigovbot.qa_v4.audit import compact, fact_candidates
from vigovbot.qa_v4.retrieval_metrics import apply_mapping, evidence_metrics, summarize_retrieval
from vigovbot.qa_v4.review import fingerprint, judgment_input, validate_judgments, METRICS
from vigovbot.qa_v4.scoring import evaluate, unpack_bert_score
from vigovbot.qa_v4.runner import run_queries
from vigovbot.rag.routing import parse_citations
from vigovbot.qa_v4.compare import compare


class ReviewTests(unittest.TestCase):
    def test_bert_score_return_contracts(self):
        scores = (object(), object(), object())
        self.assertEqual(unpack_bert_score((*scores, 'old')), (*scores, 'old'))
        self.assertEqual(unpack_bert_score((scores, 'new')), (*scores, 'new'))
        with self.assertRaises(ValueError):
            unpack_bert_score((scores,))

    def case(self):
        return {'id': 'q', 'field_id': 'f', 'expected_action': 'answer',
                'reference_answer': 'Đáp án', 'evidence': [{'unit_id': 'gold'}]}

    def test_chunk_rank_not_flattened_unit_rank(self):
        p = {'retrieved_unit_groups': [
            {'chunk_id': 'a', 'unit_ids': ['u1', 'u2', 'u3', 'u4', 'u5', 'u6']},
            {'chunk_id': 'b', 'unit_ids': ['gold']}]}
        values, state = evidence_metrics(self.case(), p, 2)
        self.assertEqual(state, 'resolved')
        self.assertEqual(values['judged_evidence_recall_at_k'], 1)
        self.assertEqual(values['mrr_at_k'], .5)

    def test_unresolved_is_not_negative_and_duplicate_chunks_do_not_consume_rank(self):
        p = {'retrieved_unit_groups': [{'chunk_id': 'a', 'unit_ids': []},
            {'chunk_id': 'a', 'unit_ids': []}, {'chunk_id': 'b', 'unit_ids': ['gold']},
            {'chunk_id': 'c', 'unit_ids': None}]}
        self.assertEqual(evidence_metrics(self.case(), p, 2)[0]['mrr_at_k'], .5)
        self.assertEqual(evidence_metrics(self.case(), p, 3), ({}, 'unresolved_mapping'))
        self.assertEqual(evidence_metrics(self.case(), {'retrieved_unit_ids': ['gold']}, 5)[1], 'unresolved_mapping')

    def test_end_to_end_failure_denominator_and_routing_skips(self):
        cases = [self.case(), {**self.case(), 'id': 'failed'}, {**self.case(), 'id': 'skip'}]
        predictions = [{'id': 'q', 'retrieved_unit_groups': [{'chunk_id': 'a', 'unit_ids': ['gold']}]},
                       {'id': 'failed', 'error': 'timeout'},
                       {'id': 'skip', 'decision_reason': 'ambiguous_question', 'retrieved_chunk_ids': []}]
        _, report = summarize_retrieval(cases, predictions, 5)
        self.assertTrue(report['available'])
        self.assertAlmostEqual(report['end_to_end_all_eligible']['judged_evidence_recall_at_k']['mean'], 1/3)

    def test_mapping_requires_review_and_matching_context(self):
        p = {'id': 'q', 'retrieved_chunk_ids': ['c'], 'context_used': [{'chunk_id': 'c', 'included_text': 'x'}]}
        entry = {'status': 'candidate', 'unit_ids': ['gold'], 'reviewer': 'a', 'reviewer_kind': 'ai',
                 'reason': 'verified source', 'source_sha256': 'source',
                 'chunk_sha256': hashlib.sha256(b'x').hexdigest()}
        mapping = {'schema_version': 1, 'chunks': {'c': entry}}
        self.assertEqual(apply_mapping([p], mapping)[0]['unit_mapping_status'], 'incomplete_mapping')
        entry['status'] = 'reviewed'
        self.assertEqual(apply_mapping([p], mapping)[0]['unit_mapping_status'], 'reviewed')
        p['context_used'][0]['included_text'] = 'changed'
        self.assertEqual(apply_mapping([p], mapping)[0]['unit_mapping_status'], 'incomplete_mapping')

    def test_unicode_pdf_spacing_and_row_conditions_preserved(self):
        self.assertEqual(compact('Đào ta ̣o'), compact('Đào tạo'))
        self.assertNotEqual(compact('không đủ'), compact('đủ'))
        c = {'required_facts': [{'fact_id': 'f1', 'unit_id': 'u', 'value': 'old'}]}
        facts = fact_candidates(c, {'u': {'headers': ['Giấy tờ', 'Số lượng'],
            'cells': [['A chỉ khi thay đổi hãng', '1 bản'], ['B', '2 bản']]}})
        self.assertEqual(len(facts), 2)
        self.assertIn('chỉ khi thay đổi hãng', facts[0]['value'])
        self.assertTrue(all(f['review_status'] == 'candidate_not_semantically_approved' for f in facts))

    def test_stale_judgments_and_ai_provenance(self):
        c = self.case(); p = {'id': 'q', 'answer': 'Đáp án', 'action': 'answer'}
        j = {'id': 'q', 'reviewer': 'codex', 'reviewer_kind': 'ai', 'reason': 'Read source',
             'input_sha256': fingerprint(judgment_input(c, p)), **{k: None for k in METRICS}, 'completeness': 1}
        validate_judgments([c], [p], [j])
        with self.assertRaises(ValueError): validate_judgments([c], [{**p, 'answer': 'changed'}], [j])
        self.assertEqual(evaluate([c], [p], [j], lexical=False)['semantic_evaluation']['reviewer_kinds'], {'ai': 1})

    def test_cached_bert_does_not_load_model_and_rejects_changed_answer(self):
        c = self.case(); p = {'id': 'q', 'answer': 'Đáp án', 'action': 'answer'}
        cache = {'input_sha256': fingerprint([('q', 'Đáp án', 'Đáp án')]),
                 'configuration': {'model': 'test'}, 'per_case': [{'id': 'q', 'precision': .8, 'recall': .7, 'f1': .75}]}
        r = evaluate([c], [p], [], lexical=False, bert_cache=cache)
        self.assertEqual(r['overall_available']['bertscore_f1']['mean'], .75)
        with self.assertRaises(ValueError): evaluate([c], [{**p, 'answer': 'new'}], [], lexical=False, bert_cache=cache)

    def test_citations_validate_source_and_exact_claim_not_entailment(self):
        text = '{"answer":"Có 3 giấy tờ", "citations":[{"chunk_id":"c","claim":"3 giấy tờ"}]}'
        self.assertEqual(parse_citations(text, [{'chunk_id': 'c', 'source_file': 'p.pdf'}])[0]['source_file'], 'p.pdf')
        with self.assertRaises(ValueError): parse_citations(text, [{'chunk_id': 'wrong'}])

    def test_oracle_only_forwards_explicit_evidence_not_gold_answer(self):
        calls = []
        def answer(question, history=None, **kwargs):
            calls.append((question, kwargs))
            return {'answer': 'generated'}
        q = {'id': 'q', 'question': 'question', 'reference_answer': 'SECRET'}
        with tempfile.TemporaryDirectory() as d:
            run_queries([q], answer, Path(d)/'p.jsonl', oracle_contexts={'q': [{'quote': 'evidence'}]})
        self.assertNotIn('SECRET', str(calls))
        self.assertEqual(calls[0][1], {'context': [{'quote': 'evidence'}]})

    def test_comparison_uses_failed_cases_and_rejects_dataset_changes(self):
        left = {'benchmark': {'hash': 'same'}, 'case_groups': {'a': 'p1', 'b': 'p2'},
                'per_case': [{'id': 'a', 'action_accuracy': 1}, {'id': 'b'}]}
        right = {**left, 'per_case': [{'id': 'a', 'action_accuracy': 1}, {'id': 'b', 'action_accuracy': 1}]}
        result = compare(left, right, samples=100)
        self.assertEqual(result['metrics']['action_accuracy']['mean_difference'], .5)
        with self.assertRaises(ValueError): compare(left, {**right, 'benchmark': {'hash': 'changed'}})


if __name__ == '__main__': unittest.main()

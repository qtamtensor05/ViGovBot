"""Export review packets and validate explicit, provenance-bound judgments."""
import argparse
import hashlib
import json
from pathlib import Path

from .io import read_jsonl

METRICS = ('correctness', 'completeness', 'faithfulness', 'citation_support', 'behavior_correct')


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                    separators=(',', ':')).encode('utf-8')).hexdigest()


def judgment_input(case, prediction):
    return {'case': {k: case.get(k) for k in ('id', 'question', 'history', 'expected_action',
             'reference_answer', 'required_facts', 'evidence', 'unsupported_requests')},
            'prediction': {k: prediction.get(k) for k in ('answer', 'action', 'error', 'context_used', 'citations')}}


def validate_judgments(cases, predictions, judgments):
    cs, ps = {c['id']: c for c in cases}, {p['id']: p for p in predictions}
    seen = set()
    for j in judgments:
        cid = j.get('id')
        if cid in seen or cid not in cs or cid not in ps or ps[cid].get('error'):
            raise ValueError('Duplicate, unknown, or failed judgment case: ' + str(cid))
        seen.add(cid)
        if j.get('reviewer_kind') not in {'human', 'ai'} or not j.get('reviewer') or not j.get('reason'):
            raise ValueError('Judgment requires reviewer_kind, reviewer and reason')
        if j.get('input_sha256') != fingerprint(judgment_input(cs[cid], ps[cid])):
            raise ValueError('Stale judgment input hash: ' + cid)
        for m in METRICS:
            if m not in j or j[m] not in (None, 0, 1) or isinstance(j[m], bool):
                raise ValueError('All semantic metrics must be explicit 0/1/null: ' + m)
        if all(j[m] is None for m in METRICS):
            raise ValueError('Empty judgment is a pending packet, not a completed judgment')
    return judgments


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--dataset', type=Path, required=True)
    ap.add_argument('--view', default='views_single_1500.json')
    ap.add_argument('--predictions', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    ids = set(json.loads((a.dataset / a.view).read_text(encoding='utf-8-sig')))
    ps = {p['id']: p for p in read_jsonl(a.predictions)}
    a.out.parent.mkdir(parents=True, exist_ok=True)
    with a.out.open('x', encoding='utf-8') as f:
        for c in read_jsonl(a.dataset / 'cases.jsonl'):
            if c['id'] not in ids: continue
            payload = judgment_input(c, ps.get(c['id'], {'error': 'missing'}))
            f.write(json.dumps({'id': c['id'], 'input': payload, 'input_sha256': fingerprint(payload),
                                'review_status': 'pending', 'rubric': 'judge_rubric.md',
                                'judgment_template': {k: None for k in METRICS}}, ensure_ascii=False) + '\n')


if __name__ == '__main__':
    main()

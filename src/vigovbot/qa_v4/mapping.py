"""Create mapping candidates, never silently label unresolved chunks as irrelevant."""
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path

from .audit import compact, sha256
from .io import read_jsonl


def build_candidates(dataset, predictions, data_root):
    chunks, conflicts = {}, set()
    for p in predictions:
        for c in p.get('context_used', []):
            cid = c['chunk_id']
            if cid in chunks and chunks[cid]['included_text'] != c['included_text']:
                conflicts.add(cid)
            chunks[cid] = c
    docs = {c['source_code'] for c in chunks.values()}
    units = defaultdict(list)
    for u in read_jsonl(Path(dataset) / 'knowledge_units.jsonl'):
        if u['document_id'] in docs: units[u['document_id']].append(u)
    hashes, entries = {}, {}
    for cid, c in chunks.items():
        doc = c['source_code']
        if doc not in hashes:
            path = Path(data_root) / 'pdf' / f'{doc}.pdf'
            hashes[doc] = sha256(path) if path.is_file() else None
        text = compact(c['included_text'])
        matches = []
        for u in units[doc]:
            parts = [v for row in u.get('cells', []) for v in row if v.strip()] or [u['value']]
            # Header and all cells must occur; associations still require review.
            if u['source_sha256'] == hashes[doc] and all(compact(v) in text for v in parts) \
                    and compact(u['section']) in text:
                matches.append(u['unit_id'])
        entries[cid] = {'status': 'conflicting_context_variants' if cid in conflicts else 'candidate',
                        'unit_ids': matches, 'source_sha256': hashes[doc], 'source_file': f'pdf/{doc}.pdf',
                        'chunk_sha256': hashlib.sha256(c['included_text'].encode('utf-8')).hexdigest(),
                        'reviewer': None, 'reviewer_kind': None, 'reason': None,
                        'candidate_method': 'same_pdf_hash_section_and_all_value_parts; requires association review'}
    return {'schema_version': 1, 'review_kind': 'pending', 'chunks': entries,
            'note': 'Empty candidate list is unresolved, not a reviewed negative. Conflicting variants need separate mapping.'}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--dataset', type=Path, required=True)
    ap.add_argument('--predictions', type=Path, required=True)
    ap.add_argument('--data-root', type=Path, default=Path('Data'))
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    mapping = build_candidates(a.dataset, list(read_jsonl(a.predictions)), a.data_root)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    with a.out.open('x', encoding='utf-8') as f: json.dump(mapping, f, ensure_ascii=False, indent=2)
    print(json.dumps({'chunks': len(mapping['chunks']),
                      'with_candidates': sum(bool(v['unit_ids']) for v in mapping['chunks'].values())}))


if __name__ == '__main__':
    main()

"""Read-only PDF/source audit. Mechanical checks are never semantic approval."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import unicodedata

from .io import read_jsonl


def compact(text):
    # PDF extraction can insert whitespace before a Vietnamese combining mark.
    text = re.sub(r'\s+', '', text)
    return ''.join(re.findall(r'\w+', unicodedata.normalize('NFC', text).casefold()))


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def fact_candidates(case, units):
    """Split table rows only; preserve each full row and its conditions verbatim."""
    facts = []
    for original in case.get('required_facts', []):
        unit = units.get(original['unit_id'], {})
        cells, headers = unit.get('cells'), unit.get('headers', [])
        values = [' | '.join(f'{headers[i] if i < len(headers) else i}: {v}'
                            for i, v in enumerate(row)) for row in cells] if cells else [original['value']]
        for value in values:
            facts.append({**original, 'fact_id': f'f{len(facts)+1}', 'value': value,
                          'review_status': 'candidate_not_semantically_approved'})
    return facts


def audit(dataset, data_root, view, out):
    import pymupdf
    dataset, data_root, out = Path(dataset), Path(data_root), Path(out)
    out.mkdir(parents=True, exist_ok=True)
    ids = set(json.loads((dataset / view).read_text(encoding='utf-8-sig')))
    cases = [c for c in read_jsonl(dataset / 'cases.jsonl') if c['id'] in ids]
    if len(cases) != len(ids):
        raise ValueError('View contains missing/duplicate case IDs')
    needed = {e['unit_id'] for c in cases for e in c.get('evidence', [])}
    units = {u['unit_id']: u for u in read_jsonl(dataset / 'knowledge_units.jsonl') if u['unit_id'] in needed}
    documents = {}

    def document(source):
        if source not in documents:
            path = (data_root / source).resolve()
            if not path.is_relative_to(data_root.resolve()):
                raise ValueError('Source path escapes Data root')
            if not path.is_file():
                documents[source] = {'error': 'missing_pdf', 'pages': []}
            else:
                try:
                    with pymupdf.open(path) as pdf:
                        documents[source] = {'source_sha256': sha256(path),
                                             'pages': [page.get_text(sort=False) for page in pdf]}
                except Exception as exc:
                    documents[source] = {'error': str(exc), 'pages': []}
        return documents[source]

    rows, packets = [], []
    for c in cases:
        checks, issues = [], []
        for e in c.get('evidence', []):
            d = document(e['source_file'])
            pages = e.get('pages', [])
            valid_pages = bool(pages) and all(isinstance(n, int) and 1 <= n <= len(d['pages']) for n in pages)
            text = '\n'.join(d['pages'][n-1] for n in pages) if valid_pages else ''
            unit = units.get(e['unit_id'], {})
            parts = [v for row in unit.get('cells', []) for v in row if v.strip()] or [e['quote']]
            missing = [v for v in parts if not compact(v) or compact(v) not in compact(text)]
            check = {'unit_id': e['unit_id'], 'source_file': e['source_file'], 'pages': pages,
                     'hash_matches': d.get('source_sha256') == e['source_sha256'],
                     'pages_valid': valid_pages, 'parts': len(parts), 'unlocated_parts': missing,
                     'unit_quote_matches': unit.get('value') == e['quote'],
                     'method': 'normalized_containment_on_declared_pages_not_visual_or_semantic_review'}
            checks.append(check)
            if not check['hash_matches']: issues.append('source_hash_mismatch_or_missing')
            if not valid_pages: issues.append('invalid_pages')
            if missing: issues.append('text_not_located_needs_visual_review')
            if not check['unit_quote_matches']: issues.append('unit_quote_mismatch')
        sampling = c.get('sampling_document_id')
        if sampling:
            d = document(f'pdf/{sampling}.pdf')
            if d.get('error'): issues.append('sampling_pdf_unreadable')
        status = 'needs_review' if issues else ('source_checks_passed' if checks else 'source_check_not_applicable')
        row = {'id': c['id'], 'expected_action': c['expected_action'], 'source_status': status,
               'checks': checks, 'issues': sorted(set(issues)), 'semantic_review': 'pending',
               'human_review': 'pending', 'required_facts_candidate': fact_candidates(c, units)}
        rows.append(row)
        packets.append({'id': c['id'], 'question': c['question'], 'expected_action': c['expected_action'],
                        'reference_answer': c['reference_answer'], 'required_facts': row['required_facts_candidate'],
                        'evidence': c.get('evidence', []), 'issues': row['issues'],
                        'source_status': status, 'semantic_review': 'pending', 'human_review': 'pending'})
    summary = {'selected_cases': len(rows), 'pdfs_read': len(documents),
               'source_status': dict(Counter(r['source_status'] for r in rows)),
               'issues': dict(Counter(i for r in rows for i in r['issues'])),
               'human_approved': 0, 'semantic_approved_by_this_script': 0,
               'dataset_sha256': sha256(dataset / 'cases.jsonl'),
               'note': 'Literal source verification only. Table cells require layout review; no automatic gold promotion.'}
    for name, values in [('case_source_audit.jsonl', rows), ('review_packets.jsonl', packets)]:
        with (out / name).open('x', encoding='utf-8') as f:
            for r in values: f.write(json.dumps(r, ensure_ascii=False) + '\n')
    with (out / 'pdf_text_cache.json').open('x', encoding='utf-8') as f:
        json.dump(documents, f, ensure_ascii=False)
    (out / 'source_audit_summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    return summary


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--dataset', type=Path, required=True)
    ap.add_argument('--data-root', type=Path, default=Path('Data'))
    ap.add_argument('--view', default='views_single_1500.json')
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    print(json.dumps(audit(a.dataset, a.data_root, a.view, a.out), ensure_ascii=False))


if __name__ == '__main__':
    main()

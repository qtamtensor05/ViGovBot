"""Evidence coverage at ORIGINAL chunk ranks; unresolved mappings are not negatives."""
import hashlib

RETRIEVAL_KEYS = {'judged_evidence_recall_at_k', 'mrr_at_k', 'judged_hit_rate_at_k',
                  'unjudged_retrieved_count'}


def apply_mapping(predictions, mapping):
    if mapping.get('schema_version') != 1 or not isinstance(mapping.get('chunks'), dict):
        raise ValueError('Use reviewed mapping schema_version=1 with chunks entries')
    result = []
    for p in predictions:
        p = dict(p)
        if 'retrieved_chunk_ids' not in p:
            result.append(p)
            continue
        contexts = {c['chunk_id']: c for c in p.get('context_used', [])}
        groups, unresolved = [], []
        for cid in p.get('retrieved_chunk_ids', []):
            entry = mapping['chunks'].get(cid, {})
            context = contexts.get(cid, {})
            text = context.get('included_text', '')
            valid = (entry.get('status') == 'reviewed' and entry.get('reviewer') and entry.get('reason')
                     and entry.get('reviewer_kind') in {'ai', 'human'}
                     and entry.get('source_sha256') and entry.get('chunk_sha256')
                     == hashlib.sha256(text.encode('utf-8')).hexdigest()
                     and isinstance(entry.get('unit_ids'), list)
                     and all(isinstance(u, str) for u in entry['unit_ids']))
            if not valid: unresolved.append(cid)
            groups.append({'chunk_id': cid, 'unit_ids': entry['unit_ids'] if valid else None})
        p['retrieved_unit_groups'] = groups
        p['unmapped_chunk_ids'] = unresolved
        p['unit_mapping_status'] = 'incomplete_mapping' if unresolved else 'reviewed'
        p['mapping_review_kind'] = mapping.get('review_kind', 'mixed_or_unspecified')
        result.append(p)
    return result


def evidence_metrics(case, prediction, k):
    gold = {e['unit_id'] for e in case.get('evidence', [])}
    if not gold:
        return {}, 'not_applicable'
    if not prediction or prediction.get('error'):
        return {}, 'failed_or_missing'
    groups = prediction.get('retrieved_unit_groups')
    if groups is None:
        # Only explicit no-retrieval decisions count as a measured empty result.
        if prediction.get('decision_reason') in {'ambiguous_question', 'out_of_scope', 'routing_fallback', 'no_context'} \
                and prediction.get('retrieved_chunk_ids') == []:
            groups = []
        else:
            return {}, 'unresolved_mapping'
    unique, seen = [], set()
    for g in groups:
        if g['chunk_id'] not in seen:
            unique.append(g)
            seen.add(g['chunk_id'])
    top = unique[:k]
    if any(g.get('unit_ids') is None for g in top):
        return {}, 'unresolved_mapping'
    units = {uid for g in top for uid in g['unit_ids']}
    hits = gold & units
    return {'judged_evidence_recall_at_k': len(hits) / len(gold),
            'judged_hit_rate_at_k': int(bool(hits)),
            'mrr_at_k': next((1 / (i+1) for i, g in enumerate(top) if gold & set(g['unit_ids'])), 0)}, \
        'resolved' if top else 'no_retrieval'


def summarize_retrieval(cases, predictions, k):
    by = {p['id']: p for p in predictions}
    rows, states = {}, {}
    for c in cases:
        metrics, state = evidence_metrics(c, by.get(c['id']), k)
        rows[c['id']] = metrics
        states[state] = states.get(state, 0) + 1
    eligible = len(cases) - states.get('not_applicable', 0)
    unresolved = states.get('unresolved_mapping', 0)
    measured = sum(bool(v) for v in rows.values())
    complete = bool(eligible) and not unresolved
    e2e = {m: {'mean': sum(r.get(m, 0) for r in rows.values()) / eligible, 'n': eligible}
           for m in RETRIEVAL_KEYS - {'unjudged_retrieved_count'}} if complete else None
    return rows, {'available': complete, 'k': k, 'rank_unit': 'original_unique_chunk',
                  'eligible_cases': eligible, 'measured_cases': measured, 'states': states,
                  'end_to_end_all_eligible': e2e,
                  'note': 'Failed/missing and explicit routing skips count as zero in end-to-end. '
                          'Unresolved top-k mappings suppress full-set claims. Available-subset means are diagnostic only.'}

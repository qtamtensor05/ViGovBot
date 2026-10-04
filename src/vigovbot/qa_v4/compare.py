"""Paired comparison, with cluster bootstrap by procedure family/conversation."""
import argparse
from collections import defaultdict
import json
from pathlib import Path
import random


def compare(left, right, samples=2000, seed=42):
    if not left.get('benchmark') or left['benchmark'] != right.get('benchmark'):
        raise ValueError('Reports must use exactly the same dataset and selected IDs')
    if left.get('history_mode') != right.get('history_mode'):
        raise ValueError('History modes differ')
    if left.get('case_groups') != right.get('case_groups'):
        raise ValueError('Cluster assignments differ')
    a = {r['id']: r for r in left['per_case']}; b = {r['id']: r for r in right['per_case']}
    if set(a) != set(b): raise ValueError('Case coverage differs')
    result = {'benchmark': left['benchmark'], 'direction': 'right_minus_left',
              'bootstrap': {'unit': 'procedure_family_or_conversation', 'samples': samples, 'seed': seed},
              'metrics': {}, 'note': 'Diagnostic CIs; model/config comparability and held-out policy still require review.'}
    for metric in ['action_accuracy', 'bertscore_f1', 'rougeL_f1', 'correctness', 'completeness', 'faithfulness',
                   'citation_support', 'behavior_correct']:
        keys_a = {cid for cid, r in a.items() if metric in r}
        keys_b = {cid for cid, r in b.items() if metric in r}
        if metric == 'action_accuracy': keys_a = keys_b = set(a)  # failures count as zero
        if not keys_a or keys_a != keys_b:
            result['metrics'][metric] = {'available': False, 'reason': 'missing or unequal judged subsets'}
            continue
        groups = defaultdict(list)
        for cid in sorted(keys_a):
            groups[left['case_groups'][cid]].append(b[cid].get(metric, 0) - a[cid].get(metric, 0))
        values = list(groups.values()); rng = random.Random(seed)
        delta = sum(sum(v) for v in values) / len(keys_a)
        draws = []
        if len(values) > 1:
            for _ in range(samples):
                selected = rng.choices(values, k=len(values))
                draws.append(sum(sum(v) for v in selected) / sum(len(v) for v in selected))
        draws.sort()
        result['metrics'][metric] = {'available': True, 'n_pairs': len(keys_a), 'n_clusters': len(values),
            'mean_difference': delta,
            'ci95': [draws[int(.025*(len(draws)-1))], draws[int(.975*(len(draws)-1))]] if draws else None}
    return result


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--left', type=Path, required=True); ap.add_argument('--right', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    result = compare(json.loads(a.left.read_text(encoding='utf-8')), json.loads(a.right.read_text(encoding='utf-8')))
    a.out.parent.mkdir(parents=True, exist_ok=True)
    with a.out.open('x', encoding='utf-8') as f: json.dump(result, f, ensure_ascii=False, indent=2)


if __name__ == '__main__': main()

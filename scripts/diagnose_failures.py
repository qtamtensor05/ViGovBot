import json
from collections import Counter

with open('outputs/evaluation/router_testset/failures.jsonl', encoding='utf-8') as f:
    failures = [json.loads(line) for line in f]

print(f"Total failures: {len(failures)}")

action_fails = [f for f in failures if not f['failure_reasons']['action_ok']]
print(f"Total action failures: {len(action_fails)}")
c = Counter()
for f in action_fails:
    exp_act = f.get('expected', {}).get('action')
    exp_reas = f.get('expected', {}).get('decision_reason')
    act_act = f.get('actual', {}).get('action')
    act_reas = f.get('actual', {}).get('decision_reason')
    pair = f"Expected: {exp_act} ({exp_reas})  ==>  Actual: {act_act} ({act_reas})"
    c[pair] += 1

for k, v in c.most_common():
    print(f"  [{v:3d}] {k}")

# Also look at section empty differences
print("\n--- Section length mismatches in action failures ---")
empty_sec_mismatch = 0
for f in action_fails:
    exp_secs = f.get('expected', {}).get('sections') or []
    act_secs = f.get('actual', {}).get('sections') or []
    if (len(exp_secs) == 0 and len(act_secs) > 0) or (len(exp_secs) > 0 and len(act_secs) == 0):
        empty_sec_mismatch += 1
print(f"Empty vs Non-empty section mismatch in action failures: {empty_sec_mismatch}/{len(action_fails)}")


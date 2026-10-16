"""Evaluate judged evidence and reviewed generation. No substring correctness score."""
import argparse
import json
import collections
def read(p):return [json.loads(x) for x in open(p,encoding='utf-8') if x.strip()]
def score(cases,preds,judgments,view_ids=None,k=5):
 ps={p['id']:p for p in preds};js={j['id']:j for j in judgments};groups=collections.defaultdict(list);rows=[]
 for c in cases:
  if view_ids is not None and c['id'] not in view_ids:continue
  p=ps.get(c['id']);j=js.get(c['id']);r={'id':c['id'],'field_id':c['field_id'],'missing_prediction':p is None}
  gold={e['unit_id'] for e in c['evidence']}
  if p and gold:
   ret=list(dict.fromkeys(p.get('retrieved_unit_ids',[])))[:k];hits=gold&set(ret)
   r['judged_evidence_recall_at_k']=len(hits)/len(gold)
   r['mrr_at_k']=next((1/(i+1) for i,x in enumerate(ret) if x in gold),0)
   r['unjudged_retrieved_count']=len(set(ret)-gold)
  if p:r['action_accuracy']=int(p.get('action')==c['expected_action'])
  if j:
   for metric in ['correctness','completeness','faithfulness','citation_support','behavior_correct']:
    v=j.get(metric)
    if v is not None:
     if v not in [0,1]:raise ValueError('Judgment must be 0/1 or null: '+metric)
     r[metric]=v
   r['reviewer']=j.get('reviewer','unspecified')
  rows.append(r);groups[c['field_id']].append(r)
 metrics=['judged_evidence_recall_at_k','mrr_at_k','action_accuracy','correctness','completeness','faithfulness','citation_support','behavior_correct']
 fields={fid:{m:sum(r[m] for r in rr if m in r)/sum(m in r for r in rr) for m in metrics if any(m in r for r in rr)} for fid,rr in groups.items()}
 return {'expected_cases':len(rows),'missing_predictions':sum(r['missing_prediction'] for r in rows),'generation_judged_cases':sum('correctness' in r for r in rows),'macro_fields':{m:sum(v[m] for v in fields.values() if m in v)/sum(m in v for v in fields.values()) for m in metrics if any(m in v for v in fields.values())},'per_field':fields,'per_case':rows,'limitations':['IR labels are non-exhaustive: unjudged units are not proven negatives.','Generation metrics require semantic judgments; action labels alone do not establish correct abstention.','Partial runs report available cases only; do not claim full benchmark performance.']}
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--cases',default='cases.jsonl');ap.add_argument('--predictions',required=True);ap.add_argument('--judgments');ap.add_argument('--view');ap.add_argument('--split',choices=['dev','test']);ap.add_argument('--k',type=int,default=5);ap.add_argument('--out',default='scores.json');a=ap.parse_args()
 v=set(json.load(open(a.view))) if a.view else None
 cases=read(a.cases)
 if a.split:cases=[c for c in cases if c['split']==a.split]
 json.dump(score(cases,read(a.predictions),read(a.judgments) if a.judgments else [],v,a.k),open(a.out,'w'),ensure_ascii=False,indent=2)

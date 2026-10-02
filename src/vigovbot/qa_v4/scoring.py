"""RAG evaluator 4.1. Offline scoring; never calls your RAG endpoint."""
import argparse
import collections
import json
import math
import re
import statistics
import unicodedata
from importlib.metadata import version, PackageNotFoundError
from .scoring_legacy import score as legacy_score

def read(path):
    if not path: return []
    with open(path, encoding='utf-8') as f: return [json.loads(x) for x in f if x.strip()]

def unique(rows):
    out = {}
    for r in rows:
        if r['id'] in out: raise ValueError('Duplicate id: '+r['id'])
        out[r['id']] = r
    return out

def tokens(s): return re.findall(r'\w+', unicodedata.normalize('NFC',s).casefold(), re.UNICODE)
def normalize(s): return ' '.join(tokens(s))
def prf(a,b):
    hit=sum((collections.Counter(a)&collections.Counter(b)).values())
    p=hit/len(a) if a else float(not b); r=hit/len(b) if b else float(not a)
    return p,r,2*p*r/(p+r) if p+r else 0.0

def summary(xs):
    xs=sorted(x for x in xs if isinstance(x,(int,float)) and not isinstance(x,bool) and math.isfinite(x))
    if not xs: return {'n':0}
    def q(p):
        pos=(len(xs)-1)*p; lo=int(pos); hi=math.ceil(pos)
        return xs[lo]+(xs[hi]-xs[lo])*(pos-lo)
    return {'n':len(xs),'mean':statistics.mean(xs),'min':xs[0],'max':xs[-1], 'p50':q(.5),'p95':q(.95),'p99':q(.99)}

class VietnameseTokenizer:
    def tokenize(self,text): return tokens(text)

def aggregate(rows, keys):
    result={}
    for key in keys:
        vals=[r[key] for r in rows if isinstance(r.get(key),(float,int))]
        if vals: result[key]={'mean':statistics.mean(vals),'n':len(vals)}
    return result

def evaluate(cases,predictions,judgments,k=5,lexical=True,bert=False,model='bert-base-multilingual-cased',device='cpu',batch_size=8):
    if k<1: raise ValueError('k must be positive')
    cs=unique(cases); ps=unique(predictions); unique(judgments)
    valid=[p for p in predictions if p['id'] in cs and not p.get('error') and isinstance(p.get('answer'),str)]
    vp=unique(valid)
    output=legacy_score(cases,valid,judgments,k=k)
    rows=output['per_case']; rowmap={r['id']:r for r in rows}
    output['evaluation_version']='4.1.0'
    output['coverage']={'expected':len(cases),'successful_predictions':len(valid),'failed_or_missing':len(cases)-len(valid),'extra_prediction_ids':len(set(ps)-set(cs))}
    output['configuration']={'k':k,'normalization':'NFC + casefold + Unicode word tokens; Vietnamese syllables, not word segmentation','bert_enabled':bert,'bert_model':model if bert else None,'bert_device':device if bert else None}
    output['packages']={}
    for pkg in ['sacrebleu','rouge-score','bert-score','torch','transformers','psutil','nvidia-ml-py']:
        try: output['packages'][pkg]=version(pkg)
        except PackageNotFoundError: pass
    if lexical:
        from sacrebleu.metrics import BLEU,CHRF,TER
        from rouge_score.rouge_scorer import RougeScorer
        bleu=BLEU(tokenize='none',effective_order=True); chrf=CHRF(word_order=2); ter=TER()
        rouge=RougeScorer(['rouge1','rouge2','rougeL'],tokenizer=VietnameseTokenizer())
    pairs=[]; metrics=['judged_evidence_recall_at_k','mrr_at_k','action_accuracy','correctness','completeness','faithfulness','citation_support','behavior_correct','judged_hit_rate_at_k','exact_match','token_precision','token_recall','token_f1']
    for c in cases:
        r=rowmap[c['id']]; p=vp.get(c['id']); r['expected_action']=c['expected_action']
        r['prediction_success']=int(p is not None)
        if not p: continue
        gold={e['unit_id'] for e in c['evidence']}
        if gold: r['judged_hit_rate_at_k']=int(bool(gold & set(list(dict.fromkeys(p.get('retrieved_unit_ids',[])))[:k])))
        # Reference similarity on substantive responses only, not abstention/clarification templates.
        if c['expected_action'] not in ['answer','partial','correct_premise']: continue
        ref=c.get('reference_answer'); hyp=p['answer']
        if not isinstance(ref,str) or not ref.strip(): continue
        pairs.append((c['id'],hyp,ref))
        r['exact_match']=int(normalize(hyp)==normalize(ref))
        r['token_precision'],r['token_recall'],r['token_f1']=prf(tokens(hyp),tokens(ref))
        if lexical:
            r['sentence_bleu']=bleu.sentence_score(normalize(hyp),[normalize(ref)]).score
            r['chrf_plus_plus']=chrf.sentence_score(hyp,[ref]).score
            r['ter']=ter.sentence_score(normalize(hyp),[normalize(ref)]).score
            for name,s in rouge.score(ref,hyp).items():
                for label,value in zip(['precision','recall','f1'],s): r[name+'_'+label]=value
    if lexical:
        metrics+=['sentence_bleu','chrf_plus_plus','ter']+[n+'_'+x for n in ['rouge1','rouge2','rougeL'] for x in ['precision','recall','f1']]
        if pairs:
            hs=[normalize(x[1]) for x in pairs]; rs=[normalize(x[2]) for x in pairs]
            output['corpus_similarity']={'n':len(pairs),'bleu':bleu.corpus_score(hs,[rs]).score,'bleu_signature':str(bleu.get_signature()),'chrf_plus_plus':chrf.corpus_score([x[1] for x in pairs],[[x[2] for x in pairs]]).score,'ter':ter.corpus_score(hs,[rs]).score}
    if bert and pairs:
        from bert_score import score
        P,R,F,hashcode=score([x[1] for x in pairs],[x[2] for x in pairs],model_type=model,lang='vi',device=device,batch_size=batch_size,rescale_with_baseline=False,return_hash=True,verbose=True)
        output['configuration']['bert_hash']=hashcode
        for i,(cid,_,_) in enumerate(pairs):
            for name,values in [('bertscore_precision',P),('bertscore_recall',R),('bertscore_f1',F)]: rowmap[cid][name]=float(values[i])
        metrics+=['bertscore_precision','bertscore_recall','bertscore_f1']
    metrics+=['prediction_success']
    output['overall_available']=aggregate(rows,metrics)
    output['per_field']={f:aggregate([r for r in rows if r['field_id']==f],metrics) for f in sorted({r['field_id'] for r in rows})}
    output['macro_fields']={m:{'mean':statistics.mean([v[m]['mean'] for v in output['per_field'].values() if m in v]),'n_fields':sum(m in v for v in output['per_field'].values())} for m in metrics if any(m in v for v in output['per_field'].values())}
    output['per_action']={a:aggregate([r for r in rows if r['expected_action']==a],metrics) for a in sorted({r['expected_action'] for r in rows})}
    actions=sorted({c['expected_action'] for c in cases}); output['action_classification']={}
    for a in actions:
        tp=sum(c['expected_action']==a and vp.get(c['id'],{}).get('action')==a for c in cases)
        fp=sum(c['expected_action']!=a and vp.get(c['id'],{}).get('action')==a for c in cases)
        fn=sum(c['expected_action']==a and vp.get(c['id'],{}).get('action')!=a for c in cases)
        p=tp/(tp+fp) if tp+fp else 0; r=tp/(tp+fn) if tp+fn else 0
        output['action_classification'][a]={'precision':p,'recall':r,'f1':2*p*r/(p+r) if p+r else 0,'support':tp+fn}
    output['action_accuracy_all_expected']=sum(vp.get(c['id'],{}).get('action')==c['expected_action'] for c in cases)/len(cases) if cases else None
    output['latency_seconds_success']=summary([p.get('latency_seconds') for p in valid])
    output['latency_seconds_failed']=summary([p.get('latency_seconds') for p in predictions if p['id'] in cs and p.get('error')])
    output['server_telemetry']={key:summary([p.get('telemetry',{}).get(key) for p in valid]) for key in ['retrieval_seconds','generation_seconds','ttft_seconds','output_tokens','generation_tokens_per_second','cost_usd']}
    conversations=collections.defaultdict(list)
    for c in cases:
        if c.get('conversation_id'): conversations[c['conversation_id']].append(rowmap[c['id']])
    fully_judged=[rr for rr in conversations.values() if all('behavior_correct' in r and r['prediction_success'] for r in rr)]
    output['conversation_behavior_success']={'n_fully_judged_in_selected_view':len(fully_judged),'rate':statistics.mean([all(r['behavior_correct']==1 for r in rr) for rr in fully_judged]) if fully_judged else None,'note':'Selected view must include every conversation turn for whole-conversation interpretation.'}
    output['limitations']+=['Similarity is not factual correctness or faithfulness.','Reference text metrics exclude abstain and clarify.','No precision/MAP/nDCG: qrels are non-exhaustive.','Missing/failed predictions excluded from similarity; see coverage and all-expected action accuracy.','BERTScore may truncate long texts to model maximum length.','No RAG model was run to build this package.']
    return output

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--cases',default='cases.jsonl'); ap.add_argument('--predictions',required=True); ap.add_argument('--judgments'); ap.add_argument('--view'); ap.add_argument('--split',choices=['dev','test']); ap.add_argument('--k',type=int,default=5); ap.add_argument('--out',default='scores.json'); ap.add_argument('--no-lexical',action='store_true'); ap.add_argument('--bertscore',action='store_true'); ap.add_argument('--bert-model',default='bert-base-multilingual-cased'); ap.add_argument('--bert-device',default='cpu'); ap.add_argument('--bert-batch-size',type=int,default=8)
    a=ap.parse_args(); cases=read(a.cases)
    if a.view:
        with open(a.view,encoding='utf-8') as f: ids=set(json.load(f))
        cases=[c for c in cases if c['id'] in ids]
    if a.split: cases=[c for c in cases if c['split']==a.split]
    preds=read(a.predictions)
    modes={p.get('history_mode') for p in preds if p.get('history_mode')}
    if len(modes)>1: raise ValueError('Do not mix history modes in one report')
    out=evaluate(cases,preds,read(a.judgments),a.k,not a.no_lexical,a.bertscore,a.bert_model,a.bert_device,a.bert_batch_size)
    out['configuration']['history_modes']=sorted(modes)
    with open(a.out,'w',encoding='utf-8') as f: json.dump(out,f,ensure_ascii=False,indent=2,allow_nan=False)
if __name__=='__main__': main()

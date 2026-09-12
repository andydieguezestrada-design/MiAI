from __future__ import annotations
import json, math, re, sqlite3, tempfile, time
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]; sys.path.insert(0,str(ROOT))
from python.rag.store import RAGStore
DATA=Path(__file__).parent/'dataset.json'
TOPICS=['arquitectura','memoria','herramientas','streaming','vision','seguridad']
CUE={
 'cerebro':'arquitectura','reutilizable':'arquitectura','cognitiva':'arquitectura','aplicaciones':'arquitectura','integrar':'arquitectura','razonamiento':'arquitectura',
 'recuerda':'memoria','conserva':'memoria','hechos':'memoria','persistentes':'memoria','futuras':'memoria','conocimiento':'memoria',
 'registro':'herramientas','funciones':'herramientas','valida':'herramientas','argumentos':'herramientas','ejecuta':'herramientas','operaciones':'herramientas',
 'progresivamente':'streaming','tokens':'streaming','eventos':'streaming','sse':'streaming','latencia':'streaming',
 'imágenes':'vision','imagenes':'vision','multimodal':'vision','archivo':'vision','visión':'vision','vision':'vision','codificadas':'vision',
 'autenticación':'seguridad','autorización':'seguridad','endpoints':'seguridad','sensibles':'seguridad','despliegue':'seguridad','local':'seguridad',
}
STOP={'el','la','los','las','de','del','y','en','un','una','que','para','por','con','se','su','como','qué','cual','cuál','es','al','una','uno','sobre','desde','cómo'}
def toks(s): return {x for x in re.findall(r'[\wÀ-ÿ]{2,}',s.lower()) if x not in STOP}
def emb(text):
 v=[0.0]*len(TOPICS)
 for tok in re.findall(r'[\wÀ-ÿ]{2,}',text.lower()):
  if tok in CUE: v[TOPICS.index(CUE[tok])]+=1
 n=math.sqrt(sum(x*x for x in v)); return [x/n for x in v] if n else v
def cosine(a,b):
 n1=math.sqrt(sum(x*x for x in a)); n2=math.sqrt(sum(x*x for x in b)); return sum(x*y for x,y in zip(a,b))/(n1*n2) if n1 and n2 else 0.0
def rerank(q, rows):
 qt=toks(q); qv=emb(q); out=[]
 for r in rows:
  text=f"{r['title']} {r['content']}"; tt=toks(text)
  lexical=len(qt&tt)/max(1,len(qt))
  semantic=cosine(qv,emb(text))
  phrase=1.0 if q.lower() in text.lower() else 0.0
  title=len(qt & toks(r['title']))/max(1,len(qt))
  coverage=len(qt&tt)/max(1,len(qt))
  # Semantic-first reranker. Lexical evidence is tie-breaking/contextual,
  # while a strong exact phrase can rescue a genuinely lexical match.
  score=0.68*semantic + 0.17*coverage + 0.10*title + 0.05*phrase
  x=dict(r); x.update(_rerank_score=score,_semantic=semantic,_coverage=coverage,_title=title,_phrase=phrase,_lexical=lexical); out.append(x)
 return sorted(out,key=lambda x:x['_rerank_score'],reverse=True)
def metrics(rows):
 pos=[r for r in rows if r['type']=='positive']; neg=[r for r in rows if r['type']=='negative']
 def hit(n): return sum(r['gold'] in r['ids'][:n] for r in pos)/len(pos)
 mrr=sum((1/(r['ids'].index(r['gold'])+1) if r['gold'] in r['ids'] else 0) for r in pos)/len(pos)
 fpr=sum(bool(r['ids']) for r in neg)/len(neg)
 return {'positive_hit_rate_at1':hit(1),'positive_hit_rate_at3':hit(3),'mrr':mrr,'false_positive_rate':fpr,'no_context_accuracy':1-fpr}
def main():
 data=json.loads(DATA.read_text()); project='rag_quality_b3'
 with tempfile.NamedTemporaryFile(suffix='.sqlite3') as f:
  store=RAGStore(f.name,embedder=emb)
  for i in range(360): store.add_document(project,f'Distractor {i}',f'Información genérica sobre mantenimiento de sistemas número {i}.')
  for d in data['documents']: store.add_document(project,d['title'],d['content'],metadata={'gold_id':d['id']})
  configs=[('rerank_gate_020',0.20,0.0),('rerank_gate_030',0.30,0.0),('rerank_gate_040',0.40,0.0),('rerank_semantic_020',0.20,0.20),('rerank_semantic_030',0.20,0.30)]
  results=[]
  for name,gate,min_sem in configs:
   rows=[]; ms=0
   for q in data['queries']:
    t0=time.perf_counter(); candidates=store.search(project,q['text'],limit=12); ranked=rerank(q['text'],candidates)
    chosen=[r for r in ranked if r['_rerank_score']>=gate and r['_semantic']>=min_sem][:3]
    ms+=(time.perf_counter()-t0)*1000
    ids=[]
    for r in chosen:
     md=r.get('metadata'); md=json.loads(md) if isinstance(md,str) else (md or {})
     ids.append(md.get('gold_id',r['title'].lower()))
    rows.append({'id':q['id'],'type':q['type'],'gold':q['gold'],'ids':ids})
   m=metrics(rows); m.update({'config':name,'gate':gate,'min_semantic':min_sem,'avg_latency_ms':ms/len(data['queries'])}); results.append(m)
  report={'version':'V0.12-B3','candidate_pool':366,'method':'semantic-first reranking over hybrid candidates + quality gate','fixture':'deterministic semantic topic embedding','results':results}
  out=Path(__file__).parent/'B3_RESULTS.json'; out.write_text(json.dumps(report,ensure_ascii=False,indent=2)); print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__': main()

from __future__ import annotations
import json, math, re, sqlite3, tempfile, time
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
from python.rag.store import RAGStore
DATA=Path(__file__).parents[1]/"dataset.json"
TOPICS=['arquitectura','memoria','herramientas','streaming','vision','seguridad']
CUE={
 'cerebro':'arquitectura','reutilizable':'arquitectura','cognitiva':'arquitectura','aplicaciones':'arquitectura','integrar':'arquitectura','razonamiento':'arquitectura',
 'recuerda':'memoria','conserva':'memoria','hechos':'memoria','persistentes':'memoria','futuras':'memoria','conocimiento':'memoria',
 'registro':'herramientas','funciones':'herramientas','valida':'herramientas','argumentos':'herramientas','ejecuta':'herramientas','operaciones':'herramientas',
 'progresivamente':'streaming','tokens':'streaming','eventos':'streaming','sse':'streaming','latencia':'streaming',
 'imágenes':'vision','imagenes':'vision','multimodal':'vision','archivo':'vision','visión':'vision','vision':'vision','codificadas':'vision',
 'autenticación':'seguridad','autorización':'seguridad','endpoints':'seguridad','sensibles':'seguridad','despliegue':'seguridad','local':'seguridad',
}
def emb(text):
    v=[0.0]*len(TOPICS)
    for tok in re.findall(r'[\wÀ-ÿ]{2,}',text.lower()):
        if tok in CUE: v[TOPICS.index(CUE[tok])]+=1
    n=math.sqrt(sum(x*x for x in v))
    return [x/n for x in v] if n else v

def lexical_score(q,t):
    tok=lambda s:set(re.findall(r'[\wÀ-ÿ]{2,}',s.lower()))
    qt=tok(q); tt=tok(t)
    return len(qt&tt)/max(1,len(qt))

def metrics(rows):
    pos=[r for r in rows if r['type']=='positive']; neg=[r for r in rows if r['type']=='negative']
    hit=sum(r['gold'] in r['ids'][:3] for r in pos)/len(pos)
    hit1=sum(r['gold'] in r['ids'][:1] for r in pos)/len(pos)
    mrr=sum((1/(r['ids'].index(r['gold'])+1) if r['gold'] in r['ids'] else 0) for r in pos)/len(pos)
    fpr=sum(bool(r['ids']) for r in neg)/len(neg)
    noctx=sum(not r['ids'] for r in neg)/len(neg)
    return hit1,hit,mrr,fpr,noctx

def main():
    data=json.loads(DATA.read_text()); docs=data['documents']; queries=data['queries']; project='rag_quality_b2'
    with tempfile.NamedTemporaryFile(suffix='.sqlite3') as f:
        # hybrid/semantic candidate pool is 300 in V0.11.1. Add 360 distractors before gold docs.
        store=RAGStore(f.name, embedder=emb)
        for i in range(360):
            store.add_document(project,f'Distractor {i}',f'Información genérica sobre mantenimiento de sistemas número {i}.')
        for d in docs:
            store.add_document(project,d['title'],d['content'],metadata={'gold_id':d['id']})
        out=[]
        for mode in ['lexical','semantic','hybrid']:
            rows=[]; total_ms=0
            for q in queries:
                t0=time.perf_counter()
                if mode=='lexical':
                    # Force lexical-only behavior by a separate store with no embedder, same DB.
                    s=RAGStore(f.name, embedder=None); result=s.search(project,q['text'],limit=3)
                elif mode=='semantic':
                    # Production store with embeddings uses hybrid; emulate pure semantic ranking over all 300+ chunks.
                    conn=sqlite3.connect(f.name); conn.row_factory=sqlite3.Row
                    qv=emb(q['text']); rr=conn.execute('SELECT c.*,e.embedding FROM chunks c JOIN chunk_embeddings e ON e.chunk_id=c.id WHERE c.project=?',(project,)).fetchall(); conn.close()
                    scored=[]
                    for r in rr:
                        v=json.loads(r['embedding']); scored.append((sum(a*b for a,b in zip(qv,v)),r))
                    scored.sort(key=lambda x:x[0],reverse=True)
                    result=[dict(r) for s,r in scored[:3] if s>=0.20]
                else:
                    result=store.search(project,q['text'],limit=3)
                total_ms+=(time.perf_counter()-t0)*1000
                ids=[]
                for r in result:
                    gid=r.get('metadata')
                    if isinstance(gid,str):
                        try: gid=json.loads(gid)
                        except: gid={}
                    ids.append(gid.get('gold_id') if isinstance(gid,dict) and gid.get('gold_id') else r['title'].lower())
                # fallback title matching for gold docs
                mapped=[]
                for x,r in zip(ids,result):
                    mapped.append(x)
                rows.append({'id':q['id'],'type':q['type'],'gold':q['gold'],'ids':mapped})
            m=metrics(rows)
            out.append({'mode':mode,'positive_hit_rate_at3':m[1],'positive_hit_rate_at1':m[0],'mrr':m[2],'false_positive_rate':m[3],'no_context_accuracy':m[4],'avg_latency_ms':total_ms/len(queries)})
        report={'version':'V0.12-B2','candidate_pool':366,'fixture':'deterministic semantic topic embedding','results':out}
        (Path(__file__).parents[1]/'B2_RESULTS.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
        print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__': main()

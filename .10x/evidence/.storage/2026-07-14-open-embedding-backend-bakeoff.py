import argparse, json, os, platform, resource, statistics, threading, time, traceback
from pathlib import Path
import numpy as np
try:
    import psutil
except ImportError:
    psutil=None

MODEL='BAAI/bge-small-en-v1.5'
BATCH=32

def rss_bytes():
    if psutil is not None:
        return psutil.Process().memory_info().rss
    # macOS ru_maxrss is bytes; this is a high-water mark rather than instantaneous RSS.
    return int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)

def encode_st(model, texts):
    return np.asarray(model.encode(texts, batch_size=BATCH, normalize_embeddings=True, show_progress_bar=False), dtype=np.float32)

def build(lane):
    if lane.startswith('torch') or lane.startswith('st_'):
        from sentence_transformers import SentenceTransformer
        if lane == 'torch_mps':
            model=SentenceTransformer(MODEL, device='mps')
        elif lane == 'st_onnx_cpu':
            model=SentenceTransformer('/tmp/buoy-embedding-bakeoff/models/st-onnx', backend='onnx', model_kwargs={'provider':'CPUExecutionProvider'})
        elif lane == 'st_onnx_coreml':
            model=SentenceTransformer('/tmp/buoy-embedding-bakeoff/models/st-onnx', backend='onnx', model_kwargs={'provider':'CoreMLExecutionProvider'})
        elif lane == 'st_openvino_cpu':
            model=SentenceTransformer('/tmp/buoy-embedding-bakeoff/models/st-openvino', backend='openvino')
        return model, lambda xs: encode_st(model,xs)
    if lane == 'fastembed_onnx':
        from fastembed import TextEmbedding
        configured_threads=os.environ.get('FASTEMBED_THREADS')
        kwargs={'threads':int(configured_threads)} if configured_threads else {}
        model=TextEmbedding(model_name=MODEL, providers=['CPUExecutionProvider'], **kwargs)
        return model, lambda xs: np.asarray(list(model.embed(xs, batch_size=BATCH)),dtype=np.float32)
    if lane == 'mlx_bf16':
        import mlx.core as mx
        from mlx_embeddings import load, generate
        model,tok=load('mlx-community/bge-small-en-v1.5-bf16')
        def enc(xs):
            chunks=[]
            for i in range(0,len(xs),BATCH):
                out=generate(model,tok,xs[i:i+BATCH],max_length=512)
                # BGE sentence-transformers contract uses normalized CLS pooling.
                v=out.last_hidden_state[:,0,:]
                v=v/mx.sqrt(mx.sum(v*v,axis=1,keepdims=True))
                mx.eval(v)
                chunks.append(np.asarray(v,dtype=np.float32))
            return np.concatenate(chunks)
        return model,enc
    raise ValueError(lane)

def top10(doc, query): return np.argsort(-(doc@query))[:10].tolist()
def cos_rows(a,b):
    aa=a/np.linalg.norm(a,axis=1,keepdims=True); bb=b/np.linalg.norm(b,axis=1,keepdims=True)
    return np.sum(aa*bb,axis=1)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('lane'); ap.add_argument('--output',required=True); args=ap.parse_args()
    payload=json.loads(Path('/tmp/buoy-embedding-bakeoff/inputs.json').read_text()); texts=payload['texts']; query=payload['query']
    result={'lane':args.lane,'status':'failed','model':MODEL,'samples':len(texts),'batch_size':BATCH,'python':platform.python_version(),'platform':platform.platform()}
    try:
        rss0=rss_bytes(); t=time.perf_counter(); model,encode=build(args.lane); load_s=time.perf_counter()-t; rss_load=rss_bytes()
        # materialize lazy runtimes outside measured warm runs
        warm=encode(texts[:BATCH]); assert warm.shape==(BATCH,384),warm.shape
        peaks=[]; seconds=[]; vec=None
        for _ in range(3):
            stop=False; peak=[rss_bytes()]
            def sample():
                while not stop:
                    peak[0]=max(peak[0],rss_bytes()); time.sleep(.01)
            th=threading.Thread(target=sample,daemon=True); th.start()
            t=time.perf_counter(); vec=encode(texts); seconds.append(time.perf_counter()-t); stop=True; th.join(); peaks.append(peak[0])
        q=encode([query])[0]
        norms=np.linalg.norm(vec,axis=1)
        result.update({'status':'ok','load_seconds':load_s,'rss_before_bytes':rss0,'rss_after_load_bytes':rss_load,'peak_rss_bytes':max(peaks),'seconds_runs':seconds,'median_seconds':statistics.median(seconds),'median_rows_per_second':len(texts)/statistics.median(seconds),'dimension':int(vec.shape[1]),'norm_min':float(norms.min()),'norm_max':float(norms.max()),'top10':top10(vec,q)})
        if args.lane=='torch_mps':
            np.save('/tmp/buoy-embedding-bakeoff/baseline_docs.npy',vec); np.save('/tmp/buoy-embedding-bakeoff/baseline_query.npy',q)
        else:
            ref=np.load('/tmp/buoy-embedding-bakeoff/baseline_docs.npy'); rq=np.load('/tmp/buoy-embedding-bakeoff/baseline_query.npy')
            cs=cos_rows(ref,vec); base_top=top10(ref,rq); candidate_top=top10(vec,q)
            query_cosine=float(cos_rows(rq.reshape(1,-1),q.reshape(1,-1))[0])
            result['parity']={'min_document_cosine':float(cs.min()),'mean_document_cosine':float(cs.mean()),'p01_document_cosine':float(np.quantile(cs,.01)),'query_cosine':query_cosine,'exact_top10_ordered_equality':candidate_top==base_top,'baseline_top10':base_top}
    except Exception as exc:
        result.update({'error_type':type(exc).__name__,'error':str(exc),'traceback':traceback.format_exc(limit=20)})
    Path(args.output).write_text(json.dumps(result,indent=2))
    print(json.dumps({k:v for k,v in result.items() if k not in {'traceback','top10'}},indent=2))

if __name__=='__main__': main()

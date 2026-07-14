#!/usr/bin/env bash
# Reproduction orchestration for the 2026-07-14 no-remote backend bake-off.
# Run from the repository root. Candidate artifacts remain under /tmp for inspection.
set -euo pipefail

ROOT=$(pwd)
D=/tmp/buoy-embedding-bakeoff
V="$D/venv/bin/python"
HARNESS="$ROOT/.10x/evidence/.storage/2026-07-14-open-embedding-backend-bakeoff.py"
SOURCE="$ROOT/artifacts/site-crawls/iceberg-apache-org-plan/chunks.jsonl"
rm -rf "$D"
mkdir -p "$D/models"
cp "$HARNESS" "$D/benchmark.py"

uv venv "$D/venv"
uv pip install --python "$V" \
  'sentence-transformers[onnx,openvino]==5.6.0' \
  'fastembed>=0.7,<0.8' \
  'mlx-embeddings>=0.0.4' psutil

"$V" - <<'PY'
import onnxruntime as ort
from fastembed import TextEmbedding
print('providers', ort.get_available_providers())
print('fastembed exact-model support', [x for x in TextEmbedding.list_supported_models() if 'bge-small-en-v1.5' in str(x)])
PY

SOURCE="$SOURCE" OUT="$D/inputs.json" .venv/bin/python - <<'PY'
import json, os
from pathlib import Path
source=Path(os.environ['SOURCE']); out=Path(os.environ['OUT'])
texts=[]; row_ids=[]
with source.open() as f:
    for _ in range(1024):
        x=json.loads(next(f)); parts=[]
        if x.get('title'): parts.append(f"Title: {x['title']}")
        if x.get('section_path'): parts.append(f"Section: {x['section_path']}")
        parts.append(x['content'])
        texts.append('\n\n'.join(p for p in parts if str(p).strip()))
        row_ids.append(x['row_id'])
out.write_text(json.dumps({'texts':texts,'row_ids':row_ids,'query':'How does Apache Iceberg handle table metadata and snapshots?'}))
PY

cat > "$D/prepare_st.py" <<'PY'
from pathlib import Path
from sentence_transformers import SentenceTransformer
for backend,name in [('onnx','st-onnx'),('openvino','st-openvino')]:
    path=Path('/tmp/buoy-embedding-bakeoff/models')/name
    model=SentenceTransformer('BAAI/bge-small-en-v1.5', backend=backend)
    model.encode(['warm export'], normalize_embeddings=True)
    model.save_pretrained(str(path))
PY
"$V" "$D/prepare_st.py" > "$D/prepare.log" 2>&1

# A subprocess wrapper preserves stdout/stderr/exit status and enforces the actual
# five-minute per-lane bound used for failed lanes. Exit 124 means timeout;
# negative SIGKILL is normalized to shell-style 137.
run_lane() {
  local python=$1 lane=$2 bound=${3:-300} label=${4:-$2}
  LANE="$lane" LABEL="$label" PYTHON_BIN="$python" BOUND="$bound" "$V" - <<'PY'
import json, os, subprocess, time
from pathlib import Path
lane=os.environ['LANE']; label=os.environ['LABEL']; python=os.environ['PYTHON_BIN']; bound=int(os.environ['BOUND'])
cmd=[python,'/tmp/buoy-embedding-bakeoff/benchmark.py',lane,'--output',f'/tmp/buoy-embedding-bakeoff/{label}.json']
started=time.perf_counter()
try:
    result=subprocess.run(cmd,text=True,capture_output=True,timeout=bound)
    code=result.returncode if result.returncode >= 0 else 128-result.returncode
    meta={'lane':lane,'label':label,'command':cmd,'timeout_seconds':bound,'elapsed_seconds':time.perf_counter()-started,'exit_code':code,'timed_out':False}
except subprocess.TimeoutExpired as exc:
    result=None
    meta={'lane':lane,'label':label,'command':cmd,'timeout_seconds':bound,'elapsed_seconds':time.perf_counter()-started,'exit_code':124,'timed_out':True}
    Path(f'/tmp/buoy-embedding-bakeoff/{label}.stdout.log').write_text(exc.stdout or '')
    Path(f'/tmp/buoy-embedding-bakeoff/{label}.stderr.log').write_text(exc.stderr or '')
else:
    Path(f'/tmp/buoy-embedding-bakeoff/{label}.stdout.log').write_text(result.stdout)
    Path(f'/tmp/buoy-embedding-bakeoff/{label}.stderr.log').write_text(result.stderr)
Path(f'/tmp/buoy-embedding-bakeoff/{label}.process.json').write_text(json.dumps(meta,indent=2)+'\n')
print(json.dumps(meta))
PY
}

run_lane "$ROOT/.venv/bin/python" torch_mps 300
run_lane "$V" st_onnx_cpu 300
run_lane "$V" st_onnx_coreml 300
run_lane "$V" st_openvino_cpu 300
run_lane "$V" fastembed_onnx 300 fastembed_onnx_default
FASTEMBED_THREADS=4 run_lane "$V" fastembed_onnx 300 fastembed_onnx_threads4
run_lane "$V" mlx_bf16 300

"$V" - <<'PY'
import hashlib, importlib, json, platform
from pathlib import Path
D=Path('/tmp/buoy-embedding-bakeoff')
source=Path('artifacts/site-crawls/iceberg-apache-org-plan/chunks.jsonl')
inputs=json.loads((D/'inputs.json').read_text())
versions={}
for name in ['sentence_transformers','torch','onnxruntime','openvino','fastembed','mlx','mlx_embeddings','numpy']:
    try:
        versions[name]=getattr(importlib.import_module(name),'__version__','unknown')
    except Exception as exc:
        versions[name]=f'error: {exc}'
print(json.dumps({
  'host':platform.platform(),
  'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
  'row_ids_sha256':hashlib.sha256('\n'.join(inputs['row_ids']).encode()).hexdigest(),
  'candidate_versions':versions,
  'result_files':sorted(str(p) for p in D.glob('*.json')),
},indent=2))
PY

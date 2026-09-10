"""Record final artifacts and read-only preservation checks; never load providers/models."""
import email
import hashlib
import json
from pathlib import Path
import subprocess
import tarfile
import zipfile

ROOT = Path('/Users/crlough/Code/personal/turbo-search.worktrees/buoy-mcp-server')
E = ROOT / '.10x/evidence/.storage/buoy-mcp-installation'
T = Path((E / 'environment-path.txt').read_text().strip())
head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
assert head == (E / 'source-head.txt').read_text().strip()
assert not subprocess.check_output(['git', 'status', '--porcelain=v1', '--untracked-files=no'], cwd=ROOT)
report = {'source_head': head, 'source_tree': subprocess.check_output(['git', 'rev-parse', 'HEAD^{tree}'], cwd=ROOT, text=True).strip(), 'branch': subprocess.check_output(['git', 'branch', '--show-current'], cwd=ROOT, text=True).strip(), 'artifacts': {}}
for artifact in sorted((T / 'dist').iterdir()):
    if artifact.name.startswith('.'):
        continue
    raw = artifact.read_bytes()
    if artifact.suffix == '.whl':
        with zipfile.ZipFile(artifact) as archive:
            names = archive.namelist()
            metadata_raw = archive.read(next(n for n in names if n.endswith('.dist-info/METADATA')))
            adapter = archive.read('buoy_search/mcp.py')
            entrypoint = archive.read(next(n for n in names if n.endswith('.dist-info/entry_points.txt'))).decode()
            assert entrypoint == '[console_scripts]\nbuoy = buoy_search.cli.entrypoint:main\n'
            report['entrypoint'] = entrypoint
    else:
        with tarfile.open(artifact) as archive:
            original = archive.getnames()
            prefix = original[0].split('/')[0] + '/'
            names = [name.removeprefix(prefix) for name in original]
            metadata_raw = archive.extractfile(prefix + 'PKG-INFO').read()
            adapter = archive.extractfile(prefix + 'src/buoy_search/mcp.py').read()
            assert archive.extractfile(prefix + 'pyproject.toml').read() == (ROOT / 'pyproject.toml').read_bytes()
            assert archive.extractfile(prefix + 'docs/mcp.md').read() == (ROOT / 'docs/mcp.md').read_bytes()
            assert archive.extractfile(prefix + 'README.md').read() == (ROOT / 'README.md').read_bytes()
    assert adapter == (ROOT / 'src/buoy_search/mcp.py').read_bytes()
    for name in names:
        assert not any(part in {'.10x', '.git', '.env', '.venv', 'skills', 'web', 'node_modules', 'outputs', 'artifacts'} for part in Path(name).parts), name
        assert not name.startswith(('buoy_search/server/', 'src/buoy_search/server/', 'buoy_search/static/', 'src/buoy_search/static/')), name
    metadata = email.message_from_bytes(metadata_raw)
    assert metadata['Version'] == '0.5.2.dev131+g89cecb2ed'
    assert set(metadata.get_all('Provides-Extra')) == {'mcp', 'bigquery', 'snowflake'}
    requirements = metadata.get_all('Requires-Dist')
    for dependency in ('mcp==2.2.0', 'anyio<5,>=4.5', 'pydantic<3,>=2.11'):
        assert dependency + "; extra == 'mcp'" in requirements
    assert not any('mcp[cli]' in value for value in requirements)
    record = {'sha256': hashlib.sha256(raw).hexdigest(), 'size_bytes': len(raw), 'version': metadata['Version'], 'extra_requirements': [r for r in requirements if "extra == 'mcp'" in r], 'member_count': len(names), 'adapter_sha256': hashlib.sha256(adapter).hexdigest()}
    report['artifacts'][artifact.name] = record
    (E / (artifact.name + '.members.txt')).write_text('\n'.join(names) + '\n')
    (E / (artifact.name + '.metadata.txt')).write_bytes(metadata_raw)
    # Retain byte-for-byte artifacts, rather than requiring temporary paths to survive.
    (E / artifact.name).write_bytes(raw)
manifest = json.loads((ROOT / '.10x/evidence/.storage/2026-09-10-buoy-mcp-original-worktree.json').read_bytes())
original = Path(manifest['source_worktree'])
for item in manifest['files']:
    path = original / item['path']
    assert path.exists() == item['exists'], item['path']
    if item['exists']:
        assert hashlib.sha256(path.read_bytes()).hexdigest() == item['sha256'], item['path']
report['original_preservation_verified'] = manifest['files']
readme_before = subprocess.check_output(['git', 'show', 'f9ddf19:README.md'], cwd=ROOT)
assert (ROOT / 'README.md').read_bytes() == readme_before.replace(b'- [Retrieve with automatic routing](docs/retrieval.md)\n', b'- [Retrieve with automatic routing](docs/retrieval.md)\n- [Connect an MCP client](docs/mcp.md)\n')
subprocess.run(['git', 'diff', '--exit-code', 'f9ddf19', '--', 'src', 'pyproject.toml', 'uv.lock', '.10x/specs'], cwd=ROOT, check=True)
workflow_before = subprocess.check_output(['git', 'show', 'f9ddf19:.github/workflows/ci.yml'], cwd=ROOT).decode()
workflow_now = (ROOT / '.github/workflows/ci.yml').read_text()
heredoc = lambda value: value.split("<<'PY'\n", 1)[1].split('\n          PY', 1)[0]
assert heredoc(workflow_before) == heredoc(workflow_now)
report['unchanged_runtime_specs_packaging_and_base_data_assertions'] = True
report['readme_change_exactly_one_link'] = True
report['isolated_home_remaining_entries'] = [str(p.relative_to(T / 'h')) for p in (T / 'h').rglob('*')]
report['runtime_cache_remaining_entries'] = [str(p.relative_to(T / 'cache')) for p in (T / 'cache').rglob('*')]
assert not report['isolated_home_remaining_entries'] and not report['runtime_cache_remaining_entries']
report['retained_for_review'] = str(T)
report['cleanup'] = 'Smoke HOME fixtures removed on exit; no runtime assets remain. Disposable wheel environments/artifacts and dependency cache retained for review; no user installation touched.'
(E / 'artifacts-preservation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))

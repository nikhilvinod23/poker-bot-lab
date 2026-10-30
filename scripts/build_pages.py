"""Publish an explicit allowlist: no SQLite files, logs, secrets or checkpoints."""
import ast
import shutil
import tarfile
import hashlib
from importlib.metadata import distribution
from pathlib import Path

root=Path(__file__).resolve().parents[1]
out=root/'pages-build'
out.mkdir(exist_ok=True)
static=root/'pokerbot'/'static'
for name in ('index.html','style.css','sidebar.css','app.js'):
    shutil.copyfile(static/name,out/name)
html=(out/'index.html').read_text(encoding='utf-8').replace('/static/','./')
# A new layout gets new asset URLs, including on phones with cached CSS/JS.
revision=hashlib.sha256(b''.join((static/name).read_bytes() for name in ('index.html','style.css','sidebar.css','app.js'))+(root/'pages-runtime'/'browser-runtime.js').read_bytes()).hexdigest()[:12]
for asset in ('style.css','sidebar.css','app.js','browser-runtime.js'):
    html=html.replace(f'./{asset}"',f'./{asset}?v={revision}"')
(out/'index.html').write_text(html,encoding='utf-8')
for name in ('browser-runtime.js','python-worker.js'):
    shutil.copyfile(root/'pages-runtime'/name,out/name)
py=out/'python'/'pokerbot';py.mkdir(parents=True,exist_ok=True)
for name in ('__init__.py','engine.py','browser_api.py'):
    shutil.copyfile(root/'pokerbot'/name,py/name)
table=(root/'pokerbot'/'table.py').read_text(encoding='utf-8')
start=table.index('import ast');end=table.index('class Table:')
table=table[:start]+'from .bot_baseline import LimitholdemRuleAgentV1\n\n'+table[end:]
table=table.replace("datetime.now(ZoneInfo('America/Chicago'))","datetime.now(timezone.utc)")
(py/'table.py').write_text(table,encoding='utf-8')
dist=distribution('rlcard')
source=dist.locate_file('rlcard/models/limitholdem_rule_models.py').read_text(encoding='utf-8')
tree=ast.parse(source)
agent=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='LimitholdemRuleAgentV1')
(py/'bot_baseline.py').write_text('# Unmodified RLCard 1.2.0 agent; see RLCard-LICENSE.md\n'+ast.get_source_segment(source,agent)+'\n',encoding='utf-8')
license_file=next(f for f in dist.files if f.name in ('LICENSE.md','LICENSE') and 'dist-info' in str(f))
shutil.copyfile(dist.locate_file(license_file),out/'RLCard-LICENSE.md')
(out/'.nojekyll').touch()
runtime=out/'runtime';runtime.mkdir(exist_ok=True)
shutil.copyfile(root/'pages-runtime'/'Pyodide-LICENSE.txt',runtime/'LICENSE.txt')
with tarfile.open(root/'runtime-cache'/'pyodide-core-314.0.7.tar.bz2') as archive:
    for member in archive.getmembers():
        if member.isfile() and Path(member.name).name in {'pyodide.js','pyodide.mjs','pyodide.asm.mjs','pyodide.asm.wasm','pyodide-lock.json','python_stdlib.zip'}:
            name=Path(member.name).name
            (runtime/name).write_bytes(archive.extractfile(member).read())
print(out)

"""Move complete trees after checking containment; retain original file contents."""
from pathlib import Path
import hashlib
import json
import shutil

ROOT = Path(__file__).resolve().parents[3]
REPORT = ROOT/'data/maintenance/cleanup_20260906'
mapping=[]
moves=[]

def relocate(old,new, runtime=False):
    source=(ROOT/old).resolve(); dest=(ROOT/new).resolve()
    assert source.is_relative_to(ROOT) and source!=ROOT
    assert dest.is_relative_to(ROOT) and dest!=ROOT
    if not source.exists():
        if not dest.exists(): return
    elif not dest.exists():
        dest.parent.mkdir(parents=True,exist_ok=True)
        try:
            source.rename(dest)
        except PermissionError:
            if not source.is_dir(): raise
            dest.mkdir(exist_ok=True)
            for child in list(source.iterdir()):
                relocate(child.relative_to(ROOT).as_posix(), (dest/child.name).relative_to(ROOT).as_posix())
            source.rmdir()
    else:
        assert source.is_dir() and dest.is_dir(), dest
        for child in list(source.iterdir()):
            relocate(child.relative_to(ROOT).as_posix(), (dest/child.name).relative_to(ROOT).as_posix())
        source.rmdir()
    moves.append({'from':old,'to':new})
    if runtime:
        mapping.extend([{'from':str(ROOT/old),'to':new},{'from':old,'to':new}])

# Every preserved original is verified by bytes, not merely counts.
protected=json.loads((REPORT/'protected_hashes.json').read_text(encoding='utf-8'))
literature={}
for name in ('pdfs','tmp/offline_reprocess_001_030','tmp/paid_complex_pdf'):
    base=ROOT/name
    if not base.exists():
        base=ROOT/{'pdfs':'data/literature/pdfs','tmp/offline_reprocess_001_030':'data/literature/recovered_001_030','tmp/paid_complex_pdf':'data/literature/validation_sample'}[name]
    for p in base.rglob('*.pdf'):
        literature[name+'/'+p.relative_to(base).as_posix()]=hashlib.sha256(p.read_bytes()).hexdigest()

relocate('pdfs','data/literature/pdfs',True)
relocate('tmp/offline_reprocess_001_030','data/literature/recovered_001_030',True)
relocate('tmp/paid_complex_pdf','data/literature/validation_sample',True)
for old,new in [('outputs/gold','data/gold'),('outputs/metrics','data/metrics'),('outputs/literature','data/literature/acquisition')]:
    relocate(old,new,True)
for p in list((ROOT/'outputs').iterdir()):
    if p.name=='runs':
        for run in list(p.iterdir()):relocate(run.relative_to(ROOT).as_posix(),'data/runs/'+run.name,True)
        p.rmdir()
    elif p.name=='literature':relocate('outputs/literature','data/literature/acquisition',True)
    elif p.name=='README.md':relocate('outputs/README.md','reference/history/outputs_README.md')
    else:relocate('outputs/'+p.name,'data/'+p.name,True)
(ROOT/'outputs').rmdir()
relocate('results','data/literature/legacy_metadata',True)
relocate('work','reference/experiments/work')
relocate('tmp','reference/experiments/tmp')
relocate('examples','reference/examples')
relocate('scripts','reference/scripts')
relocate('assets','docs/assets/original')
relocate('build','reference/build_before_cleanup')
relocate('.idea','reference/local_editor_settings')
relocate('paper-dependencies.txt','reference/legacy/paper-dependencies.txt')
relocate('comproscanner.log','data/maintenance/cleanup_20260906/before.log')
# Prefix mappings for old CLI arguments as well as nested source paths.
mapping.extend([{'from':str(ROOT/'outputs'),'to':'data'},{'from':'outputs','to':'data'}])
mapping.sort(key=lambda item:-len(item['from']))
(ROOT/'data/path_migrations.json').write_text(json.dumps(mapping,ensure_ascii=False,indent=2),encoding='utf-8')
(REPORT/'directory_moves.json').write_text(json.dumps(moves,ensure_ascii=False,indent=2),encoding='utf-8')

def destination(old):
    for item in sorted(moves,key=lambda x:-len(x['from'])):
        if old==item['from'] or old.startswith(item['from']+'/'):
            return ROOT/(item['to']+old[len(item['from']):])
    return ROOT/old

for name,digest in {**protected,**literature}.items():
    p=destination(name)
    assert p.is_file() and hashlib.sha256(p.read_bytes()).hexdigest()==digest,p
(REPORT/'data_integrity.json').write_text(json.dumps({
    'protected_result_files':len(protected),'original_pdf_files':len(literature),
    'all_hashes_unchanged':True,'moves':len(moves)},indent=2),encoding='utf-8')
print('Verified unchanged:',len(protected),'Gold/baseline files and',len(literature),'PDFs')

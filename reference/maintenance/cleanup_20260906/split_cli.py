"""Split the existing command implementations along their stage boundaries."""
from pathlib import Path
import ast

ROOT=Path(__file__).resolve().parents[3]
path=ROOT/'src/comproscanner/cli/main.py'
text=path.read_text(encoding='utf-8')
tree=ast.parse(text)
groups={
    'common': '_default_run_id _safe_file_stem _require_network_execution _load_evidence _fact_from_dict',
    'documents': '_discover _acquire_oa _process_articles',
    'evidence': '_prepare_evidence',
    'extraction': '_scientific_instructions _extraction_config _extract_evidence',
    'results': '_material_article_config _material_processor _postprocess_materials _review _evaluate _export_results',
    'run': '_processor_csv_paths _run_stage _run_pipeline _RUN_STAGES',
    'main': '_add_model_arguments _apply_preset_defaults build_parser main',
}
owner={name:group for group,names in groups.items() for name in names.split()}
imports=[n for n in tree.body if isinstance(n,(ast.Import,ast.ImportFrom)) and getattr(n,'module','')!='__future__']
for group in groups:
    nodes=[]
    for n in tree.body:
        name=getattr(n,'name',None)
        if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name):name=n.targets[0].id
        if owner.get(name)==group:nodes.append(n)
    used={n.id for node in nodes for n in ast.walk(node) if isinstance(n,ast.Name)}
    header=['"""'+group.capitalize()+' commands for the canonical workflow."""','from __future__ import annotations','']
    for n in imports:
        aliases=[a for a in n.names if (a.asname or a.name.split('.')[0]) in used]
        if aliases:
            new=ast.Import(aliases) if isinstance(n,ast.Import) else ast.ImportFrom(n.module,aliases,n.level)
            header.append(ast.unparse(new))
    for name in sorted(used & owner.keys()):
        if owner[name]!=group:header.append(f'from .{owner[name]} import {name}')
    content='\n'.join(header)+'\n\n\n'+'\n\n\n'.join(ast.get_source_segment(text,n) for n in nodes)+'\n'
    (path.parent/f'{group}.py').write_text(content,encoding='utf-8')
for p in (ROOT/'tests').rglob('*.py'):
    content=p.read_text(encoding='utf-8').replace('from comproscanner.cli.main import _scientific_instructions','from comproscanner.cli.extraction import _scientific_instructions')
    if p.name=='test_cli_run.py':
        content=content.replace('cli_main = importlib.import_module("comproscanner.cli.main")','cli_main = importlib.import_module("comproscanner.cli.run")\nfrom comproscanner.evidence.preparation import EvidencePreparationPipeline')
        content=content.replace('cli_main.EvidencePreparationPipeline','EvidencePreparationPipeline')
    if p.name=='test_cli_process_articles.py':
        content=content.replace('cli_module = importlib.import_module("comproscanner.cli.main")','cli_module = importlib.import_module("comproscanner.cli.documents")')
    p.write_text(content,encoding='utf-8')
print('CLI split into seven focused modules, implementation bodies preserved')

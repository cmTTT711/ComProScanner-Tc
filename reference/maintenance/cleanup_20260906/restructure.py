"""One-time, checked migration. The pre-migration archive is the rollback source."""
from pathlib import Path
import ast
import importlib.util
import json
import re
import shutil

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / 'src/comproscanner'
ARCHIVE = ROOT / 'reference/legacy'
MAP = {
    'agents': 'extraction',
    'article_processors': 'documents/publishers',
    'chunking': 'evidence/chunking',
    'facts': 'results/facts',
    'evaluation': 'results/evaluation',
    'ingestion': 'documents/ingestion',
    'literature': 'documents/literature',
    'schemas': 'documents/schemas',
    'pipeline/evidence_preparation.py': 'evidence/preparation.py',
    'utils/common_functions.py': 'documents/metadata.py',
    'utils/pdf_to_markdown_text.py': 'documents/docling.py',
    'utils/figure_extractor.py': 'documents/figures.py',
    'utils/prepare_iop_files.py': 'documents/prepare_iop.py',
    'utils/embeddings.py': 'evidence/rag/embeddings.py',
    'utils/configs/rag_config.py': 'evidence/rag/config.py',
    'utils/configs/article_keywords.py': 'documents/config/article_keywords.py',
    'utils/configs/base_urls.py': 'documents/config/base_urls.py',
    'utils/configs/paths_config.py': 'documents/config/paths.py',
    'utils/error_handler.py': '_errors.py',
    'utils/logger.py': '_logging.py',
}
KEEP = {'cli', 'presets', 'evidence', 'results'}

def checked(path):
    path = path.resolve()
    assert path.is_relative_to(ROOT) and path != ROOT, path
    return path

def move(src, dst):
    src, dst = checked(src), checked(dst)
    assert not dst.exists(), dst
    dst.parent.mkdir(parents=True, exist_ok=True)
    src.rename(dst)

def put(path, text):
    path = checked(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8')

def module(rel):
    return 'comproscanner.' + rel.removesuffix('.py').removesuffix('/__init__').replace('/', '.')

mapping = {}
original = {}
for p in SRC.rglob('*.py'):
    rel = p.relative_to(SRC).as_posix()
    original[rel] = p.read_text(encoding='utf-8-sig')
    for old, new in MAP.items():
        if rel == old or rel.startswith(old + '/'):
            mapping[rel] = new + rel[len(old):]
            break
    else:
        if rel.split('/')[0] in KEEP and rel != 'evaluation/legacy.py':
            mapping[rel] = rel

# Legacy evaluation adapter is required to read the original Gold, not a second evaluator.
mapping['evaluation/legacy.py'] = 'results/evaluation/legacy.py'
MODULE_MAP = {module(k): module(v) for k, v in mapping.items()}
MODULE_MAP.update({
    'comproscanner.pipeline': 'comproscanner.evidence.preparation',
    'comproscanner.utils.data_preparator': 'comproscanner.documents.csv_store',
    'comproscanner.comproscanner': 'comproscanner.documents.dispatch',
    'comproscanner.utils.database_manager': 'comproscanner.documents.csv_store',
    'comproscanner.utils.configs': 'comproscanner.documents.config',
})
SPECIAL = {
    'RAGConfig': 'comproscanner.evidence.rag.config',
    'VectorDatabaseManager': 'comproscanner.evidence.rag.store',
    'CSVDatabaseManager': 'comproscanner.documents.csv_store',
    'DatabaseConfig': 'comproscanner.documents.config',
}

def rewrite(text, old_module, is_init=False):
    tree = ast.parse(text)
    lines = text.splitlines(keepends=True)
    edits = []
    package = old_module if is_init else old_module.rsplit('.', 1)[0]
    for n in ast.walk(tree):
        if not isinstance(n, ast.ImportFrom):
            continue
        origin = importlib.util.resolve_name('.' * n.level + (n.module or ''), package) if n.level else n.module
        if not origin or not origin.startswith('comproscanner'):
            continue
        result = []
        for a in n.names:
            target = SPECIAL.get(a.name) if origin in ('comproscanner.utils.configs', 'comproscanner.utils.database_manager') else None
            target = target or MODULE_MAP.get(origin, origin)
            result.append('from ' + target + ' import ' + a.name + (' as ' + a.asname if a.asname else ''))
        indent = ' ' * n.col_offset
        edits.append((n.lineno-1, n.end_lineno, ('\n'+indent).join(result)+'\n'))
    for start, end, replacement in sorted(edits, reverse=True):
        lines[start:end] = [' ' * (len(lines[start])-len(lines[start].lstrip())) + replacement]
    text = ''.join(lines)
    # Also update string import/patch targets used by tests and lazy loading.
    for old, new in sorted(MODULE_MAP.items(), key=lambda x: -len(x[0])):
        text = text.replace(old, new)
    return text

database = original['utils/database_manager.py']
db_tree = ast.parse(database)
classes = {n.name: ast.get_source_segment(database,n) for n in db_tree.body if isinstance(n,ast.ClassDef)}
csv_header = '''"""Canonical Article CSV persistence; no SQL or model dependencies."""
import io
import os
import json
from pathlib import Path
import pandas as pd
from comproscanner.documents.schemas import normalize_legacy_article_frame, validate_article_frame
from comproscanner._logging import setup_logger
logger = setup_logger("comproscanner.log", module_name="article_csv")

def read_csv_sanitizing_nul(file_path):
    with open(file_path, "r", encoding="utf-8-sig", newline="") as file:
        csv_text = file.read().replace("\\x00", "")
    return pd.read_csv(io.StringIO(csv_text), dtype=str)

'''
rag_header = '''"""Optional vector retrieval over canonical chunks; never imported by document parsing."""
import gc
from pathlib import Path
from langchain_core.documents import Document
from langchain_chroma import Chroma
from chromadb import PersistentClient
from comproscanner._logging import setup_logger
from .embeddings import MultiModelEmbeddings
logger = setup_logger("comproscanner.log", module_name="rag")

'''
vector_tree = ast.parse(classes['VectorDatabaseManager'])
vector_tree.body[0].body = [n for n in vector_tree.body[0].body if getattr(n,'name','') != 'create_database']

# Move non-production source out of the installed package, including original SQL/vector mixture.
for rel, content in original.items():
    source = SRC / rel
    if rel not in mapping:
        move(source, ARCHIVE/'comproscanner'/rel)
    elif mapping[rel] != rel:
        move(source, SRC/mapping[rel])
for rel, dest in mapping.items():
    put(SRC/dest, rewrite(original[rel], module(rel), rel.endswith('__init__.py')))
put(SRC/'documents/csv_store.py', csv_header + classes['CSVDatabaseManager'] + '\n')
put(SRC/'evidence/rag/store.py', rag_header + ast.unparse(vector_tree) + '\n')

# Keep the existing source routing method, not the historical extraction facade.
scanner_tree = ast.parse(original['comproscanner.py'])
scanner_class = next(n for n in scanner_tree.body if isinstance(n,ast.ClassDef))
method = next(n for n in scanner_class.body if getattr(n,'name','')=='process_articles')
dispatch = '''"""Route acquisition to the existing source processors, producing only Articles."""
import os
from typing import Optional, Dict
from comproscanner._errors import ValueErrorHandler
from comproscanner._logging import setup_logger
from comproscanner.evidence.rag.config import RAGConfig
logger = setup_logger("comproscanner.log", module_name="document_dispatch")
class ArticleProcessor:
    def __init__(self, main_property_keyword):
        self.main_property_keyword = main_property_keyword
'''
dispatch += '\n'.join('    '+line for line in ast.get_source_segment(original['comproscanner.py'],method).splitlines()) + '\n'
# get_source_segment keeps indentation on all but the first line.
dispatch = dispatch[:dispatch.index('    def process_articles')] + '    ' + ast.get_source_segment(original['comproscanner.py'],method) + '\n'
put(SRC/'documents/dispatch.py', rewrite(dispatch, 'comproscanner.comproscanner'))
p=SRC/'documents/ingestion/process.py'; t=p.read_text(encoding='utf-8'); t=t.replace('import ComProScanner','import ArticleProcessor').replace('scanner_factory = ComProScanner','scanner_factory = ArticleProcessor'); put(p,t)
put(SRC/'__init__.py', '''"""ComProScanner: document → Evidence → extraction → reviewed results.

Use the `comproscanner` CLI or import the four modules directly.
Historical CrewAI/database facades are preserved only in reference/legacy.
"""
__version__ = "2026.09.06"
''')
put(SRC/'__main__.py', 'from .cli import main\nraise SystemExit(main())\n')
put(SRC/'documents/config/__init__.py', '''"""Source-format settings and intermediate Article locations."""
from .article_keywords import ArticleRelatedKeywords
from .base_urls import BaseUrls
from .paths import DefaultPaths

class DatabaseConfig:
    """Intermediate CSV naming retained for source processor interoperability."""
    def __init__(self, main_property_keyword, is_sql_db=False):
        if is_sql_db:
            raise ValueError("SQL export is archived under reference; use canonical Article output")
        self.PAPERDATA_TABLE_NAME = f"{main_property_keyword}_data"
        self.EXTRACTED_CSV_FOLDERPATH = f"results/extracted_data/{main_property_keyword}"
''')

# Delete inactive SQL and pre-Article vector side effects from the active parser implementations.
class StripSideEffects(ast.NodeTransformer):
    def visit_ImportFrom(self,n):
        if n.module and n.module.startswith(('sqlalchemy','mysql')): return None
        n.names = [a for a in n.names if a.name not in ('MySQLDatabaseManager','VectorDatabaseManager')]
        return n if n.names else None
    def visit_If(self,n):
        test=ast.unparse(n.test)
        if 'is_sql_db' in test or 'sql_dataframes' in test or 'sql_batch_size' in test:
            return [self.visit(x) for x in n.orelse]
        return self.generic_visit(n)
    def visit_Assign(self,n):
        targets=' '.join(ast.unparse(x) for x in n.targets)
        if any(x in targets for x in ('sql_dataframes','sql_db_manager','vector_db_manager','final_sql_df','remaining_sql_df')):return None
        return self.generic_visit(n)
    def visit_Expr(self,n):
        s=ast.unparse(n)
        if isinstance(n.value,ast.Call) and ('sql_dataframes.' in s or 'vector_db_manager.' in s): return None
        return self.generic_visit(n)

for p in list((SRC/'documents/publishers').glob('*_processor.py'))+[SRC/'documents/docling.py']:
    text=p.read_text(encoding='utf-8'); tree=StripSideEffects().visit(ast.parse(text))
    # Remove whole vector-only if blocks after removing their calls.
    class PruneVector(ast.NodeTransformer):
        def visit_If(self,n):
            if 'vector_db_manager' in ast.unparse(n.test): return None
            self.generic_visit(n)
            if not n.body: n.body=[ast.Pass()]
            return n
        def visit_Call(self,n):
            self.generic_visit(n)
            n.keywords=[k for k in n.keywords if k.arg!='vector_db_manager']
            return n
        def visit_FunctionDef(self,n):
            self.generic_visit(n)
            # Vector manager was only used for the deleted side effect.
            n.args.args=[a for a in n.args.args if a.arg!='vector_db_manager']
            return n
    tree=PruneVector().visit(tree)
    # Remaining blocks with diagnostics and no active side effect need valid bodies.
    for n in ast.walk(tree):
        if isinstance(n,(ast.If,ast.For,ast.While,ast.Try,ast.ExceptHandler)) and not n.body:n.body=[ast.Pass()]
    put(p,ast.unparse(ast.fix_missing_locations(tree))+'\n')

# Retained tests are for the four active modules. Legacy-only suites accompany their code.
archive_tests={'test_extract_flow.py','test_public_api.py','test_post_processing','test_agent_tools',
               'test_apis_primary','test_metadata','test_utils'}
for p in list((ROOT/'tests').iterdir()):
    if p.name in archive_tests: move(p,ARCHIVE/'tests'/p.name)
for p in (ROOT/'tests').rglob('*.py'):
    t=p.read_text(encoding='utf-8-sig')
    for old,new in sorted(MODULE_MAP.items(),key=lambda x:-len(x[0])):t=t.replace(old,new)
    put(p,t)

# Move non-code resources belonging exclusively to the old CrewAI flow.
for p in list(SRC.rglob('*')):
    if p.is_file() and p.suffix in ('.yaml','.yml') and ('extract_flow' in p.parts or 'post_processing' in p.parts):
        move(p,ARCHIVE/'comproscanner'/p.relative_to(SRC))
# Remove generated bytecode only, then empty directories; all targets checked under SRC.
for p in sorted(SRC.rglob('__pycache__'),key=lambda p:len(p.parts),reverse=True):shutil.rmtree(checked(p))
for p in sorted(SRC.rglob('*'),key=lambda p:len(p.parts),reverse=True):
    if p.is_dir() and not any(p.iterdir()):p.rmdir()
for name in ('documents','documents/config','evidence/rag','results/evaluation'):
    p=SRC/name/'__init__.py'
    if not p.exists():put(p,'"""'+name.replace('/',' ')+' module."""\n')
put(ROOT/'data/maintenance/cleanup_20260906/module_map.json',json.dumps(MODULE_MAP,indent=2))
print('Migrated',len(mapping),'active source files; archived',len(original)-len(mapping),'legacy source files')

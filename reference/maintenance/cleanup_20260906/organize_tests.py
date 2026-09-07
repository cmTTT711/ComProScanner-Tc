"""Keep tests aligned with the four production modules."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
tests=ROOT/'tests'
mapping={
    'test_article_processors':'documents/publishers',
    'test_ingestion':'documents/ingestion','test_literature':'documents/literature',
    'test_schemas':'documents/schemas','test_chunking':'evidence/chunking',
    'test_evidence':'evidence/providers','test_pipeline':'evidence/preparation',
    'test_agents':'extraction','test_facts':'results/facts',
    'test_results':'results/export','test_evaluation':'results/evaluation',
    'test_cli.py':'cli/test_commands.py','test_cli_run.py':'cli/test_run.py',
    'test_cli_extract_guard.py':'cli/test_extract_guard.py',
    'test_cli_process_articles.py':'cli/test_process_articles.py',
    'test_presets.py':'presets/test_registry.py',
    'test_tc_evidence_baseline.py':'presets/test_tc_baseline.py',
    'test_figure_source_identity.py':'evidence/test_figure_identity.py',
    'test_preset_pipeline.py':'test_preset_pipeline.py',
}
# Relative fixture paths survive additional publisher directory nesting.
for p in (tests/'test_article_processors').glob('*.py'):
    text=p.read_text(encoding='utf-8').replace("'../fixtures'", "'../../fixtures'")
    p.write_text(text,encoding='utf-8')
# Root-aware invariants must not depend on the depth of their test file.
for p in tests.rglob('*.py'):
    t=p.read_text(encoding='utf-8')
    if p.name=='test_presets.py':
        t=t.replace('Path(__file__).resolve().parents[1]', 'Path(__file__).resolve().parents[2]')
    p.write_text(t,encoding='utf-8')
for old,new in mapping.items():
    if old==new:continue
    source=tests/old;target=tests/new
    if not source.exists():continue
    assert source.resolve().is_relative_to(tests.resolve())
    assert target.resolve().is_relative_to(tests.resolve()) and not target.exists()
    target.parent.mkdir(parents=True,exist_ok=True)
    source.rename(target)

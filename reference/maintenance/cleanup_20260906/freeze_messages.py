"""Capture expected wire messages from the pre-cleanup source, without model calls."""
import json
from pathlib import Path
import types
import zipfile
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'src'))
from comproscanner.evidence import Evidence, EvidenceType, RetrievalMethod
from comproscanner.presets import get_preset
from comproscanner.cli.extraction import _scientific_instructions

with zipfile.ZipFile(ROOT/'data/maintenance/cleanup_20260906/before_cleanup.zip') as archive:
    source = archive.read('src/comproscanner/agents/litellm_adapters.py').decode('utf-8')
module = types.ModuleType('comproscanner.extraction._frozen_adapter')
module.__package__ = 'comproscanner.extraction'
sys.modules[module.__name__] = module
exec(compile(source, '<pre-cleanup adapter>', 'exec'), module.__dict__)
messages=[]
def complete(self, prompt):
    messages.append(prompt)
    return '{"answer":"yes","facts":[]}'
module._LiteLLMClient.complete=complete
policy=get_preset('curie_temperature')
for kind in ('text', 'table', 'equation'):
    evidence=Evidence(evidence_id='e1',document_id='p1',target_property='Curie temperature',
                      source_type=EvidenceType(kind),source_id='s1',content='BiFeO3 has Tc ~1103 K.',retrieval_methods=(RetrievalMethod("fixture"),))
    module.LiteLLMEvidenceIdentifier(module.ModelSettings('fixture'),policy.identifier_query).identify(evidence)
    module.LiteLLMEvidenceExtractor(module.ModelSettings('fixture'),_scientific_instructions(policy)).extract(evidence)
evidence=Evidence(evidence_id='e1',document_id='p1',target_property='Curie temperature',
                  source_type=EvidenceType.FIGURE,source_id='s1',content='BiFeO3 has Tc ~1103 K.',retrieval_methods=(RetrievalMethod("fixture"),))
module.LiteLLMEvidenceExtractor(module.ModelSettings('fixture'),_scientific_instructions(policy)).extract(evidence,visual_observation='Original figure labels: BiFeO3, ~1103 K.')
path=ROOT/'tests/fixtures/tc_wire_messages.json'
path.write_text(json.dumps(messages,ensure_ascii=False,indent=2),encoding='utf-8')
print('Captured',len(messages),'pre-cleanup message sequences; external calls: 0')

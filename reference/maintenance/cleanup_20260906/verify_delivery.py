"""Final local delivery checks; never invokes a model or external service."""
from pathlib import Path
import hashlib
import json
import os
import re
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "data/maintenance/cleanup_20260906"
sys.path.insert(0, str(ROOT / "src"))
from comproscanner._paths import resolve_recorded_path

protected = json.loads((BASE / "protected_hashes.json").read_text(encoding="utf-8"))
for old, digest in protected.items():
    assert hashlib.sha256(resolve_recorded_path(ROOT / old).read_bytes()).hexdigest() == digest, old

wheel = next((BASE / "dist").glob("*.whl"))
with zipfile.ZipFile(wheel) as archive:
    assert not any("reference/" in name or "comproscanner/utils/" in name or "comproscanner/agents/" in name for name in archive.namelist())
    for path in (ROOT / "src/comproscanner").rglob("*.py"):
        assert archive.read(path.relative_to(ROOT / "src").as_posix()) == path.read_bytes(), path

code = '''
import sys
import comproscanner
from comproscanner.cli.main import main
from comproscanner.evidence.rag.config import RAGConfig
assert "installed_package" in comproscanner.__file__
assert main(["presets"]) == 0
assert main(["sources"]) == 0
assert "rag_chat_model" not in RAGConfig.__dataclass_fields__
assert not any(name in sys.modules for name in ("crewai", "mysql", "neo4j", "torch", "litellm"))
print("Independent installed wheel CLI and lazy imports: PASS")
'''
env = os.environ.copy()
env["PYTHONPATH"] = str(BASE / "installed_package")
result = subprocess.run([sys.executable, "-X", "utf8", "-c", code], cwd=BASE, env=env, capture_output=True, text=True, encoding="utf-8")
(BASE / "wheel_smoke.txt").write_text(result.stdout + result.stderr, encoding="utf-8")
assert result.returncode == 0, result.stderr

for path in [ROOT / "README.md", *(ROOT / "docs").glob("*.md")]:
    for target in re.findall(r"\]\(([^)]+)\)", path.read_text(encoding="utf-8")):
        if "://" not in target and not target.startswith("#"):
            assert (path.parent / target.split("#", 1)[0]).exists(), (path, target)

rag = json.loads((ROOT / "data/runs/cleanup_rag_final_20260906/evidence/all.json").read_text(encoding="utf-8"))
assert len(rag) == 6
assert not json.loads((ROOT / "data/runs/cleanup_rag_final_20260906/failures.json").read_text(encoding="utf-8"))
print(json.dumps({"protected_files": len(protected), "wheel_matches_final_source": True, "installed_cli": "PASS", "documentation_links": "PASS", "rag_evidence": len(rag)}, indent=2))

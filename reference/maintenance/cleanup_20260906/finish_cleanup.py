"""Remove verified temporary copies and keep migration scripts outside active code."""
from pathlib import Path
import json
import shutil

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "data/maintenance/cleanup_20260906"
assert (BASE / "delivery_checks.txt").is_file()
assert '"wheel_matches_final_source": true' in (BASE / "delivery_checks.txt").read_text(encoding="utf-8")

generated_results = ROOT / "results"
if generated_results.exists():
    destination = BASE / "generated_test_outputs"
    assert generated_results.resolve() == ROOT / "results"
    assert generated_results.resolve().is_relative_to(ROOT)
    assert not destination.exists()
    shutil.move(str(generated_results), str(destination))

removed = []
for directory in [BASE / "baseline_package", BASE / "installed_package", BASE / "format_tools", ROOT / "build", ROOT / ".pytest_cache"]:
    assert directory.resolve().is_relative_to(ROOT)
    assert not directory.is_symlink() and not directory.is_junction()
    if directory.exists():
        shutil.rmtree(directory)
        removed.append(str(directory.relative_to(ROOT)))

destination = ROOT / "reference/maintenance/cleanup_20260906"
destination.mkdir(parents=True, exist_ok=True)
scripts = list(BASE.glob("*.py"))
for script in scripts:
    assert script.resolve().is_relative_to(BASE)
    assert not (destination / script.name).exists()
    if script.name == "freeze_messages.py":
        script.write_text(script.read_text(encoding="utf-8").replace("from comproscanner.cli.main import _scientific_instructions", "from comproscanner.cli.extraction import _scientific_instructions"), encoding="utf-8")
    shutil.move(str(script), str(destination / script.name))

report = {"temporary_directories_removed": removed, "scripts_moved_to_reference": len(scripts), "root_directories": sorted(path.name for path in ROOT.iterdir() if path.is_dir())}
(BASE / "final_layout.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(report, ensure_ascii=False))

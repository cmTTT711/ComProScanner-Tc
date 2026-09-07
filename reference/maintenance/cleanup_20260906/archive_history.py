"""Archive retired local experiments, verify bytes, then remove duplicate trees."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import zipfile

ROOT = Path(__file__).resolve().parents[3]
REFERENCE = ROOT / "reference"
names = ("build_before_cleanup", "examples", "experiments", "history", "local_editor_settings", "scripts")
sources = [REFERENCE / name for name in names]
archive_path = REFERENCE / "history.zip"
assert not archive_path.exists(), "Archive already exists; do not overwrite"
files = []
links = []
for source in sources:
    assert source.resolve().is_relative_to(REFERENCE.resolve())
    for directory, dirs, filenames in os.walk(source, followlinks=False):
        for name in list(dirs) + filenames:
            path = Path(directory) / name
            if path.is_symlink() or path.is_junction():
                links.append({"path": str(path.relative_to(REFERENCE)), "target": str(path.resolve()), "junction": path.is_junction()})
                if name in dirs:
                    dirs.remove(name)
                continue
            assert path.resolve().is_relative_to(REFERENCE.resolve()), path
            if path.is_file():
                files.append(path)
with zipfile.ZipFile(archive_path, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=3) as archive:
    for path in files:
        archive.write(path, path.relative_to(REFERENCE).as_posix())
    archive.writestr("_external_links.json", json.dumps(links, indent=2))
with zipfile.ZipFile(archive_path) as archive:
    for path in files:
        with path.open("rb") as source, archive.open(path.relative_to(REFERENCE).as_posix()) as stored:
            assert hashlib.file_digest(source, "sha256").digest() == hashlib.file_digest(stored, "sha256").digest(), path
report = {"files": len(files), "archive": str(archive_path.relative_to(ROOT)), "verified_all_file_bytes": True}
(ROOT / "data/maintenance/cleanup_20260906/history_archive.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
for link in links:
    path = REFERENCE / link["path"]
    assert path.parent.resolve().is_relative_to(REFERENCE.resolve())
    # Remove the link itself, never recurse into the external dependency runtime.
    if link["junction"]:
        assert path.is_junction()
        os.rmdir(path)
    else:
        assert path.is_symlink()
        path.unlink()
for source in sources:
    assert source.resolve().is_relative_to(REFERENCE.resolve()) and source.name in names
    if source.exists():
        shutil.rmtree(source)
print(json.dumps(report))

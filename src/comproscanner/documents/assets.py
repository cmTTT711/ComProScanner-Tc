"""Lossless parser sidecars, independent of property selection."""

from pathlib import Path
import hashlib
import json
import shutil


def xml_article_text(root):
    """Retain all source text before legacy section/MathML transformations."""
    nodes = root.xpath(
        './/*[local-name()="article-title" or local-name()="title-group" or local-name()="abstract" or local-name()="description" or local-name()="body" or local-name()="sections" or local-name()="ref-list"]'
    )
    selected = set(nodes)
    # Skip children of an already selected container to avoid duplicated text.
    return (
        "\n\n".join(
            "".join(node.itertext()).strip()
            for node in nodes
            if not any(parent in selected for parent in node.iterancestors())
        )
        or "".join(root.itertext()).strip()
    )


def document_title(document):
    """Use the parser's first-page title/header, never an external lookup."""
    candidates = []
    for item in document.texts:
        label = str(item.label).lower()
        if label not in {
            "title",
            "section_header",
            "docitemlabel.title",
            "docitemlabel.section_header",
        }:
            continue
        if not item.prov or item.prov[0].page_no != 1:
            continue
        title = item.text.strip()
        if title.casefold() in {"abstract", "introduction", "contents", "references"}:
            continue
        candidates.append(title)
    return candidates[0] if candidates else ""


def save_document_assets(document, markdown, source, root="documents"):
    """Keep original input, Markdown, Docling structure, page renders and item images.

    Failures are recorded explicitly so an incomplete image export is reviewable.
    Evidence selection happens later and never controls this archive.
    """
    source = Path(source)
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    folder = Path(root).resolve() / digest[:16]
    folder.mkdir(parents=True, exist_ok=True)
    original = folder / "original.pdf"
    if source.resolve() != original.resolve():
        shutil.copy2(source, original)
    (folder / "article.md").write_text(markdown, encoding="utf-8")
    document.save_as_json(folder / "document.json")
    errors, pages, images = [], [], []
    for number, page in document.pages.items():
        try:
            target = folder / "pages" / f"{number}.png"
            target.parent.mkdir(exist_ok=True)
            page.image.pil_image.save(target)
            pages.append(str(target.relative_to(folder)))
        except Exception as exc:
            errors.append(f"page {number}: {type(exc).__name__}: {exc}")
    # All pictures and tables are retained, including those unrelated to this preset.
    for kind in ("pictures", "tables"):
        for number, item in enumerate(getattr(document, kind), 1):
            try:
                target = folder / kind / f"{number}.png"
                target.parent.mkdir(exist_ok=True)
                pixels = item.get_image(document)
                if pixels is None:
                    raise ValueError("Docling returned no image")
                pixels.save(target)
                images.append(
                    {
                        "kind": kind,
                        "path": str(target.relative_to(folder)),
                        "source_ref": item.self_ref,
                    }
                )
            except Exception as exc:
                errors.append(f"{kind} {number}: {type(exc).__name__}: {exc}")
    manifest = {
        "source_path": str(source.resolve()),
        "sha256": digest,
        "markdown": "article.md",
        "docling": "document.json",
        "original": "original.pdf",
        "pages": pages,
        "images": images,
        "errors": errors,
    }
    (folder / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return str(folder / "manifest.json")

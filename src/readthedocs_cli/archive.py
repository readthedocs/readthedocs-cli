"""Build the artifacts zip in the layout the upload API expects."""

import logging
import os
import zipfile
from collections.abc import Iterator
from pathlib import Path

from readthedocs_cli.exceptions import ReadTheDocsError


log = logging.getLogger(__name__)

# Same limit as the presigned URL returned by the API.
MAX_UPLOAD_SIZE = 1024**3
EXCLUDED_DIRS = {".git"}


def validate_artifacts(html_dir: Path, files: dict[str, Path]) -> None:
    if not html_dir.is_dir():
        raise ReadTheDocsError(f"HTML directory does not exist: {html_dir}")
    if not (html_dir / "index.html").is_file():
        raise ReadTheDocsError(
            f"HTML directory does not contain an index.html at its root: {html_dir}"
        )
    for type_, path in files.items():
        if not path.is_file():
            raise ReadTheDocsError(f"{type_} file does not exist: {path}")


def create_archive(html_dir: Path, files: dict[str, Path], destination: Path) -> Path:
    """
    Write ``html_dir`` and the extra ``files`` (keyed by type: pdf, epub, htmlzip) to a zip.

    Layout: ``html/**``, ``pdf/<name>``, ``epub/<name>``, ``htmlzip/<name>``.
    """
    validate_artifacts(html_dir, files)

    with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in _walk(html_dir):
            archive.write(path, Path("html") / path.relative_to(html_dir))
        for type_, path in files.items():
            archive.write(path, Path(type_) / path.name)

    size = destination.stat().st_size
    log.info("Archive created: %s (%.1f MB)", destination, size / 1024**2)
    if size > MAX_UPLOAD_SIZE:
        raise ReadTheDocsError(
            f"Archive is {size / 1024**2:.1f} MB, above the {MAX_UPLOAD_SIZE // 1024**2} MB limit."
        )
    return destination


def _walk(root: Path) -> Iterator[Path]:
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [name for name in dirnames if name not in EXCLUDED_DIRS]
        for filename in filenames:
            yield Path(dirpath) / filename

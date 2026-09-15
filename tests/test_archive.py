import zipfile

import pytest

from readthedocs_cli import archive
from readthedocs_cli.archive import create_archive
from readthedocs_cli.exceptions import ReadTheDocsError


def names(path):
    with zipfile.ZipFile(path) as zf:
        return sorted(zf.namelist())


def test_html_dir_is_archived_under_html(html_dir, tmp_path):
    (html_dir / "_static").mkdir()
    (html_dir / "_static" / "style.css").write_text("body {}")
    (html_dir / "page.html").write_text("<p>")

    result = create_archive(html_dir, {}, tmp_path / "out.zip")

    assert names(result) == ["html/_static/style.css", "html/index.html", "html/page.html"]


def test_git_directory_is_excluded(html_dir, tmp_path):
    (html_dir / ".git").mkdir()
    (html_dir / ".git" / "HEAD").write_text("ref")

    result = create_archive(html_dir, {}, tmp_path / "out.zip")

    assert names(result) == ["html/index.html"]


def test_extra_files_are_archived_under_their_type(html_dir, tmp_path):
    pdf = tmp_path / "docs.pdf"
    pdf.write_bytes(b"%PDF")
    epub = tmp_path / "docs.epub"
    epub.write_bytes(b"epub")

    result = create_archive(html_dir, {"pdf": pdf, "epub": epub}, tmp_path / "out.zip")

    assert names(result) == ["epub/docs.epub", "html/index.html", "pdf/docs.pdf"]


def test_missing_html_dir(tmp_path):
    with pytest.raises(ReadTheDocsError, match="does not exist"):
        create_archive(tmp_path / "missing", {}, tmp_path / "out.zip")


def test_missing_index_html(tmp_path):
    html = tmp_path / "html"
    html.mkdir()

    with pytest.raises(ReadTheDocsError, match="index.html"):
        create_archive(html, {}, tmp_path / "out.zip")


def test_missing_pdf_file(html_dir, tmp_path):
    with pytest.raises(ReadTheDocsError, match="pdf file does not exist"):
        create_archive(html_dir, {"pdf": tmp_path / "missing.pdf"}, tmp_path / "out.zip")


def test_archive_above_size_limit(html_dir, tmp_path, monkeypatch):
    monkeypatch.setattr(archive, "MAX_UPLOAD_SIZE", 10)

    with pytest.raises(ReadTheDocsError, match="above the"):
        create_archive(html_dir, {}, tmp_path / "out.zip")

import pytest


ENV_VARS = (
    "READTHEDOCS_TOKEN",
    "READTHEDOCS_API_URL",
    "GITHUB_ACTIONS",
    "GITHUB_EVENT_NAME",
    "GITHUB_EVENT_PATH",
    "GITHUB_REF_TYPE",
    "GITHUB_REF_NAME",
    "GITHUB_SHA",
)


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for name in ENV_VARS:
        monkeypatch.delenv(name, raising=False)


@pytest.fixture
def html_dir(tmp_path):
    path = tmp_path / "html"
    path.mkdir()
    (path / "index.html").write_text("<html></html>")
    return path

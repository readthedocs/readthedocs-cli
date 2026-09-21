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
    "CIRCLECI",
    "CIRCLE_BRANCH",
    "CIRCLE_TAG",
    "CIRCLE_SHA1",
    "CIRCLE_PULL_REQUEST",
    "CIRCLE_PR_NUMBER",
    "GITLAB_CI",
    "CI_COMMIT_SHA",
    "CI_COMMIT_BRANCH",
    "CI_COMMIT_TAG",
    "CI_MERGE_REQUEST_IID",
    "CI_MERGE_REQUEST_SOURCE_BRANCH_SHA",
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

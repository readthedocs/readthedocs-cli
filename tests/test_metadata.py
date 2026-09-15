import json
import subprocess

import pytest

from readthedocs_cli.exceptions import ReadTheDocsError
from readthedocs_cli.metadata import Version
from readthedocs_cli.metadata import resolve_version


def github(monkeypatch, **env):
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    for name, value in env.items():
        monkeypatch.setenv(name, value)


@pytest.fixture
def git_repo(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    def git(*args):
        subprocess.run(
            ["git", "-c", "user.name=test", "-c", "user.email=test@example.com", *args],
            check=True,
            capture_output=True,
        )

    git("init", "-q", "-b", "main")
    git("-c", "commit.gpgsign=false", "commit", "-q", "--allow-empty", "-m", "init")
    return git


def test_github_branch_push(monkeypatch):
    github(
        monkeypatch,
        GITHUB_EVENT_NAME="push",
        GITHUB_REF_TYPE="branch",
        GITHUB_REF_NAME="main",
        GITHUB_SHA="abc123",
    )

    assert resolve_version() == Version("main", "branch", "abc123")


def test_github_tag_push(monkeypatch):
    github(
        monkeypatch,
        GITHUB_EVENT_NAME="push",
        GITHUB_REF_TYPE="tag",
        GITHUB_REF_NAME="v1.2.0",
        GITHUB_SHA="abc123",
    )

    assert resolve_version() == Version("v1.2.0", "tag", "abc123")


@pytest.mark.parametrize("event", ["pull_request", "pull_request_target"])
def test_github_pull_request_uses_head_sha(monkeypatch, tmp_path, event):
    event_path = tmp_path / "event.json"
    event_path.write_text(json.dumps({"pull_request": {"number": 481, "head": {"sha": "headsha"}}}))
    github(
        monkeypatch,
        GITHUB_EVENT_NAME=event,
        GITHUB_EVENT_PATH=str(event_path),
        GITHUB_REF_TYPE="branch",
        GITHUB_REF_NAME="481/merge",
        GITHUB_SHA="mergesha",
    )

    assert resolve_version() == Version("481", "external", "headsha")


def test_explicit_values_win_per_field(monkeypatch):
    github(
        monkeypatch,
        GITHUB_EVENT_NAME="push",
        GITHUB_REF_TYPE="branch",
        GITHUB_REF_NAME="main",
        GITHUB_SHA="abc123",
    )

    assert resolve_version(name="docs", commit="def456") == Version("docs", "branch", "def456")


def test_all_explicit_values_skip_inference(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    assert resolve_version("main", "branch", "abc123") == Version("main", "branch", "abc123")


def test_git_branch(git_repo):
    version = resolve_version()

    assert version.name == "main"
    assert version.type == "branch"
    assert len(version.commit) == 40


def test_git_tag(git_repo):
    git_repo("tag", "v1.0")
    git_repo("checkout", "-q", "v1.0")

    version = resolve_version()

    assert version.name == "v1.0"
    assert version.type == "tag"


def test_git_detached_head_requires_name_and_type(git_repo):
    git_repo("checkout", "-q", "--detach")

    with pytest.raises(ReadTheDocsError, match=r"Pass --version-name, --version-type explicitly"):
        resolve_version()


def test_git_detached_head_still_infers_commit(git_repo):
    git_repo("checkout", "-q", "--detach")

    version = resolve_version(name="481", type="external")

    assert len(version.commit) == 40


def test_not_a_git_repo(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    with pytest.raises(ReadTheDocsError, match=r"--version-name, --version-type, --commit"):
        resolve_version()

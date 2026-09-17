import json

import pytest
import responses
from click.testing import CliRunner

from readthedocs_cli import __version__
from readthedocs_cli import api as api_module
from readthedocs_cli.cli import main


BASE_URL = "https://app.readthedocs.org"
INITIATE_URL = f"{BASE_URL}/api/v3/upload/initiate/"
COMPLETE_URL = f"{BASE_URL}/api/v3/upload/complete/"
STORAGE_URL = "https://bucket.s3.amazonaws.com/"
BUILD_URL = f"{BASE_URL}/projects/proj/builds/7/"
INITIATE_RESPONSE = {
    "build": {"id": 7, "urls": {"build": BUILD_URL}},
    "version": {"slug": "main"},
    "upload_url": {"url": STORAGE_URL, "fields": {"key": "k"}},
}


@pytest.fixture
def token(monkeypatch):
    monkeypatch.setenv("READTHEDOCS_TOKEN", "secret")


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    monkeypatch.setattr(api_module.time, "sleep", lambda seconds: None)


def upload_args(html_dir, *extra):
    return [
        "upload",
        "--project-slug",
        "proj",
        "--html",
        str(html_dir),
        "--version-name",
        "main",
        "--version-type",
        "branch",
        "--commit",
        "abc123",
        *extra,
    ]


def register_success(base_url=BASE_URL):
    responses.post(f"{base_url}/api/v3/upload/initiate/", json=INITIATE_RESPONSE, status=201)
    responses.post(STORAGE_URL, status=204)
    responses.post(f"{base_url}/api/v3/upload/complete/", json={"build": {"id": 7}}, status=202)


@responses.activate
def test_upload_success_prints_build_url(runner, html_dir, token):
    register_success()

    result = runner.invoke(main, upload_args(html_dir))

    assert result.exit_code == 0, result.output
    assert result.stdout == f"{BUILD_URL}\n"
    assert json.loads(responses.calls[0].request.body) == {
        "project": "proj",
        "version": {"name": "main", "type": "branch", "commit": "abc123"},
    }
    assert json.loads(responses.calls[2].request.body) == {"build": 7, "status": "success"}


@responses.activate
def test_privacy_level_is_sent_when_given(runner, html_dir, token):
    register_success()

    result = runner.invoke(main, upload_args(html_dir, "--privacy-level", "private"))

    assert result.exit_code == 0, result.output
    payload = json.loads(responses.calls[0].request.body)
    assert payload["version"]["privacy_level"] == "private"


@responses.activate
def test_missing_token_fails_before_any_request(runner, html_dir):
    result = runner.invoke(main, upload_args(html_dir))

    assert result.exit_code == 1
    assert "READTHEDOCS_TOKEN environment variable is not set" in result.output
    assert len(responses.calls) == 0


def test_missing_token_on_pull_request_mentions_forks(runner, html_dir, monkeypatch):
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setenv("GITHUB_EVENT_NAME", "pull_request")

    result = runner.invoke(main, upload_args(html_dir))

    assert result.exit_code == 1
    assert "pull requests from forks" in result.output


@responses.activate
def test_invalid_html_dir_fails_before_any_request(runner, tmp_path, token):
    result = runner.invoke(main, upload_args(tmp_path / "missing"))

    assert result.exit_code == 1
    assert "HTML directory does not exist" in result.output
    assert len(responses.calls) == 0


@responses.activate
def test_storage_failure_reports_failed_build(runner, html_dir, token):
    responses.post(INITIATE_URL, json=INITIATE_RESPONSE, status=201)
    responses.post(STORAGE_URL, status=403)
    responses.post(COMPLETE_URL, json={"build": {"id": 7}}, status=200)

    result = runner.invoke(main, upload_args(html_dir))

    assert result.exit_code == 1
    assert "Upload to storage failed: HTTP 403" in result.output
    assert json.loads(responses.calls[-1].request.body) == {"build": 7, "status": "failed"}


@responses.activate
def test_interrupt_during_upload_reports_failed_build(runner, html_dir, token, monkeypatch):
    responses.post(INITIATE_URL, json=INITIATE_RESPONSE, status=201)
    responses.post(COMPLETE_URL, json={"build": {"id": 7}}, status=200)

    def interrupt(self, upload_url, path):
        raise KeyboardInterrupt

    monkeypatch.setattr(api_module.ReadTheDocsAPI, "upload_artifacts", interrupt)

    result = runner.invoke(main, upload_args(html_dir))

    assert result.exit_code == 1
    assert json.loads(responses.calls[-1].request.body) == {"build": 7, "status": "failed"}


@responses.activate
def test_api_url_option(runner, html_dir, token):
    register_success("https://devthedocs.org")

    result = runner.invoke(main, ["--api-url", "https://devthedocs.org/", *upload_args(html_dir)])

    assert result.exit_code == 0, result.output
    assert responses.calls[0].request.url == "https://devthedocs.org/api/v3/upload/initiate/"


@responses.activate
def test_api_url_env_var(runner, html_dir, token, monkeypatch):
    monkeypatch.setenv("READTHEDOCS_API_URL", "https://devthedocs.org")
    register_success("https://devthedocs.org")

    result = runner.invoke(main, upload_args(html_dir))

    assert result.exit_code == 0, result.output
    assert responses.calls[0].request.url == "https://devthedocs.org/api/v3/upload/initiate/"


def test_version_option(runner):
    result = runner.invoke(main, ["--version"])

    assert result.exit_code == 0
    assert __version__ in result.output

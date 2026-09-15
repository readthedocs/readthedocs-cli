import json

import pytest
import requests
import responses

from readthedocs_cli import __version__
from readthedocs_cli import api as api_module
from readthedocs_cli.api import ReadTheDocsAPI
from readthedocs_cli.exceptions import APIError


BASE_URL = "https://app.readthedocs.org"
INITIATE_URL = f"{BASE_URL}/api/v3/upload/initiate/"
COMPLETE_URL = f"{BASE_URL}/api/v3/upload/complete/"
STORAGE_URL = "https://bucket.s3.amazonaws.com/"
UPLOAD_URL = {"url": STORAGE_URL, "fields": {"key": "k", "policy": "p"}}
VERSION = {"name": "main", "type": "branch", "commit": "abc123"}


@pytest.fixture
def api():
    return ReadTheDocsAPI(BASE_URL + "/", "secret")


@pytest.fixture
def archive(tmp_path):
    path = tmp_path / "artifacts.zip"
    path.write_bytes(b"zip")
    return path


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    monkeypatch.setattr(api_module.time, "sleep", lambda seconds: None)


@responses.activate
def test_initiate_sends_payload_and_headers(api):
    responses.post(INITIATE_URL, json={"build": {"id": 1}}, status=201)

    result = api.initiate_upload("proj", VERSION)

    assert result == {"build": {"id": 1}}
    request = responses.calls[0].request
    assert json.loads(request.body) == {"project": "proj", "version": VERSION}
    assert request.headers["Authorization"] == "Token secret"
    assert request.headers["User-Agent"] == f"readthedocs-cli/{__version__}"


@responses.activate
def test_complete_sends_build_and_status(api):
    responses.post(COMPLETE_URL, json={"build": {"id": 7}}, status=202)

    api.complete_upload(7, "success")

    assert json.loads(responses.calls[0].request.body) == {"build": 7, "status": "success"}


@responses.activate
@pytest.mark.parametrize("status", [401, 403, 404, 429])
def test_error_uses_detail_from_response(api, status):
    responses.post(INITIATE_URL, json={"detail": "Nope."}, status=status)

    with pytest.raises(APIError, match=f"HTTP {status}: Nope."):
        api.initiate_upload("proj", VERSION)


@responses.activate
def test_error_without_detail_uses_body(api):
    responses.post(INITIATE_URL, json={"project": ["Required."]}, status=400)

    with pytest.raises(APIError, match=r'HTTP 400: {"project": \["Required."\]}'):
        api.initiate_upload("proj", VERSION)


@responses.activate
def test_non_json_error_uses_body(api):
    responses.post(INITIATE_URL, body="<html>", status=502)

    with pytest.raises(APIError, match="HTTP 502: <html>"):
        api.initiate_upload("proj", VERSION)


@responses.activate
def test_connection_error_is_wrapped(api):
    responses.post(INITIATE_URL, body=requests.ConnectionError("boom"))

    with pytest.raises(APIError, match="boom"):
        api.initiate_upload("proj", VERSION)


@responses.activate
def test_upload_sends_fields_then_file(api, archive):
    responses.post(STORAGE_URL, status=204)

    api.upload_artifacts(UPLOAD_URL, archive)

    request = responses.calls[0].request
    body = request.body
    assert b'name="key"\r\n\r\nk\r\n' in body
    assert b'name="policy"\r\n\r\np\r\n' in body
    assert b'filename="artifacts.zip"\r\nContent-Type: application/zip\r\n\r\nzip\r\n' in body
    assert body.index(b'name="policy"') < body.index(b'name="file"')
    assert "Authorization" not in request.headers


@responses.activate
def test_upload_retries_on_5xx(api, archive):
    responses.post(STORAGE_URL, status=500)
    responses.post(STORAGE_URL, status=204)

    api.upload_artifacts(UPLOAD_URL, archive)

    assert len(responses.calls) == 2


@responses.activate
def test_upload_retries_on_connection_error(api, archive):
    responses.post(STORAGE_URL, body=requests.ConnectionError("boom"))
    responses.post(STORAGE_URL, status=204)

    api.upload_artifacts(UPLOAD_URL, archive)

    assert len(responses.calls) == 2


@responses.activate
def test_upload_fails_after_all_attempts(api, archive):
    for _ in range(3):
        responses.post(STORAGE_URL, status=503)

    with pytest.raises(APIError, match="after 3 attempts: HTTP 503"):
        api.upload_artifacts(UPLOAD_URL, archive)

    assert len(responses.calls) == 3


@responses.activate
def test_upload_does_not_retry_on_4xx(api, archive):
    responses.post(STORAGE_URL, status=403)

    with pytest.raises(APIError, match="HTTP 403"):
        api.upload_artifacts(UPLOAD_URL, archive)

    assert len(responses.calls) == 1

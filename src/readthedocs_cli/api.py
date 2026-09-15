"""HTTP client for the Read the Docs upload API."""

import logging
import time
from pathlib import Path

import requests

from readthedocs_cli import __version__
from readthedocs_cli.exceptions import APIError


log = logging.getLogger(__name__)

API_TIMEOUT = 30
UPLOAD_TIMEOUT = 10 * 60
UPLOAD_ATTEMPTS = 3
RETRY_DELAY = 1  # seconds, doubled after each failed attempt


class ReadTheDocsAPI:
    def __init__(self, base_url: str, token: str, session: requests.Session | None = None):
        self.base_url = base_url.rstrip("/")
        self.session = session or requests.Session()
        self.session.headers["Authorization"] = f"Token {token}"
        self.session.headers["User-Agent"] = f"readthedocs-cli/{__version__}"

    def initiate_upload(self, project: str, version: dict) -> dict:
        return self._post("/api/v3/upload/initiate/", {"project": project, "version": version})

    def complete_upload(self, build_id: int, status: str) -> dict:
        return self._post("/api/v3/upload/complete/", {"build": build_id, "status": status})

    def upload_artifacts(self, upload_url: dict, path: Path) -> None:
        """
        POST the archive to the presigned URL.

        Retries on connection errors and 5xx responses. Uses a bare request (no session)on purpose,
        so the API token is never sent to the S3 storage.
        """
        url = upload_url["url"]
        delay = RETRY_DELAY
        for attempt in range(1, UPLOAD_ATTEMPTS + 1):
            log.debug("POST %s (attempt %d/%d)", url, attempt, UPLOAD_ATTEMPTS)
            try:
                with open(path, "rb") as fh:
                    response = requests.post(
                        url,
                        data=upload_url["fields"],
                        files={"file": (path.name, fh, "application/zip")},
                        timeout=UPLOAD_TIMEOUT,
                    )
            except (requests.ConnectionError, requests.Timeout) as exc:
                error = str(exc)
            else:
                if response.ok:
                    return
                error = f"HTTP {response.status_code}"
                log.debug("Storage response: %s", response.text)
                if response.status_code < 500:
                    raise APIError(f"Upload to storage failed: {error}")

            if attempt == UPLOAD_ATTEMPTS:
                raise APIError(
                    f"Upload to storage failed after {UPLOAD_ATTEMPTS} attempts: {error}"
                )
            log.warning("Upload to storage failed (%s). Retrying in %d seconds.", error, delay)
            time.sleep(delay)
            delay *= 2

    def _post(self, path: str, payload: dict) -> dict:
        url = f"{self.base_url}{path}"
        log.debug("POST %s", url)
        try:
            response = self.session.post(url, json=payload, timeout=API_TIMEOUT)
        except requests.RequestException as exc:
            raise APIError(f"Request to {url} failed: {exc}") from exc
        if not response.ok:
            raise APIError(f"{url} returned HTTP {response.status_code}: {_error_detail(response)}")
        return response.json()


def _error_detail(response: requests.Response) -> str:
    """The ``detail`` message from the API, or the raw body when there is none."""
    try:
        return response.json()["detail"]
    except (ValueError, KeyError, TypeError):
        return response.text

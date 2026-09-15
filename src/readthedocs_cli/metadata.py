"""
Resolve the version metadata (name, type and commit) from the environment.

Supported today: GitHub Actions and a local git checkout.
Inference for other CI providers (GitLab CI, CircleCI, etc.) will be added here later.
"""

import json
import logging
import os
import subprocess
from dataclasses import dataclass

from readthedocs_cli.exceptions import ReadTheDocsError


log = logging.getLogger(__name__)

BRANCH = "branch"
TAG = "tag"
EXTERNAL = "external"
VERSION_TYPES = (BRANCH, TAG, EXTERNAL)

FLAGS = {
    "name": "--version-name",
    "type": "--version-type",
    "commit": "--commit",
}


@dataclass
class Version:
    name: str
    type: str
    commit: str


def resolve_version(
    name: str | None = None,
    type: str | None = None,
    commit: str | None = None,
) -> Version:
    """Return the version to upload, inferring any field that wasn't given explicitly."""
    explicit = {"name": name, "type": type, "commit": commit}
    if all(explicit.values()):
        return Version(**explicit)

    inferred = _from_github_actions() or _from_git()
    values = {key: value or inferred.get(key) for key, value in explicit.items()}
    missing = [key for key, value in values.items() if not value]
    if missing:
        flags = ", ".join(FLAGS[key] for key in missing)
        raise ReadTheDocsError(
            f"Could not infer the version {', '.join(missing)} from the environment. "
            f"Pass {flags} explicitly."
        )
    return Version(**values)


def _from_github_actions() -> dict:
    # https://docs.github.com/en/actions/reference/workflows-and-actions/variables
    if os.environ.get("GITHUB_ACTIONS") != "true":
        return {}

    event_name = os.environ.get("GITHUB_EVENT_NAME")
    if event_name in ("pull_request", "pull_request_target"):
        # GITHUB_SHA is the ephemeral merge commit on pull requests.
        # The commit users expect is the head of the pull request.
        with open(os.environ["GITHUB_EVENT_PATH"]) as fh:
            pull_request = json.load(fh)["pull_request"]
        log.debug("Version inferred from GitHub Actions pull request event.")
        return {
            "name": str(pull_request["number"]),
            "type": EXTERNAL,
            "commit": pull_request["head"]["sha"],
        }

    ref_type = os.environ.get("GITHUB_REF_TYPE")
    if ref_type in (BRANCH, TAG):
        log.debug("Version inferred from GitHub Actions %s event.", event_name)
        return {
            "name": os.environ.get("GITHUB_REF_NAME"),
            "type": ref_type,
            "commit": os.environ.get("GITHUB_SHA"),
        }
    return {}


def _from_git() -> dict:
    commit = _git("rev-parse", "HEAD")
    if not commit:
        log.debug("Not a git repository, or git is not installed.")
        return {}

    values = {"commit": commit}
    branch = _git("symbolic-ref", "--short", "-q", "HEAD")
    if branch:
        values.update(name=branch, type=BRANCH)
    else:
        tag = _git("describe", "--tags", "--exact-match", "HEAD")
        if tag:
            values.update(name=tag, type=TAG)
    log.debug("Version inferred from git: %s", values)
    return values


def _git(*args: str) -> str | None:
    try:
        result = subprocess.run(["git", *args], capture_output=True, text=True, check=False)
    except FileNotFoundError:
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None

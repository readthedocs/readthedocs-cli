import logging
import os
import sys
import tempfile
from pathlib import Path

import click

from readthedocs_cli import __version__
from readthedocs_cli.api import ReadTheDocsAPI
from readthedocs_cli.archive import create_archive
from readthedocs_cli.exceptions import ReadTheDocsError
from readthedocs_cli.metadata import VERSION_TYPES
from readthedocs_cli.metadata import resolve_version


log = logging.getLogger(__name__)

DEFAULT_API_URL = "https://app.readthedocs.org"
FORK_SECRETS_DOCS = "https://docs.github.com/en/actions/security-for-github-actions/security-guides/using-secrets-in-github-actions"


@click.group()
@click.version_option(__version__, prog_name="readthedocs")
@click.option(
    "--api-url",
    envvar="READTHEDOCS_API_URL",
    default=DEFAULT_API_URL,
    show_default=True,
    show_envvar=True,
    help="Base URL of the Read the Docs instance.",
)
@click.option("-v", "--verbose", is_flag=True, help="Show debug output.")
@click.pass_context
def main(ctx: click.Context, api_url: str, verbose: bool) -> None:
    """Read the Docs command line client."""
    _configure_logging(verbose)
    ctx.obj = {"api_url": api_url}


@main.command()
@click.option("--project-slug", required=True, help="Slug of the project to upload to.")
@click.option(
    "--html-dir",
    required=True,
    type=click.Path(path_type=Path),
    help="Directory containing the built HTML.",
)
@click.option("--pdf", type=click.Path(path_type=Path), help="PDF file to upload.")
@click.option("--epub", type=click.Path(path_type=Path), help="ePub file to upload.")
@click.option("--htmlzip", type=click.Path(path_type=Path), help="HTML zip file to upload.")
@click.option(
    "--privacy-level",
    type=click.Choice(["public", "private"]),
    help="Privacy level of the version. Read the Docs for Business only.",
)
@click.option(
    "--version-name",
    help="Branch or tag name, or pull request number. Inferred from the environment when omitted.",
)
@click.option(
    "--version-type",
    type=click.Choice(VERSION_TYPES),
    help="Inferred from the environment when omitted.",
)
@click.option("--commit", help="Full commit hash. Inferred from the environment when omitted.")
@click.pass_context
def upload(
    ctx: click.Context,
    project_slug: str,
    html_dir: Path,
    pdf: Path | None,
    epub: Path | None,
    htmlzip: Path | None,
    privacy_level: str | None,
    version_name: str | None,
    version_type: str | None,
    commit: str | None,
) -> None:
    """Upload pre-built documentation artifacts to Read the Docs."""
    files = {
        type_: path
        for type_, path in {"pdf": pdf, "epub": epub, "htmlzip": htmlzip}.items()
        if path is not None
    }
    try:
        build_url = _upload(
            api_url=ctx.obj["api_url"],
            project_slug=project_slug,
            html_dir=html_dir,
            files=files,
            privacy_level=privacy_level,
            version_name=version_name,
            version_type=version_type,
            commit=commit,
        )
    except ReadTheDocsError as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(build_url)


def _upload(
    *,
    api_url: str,
    project_slug: str,
    html_dir: Path,
    files: dict[str, Path],
    privacy_level: str | None,
    version_name: str | None,
    version_type: str | None,
    commit: str | None,
) -> str:
    token = _get_token()
    version = resolve_version(name=version_name, type=version_type, commit=commit)
    log.info(
        "Uploading %s %r at commit %s to project %r.",
        version.type,
        version.name,
        version.commit,
        project_slug,
    )
    payload = {"name": version.name, "type": version.type, "commit": version.commit}
    if privacy_level:
        payload["privacy_level"] = privacy_level

    api = ReadTheDocsAPI(api_url, token)
    with tempfile.TemporaryDirectory() as tmp_dir:
        archive = create_archive(html_dir, files, Path(tmp_dir) / "artifacts.zip")

        response = api.initiate_upload(project_slug, payload)
        build = response["build"]
        build_url = build["urls"]["build"]
        log.info("Build #%s created: %s", build["id"], build_url)

        log.info("Uploading archive.")
        try:
            api.upload_artifacts(response["upload_url"], archive)
        except BaseException:
            _report_failure(api, build["id"])
            raise

    api.complete_upload(build["id"], "success")
    log.info("Upload complete. The build will be processed shortly.")
    return build_url


def _report_failure(api: ReadTheDocsAPI, build_id: int) -> None:
    log.error("Upload failed. Reporting the failure to Read the Docs.")
    try:
        api.complete_upload(build_id, "failed")
    except ReadTheDocsError as exc:
        log.error("Could not report the failure: %s", exc)


def _get_token() -> str:
    token = os.environ.get("READTHEDOCS_TOKEN")
    if token:
        return token
    message = "READTHEDOCS_TOKEN environment variable is not set."
    if (
        os.environ.get("GITHUB_ACTIONS") == "true"
        and os.environ.get("GITHUB_EVENT_NAME") == "pull_request"
    ):
        message += (
            " Secrets are not available to workflows triggered by pull requests from forks."
            f" See {FORK_SECRETS_DOCS}"
        )
    raise ReadTheDocsError(message)


def _configure_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s" if verbose else "%(levelname)s: %(message)s",
        stream=sys.stderr,
        force=True,
    )

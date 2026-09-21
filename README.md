# readthedocs-cli

Command line client for [Read the Docs](https://readthedocs.com/).
Build your documentation anywhere and upload the artifacts to Read the Docs for hosting.

## Installation

```bash
uvx --from readthedocs-upload readthedocs --help
# or
pip install readthedocs-upload
```

Python 3.10 or newer is required.

## Usage

```bash
export READTHEDOCS_TOKEN=...
readthedocs upload --project-slug my-project --html _build/html
```

Downloadable formats are optional and point at a single file each:

```bash
readthedocs upload \
    --project-slug my-project \
    --html _build/html \
    --pdf _build/latex/my-project.pdf \
    --epub _build/epub/my-project.epub
```

Run `readthedocs upload --help` for all options.

### Environment variables

| Variable | Description |
|---|---|
| `READTHEDOCS_TOKEN` | API token. Required. Never passed as a command line argument. |
| `READTHEDOCS_API_URL` | Base URL of the Read the Docs instance. Defaults to `https://app.readthedocs.org`. Same as `--api-url`. |

### Version metadata

The client infers the version to upload from the environment.
Every inferred value can be overridden with `--version-name`, `--version-type` and `--commit`.

| Environment | name | type | commit |
|---|---|---|---|
| GitHub Actions, push to a branch | `GITHUB_REF_NAME` | `branch` | `GITHUB_SHA` |
| GitHub Actions, push of a tag | `GITHUB_REF_NAME` | `tag` | `GITHUB_SHA` |
| GitHub Actions, pull request | pull request number | `external` | pull request head commit |
| CircleCI, push to a branch | `CIRCLE_BRANCH` | `branch` | `CIRCLE_SHA1` |
| CircleCI, push of a tag | `CIRCLE_TAG` | `tag` | `CIRCLE_SHA1` |
| CircleCI, pull request | pull request number | `external` | `CIRCLE_SHA1` |
| Local git checkout, on a branch | branch name | `branch` | `HEAD` |
| Local git checkout, on a tag | tag name | `tag` | `HEAD` |

On CircleCI, a build is treated as a pull request when `CIRCLE_PULL_REQUEST` is set,
which requires the pull request to be open when the pipeline is triggered.

Other CI providers work with the explicit flags.

### GitHub Actions

On GitHub, use the [readthedocs/upload-action](https://github.com/readthedocs/upload-action),
which wraps this client and resolves the Git metadata from the workflow event:

```yaml
- uses: readthedocs/upload-action@v1
  with:
    token: ${{ secrets.READTHEDOCS_TOKEN }}
    project-slug: my-project
    html: _build/html
```

### CircleCI

Store the token as a `READTHEDOCS_TOKEN` project environment variable and run the client after the build step.
The version metadata is inferred from the CircleCI built-in environment variables.
Running the client with `uvx` keeps its dependencies out of the environment used to build the documentation.
The `cimg/python` images ship `uv` preinstalled:

```yaml
- run:
    name: Upload documentation to Read the Docs
    command: uvx --from readthedocs-upload readthedocs upload --project-slug my-project --html _build/html
```

On images without `uv`, install it first with `curl -LsSf https://astral.sh/uv/install.sh | sh`.

Tag builds need a `filters.tags` entry in the workflow, since CircleCI does not run jobs on tags by default.

## Development

```bash
git submodule update --init
uv sync
uv run readthedocs --help
uv run --with tox --with tox-uv tox
```

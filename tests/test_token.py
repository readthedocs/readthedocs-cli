import pytest

from readthedocs_cli.token import TokenInfo
from readthedocs_cli.token import parse_token


@pytest.mark.parametrize(
    ("token", "expected"),
    [
        ("rtdcommunity_project_abc123_secret", TokenInfo(platform="rtdcommunity", scope="project")),
        ("rtdbusiness_project_abc123_secret", TokenInfo(platform="rtdbusiness", scope="project")),
        # Other scopes still infer the platform.
        ("rtdcommunity_user_abc123_secret", TokenInfo(platform="rtdcommunity", scope="user")),
        (
            "rtdbusiness_organization_abc123_secret",
            TokenInfo(platform="rtdbusiness", scope="organization"),
        ),
        # User tokens, or tokens from platforms we don't know about.
        ("0123456789abcdef", TokenInfo()),
        ("rtdxyz_project_abc123_secret", TokenInfo()),
        ("", TokenInfo()),
    ],
)
def test_parse_token(token, expected):
    assert parse_token(token) == expected


@pytest.mark.parametrize(
    "token",
    [
        # The platform must match exactly, and be the first part of the token.
        "RTDCOMMUNITY_project_abc123_secret",
        "Rtdbusiness_project_abc123_secret",
        "rtdcommunityx_project_abc123_secret",
        "rtdcommunityproject_abc123_secret",
        "xrtdcommunity_project_abc123_secret",
        "_rtdcommunity_project_abc123_secret",
        " rtdcommunity_project_abc123_secret",
        # Other separators.
        "rtdcommunity-project-abc123-secret",
        "rtdcommunity.project.abc123.secret",
        # Old prefixes, they were never released.
        "rtdorg_project_abc123_secret",
        "rtdcom_project_abc123_secret",
        "_",
        "___",
    ],
)
def test_parse_malformed_token_infers_nothing(token):
    assert parse_token(token) == TokenInfo()


@pytest.mark.parametrize(
    "token",
    [
        "rtdcommunity",
        "rtdcommunity_",
        "rtdcommunity__abc123_secret",
        "rtdcommunity___",
    ],
)
def test_parse_token_without_scope_infers_only_the_platform(token):
    info = parse_token(token)

    assert info == TokenInfo(platform="rtdcommunity")
    assert info.api_url == "https://app.readthedocs.org"
    assert not info.is_project_scoped


@pytest.mark.parametrize(
    ("token", "scope"),
    [
        # The scope is kept as is, only an exact "project" scope infers the project.
        ("rtdbusiness_PROJECT_abc123_secret", "PROJECT"),
        ("rtdbusiness_projects_abc123_secret", "projects"),
        ("rtdbusiness_project-x_abc123_secret", "project-x"),
        ("rtdbusiness_ project_abc123_secret", " project"),
    ],
)
def test_parse_token_with_unknown_scope_is_not_project_scoped(token, scope):
    info = parse_token(token)

    assert info == TokenInfo(platform="rtdbusiness", scope=scope)
    assert info.api_url == "https://app.readthedocs.com"
    assert not info.is_project_scoped


@pytest.mark.parametrize(
    "token",
    [
        # Missing the random part or the secret, the API rejects these,
        # but the platform and scope can still be inferred.
        "rtdcommunity_project",
        "rtdcommunity_project_",
        "rtdcommunity_project_abc123",
        "rtdcommunity_project__",
        # Extra parts.
        "rtdcommunity_project_abc123_secret_extra",
    ],
)
def test_parse_incomplete_project_token(token):
    info = parse_token(token)

    assert info == TokenInfo(platform="rtdcommunity", scope="project")
    assert info.is_project_scoped


def test_api_url_and_scope():
    assert parse_token("rtdcommunity_project_a_b").api_url == "https://app.readthedocs.org"
    assert parse_token("rtdbusiness_project_a_b").api_url == "https://app.readthedocs.com"
    assert parse_token("rtdbusiness_project_a_b").is_project_scoped
    assert parse_token("rtdbusiness_organization_a_b").api_url == "https://app.readthedocs.com"
    assert not parse_token("rtdbusiness_organization_a_b").is_project_scoped
    assert parse_token("secret").api_url is None
    assert not parse_token("secret").is_project_scoped

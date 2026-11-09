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


def test_api_url_and_scope():
    assert parse_token("rtdcommunity_project_a_b").api_url == "https://app.readthedocs.org"
    assert parse_token("rtdbusiness_project_a_b").api_url == "https://app.readthedocs.com"
    assert parse_token("rtdbusiness_project_a_b").is_project_scoped
    assert parse_token("rtdbusiness_organization_a_b").api_url == "https://app.readthedocs.com"
    assert not parse_token("rtdbusiness_organization_a_b").is_project_scoped
    assert parse_token("secret").api_url is None
    assert not parse_token("secret").is_project_scoped

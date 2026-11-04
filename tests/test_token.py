import pytest

from readthedocs_cli.token import TokenInfo
from readthedocs_cli.token import parse_token


@pytest.mark.parametrize(
    ("token", "expected"),
    [
        ("rtdorg_project_abc123_secret", TokenInfo(platform="rtdorg", scope="project")),
        ("rtdcom_project_abc123_secret", TokenInfo(platform="rtdcom", scope="project")),
        # Other scopes still infer the platform.
        ("rtdorg_user_abc123_secret", TokenInfo(platform="rtdorg", scope="user")),
        ("rtdcom_organization_abc123_secret", TokenInfo(platform="rtdcom", scope="organization")),
        # User tokens, or tokens from platforms we don't know about.
        ("0123456789abcdef", TokenInfo()),
        ("rtdxyz_project_abc123_secret", TokenInfo()),
        ("", TokenInfo()),
    ],
)
def test_parse_token(token, expected):
    assert parse_token(token) == expected


def test_api_url_and_scope():
    assert parse_token("rtdorg_project_a_b").api_url == "https://app.readthedocs.org"
    assert parse_token("rtdcom_project_a_b").api_url == "https://app.readthedocs.com"
    assert parse_token("rtdcom_project_a_b").is_project_scoped
    assert parse_token("rtdcom_organization_a_b").api_url == "https://app.readthedocs.com"
    assert not parse_token("rtdcom_organization_a_b").is_project_scoped
    assert parse_token("secret").api_url is None
    assert not parse_token("secret").is_project_scoped

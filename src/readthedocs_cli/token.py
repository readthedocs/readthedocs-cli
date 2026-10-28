"""
Infer the platform and scope of a Read the Docs API token from its prefix.

API tokens have the form ``<platform>_<scope>_<random>_<secret>``,
for example ``rtdorg_project_<random>_<secret>``.
User tokens have no prefix, nothing is inferred from them.
The project is only inferred from project scoped tokens.
"""

from dataclasses import dataclass


PLATFORM_API_URLS = {
    "rtdorg": "https://app.readthedocs.org",
    "rtdcom": "https://app.readthedocs.com",
}
PROJECT_SCOPE = "project"


@dataclass
class TokenInfo:
    platform: str | None = None
    scope: str | None = None

    @property
    def api_url(self) -> str | None:
        return PLATFORM_API_URLS.get(self.platform)

    @property
    def is_project_scoped(self) -> bool:
        return self.scope == PROJECT_SCOPE


def parse_token(token: str) -> TokenInfo:
    """
    Return the platform and scope of the token.

    The platform is inferred from any of our tokens, whatever their scope,
    the scope is kept as is, so new scopes (organization, user) work without changes.
    """
    platform, _, rest = token.partition("_")
    if platform not in PLATFORM_API_URLS:
        return TokenInfo()
    scope, _, _ = rest.partition("_")
    return TokenInfo(platform=platform, scope=scope or None)

"""
Infer the platform and scope of a Read the Docs API token from its prefix.

API tokens have the form ``<platform>_<scope>_<random>_<secret>``,
for example ``rtdorg_project_<random>_<secret>``.
User tokens have no prefix, nothing is inferred from them.
"""

from dataclasses import dataclass


PLATFORM_API_URLS = {
    "rtdorg": "https://app.readthedocs.org",
    "rtdcom": "https://app.readthedocs.com",
}
PROJECT_SCOPE = "project"
SCOPES = (PROJECT_SCOPE,)


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
    platform, _, rest = token.partition("_")
    scope, _, _ = rest.partition("_")
    if platform not in PLATFORM_API_URLS or scope not in SCOPES:
        return TokenInfo()
    return TokenInfo(platform=platform, scope=scope)

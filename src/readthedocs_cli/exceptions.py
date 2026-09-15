class ReadTheDocsError(Exception):
    """Error reported to the user without a traceback."""


class APIError(ReadTheDocsError):
    """The API or the storage returned an error response."""

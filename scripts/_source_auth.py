"""Credential handling for the agent-facing public-source adapters.

Only the user's process environment supplies credentials. Responses are ordinary
metadata, never a credential export; sanitizing also covers a source that echoes
an input secret or unexpectedly returns an authentication-shaped field.
"""
from __future__ import annotations

import os
import re
from typing import Any
from urllib import error, parse, request

AUTH_ENVIRONMENT = (
    "RMIS_API_KEY", "RMPC_API_KEY", "RMIS_JWT", "RMIS_EMAIL", "RMIS_PASSWORD",
    "PTAGIS_API_TOKEN", "PTAGIS_API_KEY", "STREAMNET_API_KEY",
)
CREDENTIAL_FIELDS = frozenset({
    "password", "passwd", "token", "authtoken", "apikey", "xapikey", "authorization",
    "accesstoken", "refreshtoken", "idtoken", "clientsecret", "secret", "credential", "credentials", "cookie", "setcookie",
})
REDACTED = "[REDACTED]"


def credential_field(name: str) -> bool:
    return re.sub(r"[^a-z0-9]", "", name.lower()) in CREDENTIAL_FIELDS


def redact_credentials(value: Any) -> Any:
    """Return a copy safe for ordinary output, files and error messages."""
    secrets = {os.environ[name] for name in AUTH_ENVIRONMENT if os.environ.get(name)}
    variants = secrets | {parse.quote(secret, safe="") for secret in secrets} | {parse.quote_plus(secret) for secret in secrets}

    def text(value: str) -> str:
        for secret in sorted(variants, key=len, reverse=True):
            value = value.replace(secret, REDACTED)
        return value

    def clean(item: Any) -> Any:
        if isinstance(item, dict):
            return {
                text(str(key)): REDACTED if credential_field(str(key)) else clean(content)
                for key, content in item.items()
            }
        if isinstance(item, (list, tuple)):
            return [clean(content) for content in item]
        return text(item) if isinstance(item, str) else item

    return clean(value)


def authenticated_headers(headers: dict[str, str] | None) -> bool:
    return any(credential_field(name) for name in (headers or {}))


class SourcePolicyError(RuntimeError):
    """A public, credential-free refusal reason."""
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def _origin(url: str) -> tuple[str, str, int]:
    try:
        parsed = parse.urlsplit(url)
        port = parsed.port if parsed.port is not None else (443 if parsed.scheme == "https" else 80)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username is not None or parsed.password is not None:
            raise ValueError
        return parsed.scheme, parsed.hostname.lower(), port
    except ValueError:
        raise SourcePolicyError("https_required", "Authenticated source requests require an HTTPS URL without user information.") from None


def source_urlopen(req: request.Request, *, timeout: int, allowed_origins=None):
    """Keep named-source requests within policy before every network hop."""
    sensitive = authenticated_headers(dict(req.header_items()))
    validate_source_destination(req.full_url, allowed_origins)
    original = req.full_url if sensitive else None

    class OriginRedirects(request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            validate_source_destination(newurl, allowed_origins, authenticated_origin=original)
            return super().redirect_request(req, fp, code, msg, headers, newurl)

    return request.build_opener(OriginRedirects()).open(req, timeout=timeout)


def contains_inline_credentials(value: Any) -> bool:
    """Refuse credential-shaped input fields, including nested query parameters."""
    if isinstance(value, dict):
        for key, content in value.items():
            if credential_field(str(key)) or str(key).lower() == "email":
                return True
            if key in {"params", "path"} and isinstance(content, str):
                # params is a query string, so '?' inside a value is data.
                # path is a URL/path and only its actual query is relevant.
                query = content.lstrip("?") if key == "params" else parse.urlsplit(content).query
                if _query_contains_credentials(query):
                    return True
            if contains_inline_credentials(content):
                return True
    elif isinstance(value, list):
        return any(contains_inline_credentials(content) for content in value)
    return False


def _query_contains_credentials(query: str) -> bool:
    return any(credential_field(name) or name.lower() == "email" for name, _ in parse.parse_qsl(query, keep_blank_values=True))


def source_path_segment(value: str | int) -> str:
    """Treat a source identifier as one opaque path segment, never URL syntax."""
    if not isinstance(value, str) and type(value) is not int:
        raise SourcePolicyError("invalid_identifier", "Source identifiers must be text or integers.")
    text = str(value)
    if not text or any(ord(character) < 32 or ord(character) == 127 for character in text):
        raise SourcePolicyError("invalid_identifier", "Source identifiers must be nonempty and contain no control characters.")
    queries = [text.partition("?")[2], text.partition("#")[2]]
    if "=" in text:
        queries.append(text)
    if any(_query_contains_credentials(query) for query in queries):
        raise SourcePolicyError("inline_credentials_refused", "Credentials cannot be supplied in source identifiers or URLs. Use the local environment.")
    return parse.quote(text, safe="")


def validate_source_url(url: str) -> None:
    """Check the actual outgoing URL after all path and query construction."""
    try:
        parsed = parse.urlsplit(url)
    except ValueError:
        raise SourcePolicyError("invalid_source_url", "The source URL is invalid.") from None
    # Opaque encoded identifiers cannot hide credential-shaped query syntax.
    for segment in parsed.path.split("/"):
        if segment:
            source_path_segment(parse.unquote(segment))
    if parsed.username is not None or parsed.password is not None or _query_contains_credentials(parsed.query) or _query_contains_credentials(parsed.fragment):
        raise SourcePolicyError("inline_credentials_refused", "Credentials cannot be supplied in source identifiers or URLs. Use the local environment.")


def validate_source_destination(url: str, allowed_origins, *, authenticated_origin: str | None = None) -> None:
    validate_source_url(url)
    if not allowed_origins:
        raise SourcePolicyError("destination_policy_required", "Source requests require an explicit destination policy.")
    origin = _origin(url)
    if origin not in {_origin(allowed) for allowed in allowed_origins}:
        raise SourcePolicyError("destination_refused", "The destination is outside the named source origin policy.")
    if authenticated_origin is not None and origin != _origin(authenticated_origin):
        raise SourcePolicyError("redirect_refused", "Authenticated source redirects must remain on the original HTTPS origin.")

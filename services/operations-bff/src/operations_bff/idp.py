"""Application-layer port to an OIDC identity provider.

The port returns only a provider-validated identity: access, refresh and ID
tokens stay inside the concrete adapter, which does not exist yet.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .session import AuthenticatedIdentity


class IdentityProviderError(Exception):
    """The provider refused the code, verifier, nonce or token validation."""


class IdentityProviderUnavailable(Exception):
    """The provider could not be reached or answered unusably."""


@dataclass(frozen=True)
class AuthorizationRequest:
    state: str
    code_challenge: str
    nonce: str
    code_challenge_method: str = "S256"
    redirect_uri: str | None = None


class IdentityProvider(Protocol):
    def authorization_url(self, request: AuthorizationRequest) -> str:
        """Provider URL the browser is redirected to (adapter owns client config)."""
        ...

    def complete(
        self,
        *,
        code: str,
        code_verifier: str,
        nonce: str,
        redirect_uri: str | None = None,
    ) -> AuthenticatedIdentity:
        """Exchange the code server side and return the validated identity.

        Raises IdentityProviderError on refusal and IdentityProviderUnavailable
        when the provider cannot answer.
        """
        ...

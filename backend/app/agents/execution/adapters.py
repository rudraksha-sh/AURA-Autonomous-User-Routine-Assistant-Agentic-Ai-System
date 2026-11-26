"""Provider boundary for an allowlisted synthetic calendar hold."""
from dataclasses import dataclass
from typing import Protocol


PROVIDER = "sandbox_calendar"
OPERATION = "calendar.hold.create"
CONSENT_VERSION = "sandbox-hold-v1"


@dataclass(frozen=True)
class ProviderReceipt:
    identifier: str
    fingerprint: str


class NoEffectRetryable(Exception):
    """Adapter has affirmative evidence that the provider applied no effect."""


class ProviderAdapter(Protocol):
    def apply(self, *, key: str, resource: str, payload: dict, fingerprint: str, timeout_seconds: int) -> ProviderReceipt: ...

    def lookup(self, *, key: str, resource: str, timeout_seconds: int) -> ProviderReceipt | None: ...

    def compensate(self, *, key: str, resource: str, receipt: dict, timeout_seconds: int) -> str: ...


# Only an explicitly supplied synthetic adapter can run this action.
# The application ships without live adapters or provider credentials here.
ADAPTERS: dict[tuple[str, str], ProviderAdapter] = {}


def get_adapter(provider: str, operation: str) -> ProviderAdapter | None:
    return ADAPTERS.get((provider, operation))

"""One error type with stable codes, so callers and tests branch on ``code``."""


class ContractError(ValueError):
    """A registry, version-rule or boundary failure.

    ``code`` is a stable upper-case identifier; ``detail`` is bounded text that never
    contains payload values.
    """

    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code
        self.detail = detail

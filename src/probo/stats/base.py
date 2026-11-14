# SPDX-License-Identifier: Apache-2.0
"""Base model for Probo's statistics values: frozen, strict, re-validated on copy."""

import copy
from collections.abc import Mapping
from typing import Any, ClassVar, Self, cast

from pydantic import BaseModel, ConfigDict, ModelWrapValidatorHandler, model_validator

DERIVED_TOLERANCE = 1e-9
"""Largest absolute difference allowed between a supplied derived float and its recomputed value."""


class FrozenModel(BaseModel):
    """Frozen, strict model that keeps its invariants under validation and ``model_copy``.

    Enforced: construction, ``model_validate``, ``model_validate_json`` and
    ``model_copy(update=...)`` all run full validation, so every instance obtained through them
    satisfies the subclass's checks. Not enforced: ``model_construct`` and
    ``object.__setattr__`` bypass validation by design.

    Derived values (listed in ``DERIVED``) are never stored; they are computed from the stored
    fields and appear in ``model_dump`` and JSON output as computed fields. On input the
    derived keys may be omitted. When one is present, ``check_derived`` must accept it as
    agreeing with the recomputed value (floats within ``DERIVED_TOLERANCE``), otherwise
    validation fails; the instance always holds the recomputed value, never the supplied one.
    """

    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")

    DERIVED: ClassVar[tuple[str, ...]] = ()
    """Names of computed fields that input may carry and that are checked, not stored."""

    @model_validator(mode="wrap")
    @classmethod
    def _supplied_derived_values_agree(
        cls, data: Any, handler: ModelWrapValidatorHandler[Self]
    ) -> Self:
        supplied: dict[str, object] = {}
        if cls.DERIVED and isinstance(data, Mapping):
            fields = dict(cast(Mapping[str, object], data))
            for name in cls.DERIVED:
                if name in fields:
                    supplied[name] = fields.pop(name)
            data = fields
        model = handler(data)
        for name, value in supplied.items():
            model.check_derived(name, value)
        return model

    def check_derived(self, name: str, value: object) -> None:
        """Raise ``ValueError`` unless ``value`` agrees with the recomputed derived ``name``."""
        raise ValueError(f"{type(self).__name__} has no derived value {name!r}")

    def model_copy(self, *, update: Mapping[str, Any] | None = None, deep: bool = False) -> Self:
        """Return a copy with ``update`` applied, fully re-validated (unlike pydantic's default)."""
        data: dict[str, Any] = {name: getattr(self, name) for name in type(self).model_fields}
        if deep:
            data = copy.deepcopy(data)
        data.update(update or {})
        return self.model_validate(data)


def require_close(name: str, supplied: object, computed: float) -> None:
    """Raise ``ValueError`` unless ``supplied`` is a float within the tolerance of ``computed``."""
    if type(supplied) not in (int, float):
        raise ValueError(f"{name} must be a number, got {supplied!r}")
    if not abs(cast(float, supplied) - computed) <= DERIVED_TOLERANCE:
        raise ValueError(f"supplied {name} {supplied} disagrees with computed {computed}")

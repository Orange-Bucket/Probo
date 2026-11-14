# SPDX-License-Identifier: Apache-2.0
"""Dated, versioned text templates for filling scenario text slots, and their loader.

This package holds only the schema and loader; template content lives in the TOML files under
``probo/attacks/corpus/<family>/<version>/``.
"""

from probo.attacks.templates import (
    Corpus,
    CorpusError,
    Template,
    available_versions,
    load_corpus,
    load_corpus_from,
)

__all__ = [
    "Corpus",
    "CorpusError",
    "Template",
    "available_versions",
    "load_corpus",
    "load_corpus_from",
]

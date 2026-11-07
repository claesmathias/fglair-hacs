"""Device model / template detection, mirroring FGLair's config/datasets/template_types.js."""
from __future__ import annotations

import re

from .const import FGL_MODEL_RE, FGLB_MODEL_RE

_FGL_RE = re.compile(FGL_MODEL_RE)
_FGLB_RE = re.compile(FGLB_MODEL_RE)


def device_type(model: str | None) -> str:
    """Return "fgl" (FGLair template A/F), "fglb" (template B) or "ac" (Hisense).

    Development firmware reports models with a "-dev" suffix (e.g. "AP-WB2E-dev");
    the FGLair app strips it before looking up the template, so we do the same.
    """
    model = (model or "").replace("-dev", "")
    if _FGL_RE.fullmatch(model):
        return "fgl"
    if _FGLB_RE.fullmatch(model):
        return "fglb"
    return "ac"

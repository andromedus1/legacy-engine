from __future__ import annotations

import json
from pathlib import Path

from .models import AmplificationProfile

def load_amplification_profile(path: str | Path) -> AmplificationProfile:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return AmplificationProfile.model_validate(payload)

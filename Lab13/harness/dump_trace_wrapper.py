"""One-off trace dump wrapper."""
from __future__ import annotations

import copy
import json
import re
import threading
import time
import unicodedata

from telemetry.cost import cost_from_usage
from telemetry.logger import logger, set_correlation_id
from telemetry.redact import redact
from telemetry.tracing import Tracer

_PROMPT = ""
try:
    with open("solution/prompt.txt", encoding="utf-8") as f:
        _PROMPT = f.read().strip()
except OSError:
    pass

_NOTE_RE = re.compile(r"\s*[-–—]\s*(?:GHI\s*CHU|GHI\s*CHÚ|ghi\s*chu).*$", re.I | re.DOTALL)


def mitigate(call_next, question, config, context):
    conf = copy.deepcopy(config)
    if _PROMPT:
        conf["system_prompt"] = _PROMPT
    question = unicodedata.normalize("NFC", question)
    question = _NOTE_RE.sub("", question).strip()
    result = call_next(question, conf)
    with open("_trace_sample.json", "w", encoding="utf-8") as f:
        json.dump({"question": question, "result": result}, f, ensure_ascii=False, indent=2)
    return result

#!/usr/bin/env python3
import json
from pathlib import Path
import jsonschema

schema=json.loads(Path("schemas/hosted-realization.schema.json").read_text())

direct={
  "schema_version":1,
  "kind":"hosted-realization",
  "provider":"example-provider",
  "requested_model":"example-stable-model",
  "resolved_model":"example-stable-model",
  "provider_model_version":"2026-09-01",
  "system_fingerprint":None,
  "api_interface":"openai-compatible-v1",
  "service_tier":"free",
  "observed_at":"2026-09-20T12:00:00Z",
  "provenance_strength":"VERSIONED_HOSTED",
  "route":{"mode":"direct","intermediary":None,"upstream_provider":None,"fallback_observed":False},
  "evidence":{"source":"qualification-receipt","response_metadata_digest":"sha256:"+"0"*64}
}
jsonschema.validate(direct,schema)

routed=dict(direct)
routed["provider"]="openrouter"
routed["requested_model"]="openrouter/free"
routed["resolved_model"]=None
routed["provider_model_version"]=None
routed["provenance_strength"]="ROUTED_UNKNOWN"
routed["route"]={"mode":"intermediary","intermediary":"openrouter","upstream_provider":None,"fallback_observed":None}
jsonschema.validate(routed,schema)

bad=dict(direct)
bad["provenance_strength"]="IMMUTABLE_ARTIFACT"
try:
    jsonschema.validate(bad,schema)
except jsonschema.ValidationError:
    pass
else:
    raise AssertionError("hosted realization must not claim immutable artifact provenance")

bad_route=dict(direct)
bad_route["route"]={"mode":"magic"}
try:
    jsonschema.validate(bad_route,schema)
except jsonschema.ValidationError:
    pass
else:
    raise AssertionError("unknown routing mode should fail closed")

print("PASS hosted realization contract")

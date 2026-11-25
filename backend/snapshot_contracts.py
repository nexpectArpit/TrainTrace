"""Version markers and compatibility checks for evolving JSON evidence."""

import json


CURRENT_SCHEMA = {
    "environment": 1,
    "dataset": 1,
    "validation": 1,
    "final_evaluation": 1,
    "decision_details": 1,
    "decision_evidence": 1,
    "audit_report": 1,
    "model_manifest": 1,
}
CONFIG_SCHEMA_VERSION = 1


def encode_snapshot(kind, value):
    if kind not in CURRENT_SCHEMA or not isinstance(value, dict):
        raise ValueError(f"Unsupported snapshot contract: {kind}")
    result = dict(value)
    result["snapshot_schema_version"] = CURRENT_SCHEMA[kind]
    return json.dumps(result, allow_nan=False)


def decode_snapshot(raw, kind):
    if raw is None:
        return None
    value = json.loads(raw)
    if not isinstance(value, dict):
        return value
    version = value.get("snapshot_schema_version", 1)
    supported = CURRENT_SCHEMA[kind]
    if not isinstance(version, int) or version < 1 or version > supported:
        raise ValueError(f"Unsupported {kind} schema version: {version}")
    return value


def decode_config(raw):
    if raw is None:
        return None
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ValueError("Run configuration snapshot must be an object")
    version = value.get("config_schema_version", 1)
    if not isinstance(version, int) or version < 1 or version > CONFIG_SCHEMA_VERSION:
        raise ValueError(f"Unsupported run configuration schema version: {version}")
    value["config_schema_version"] = version
    return value

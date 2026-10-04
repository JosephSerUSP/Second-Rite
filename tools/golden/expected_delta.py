#!/usr/bin/env python3
"""Durable, reviewer-authored approvals for expected G5/G6 visual deltas.

An approval never decides that a delta is expected. It records a human/agent
review of one exact relative-capture observation. The comparator fingerprints
that observation from complete base/candidate capture trees plus the named
pixel/topology differences. Any later evidence change misses the fingerprint
and is red again.
"""

import hashlib
import json
import re
from pathlib import Path

SCHEMA_VERSION = 1
DEFAULT_APPROVAL_DIR = Path(__file__).with_name("expected-deltas")


def digest_json(value):
    encoded = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _project_detail(detail):
    return {
        "path": detail["path"],
        "changedPixels": detail["changedPixels"],
        "leftPresent": bool(detail["leftPresent"]),
        "rightPresent": bool(detail["rightPresent"]),
        "leftImage": detail.get("leftImage"),
        "rightImage": detail.get("rightImage"),
    }


def evidence_payload(result):
    surfaces = {}
    for surface in sorted(result.get("surfaces", {})):
        row = result["surfaces"][surface]
        candidate_details = {
            detail["path"]: detail for detail in row.get("candidate", {}).get("details", [])
        }
        surfaces[surface] = {
            "baseCaptureFingerprint": row.get("baseCaptureFingerprint"),
            "candidateCaptureFingerprint": row.get("candidateCaptureFingerprint"),
            "stableDifferences": [
                _project_detail(detail)
                for detail in sorted(
                    row.get("stableCandidateDifferences", []),
                    key=lambda detail: detail["path"],
                )
            ],
            "newTargets": [
                _project_detail(candidate_details[path])
                for path in sorted(row.get("newCandidateFrames", []))
            ],
            "missingTargets": [
                _project_detail(candidate_details[path])
                for path in sorted(row.get("missingCandidateFrames", []))
            ],
        }
    return {
        "schemaVersion": SCHEMA_VERSION,
        "gate": result.get("gate"),
        "surfaces": surfaces,
    }


def evidence_fingerprint(result):
    return digest_json(evidence_payload(result))


def evidence_summary(result):
    stable = []
    new = []
    missing = []
    for surface, row in sorted(result.get("surfaces", {}).items()):
        stable.extend(
            "%s/%s" % (surface, detail["path"])
            for detail in row.get("stableCandidateDifferences", [])
        )
        new.extend(
            "%s/%s" % (surface, path)
            for path in row.get("newCandidateFrames", [])
        )
        missing.extend(
            "%s/%s" % (surface, path)
            for path in row.get("missingCandidateFrames", [])
        )
    return {
        "stableDifferences": sorted(stable),
        "newTargets": sorted(new),
        "missingTargets": sorted(missing),
    }


def promotable(result):
    if result.get("status") != "candidate-diff":
        return False, "only an investigated red candidate-diff can be promoted"

    unstable = []
    for surface, row in result.get("surfaces", {}).items():
        unstable.extend("%s/%s" % (surface, path) for path in row.get("unstableFrames", []))
    if unstable:
        return False, "repeat-control evidence is unstable: %s" % ", ".join(sorted(unstable))

    capture_evidence = result.get("captureEvidence") or {}
    required = ("baseA", "baseB", "candidate")
    missing = [name for name in required if name not in capture_evidence]
    if missing:
        return False, "capture completeness is not recorded for: %s" % ", ".join(missing)
    incomplete = [
        name for name in required
        if capture_evidence.get(name, {}).get("complete") is not True
    ]
    if incomplete:
        return False, "capture evidence is incomplete for: %s" % ", ".join(incomplete)
    return True, None


def build_approval(result, approval_id, reviewer, rationale, references=None):
    ok, reason = promotable(result)
    if not ok:
        raise ValueError(reason)
    approval_id = str(approval_id).strip()
    reviewer = str(reviewer).strip()
    rationale = str(rationale).strip()
    if not approval_id:
        raise ValueError("approval id is required")
    if not reviewer:
        raise ValueError("reviewer is required")
    if not rationale:
        raise ValueError("rationale is required")
    return {
        "schemaVersion": SCHEMA_VERSION,
        "id": approval_id,
        "gate": result["gate"],
        "state": "expected-delta",
        "evidenceFingerprint": evidence_fingerprint(result),
        "evidence": evidence_payload(result),
        "summary": evidence_summary(result),
        "reviewer": reviewer,
        "rationale": rationale,
        "references": list(references or []),
        "pending": "approved reference recapture/update",
        "observedBaseRef": result.get("baseRef"),
        "observedCandidateRef": result.get("candidateRef"),
    }


def safe_filename(approval_id):
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", str(approval_id).strip()).strip("-.")
    if not slug:
        raise ValueError("approval id does not contain a usable filename")
    return slug + ".json"


def load_approvals(directory=DEFAULT_APPROVAL_DIR):
    directory = Path(directory)
    if not directory.exists():
        return []
    approvals = []
    for path in sorted(directory.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("schemaVersion") != SCHEMA_VERSION:
            raise ValueError("%s has unsupported schemaVersion" % path)
        if payload.get("state") != "expected-delta":
            raise ValueError("%s is not an expected-delta record" % path)
        if not payload.get("gate") or not payload.get("evidenceFingerprint"):
            raise ValueError("%s is missing gate/evidenceFingerprint" % path)
        item = dict(payload)
        item["recordPath"] = path.as_posix()
        approvals.append(item)
    return approvals


def find_matching_approval(result, directory=DEFAULT_APPROVAL_DIR):
    fingerprint = evidence_fingerprint(result)
    matches = [
        approval for approval in load_approvals(directory)
        if approval.get("gate") == result.get("gate")
        and approval.get("evidenceFingerprint") == fingerprint
    ]
    if len(matches) > 1:
        raise ValueError(
            "multiple expected-delta approvals match %s/%s" % (result.get("gate"), fingerprint)
        )
    return matches[0] if matches else None

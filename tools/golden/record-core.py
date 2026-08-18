#!/usr/bin/env python3
"""Create durable evidence records for Second Rite's G5/G6 pixel gates.

Live usage (normally through record.ps1):
    python tools/golden/record.py --gate g5
    python tools/golden/record.py --gate g6
    python tools/golden/record.py --gate all

Offline G5 re-analysis from a previously saved ``lovec . screenshots`` output:
    python tools/golden/record.py --from-capture capture.txt --surface classic
    python tools/golden/record.py --from-capture capture-wide.txt --surface wide

The live recorder deliberately *runs the existing check-*.ps1 scripts*. It does
not transcribe the G5 sequence. Temporary PATH shims observe the commands those
scripts already invoke, give every direct child process a timeout, and append a
JSONL step trace. This is how the record can say which of G5's classic capture,
classic comparison, crop invariant, wide capture, or wide comparison failed
without making a second implementation of the gate.

Fixture-tested without a GPU: gate-output parsing, manifest assembly, exact
per-step exit-code preservation, timeout classification, and the differing-frame
record layout. The offline replay path is implemented by calling screens.py
directly, but the real capture parser still needs repository integration coverage. The live PowerShell integration still
needs a Windows checkout with LOVE/lovec, a GPU, and (for effect frames) a built
``effekseer_shim.dll``. G6 additionally needs Chrome and Node. A PR produced in
an environment without those dependencies must say that the live integration
was not exercised.

Records are evidence, never references. This module never writes below
``tools/golden/screens*/`` or ``tools/golden/editor-screens/``. The only files it
reads there are references and the disposable ``*-actual`` outputs already made
by the existing checks. Recapture remains a separate owner-signed action.
"""

from __future__ import print_function

import argparse
import contextlib
import datetime as _dt
import hashlib
import html
import importlib.util
import io
import json
import os
import platform
import re
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

SCHEMA_VERSION = 2
TIMEOUT_EXIT_CODE = 124
UNAVAILABLE_EXIT_CODE = 127
DEFAULT_STEP_TIMEOUT = 180
DEFAULT_GATE_TIMEOUT = 1200

G5_SURFACES = {
    "classic": {
        "ref": "tools/golden/screens",
        "actual": "tools/golden/screens-actual",
        "comparison": "tools/golden/screens-comparison.html",
    },
    "wide": {
        "ref": "tools/golden/screens-wide",
        "actual": "tools/golden/screens-actual-wide",
        "comparison": "tools/golden/screens-comparison-wide.html",
    },
}
G6_SURFACE = {
    "editor": {
        "ref": "tools/golden/editor-screens",
        "actual": "tools/golden/editor-screens-actual",
        "comparison": None,
    }
}


def repo_root():
    return Path(__file__).resolve().parents[2]


def utc_now():
    return _dt.datetime.now(_dt.timezone.utc)


def iso_utc(value):
    return value.astimezone(_dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _decode_for_parse(data):
    if isinstance(data, str):
        return data
    # Windows PowerShell 5.1 has several different output encodings depending
    # on whether it owns a console, redirects to a file, or writes through a
    # native child. Preserve the original bytes on disk, but decode generously
    # for the summary parser. A UTF-16 stream can contain perfectly valid UTF-8
    # byte sequences separated by NULs, so detect it before trying UTF-8.
    if data.startswith((b"\xff\xfe", b"\xfe\xff")):
        try:
            return data.decode("utf-16")
        except UnicodeDecodeError:
            pass
    if b"\x00" in data[:256]:
        try:
            return data.decode("utf-16-le")
        except UnicodeDecodeError:
            pass
    for encoding in ("utf-8-sig", "utf-8", "cp1252"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            pass
    return data.decode("utf-8", errors="replace")


def _git(root, *args):
    try:
        proc = subprocess.run(
            ["git"] + list(args), cwd=str(root), stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, timeout=20, check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0:
        return None
    return _decode_for_parse(proc.stdout).strip()


def git_state(root):
    sha = _git(root, "rev-parse", "HEAD") or "unknown"
    status = _git(root, "status", "--porcelain=v1", "--untracked-files=all")
    return {
        "sha": sha,
        "shortSha": sha[:8] if sha != "unknown" else "unknown",
        "dirty": bool(status),
    }


def git_ignores(root, rel_path):
    try:
        proc = subprocess.run(
            ["git", "check-ignore", "-q", "--", rel_path], cwd=str(root),
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10,
            check=False,
        )
        return proc.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return None


def host_state():
    return {
        "hostname": socket.gethostname(),
        "platform": platform.platform(),
        "python": platform.python_version(),
    }


def ensure_output_is_local_evidence(root, output_root):
    """Keep default records out of git without changing tracked .gitignore.

    #245 was written assuming root ``out/`` was already ignored, but some
    checkouts predate that convention. An ignore file *inside* the generated
    record root can ignore itself plus every record, so the tool preserves the
    local-evidence contract without touching repository policy outside this
    issue's allowed paths. Existing user-authored ignore files are never
    overwritten.
    """
    try:
        rel = output_root.relative_to(root)
    except ValueError:
        return None
    output_root.mkdir(parents=True, exist_ok=True)
    probe = str((rel / ".gitignore-probe")).replace("\\", "/")
    ignored = git_ignores(root, probe)
    if ignored is False:
        local_ignore = output_root / ".gitignore"
        if not local_ignore.exists():
            local_ignore.write_text(
                "# Local gate evidence generated by tools/golden/record.py\n*\n",
                encoding="utf-8", newline="\n",
            )
            ignored = git_ignores(root, probe)
    return ignored


def _safe_record_dir(output_root, started, gate, short_sha):
    stamp = started.strftime("%Y%m%dT%H%M%SZ")
    base = output_root / ("%s-%s-%s" % (stamp, gate, short_sha))
    candidate = base
    suffix = 2
    while candidate.exists():
        candidate = Path(str(base) + "-%d" % suffix)
        suffix += 1
    candidate.mkdir(parents=True, exist_ok=False)
    return candidate


def classify_step(tool, args):
    lowered = [str(arg).replace("\\", "/").lower() for arg in args]
    if tool == "lovec":
        if any(arg == "surface-crop-check" for arg in lowered):
            return "surface-crop-check"
        if "screenshots" in lowered and any(arg == "surface=wide" for arg in lowered):
            return "wide-capture"
        if "screenshots" in lowered:
            return "classic-capture"
    if tool == "python" and lowered:
        script = lowered[0]
        if script.endswith("tools/golden/screens.py") and "check" in lowered:
            if "--surface" in lowered:
                try:
                    index = lowered.index("--surface")
                    if index + 1 < len(lowered) and lowered[index + 1] == "wide":
                        return "wide-check"
                except ValueError:
                    pass
            return "classic-check"
        if script.endswith("tools/golden/editor-screens.py") and "check" in lowered:
            return "editor-check"
    return "%s:%s" % (tool, " ".join(str(arg) for arg in args[:3]))


def _append_jsonl(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(payload, sort_keys=True) + "\n")


def _kill_process_tree(proc):
    if proc.poll() is not None:
        return
    if os.name == "nt":
        try:
            subprocess.run(
                ["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                timeout=15, check=False,
            )
            return
        except (OSError, subprocess.TimeoutExpired):
            pass
    else:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
            return
        except (OSError, ProcessLookupError):
            pass
    try:
        proc.kill()
    except OSError:
        pass


def _run_with_timeout(command, cwd, env, timeout_seconds):
    kwargs = {
        "cwd": str(cwd),
        "env": env,
        "stdout": subprocess.PIPE,
        "stderr": subprocess.PIPE,
    }
    if os.name == "nt":
        kwargs["creationflags"] = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    else:
        kwargs["start_new_session"] = True
    proc = subprocess.Popen(command, **kwargs)
    try:
        stdout, stderr = proc.communicate(timeout=timeout_seconds)
        return proc.returncode, stdout, stderr, False
    except subprocess.TimeoutExpired:
        _kill_process_tree(proc)
        stdout, stderr = proc.communicate()
        return TIMEOUT_EXIT_CODE, stdout, stderr, True


def _raw_capture_name(step_name):
    if step_name == "classic-capture":
        return "classic.txt"
    if step_name == "wide-capture":
        return "wide.txt"
    return None


def exec_step(tool, args):
    """Internal entrypoint used only by the temporary PATH shims."""
    trace = Path(os.environ["SECOND_RITE_RECORD_TRACE"])
    raw_dir = Path(os.environ["SECOND_RITE_RECORD_RAW"])
    timeout_seconds = int(os.environ.get("SECOND_RITE_RECORD_STEP_TIMEOUT", DEFAULT_STEP_TIMEOUT))
    real_key = "SECOND_RITE_RECORD_REAL_%s" % tool.upper()
    real = os.environ.get(real_key, "")
    step_name = classify_step(tool, args)
    started = utc_now()
    monotonic_start = time.monotonic()

    if not real or not Path(real).exists():
        event = {
            "name": step_name,
            "command": tool,
            "args": list(args),
            "startedAtUtc": iso_utc(started),
            "endedAtUtc": iso_utc(utc_now()),
            "durationSeconds": round(time.monotonic() - monotonic_start, 3),
            "outcome": "unavailable",
            "exitCode": None,
            "wrapperExitCode": UNAVAILABLE_EXIT_CODE,
        }
        _append_jsonl(trace, event)
        sys.stderr.write("record.py: %s executable is unavailable\n" % tool)
        return UNAVAILABLE_EXIT_CODE

    # The shim must be transparent: run the real tool in the working directory
    # the gate script chose, not in `root`. Pinning root silently defeated
    # check-screens.ps1's per-invocation working directory, and the Effekseer
    # shim resolves effect paths against the PROCESS working directory, so the
    # recorder rendered the two effect-bearing frames without their effect while
    # a direct gate run did not. A wrapper that changes the observed behaviour
    # is not a measurement.
    code, stdout, stderr, timed_out = _run_with_timeout(
        [real] + list(args), os.getcwd(), os.environ.copy(), timeout_seconds,
    )
    raw_name = _raw_capture_name(step_name)
    if raw_name:
        raw_dir.mkdir(parents=True, exist_ok=True)
        (raw_dir / raw_name).write_bytes(stdout)

    if stdout:
        sys.stdout.buffer.write(stdout)
        sys.stdout.buffer.flush()
    if stderr:
        sys.stderr.buffer.write(stderr)
        sys.stderr.buffer.flush()

    event = {
        "name": step_name,
        "command": tool,
        "args": list(args),
        "startedAtUtc": iso_utc(started),
        "endedAtUtc": iso_utc(utc_now()),
        "durationSeconds": round(time.monotonic() - monotonic_start, 3),
        "outcome": "timeout" if timed_out else ("passed" if code == 0 else "failed"),
        "exitCode": None if timed_out else code,
        "wrapperExitCode": TIMEOUT_EXIT_CODE if timed_out else code,
    }
    _append_jsonl(trace, event)
    return TIMEOUT_EXIT_CODE if timed_out else code


def _write_windows_shim(path, tool):
    # Built by concatenation rather than %-formatting: the batch body is dense
    # with literal percent signs (%VAR%, %*, %ERRORLEVEL%), and mixing those
    # with a format operator means one unescaped pair silently becomes a format
    # spec. Keeping the text literal is what you read is what gets written.
    script = (
        "@echo off\r\n"
        '"%SECOND_RITE_RECORD_REAL_PYTHON%" "%SECOND_RITE_RECORD_SCRIPT%" '
        "_exec-step --tool " + tool + " -- %*\r\n"
        "exit /b %ERRORLEVEL%\r\n"
    )
    path.write_text(script, encoding="utf-8", newline="")


def _write_posix_shim(path, tool):
    script = (
        "#!/bin/sh\n"
        'exec "$SECOND_RITE_RECORD_REAL_PYTHON" "$SECOND_RITE_RECORD_SCRIPT" '
        "_exec-step --tool %s -- \"$@\"\n" % tool
    )
    path.write_text(script, encoding="utf-8")
    path.chmod(0o755)


def _make_shims(directory):
    if os.name == "nt":
        _write_windows_shim(directory / "python.cmd", "python")
        _write_windows_shim(directory / "lovec.cmd", "lovec")
    else:
        _write_posix_shim(directory / "python", "python")
        _write_posix_shim(directory / "lovec", "lovec")


def _powershell_executable():
    candidates = []
    if os.name == "nt":
        windir = os.environ.get("WINDIR")
        if windir:
            candidates.append(Path(windir) / "System32" / "WindowsPowerShell" / "v1.0" / "powershell.exe")
    for name in ("powershell.exe", "powershell", "pwsh.exe", "pwsh"):
        found = shutil.which(name)
        if found:
            candidates.append(Path(found))
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return None


def load_step_trace(path):
    events = []
    path = Path(path)
    if not path.exists():
        return events
    with path.open("r", encoding="utf-8-sig", errors="replace") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                events.append({"name": "trace-parse-error", "outcome": "recording-error", "raw": line})
    return events


_G5_SUMMARY = re.compile(r"^Golden screenshots:\s+(\d+)/(\d+)\s+match\.$")
_G6_SUMMARY = re.compile(r"^Golden editor screenshots:\s+(\d+)/(\d+)\s+match\.$")
_MISMATCH = re.compile(r"^\s*MISMATCH\s+(.+?)\s*$")
_NEW = re.compile(r"^\s*NO REFERENCE\s+(.+?)\s+\(new capture\)\s*$")
_ORPHAN = re.compile(r"^\s*ORPHANED REFERENCE\s+(.+?)\s+\(no longer captured\)\s*$")


def _empty_surface():
    return {"matched": None, "compared": None, "differing": 0, "frames": []}


def _expected_surfaces(gate, source_details=None):
    """Return surfaces this record was intended to compare.

    Offline G5 replays intentionally represent only one saved surface.  Its
    other surface is therefore not expected, rather than an unmeasured gate.
    """
    if source_details and source_details.get("partialGate"):
        return {source_details["surface"]}
    return set(G5_SURFACES if gate == "g5" else ("editor",))


def _measurement_state(name, surface, expected):
    if name not in expected:
        return "not-expected"
    return "measured" if surface.get("compared") is not None else "unmeasured"


def parse_gate_output(gate, stdout_text):
    result = {"surfaces": {}}
    if gate == "g5":
        result["surfaces"] = {"classic": _empty_surface(), "wide": _empty_surface()}
    else:
        result["surfaces"] = {"editor": _empty_surface()}

    current = None
    g5_summary_count = 0
    for raw_line in stdout_text.splitlines():
        line = raw_line.rstrip("\r\n")
        if gate == "g5":
            match = _G5_SUMMARY.match(line)
            if match:
                current = "classic" if g5_summary_count == 0 else "wide"
                g5_summary_count += 1
                surface = result["surfaces"][current]
                surface["matched"] = int(match.group(1))
                surface["compared"] = int(match.group(2))
                continue
        else:
            match = _G6_SUMMARY.match(line)
            if match:
                current = "editor"
                surface = result["surfaces"][current]
                surface["matched"] = int(match.group(1))
                surface["compared"] = int(match.group(2))
                continue
        if not current:
            continue
        for regex, status in ((_MISMATCH, "mismatch"), (_NEW, "new"), (_ORPHAN, "orphaned")):
            found = regex.match(line)
            if found:
                rel = found.group(1).replace("\\", "/")
                result["surfaces"][current]["frames"].append({
                    "surface": current, "path": rel, "status": status,
                })
                result["surfaces"][current]["differing"] += 1
                break
    return result


def _step_map(steps):
    return {step.get("name"): step for step in steps if step.get("name")}


def build_manifest(gate, gate_exit_code, gate_timed_out, started, ended, git_info,
                   host_info, steps, parsed, shim_present, source="live",
                   source_details=None, output_ignored=None):
    expected_surfaces = _expected_surfaces(gate, source_details)
    unmeasured_surfaces = [
        name for name, data in parsed.get("surfaces", {}).items()
        if _measurement_state(name, data, expected_surfaces) == "unmeasured"
    ]
    has_step_timeout = any(step.get("outcome") == "timeout" for step in steps)
    has_recording_error = any(step.get("outcome") == "recording-error" for step in steps)
    if gate_timed_out or has_step_timeout:
        outcome = "timeout"
    elif unmeasured_surfaces:
        outcome = "unmeasured"
    elif gate_exit_code == 0:
        outcome = "passed"
    else:
        outcome = "failed"
    manifest = {
        "schemaVersion": SCHEMA_VERSION,
        "gate": gate,
        "source": source,
        "exitCode": gate_exit_code,
        "outcome": outcome,
        "utcStart": iso_utc(started),
        "utcEnd": iso_utc(ended),
        "gitSha": git_info.get("sha"),
        "gitShortSha": git_info.get("shortSha"),
        "dirtyTree": bool(git_info.get("dirty")),
        "host": host_info,
        "effekseerShimPresent": bool(shim_present),
        "gateProcessTimedOut": bool(gate_timed_out),
        "steps": steps,
        "frameCounts": {},
        "recording": {
            "hadTraceParseError": has_recording_error,
            "outputIgnoredByGit": output_ignored,
        },
    }
    if source_details:
        manifest["sourceDetails"] = source_details
    for surface, data in parsed.get("surfaces", {}).items():
        manifest["frameCounts"][surface] = {
            "matched": data.get("matched"),
            "compared": data.get("compared"),
            "differing": data.get("differing", 0),
            "measurement": _measurement_state(surface, data, expected_surfaces),
        }
    if gate == "g5":
        by_name = _step_map(steps)
        crop = by_name.get("surface-crop-check")
        manifest["surfaceCropCheck"] = {
            "outcome": crop.get("outcome") if crop else "not-run",
            "exitCode": crop.get("exitCode") if crop else None,
        }
    return manifest


def _surface_config(gate, surface):
    if gate == "g5":
        return G5_SURFACES[surface]
    return G6_SURFACE[surface]


def _record_frame_dir(frames_root, surface, rel_path):
    stem = rel_path[:-4] if rel_path.lower().endswith(".png") else rel_path
    readable = re.sub(r"[^A-Za-z0-9._-]+", "-", stem.replace("/", "-")).strip("-")
    if len(readable) > 80:
        readable = readable[-80:]
    digest = hashlib.sha1((surface + "\0" + rel_path).encode("utf-8")).hexdigest()[:8]
    name = "%s-%s-%s" % (surface, readable or "frame", digest)
    dest = frames_root / name
    dest.mkdir(parents=True, exist_ok=True)
    return dest


def _write_visual_diff(ref_path, actual_path, dest):
    try:
        from PIL import Image, ImageChops
    except ImportError as exc:
        raise RuntimeError("record.py needs Pillow to write frames/*/diff.png: %s" % exc)

    ref = Image.open(str(ref_path)).convert("RGB") if ref_path and Path(ref_path).exists() else None
    actual = Image.open(str(actual_path)).convert("RGB") if actual_path and Path(actual_path).exists() else None
    if ref is None and actual is None:
        raise RuntimeError("cannot make a diff when neither frame exists")
    width = max(img.width for img in (ref, actual) if img is not None)
    height = max(img.height for img in (ref, actual) if img is not None)

    def canvas(image):
        out = Image.new("RGB", (width, height), (0, 0, 0))
        if image is not None:
            out.paste(image, (0, 0))
        return out

    ImageChops.difference(canvas(ref), canvas(actual)).save(str(dest), format="PNG")


def copy_differing_frames(root, record_dir, gate, parsed, actual_overrides=None):
    actual_overrides = actual_overrides or {}
    frames_root = record_dir / "frames"
    records = []
    for surface, data in parsed.get("surfaces", {}).items():
        cfg = _surface_config(gate, surface)
        ref_root = root / cfg["ref"]
        actual_root = Path(actual_overrides.get(surface, root / cfg["actual"]))
        for frame in data.get("frames", []):
            rel = frame["path"]
            src_ref = ref_root / Path(rel)
            src_actual = actual_root / Path(rel)
            dest = _record_frame_dir(frames_root, surface, rel)
            ref_dest = dest / "reference.png"
            actual_dest = dest / "actual.png"
            if src_ref.exists():
                shutil.copy2(str(src_ref), str(ref_dest))
            if src_actual.exists():
                shutil.copy2(str(src_actual), str(actual_dest))
            if ref_dest.exists() or actual_dest.exists():
                _write_visual_diff(
                    ref_dest if ref_dest.exists() else None,
                    actual_dest if actual_dest.exists() else None,
                    dest / "diff.png",
                )
            records.append({
                "surface": surface,
                "path": rel,
                "status": frame["status"],
                "directory": str(dest.relative_to(record_dir)).replace("\\", "/"),
                "hasReference": ref_dest.exists(),
                "hasActual": actual_dest.exists(),
                "hasDiff": (dest / "diff.png").exists(),
            })
    return records


def _comparison_html(frame_records):
    rows = []
    for frame in frame_records:
        directory = html.escape(frame["directory"])
        label = html.escape("%s / %s" % (frame["surface"], frame["path"]))
        status = html.escape(frame["status"])
        cells = []
        for filename, title, present in (
            ("reference.png", "Reference", frame["hasReference"]),
            ("actual.png", "Actual", frame["hasActual"]),
            ("diff.png", "Diff", frame["hasDiff"]),
        ):
            if present:
                body = '<img src="%s/%s" loading="lazy" alt="%s">' % (directory, filename, title)
            else:
                body = '<div class="missing">Not available</div>'
            cells.append("<figure><figcaption>%s</figcaption>%s</figure>" % (title, body))
        rows.append(
            '<article><header><code>%s</code><b>%s</b></header><div class="triplet">%s</div></article>'
            % (label, status.upper(), "".join(cells))
        )
    if not rows:
        rows.append("<p>No differing frames were reported by this run.</p>")
    return """<!doctype html>
<meta charset="utf-8">
<title>Gate record comparison</title>
<style>
*{box-sizing:border-box}body{margin:0;background:#111827;color:#e5e7eb;font:14px system-ui,sans-serif;padding:20px}
h1{margin-top:0}article{background:#1f2937;border:1px solid #374151;border-radius:8px;padding:12px;margin:0 0 16px}article>header{display:flex;justify-content:space-between;gap:12px;margin-bottom:10px}.triplet{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px}figure{margin:0;background:#030712;padding:6px}figcaption{color:#9ca3af;font-size:12px;margin-bottom:5px}img{display:block;width:100%%}.missing{min-height:160px;display:grid;place-items:center;color:#6b7280}@media(max-width:900px){.triplet{grid-template-columns:1fr}}
</style>
<h1>Gate record comparison</h1>
%s
""" % "\n".join(rows)


def write_comparison(record_dir, frame_records):
    (record_dir / "comparison.html").write_text(_comparison_html(frame_records), encoding="utf-8", newline="\n")


def _completed_step(steps, name):
    for step in steps:
        if step.get("name") == name:
            return step.get("outcome") in ("passed", "failed")
    return False


def copy_source_comparisons(root, record_dir, gate, steps):
    copied = []
    if gate != "g5":
        return copied
    candidates = []
    if _completed_step(steps, "classic-check"):
        candidates.append((G5_SURFACES["classic"]["comparison"], "comparison-source.html"))
    if _completed_step(steps, "wide-check"):
        candidates.append((G5_SURFACES["wide"]["comparison"], "comparison-wide-source.html"))
    for rel, name in candidates:
        source = root / rel
        if source.exists():
            shutil.copy2(str(source), str(record_dir / name))
            copied.append(name)
    return copied


def _load_triage_module(root):
    path = root / "tools/golden/triage.py"
    spec = importlib.util.spec_from_file_location("second_rite_triage_for_record", str(path))
    if spec is None or spec.loader is None:
        raise RuntimeError("could not import %s" % path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _triage_custom(root, gate, parsed, record_dir, actual_overrides=None, source_details=None):
    """Run triage.py's own analysis against only this run's differing actuals.

    The ordinary triage CLI reads the shared *-actual directories, which may
    contain STALE output from an older run. Build a temporary actual tree from
    the frame names emitted by this gate, then point triage.py's existing
    triage_gate() function at that tree. Its compare/classification logic stays
    the single source of truth; record.py only scopes the inputs.
    """
    actual_overrides = actual_overrides or {}
    blocks = ["# Golden gate triage\n"]
    expected_surfaces = _expected_surfaces(gate, source_details)
    unmeasured_surfaces = [
        name for name, data in parsed.get("surfaces", {}).items()
        if _measurement_state(name, data, expected_surfaces) == "unmeasured"
    ]
    measured_surfaces = [
        name for name, data in parsed.get("surfaces", {}).items()
        if _measurement_state(name, data, expected_surfaces) == "measured"
    ]
    any_frames = any(
        surface.get("frames")
        for surface in parsed.get("surfaces", {}).values()
    )
    if not any_frames:
        if unmeasured_surfaces and not measured_surfaces:
            blocks.append(
                "The gate did not compare any frames (measurement: unmeasured) for expected surface%s: %s.\n"
                % ("s" if len(unmeasured_surfaces) != 1 else "", ", ".join(unmeasured_surfaces))
            )
            return "\n".join(blocks).rstrip() + "\n"
        if unmeasured_surfaces:
            blocks.append(
                "Expected surface%s not measured (measurement: unmeasured): %s.\n"
                % ("s" if len(unmeasured_surfaces) != 1 else "", ", ".join(unmeasured_surfaces))
            )
        blocks.append("No differing frames were reported by the gate.\n")
        return "\n".join(blocks).rstrip() + "\n"
    try:
        triage = _load_triage_module(root)
    except (Exception, SystemExit) as exc:
        return "# Golden gate triage\n\ntriage.py could not be loaded: %s\n" % exc

    # Staged inside record_dir rather than the system temp: triage.GATES holds
    # paths relative to the repository root, and on Windows os.path.relpath
    # raises when the two sides sit on different drives. A repo with its
    # checkout on D: and TEMP on C: is an ordinary setup, so the system temp
    # cannot be used here. record_dir is already under the gitignored record
    # root, so this scratch never reaches git.
    Path(record_dir).mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="triage-", dir=str(record_dir)) as temp_name:
        temp_root = Path(temp_name)
        for surface, data in parsed.get("surfaces", {}).items():
            frames_with_actual = [frame for frame in data.get("frames", []) if frame.get("status") != "orphaned"]
            orphaned = [frame for frame in data.get("frames", []) if frame.get("status") == "orphaned"]
            if not frames_with_actual and not orphaned:
                continue
            cfg = _surface_config(gate, surface)
            ref_root = root / cfg["ref"]
            source_actual_root = Path(actual_overrides.get(surface, root / cfg["actual"]))
            actual_root = temp_root / surface
            for frame in frames_with_actual:
                src = source_actual_root / Path(frame["path"])
                if src.exists():
                    dst = actual_root / Path(frame["path"])
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(str(src), str(dst))

            blocks.append("## %s\n" % surface)
            if frames_with_actual and actual_root.exists():
                key = "record-%s" % surface
                triage.GATES[key] = (
                    "%s %s record" % (gate.upper(), surface),
                    os.path.relpath(str(ref_root), str(root)).replace("\\", "/"),
                    os.path.relpath(str(actual_root), str(root)).replace("\\", "/"),
                )
                capture = io.StringIO()
                with contextlib.redirect_stdout(capture):
                    triage.triage_gate(key, False)
                blocks.append(capture.getvalue().rstrip() + "\n")
            for frame in orphaned:
                blocks.append("- `ORPHANED` `%s`: no actual frame exists to measure.\n" % frame["path"])
    return "\n".join(blocks).rstrip() + "\n"


def _copy_raw_captures(raw_dir, record_dir):
    copied = []
    raw_dir = Path(raw_dir)
    if not raw_dir.exists():
        return copied
    destination = record_dir / "captures"
    for source in sorted(raw_dir.glob("*.txt")):
        destination.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(source), str(destination / source.name))
        copied.append("captures/" + source.name)
    return copied


def _gate_script(root, gate):
    return root / "tools/golden" / ("check-screens.ps1" if gate == "g5" else "check-editor.ps1")


def _run_live_gate(root, gate, step_timeout, gate_timeout):
    started = utc_now()
    git_info = git_state(root)
    host_info = host_state()
    shim_present = (root / "effekseer_shim.dll").is_file()
    with tempfile.TemporaryDirectory(prefix="gate-record-") as temp_name:
        temp = Path(temp_name)
        shim_dir = temp / "shims"
        shim_dir.mkdir()
        trace = temp / "steps.jsonl"
        raw_dir = temp / "raw"
        _make_shims(shim_dir)

        powershell = _powershell_executable()
        env = os.environ.copy()
        env.update({
            "SECOND_RITE_RECORD_ROOT": str(root),
            "SECOND_RITE_RECORD_TRACE": str(trace),
            "SECOND_RITE_RECORD_RAW": str(raw_dir),
            "SECOND_RITE_RECORD_STEP_TIMEOUT": str(step_timeout),
            "SECOND_RITE_RECORD_REAL_PYTHON": sys.executable,
            "SECOND_RITE_RECORD_REAL_LOVEC": shutil.which("lovec") or "",
            "SECOND_RITE_RECORD_SCRIPT": str(Path(__file__).resolve()),
        })
        env["PATH"] = str(shim_dir) + os.pathsep + env.get("PATH", "")

        if powershell:
            command = [powershell, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(_gate_script(root, gate))]
            gate_exit, stdout, stderr, gate_timed_out = _run_with_timeout(
                command, root, env, gate_timeout,
            )
        else:
            gate_exit = UNAVAILABLE_EXIT_CODE
            gate_timed_out = False
            stdout = b""
            stderr = b"record.py: PowerShell is unavailable; cannot run the Windows golden gate.\n"

        ended = utc_now()
        steps = load_step_trace(trace)
        parsed = parse_gate_output(gate, _decode_for_parse(stdout))
        bundle = {
            "started": started,
            "ended": ended,
            "git": git_info,
            "host": host_info,
            "shimPresent": shim_present,
            "exitCode": gate_exit,
            "gateTimedOut": gate_timed_out,
            "stdout": stdout,
            "stderr": stderr,
            "steps": steps,
            "parsed": parsed,
            "rawDir": temp / "raw-copy",
        }
        if raw_dir.exists():
            shutil.copytree(str(raw_dir), str(bundle["rawDir"]))
        # The TemporaryDirectory disappears when this function returns, so keep
        # raw capture bytes in memory too for the caller's record assembly.
        bundle["rawCaptures"] = {
            path.name: path.read_bytes() for path in raw_dir.glob("*.txt")
        } if raw_dir.exists() else {}
        return bundle


def _write_bundle(root, gate, bundle, output_root, source="live", source_details=None,
                  actual_overrides=None, source_comparisons=True):
    ignored = ensure_output_is_local_evidence(root, output_root)
    record_dir = _safe_record_dir(output_root, bundle["started"], gate, bundle["git"]["shortSha"])
    (record_dir / "stdout.txt").write_bytes(bundle["stdout"])
    (record_dir / "stderr.txt").write_bytes(bundle["stderr"])

    raw_captures = bundle.get("rawCaptures", {})
    if raw_captures:
        capture_dir = record_dir / "captures"
        capture_dir.mkdir()
        for name, data in sorted(raw_captures.items()):
            (capture_dir / name).write_bytes(data)

    frame_records = copy_differing_frames(root, record_dir, gate, bundle["parsed"], actual_overrides)
    write_comparison(record_dir, frame_records)
    copied_source_comparisons = copy_source_comparisons(root, record_dir, gate, bundle["steps"]) if source_comparisons else []
    triage = _triage_custom(
        root, gate, bundle["parsed"], record_dir, actual_overrides,
        source_details=source_details,
    )
    (record_dir / "triage.md").write_text(triage, encoding="utf-8", newline="\n")

    manifest = build_manifest(
        gate, bundle["exitCode"], bundle["gateTimedOut"], bundle["started"], bundle["ended"],
        bundle["git"], bundle["host"], bundle["steps"], bundle["parsed"], bundle["shimPresent"],
        source=source, source_details=source_details, output_ignored=ignored,
    )
    manifest["frames"] = frame_records
    manifest["artifacts"] = {
        "stdout": "stdout.txt",
        "stderr": "stderr.txt",
        "triage": "triage.md",
        "comparison": "comparison.html",
        "sourceComparisons": copied_source_comparisons,
        "captures": sorted("captures/" + name for name in raw_captures),
    }
    (record_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8", newline="\n",
    )
    if ignored is False:
        print("WARNING: %s is not ignored by git in this checkout." % output_root)
    print("Gate record: %s" % record_dir)
    return record_dir, manifest


def _load_screens_module(root):
    path = root / "tools/golden/screens.py"
    spec = importlib.util.spec_from_file_location("second_rite_screens_for_record", str(path))
    if spec is None or spec.loader is None:
        raise RuntimeError("could not import %s" % path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _offline_capture_bundle(root, capture_path, surface):
    started = utc_now()
    screens = _load_screens_module(root)
    with tempfile.TemporaryDirectory(prefix="gate-record-from-capture-") as temp_name:
        temp = Path(temp_name)
        if surface != "classic":
            allowed = screens.select_surface(surface)
        else:
            allowed = None
        ref_dir = Path(screens.REF_DIR)
        screens.ACTUAL_DIR = str(temp / "actual")
        screens.COMPARISON_HTML = str(temp / "comparison.html")
        captures = screens.load_captures(str(capture_path))
        if allowed is not None:
            captures = [capture for capture in captures
                        if screens.safe_relpath(capture["path"]).startswith(allowed)]
            if not captures:
                raise RuntimeError("surface %s matched none of the saved captures" % surface)

        stdout_io = io.StringIO()
        stderr_io = io.StringIO()
        exit_code = 0
        with contextlib.redirect_stdout(stdout_io), contextlib.redirect_stderr(stderr_io):
            try:
                screens.do_check(captures)
            except SystemExit as exc:
                code = exc.code
                if isinstance(code, int):
                    exit_code = code
                elif code is None:
                    exit_code = 0
                else:
                    print(code, file=sys.stderr)
                    exit_code = 1
        ended = utc_now()
        stdout = stdout_io.getvalue().encode("utf-8")
        stderr = stderr_io.getvalue().encode("utf-8")
        parsed = parse_gate_output("g5", _decode_for_parse(stdout))
        if surface == "wide":
            # A replayed wide check prints one G5 summary. parse_gate_output has
            # no live sequence context and calls the first summary classic; move
            # it to the surface the caller explicitly supplied.
            parsed["surfaces"]["wide"] = parsed["surfaces"]["classic"]
            parsed["surfaces"]["classic"] = _empty_surface()
        step_name = "%s-check-from-capture" % surface
        step = {
            "name": step_name,
            "command": "screens.py",
            "args": ["check", "--input", str(capture_path), "--surface", surface],
            "startedAtUtc": iso_utc(started),
            "endedAtUtc": iso_utc(ended),
            "durationSeconds": round((ended - started).total_seconds(), 3),
            "outcome": "passed" if exit_code == 0 else "failed",
            "exitCode": exit_code,
            "wrapperExitCode": exit_code,
        }
        actual_dir = temp / "actual-copy"
        if Path(screens.ACTUAL_DIR).exists():
            shutil.copytree(screens.ACTUAL_DIR, str(actual_dir))
        bundle = {
            "started": started,
            "ended": ended,
            "git": git_state(root),
            "host": host_state(),
            "shimPresent": (root / "effekseer_shim.dll").is_file(),
            "exitCode": exit_code,
            "gateTimedOut": False,
            "stdout": stdout,
            "stderr": stderr,
            "steps": [step],
            "parsed": parsed,
            "rawCaptures": {"%s.txt" % surface: Path(capture_path).read_bytes()},
            "actualBytes": {},
            "actualSurface": surface,
            "refDir": ref_dir,
        }
        if actual_dir.exists():
            for file_path in actual_dir.rglob("*.png"):
                bundle["actualBytes"][str(file_path.relative_to(actual_dir)).replace("\\", "/")] = file_path.read_bytes()
        return bundle


def record_from_capture(root, capture_path, surface, output_root):
    bundle = _offline_capture_bundle(root, capture_path, surface)
    with tempfile.TemporaryDirectory(prefix="gate-record-offline-actual-") as temp_name:
        actual_root = Path(temp_name)
        for rel, data in bundle.pop("actualBytes").items():
            target = actual_root / Path(rel)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        source_details = {
            "kind": "g5-harness-output",
            "surface": surface,
            "partialGate": True,
            "note": "Replays only the saved screenshot comparison; it cannot re-run the live surface-crop invariant or the other render surface.",
        }
        record_dir, manifest = _write_bundle(
            root, "g5", bundle, output_root, source="from-capture",
            source_details=source_details, actual_overrides={surface: actual_root},
            source_comparisons=False,
        )
        return record_dir, manifest


def run_live(root, gate_arg, output_root, step_timeout, gate_timeout):
    gates = ["g5", "g6"] if gate_arg == "all" else [gate_arg]
    results = []
    for gate in gates:
        bundle = _run_live_gate(root, gate, step_timeout, gate_timeout)
        record_dir, manifest = _write_bundle(root, gate, bundle, output_root)
        results.append((record_dir, manifest))
    for _, manifest in results:
        if manifest["exitCode"] != 0:
            return manifest["exitCode"]
    return 0


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gate", choices=("g5", "g6", "all"), default="all")
    parser.add_argument("--output-root", default=None,
                        help="record root (default: out/gate-records under the repository)")
    parser.add_argument("--step-timeout", type=int, default=DEFAULT_STEP_TIMEOUT,
                        help="seconds allowed for each direct gate subprocess")
    parser.add_argument("--gate-timeout", type=int, default=DEFAULT_GATE_TIMEOUT,
                        help="outer failsafe for one complete check-*.ps1 run")
    parser.add_argument("--from-capture", type=Path,
                        help="offline G5 replay from saved lovec screenshot harness stdout")
    parser.add_argument("--surface", choices=("classic", "wide"), default="classic",
                        help="surface represented by --from-capture")
    subparsers = parser.add_subparsers(dest="internal")
    internal = subparsers.add_parser("_exec-step", help=argparse.SUPPRESS)
    internal.add_argument("--tool", required=True, choices=("python", "lovec"))
    internal.add_argument("args", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    return args


def main(argv=None):
    args = parse_args(argv)
    if args.internal == "_exec-step":
        step_args = list(args.args)
        if step_args and step_args[0] == "--":
            step_args = step_args[1:]
        return exec_step(args.tool, step_args)

    root = repo_root()
    output_root = Path(args.output_root) if args.output_root else root / "out" / "gate-records"
    if not output_root.is_absolute():
        output_root = root / output_root

    if args.step_timeout <= 0 or args.gate_timeout <= 0:
        raise SystemExit("timeouts must be positive seconds")
    if args.from_capture:
        capture = args.from_capture if args.from_capture.is_absolute() else Path.cwd() / args.from_capture
        _, manifest = record_from_capture(root, capture, args.surface, output_root)
        return manifest["exitCode"]
    return run_live(root, args.gate, output_root, args.step_timeout, args.gate_timeout)


if __name__ == "__main__":
    raise SystemExit(main())

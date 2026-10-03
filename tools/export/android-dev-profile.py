#!/usr/bin/env python3
"""Stamp developer-only UI into an exported Second Gate .love archive.

The ordinary Project remains player-facing. The Android *dev* package owns this
profile at export time so a future release APK cannot accidentally inherit
Developer Room / CRT Lab access merely because it also runs on Android.
"""
from __future__ import annotations

import argparse
import json
import os
import tempfile
import zipfile
from pathlib import Path

CURATED_CRT = [
    ("crt", "CRT"),
    ("crt-lab:heavy-beam", "HEAVY BEAM"),
    ("crt-lab:halation", "HALATION"),
    ("crt-lab:aperture", "APERTURE"),
    ("crt-lab:slot-mask", "SLOT MASK"),
    ("crt-lab:composite", "COMPOSITE"),
    ("crt-lab:convergence", "CONVERGENCE"),
]

REQUIRED_JSON = {
    "data/terms.json",
    "data/scenes/title.json",
    "data/scenes/options.json",
    "data/scenes/developer_menu.json",
}


def _lua_table(items: list[tuple[str, str]], column: int) -> str:
    values = [item[column] for item in items]
    if column == 0:
        return "{ " + ", ".join(json.dumps(value) for value in values) + " }"
    return "{ " + ", ".join(
        "[" + json.dumps(mode) + "]=" + json.dumps(label)
        for mode, label in items
    ) + " }"


def crt_init_script() -> str:
    labels = _lua_table(CURATED_CRT, 1)
    return (
        f"local labels = {labels}\n"
        "ctx.sceneState.crtLabMode = api.getOutputPresentation()\n"
        "ctx.sceneState.crtLabLabel = labels[ctx.sceneState.crtLabMode] or "
        "string.upper(tostring(ctx.sceneState.crtLabMode or ''))"
    )


def crt_cycle_script() -> str:
    modes = _lua_table(CURATED_CRT, 0)
    labels = _lua_table(CURATED_CRT, 1)
    return (
        f"local modes = {modes}\n"
        f"local labels = {labels}\n"
        "local current = api.getOutputPresentation()\n"
        "local nextMode = modes[1]\n"
        "for i, id in ipairs(modes) do\n"
        "  if id == current then nextMode = modes[(i % #modes) + 1]; break end\n"
        "end\n"
        "api.setOutputPresentation(nextMode)\n"
        "ctx.sceneState.crtLabMode = api.getOutputPresentation()\n"
        "ctx.sceneState.crtLabLabel = labels[ctx.sceneState.crtLabMode] or "
        "string.upper(tostring(ctx.sceneState.crtLabMode or ''))"
    )


def _window(scene: dict, window_id: str) -> dict:
    for window in scene.get("windows", []):
        if window.get("id") == window_id:
            return window
    raise ValueError(f"scene {scene.get('id')} is missing window {window_id}")


def _list_block(scene: dict, window_id: str, list_id: str) -> dict:
    for block in _window(scene, window_id).get("content", []):
        if block.get("listId") == list_id:
            return block
    raise ValueError(f"scene {scene.get('id')} is missing list block {list_id}")


def _hook(scene: dict, name: str) -> list[dict]:
    hooks = scene.setdefault("hooks", {})
    if name not in hooks or not isinstance(hooks[name], list):
        raise ValueError(f"scene {scene.get('id')} is missing hook {name}")
    return hooks[name]


def _select_handler(hook: list[dict], index: int) -> dict | None:
    needle = f"sceneState.idx == {index}"
    for command in hook:
        if command.get("cmd") == "IF" and needle in str(command.get("condition", "")):
            return command
    return None


def _insert_before_id(rows: list[dict], before_id: str, row: dict) -> None:
    if any(existing.get("id") == row.get("id") for existing in rows):
        return
    for i, existing in enumerate(rows):
        if existing.get("id") == before_id:
            rows.insert(i, row)
            return
    raise ValueError(f"could not insert {row.get('id')} before missing {before_id}")


def patch_title(scene: dict, terms: dict) -> None:
    options = terms.setdefault("title", {}).setdefault("options", [])
    if "Developer Room" not in options:
        if len(options) != 4:
            raise ValueError(f"unexpected title option count before developer stamp: {len(options)}")
        options.append("Developer Room")

    found = False
    for command in _hook(scene, "on_down"):
        condition = str(command.get("condition", ""))
        if "sceneState.idx <" in condition:
            if "session.developerMode" in condition:
                command["condition"] = "sceneState.loadPickerOpen ~= true and sceneState.idx < 5"
            elif "sceneState.idx < 5" not in condition:
                raise ValueError(f"unexpected title on_down condition: {condition}")
            found = True
            break
    if not found:
        raise ValueError("title scene has no navigational on_down bound")

    if _select_handler(_hook(scene, "on_select"), 5) is None:
        raise ValueError("title scene has no authored Developer Room handler at index 5")


def _ensure_crt_format(block: dict, *, output_row: bool) -> None:
    fmt = block.get("formatRight")
    if not isinstance(fmt, str) or not fmt.startswith("{") or not fmt.endswith("}"):
        raise ValueError("CRT developer row requires a formula-backed formatRight")
    if output_row:
        old = "id == 'output' and (sceneState.output == 'crt' and 'CRT' or 'NEAREST')"
        new = (
            "id == 'output' and (sceneState.output == 'crt' and 'CRT' or "
            "sceneState.output ~= 'nearest' and 'LAB' or 'NEAREST')"
        )
        if old in fmt:
            fmt = fmt.replace(old, new, 1)
        elif new not in fmt:
            raise ValueError("unexpected Options OUTPUT formatRight expression")
    if "id == 'crt_lab'" not in fmt:
        tail = "or ''}"
        if not fmt.endswith(tail):
            raise ValueError("formatRight no longer ends in the expected fallback")
        fmt = fmt[: -len(tail)] + "or id == 'crt_lab' and (sceneState.crtLabLabel or '') or ''}"
    block["formatRight"] = fmt


def _append_init_to_script(scene: dict, marker: str) -> None:
    for command in _hook(scene, "on_enter"):
        if command.get("cmd") == "SCRIPT" and "api.getOutputPresentation()" in str(command.get("code", "")):
            code = str(command.get("code", ""))
            if marker not in code:
                command["code"] = code + "\n" + crt_init_script()
            return
    raise ValueError(f"scene {scene.get('id')} has no output-presentation init SCRIPT")


def _crt_select_handler(index: int) -> dict:
    return {
        "cmd": "IF",
        "condition": f"locals._guard == 0 and sceneState.idx == {index}",
        "then": [
            {"cmd": "SET_LOCAL", "name": "_guard", "value": 1},
            {"cmd": "SCRIPT", "code": crt_cycle_script()},
        ],
    }


def patch_options(scene: dict) -> None:
    rows = scene.setdefault("config", {}).setdefault("optionsCommands", [])
    _insert_before_id(rows, "exit", {
        "id": "crt_lab",
        "name": "CRT LAB",
        "help": "Developer build: cycle the curated strong CRT presets live. Curved and maximal experiments stay CLI-only.",
    })
    if len(rows) != 8:
        raise ValueError(f"unexpected Android-dev Options row count: {len(rows)}")

    block = _list_block(scene, "options_list", "config:optionsCommands")
    _ensure_crt_format(block, output_row=True)
    _append_init_to_script(scene, "crtLabLabel")

    nav_down = False
    for command in _hook(scene, "on_down"):
        condition = str(command.get("condition", ""))
        if "sceneState.mode == 'nav'" in condition and "sceneState.idx <" in condition:
            command["condition"] = "sceneState.mode == 'nav' and sceneState.idx < 8"
            nav_down = True
            break
    if not nav_down:
        raise ValueError("Options scene has no nav on_down bound")

    select = _hook(scene, "on_select")
    if _select_handler(select, 7) and _select_handler(select, 8) is None:
        old_exit = _select_handler(select, 7)
        condition = str(old_exit["condition"])
        old_exit["condition"] = condition.replace("sceneState.idx == 7", "sceneState.idx == 8", 1)
    if _select_handler(select, 8) is None:
        raise ValueError("Options EXIT handler did not move to index 8")
    if _select_handler(select, 7) is None:
        exit_pos = select.index(_select_handler(select, 8))
        select.insert(exit_pos, _crt_select_handler(7))


def patch_developer_menu(scene: dict) -> None:
    rows = scene.setdefault("config", {}).setdefault("developerCommands", [])
    _insert_before_id(rows, "title", {
        "id": "crt_lab",
        "name": "CRT LAB",
        "help": "Cycle the curated flat CRT experiments live. Curved and maximal remain explicit CLI-only experiments.",
    })
    if len(rows) != 15:
        raise ValueError(f"unexpected Android-dev Developer row count: {len(rows)}")

    block = _list_block(scene, "developer_list", "config:developerCommands")
    _ensure_crt_format(block, output_row=False)

    # The Developer menu's existing init SCRIPT does not mention output mode.
    # Append a dedicated SCRIPT instead of coupling unrelated presentation state.
    on_enter = _hook(scene, "on_enter")
    if not any(command.get("cmd") == "SCRIPT" and "crtLabLabel" in str(command.get("code", "")) for command in on_enter):
        on_enter.append({"cmd": "SCRIPT", "code": crt_init_script()})

    for command in _hook(scene, "on_down"):
        condition = str(command.get("condition", ""))
        if "sceneState.idx <" in condition:
            command["condition"] = "sceneState.idx < 15"
            break
    else:
        raise ValueError("Developer menu has no on_down bound")

    select = _hook(scene, "on_select")
    title_handler = _select_handler(select, 14)
    if title_handler and _select_handler(select, 15) is None:
        title_handler["condition"] = str(title_handler["condition"]).replace(
            "sceneState.idx == 14", "sceneState.idx == 15", 1)
    if _select_handler(select, 15) is None:
        raise ValueError("Developer TITLE handler did not move to index 15")
    if _select_handler(select, 14) is None:
        title_pos = select.index(_select_handler(select, 15))
        select.insert(title_pos, _crt_select_handler(14))


def patch_documents(docs: dict[str, dict]) -> None:
    patch_title(docs["data/scenes/title.json"], docs["data/terms.json"])
    patch_options(docs["data/scenes/options.json"])
    patch_developer_menu(docs["data/scenes/developer_menu.json"])


def patch_archive(love_path: Path) -> None:
    if not love_path.is_file():
        raise FileNotFoundError(f".love archive does not exist: {love_path}")

    with zipfile.ZipFile(love_path, "r") as source:
        infos = source.infolist()
        names = [info.filename for info in infos]
        duplicates = sorted({name for name in names if names.count(name) > 1})
        if duplicates:
            raise ValueError(f".love archive contains duplicate entries: {duplicates}")
        missing = sorted(REQUIRED_JSON.difference(names))
        if missing:
            raise ValueError(f".love archive is missing developer-profile inputs: {missing}")
        docs = {
            name: json.loads(source.read(name).decode("utf-8"))
            for name in REQUIRED_JSON
        }
        patch_documents(docs)
        replacements = {
            name: (json.dumps(doc, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
            for name, doc in docs.items()
        }

        fd, temp_name = tempfile.mkstemp(prefix=love_path.name + ".", suffix=".tmp", dir=love_path.parent)
        os.close(fd)
        temp_path = Path(temp_name)
        try:
            with zipfile.ZipFile(temp_path, "w") as target:
                for info in infos:
                    payload = replacements.get(info.filename, source.read(info.filename))
                    target.writestr(info, payload)
            os.replace(temp_path, love_path)
        finally:
            if temp_path.exists():
                temp_path.unlink()

    # Re-open the real output and prove the developer rows survived serialization.
    with zipfile.ZipFile(love_path, "r") as result:
        title = json.loads(result.read("data/scenes/title.json"))
        terms = json.loads(result.read("data/terms.json"))
        options = json.loads(result.read("data/scenes/options.json"))
        developer = json.loads(result.read("data/scenes/developer_menu.json"))
    if terms["title"]["options"][-1] != "Developer Room":
        raise AssertionError("developer title option was not stamped")
    if not any(row.get("id") == "crt_lab" for row in options["config"]["optionsCommands"]):
        raise AssertionError("Options CRT LAB row was not stamped")
    if not any(row.get("id") == "crt_lab" for row in developer["config"]["developerCommands"]):
        raise AssertionError("Developer CRT LAB row was not stamped")
    if _select_handler(title["hooks"]["on_select"], 5) is None:
        raise AssertionError("Developer Room title action disappeared")


def self_test() -> None:
    title = {
        "id": "title",
        "hooks": {
            "on_down": [{"cmd": "IF", "condition": "sceneState.loadPickerOpen ~= true and sceneState.idx < (((session and session.developerMode) == true) and 5 or 4)", "then": []}],
            "on_select": [{"cmd": "IF", "condition": "sceneState.loadPickerOpen ~= true and sceneState.idx == 5", "then": []}],
        },
    }
    options = {
        "id": "options",
        "windows": [{"id": "options_list", "content": [{
            "listId": "config:optionsCommands",
            "formatRight": "{id == 'output' and (sceneState.output == 'crt' and 'CRT' or 'NEAREST') or ''}",
        }]}],
        "hooks": {
            "on_enter": [{"cmd": "SCRIPT", "code": "ctx.sceneState.output = api.getOutputPresentation()"}],
            "on_down": [{"cmd": "IF", "condition": "sceneState.mode == 'nav' and sceneState.idx < 7", "then": []}],
            "on_select": [{"cmd": "IF", "condition": "locals._guard == 0 and sceneState.mode == 'nav' and sceneState.idx == 7", "then": []}],
        },
        "config": {"optionsCommands": [
            {"id": "controls"}, {"id": "autoredirect"}, {"id": "aspect"},
            {"id": "output"}, {"id": "display_info"}, {"id": "font"}, {"id": "exit"},
        ]},
    }
    developer = {
        "id": "developer_menu",
        "windows": [{"id": "developer_list", "content": [{
            "listId": "config:developerCommands", "formatRight": "{id == 'fps' and 'OFF' or ''}",
        }]}],
        "hooks": {
            "on_enter": [{"cmd": "SCRIPT", "code": "ctx.sceneState.fps = api.getFpsToggle()"}],
            "on_down": [{"cmd": "IF", "condition": "sceneState.idx < 14", "then": []}],
            "on_select": [{"cmd": "IF", "condition": "locals._guard == 0 and sceneState.idx == 14", "then": []}],
        },
        "config": {"developerCommands": [{"id": f"row{i}"} for i in range(1, 14)] + [{"id": "title"}]},
    }
    terms = {"title": {"options": ["New Game", "Continue", "Options", "Exit"]}}
    docs = {
        "data/scenes/title.json": title,
        "data/scenes/options.json": options,
        "data/scenes/developer_menu.json": developer,
        "data/terms.json": terms,
    }

    with tempfile.TemporaryDirectory() as td:
        love_path = Path(td) / "test.love"
        with zipfile.ZipFile(love_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for name, doc in docs.items():
                archive.writestr(name, json.dumps(doc))
            archive.writestr("main.lua", "return true\n")
        patch_archive(love_path)
        # Idempotence is important for local/manual packaging retries.
        patch_archive(love_path)

    assert len(terms["title"]["options"]) == 4, "self-test source fixture was mutated in-place unexpectedly"
    print("ANDROID DEV PROFILE SELF-TEST OK")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--love", type=Path, help="Exported .love archive to stamp in-place")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
    if args.love:
        patch_archive(args.love)
        print(f"ANDROID DEV PROFILE OK: {args.love}")
    if not args.self_test and not args.love:
        parser.error("provide --love PATH and/or --self-test")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Stamp developer-only UI into an exported Second Gate .love archive.

The ordinary Project remains player-facing. The Android *dev* package owns this
profile at export time so a future release APK cannot accidentally inherit
Developer Room / CRT Lab access merely because it also runs on Android.

Exported players contain the compiled semantic scene bank at data/scenes.json,
not the source-authoring data/scenes/*.json fragments. This adapter therefore
operates on that compiled ownership boundary and validates the finished archive.
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

SCENES_PATH = "data/scenes.json"
TERMS_PATH = "data/terms.json"
RUNTIME_MAIN = "main.lua"
REQUIRED_FILES = {SCENES_PATH, TERMS_PATH, RUNTIME_MAIN}
DEV_MODE_SOURCE = "    session.developerMode = cli.isDeveloperMode\n"
DEV_MODE_STAMP = "    session.developerMode = true -- Android Dev profile\n"


def _lua_modes() -> str:
    return "{ " + ", ".join(json.dumps(mode) for mode, _ in CURATED_CRT) + " }"


def _lua_labels() -> str:
    return "{ " + ", ".join(
        "[" + json.dumps(mode) + "]=" + json.dumps(label)
        for mode, label in CURATED_CRT
    ) + " }"


def crt_init_script() -> str:
    return (
        f"local labels = {_lua_labels()}\n"
        "ctx.sceneState.crtLabMode = api.getOutputPresentation()\n"
        "ctx.sceneState.crtLabLabel = labels[ctx.sceneState.crtLabMode] or "
        "string.upper(tostring(ctx.sceneState.crtLabMode or ''))"
    )


def crt_cycle_script() -> str:
    return (
        f"local modes = {_lua_modes()}\n"
        f"local labels = {_lua_labels()}\n"
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


def patch_runtime_main(source: str) -> str:
    if DEV_MODE_STAMP in source:
        return source
    count = source.count(DEV_MODE_SOURCE)
    if count != 1:
        raise ValueError(f"expected one runtime developer-mode assignment, found {count}")
    return source.replace(DEV_MODE_SOURCE, DEV_MODE_STAMP, 1)


def scene_by_id(scenes: list[dict], scene_id: str) -> dict:
    matches = [scene for scene in scenes if scene.get("id") == scene_id]
    if len(matches) != 1:
        raise ValueError(f"compiled scene bank expected one {scene_id!r}, found {len(matches)}")
    return matches[0]


def _window(scene: dict, window_id: str) -> dict:
    matches = [window for window in scene.get("windows", []) if window.get("id") == window_id]
    if len(matches) != 1:
        raise ValueError(f"scene {scene.get('id')} expected one window {window_id}, found {len(matches)}")
    return matches[0]


def _list_block(scene: dict, window_id: str, list_id: str) -> dict:
    matches = [
        block for block in _window(scene, window_id).get("content", [])
        if block.get("listId") == list_id
    ]
    if len(matches) != 1:
        raise ValueError(f"scene {scene.get('id')} expected one list block {list_id}, found {len(matches)}")
    return matches[0]


def _hook(scene: dict, name: str) -> list[dict]:
    value = scene.get("hooks", {}).get(name)
    if not isinstance(value, list):
        raise ValueError(f"scene {scene.get('id')} is missing hook {name}")
    return value


def _select_handler(hook: list[dict], index: int, *, nav: bool = False) -> dict | None:
    needle = f"sceneState.idx == {index}"
    for command in hook:
        condition = str(command.get("condition", ""))
        if command.get("cmd") != "IF" or needle not in condition:
            continue
        if nav and "sceneState.mode == 'nav'" not in condition:
            continue
        return command
    return None


def _row_index(rows: list[dict], row_id: str) -> int:
    matches = [i for i, row in enumerate(rows, start=1) if row.get("id") == row_id]
    if len(matches) != 1:
        raise ValueError(f"expected one Options row {row_id!r}, found {len(matches)}")
    return matches[0]


def _insert_before_id(rows: list[dict], before_id: str, row: dict) -> bool:
    if any(existing.get("id") == row.get("id") for existing in rows):
        return False
    for index, existing in enumerate(rows):
        if existing.get("id") == before_id:
            rows.insert(index, row)
            return True
    raise ValueError(f"could not insert {row.get('id')} before missing {before_id}")


def _rewrite_idx(command: dict, old_index: int, new_index: int) -> None:
    condition = str(command.get("condition", ""))
    old = f"sceneState.idx == {old_index}"
    new = f"sceneState.idx == {new_index}"
    if old not in condition:
        raise ValueError(f"handler no longer contains expected index {old_index}: {condition}")
    command["condition"] = condition.replace(old, new, 1)


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
        suffix = "or ''}"
        if not fmt.endswith(suffix):
            raise ValueError("formatRight no longer ends in the expected fallback")
        fmt = fmt[:-len(suffix)] + "or id == 'crt_lab' and (sceneState.crtLabLabel or '') or ''}"
    block["formatRight"] = fmt


def _validate_option_rows(rows: list[dict]) -> None:
    ids = [row.get("id") for row in rows]
    if any(not isinstance(row_id, str) for row_id in ids) or len(ids) != len(set(ids)):
        raise ValueError(f"Options rows require unique string ids: {ids}")
    core = {"controls", "autoredirect", "aspect", "output", "display_info", "font", "exit"}
    allowed = core | {"navigation_arrows", "developer_menu", "crt_lab"}
    unknown = sorted(set(ids) - allowed)
    missing = sorted(core - set(ids))
    if unknown or missing:
        raise ValueError(f"unexpected Android-dev Options rows; missing={missing}, unknown={unknown}")
    if ids[-3:] != ["developer_menu", "crt_lab", "exit"]:
        raise ValueError(f"Android developer rows must remain immediately before EXIT: {ids[-3:]}")


def patch_options(scene: dict) -> None:
    rows = scene.setdefault("config", {}).setdefault("optionsCommands", [])
    had_dev = any(row.get("id") == "developer_menu" for row in rows)
    had_crt = any(row.get("id") == "crt_lab" for row in rows)
    _insert_before_id(rows, "exit", {
        "id": "developer_menu",
        "name": "DEVELOPER MENU",
        "help": "Android developer build: open the touch-accessible developer tools menu.",
    })
    _insert_before_id(rows, "exit", {
        "id": "crt_lab",
        "name": "CRT LAB",
        "help": "Developer build: cycle the curated strong CRT presets live. Curved and maximal experiments stay CLI-only.",
    })
    _validate_option_rows(rows)

    block = _list_block(scene, "options_list", "config:optionsCommands")
    _ensure_crt_format(block, output_row=True)

    init_found = False
    for command in _hook(scene, "on_enter"):
        if command.get("cmd") == "SCRIPT" and "api.getOutputPresentation()" in str(command.get("code", "")):
            init_found = True
            if "crtLabLabel" not in str(command.get("code", "")):
                command["code"] = str(command.get("code", "")) + "\n" + crt_init_script()
            break
    if not init_found:
        raise ValueError("Options scene has no output-presentation init SCRIPT")

    row_count = len(rows)
    for command in _hook(scene, "on_down"):
        condition = str(command.get("condition", ""))
        if "sceneState.mode == 'nav'" in condition and "sceneState.idx <" in condition:
            command["condition"] = f"sceneState.mode == 'nav' and sceneState.idx < {row_count}"
            break
    else:
        raise ValueError("Options scene has no nav on_down bound")

    dev_index = _row_index(rows, "developer_menu")
    crt_index = _row_index(rows, "crt_lab")
    exit_index = _row_index(rows, "exit")
    inserted = int(not had_dev) + int(not had_crt)
    old_exit_index = exit_index - inserted

    select = _hook(scene, "on_select")
    exit_handler = _select_handler(select, exit_index, nav=True)
    if exit_handler is None:
        exit_handler = _select_handler(select, old_exit_index, nav=True)
        if exit_handler is None:
            raise ValueError(
                f"Options EXIT handler is missing from nav index {old_exit_index}/{exit_index}"
            )
        _rewrite_idx(exit_handler, old_exit_index, exit_index)

    dev_handlers = [
        command for command in select
        if any(step.get("cmd") == "SCENE_EVENT" and step.get("scene") == "developer_menu"
               for step in command.get("then", []))
    ]
    if len(dev_handlers) > 1:
        raise ValueError("Options has multiple Developer Menu handlers")
    if dev_handlers:
        command = dev_handlers[0]
        if f"sceneState.idx == {dev_index}" not in str(command.get("condition", "")):
            raise ValueError("Options Developer Menu handler is bound to an unexpected row")
    else:
        select.insert(select.index(exit_handler), {
            "cmd": "IF",
            "condition": f"locals._guard == 0 and sceneState.mode == 'nav' and sceneState.idx == {dev_index}",
            "then": [
                {"cmd": "SET_LOCAL", "name": "_guard", "value": 1},
                {"cmd": "SCENE_EVENT", "kind": "push", "scene": "developer_menu"},
            ],
        })

    crt_handlers = [
        command for command in select
        if any(step.get("cmd") == "SCRIPT" and "crtLabMode" in str(step.get("code", ""))
               for step in command.get("then", []))
    ]
    if len(crt_handlers) > 1:
        raise ValueError("Options has multiple CRT Lab handlers")
    if crt_handlers:
        command = crt_handlers[0]
        if f"sceneState.idx == {crt_index}" not in str(command.get("condition", "")):
            raise ValueError("Options CRT Lab handler is bound to an unexpected row")
    else:
        select.insert(select.index(exit_handler), {
            "cmd": "IF",
            "condition": f"locals._guard == 0 and sceneState.mode == 'nav' and sceneState.idx == {crt_index}",
            "then": [
                {"cmd": "SET_LOCAL", "name": "_guard", "value": 1},
                {"cmd": "SCRIPT", "code": crt_cycle_script()},
            ],
        })


def patch_developer_menu(scene: dict) -> None:
    rows = scene.setdefault("config", {}).setdefault("developerCommands", [])
    had_crt = any(row.get("id") == "crt_lab" for row in rows)
    _insert_before_id(rows, "title", {
        "id": "crt_lab",
        "name": "CRT LAB",
        "help": "Cycle the curated flat CRT experiments live. Curved and maximal remain explicit CLI-only experiments.",
    })
    if len(rows) != 15:
        raise ValueError(f"unexpected Android-dev Developer row count: {len(rows)}")

    _ensure_crt_format(_list_block(scene, "developer_list", "config:developerCommands"), output_row=False)
    on_enter = _hook(scene, "on_enter")
    if not any(command.get("cmd") == "SCRIPT" and "crtLabLabel" in str(command.get("code", "")) for command in on_enter):
        on_enter.append({"cmd": "SCRIPT", "code": crt_init_script()})

    for command in _hook(scene, "on_down"):
        if "sceneState.idx <" in str(command.get("condition", "")):
            command["condition"] = f"sceneState.idx < {len(rows)}"
            break
    else:
        raise ValueError("Developer menu has no on_down bound")

    title_index = next((i for i, row in enumerate(rows, start=1) if row.get("id") == "title"), None)
    crt_index = next((i for i, row in enumerate(rows, start=1) if row.get("id") == "crt_lab"), None)
    if title_index is None or crt_index is None:
        raise ValueError("Developer menu is missing TITLE or CRT LAB row")
    old_title_index = title_index - int(not had_crt)

    select = _hook(scene, "on_select")
    title_handler = _select_handler(select, title_index)
    if title_handler is None:
        title_handler = _select_handler(select, old_title_index)
        if title_handler is None:
            raise ValueError(f"Developer TITLE handler is missing from index {old_title_index}/{title_index}")
        _rewrite_idx(title_handler, old_title_index, title_index)

    crt_handlers = [
        command for command in select
        if any(step.get("cmd") == "SCRIPT" and "crtLabMode" in str(step.get("code", ""))
               for step in command.get("then", []))
    ]
    if len(crt_handlers) > 1:
        raise ValueError("Developer menu has multiple CRT Lab handlers")
    if crt_handlers:
        if f"sceneState.idx == {crt_index}" not in str(crt_handlers[0].get("condition", "")):
            raise ValueError("Developer CRT Lab handler is bound to an unexpected row")
    else:
        select.insert(select.index(title_handler), {
            "cmd": "IF",
            "condition": f"locals._guard == 0 and sceneState.idx == {crt_index}",
            "then": [
                {"cmd": "SET_LOCAL", "name": "_guard", "value": 1},
                {"cmd": "SCRIPT", "code": crt_cycle_script()},
            ],
        })


def patch_compiled_data(scenes: list[dict], terms: dict) -> None:
    if not isinstance(scenes, list):
        raise ValueError("data/scenes.json must be the compiled ordered scene collection")
    patch_title(scene_by_id(scenes, "title"), terms)
    patch_options(scene_by_id(scenes, "options"))
    patch_developer_menu(scene_by_id(scenes, "developer_menu"))


def patch_archive(love_path: Path) -> None:
    if not love_path.is_file():
        raise FileNotFoundError(f".love archive does not exist: {love_path}")

    with zipfile.ZipFile(love_path, "r") as source:
        infos = source.infolist()
        names = [info.filename for info in infos]
        if len(names) != len(set(names)):
            raise ValueError(".love archive contains duplicate entries")
        missing = sorted(REQUIRED_FILES.difference(names))
        if missing:
            raise ValueError(f".love archive is missing developer-profile inputs: {missing}")

        scenes = json.loads(source.read(SCENES_PATH).decode("utf-8"))
        terms = json.loads(source.read(TERMS_PATH).decode("utf-8"))
        runtime_main = patch_runtime_main(source.read(RUNTIME_MAIN).decode("utf-8"))
        patch_compiled_data(scenes, terms)
        replacements = {
            SCENES_PATH: (json.dumps(scenes, ensure_ascii=False, indent=2) + "\n").encode("utf-8"),
            TERMS_PATH: (json.dumps(terms, ensure_ascii=False, indent=2) + "\n").encode("utf-8"),
            RUNTIME_MAIN: runtime_main.encode("utf-8"),
        }

        fd, temp_name = tempfile.mkstemp(prefix=love_path.name + ".", suffix=".tmp", dir=love_path.parent)
        os.close(fd)
        temp_path = Path(temp_name)
        try:
            with zipfile.ZipFile(temp_path, "w") as target:
                for info in infos:
                    target.writestr(info, replacements.get(info.filename, source.read(info.filename)))
            os.replace(temp_path, love_path)
        finally:
            if temp_path.exists():
                temp_path.unlink()

    with zipfile.ZipFile(love_path, "r") as result:
        runtime_main = result.read(RUNTIME_MAIN).decode("utf-8")
        scenes = json.loads(result.read(SCENES_PATH))
        terms = json.loads(result.read(TERMS_PATH))
    options = scene_by_id(scenes, "options")
    developer = scene_by_id(scenes, "developer_menu")
    title = scene_by_id(scenes, "title")
    if DEV_MODE_STAMP not in runtime_main:
        raise AssertionError("Android dev runtime does not boot in developer mode")
    if terms["title"]["options"][-1] != "Developer Room":
        raise AssertionError("developer title option was not stamped")
    option_rows = options["config"]["optionsCommands"]
    if not any(row.get("id") == "developer_menu" for row in option_rows):
        raise AssertionError("Options developer-menu row was not stamped")
    if not any(row.get("id") == "crt_lab" for row in option_rows):
        raise AssertionError("Options CRT LAB row was not stamped")
    if not any(row.get("id") == "crt_lab" for row in developer["config"]["developerCommands"]):
        raise AssertionError("Developer CRT LAB row was not stamped")
    if _select_handler(title["hooks"]["on_select"], 5) is None:
        raise AssertionError("Developer Room title action disappeared")
    exit_index = _row_index(option_rows, "exit")
    if _select_handler(options["hooks"]["on_select"], exit_index, nav=True) is None:
        raise AssertionError("Options EXIT action does not follow the stamped row layout")


def _fixture_options(*, navigation_arrows: bool) -> dict:
    rows = [
        {"id": "controls"}, {"id": "autoredirect"}, {"id": "aspect"},
        {"id": "output"}, {"id": "display_info"}, {"id": "font"},
    ]
    on_select = []
    if navigation_arrows:
        rows.append({"id": "navigation_arrows"})
        on_select.append({
            "cmd": "IF",
            "condition": "locals._guard == 0 and sceneState.mode == 'nav' and sceneState.idx == 7",
            "then": [{"cmd": "SCRIPT", "code": "api.setTransitionArrowsVisible(true)"}],
        })
    rows.append({"id": "exit"})
    exit_index = len(rows)
    on_select.append({
        "cmd": "IF",
        "condition": f"locals._guard == 0 and sceneState.mode == 'nav' and sceneState.idx == {exit_index}",
        "then": [{"cmd": "SET_SCENE_STATE", "name": "mode", "value": "'confirm'"}],
    })
    fmt = "{id == 'output' and (sceneState.output == 'crt' and 'CRT' or 'NEAREST')"
    if navigation_arrows:
        fmt += " or id == 'navigation_arrows' and (sceneState.navigationArrows and 'ON' or 'OFF')"
    fmt += " or ''}"
    return {
        "id": "options",
        "windows": [{"id": "options_list", "content": [{
            "listId": "config:optionsCommands", "formatRight": fmt,
        }]}],
        "hooks": {
            "on_enter": [{"cmd": "SCRIPT", "code": "ctx.sceneState.output = api.getOutputPresentation()"}],
            "on_down": [{"cmd": "IF", "condition": f"sceneState.mode == 'nav' and sceneState.idx < {exit_index}", "then": []}],
            "on_select": on_select,
        },
        "config": {"optionsCommands": rows},
    }


def self_test() -> None:
    for navigation_arrows in (False, True):
        title = {
            "id": "title",
            "hooks": {
                "on_down": [{"cmd": "IF", "condition": "sceneState.loadPickerOpen ~= true and sceneState.idx < (((session and session.developerMode) == true) and 5 or 4)", "then": []}],
                "on_select": [{"cmd": "IF", "condition": "sceneState.loadPickerOpen ~= true and sceneState.idx == 5", "then": []}],
            },
        }
        options = _fixture_options(navigation_arrows=navigation_arrows)
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
        runtime_main = "function boot()\n" + DEV_MODE_SOURCE + "end\n"

        with tempfile.TemporaryDirectory() as td:
            love_path = Path(td) / "test.love"
            with zipfile.ZipFile(love_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                archive.writestr(SCENES_PATH, json.dumps([title, options, developer]))
                archive.writestr(TERMS_PATH, json.dumps(terms))
                archive.writestr(RUNTIME_MAIN, runtime_main)
            patch_archive(love_path)
            patch_archive(love_path)

            with zipfile.ZipFile(love_path, "r") as archive:
                stamped_scenes = json.loads(archive.read(SCENES_PATH))
            stamped_options = scene_by_id(stamped_scenes, "options")
            ids = [row["id"] for row in stamped_options["config"]["optionsCommands"]]
            expected_tail = ["developer_menu", "crt_lab", "exit"]
            if ids[-3:] != expected_tail:
                raise AssertionError(f"unexpected stamped Options tail: {ids}")
            if navigation_arrows and ids[-4] != "navigation_arrows":
                raise AssertionError(f"navigation row moved unexpectedly: {ids}")

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

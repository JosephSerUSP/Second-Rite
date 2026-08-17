#!/usr/bin/env python3
"""Stage pale-crossing project, generate preview captures for all maps, and save to artifacts/lab-review/pale-crossing/maps/
"""
import os
import sys
import json
import base64
import subprocess
import shutil
import tempfile
import pathlib

BEGIN = "PREVIEW BEGIN"
END = "PREVIEW END"

LOVEC = r"C:\Program Files\LOVE\lovec.exe"

def stage_project(project_path):
    cmd = [
        "node", "-e",
        "const path=require('path'); const play=require('./tools/editor/project-play'); "
        "const stage=play.stageProject({installRoot:process.cwd(), projectRoot:path.resolve(process.argv[1])}); "
        "console.log(stage);",
        project_path
    ]
    out = subprocess.check_output(cmd, encoding="utf-8").strip()
    return out

def remove_stage(stage_dir):
    cmd = [
        "node", "-e",
        "require('./tools/editor/project-play').removeStage(process.argv[1]);",
        stage_dir
    ]
    subprocess.run(cmd, check=False)

def main():
    project_root = "projects/labs/pale-crossing"
    artifact_dir = pathlib.Path("artifacts/lab-review/pale-crossing/maps")
    artifact_dir.mkdir(parents=True, exist_ok=True)

    print(f"Staging {project_root}...")
    stage_dir = stage_project(project_root)
    print(f"Staged at: {stage_dir}")

    try:
        for map_id in range(1, 9):
            print(f"Generating preview for Map {map_id}...")
            res = subprocess.run(
                [LOVEC, ".", "preview-map", str(map_id)],
                cwd=stage_dir,
                capture_output=True,
                text=True,
                timeout=30,
                encoding="utf-8",
                errors="replace"
            )
            stdout = res.stdout
            if BEGIN not in stdout or END not in stdout:
                print(f"WARN: No PREVIEW payload for map {map_id}. Stderr: {res.stderr[:200]}")
                continue
            
            start = stdout.index(BEGIN) + len(BEGIN)
            end = stdout.index(END)
            payload = json.loads(stdout[start:end].strip())
            
            if payload.get("error"):
                print(f"ERR preview map {map_id}: {payload['error']}")
                continue
            
            image_b64 = payload.get("image")
            if image_b64:
                out_png = artifact_dir / f"{map_id}.png"
                out_png.write_bytes(base64.b64decode(image_b64))
                print(f"OK: Saved {out_png}")
            else:
                print(f"WARN: Map {map_id} returned no image in preview payload")

    finally:
        print("Cleaning up stage...")
        remove_stage(stage_dir)
        print("Done!")

if __name__ == "__main__":
    main()

"""Put one screen's prompt on the clipboard and open its files, for the desktop app.

The ChatGPT Windows app exposes no local port -- no endpoint, no MCP server, no
IPC -- so there is nothing to talk to. Driving it blind with synthetic keystrokes
would type a prompt in and then be unable to read the answer, since the window is
native: no text to extract and no signal that a generation finished.

So this removes the friction instead of the human. The prompt goes on the
clipboard and the folder opens with the two images selected, which makes the
handoff Ctrl+V and a drag.

    python tools/asset-gen/hand_to_chatgpt.py 19            # the layout prompt
    python tools/asset-gen/hand_to_chatgpt.py 19 --look     # no guide
    python tools/asset-gen/hand_to_chatgpt.py --follow-up   # remove the people
"""

from __future__ import annotations

import argparse
import re
import subprocess
from pathlib import Path

GUIDES = Path("out/town-guides")
FOLLOW_UP = "now take the people out, change nothing else"


def brief(map_id):
    text = (GUIDES / "PROMPTS.md").read_text(encoding="utf-8")
    blocks = re.split(r"^## ", text, flags=re.M)
    for block in blocks:
        if block.startswith("%d." % map_id):
            return block
    raise SystemExit("no brief for map %d in %s" % (map_id, GUIDES / "PROMPTS.md"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("map_id", nargs="?", type=int)
    parser.add_argument("--look", action="store_true",
                        help="the prompt without the guide")
    parser.add_argument("--follow-up", action="store_true")
    args = parser.parse_args()

    if args.follow_up:
        prompt, guide = FOLLOW_UP, None
    else:
        if args.map_id is None:
            raise SystemExit("a map id, or --follow-up")
        block = brief(args.map_id)
        prompts = re.findall(r"```\n(.+?)\n```", block, re.S)
        prompt = prompts[1 if args.look else 0].strip()
        found = re.search(r"guide: `([^`]+)`", block)
        guide = GUIDES / found.group(1) if found else None
        print(block.splitlines()[0])

    subprocess.run(["powershell", "-NoProfile", "-Command", "Set-Clipboard"],
                   input=prompt, text=True, check=True)
    print("clipboard:")
    print("  " + prompt)
    if guide and guide.exists():
        style = GUIDES / "00-style-reference.png"
        subprocess.run(["explorer", "/select,", str(guide.resolve())])
        print("\ndrag in this order: %s  then  %s" % (style.name, guide.name))


if __name__ == "__main__":
    main()

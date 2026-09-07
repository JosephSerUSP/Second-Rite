import os
import urllib.request
import json

def main():
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("No GITHUB_TOKEN found, outputting to stdout:")
        print("Re-authored C002 Splitting Pong experiment to use v.time.dt, inline on_enter, semantic collision variables, and added goldenScript metadata.")
        return

    req = urllib.request.Request(
        "https://api.github.com/repos/JosephSerUSP/Second-Rite/pulls",
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github.v3+json",
            "Content-Type": "application/json",
        },
        data=json.dumps({
            "title": "Re-author C002 Splitting Pong benchmark",
            "head": "agent/c002-splitting-pong-reauthor",
            "base": "main",
            "body": "Re-authored C002 Splitting Pong experiment to use v.time.dt, inline on_enter, semantic collision variables, and added goldenScript metadata. Added version 2 report."
        }).encode("utf-8")
    )

    try:
        with urllib.request.urlopen(req) as response:
            print(f"Created PR: {json.loads(response.read().decode())['html_url']}")
    except urllib.error.HTTPError as e:
        print(f"Failed to create PR: {e.code} {e.reason}")
        print(e.read().decode())

if __name__ == "__main__":
    main()

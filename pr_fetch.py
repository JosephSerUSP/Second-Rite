import urllib.request
import json
import sys

def run():
    try:
        url = 'https://api.github.com/repos/JosephSerUSP/Second-Rite/pulls?state=all&per_page=100'

        all_pulls = []
        page = 1
        while True:
            req_url = f"{url}&page={page}"
            req = urllib.request.Request(req_url)
            with urllib.request.urlopen(req) as response:
                pulls = json.loads(response.read())
                if not pulls:
                    break
                all_pulls.extend(pulls)
                page += 1

        result = {}
        # Sort by number ascending, so later ones override earlier ones
        all_pulls.sort(key=lambda x: x['number'])
        for p in all_pulls:
            head_ref = p['head']['ref']
            result[head_ref] = {
                'number': p['number'],
                'state': p['state'],
                'draft': p.get('draft', False)
            }

        with open('prs.json', 'w') as f:
            json.dump(result, f)

    except Exception as e:
        print(f"Error fetching PRs: {e}", file=sys.stderr)
        sys.exit(1)

run()

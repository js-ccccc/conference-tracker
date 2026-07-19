import re
import time
import requests

h = {"User-Agent": "Mozilla/5.0"}
oh = {"User-Agent": "ConferenceTracker/1.0 (mailto:tracker@example.com)"}

# DBLP search Chinese institutions at ACL 2026
for q in ["Tsinghua ACL 2026", "Peking University ACL 2026", "affiliation:Tsinghua"]:
    r = requests.get(
        "https://dblp.org/search/publ/api",
        params={"q": q, "format": "json", "h": 3},
        headers=h,
        timeout=20,
    )
    total = r.json().get("result", {}).get("hits", {}).get("@total", 0)
    print(f"dblp q={q!r} total={total}")

# S2 with API key header optional
url = "https://aclanthology.org/2026.acl-long.1221/"
r = requests.get(url, headers=h, timeout=20)
dois = re.findall(r"10\.\d{4,9}/[^\s\"<>]+", r.text)
print("dois on page", dois[:2])

time.sleep(2)
r = requests.get(
    "https://api.semanticscholar.org/graph/v1/paper/search",
    params={
        "query": "ConfSpec Efficient Step-Level Speculative Reasoning",
        "limit": 1,
        "fields": "title,authors,authors.affiliations,externalIds",
    },
    headers={"User-Agent": "ConferenceTracker/1.0"},
    timeout=20,
)
print("s2", r.status_code)
if r.ok and r.json().get("data"):
    d = r.json()["data"][0]
    print(d.get("title", "")[:60])
    for a in d.get("authors", [])[:3]:
        print(" ", a.get("name"), a.get("affiliations"))

"""Move charts/ai-compare to the latest SUSE Application Collection images, and the
upstream edition to the equivalent community images.

For each image in editions.suse, finds the newest version (and newest build of
it) the Application Collection publishes, then points editions.upstream at the
same version of the community image, checking that tag exists. Only the `tag:`
lines under editions: are rewritten, so comments survive. Re-run
gen-ai-compare-upstream.py afterwards (the workflow does).

Usage (needs PyYAML): python3 scripts/sync-ai-compare-versions.py . [--check] [--summary FILE]
  --check    report only, change nothing (exit 0 either way)
  --summary  write a Markdown table of the changes (for the PR body)

Edit IMAGES/HOLDS below when the chart gains an image or a SUSE build breaks."""
import json, re, sys, urllib.request, urllib.error, yaml

ROOT = sys.argv[1]
CHECK = "--check" in sys.argv
SUMMARY = sys.argv[sys.argv.index("--summary") + 1] if "--summary" in sys.argv else None
VALUES = f"{ROOT}/charts/ai-compare/values.yaml"
APPCO = "https://api.apps.rancher.io/v1/components/"

# editions.<edition>.<key> -> AppCo component, image flavor (None = plain build),
# and where the upstream equivalent lives. upstream "same" = same version number,
# "le" = newest upstream release not newer than the SUSE one (alpine/git lags).
IMAGES = {
    "ollama": dict(component="ollama", flavor="nvidia", upstream=("hub", "ollama/ollama"), match="same"),
    "openWebui": dict(component="open-webui", flavor=None, upstream=("ghcr", "open-webui/open-webui"), match="same"),
    "pipelines": dict(component="open-webui-pipelines", flavor=None, upstream=("ghcr", "open-webui/pipelines"), match="commit"),
    "otelCollector": dict(component="opentelemetry-collector", flavor="contrib", upstream=("hub", "otel/opentelemetry-collector-contrib"), match="same"),
    "curl": dict(component="curl", flavor=None, upstream=("hub", "curlimages/curl"), match="same"),
    "git": dict(component="git", flavor=None, upstream=("hub", "alpine/git"), match="le"),
}

# SUSE builds that are known not to start. The tag stays put until the hold is
# removed; the summary still reports what is available.
HOLDS = {
    "openWebui": ("0.6.41-15.13", "later 0.6.41 builds lack langchain.text_splitter and 0.8.0 builds lack mimeparse (checked 0.6.41-15.24, 0.8.0-15.54)"),
}

# Pipelines has no upstream releases, only commit tags: SUSE version -> the
# commit it was built from. Add an entry when SUSE ships a new pipelines build.
PIPELINES_COMMITS = {
    "0.20250819.030501": "git-039f9c5",
}


def get_json(url, headers=None):
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def vkey(v):
    return tuple(int(x) for x in re.findall(r"\d+", v))


def latest_suse(component, flavor):
    """(version, tag) of the newest container build with the wanted flavor."""
    builds = []
    for br in get_json(APPCO + component)["branches"]:
        for v in br["versions"]:
            ver = v["version_number"]
            pat = re.compile(rf"^{re.escape(ver)}-{re.escape(flavor)}-(\d+(?:\.\d+)*)$" if flavor else rf"^{re.escape(ver)}-(\d+(?:\.\d+)*)$")
            for a in v["artifacts"]:
                if a["packaging_format"] != "CONTAINER":
                    continue
                tag = a["name"].split(":", 1)[1]
                m = pat.match(tag)
                if m:
                    builds.append((vkey(ver), vkey(m.group(1)), ver, tag))
    if not builds:
        raise SystemExit(f"{component}: no {flavor or 'plain'} container build in the Application Collection")
    _, _, ver, tag = max(builds)
    return ver, tag


def upstream_exists(kind, repo, tag):
    try:
        if kind == "hub":
            ns, name = repo.split("/")
            get_json(f"https://hub.docker.com/v2/namespaces/{ns}/repositories/{name}/tags/{tag}")
        else:
            tok = get_json(f"https://ghcr.io/token?scope=repository:{repo}:pull")["token"]
            req = urllib.request.Request(f"https://ghcr.io/v2/{repo}/manifests/{tag}", method="HEAD", headers={
                "Authorization": f"Bearer {tok}",
                "Accept": "application/vnd.oci.image.index.v1+json,application/vnd.docker.distribution.manifest.list.v2+json"})
            urllib.request.urlopen(req, timeout=30)
        return True
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return False
        raise


def upstream_le(repo, version):
    """Newest x.y.z Docker Hub tag of repo that is not newer than version."""
    ns, name = repo.split("/")
    tags = get_json(f"https://hub.docker.com/v2/namespaces/{ns}/repositories/{name}/tags?page_size=100&ordering=last_updated")["results"]
    ok = [t["name"] for t in tags if re.fullmatch(r"\d+\.\d+\.\d+", t["name"]) and vkey(t["name"]) <= vkey(version)]
    return max(ok, key=vkey) if ok else None


def upstream_for(key, cfg, version, current):
    kind, repo = cfg["upstream"]
    if cfg["match"] == "commit":
        tag = PIPELINES_COMMITS.get(version)
        if not tag:
            return current, f"no commit known for SUSE {version}; add it to PIPELINES_COMMITS"
    elif cfg["match"] == "le":
        tag = upstream_le(repo, version)
        if not tag:
            return current, f"no upstream release <= {version}"
        if tag != version:
            return tag, f"newest upstream release is {tag}"
        return tag, ""
    else:
        tag = version
    if not upstream_exists(kind, repo, tag):
        return current, f"{repo}:{tag} not published"
    return tag, ""


def set_tags(text, new):
    """Rewrite editions.<edition>.<key>.tag for each (edition, key) in new."""
    out, edition, key, inside = [], None, None, False
    for line in text.splitlines(keepends=True):
        if re.match(r"^\S", line):
            inside = line.startswith("editions:")
        elif inside:
            if m := re.match(r"^  (\w+):\s*$", line):
                edition, key = m.group(1), None
            elif m := re.match(r"^    (\w+):\s*$", line):
                key = m.group(1)
            elif (m := re.match(r'^(      tag:\s*)(["\']?)[^"\'\s#]*\2(.*)$', line, re.S)) and (edition, key) in new:
                line = f'{m.group(1)}"{new[(edition, key)]}"{m.group(3)}'
        out.append(line)
    return "".join(out)


def main():
    editions = yaml.safe_load(open(VALUES))["editions"]
    new, rows = {}, []
    for key, cfg in IMAGES.items():
        cur_s, cur_u = str(editions["suse"][key]["tag"]), str(editions["upstream"][key]["tag"])
        version, latest = latest_suse(cfg["component"], cfg["flavor"])
        note = ""
        if key in HOLDS:
            tag_s, reason = HOLDS[key]
            note = f"held: {reason}" + (f"; newest is {latest}" if latest != tag_s else "")
            version = re.match(r"^\d+(?:\.\d+)*", tag_s).group(0)
        else:
            tag_s = latest
        tag_u, unote = upstream_for(key, cfg, version, cur_u)
        note = "; ".join(n for n in (note, unote) if n)
        if tag_s != cur_s:
            new[("suse", key)] = tag_s
        if tag_u != cur_u:
            new[("upstream", key)] = tag_u
        rows.append((key, cur_s, tag_s, cur_u, tag_u, note))

    print(f"{'image':14} {'suse':44} {'upstream':28} note")
    for key, cs, ts, cu, tu, note in rows:
        print(f"{key:14} {cs + (' -> ' + ts if ts != cs else ''):44} {cu + (' -> ' + tu if tu != cu else ''):28} {note}")

    if SUMMARY:
        with open(SUMMARY, "w") as f:
            f.write("| Image | SUSE | Upstream | Note |\n|---|---|---|---|\n")
            for key, cs, ts, cu, tu, note in rows:
                arrow = lambda c, t: f"`{c}` → **`{t}`**" if c != t else f"`{c}`"
                f.write(f"| {key} | {arrow(cs, ts)} | {arrow(cu, tu)} | {note} |\n")

    if new and not CHECK:
        with open(VALUES) as f:
            text = f.read()
        with open(VALUES, "w") as f:
            f.write(set_tags(text, new))
    print(f"{len(new)} tag(s) {'would change' if CHECK else 'changed'}")


main()

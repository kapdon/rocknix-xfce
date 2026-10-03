#!/usr/bin/env python3
"""Publish release highlights and retain the full development history in CHANGELOG.md."""
import argparse
from pathlib import Path
import json
import re
import subprocess
from urllib.parse import quote

REPO = "kapdon/rocknix-desktop"
PROJECT = Path(__file__).resolve().parents[1]
CHANGELOG_START = "<!-- development-changelog:start -->"
CHANGELOG_END = "<!-- development-changelog:end -->"
RECORD_SUBJECT = "docs: record development changelog [skip ci]"


def api(endpoint, paginate=False, repository=REPO):
    command = ["gh", "api", f"repos/{repository}/{endpoint}"]
    if paginate:
        command += ["--paginate", "--slurp"]
    return json.loads(subprocess.check_output(command, text=True))


def notes(revision, built_at, repository=REPO):
    latest = api("releases/latest", repository=repository)
    tag = latest["tag_name"]
    comparison = f"{quote(tag, safe='')}...{revision}"
    pages = api(f"compare/{comparison}?per_page=100", paginate=True, repository=repository)
    commits = [commit for page in pages for commit in page["commits"]]
    # GitHub compare returns paginated commits in chronological order.
    if not pages or len(commits) != pages[0]["total_commits"]:
        raise RuntimeError("Incomplete development comparison")
    # Recording a successful build must not add a changelog entry about itself.
    commits = [commit for commit in commits if not (
        commit["commit"]["message"].splitlines()[0] == RECORD_SUBJECT
        and (commit.get("author") or {}).get("login") == "github-actions[bot]")]
    lines = [f"Commit: `{revision}`", f"Built: {built_at}", "",
             "Rolling dev pre-release. The installer selects the latest successful build.", "",
             f"## Changes since {tag}", "",
             "Compared with the latest stable release, not the previous development build.", ""]
    for commit in commits:
        subject = commit["commit"]["message"].splitlines()[0]
        subject = re.sub(r"([\\`*_{}\[\]<>])", r"\\\1", subject)
        lines.append(f"- {subject} ([{commit['sha'][:7]}]({commit['html_url']}))")
    if not commits:
        lines.append("No commits ahead of the latest stable release.")
    lines += ["", f"[Full comparison](https://github.com/{repository}/compare/{comparison})", ""]
    return "\n".join(lines)


def changelog_section(content):
    if content.count(CHANGELOG_START) != 1 or content.count(CHANGELOG_END) != 1:
        raise RuntimeError("CHANGELOG.md must contain exactly one development section")
    before, rest = content.split(CHANGELOG_START)
    if CHANGELOG_END not in rest:
        raise RuntimeError("CHANGELOG.md development markers are out of order")
    section, after = rest.split(CHANGELOG_END)
    return before, section, after


def release_summary(details, changelog, repository=REPO):
    heading = re.search(r"^## Changes since ([^\n]+)$", details, re.MULTILINE)
    if heading is None:
        raise RuntimeError("Development notes are missing the stable release comparison")
    tag = heading.group(1)
    prefix, _, _ = changelog_section(changelog)
    # Highlights are maintained alongside feature changes, outside the generated
    # history. Never reuse an old stable release's highlights after a new release.
    highlights = re.search(r"^## Highlights since " + re.escape(tag) + r"\n+(.*?)(?=^## |\Z)",
                           prefix, re.MULTILINE | re.DOTALL)
    count = len(re.findall(r"^- ", details, re.MULTILINE))
    if not count:
        body = "No commits ahead of the latest stable release."
    elif highlights and highlights.group(1).strip():
        body = highlights.group(1).strip()
    else:
        noun = "commit" if count == 1 else "commits"
        body = f"{count} {noun} since {tag}. See the full changelog for details."
    return (details[:heading.start()] + f"## Highlights since {tag}\n\n" + body
            + f"\n\n[Full changelog](https://github.com/{repository}/blob/dev/CHANGELOG.md)\n")


def render_changelog(content, release_notes):
    before, _, after = changelog_section(content)
    return (before + CHANGELOG_START + "\n\n## Development\n\n"
            + release_notes.rstrip() + "\n\n" + CHANGELOG_END + after)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("revision")
    parser.add_argument("built_at")
    parser.add_argument("--repository", default=REPO)
    parser.add_argument("--changelog", type=Path,
                        help="write the full commit history into a copy of the checked-in changelog")
    args = parser.parse_args()
    if not re.fullmatch(r"[0-9a-f]{40}", args.revision):
        parser.error("revision must be a full commit SHA")
    details = notes(args.revision, args.built_at, args.repository)
    content = (PROJECT / "CHANGELOG.md").read_text()
    summary = release_summary(details, content, args.repository)
    if args.changelog:
        args.changelog.write_text(render_changelog(content, details))
    print(summary, end="")

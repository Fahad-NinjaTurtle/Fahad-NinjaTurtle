#!/usr/bin/env python3
"""Generate light and dark self-contained SVG terminal profile art.

Online: python scripts/generate.py   (GITHUB_TOKEN is recommended/required for GraphQL)
Offline: python scripts/generate.py --offline  (keeps verified cached stats)

Uses Python standard library only. The SVG includes a base64 avatar when available.
"""

from __future__ import annotations

import argparse
import base64
from collections import Counter
from datetime import datetime, timedelta, timezone
from html import escape
import json
import mimetypes
import os
from pathlib import Path
import sys
import urllib.error
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
USER_AGENT = "Fahad-Profile-Terminal-Generator/1.0"
BASE_URL = "https://api.github.com"


def json_file(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def api_get(path: str, token: str | None):
    headers = {"Accept": "application/vnd.github+json", "User-Agent": USER_AGENT,
               "X-GitHub-Api-Version": "2022-11-28"}
    if token:
        headers["Authorization"] = "Bearer " + token
    req = urllib.request.Request(BASE_URL + path, headers=headers)
    with urllib.request.urlopen(req, timeout=25) as reply:
        return json.loads(reply.read())


def api_post_graphql(query: str, variables: dict, token: str):
    body = json.dumps({"query": query, "variables": variables}).encode("utf-8")
    req = urllib.request.Request(BASE_URL + "/graphql", data=body, headers={
        "Accept": "application/vnd.github+json",
        "Content-Type": "application/json",
        "Authorization": "Bearer " + token,
        "User-Agent": USER_AGENT,
    }, method="POST")
    with urllib.request.urlopen(req, timeout=25) as reply:
        payload = json.loads(reply.read())
    if payload.get("errors"):
        raise RuntimeError("GraphQL errors: " + repr(payload["errors"]))
    return payload["data"]


def download_avatar(url: str, token: str | None):
    # Avatar is downloaded as an image and embedded as data URI in BOTH SVGs.
    # No externally linked images are needed by GitHub's SVG sanitizer/proxy.
    req = urllib.request.Request(url.split("?")[0] + "?s=320&v=4", headers={
        "User-Agent": USER_AGENT,
        "Accept": "image/jpeg,image/png,image/webp,image/*",
    })
    with urllib.request.urlopen(req, timeout=25) as reply:
        blob = reply.read(4_000_001)
        mime = reply.headers.get_content_type()
    if len(blob) > 4_000_000 or not mime.startswith("image/"):
        raise ValueError("Avatar response is not a supported image")
    # Store only for easier inspection/debugging; SVGs embed all the pixels.
    suffix = {"image/png": ".png", "image/webp": ".webp"}.get(mime, ".jpg")
    target = ROOT / "assets" / ("github-avatar" + suffix)
    for old in (ROOT / "assets").glob("github-avatar.*"):
        old.unlink()
    target.write_bytes(blob)
    return target


def collect_data(config: dict, stats: dict, token: str | None):
    login = config["username"]
    user = api_get("/users/" + urllib.parse.quote(login), token)
    print("Public GitHub profile:", user.get("html_url"))

    repos = []
    page = 1
    while True:
        batch = api_get("/users/" + urllib.parse.quote(login) +
                        f"/repos?per_page=100&page={page}&type=owner", token)
        repos.extend(batch)
        if len(batch) < 100:
            break
        page += 1

    # public_repos is GitHub's own public-repository count. 'Stars earned'
    # totals stargazers_count on the user's owned public repositories.
    stats["public_repos"] = user["public_repos"]
    stats["stars_earned"] = sum(repo["stargazers_count"] for repo in repos)
    lang_counts = Counter(repo["language"] for repo in repos if repo.get("language"))
    # Counts *primary languages of owned repos*, not GitHub's byte-by-byte share.
    stats["top_languages"] = [lang for lang, _ in lang_counts.most_common(4)]

    if user.get("avatar_url"):
        try:
            path = download_avatar(user["avatar_url"], token)
            print("Avatar saved:", path.relative_to(ROOT))
        except Exception as exc:
            print("WARNING: Avatar download failed (will keep existing avatar):", exc,
                  file=sys.stderr)

    # GitHub GraphQL contribution counts measure the rolling last year,
    # matching the contribution period rather than all-time account history.
    if token:
        try:
            end = datetime.now(timezone.utc)
            beginning = end - timedelta(days=365)
            result = api_post_graphql('''
                query($login: String!, $from: DateTime!, $to: DateTime!) {
                  user(login: $login) {
                    contributionsCollection(from: $from, to: $to) {
                      totalCommitContributions
                      totalPullRequestContributions
                    }
                  }
                }
            ''', {
                "login": login,
                "from": beginning.isoformat(),
                "to": end.isoformat(),
            }, token)
            collection = result["user"]["contributionsCollection"]
            stats["commits_365d"] = collection["totalCommitContributions"]
            stats["prs_365d"] = collection["totalPullRequestContributions"]
        except Exception as exc:
            print("WARNING: GitHub GraphQL is unavailable:", exc, file=sys.stderr)
    else:
        print("WARNING: No GITHUB_TOKEN; contribution counts need a workflow sync.",
              file=sys.stderr)

    # GraphQL failures retain previously verified values, never fabricated ones.
    stats["updated_utc"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    stats.pop("seed_note", None)
    return stats


def get_avatar_data_uri():
    paths = sorted((ROOT / "assets").glob("github-avatar.*"))
    if not paths:
        return None
    p = paths[0]
    mime, _ = mimetypes.guess_type(p.name)
    if mime not in ("image/jpeg", "image/png", "image/webp"):
        return None
    return "data:" + mime + ";base64," + base64.b64encode(p.read_bytes()).decode("ascii")


PALETTES = {
    "dark": {
        "outside": "#070c15", "base": "#101723", "border": "#2a3a50",
        "toolbar": "#172231", "sidebar": "#101e2d", "chip": "#142333",
        "fg": "#eff6ff", "soft": "#c6d3e6", "muted": "#8c9db6",
        "fade": "#34475d", "blue": "#57adff", "orange": "#ffb86c",
        "green": "#55d6a0", "red": "#f77785", "turtle": "#74c7aa",
        "glow": "#23415b", "shadow": "#02040a", "tag": "#8ac6f7",
    },
    "light": {
        "outside": "#eef3fb", "base": "#ffffff", "border": "#c9d7e6",
        "toolbar": "#e9eff8", "sidebar": "#f5f9ff", "chip": "#f0f6ff",
        "fg": "#183149", "soft": "#2f4762", "muted": "#586f86",
        "fade": "#c1cedf", "blue": "#0968c6", "orange": "#bb5706",
        "green": "#087b56", "red": "#b83652", "turtle": "#2d8c79",
        "glow": "#d8edf1", "shadow": "#bdcadb", "tag": "#155f99",
    },
}


def render_svg(mode, config, stats, avatar_uri):
    c = PALETTES[mode]
    parts = []

    def add(t):
        parts.append(t)

    def e(s):
        return escape(str(s), quote=True)

    def txt(x, y, label, size=20, color="fg", weight=400, anchor=None,
            opacity=1, letter_spacing=None):
        attributes = f'x="{x}" y="{y}" font-size="{size}" fill="{c.get(color, color)}" font-weight="{weight}" opacity="{opacity}"'
        if anchor:
            attributes += f' text-anchor="{anchor}"'
        if letter_spacing is not None:
            attributes += f' letter-spacing="{letter_spacing}"'
        add(f'<text {attributes}>{e(label)}</text>')

    add(f'''<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"
      width="1440" height="750" viewBox="0 0 1440 750" role="img"
      aria-label="Fahad GitHub profile terminal, {mode} theme">
      <title>Fahad — developer terminal ({mode})</title>
      <desc>Developer information with live GitHub repository, star, commit and pull request statistics.</desc>
      <defs>
        <clipPath id="avatar-clip"><circle cx="244" cy="218" r="76"/></clipPath>
        <linearGradient id="avatar-glow" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stop-color="{c['blue']}"/><stop offset="1" stop-color="{c['green']}"/>
        </linearGradient>
        <filter id="soft-shadow" x="-20%" y="-20%" width="150%" height="150%">
          <feGaussianBlur stdDeviation="8"/>
        </filter>
      </defs>
      <g font-family="'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace">
        <rect width="1440" height="750" fill="{c['outside']}"/>
        <rect x="34" y="41" width="1372" height="684" rx="19" fill="{c['shadow']}" opacity="0.23" filter="url(#soft-shadow)"/>
        <rect x="26" y="24" width="1388" height="693" rx="18" fill="{c['base']}" stroke="{c['border']}" stroke-width="2"/>
        <path d="M 44 24 H 1396 Q 1414 24 1414 42 V 87 H 26 V 42 Q 26 24 44 24 Z" fill="{c['toolbar']}"/>
        <path d="M 26 87 H 1414" stroke="{c['border']}"/>
        <circle cx="59" cy="56" r="7" fill="#ff6c6b"/><circle cx="83" cy="56" r="7" fill="#ffbe4d"/><circle cx="107" cy="56" r="7" fill="#54c985"/>
        <rect x="141" y="39" width="268" height="35" rx="8" fill="{c['base']}"/>
      ''')
    txt(157, 63, "~/Fahad-NinjaTurtle", 15, "blue", 600)
    txt(1381, 61, "PROFILE // v2.0", 14, "muted", anchor="end", letter_spacing=1)
    # Sidebar panel
    add(f'<rect x="43" y="103" width="422" height="597" rx="14" fill="{c["sidebar"]}"/>')
    add(f'<path d="M 487 118 V 685" stroke="{c["fade"]}" stroke-dasharray="3 8"/>')
    txt(66, 135, "01 / identity", 15, "muted", 600)
    txt(439, 135, "[ online ]", 14, "green", anchor="end")
    add(f'<circle cx="244" cy="218" r="92" fill="none" stroke="{c["glow"]}" stroke-width="13"/>')
    add(f'<circle cx="244" cy="218" r="81" fill="none" stroke="url(#avatar-glow)" stroke-width="5"/>')
    if avatar_uri:
        add(f'<image x="168" y="142" width="152" height="152" preserveAspectRatio="xMidYMid slice" clip-path="url(#avatar-clip)" xlink:href="{e(avatar_uri)}"/>')
    else:
        # Offline-safe vector-only illustration until first authenticated Actions run.
        add(f'<circle cx="244" cy="218" r="76" fill="{c["glow"]}"/>')
        add(f'<g fill="{c["turtle"]}"><circle cx="244" cy="202" r="36"/><path d="M 184 286 Q 184 241 244 241 Q 304 241 304 286 Z"/></g>')
        add(f'<path d="M 209 199 Q 244 190 279 199" stroke="{c["sidebar"]}" stroke-width="12" fill="none"/>')
        add(f'<g fill="{c["sidebar"]}"><circle cx="229" cy="199" r="4"/><circle cx="259" cy="199" r="4"/></g>')
    add(f'<circle cx="308" cy="277" r="11" fill="{c["sidebar"]}"/><circle cx="308" cy="277" r="6" fill="{c["green"]}"/>')
    txt(244, 332, config.get("display_name", "Fahad").upper(), 32, "fg", 700, "middle", letter_spacing=4)
    txt(244, 359, "@" + config["username"], 15, "blue", anchor="middle")
    add(f'<path d="M 100 383 H 388" stroke="{c["border"]}"/>')
    # Turtle-inspired ASCII shell, a vector text design, not a screenshot.
    turtle = [
        "         .-========-.",
        "      .-'  .------.  '-.",
        "    .'   .'  /\\  '.   '.",
        "   /    /  /  \\   \\    \\",
        "  |    |  | () |   |    |",
        "  |    |  |____|   |    |",
        "   \\    \\  '--'  /    /",
        "    '.   '------'   .'",
        "      '-.________.-'",
        "       _/ /    \\ \\_",
        "      /__/      \\__\\",
    ]
    for i, s in enumerate(turtle):
        txt(77, 413 + i * 19, s, 17, "turtle", 500)
    add(f'<path d="M 100 650 H 388" stroke="{c["border"]}"/>')
    txt(244, 671, "> build • ship • repeat", 15, "muted", anchor="middle")
    # Right column info and dotted leaders.
    txt(526, 145, "fahad@github", 21, "blue", 700)
    txt(700, 145, "~", 21, "green", 700)
    add(f'<path d="M 733 139 H 1370" stroke="{c["fade"]}"/>')
    txt(526, 181, "SYSTEM", 14, "blue", 700, letter_spacing=2)

    def row(y, label, value, trim=42):
        txt(526, y, label, 18, "orange", 600)
        start = 540 + len(label) * 11
        add(f'<path d="M {start} {y-6} H 970" stroke="{c["fade"]}" stroke-width="2" stroke-dasharray="2 7"/>')
        value = str(value)
        if len(value) > trim:
            value = value[:trim-1] + "…"
        txt(988, y, value, 18, "fg", 450)

    row(217, "Name:", config.get("display_name", "Fahad"))
    row(251, "Building:", config.get("focus", "Systems, games & apps"))
    row(285, "Organization:", config.get("organization", "Tecshield"))
    row(319, "Based in:", config.get("location", "Lahore, Pakistan"))
    row(353, "GitHub:", "github.com/" + config["username"])

    txt(526, 401, "CONTACT", 14, "blue", 700, letter_spacing=2)
    add(f'<path d="M 627 395 H 1370" stroke="{c["fade"]}"/>')
    site = config.get("portfolio", "").removeprefix("https://").removeprefix("http://").rstrip("/")
    linkedin = config.get("linkedin", "").removeprefix("https://").removeprefix("http://")
    row(437, "Portfolio:", site)
    row(471, "LinkedIn:", linkedin)

    txt(526, 515, "GITHUB STATS / real data", 14, "blue", 700, letter_spacing=2)
    add(f'<path d="M 815 508 H 1370" stroke="{c["fade"]}"/>')

    def fmt(n):
        return format(n, ",") if isinstance(n, int) else "—"

    metrics = [
        ("PUBLIC REPOS", fmt(stats.get("public_repos")), "blue"),
        ("STARS EARNED", fmt(stats.get("stars_earned")), "orange"),
        ("COMMITS / 365D", fmt(stats.get("commits_365d")), "green"),
        ("PRS / 365D", fmt(stats.get("prs_365d")), "red"),
    ]
    for i, (label, val, color) in enumerate(metrics):
        x = 526 + i * 212
        add(f'<rect x="{x}" y="536" width="198" height="95" rx="10" fill="{c["chip"]}" stroke="{c["border"]}"/>')
        add(f'<rect x="{x+15}" y="548" width="27" height="3" rx="1.5" fill="{c[color]}"/>')
        txt(x + 16, 578, label, 13, "muted", 650, letter_spacing=0.3)
        txt(x + 16, 615, val, 29, color, 700)

    langs = stats.get("top_languages") or []
    lang_label = " · ".join(langs[:3]) if langs else "Syncing primary repo languages..."
    txt(526, 672, "LANGUAGES", 13, "orange", 700)
    txt(658, 672, lang_label[:59], 15, "soft")
    updated = stats.get("updated_utc") or "awaiting first sync"
    txt(1370, 696, "Updated: " + updated, 12, "muted", anchor="end")
    add('</g></svg>')
    return "\n".join(parts) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline", action="store_true", help="Generate using cached data, no API calls")
    args = parser.parse_args()
    config = json_file(ROOT / "profile.json")
    stats_path = ROOT / "data" / "stats.json"
    stats = json_file(stats_path)
    if not args.offline:
        token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
        stats = collect_data(config, stats, token)
        stats_path.write_text(json.dumps(stats, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    avatar_uri = get_avatar_data_uri()
    for theme in ("dark", "light"):
        output = ROOT / "assets" / f"terminal-{theme}.svg"
        output.write_text(render_svg(theme, config, stats, avatar_uri), encoding="utf-8")
        print("Generated", output.relative_to(ROOT), "(avatar embedded:", bool(avatar_uri), ")")
    print("Stats:", {key: stats.get(key) for key in (
        "public_repos", "stars_earned", "commits_365d", "prs_365d")})


if __name__ == "__main__":
    main()

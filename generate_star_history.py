#!/usr/bin/env python3
"""Generate GitHub star history charts as static SVGs.

Reads repos from repos.txt (one "owner/repo" per line), fetches star
timestamps via the GitHub API (requires owner/collaborator access since
GitHub's 2026-06 stargazer API restriction), and writes:

  charts/{owner}_{repo}.svg        light theme
  charts/{owner}_{repo}_dark.svg   dark theme
  data/{owner}_{repo}.json         daily cumulative series (timestamps only,
                                   no stargazer identities)

Only the Python standard library is used.
"""

import json
import math
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

API = "https://api.github.com"
ROOT = Path(__file__).resolve().parent

# --- palette (validated for CVD/contrast on both surfaces) ---
THEMES = {
    "light": {
        "surface": "#fcfcfb",
        "series": "#2a78d6",
        "ink": "#0b0b0b",
        "muted": "#898781",
        "grid": "#e1e0d9",
        "baseline": "#c3c2b7",
    },
    "dark": {
        "surface": "#1a1a19",
        "series": "#3987e5",
        "ink": "#ffffff",
        "muted": "#898781",
        "grid": "#2c2c2a",
        "baseline": "#383835",
    },
}

W, H = 840, 420
M_LEFT, M_RIGHT, M_TOP, M_BOTTOM = 64, 40, 64, 44


def gh_get(url: str, token: str):
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github.star+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "star-history-generator",
        },
    )
    with urllib.request.urlopen(req) as res:
        return json.load(res), res.headers.get("Link", "")


def fetch_star_dates(repo: str, token: str) -> list[datetime]:
    dates = []
    page = 1
    while True:
        url = f"{API}/repos/{repo}/stargazers?per_page=100&page={page}"
        try:
            items, link = gh_get(url, token)
        except urllib.error.HTTPError as e:
            if e.code in (401, 403, 404):
                raise SystemExit(
                    f"error: cannot read stargazers of {repo} (HTTP {e.code}). "
                    "The token must belong to an owner/collaborator of the repo "
                    "(fine-grained PAT with Metadata: read)."
                )
            raise
        for item in items:
            dates.append(
                datetime.strptime(item["starred_at"], "%Y-%m-%dT%H:%M:%SZ").replace(
                    tzinfo=timezone.utc
                )
            )
        if 'rel="next"' not in link:
            break
        page += 1
        if page > 400:  # API refuses to paginate past 40k stars
            break
    return sorted(dates)


def daily_cumulative(dates: list[datetime]) -> list[tuple[str, int]]:
    series = []
    count = 0
    for d in dates:
        day = d.strftime("%Y-%m-%d")
        count += 1
        if series and series[-1][0] == day:
            series[-1] = (day, count)
        else:
            series.append((day, count))
    return series


def nice_step(vmax: float, target: int = 4) -> int:
    raw = max(vmax / target, 1)
    mag = 10 ** math.floor(math.log10(raw))
    for m in (1, 2, 5, 10):
        if vmax / (m * mag) <= target:
            return int(m * mag)
    return int(10 * mag)


def fmt_date(ts: float, span_days: float) -> str:
    d = datetime.fromtimestamp(ts, tz=timezone.utc)
    if span_days <= 180:
        return d.strftime("%b %-d")
    if span_days <= 1200:
        return d.strftime("%b %Y")
    return d.strftime("%Y")


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def render_svg(repo: str, dates: list[datetime], now: datetime, theme: dict) -> str:
    plot_w = W - M_LEFT - M_RIGHT
    plot_h = H - M_TOP - M_BOTTOM
    total = len(dates)

    font = 'font-family="system-ui, -apple-system, &quot;Segoe UI&quot;, sans-serif"'
    head = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
        f'viewBox="0 0 {W} {H}" role="img" '
        f'aria-label="Star history of {esc(repo)}: {total} stars">\n'
        f'<rect width="{W}" height="{H}" rx="8" fill="{theme["surface"]}"/>\n'
        f'<text x="{M_LEFT}" y="30" {font} font-size="16" font-weight="600" '
        f'fill="{theme["ink"]}">{esc(repo)}</text>\n'
        f'<text x="{M_LEFT}" y="48" {font} font-size="11" '
        f'fill="{theme["muted"]}">GitHub stars · updated '
        f'{now.strftime("%Y-%m-%d")} UTC</text>\n'
    )

    if total == 0:
        return head + (
            f'<text x="{W / 2}" y="{H / 2}" {font} font-size="13" '
            f'fill="{theme["muted"]}" text-anchor="middle">No stars yet</text>\n</svg>\n'
        )

    t0 = dates[0].timestamp()
    t1 = max(now.timestamp(), t0 + 1)
    span_days = (t1 - t0) / 86400
    step = nice_step(total)
    ymax = max(total * 1.15, step)

    def x(ts: float) -> float:
        return M_LEFT + (ts - t0) / (t1 - t0) * plot_w

    def y(v: float) -> float:
        return M_TOP + plot_h - v / ymax * plot_h

    # horizontal gridlines + y tick labels
    grid = []
    v = 0
    while v <= ymax:
        gy = y(v)
        grid.append(
            f'<line x1="{M_LEFT}" y1="{gy:.1f}" x2="{W - M_RIGHT}" y2="{gy:.1f}" '
            f'stroke="{theme["grid"]}" stroke-width="1"/>'
            f'<text x="{M_LEFT - 8}" y="{gy + 3.5:.1f}" {font} font-size="11" '
            f'fill="{theme["muted"]}" text-anchor="end" '
            f'style="font-variant-numeric: tabular-nums">{v}</text>'
        )
        v += step

    # x tick labels
    xticks = []
    n_xticks = 4 if span_days > 30 else 3
    for i in range(n_xticks + 1):
        ts = t0 + (t1 - t0) * i / n_xticks
        anchor = "start" if i == 0 else ("end" if i == n_xticks else "middle")
        xticks.append(
            f'<text x="{x(ts):.1f}" y="{H - M_BOTTOM + 20}" {font} font-size="11" '
            f'fill="{theme["muted"]}" text-anchor="{anchor}">'
            f"{fmt_date(ts, span_days)}</text>"
        )

    # step-after cumulative line, extended to now
    pts = [(d.timestamp(), i + 1) for i, d in enumerate(dates)]
    path = f"M {x(pts[0][0]):.1f} {y(0):.1f} L {x(pts[0][0]):.1f} {y(1):.1f}"
    for (ts, v_), (prev_ts, prev_v) in zip(pts[1:], pts[:-1]):
        path += f" L {x(ts):.1f} {y(prev_v):.1f} L {x(ts):.1f} {y(v_):.1f}"
    path += f" L {x(t1):.1f} {y(total):.1f}"
    area = path + f" L {x(t1):.1f} {y(0):.1f} Z"

    ex, ey = x(t1), y(total)
    label_anchor = "end"
    label_x = ex - 12
    end = (
        f'<path d="{area}" fill="{theme["series"]}" fill-opacity="0.08" stroke="none"/>\n'
        f'<path d="{path}" fill="none" stroke="{theme["series"]}" stroke-width="2" '
        f'stroke-linejoin="round"/>\n'
        f'<circle cx="{ex:.1f}" cy="{ey:.1f}" r="4" fill="{theme["series"]}" '
        f'stroke="{theme["surface"]}" stroke-width="2"/>\n'
        f'<text x="{label_x:.1f}" y="{ey - 8:.1f}" {font} font-size="13" '
        f'font-weight="600" fill="{theme["ink"]}" text-anchor="{label_anchor}" '
        f'style="font-variant-numeric: tabular-nums">{total}</text>\n'
    )

    baseline = (
        f'<line x1="{M_LEFT}" y1="{y(0):.1f}" x2="{W - M_RIGHT}" y2="{y(0):.1f}" '
        f'stroke="{theme["baseline"]}" stroke-width="1"/>\n'
    )

    return head + "\n".join(grid) + "\n" + baseline + "\n".join(xticks) + "\n" + end + "</svg>\n"


def main() -> None:
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not token:
        raise SystemExit("error: set GH_TOKEN (a PAT of the repo owner)")

    repos = [
        line.strip()
        for line in (ROOT / "repos.txt").read_text().splitlines()
        if line.strip() and not line.startswith("#")
    ]
    if not repos:
        raise SystemExit("error: repos.txt is empty")

    now = datetime.now(timezone.utc)
    (ROOT / "charts").mkdir(exist_ok=True)
    (ROOT / "data").mkdir(exist_ok=True)

    for repo in repos:
        dates = fetch_star_dates(repo, token)
        slug = repo.replace("/", "_")
        for theme_name, theme in THEMES.items():
            suffix = "" if theme_name == "light" else f"_{theme_name}"
            out = ROOT / "charts" / f"{slug}{suffix}.svg"
            out.write_text(render_svg(repo, dates, now, theme))
        (ROOT / "data" / f"{slug}.json").write_text(
            json.dumps(
                {
                    "repo": repo,
                    "updated": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "stars": len(dates),
                    "daily_cumulative": daily_cumulative(dates),
                },
                indent=2,
            )
            + "\n"
        )
        print(f"{repo}: {len(dates)} stars -> charts/{slug}.svg")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Contribution-grid maze snake.
Real contribution cells stay green; empty cells get a randomized-DFS maze whose
walls are green cells. A snake sweeps the grid and eats every green cell.
Usage: GITHUB_TOKEN=... python3 maze_snake.py <user> <outdir>
"""
import json, os, random, sys, urllib.request

W, H, CELL, GAP = 53, 7, 12, 3
STEP = 0.045          # seconds per cell
PAUSE = 2.0           # seconds of empty grid / full grid
SNAKE_LEN = 6

def fetch(user, token):
    q = """query($u:String!){user(login:$u){contributionsCollection{contributionCalendar{
      weeks{contributionDays{weekday contributionLevel}}}}}}"""
    req = urllib.request.Request("https://api.github.com/graphql",
        data=json.dumps({"query": q, "variables": {"u": user}}).encode(),
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json"})
    weeks = json.load(urllib.request.urlopen(req))["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
    lv = {"NONE": 0, "FIRST_QUARTILE": 1, "SECOND_QUARTILE": 2, "THIRD_QUARTILE": 3, "FOURTH_QUARTILE": 4}
    grid = [[None] * H for _ in range(W)]           # None = day outside calendar
    weeks = weeks[-W:]
    off = W - len(weeks)
    for x, w in enumerate(weeks):
        for d in w["contributionDays"]:
            grid[x + off][d["weekday"]] = lv[d["contributionLevel"]]
    return grid

def maze(seed):
    """Wall mask: True = wall. Passages on odd rows/cols, carved by DFS."""
    rnd = random.Random(seed)
    wall = [[True] * H for _ in range(W)]
    start = (1, 1); wall[1][1] = False; stack = [start]
    while stack:
        x, y = stack[-1]
        nb = [(x+dx, y+dy, dx, dy) for dx, dy in ((2,0),(-2,0),(0,2),(0,-2))
              if 0 < x+dx < W-1 and 0 < y+dy < H-1 and wall[x+dx][y+dy]]
        if not nb: stack.pop(); continue
        nx, ny, dx, dy = rnd.choice(nb)
        wall[x+dx//2][y+dy//2] = False; wall[nx][ny] = False
        stack.append((nx, ny))
    # a few extra openings so it reads as a maze, not a solid block
    for _ in range(12):
        x, y = rnd.randrange(1, W-1), rnd.randrange(1, H-1)
        if (x + y) % 2 == 1: wall[x][y] = False
    return wall

def build(grid, wall, pal):
    green = {}   # (x,y) -> level
    for x in range(W):
        for y in range(H):
            v = grid[x][y]
            if v is None: continue
            if v > 0: green[(x, y)] = v
            elif wall[x][y]: green[(x, y)] = 2   # walls: single shade
    # serpentine sweep path (column by column)
    path = [(x, y) for x in range(W) for y in (range(H) if x % 2 == 0 else range(H-1, -1, -1))]
    n = len(path); total = PAUSE + n * STEP + PAUSE
    pct = lambda t: f"{100 * t / total:.3f}%"
    px = lambda i: i * (CELL + GAP)
    css, body = [], []
    css.append(f".c{{rx:2;ry:2;width:{CELL}px;height:{CELL}px}}"
               f".e{{fill:{pal['empty']}}}" + "".join(f".l{k}{{fill:{pal['lv'][k]}}}" for k in range(1, 5)))
    # empty base grid
    for x in range(W):
        for y in range(H):
            if grid[x][y] is not None:
                body.append(f'<rect class="c e" x="{px(x)}" y="{px(y)}"/>')
    # green cells, each vanishes when the head reaches it
    eat_at = {c: PAUSE + i * STEP for i, c in enumerate(path)}
    for i, (c, lv) in enumerate(sorted(green.items(), key=lambda kv: eat_at[kv[0]])):
        t = eat_at[c]
        css.append(f"@keyframes g{i}{{0%,{pct(t)}{{opacity:1}}{pct(t+0.001)},100%{{opacity:0}}}}"
                   f".g{i}{{animation:g{i} {total:.2f}s linear infinite}}")
        body.append(f'<rect class="c l{lv} g{i}" x="{px(c[0])}" y="{px(c[1])}"/>')
    # snake: one keyframes of head positions, segments delayed behind it
    stops = [f"0%{{transform:translate({px(path[0][0])}px,{px(-2)}px);opacity:0}}"]
    for i, (x, y) in enumerate(path):
        stops.append(f"{pct(PAUSE + i*STEP)}{{transform:translate({px(x)}px,{px(y)}px);opacity:1}}")
    stops.append(f"{pct(PAUSE + n*STEP + 0.01)},100%{{transform:translate({px(path[-1][0])}px,{px(H+1)}px);opacity:0}}")
    css.append("@keyframes s{" + "".join(stops) + "}")
    for k in range(SNAKE_LEN):
        sz = CELL - k * 0.8; o = (CELL - sz) / 2
        css.append(f".s{k}{{animation:s {total:.2f}s linear infinite;animation-delay:{k*STEP:.3f}s;animation-fill-mode:backwards;opacity:0}}")
        body.append(f'<g class="s{k}"><rect x="{o:.1f}" y="{o:.1f}" width="{sz:.1f}" height="{sz:.1f}" rx="3" fill="{pal["snake"]}"/></g>')
    w, h = px(W) - GAP, px(H) - GAP
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="-6 -6 {w+12} {h+12}" width="{w+12}" height="{h+12}">'
            f'<style>{"".join(css)}</style>{"".join(body[::-1][:SNAKE_LEN][::-1]) if False else "".join(body)}</svg>')

DARK = {"empty": "#24283b", "lv": {1: "#3d5a2a", 2: "#5c8a3a", 3: "#7fb050", 4: "#9ece6a"}, "snake": "#7aa2f7"}
LIGHT = {"empty": "#ebedf0", "lv": {1: "#9be9a8", 2: "#40c463", 3: "#30a14e", 4: "#216e39"}, "snake": "#3d59a1"}

if __name__ == "__main__":
    user, out = sys.argv[1], sys.argv[2]
    os.makedirs(out, exist_ok=True)
    grid = fetch(user, os.environ["GITHUB_TOKEN"])
    wall = maze(seed=user)
    for name, pal in (("snake.svg", LIGHT), ("snake-dark.svg", DARK)):
        s = build(grid, wall, pal)
        open(os.path.join(out, name), "w").write(s)
        print(name, len(s) // 1024, "KB")

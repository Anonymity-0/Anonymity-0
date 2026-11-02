"""Generate transparent contribution-grid SVGs using only the Python standard library."""
import argparse
import base64
import bisect
from datetime import date
import json
from pathlib import Path

WIDTH, HEIGHT = 900, 200
X0, Y0, PITCH, DOT = 40, 55, 16, 12
LEVEL_NAMES = ['NONE', 'FIRST_QUARTILE', 'SECOND_QUARTILE', 'THIRD_QUARTILE', 'FOURTH_QUARTILE']
THEMES = {
    'light': {'colors': ['#ebedf0', '#9be9a8', '#40c463', '#30a14e', '#216e39'], 'text': '#59636e', 'border': '#1b1f23'},
    'dark': {'colors': ['#161b22', '#0e4429', '#006d32', '#26a641', '#39d353'], 'text': '#9198a1', 'border': '#ffffff'},
}


def load_calendar(path):
    payload = json.loads(Path(path).read_text(encoding='utf-8'))
    if payload.get('errors'):
        raise ValueError('GitHub returned errors; keeping the existing animation.')
    calendar = payload['data']['user']['contributionsCollection']['contributionCalendar']
    weeks = calendar['weeks']
    if not 52 <= len(weeks) <= 54:
        raise ValueError('Unexpected contribution calendar width.')
    cells = []
    for col, week in enumerate(weeks[-53:]):
        for day in week['contributionDays']:
            day_date = date.fromisoformat(day['date'])
            cells.append({'x': col, 'y': (day_date.weekday() + 1) % 7,
                          'date': day['date'], 'count': day['contributionCount'],
                          'level': LEVEL_NAMES.index(day['contributionLevel'])})
    return calendar, cells


def plan_worker(cells, who):
    """Walk adjacent cells, stop to pull each occupied cell, then return home."""
    start = (0, 6) if who == 0 else (52, 6)
    x, y = start
    t = 1.5
    route = [(0., x, y, 0), (t, x, y, 0)]
    harvest = {}
    remaining = {(c['x'], c['y']) for c in cells if c['level'] and (c['x'] <= 26) == (who == 0)}

    def add(dt, nx, ny, pose):
        nonlocal t, x, y
        t += dt
        x, y = nx, ny
        route.append((round(t, 4), x, y, pose))

    def walk(tx, ty):
        nonlocal x, y
        add(.01, x, y, 0)
        while (x, y) != (tx, ty):
            if x != tx:
                add(.065, x + (1 if tx > x else -1), y, 0)
            else:
                add(.065, x, y + (1 if ty > y else -1), 0)

    while remaining:
        target = min(remaining, key=lambda p: (abs(p[0]-x) + abs(p[1]-y), p[0], p[1]))
        walk(*target)
        add(.06, x, y, 1)
        add(.14, x, y, 2)
        add(.14, x, y, 3)
        harvest[target] = round(t, 4)
        add(.12, x, y, 3)
        remaining.remove(target)
    add(.6, x, y, 3 if harvest else 0)
    walk(*start)
    return route, harvest


def prepare(data_path):
    calendar, cells = load_calendar(data_path)
    plans = [plan_worker(cells, who) for who in (0, 1)]
    duration = round(max(plan[0][-1][0] for plan in plans) + 2, 4)
    for route, _ in plans:
        route.append((duration, route[-1][1], route[-1][2], 0))
    return calendar, cells, plans, duration


def state_at(route, t):
    i = max(0, bisect.bisect_right([s[0] for s in route], t) - 1)
    a = route[i]
    b = route[min(i+1, len(route)-1)]
    u = min(1, max(0, (t-a[0]) / (b[0]-a[0]))) if b[0] > a[0] else 0
    return a[1] + (b[1]-a[1])*u, a[2] + (b[2]-a[2])*u, a[3]


def animation(attribute, values, times, duration, discrete=False, kind=None):
    tag = 'animateTransform' if kind else 'animate'
    extra = f' type="{kind}"' if kind else ''
    return (f'<{tag} attributeName="{attribute}"{extra} values="{";".join(map(str, values))}" '
            f'keyTimes="{";".join(f"{t/duration:.7f}" for t in times)}" dur="{duration}s" '
            f'calcMode="{"discrete" if discrete else "linear"}" repeatCount="indefinite"/>')


def svg(prepared, sprites_path, theme='light', at=None, characters=True):
    calendar, cells, plans, duration = prepared
    palette = THEMES[theme]
    colors = palette['colors']
    t = 0 if at is None else at % duration
    harvested = dict(plans[0][1])
    harvested.update(plans[1][1])
    by_position = {(c['x'], c['y']): c for c in cells}
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}" role="img" aria-labelledby="title desc">',
           '<title id="title">乌萨奇和小八的贡献草地</title>',
           f'<desc id="desc">真实 GitHub 贡献日历，共 {calendar["totalContributions"]} 次贡献；两只角色沿格子移动并逐格拔草。</desc>']
    if characters:
        out.append('<defs>')
        for who in (0, 1):
            for pose in range(4):
                encoded = base64.b64encode((Path(sprites_path) / f'{who}-{pose}.png').read_bytes()).decode()
                out.append(f'<image id="s{who}{pose}" width="42" height="56" xlink:href="data:image/png;base64,{encoded}"/>')
        out.append('</defs>')
    out.append(f'<g fill="{palette["text"]}" font-family="PingFang SC, Microsoft YaHei, sans-serif" font-size="10">')
    out.append(f'<text x="{X0}" y="14">过去一年 {calendar["totalContributions"]} 次贡献</text>')
    months = []
    last_month = None
    for c in cells:
        month = c['date'][:7]
        if month != last_month:
            months.append((c['x'], int(c['date'][5:7])))
            last_month = month
    for index, (col, month) in enumerate(months):
        if index and col - months[index-1][0] < 2:
            continue
        out.append(f'<text x="{X0+col*PITCH}" y="38">{month}月</text>')
    for row, text in [(1, '一'), (3, '三'), (5, '五')]:
        out.append(f'<text x="17" y="{Y0+row*PITCH+10}">{text}</text>')
    out.append('</g>')
    for col in range(53):
        for row in range(7):
            c = by_position.get((col, row))
            if c is None:
                continue
            cut = harvested.get((col, row))
            color = colors[c['level']]
            fill = colors[0] if cut is not None and cut <= t < duration-.7 else color
            out.append(f'<rect x="{X0+col*PITCH}" y="{Y0+row*PITCH}" width="{DOT}" height="{DOT}" rx="2" fill="{fill}" stroke="{palette["border"]}" stroke-width="1" stroke-opacity=".06">')
            out.append(f'<title>{c["date"]}：{c["count"]} 次贡献</title>')
            if at is None and cut is not None:
                out.append(animation('fill', [color,color,colors[0],colors[0],color], [0,cut-.001,cut,duration-.7,duration], duration))
            out.append('</rect>')
    out.append(f'<g fill="{palette["text"]}" font-family="PingFang SC, Microsoft YaHei, sans-serif" font-size="10"><text x="739" y="188">少</text><text x="871" y="188">多</text></g>')
    for level, color in enumerate(colors):
        out.append(f'<rect x="{760+level*20}" y="178" width="12" height="12" rx="2" fill="{color}" stroke="{palette["border"]}" stroke-opacity=".06"/>')
    if characters:
        for who, (route, _) in enumerate(plans):
            x,y,pose = state_at(route,t)
            out.append(f'<g transform="translate({X0+x*PITCH+DOT/2:.2f},{Y0+y*PITCH+DOT/2:.2f})">')
            if at is None:
                out.append(animation('transform', [f'{X0+s[1]*PITCH+DOT/2} {Y0+s[2]*PITCH+DOT/2}' for s in route], [s[0] for s in route], duration, kind='translate'))
            for frame in range(4):
                out.append(f'<g opacity="{int(frame==pose)}">')
                if at is None:
                    out.append(animation('opacity', [int(s[3]==frame) for s in route], [s[0] for s in route], duration, True))
                out.append(f'<use xlink:href="#s{who}{frame}" x="-21" y="{-50+who*3}"/></g>')
            out.append('</g>')
    out.append('</svg>')
    return ''.join(out)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--data', type=Path, default=Path(__file__).with_name('contributions.json'))
    parser.add_argument('--sprites', type=Path, default=Path(__file__).with_name('sprites'))
    parser.add_argument('--output', type=Path, default=Path(__file__).parent)
    args = parser.parse_args()
    prepared = prepare(args.data)
    args.output.mkdir(parents=True, exist_ok=True)
    for theme in THEMES:
        (args.output / f'chiikawa-{theme}.svg').write_text(svg(prepared,args.sprites,theme),encoding='utf-8')
    print(json.dumps({'contributions':prepared[0]['totalContributions'], 'active_days':sum(c['level']>0 for c in prepared[1]), 'seconds':prepared[3]}))


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""Regenerate the AT4Engineer weekly dashboard. Usage: python3 build.py [--per-day N]
Sources (all on the box): /workspace/yt/Table data.csv (Studio 28-day export),
/workspace/yt/Totals.csv, /workspace/yt/baseline-90d.md, /workspace/shorts/short*.mp4 (+ r*.log)."""
import csv, glob, os, re, sys, html, datetime as dt
TARGET_PER_DAY = float(sys.argv[sys.argv.index('--per-day')+1]) if '--per-day' in sys.argv else 1.0  # ASSUMED cadence
W='/workspace'; today=dt.date.today()
wk_start=today-dt.timedelta(days=(today.weekday()+1)%7)  # Sunday-start week
e=html.escape
import json
_lu=os.path.join(os.path.dirname(os.path.abspath(__file__)),'live_url.txt')
LIVE_URL=open(_lu).read().strip() if os.path.exists(_lu) else ''
def fmt(n): return f"{int(n):,}"
# --- videos from Studio export
vids=[]
with open(f'{W}/yt/Table data.csv',newline='') as f:
    for r in csv.DictReader(f):
        if r['Content']=='Total': continue
        try: d=dt.datetime.strptime(r['Video publish time'],'%b %d, %Y').date()
        except: d=None
        vids.append(dict(id=r['Content'],t=r['Video title'],d=d,v=int(float(r['Views'] or 0)),dur=int(float(r['Duration'] or 0)),subs=r['Subscribers']))
recent=sorted([v for v in vids if v['d'] and v['d']>=today-dt.timedelta(days=14)],key=lambda v:v['d'],reverse=True)
nodate=[v for v in vids if not v['d']]
top28=sorted(vids,key=lambda v:-v['v'])[:5]
tot=list(csv.DictReader(open(f'{W}/yt/Table data.csv')))[0]
daily=[(r['Date'],int(r['Views'])) for r in csv.DictReader(open(f'{W}/yt/Totals.csv'))]
last7=daily[-7:]; prev7=daily[-14:-7]
s7=sum(v for _,v in last7); p7=sum(v for _,v in prev7)
export_mtime=dt.datetime.fromtimestamp(os.path.getmtime(f'{W}/yt/Totals.csv'))
# --- pipeline: rendered shorts
logs={}
for p in glob.glob(f'{W}/shorts/r*.log'):
    logs[re.sub(r'\D','',os.path.basename(p))]=open(p).read().strip().splitlines()[0]
pipe=[]
for p in sorted(glob.glob(f'{W}/shorts/short*.mp4')):
    n=re.sub(r'\D','',os.path.basename(p)); m=dt.datetime.fromtimestamp(os.path.getmtime(p))
    pipe.append(dict(n=n,mb=os.path.getsize(p)/1e6,when=m,log=logs.get(n,'')))
queued=len(pipe)
covered_days=int(queued//TARGET_PER_DAY) if TARGET_PER_DAY else 0
first=today+dt.timedelta(days=1)
covered_through=first+dt.timedelta(days=covered_days-1)
need_by=covered_through+dt.timedelta(days=1)
ok=covered_days>=7
verdict=("You're covered" if ok else "Partly covered")+f" — {queued} Shorts rendered = {covered_days} days at {TARGET_PER_DAY:g}/day"
verdict2=f"Covered through {covered_through:%a %b %-d}. Need new content by {need_by:%a %b %-d}."
# --- scheduled uploads (YouTube Bot: batch*/upload_results.json + yt/checks.md)
import zoneinfo
ET=zoneinfo.ZoneInfo('America/New_York'); now_et=dt.datetime.now(ET)
sched={}
for p in glob.glob(f'{W}/shorts/batch*/upload_results.json'):
    try:
        for row in json.load(open(p)):
            if len(row)>=5 and row[4]=='ok' and row[3]:
                sched[row[2]]=dict(id=row[2],t=re.sub(r'\s*#\S+','',row[1]).strip(),when=dt.datetime.fromisoformat(row[3].replace('Z','+00:00')).astimezone(ET))
    except Exception: pass
if os.path.exists(f'{W}/yt/checks.md'):
    for m in re.finditer(r'^- \[.\] (\S+) (.+?) \(pub \w+ (\w+ \d+) (\d+)(?::(\d+))? ?([AP]M)\)',open(f'{W}/yt/checks.md').read(),re.M):
        vid,t,md,h,mi,ap=m.groups()
        try: w=dt.datetime.strptime(f'{md} {today.year} {h}:{mi or "00"} {ap}','%b %d %Y %I:%M %p').replace(tzinfo=ET)
        except Exception: continue
        sched.setdefault(vid,dict(id=vid,t=t.strip(),when=w))
upcoming=sorted([v for v in sched.values() if v['when']>now_et],key=lambda v:v['when'])
if upcoming:
    covered_through=upcoming[-1]['when'].date(); covered_days=(covered_through-today).days
    need_by=covered_through+dt.timedelta(days=1); ok=covered_days>=7
    days={v['when'].date() for v in upcoming}
    gaps=[today+dt.timedelta(days=i) for i in range(1,covered_days+1) if today+dt.timedelta(days=i) not in days]
    verdict=("You're covered" if ok else "Partly covered")+f" — {len(upcoming)} Shorts scheduled in YouTube, {covered_days} days of runway"
    verdict2=f"Covered through {covered_through:%a %b %-d}. Need new content by {need_by:%a %b %-d}."+(f" Gaps: {', '.join(f'{d:%a %b %-d}' for d in gaps)}." if gaps else " No gaps.")
sched_rows=''.join(f'<tr><td>{v["when"]:%a %b %-d, %-I:%M %p}</td><td><a href="https://youtu.be/{e(v["id"])}">{e(v["t"])}</a></td><td><span class="pill green">Scheduled</span></td></tr>' for v in upcoming)
# --- render
bars=''.join(f'<div class="bar" title="{d}: {v:,}"><i style="height:{v/max(x for _,x in daily)*100:.0f}%"></i></div>' for d,v in daily)
def rows(vs): return ''.join(f'<tr><td>{v["d"]:%a %b %-d}</td><td><a href="https://youtu.be/{e(v["id"])}">{e(v["t"])}</a></td><td class=n>{fmt(v["v"])}</td></tr>' for v in vs) or '<tr><td colspan=3>None found</td></tr>'
pipe_rows=''.join(f'<tr><td>short{p["n"]}.mp4</td><td>{e(p["log"]) or "—"}</td><td>{p["when"]:%a %-I:%M %p}</td><td><span class="pill amber">Rendered · upload status unknown</span></td></tr>' for p in pipe)
page=f'''<!doctype html><html lang=en><head><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1">
<title>AT4Engineer · Week of {wk_start:%b %-d}</title><style>
:root{{--bg:#0f1115;--card:#181b22;--mut:#9aa3b2;--ok:#2ecc71;--warn:#f5b041;--bad:#e74c3c;--acc:#ff4d4d}}
*{{box-sizing:border-box}}body{{margin:0;font:15px/1.45 system-ui,-apple-system,Segoe UI,Roboto,sans-serif;background:var(--bg);color:#e8ebf0}}
main{{max-width:880px;margin:auto;padding:16px}}h1{{font-size:22px;margin:4px 0}}h2{{font-size:16px;margin:0 0 10px;color:#fff}}
.mut{{color:var(--mut);font-size:13px}}.card{{background:var(--card);border-radius:14px;padding:16px;margin:12px 0}}
.verdict{{border-left:6px solid {"var(--ok)" if ok else "var(--warn)"}}}.verdict b{{font-size:20px;display:block}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px}}.kpi{{background:#11141a;border-radius:10px;padding:12px}}
.kpi b{{font-size:22px;display:block}}table{{width:100%;border-collapse:collapse;font-size:14px}}td{{padding:7px 4px;border-top:1px solid #262a33;vertical-align:top}}
td.n{{text-align:right;white-space:nowrap}}a{{color:#8ab4ff;text-decoration:none}}.pill{{font-size:12px;padding:2px 8px;border-radius:99px;white-space:nowrap}}
.amber{{background:#3a2f12;color:var(--warn)}}.green{{background:#123a22;color:var(--ok)}}.gray{{background:#2a2e36;color:var(--mut)}}
.chart{{display:flex;align-items:flex-end;gap:2px;height:90px}}.bar{{flex:1;height:100%;display:flex;align-items:flex-end}}.bar i{{display:block;width:100%;background:var(--acc);border-radius:2px 2px 0 0}}
ul{{margin:0;padding-left:18px}}li{{margin:4px 0}}.tbl{{overflow-x:auto}}
</style></head><body><main>
<p class=mut>@AT4Engineer · week of {wk_start:%a %b %-d} · generated {dt.datetime.now():%a %b %-d, %-I:%M %p} ET</p>
<div style="display:flex;justify-content:space-between;align-items:center;gap:10px;flex-wrap:wrap"><h1>Your YouTube week</h1><button id=rf onclick="doRefresh()" style="background:var(--acc);color:#fff;border:0;border-radius:10px;padding:10px 16px;font-size:15px;font-weight:600;cursor:pointer">&#x21bb; Refresh</button></div>
<p class=mut style="margin:2px 0 0"><b style="color:#e8ebf0">Last updated {dt.datetime.now():%a %b %-d, %-I:%M %p} ET</b> · <span id=rfmsg>Refresh rebuilds the dashboard on the box, then reloads.</span></p>
<div class="card verdict"><b>{e(verdict)}</b>{e(verdict2)}<p class=mut>Cadence target ({TARGET_PER_DAY:g} Short/day) is an assumption — change with <code>build.py --per-day N</code>. {"Runway counts Shorts YouTube Bot has scheduled in YouTube (from its upload results on the box)." if upcoming else '"Queued" counts finished renders on the box; none are confirmed scheduled in YouTube Studio yet.'}</p></div>
<div class="card"><h2>Week at a glance</h2><div class=grid>
<div class=kpi><span class=mut>Views, last 7 days</span><b>{fmt(s7)}</b><span class=mut>{"+" if s7>=p7 else ""}{(s7-p7)/p7*100:.0f}% vs prior 7</span></div>
<div class=kpi><span class=mut>Views, 28 days</span><b>{fmt(tot["Views"])}</b><span class=mut>+{tot["Subscribers"]} subs</span></div>
<div class=kpi><span class=mut>Published last 14 days</span><b>{len(recent)}</b><span class=mut>videos/streams</span></div>
<div class=kpi><span class=mut>Ready in pipeline</span><b>{queued}</b><span class=mut>Shorts rendered</span></div></div>
<p class=mut style="margin-top:12px">Daily views {daily[0][0]} → {daily[-1][0]} (Studio export pulled {export_mtime:%b %-d %-I:%M %p}; latest days lag)</p><div class=chart>{bars}</div></div>
<div class=card><h2>Published recently</h2><div class=tbl><table>{rows(recent)}</table></div>
{"<p class=mut>No publish date in export (draft / unlisted / scheduled? unknown): "+", ".join(e(v["t"]) for v in nodate)+"</p>" if nodate else ""}</div>
<div class=card><h2>Content runway</h2>{"<h2 style=\"font-size:14px\">Scheduled to publish</h2><div class=tbl><table>"+sched_rows+"</table></div><h2 style=\"font-size:14px;margin-top:14px\">Rendered files (batch 1)</h2>" if upcoming else ""}<div class=tbl><table><tr class=mut><td>File</td><td>Sim result</td><td>Rendered</td><td>Status</td></tr>{pipe_rows}</table></div>
<p class=mut>Formats YouTube Bot's generator supports: race, bounce, bridge, escape, grow, hexagon (physics-sim series). {"" if upcoming else "Scheduled uploads in Studio: <b>unknown</b>."}</p></div>
<div class=card><h2>What your bots did</h2>
<p><span class="pill green">YouTube Bot</span></p><ul>
<li>Built a physics-sim Shorts generator (<code>make_short.py</code>: race, bounce, bridge, escape, grow, hexagon; public-domain melodies on collisions).</li>
<li>Rendered {queued} new Shorts ({pipe[0]["when"]:%a %-I:%M %p} – {pipe[-1]["when"]:%a %-I:%M %p}) with QA frames/contact sheets.</li>
<li>Earlier Sat evening: produced a promo video render (<code>/workspace/promo</code>).</li></ul>
<p style="margin-top:12px"><span class="pill green">Channel Analytics</span></p><ul>
<li>Pulled a 90-day Shorts baseline via the Analytics API: 224,830 Shorts views, 206 subs gained.</li>
<li>Physics-sim is the breakout series: <b>Which ball wins? PT2</b> 27,956 views (121.7% avg viewed), PT3 marble 8,787.</li>
<li>Best days for Shorts: Sat (2,381/day) and Sun (2,348/day). Swipe-away rate and best posting hour aren't in the API (Studio only).</li></ul></div>
<div class=card><h2>Top videos, last 28 days</h2><div class=tbl><table>{"".join(f'<tr><td><a href="https://youtu.be/{e(v["id"])}">{e(v["t"])}</a></td><td class=n>{fmt(v["v"])}</td></tr>' for v in top28)}</table></div></div>
<div class=card><h2>Data gaps</h2><ul class=mut>
{"" if upcoming else "<li>No Studio schedule data: we don't know whether any Shorts are scheduled to publish.</li>"}
<li>No titles/upload status for the {queued} rendered Shorts.</li>
<li>Bot chat transcripts weren't readable; "what bots did" comes from files they left on the box.</li>
<li>No written ideas backlog was found.</li></ul></div>
</main><script>
const LIVE={json.dumps(LIVE_URL)};
function bust(){{location.replace(location.pathname+'?v='+Date.now())}}
async function doRefresh(){{const b=document.getElementById('rf'),m=document.getElementById('rfmsg');b.disabled=true;b.textContent='Refreshing…';
 if(!LIVE){{m.textContent='live refresh offline';return setTimeout(bust,1200)}}
 try{{const c=new AbortController();setTimeout(()=>c.abort(),90000);const r=await fetch(LIVE+'/refresh',{{method:'POST',signal:c.signal}});
  if(r.status==429){{const j=await r.json();m.textContent='Just refreshed — try again in '+j.retry_in+'s (reloading latest)';}}
  else if(!r.ok) throw 0; else m.textContent='Rebuilt — reloading…';
  if(location.hostname.endsWith('github.io')){{location.replace(LIVE+'/?v='+Date.now())}} else bust();
 }}catch(e){{m.textContent='live refresh offline';setTimeout(bust,1500)}}}}
</script></body></html>'''
open(os.path.join(os.path.dirname(os.path.abspath(__file__)),'index.html'),'w').write(page)
print(verdict,'|',verdict2)

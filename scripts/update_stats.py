"""Fetch public-only GitHub data and draw repository-local stats cards.
No third-party Python packages. No private repositories are requested.
"""
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import urlencode
from concurrent.futures import ThreadPoolExecutor
from collections import Counter
from datetime import datetime, timezone
from html import escape
import json, os, xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
USER='Abhijeet38'
BG,FG,MUTED,ACCENT,LINE='#181b19','#f4eedf','#b4bcae','#ff9955','#354139'

def fetch(url):
    headers={'User-Agent':'Abhijeet38-profile-stats','Accept':'application/json'}
    if url.startswith('https://api.github.com/') and os.getenv('GITHUB_TOKEN'):
        headers['Authorization']='Bearer '+os.environ['GITHUB_TOKEN']
    with urlopen(Request(url,headers=headers),timeout=30) as r:
        return json.load(r)

def t(x,y,s,size=18,color=FG,weight=400):
    return f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}" font-weight="{weight}">{escape(str(s))}</text>'

def card(name,body,desc):
    data=f'<svg xmlns="http://www.w3.org/2000/svg" width="460" height="300" viewBox="0 0 460 300" role="img"><title>{escape(desc)}</title><rect x=".5" y=".5" width="459" height="299" rx="14" fill="{BG}" stroke="{LINE}"/><g font-family="Trebuchet MS, DejaVu Sans, sans-serif">{body}</g></svg>'
    ET.fromstring(data)
    return data

def main():
    repos=[]
    page=1
    while True:
        batch=fetch(f'https://api.github.com/users/{USER}/repos?type=owner&per_page=100&page={page}')
        repos.extend(r for r in batch if not r.get('private',True))
        if len(batch)<100:break
        page+=1
    own=[r for r in repos if not r['fork']]
    with ThreadPoolExecutor(max_workers=4) as pool:
        langsets=list(pool.map(lambda r:fetch(r['languages_url']),own))
    langs=Counter()
    for d in langsets:langs.update(d)
    streak=fetch('https://streak-stats.demolab.com/?'+urlencode({'user':USER,'type':'json','timezone':'Asia/Kolkata'}))
    assert all(k in streak for k in ('totalContributions','currentStreak','longestStreak'))
    stamp=datetime.now(timezone.utc).strftime('%d %b %Y')
    data={'updated_utc':datetime.now(timezone.utc).isoformat(),'public_repositories':len(repos),'original_public_repositories':len(own),'stars_original_repositories':sum(r['stargazers_count'] for r in own),'language_bytes':dict(langs.most_common()),'streak':streak}
    head=lambda s:t(24,34,s,12,ACCENT,700)
    b=head('GITHUB / PUBLIC FOOTPRINT')
    b+=t(24,101,len(repos),48,FG,700)+t(25,126,'public repositories',14,MUTED)
    b+=t(250,101,data['stars_original_repositories'],48,FG,700)+t(251,126,'stars on original repos',14,MUTED)
    b+=f'<path d="M24 148H436" stroke="{LINE}"/>'
    b+=t(24,182,'CONTRIBUTION STREAKS',11,ACCENT,700)
    for x,val,lab in [(24,streak['totalContributions'],'Total contributions'),(185,streak['currentStreak']['length'],'Current / days'),(325,streak['longestStreak']['length'],'Longest / days')]:
        b+=t(x,223,val,30,FG,700)+t(x,246,lab,11,MUTED)
    b+=t(24,278,'Refreshed '+stamp+' UTC',11,MUTED)
    stats=card('stats.svg',b,'Public GitHub repositories, stars, total contributions, current and longest streak. Refreshed '+stamp+' UTC.')
    b=head('LANGUAGES / PUBLIC CODE')
    total=sum(langs.values())
    palette=[ACCENT,'#c9d48f','#83ada4','#d3b7a5','#a5a0bc','#a4b3c4']
    top=langs.most_common(5)
    other=total-sum(n for _,n in top)
    if other:top.append(('Other',other))
    x=24
    if total:
        for (name,n),color in zip(top,palette):
            w=412*n/total
            b+=f'<rect x="{x:.3f}" y="57" width="{w:.3f}" height="19" fill="{color}"/>'
            x+=w
        for i,((name,n),color) in enumerate(zip(top,palette)):
            y=109+i*24
            b+=f'<circle cx="29" cy="{y-5}" r="4" fill="{color}"/>'+t(43,y,name,14,FG)+t(365,y,f'{100*n/total:.1f}%',14,MUTED)
    else:b+=t(24,115,'No language data available',17,MUTED)
    b+=t(24,264,'By bytes in owned public, non-fork repositories.',10,MUTED)
    b+=t(24,282,'Not a measure of proficiency. Updated '+stamp+'.',10,MUTED)
    language=card('languages.svg',b,'Language shares by bytes in owned public non-fork repositories. Not a measure of proficiency. Refreshed '+stamp+' UTC.')
    # Write only after every fetch and render succeeds; leave last good cards on failure.
    for filename,value in [('stats.svg',stats),('languages.svg',language)]:
        out=ROOT/'assets'/filename
        tmp=out.with_suffix('.tmp')
        tmp.write_text(value)
        tmp.replace(out)
    (ROOT/'assets'/'stats-data.json').write_text(json.dumps(data,indent=2)+'\n')
    print(json.dumps(data,indent=2))

if __name__=='__main__':main()

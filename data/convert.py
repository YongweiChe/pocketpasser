import csv,re,json,math,glob,os,datetime
HERE=os.path.dirname(os.path.abspath(__file__))
TEAMS={'ARI':'Arizona Cardinals','ATL':'Atlanta Falcons','BAL':'Baltimore Ravens','BUF':'Buffalo Bills','CAR':'Carolina Panthers','CHI':'Chicago Bears','CIN':'Cincinnati Bengals','CLE':'Cleveland Browns','DAL':'Dallas Cowboys','DEN':'Denver Broncos','DET':'Detroit Lions','GB':'Green Bay Packers','HOU':'Houston Texans','IND':'Indianapolis Colts','JAX':'Jacksonville Jaguars','KC':'Kansas City Chiefs','LA':'Los Angeles Rams','LAC':'Los Angeles Chargers','MIA':'Miami Dolphins','MIN':'Minnesota Vikings','NE':'New England Patriots','NO':'New Orleans Saints','NYG':'New York Giants','NYJ':'New York Jets','OAK':'Oakland Raiders','LV':'Las Vegas Raiders','PHI':'Philadelphia Eagles','PIT':'Pittsburgh Steelers','SEA':'Seattle Seahawks','SF':'San Francisco 49ers','TB':'Tampa Bay Buccaneers','TEN':'Tennessee Titans','WAS':'Washington Redskins'}
ROUND={'POST':{18:'Wild Card',19:'Divisional round',20:'Conference championship',21:'Pro Bowl',22:'Super Bowl'}}
W=53.33
def fl(v):
    try: return float(v)
    except: return None
out=[]
order=['2017_MIN_2018011401_4497','2018_KC_2018111900_4120','2019_MIA_2019122910_1072','2018_NO_2018110409_3891','2018_NE_2019020300_3556','2019_BAL_2019102010_1654','2018_GB_2018090912_3564','2019_BAL_2019090803_683','2018_MIA_2018121607_1435','2018_DAL_2018112201_2897','2018_KC_2018101412_2072','2019_ARI_2019092908_631','2018_PHI_2019011301_276','2018_BUF_2018112501_875','2018_HOU_2018121500_1484']
for key in order:
    rows=list(csv.DictReader(open(os.path.join(HERE,'raw',f'{key}.tsv')),delimiter='\t'))
    r0=rows[0];desc=r0['playDescription']
    frames={}
    for r in rows: frames.setdefault(int(r['frame']),[]).append(r)
    ev={}
    for f in sorted(frames):
        for r in frames[f]:
            if r['event'] and r['event'] not in ev: ev[r['event']]=f
    snap=ev.get('ball_snap');fwd=ev.get('pass_forward') or ev.get('pass_shovel')
    arr=ev.get('pass_arrived') or ev.get('pass_outcome_caught') or ev.get('pass_outcome_interception') or ev.get('pass_outcome_incomplete')
    if snap is None or fwd is None or arr is None: print('skip',key,ev.keys());continue
    d=1 if r0['playDirection']=='right' else -1
    # some older clips store orientation rotated 90 deg; measure it against motion direction of fast runners
    import statistics
    _dd=[((fl(r['o'])-fl(r['dir'])+180)%360-180) for r in rows if r['displayName']!='ball' and r['o'] and r['dir'] and (fl(r['s']) or 0)>4.5]
    oFix=round(statistics.median(_dd)/90)*90 if _dd else 0
    ball={int(r['frame']):(fl(r['x']),fl(r['y'])) for r in rows if r['displayName']=='ball'}
    losX=ball[snap][0]
    tx=lambda x,y:(round((W-y) if d>0 else y,2),round((x-losX)*d,2))
    players={}
    for r in rows:
        if r['displayName']=='ball':continue
        players.setdefault(r['nflId'] or r['displayName'],[]).append(r)
    m=re.search(r'([A-Z][a-z]?\.[A-Za-z\'-]+) pass',desc);qbn=m.group(1)
    tm=re.search(r'(?:pass [a-z ]*?(?:to|intended for) )([A-Z][a-z]?\.[A-Za-z\'-]+)',desc);tgt=tm.group(1) if tm else None
    def match(nm,abbr):
        ini,last=abbr.split('.',1);fn,ln=nm.split(' ',1) if ' ' in nm else (nm,'')
        return ln.replace(' ','').lower().startswith(last.replace(' ','').lower()) and fn.lower().startswith(ini.lower())
    T=(fwd-snap)/10;tA=(arr-snap)/10;endF=min(max(frames),arr+12)
    off,de=[],[];qb=None;home=away=offT=defT=None
    for pid,rs in players.items():
        rs.sort(key=lambda r:int(r['frame']))
        pos=rs[0]['position'];nm=rs[0]['displayName'];num=int(float(rs[0]['jerseyNumber'] or 0));team=rs[0]['teamAbbr'];isOff=rs[0]['possessionFlag'].startswith('1')
        if rs[0]['homeTeamFlag'].startswith('1'):home=team
        else:away=team
        if isOff:offT=team
        else:defT=team
        trk=[];ss=0;ss2=0;ori=[]
        for r in rs:
            f=int(r['frame'])
            if f<snap or f>endF or (f-snap)%2:continue
            x,y=tx(fl(r['x']),fl(r['y']));trk+= [round((f-snap)/10,2),x,y]
            if f<=arr:ss=max(ss,fl(r['s']) or 0)
            ss2=max(ss2,fl(r['s']) or 0)
            o=fl(r['o']);o=None if o is None else o-oFix
            if o is None: ori.append(ori[-1] if ori else 90)
            else:
                so,co=math.sin(math.radians(o)),math.cos(math.radians(o))
                gx,gy=(-co,so) if d>0 else (co,-so)
                ori.append(round(math.degrees(math.atan2(gy,gx))))
        if not trk:continue
        p={'num':num,'name':nm,'pos':pos,'f':trk}
        if isOff:
            if pos=='QB' and match(nm,qbn): qb=p;continue
            p['elig']=pos in ('WR','TE','RB','FB','HB');p['speed']=round(min(9.5,max(6.2,ss*1.0)),2)
            if tgt and match(nm,tgt):p['target']=True
            off.append(p)
        else:
            # rusher if he is in the backfield at the throw
            yT=None
            for i in range(0,len(trk),3):
                if trk[i]<=T+.05:yT=trk[i+2]
            p['rush']=pos in ('DE','DT','NT','DL') or (yT is not None and yT<-.5)
            base=8 if pos in ('CB','DB','S','SS','FS') else 7 if 'LB' in pos else 6.2
            p['sprint']=round(min(9.8,max(base,ss2)),2)   # his own top speed on this play if faster than the position norm (yd/s)
            p['react']=.4 if pos in ('CB','DB','S','SS','FS') else .35  # fallback only
            p['o']=ori   # facing angle per frame, game coords (deg, atan2(dy,dx))
            de.append(p)
    bx=ball.get(arr) or ball.get(arr-1);spot=tx(*bx)
    qbT=None
    for i in range(0,len(qb['f']),3):
        if qb['f'][i]<=T+.05:qbT=(qb['f'][i+1],qb['f'][i+2])
    dd=math.hypot(spot[0]-qbT[0],spot[1]-qbT[1]);air=tA-T
    typ='fast' if abs((.05+dd/23)-air)<=abs((.15+dd/18.5)-air) else 'touch'
    kind='int' if 'INTERCEPTED' in desc else 'incomplete' if 'incomplete' in desc.lower() else 'complete'
    gm=re.search(r'for (-?\d+) yards',desc);gain=int(gm.group(1)) if gm else 0
    yac=max(0,gain-round(spot[1])) if kind=='complete' else 0
    yl=fl(r0['absoluteYardlineNumber']);ytg=round(110-losX) if d>0 else round(losX-10)
    q=int(float(r0['quarter']));clk=r0['gameClock'][:5].lstrip('0') or '0:00'
    hs,vs=int(float(r0['preSnapHomeScore'])),int(float(r0['preSnapVisitorScore']))
    offS,defS=(hs,vs) if offT==home else (vs,hs);diff=offS-defS
    gid=r0['gameId'];date=datetime.date(int(gid[:4]),int(gid[4:6]),int(gid[6:8]))
    st=r0['seasonType'];wk=int(float(r0['week']));rnd=ROUND.get(st,{}).get(wk) if st=='POST' else f'Week {wk}'
    cdesc=re.sub(r'^\([^)]*\)\s*','',desc);cdesc=re.sub(r'^\((Shotgun|No Huddle, Shotgun|No Huddle)\)\s*','',cdesc)
    cdesc=re.split(r'(?<=\.)\s+(?=(The Replay|PENALTY|Penalty|NE 12|Pass \d|Caught|[A-Z][a-z]+ challenge|CLV|Los Angeles))',cdesc)[0]
    tgtP=next((p for p in off if p.get('target')),None)
    out.append({'key':key,'real':True,'season':int(r0['season']),'round':rnd,'date':date.strftime('%b %-d, %Y'),'home':home,'away':away,'offT':offT,'defT':defT,
      'offName':TEAMS.get(offT,offT),'defName':TEAMS.get(defT,defT),'down':int(float(r0['down'])),'dist':int(float(r0['yardsToGo'])),'ytg':ytg,
      'clock':f"Q{q} · {clk} · "+('tied' if diff==0 else ('up ' if diff>0 else 'down ')+str(abs(diff))),'score':[hs,vs],'T':round(T,2),
      'qb':qb,'off':off,'def':de,'pro':{'targetNum':tgtP['num'] if tgtP else None,'spot':{'x':spot[0],'y':spot[1]},'type':typ,'result':{'kind':kind,'yac':yac},'text':cdesc,'gain':gain,'air':round(air,2)},
      'targetName':tgtP['name'] if tgtP else None})
    print(key,qb['name'],'T',round(T,2),'air',round(air,2),typ,kind,'spot',spot,'tgt',tgtP and tgtP['name'],'ytg',ytg,len(off),len(de))
json.dump(out,open(os.path.join(HERE,'..','real_plays.json'),'w'),separators=(',',':'))
print(os.path.getsize(os.path.join(HERE,'..','real_plays.json')))

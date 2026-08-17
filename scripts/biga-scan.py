#!/usr/bin/env python3
import json,os,re,sys,time,urllib.request,shutil
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone,timedelta
C=timezone(timedelta(hours=8))
P={"6":"sh","0":"sz","3":"sz","8":"bj","4":"bj"}
N=[("sh000001","上证指数"),("sz399001","深证成指"),("sz399006","创业板指")]
F={"name":1,"code":2,"price":3,"y":4,"o":5,"v":6,"h":31,"change_pct":32,"H":33,"L":34,"turnover_rate":38,"pe":39,"amplitude":43,"market_cap":44}
OC=shutil.which("openclaw")or"/Users/guoxia/.npm-global/bin/openclaw"
K="/tmp/bk"; PP=os.path.expanduser("~/.openclaw/workspace/memory/biga-stock-pool.md"); TP=os.path.expanduser("~/.openclaw/workspace/memory/biga-technical-data.md")
def f(v,d=0.0):
 try: return float(str(v).strip())
 except: return d
def i(v,d=0):
 try: return int(float(str(v).strip()))
 except: return d
def px(c): return P.get(c[0],"sh")
def nw(): return datetime.now(C).strftime("%Y-%m-%d %H:%M")
def is_td():
 """查询深交所日历判断今天是否为A股交易日"""
 td=datetime.now(C).strftime("%Y-%m-%d");ym=td[:7]
 try:
  req=urllib.request.Request(f"http://www.szse.cn/api/report/exchange/onepersistenthour/monthList?month={ym}")
  req.add_header("User-Agent","Mozilla/5.0");req.add_header("Referer","http://www.szse.cn/aboutus/calendar/index.html")
  with urllib.request.urlopen(req,timeout=5)as r:d=json.loads(r.read().decode("utf-8"))
  for e in d.get("data",[]):
   if e.get("jyrq")==td:return e.get("jybz")=="1"
  return False
 except:return False
def _cg(d,idx,default=""):
 try: return d[idx] if idx<len(d) else default
 except: return default
def _safe(val,default=0):
 try: v=float(val);return v if v>0 else default
 except: return default

def pp_(p):
 st,se=[],set()
 if not os.path.isfile(p): return st
 with open(p,encoding="utf-8") as fg: ls=fg.readlines()
 ca=False
 for l in ls:
  if not l.strip(): continue
  if l.strip().startswith("#"): continue
  if "代码" in l and "名称" in l: ca=True;continue
  if not ca: continue
  # 解析Markdown表格或空格分隔格式
  if '|' in l:
   cols=[c.strip() for c in l.split('|') if c.strip()]
   cd,nm='',''
   for c in cols:
    m=re.match(r"^(sh|sz|bj)?(\d{6})$",c.strip())
    if m: cd=m.group(2);break
   if cd and len(cols)>=2:
    nm=cols[1]if cd else ''
   else:
    continue
  else:
   p2=l.strip().split()
   if len(p2)<2: continue
   cd=p2[0].strip();nm=p2[1].strip()
   if not re.match(r"^\d{6}$",cd): continue
  if cd in se: continue
  se.add(cd);st.append({"code":cd,"name":nm,"note":"","rating":"","biga_score":0,"t":0,"l":""})
 return st

def _parse_tx(p):
 yc=f(_cg(p,4,0))
 px_=f(_cg(p,3,0))
 if px_==0: return None
 return {"name":_cg(p,1,""),"price":px_,"y":yc,"o":_cg(p,5,""),"v":f(_cg(p,6,0)),"h":"","change_pct":round((px_-yc)/yc*100,2) if yc else 0,"H":_cg(p,33,0),"L":_cg(p,34,0),"turnover_rate":f(_cg(p,38,0)),"pe":f(_cg(p,39,0)),"amplitude":0,"market_cap":_cg(p,44,0)}

def fq(cs):
 if not cs: return {}
 qt={}
 missing=[]
 # 主接口: 腾讯(字段映射确认可靠,且更稳定)
 def _fetch(url):
  try: return urllib.request.urlopen(url, timeout=5).read().decode("gbk","ignore")
  except: return ""
 with ThreadPoolExecutor(max_workers=8) as ex:
  futs={}
  for c in cs:
   x=px(c);lk=c if c.startswith(("sh","sz","bj")) else x+c
   futs[ex.submit(_fetch,f"http://qt.gtimg.cn/q={lk}")]=lk
  for fu in futs:
   lk=futs[fu];d=fu.result()
   m=re.search(r'="([^"]*)"',d)
   if m and len(m.group(1).split("~"))>44:
    r=_parse_tx(m.group(1).split("~"))
    if r: qt[lk]=r
    else: missing.append(lk)
   else: missing.append(lk)
 # 备用: 新浪补拉腾讯失败的
 if missing:
  def _fetch_sina(url):
   try:
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0', 'Referer': 'http://finance.sina.com.cn'})
    return urllib.request.urlopen(req, timeout=5).read().decode("gbk","ignore")
   except: return ""
  with ThreadPoolExecutor(max_workers=8) as ex2:
   futs2={}
   for lk in missing:
    futs2[ex2.submit(_fetch_sina,f"http://hq.sinajs.cn/list={lk}")]=lk
   for fu in futs2:
    lk=futs2[fu];d=fu.result()
    m=re.search(r'="([^"]*)"',d)
    if m:
     p=m.group(1).split(",")
     qt[lk]={"name":_cg(p,0,""),"price":_safe(_cg(p,3,0)),"y":_cg(p,2,""),"o":_cg(p,1,""),"v":f(_cg(p,8,0)),"h":"","change_pct":0,"H":_cg(p,4,""),"L":_cg(p,5,""),"turnover_rate":0,"pe":0,"amplitude":0,"market_cap":0}
 return qt

def fk(c):
 lk=c if c.startswith(("sh","sz","bj")) else px(c)+c
 # 主接口: 新浪日K线 (支持多只并发, 返回干净JSON)
 for try_sina in (True, False):
  try:
   url = f"http://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData?symbol={lk}&scale=240&ma=5&datalen=10&r={time.time()}" if try_sina else f"http://web.ifzq.gtimg.cn/appstock/app/kline/getkline?_var=kline_dayqfq&param={lk},day,,,10,qfq&r={time.time()}"
   d=urllib.request.urlopen(url,timeout=5).read().decode("utf-8","ignore")
   if try_sina:
    # 新浪: 直接解析JSON
    kl=json.loads(d)
    if not kl: continue
    return sorted([{"code":f(it["close"]),"v":f(it["volume"]),"t":int(time.mktime(datetime.strptime(it["day"][:10],"%Y-%m-%d").timetuple()))} for it in kl],key=lambda x:x["t"])
   else:
    # 腾讯: 正则解析
    m=re.search(r'"day"\s*:\s*\[([^\]]+)\]',d)
    if not m: continue
    items=re.findall(r'\["([^"]+)"',m.group(1))
    return sorted([{"code":f(p2[1]),"v":f(p2[5]),"t":int(time.mktime(datetime.strptime(p2[0],"%Y-%m-%d").timetuple()))} for it in items for p2 in [it.split(",")]],key=lambda x:x["t"])
  except: continue
 return []

def fks(st):
 kl,kf={},{}
 with ThreadPoolExecutor(max_workers=8) as ex:
  futs={}
  for s in st:
   cd=s["code"]
   futs[ex.submit(fk,cd)]=cd
  for fu in futs:
   cd=futs[fu]
   try: kl2=fu.result()
   except: kl2=[]
   if kl2: kl[cd]=kl2
 return kl,kf

def ct(kl2,q):
 if not kl2 or len(kl2)<2: return {"score":0,"available":False}
 mp=f(q.get("price",0));mc=f(q.get("market_cap",0))
 ch=[k["code"] for k in kl2]
 ma5=sum(ch[-5:])/5;ma20=sum(ch[-20:])/20 if len(ch)>=20 else ma5
 vo=[k["v"]for k in kl2];avg=sum(vo)/len(vo);vr=kl2[-1]["v"]/avg if avg>0 else 0
 pct=f(q.get("change_pct",0))
 sc=0
 if ma5>ma20*1.02: sc+=4
 elif ma5>ma20: sc+=2
 elif ma5>ma20*0.98: sc+=0
 else: sc-=2
 sc+=5 if pct>3 else 4 if pct>0 else 3 if pct>-3 else 2
 sc+=4 if vr>1.5 else 3 if vr>0.8 else 2
 return {"score":sc,"available":True}

def ss(kl2,q,ts):
 if not kl2 or len(kl2)<5: return {"sg":"--","advice":"K线不足"}
 ch=[k["code"]for k in kl2];ma5=sum(ch[-5:])/5;ma20=sum(ch[-20:])/20 if len(ch)>=20 else ma5
 tp=f(q.get("price",0));mc=f(q.get("market_cap",0))
 pct=f(q.get("change_pct",0));vr=kl2[-1]["v"]/(sum(k["v"]for k in kl2[-20:])/len(kl2[-20:])) if len(kl2)>=20 else 0
 sc=0
 sc+=8 if ma5>ma20*1.05 else 6 if ma5>ma20 else 4 if ma5>ma20*0.95 else 2
 sc+=6 if pct>5 else 4 if pct>0 else 2 if pct>-3 else 1
 sc+=4 if vr>1.3 else 3 if vr>0.7 else 2
 sg="--" if sc<12 else "+" if sc<15 else "++" if sc<18 else "+++"
 adv="观望" if sc<10 else "持有" if sc<14 else "关注" if sc<17 else "买入"
 return {"sg":sg,"advice":adv,"score":sc}

def entry_readiness(kl2, q):
 """入场就绪度 0-10：上涨回调后是否适合买入"""
 if not kl2 or len(kl2)<3: return {"score":0,"note":"数据不足"}
 ch=[k["code"] for k in kl2];vo=[k["v"] for k in kl2]
 price=f(q.get("price",0));ma5=sum(ch[-5:])/5;ma20=sum(ch[-20:])/20 if len(ch)>=20 else ma5
 ma10=sum(ch[-10:])/10 if len(ch)>=10 else ma5
 avg_vol=sum(vo)/len(vo);vr=kl2[-1]["v"]/avg_vol if avg_vol>0 else 1
 sc=0
 dp10=abs(price-ma10)/ma10 if ma10>0 else 99
 if dp10<0.03: sc+=2
 dp20=abs(price-ma20)/ma20 if ma20>0 else 99
 if dp20<0.03: sc+=3
 if vr<0.6: sc+=2
 elif vr<0.8: sc+=1
 body_ratio=abs(ch[-1]-f(q.get("o",price)))/(ch[-1] if ch[-1]>0 else 1)
 if body_ratio<0.02: sc+=1
 if ma5>ma20*1.02: sc+=1
 if len(ch)>=3:
  d1=ch[-1]-ch[-2];d2=ch[-2]-ch[-3]
  if d2<0 and d1>d2: sc+=1
 return {"score":min(sc,10),"note":f"入场就绪{min(sc,10)}/10"}

def risk_filter(kl2, q):
 """风控过滤：追高/抄底风险警告"""
 warnings=[]
 if not kl2 or len(kl2)<3: return {"safe":True,"warnings":warnings,"5d_change":0,"ma20_dev":0}
 ch=[k["code"] for k in kl2];vo=[k["v"] for k in kl2]
 price=f(q.get("price",0));ma20=sum(ch[-20:])/20 if len(ch)>=20 else sum(ch)/len(ch)
 pct=f(q.get("change_pct",0))
 avg_vol=sum(vo)/len(vo);vr=kl2[-1]["v"]/avg_vol if avg_vol>0 else 1
 d5=(ch[-1]-ch[-5])/ch[-5]*100 if len(ch)>=5 else 0
 if d5>15: warnings.append("5日涨幅%.1f%%过高"%d5)
 if d5>25: warnings.append("短线回避：5日涨%.1f%%"%d5)
 if d5<-15: warnings.append("5日跌幅%.1f%%"%d5)
 dev=(price-ma20)/ma20*100 if ma20>0 else 0
 if dev>15: warnings.append("偏离MA20 %.1f%%"%dev)
 if pct>2 and vr<0.7: warnings.append("量价背离: 涨幅%.1f%%"%pct)
 if pct<-5 and vr>1.5: warnings.append("恐慌杀跌：不接飞刀")
 return {"safe":len(warnings)==0,"warnings":warnings,"5d_change":round(d5,1)if len(ch)>=5 else 0,"ma20_dev":round(dev,1)}

def breakout_signals(kl2, q):
 """趋势启动信号检测"""
 signals=[]
 if not kl2 or len(kl2)<5: return {"signals":signals,"strength":0,"note":"数据不足"}
 ch=[k["code"] for k in kl2];vo=[k["v"] for k in kl2]
 price=f(q.get("price",0));ma5=sum(ch[-5:])/5
 ma10=sum(ch[-10:])/10 if len(ch)>=10 else ma5
 ma20=sum(ch[-20:])/20 if len(ch)>=20 else ma5
 avg_vol=sum(vo)/len(vo);vr=kl2[-1]["v"]/avg_vol if avg_vol>0 else 1
 pct=f(q.get("change_pct",0))
 if len(ch)>=6 and ma5>ma10*1.005: signals.append("均线金叉")
 ma_diff=max(ma5,ma10,ma20)-min(ma5,ma10,ma20)
 mid=(ma5+ma10+ma20)/3 if (ma5+ma10+ma20)>0 else 1
 if ma_diff/mid<0.02 and ma5>ma10>ma20: signals.append("均线粘合发散")
 if pct>3 and vr>1.5:
  high_5=max(ch[-5:]) if len(ch)>=5 else max(ch)
  if price>=high_5*0.99: signals.append("底部放量突破")
 if ma5>ma10 and len(ch)>=3 and ch[-3]<=sum(ch[-2:])/2: signals.append("MACD零轴金叉")
 if len(ch)>=8:
  low_10=min(ch[-10:]);high_10=max(ch[-10:])
  amp=(high_10-low_10)/low_10*100 if low_10>0 else 0
  if amp<12 and price>high_10*0.99 and vr>1.3: signals.append("底部箱体突破")
 strength=min(len(signals),3)
 return {"signals":signals,"strength":strength,"note":f"启动信号{strength}/3" if signals else "无"}

def fo(d):
 ts=d.get("st","");an=d.get("stocks",[]);id_=d.get("indices",{});sm=d.get("sm",{})
 lns=[f"# BigA 股票扫描 {ts}"]
 ix=id_.get("上证指数",{});ni=id_.get("深证成指",{});ci=id_.get("创业板指",{})
 lns.append(f"\n## 大盘\n")
 lns.append(f"上证 {ix.get('price','--')} ({ix.get('change_pct','--')}%) | 深成 {ni.get('price','--')} ({ni.get('change_pct','--')}%) | 创业板 {ci.get('price','--')} ({ci.get('change_pct','--')}%)")
 lns.append(f"\n## 股票池 ({sm.get('sc','?')}支)")
 for e in an:
  nm=e.get("name",e.get("code","?"))
  cd=e.get("code","?")
  qt=e.get("quote",{});pr=qt.get("price","?");pc=qt.get("change_pct","?");pe_=qt.get("pe","?");tr=qt.get("turnover_rate","?")
  tm=e.get("technical_timing",{});st2=e.get("short_term",{});lt=e.get("long_term",{})
  tsb=e.get("biga_estimate",{});tot=tsb.get("total","?");nt=tsb.get("note","")
  lns.append(f"\n### {nm}({cd}) 评分{tot}")
  lns.append(f"价格:{pr} 涨跌:{pc}% PE:{pe_} 换手:{tr}%")
  lns.append(f"K线: {tm.get('score','?')}分 | {'✅' if tm.get('available') else '❌'}")
  lns.append(f"短线: {st2.get('advice','--')} | 长线: {lt.get('action','--')} — {lt.get('note','')}")
  # 新信号
  er=e.get("entry_readiness",{});rf=e.get("risk_filter",{});bo=e.get("breakout",{})
  if er.get("score",0)>0: lns.append(f"入场就绪: {er['score']}/10")
  w=rf.get("warnings",[])
  if w: lns.append(f"风控: {'; '.join(w)}")
  bd=bo.get("signals",[])
  if bd: lns.append(f"启动信号: {' | '.join(bd)} (强度{bo.get('strength',0)})")
 lns.append(f"\n---\n*扫描{int(sm.get('el',0))}秒 | K线{sm.get('ks','?')}/{sm.get('sc','?')}*")
 return "\n".join(lns)

def sg(t,mc=500):
 if not t: return []
 b2=t.split("\n");sg2,c=[],[]
 for b in b2:
  b=b.strip()
  if not b: continue
  if c and len(c)+len(b)+2>mc: sg2.append(c.strip());c=b
  else: c=(c+"\n\n"+b)if c else b
 if c: sg2.append(c.strip())
 sg3=[]
 for s2 in sg2:
  if sg3 and len(s2)<100: sg3[-1]+="\n\n"+s2
  else: sg3.append(s2)
 sg2=sg3
 if len(sg2)<=1 and sg2 and len(sg2[0])>mc:
  l=sg2[0].split("\n");sg2,c=[],''
  for ln in l:
   if c and len(c)+len(ln)+1>mc: sg2.append(c.strip());c=ln
   else: c=(c+"\n"+ln)if c else ln
  if c: sg2.append(c.strip())
 return sg2

def cmd_send_segments(json_str=None):
 """解析含---SEGMENT---标记的文本，自动逐段发送到飞书。
    json_str: 直接传入JSON字符串（推荐），否则从argv或stdin读。
    输入JSON: {"content": "含---SEGMENT---的完整文本"}
    通过openclaw CLI逐段发送，避免飞书单条消息截断。
    """
 import subprocess
 openclaw_bin = OC
 if json_str is None:
     json_str = sys.argv[2] if len(sys.argv) > 2 else ''
 if not json_str and not sys.stdin.isatty():
     json_str = sys.stdin.read().strip()
 try: nd = json.loads(json_str) if json_str else {}
 except: return {"error": "JSON解析失败"}
 content = nd.get("content", "")
 channel = nd.get("channel")
 target = nd.get("target", "")
 if not channel or not target:
     try:
         with open(os.path.expanduser('~/.openclaw/workspace/memory/biga-send-config.json')) as f:
             cfg = json.load(f)
         if not channel: channel = cfg.get('channel')
         if not target: target = cfg.get('target')
     except: pass
 if not content or not target or not channel:
     return {"error": "缺少发送参数(content/channel/target)"}
 parts = content.split("---SEGMENT---")
 segs = [p.strip() for p in parts if p.strip()]
 if len(segs) <= 1 and len(content) > 500:
     from re import split as re_split
     auto_parts = re_split(r'\n{2,}', content)
     auto_segs = []
     for p in auto_parts:
         p=p.strip()
         if not p: continue
         if auto_segs and len(p) < 50:
             auto_segs[-1] += '\n\n' + p
         else:
             auto_segs.append(p)
     if len(auto_segs) > 1:
         segs = auto_segs
 merged = []
 for seg in segs:
     if merged and len(seg) < 250:
         combined = merged[-1] + "\n\n" + seg
         if len(combined) <= 600:
             merged[-1] = combined
         else:
             merged.append(seg)
     else:
         merged.append(seg)
 segs = merged
 results = []
 for i, seg in enumerate(segs):
     if not seg: continue
     for attempt in range(3):
         p = subprocess.Popen(
             [openclaw_bin, "message", "send",
              "--channel", channel,
              "--target", target,
              "--message", seg,
              "--json"],
             stdin=subprocess.DEVNULL,
             stdout=subprocess.PIPE,
             stderr=subprocess.PIPE)
         stdout, stderr = p.communicate(timeout=15)
         ok = False
         if p.returncode == 0:
             try:
                 resp = json.loads(stdout.decode())
                 ok = resp.get("payload", {}).get("ok", False)
             except:
                 ok = False
         if ok:
             results.append({"segment": i+1, "status": "sent", "attempt": attempt+1})
             break
         time.sleep(1)
     else:
         results.append({"segment": i+1, "status": "failed", "attempt": 3})
 sent = sum(1 for r in results if r["status"] == "sent")
 return {"action": "send-segments", "total": len(segs), "sent": sent,
         "failed": len(segs) - sent, "details": results}

def main():
 pp=PP;tp=TP;fm=False;sg_f=False;ss_cmd=False;cds=[]
 a2=list(sys.argv[1:]);i=0
 while i<len(a2):
  a=a2[i]
  if a in("--format","-f"): fm=True;a2.pop(i);continue
  if a in("--send-segments",): ss_cmd=True;a2.pop(i);continue
  if a in("--segments","-s"): sg_f=True;fm=True;a2.pop(i);continue
  if a.startswith("--codes="): cds=[c.strip()for c in a.split("=",1)[1].split(",")if c.strip()];a2.pop(i);continue
  if a=="--codes"and i+1<len(a2): cds=[c.strip()for c in a2[i+1].split(",")if c.strip()];a2.pop(i);a2.pop(i);continue
  i+=1
 # 交易日检查：非交易日直接退出
 if not is_td():
  td=datetime.now(C).strftime("%Y-%m-%d")
  if sg_f or fm:
   print(f"📅 非交易日 — {td} A股休市，不做A股分析")
   sys.exit(0)
  else:
   print(json.dumps({"holiday":True,"date":td,"note":"A股休市"},ensure_ascii=False))
   sys.exit(0)
 if ss_cmd and a2:
     # 快速模式：直接发送自定义JSON内容，跳过池读取
     import json as _j
     result = cmd_send_segments(' '.join(a2))
     print(_j.dumps(result, ensure_ascii=False))
     return
 if a2: pp=os.path.expanduser(a2[0])
 if len(a2)>1: tp=os.path.expanduser(a2[1])
 ts=time.time()
 if cds: st=[{"code":re.sub(r"^(sh|sz|bj)","",c.strip()),"note":"","rating":"","biga_score":0,"t":0,"l":""}for c in cds if len(c.strip())>=6]
 else: st=pp_(pp)
 if not st: print(json.dumps({"e":"空池"}));return
 sc=[s["code"]for s in st];qt=fq(sc+[ic for ic,_ in N])
 kl,kf=fks(st)
 id_={}
 for ic,nm in N:
  if ic in qt: id_[nm]={"price":qt[ic].get("price",0),"change_pct":qt[ic].get("change_pct",0)}
 an=[]
 for s in st:
  c=s["code"];q=qt.get(c if c.startswith(("sh","sz","bj")) else px(c)+c,{});kl2=kl.get(c,[])
  tm=ct(kl2,q)if kl2 else{"score":0,"available":False}
  st2=ss(kl2,q,tm.get("score",0))if kl2 else{"sg":"--","advice":"K线不足"}
  qp=q.get("price",0);qc=q.get("change_pct",0);qpe=q.get("pe",0);qtr=q.get("turnover_rate",0);qamp=q.get("amplitude",0);qmc=q.get("market_cap",0)
  ps=15 if 15<=qpe<=40 else 10 if 10<=qpe<=60 else 5 if qpe>0 else 0
  if not kl2 or len(kl2)<5: tsb=0
  else:
   cls=[k["code"]for k in kl2];ma5=sum(cls[-5:])/5;ma20=sum(cls[-20:])/20 if len(cls)>=20 else ma5
   tsb=(10 if ma5>ma20*1.02 else 7 if ma5>ma20 else 5 if ma5>ma20*0.98 else 3 if ma5>ma20*0.95 else 1)
   vols=[k["v"]for k in kl2];avg=sum(vols)/len(vols);vr2=kl2[-1]["v"]/avg if avg>0 else 1
   tsb+=(5 if qc>2 and vr2>1.2 else 4 if qc>0 and vr2>0.8 else 3 if qc>-2 else 1)+3
  if tsb>=14 and ps>=10 and tm.get("score",0)>=0: lt={"action":"买入","note":"技术强+PE合理"}
  elif tsb>=14 and tm.get("score",0)>=-2: lt={"action":"持有","note":"技术面好"}
  elif tsb>=10 and tm.get("score",0)>=-2: lt={"action":"持有","note":"趋势尚可"}
  elif tm.get("score",0)<=-5: lt={"action":"减仓","note":"技术走弱"}
  elif tsb<10: lt={"action":"观察","note":"技术偏弱"}
  else: lt={"action":"持有观察","note":"信号不明"}
  en={"code":c,"name":q.get("name",s.get("name","")),"rating":s.get("rating",""),"previous_biga":s.get("biga_score",0),
   "quote":{"price":qp,"change_pct":qc,"pe":qpe,"turnover_rate":qtr,"amplitude":qamp,"market_cap":qmc},
   "technical_timing":tm,"short_term":st2,"long_term":lt,"kline_available":len(kl2)>=5,"kline_days":len(kl2)}
  en["entry_readiness"]=entry_readiness(kl2,q)if kl2 else{"score":0,"note":"无K线"}
  en["risk_filter"]=risk_filter(kl2,q)
  en["breakout"]=breakout_signals(kl2,q)
  en["biga_estimate"]={"total":tsb+ps,"note":"脚本估分(技术+PE),完整BigA需模型补"}
  an.append(en)
 el=round(time.time()-ts,1);r={"st":nw(),"stocks":an,"indices":id_,"sm":{"sc":len(st),"ks":len(kl),"el":el}}
 print(f"[I] BigA完成 {el}s | {len(st)}支 | K线{len(kl)}/{len(st)}",file=sys.stderr)
 if ss_cmd:
     import json as _j
     if a2:
         # 模型传入自定义内容: --send-segments '{"content":"...","channel":"...","target":"..."}'
         result = cmd_send_segments(' '.join(a2))
     else:
         cfg_path = os.path.expanduser('~/.openclaw/workspace/memory/biga-send-config.json')
         try:
             with open(cfg_path) as f:
                 cfg = _j.load(f)
             content = '\n---SEGMENT---\n'.join(sg(fo(r)))
             result = cmd_send_segments(_j.dumps({**cfg, 'content': content}, ensure_ascii=False))
         except:
             result = {'error': '缺少参数: python3 biga-scan.py --send-segments \'{"content":"..."}\'', 'tip': 'channel/target 从 memory/biga-send-config.json 读取，缺失则创建'}
     print(_j.dumps(result, ensure_ascii=False))
     return
 elif sg_f: print("\n---SEGMENT---\n".join(sg(fo(r))))
 elif fm: print(fo(r))
 else: print(json.dumps(r,ensure_ascii=False))
if __name__=="__main__": main()
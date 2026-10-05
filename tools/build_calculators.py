#!/usr/bin/env python3
"""Генератор SEO-страниц и виджета «Калькулятор баллов ЕГЭ/ОГЭ». Шкалы берутся из app.html (единый источник).
Запуск из корня проекта: python3 tools/build_calculators.py
Создаёт: kalkulyator-ballov-ege.html, kalkulyator-ballov-oge.html, perevod-ballov-{ege,oge}-*.html,
widget.html (для iframe), vstroit-kalkulyator.html, sitemap.xml."""
import re, json, html, os
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
app=open(os.path.join(ROOT,'app.html'),encoding='utf-8').read()
SITE="https://ege-map.ru"
UPDATED_ISO="2026-10-06"; UPDATED_RU="6 октября 2026 г."
YEAR={"ege":"2026","oge":"2026–2027"}
EXAMNAME={"ege":"ЕГЭ","oge":"ОГЭ"}

def arr(name):
    m=re.search(r'const '+name+r' = \[(.*?)\];',app,re.S); assert m,name
    return [int(x) for x in re.findall(r'-?\d+',m.group(1))]
def marks(name):
    m=re.search(r'const '+name+r' = \[(.*?)\];',app,re.S); assert m,name
    out=[]
    for blk in re.findall(r'\{[^}]*\}',m.group(1)):
        d=dict(re.findall(r'(\w+):\s*(\d+)',blk))
        out.append(dict(mark=int(d["mark"]),frm=int(d["from"]),to=int(d["to"]),gr=int(d.get("grammar",0))))
    return out

# id, ключ в URL, название, «по …», краткое название клавиши
SUBJ=[("rus","russkiy-yazyk","Русский язык","по русскому языку","РУС"),
      ("lit","literatura","Литература","по литературе","ЛИТ"),
      ("math","matematika","Математика","по математике","МАТ"),
      ("bio","biologiya","Биология","по биологии","БИО"),
      ("geo","geografiya","География","по географии","ГЕО"),
      ("phys","fizika","Физика","по физике","ФИЗ"),
      ("chem","himiya","Химия","по химии","ХИМ"),
      ("inf","informatika","Информатика","по информатике","ИНФ")]
SRC={"ege":{"rus":("t","EGE_SCALE"),"lit":("t","LIT_SCALE"),"math":("m","MATH_EGE_MARK_SCALE"),"bio":("t","BIO_EGE_SCALE"),
             "geo":("t","GEO_EGE_SCALE"),"phys":("t","PHYS_EGE_SCALE"),"chem":("t","CHEM_EGE_SCALE"),"inf":("t","INF_EGE_SCALE")},
     "oge":{"rus":("m","OGE_MARK_SCALE"),"lit":("m","LITOGE_MARK_SCALE"),"math":("m","MATH_OGE_MARK_SCALE"),"bio":("m","BIO_OGE_MARK_SCALE"),
             "geo":("m","GEO_OGE_MARK_SCALE"),"phys":("m","PHYS_OGE_MARK_SCALE"),"chem":("m","CHEM_OGE_MARK_SCALE"),"inf":("m","INF_OGE_MARK_SCALE")}}
PROFILES={"ege":{},"oge":{}}
for ex in ("ege","oge"):
    for sid,slug,name,by,key in SUBJ:
        kind,const=SRC[ex][sid]
        p=dict(id=sid,exam=ex,slug=slug,name=name,by=by,key=key,kind="test" if kind=="t" else "mark",
               url=f"/perevod-ballov-{ex}-{slug}.html")
        if kind=="t":
            sc=arr(const); assert sc[0]==0 and sc[-1]==100 and all(b>=a for a,b in zip(sc,sc[1:])),const
            p["scale"]=sc; p["max"]=len(sc)-1
        else:
            ms=marks(const); assert [m["mark"] for m in ms]==[2,3,4,5] and ms[0]["frm"]==0,const
            p["marks"]=ms; p["max"]=ms[-1]["to"]
            if ex=="ege" and sid=="math":
                p["name"]="Математика (базовый)"; p["by"]="по математике (базовый уровень)"
        if ex=="oge" and sid=="math": p["geom"]=True
        PROFILES[ex][sid]=p
HUBS={"ege":"/kalkulyator-ballov-ege.html","oge":"/kalkulyator-ballov-oge.html"}
EMBED_URL="/vstroit-kalkulyator.html"

def E(x): return html.escape(str(x),quote=True)
def min_primary(scale,t):
    for i,v in enumerate(scale):
        if v>=t: return i
    return None

def js_profiles():
    out={}
    for ex in PROFILES:
        out[ex]={}
        for sid,p in PROFILES[ex].items():
            d={"n":p["name"],"k":p["kind"],"max":p["max"],"u":p["url"]}
            if p["kind"]=="test": d["s"]=p["scale"]
            else: d["m"]=[[m["mark"],m["frm"],m["to"],m["gr"]] for m in p["marks"]]
            if p.get("geom"): d["geom"]=1
            out[ex][sid]=d
    return json.dumps(out,ensure_ascii=False,separators=(',',':'))

CSS_BASE="""
:root{--cy:#00FDFF;--cy-t:#E4FDFE;--lime:#D7F205;--ink:#0C0C0A;--mut:#4F5A59;--mut2:#6F7B7A;--line:rgba(12,12,10,.12);--paper:#F2F4F3}
*{box-sizing:border-box}[hidden]{display:none!important}
body{margin:0;background:var(--paper);color:var(--ink);font-family:'Onest',system-ui,sans-serif;line-height:1.5;-webkit-font-smoothing:antialiased}
a{color:inherit}.wrap{max-width:1100px;margin:0 auto;padding:0 20px}
"""
CSS_CALC="""
.cw{position:relative;width:100%;max-width:380px;margin:0 auto;padding:16px 16px 18px;border-radius:30px;color:#fff;
  background:linear-gradient(180deg,#232C2C 0%,#141A1A 100%);box-shadow:0 30px 60px -24px rgba(12,12,10,.55),0 2px 0 rgba(255,255,255,.08) inset,0 -4px 0 rgba(0,0,0,.35) inset;user-select:none;-webkit-user-select:none;touch-action:manipulation}
.cw-head{display:flex;align-items:center;justify-content:space-between;gap:10px;margin-bottom:12px;padding-right:96px}
.cw-logo img{display:block;height:24px;width:auto}
.cw-seg{display:inline-flex;padding:3px;border-radius:999px;background:#0C1010;box-shadow:inset 0 1px 3px rgba(0,0,0,.6)}
.cw-seg button{border:0;background:transparent;color:#9FB0AF;font:700 12px/1 'IBM Plex Mono',monospace;letter-spacing:.04em;padding:8px 12px;border-radius:999px;cursor:pointer;transition:background .15s,color .15s}
.cw-seg button.on{background:var(--lime);color:var(--ink)}
.cw-lcd{position:relative;border-radius:16px;padding:12px 14px 12px;color:var(--ink);overflow:hidden;
  background:linear-gradient(180deg,#D4FBFC 0%,#E8FEFE 100%);box-shadow:inset 0 3px 8px rgba(0,60,62,.28),inset 0 0 0 2px rgba(0,0,0,.35),0 1px 0 rgba(255,255,255,.12)}
.cw-lcd .r1{display:flex;justify-content:space-between;gap:8px;font:600 11px/1.2 'IBM Plex Mono',monospace;letter-spacing:.05em;text-transform:uppercase;color:rgba(12,12,10,.62)}
.cw-lcd .r2{margin-top:6px;font:600 13px/1.2 'IBM Plex Mono',monospace;color:rgba(12,12,10,.7);display:flex;justify-content:space-between}
.cw-lcd .r2 b{font-weight:700;color:var(--ink)}
.cw-res{margin-top:2px;text-align:right;font:800 66px/1.05 'IBM Plex Mono',monospace;letter-spacing:-.04em;min-height:70px}
.cw-res.dim{color:rgba(12,12,10,.25)}
.cw-res.pop{animation:cwpop .22s ease}
.cw-unit{display:flex;justify-content:space-between;gap:8px;font:600 11.5px/1.3 'IBM Plex Mono',monospace;color:rgba(12,12,10,.66);min-height:15px}
.cw-warn{margin-top:6px;font:600 11px/1.3 'IBM Plex Mono',monospace;color:#7A4A00;min-height:14px}
@keyframes cwpop{from{transform:translateY(6px);opacity:.3}to{transform:none;opacity:1}}
.cw-keys{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-top:14px}
.cw-k{height:54px;border:0;border-radius:14px;font:700 22px/1 'IBM Plex Mono',monospace;cursor:pointer;color:var(--ink);background:#F2F4F3;
  box-shadow:0 4px 0 #A9B3B2,0 6px 10px rgba(0,0,0,.35);transition:transform .06s,box-shadow .06s,background .15s}
.cw-k:active,.cw-k.press{transform:translateY(3px);box-shadow:0 1px 0 #A9B3B2,0 2px 4px rgba(0,0,0,.35)}
.cw-k.op{background:#36403F;color:#fff;box-shadow:0 4px 0 #0A0E0E,0 6px 10px rgba(0,0,0,.35)}
.cw-k.op:active,.cw-k.op.press{box-shadow:0 1px 0 #0A0E0E,0 2px 4px rgba(0,0,0,.35)}
.cw-k.clr{background:var(--lime);box-shadow:0 4px 0 #8E9E00,0 6px 10px rgba(0,0,0,.35)}
.cw-k.clr:active,.cw-k.clr.press{box-shadow:0 1px 0 #8E9E00,0 2px 4px rgba(0,0,0,.35)}
.cw-k.zero{grid-column:span 3;text-align:left;padding-left:26px}
.cw-subj{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-top:16px;padding-top:14px;border-top:1px solid rgba(255,255,255,.1)}
.cw-s{height:40px;border:0;border-radius:11px;background:#2B3534;color:#CFE6E5;font:700 12.5px/1 'IBM Plex Mono',monospace;letter-spacing:.04em;cursor:pointer;
  box-shadow:0 3px 0 #0A0E0E;transition:transform .06s,background .15s,color .15s}
.cw-s:active{transform:translateY(2px);box-shadow:0 1px 0 #0A0E0E}
.cw-s.on{background:var(--cy);color:var(--ink);box-shadow:0 3px 0 #00A9B0,0 0 18px rgba(0,253,255,.45)}
.cw-sticker{position:absolute;right:-8px;top:-14px;transform:rotate(6deg);display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;
  width:96px;padding:9px 6px;border-radius:14px;background:var(--lime);color:var(--ink);text-decoration:none;font:800 12.5px/1.15 'Onest',sans-serif;
  box-shadow:0 8px 18px -6px rgba(0,0,0,.5),0 0 0 3px #fff;transition:transform .2s}
.cw-sticker:hover{transform:rotate(-2deg) scale(1.05)}
.cw-sticker small{display:block;margin-top:3px;font:600 9.5px/1.1 'IBM Plex Mono',monospace;letter-spacing:.04em;text-transform:uppercase;opacity:.7}
@media (max-width:380px){.cw{padding:14px 12px 16px}.cw-k{height:50px}.cw-res{font-size:58px}.cw-sticker{right:-4px}}
@media (prefers-reduced-motion:reduce){.cw-res.pop{animation:none}.cw *{transition:none!important}}
"""
CSS_PAGE="""
html{scroll-behavior:smooth}
header.top{background:#fff;border-bottom:2px solid var(--cy);position:sticky;top:0;z-index:5}
header.top .wrap{height:64px;display:flex;align-items:center;justify-content:space-between;gap:12px}
header.top img{height:34px;display:block}
.pill{display:inline-flex;align-items:center;justify-content:center;gap:8px;height:44px;padding:0 22px;border-radius:999px;font-weight:700;font-size:14px;text-decoration:none;border:0;cursor:pointer;transition:background .15s}
.pill.lime{background:var(--lime);color:var(--ink)}.pill.lime:hover{background:#C3E600}
.pill.dark{background:var(--ink);color:#fff}.pill.ghost{background:#fff;box-shadow:inset 0 0 0 1.5px var(--line)}.pill.ghost:hover{box-shadow:inset 0 0 0 1.5px var(--ink)}
nav.crumbs{font-size:13px;color:var(--mut2);padding:16px 0 0}nav.crumbs a{text-decoration:none}nav.crumbs a:hover{text-decoration:underline}
.stage{display:grid;grid-template-columns:minmax(0,420px) minmax(0,1fr);grid-template-areas:"calc head" "calc tbl" "calc cta";gap:0 34px;margin-top:16px;align-items:start}
.hero{grid-area:head;background:var(--cy);border-radius:30px;padding:26px 28px}
.col-calc{grid-area:calc;position:sticky;top:84px;padding:20px 8px 6px;background:var(--cy);border-radius:34px}
.tag{display:inline-block;font:500 10.5px/1 'IBM Plex Mono',monospace;letter-spacing:.08em;text-transform:uppercase;background:rgba(255,255,255,.6);padding:8px 12px;border-radius:999px}
h1{margin:14px 0 8px;font-size:clamp(26px,4.4vw,40px);line-height:1.05;letter-spacing:-.035em;font-weight:800;text-wrap:balance}
.lead{margin:0;color:rgba(12,12,10,.72);font-size:15.5px}
.card{background:#fff;border-radius:26px;padding:22px;margin-top:16px}
#tblcard{grid-area:tbl}.cta{grid-area:cta}
h2{font-size:clamp(20px,3vw,26px);letter-spacing:-.03em;line-height:1.1;margin:0 0 12px;font-weight:800}
.tbl{display:grid;grid-template-columns:repeat(auto-fill,minmax(118px,1fr));gap:6px}
.tbl button{display:flex;justify-content:space-between;gap:8px;padding:8px 11px;border-radius:11px;border:0;background:var(--paper);font:500 13.5px 'IBM Plex Mono',monospace;cursor:pointer;color:var(--ink);text-align:left;transition:background .15s}
.tbl button:hover{background:var(--cy-t)}.tbl button b{font-weight:700}.tbl button.cur{background:var(--ink);color:#fff}
.marks{width:100%;border-collapse:collapse;font-size:15px}.marks th,.marks td{padding:9px 10px;text-align:left;border-bottom:1px solid var(--line)}.marks th{font:500 11px 'IBM Plex Mono',monospace;color:var(--mut2);text-transform:uppercase;letter-spacing:.05em}.marks tr.cur td{background:var(--cy-t);font-weight:700}.marks .w{color:#7A4A00;font-size:13px}
.src{margin:12px 0 0;font-size:12.5px;color:var(--mut2)}
.cta{background:var(--ink);color:#fff;border-radius:26px;padding:22px;margin-top:16px;display:flex;flex-wrap:wrap;gap:14px 20px;align-items:center;justify-content:space-between}
.cta h2{color:#fff;margin:0}.cta p{margin:4px 0 0;color:rgba(255,255,255,.65);font-size:14.5px}
.cta .acts{display:flex;gap:10px;flex-wrap:wrap}
section.blk{margin-top:26px}
.faq details{border-bottom:1px solid var(--line);padding:12px 0}.faq summary{cursor:pointer;font-weight:700;list-style:none;display:flex;justify-content:space-between;gap:12px}
.faq summary::after{content:"+";font:500 22px/1 'IBM Plex Mono',monospace;color:var(--mut2)}.faq details[open] summary::after{content:"−"}.faq p{margin:8px 0 0;color:var(--mut)}
.chips{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:10px}.chips b{font:500 11px/36px 'IBM Plex Mono',monospace;color:var(--mut2);letter-spacing:.06em;text-transform:uppercase;width:44px}
.chips a{padding:8px 15px;border-radius:999px;background:#fff;text-decoration:none;font-weight:600;font-size:14px;box-shadow:inset 0 0 0 1.5px var(--line)}.chips a:hover{box-shadow:inset 0 0 0 1.5px var(--ink)}.chips a.on{background:var(--ink);color:#fff;box-shadow:none}
.embedcard{display:flex;flex-wrap:wrap;gap:12px 20px;align-items:center;justify-content:space-between}
footer.ft{margin-top:34px;padding:22px 0 90px;font-size:13px;color:var(--mut2);border-top:1px solid var(--line)}footer.ft a{text-decoration:none;border-bottom:1px solid var(--line)}
.sbar{display:none}
@media(max-width:860px){
  .stage{grid-template-columns:1fr;grid-template-areas:"head" "calc" "tbl" "cta";gap:0}
  .col-calc{position:static;margin-top:14px}.hero{padding:22px 20px}
  .sbar{display:flex;position:fixed;left:0;right:0;bottom:0;z-index:20;align-items:center;gap:10px;padding:10px 14px calc(10px + env(safe-area-inset-bottom));background:var(--ink);color:#fff;box-shadow:0 -10px 30px rgba(0,0,0,.25)}
  .sbar span{flex:1;font-size:13.5px;font-weight:600;line-height:1.25}.sbar .pill{height:40px;padding:0 16px;font-size:13px}
  .sbar button{border:0;background:transparent;color:rgba(255,255,255,.55);font-size:20px;width:32px;height:32px;cursor:pointer}
  header.top .pill{display:none}
}
"""

JS="""
(function(){
  var P=%%PROFILES%%, C=window.EGE_CALC||{}, S={exam:C.exam||"ege",subj:C.subj||"rus",val:""};
  var $=function(i){return document.getElementById(i)}, EXN={ege:"ЕГЭ",oge:"ОГЭ"};
  function prof(){return P[S.exam][S.subj]}
  function pl(n,a,b,c){n=Math.abs(n);return n%10===1&&n%100!==11?a:(n%10>=2&&n%10<=4&&!(n%100>=12&&n%100<=14))?b:c}
  function markOf(p,v){for(var i=0;i<p.m.length;i++){if(v>=p.m[i][1]&&v<=p.m[i][2])return p.m[i]}return p.m[0]}
  function render(){
    var p=prof(), has=S.val!=="", v=has?+S.val:0, res=$("cwRes");
    $("cwCtx").textContent=EXN[S.exam]+" · "+p.n; $("cwMax").textContent="макс "+p.max;
    $("cwIn").textContent=has?v:"—";
    var out,unit,sub="",warn="";
    if(!has){out="0";unit="введите первичные баллы";}
    else if(p.k==="test"){
      out=p.s[v]; unit="тестовых баллов";
      sub=v<p.max?"+1 первичный → "+p.s[v+1]+" (+"+(p.s[v+1]-p.s[v])+")":"максимум";
    }else{
      var m=markOf(p,v); out=m[0]; unit="отметка";
      var nx=null; for(var i=0;i<p.m.length;i++){if(p.m[i][1]>v){nx=p.m[i];break}}
      sub=nx?"до «"+nx[0]+"»: ещё "+(nx[1]-v):"максимум";
      if(S.exam==="oge"&&S.subj==="rus"&&m[3])warn="⚠ нужна грамотность ≥ "+m[3];
      if(p.geom&&m[0]>=3)warn="⚠ нужно ≥ 2 б. по геометрии";
    }
    res.className="cw-res"+(has?"":" dim"); res.textContent=out;
    if(has){res.classList.remove("pop");void res.offsetWidth;res.classList.add("pop")}
    $("cwUnit").textContent=unit; $("cwSub").textContent=sub; $("cwWarn").textContent=warn;
    document.querySelectorAll("[data-exam]").forEach(function(b){b.classList.toggle("on",b.dataset.exam===S.exam);b.setAttribute("aria-pressed",b.dataset.exam===S.exam)});
    document.querySelectorAll("[data-subj]").forEach(function(b){b.classList.toggle("on",b.dataset.subj===S.subj);b.setAttribute("aria-pressed",b.dataset.subj===S.subj)});
    var t=$("tbl"); if(t&&C.dynTable) table(p,has?v:-1);
  }
  function table(p,v){
    var t=$("tbl"),h="";
    if(p.k==="test"){p.s.forEach(function(x,i){h+='<button type="button" data-p="'+i+'"'+(i===v?' class="cur"':'')+' aria-label="'+i+' первичных — '+x+' тестовых"><span>'+i+'</span><b>'+x+'</b></button>'});t.className="tbl";t.innerHTML=h}
    else{h='<table class="marks"><thead><tr><th>Отметка</th><th>Первичные</th><th></th></tr></thead><tbody>';
      var cur=v>=0?markOf(p,v)[0]:0;
      p.m.forEach(function(m){var w="";if(S.exam==="oge"&&S.subj==="rus"&&m[3])w="грамотность ≥ "+m[3];if(p.geom&&m[0]>=3)w="≥ 2 балла по геометрии";
        h+='<tr'+(m[0]===cur?' class="cur"':'')+'><td><b>'+m[0]+'</b></td><td class="mono">'+m[1]+'–'+m[2]+'</td><td class="w">'+w+'</td></tr>'});
      t.className="";t.innerHTML=h+'</tbody></table>'}
    var tt=$("tblTitle"); if(tt)tt.textContent=EXN[S.exam]+" · "+p.n+": "+(p.k==="test"?"первичные → тестовые":"первичные → отметка");
  }
  function press(el){if(!el)return;el.classList.add("press");setTimeout(function(){el.classList.remove("press")},90);if(navigator.vibrate)try{navigator.vibrate(8)}catch(e){}}
  function digit(d){var p=prof(),n=S.val===""?String(d):S.val+String(d);if(n.length>1&&n[0]==="0")n=String(+n);if(+n>p.max)n=String(d);S.val=n;render()}
  function step(k){var p=prof(),v=S.val===""?(k>0?-1:p.max+1):+S.val;v=Math.max(0,Math.min(p.max,v+k));S.val=String(v);render()}
  function act(a){
    if(a==="C")S.val="";else if(a==="B")S.val=S.val.slice(0,-1);else if(a==="+")step(1);else if(a==="-")step(-1);else digit(a);
    if(a==="C"||a==="B")render();
  }
  document.querySelectorAll("[data-k]").forEach(function(b){b.addEventListener("click",function(){press(b);act(b.dataset.k)})});
  document.querySelectorAll("[data-exam]").forEach(function(b){b.addEventListener("click",function(){S.exam=b.dataset.exam;press(b);var p=prof();if(S.val!==""&&+S.val>p.max)S.val=String(p.max);render()})});
  document.querySelectorAll("[data-subj]").forEach(function(b){b.addEventListener("click",function(){S.subj=b.dataset.subj;press(b);var p=prof();if(S.val!==""&&+S.val>p.max)S.val=String(p.max);render()})});
  document.addEventListener("keydown",function(e){
    if(e.ctrlKey||e.metaKey||e.altKey)return; var t=e.target&&e.target.tagName; if(t==="INPUT"||t==="SELECT"||t==="TEXTAREA")return;
    var k=e.key,map={Backspace:"B",Delete:"C",Escape:"C",ArrowUp:"+",ArrowDown:"-","+":"+","-":"-"},a=null;
    if(/^[0-9]$/.test(k))a=k;else if(map[k])a=map[k]; if(a===null)return;
    e.preventDefault();var el=document.querySelector('[data-k="'+a+'"]');press(el);act(a);
  });
  var tb=$("tbl"); if(tb)tb.addEventListener("click",function(e){var b=e.target.closest("[data-p]");if(!b)return;S.val=b.dataset.p;render()});
  var sb=$("sbarX"); if(sb)sb.onclick=function(){$("sbar").hidden=true;document.body.style.paddingBottom=0};
  render();
})();
"""

def calc_html(p, embed=False):
    exam=p["exam"]
    subj=''.join(f'<button type="button" class="cw-s{" on" if s[0]==p["id"] else ""}" data-subj="{s[0]}" aria-pressed="{"true" if s[0]==p["id"] else "false"}" aria-label="{E(s[2])}">{s[4]}</button>' for s in SUBJ)
    stk=('<a class="cw-sticker" href="https://ege-map.ru/?utm_source=widget" target="_blank" rel="noopener">ЕГЭ_Map<small>калькулятор</small></a>' if embed else
         '<a class="cw-sticker" href="/app.html" aria-label="ЕГЭ_Map: 3 ученика бесплатно">3 ученика<br>бесплатно<small>для учителей ↗</small></a>')
    logo=('<a class="cw-logo" href="https://ege-map.ru/?utm_source=widget" target="_blank" rel="noopener" aria-label="ЕГЭ_Map"><img src="/logo-lockup-dark.svg" alt="ЕГЭ_Map"></a>' if embed else
          '<a class="cw-logo" href="/" aria-label="ЕГЭ_Map"><img src="/logo-lockup-dark.svg" alt="ЕГЭ_Map"></a>')
    keys=lambda k,c="":f'<button type="button" class="cw-k {c}" data-k="{k}" aria-label="{ {"B":"Стереть","C":"Сбросить","+":"Плюс один","-":"Минус один"}.get(k,k) }">{ {"B":"⌫","-":"−"}.get(k,k) }</button>'
    grid=(keys("7")+keys("8")+keys("9")+keys("C","clr")+keys("4")+keys("5")+keys("6")+keys("B","op")+keys("1")+keys("2")+keys("3")+keys("-","op")
          +keys("0","zero")+keys("+","op"))
    return f'''<div class="cw" id="cw" role="group" aria-label="Калькулятор баллов">
  {stk}
  <div class="cw-head">{logo}<div class="cw-seg"><button type="button" data-exam="ege" class="{"on" if exam=="ege" else ""}" aria-pressed="{"true" if exam=="ege" else "false"}">ЕГЭ</button><button type="button" data-exam="oge" class="{"on" if exam=="oge" else ""}" aria-pressed="{"true" if exam=="oge" else "false"}">ОГЭ</button></div></div>
  <div class="cw-lcd" aria-live="polite">
    <div class="r1"><span id="cwCtx">{EXAMNAME[exam]} · {E(p["name"])}</span><span id="cwMax">макс {p["max"]}</span></div>
    <div class="r2"><span>первичных</span><b id="cwIn">—</b></div>
    <div class="cw-res dim" id="cwRes">0</div>
    <div class="cw-unit"><span id="cwUnit">введите первичные баллы</span><span id="cwSub"></span></div>
    <div class="cw-warn" id="cwWarn"></div>
  </div>
  <div class="cw-keys">{grid}</div>
  <div class="cw-subj">{subj}</div>
</div>'''

def table_html(p):
    if p["kind"]=="mark":
        rows=''
        for m in p["marks"]:
            w=("грамотность ≥ "+str(m["gr"])) if (p["exam"]=="oge" and p["id"]=="rus" and m["gr"]) else ("≥ 2 балла по геометрии" if p.get("geom") and m["mark"]>=3 else "")
            rows+=f'<tr><td><b>{m["mark"]}</b></td><td class="mono">{m["frm"]}–{m["to"]}</td><td class="w">{w}</td></tr>'
        return f'<table class="marks"><thead><tr><th>Отметка</th><th>Первичные</th><th></th></tr></thead><tbody>{rows}</tbody></table>'
    return ''.join(f'<button type="button" data-p="{i}" aria-label="{i} первичных — {v} тестовых"><span>{i}</span><b>{v}</b></button>' for i,v in enumerate(p["scale"]))

def faq_for(p,hub=False):
    ex=p["exam"]; by=p["by"]; X=EXAMNAME[ex]; yr=YEAR[ex]
    if p["kind"]=="test":
        sc=p["scale"]; parts=[]
        for t in (60,70,80,90,100):
            mp=min_primary(sc,t)
            if mp is not None: parts.append(f"{t} — {mp}")
        return [(f"Сколько первичных баллов на ЕГЭ {by}?",f"Максимум — {p['max']} первичных баллов, это 100 тестовых."),
                (f"Сколько первичных нужно для 60, 70, 80, 90, 100 баллов?","Минимум первичных: "+", ".join(parts)+"."),
                ("Шкала каждый год одинаковая?","Нет, Рособрнадзор утверждает её ежегодно. Здесь шкала "+yr+" года.")]
    ms=p["marks"]
    q=[(f"Сколько баллов нужно на «5», «4» и «3» {X} {by}?",f"«5» — от {ms[3]['frm']}, «4» — от {ms[2]['frm']}, «3» — от {ms[1]['frm']} первичных баллов из {p['max']}.")]
    if ex=="oge" and p["id"]=="rus":
        q.append(("Что с грамотностью?",f"Для «4» нужно не менее {ms[2]['gr']} баллов по грамотности, для «5» — не менее {ms[3]['gr']}."))
    elif p.get("geom"):
        q.append(("Что с геометрией?","Для отметки «3» нужно не менее 2 баллов по геометрии, даже если общая сумма достаточна."))
    else:
        q.append(("Что такое первичный балл?","Сумма баллов за все верно выполненные задания. Отметка выставляется по таблице перевода."))
    q.append(("Шкала каждый год одинаковая?","Не всегда: её утверждают ежегодно. Здесь шкала "+yr+" года."))
    return q

def title_for(p,hub):
    ex=p["exam"]; X=EXAMNAME[ex]; yr=YEAR[ex]
    if hub:
        if ex=="ege": return (f"Калькулятор баллов ЕГЭ {yr}: перевод первичных баллов в тестовые",
            "Онлайн-калькулятор: наберите первичные баллы ЕГЭ и получите тестовый балл. Русский, литература, биология, география, физика, химия, информатика, математика (база).",
            "Калькулятор баллов ЕГЭ","Наберите баллы, выберите предмет")
        return (f"Калькулятор баллов ОГЭ {yr}: перевод в оценку",
            "Онлайн-калькулятор: наберите первичные баллы ОГЭ и получите оценку 2–5. Все предметы, шкала по данным ФИПИ.",
            "Калькулятор баллов ОГЭ","Наберите баллы, выберите предмет")
    if p["kind"]=="test":
        return (f"Перевод баллов ЕГЭ {p['by']} {yr}: калькулятор и таблица",
                f"Калькулятор перевода первичных баллов ЕГЭ {p['by']} в тестовые. Максимум — {p['max']} первичных (100 тестовых). Полная таблица шкалы {yr} года.",
                f"Баллы ЕГЭ {p['by']}","Первичные → тестовые")
    if ex=="ege":
        return (f"Перевод баллов ЕГЭ по математике (база) в оценку {yr}: калькулятор",
                f"Сколько баллов нужно на ЕГЭ по математике базового уровня для оценки 3, 4 и 5. Калькулятор и таблица перевода (максимум {p['max']} первичных баллов).",
                "Баллы ЕГЭ по математике (база)","Первичные → отметка")
    return (f"Перевод баллов ОГЭ {p['by']} в оценку {yr}: калькулятор и таблица",
            f"Калькулятор перевода первичных баллов ОГЭ {p['by']} в оценку 2–5. Максимум — {p['max']} баллов. Таблица шкалы.",
            f"Баллы ОГЭ {p['by']}","Первичные → отметка")

def page(p,hub=False):
    ex=p["exam"]; title,desc,h1,lead=title_for(p,hub)
    url=HUBS[ex] if hub else p["url"]; canon=SITE+url
    faqs=faq_for(p)
    ld=[{"@context":"https://schema.org","@type":"BreadcrumbList","itemListElement":[
          {"@type":"ListItem","position":1,"name":"ЕГЭ_Map","item":SITE+"/"},
          {"@type":"ListItem","position":2,"name":"Калькулятор баллов "+EXAMNAME[ex],"item":SITE+HUBS[ex]}]+([] if hub else [{"@type":"ListItem","position":3,"name":p["name"],"item":canon}])},
        {"@context":"https://schema.org","@type":"WebApplication","name":"Калькулятор баллов "+EXAMNAME[ex],"url":canon,"applicationCategory":"EducationalApplication","operatingSystem":"Web","inLanguage":"ru",
         "offers":{"@type":"Offer","price":"0","priceCurrency":"RUB"},"publisher":{"@type":"Organization","name":"ЕГЭ_Map","url":SITE+"/"}},
        {"@context":"https://schema.org","@type":"FAQPage","mainEntity":[{"@type":"Question","name":q,"acceptedAnswer":{"@type":"Answer","text":a}} for q,a in faqs]}]
    chips=''
    for e in ("ege","oge"):
        chips+=f'<div class="chips"><b>{EXAMNAME[e]}</b>'+''.join(f'<a href="{PROFILES[e][s[0]]["url"]}"{" class=on" if (not hub and e==ex and s[0]==p["id"]) else ""}>{E(s[2])}</a>' for s in SUBJ)+'</div>'
    tbl_title=f'{EXAMNAME[ex]} · {p["name"]}: '+("первичные → тестовые" if p["kind"]=="test" else "первичные → отметка")
    src=f'Шкала {YEAR[ex]}, по данным ФИПИ и Рособрнадзора. Обновлено {UPDATED_RU} Расчёт ориентировочный.'
    faq_html=''.join(f'<details><summary>{E(q)}</summary><p>{E(a)}</p></details>' for q,a in faqs)
    init=f'{{exam:"{ex}",subj:"{p["id"]}",dynTable:true}}'
    return url,f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{E(title)}</title>
<meta name="description" content="{E(desc)}">
<link rel="canonical" href="{canon}">
<meta name="theme-color" content="#00FDFF">
<link rel="icon" href="/favicon.ico" sizes="any">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="icon" href="/favicon-120.png" type="image/png" sizes="120x120">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<meta property="og:type" content="website">
<meta property="og:site_name" content="ЕГЭ_Map">
<meta property="og:locale" content="ru_RU">
<meta property="og:url" content="{canon}">
<meta property="og:title" content="{E(title)}">
<meta property="og:description" content="{E(desc)}">
<meta property="og:image" content="{SITE}/og-image.png?v=2">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{E(title)}">
<meta name="twitter:description" content="{E(desc)}">
<meta name="twitter:image" content="{SITE}/og-image.png?v=2">
<link rel="stylesheet" href="/fonts/fonts.css">
<style>{CSS_BASE}{CSS_PAGE}{CSS_CALC}</style>
<script type="application/ld+json">{json.dumps(ld,ensure_ascii=False)}</script>
</head>
<body>
<header class="top"><div class="wrap">
  <a href="/" aria-label="ЕГЭ_Map — на главную"><img src="/logo-lockup.svg" alt="ЕГЭ_Map"></a>
  <a class="pill lime" href="/app.html?demo=1">Для учителей: демо-класс</a>
</div></header>
<main class="wrap">
  <nav class="crumbs" aria-label="Навигация"><a href="/">ЕГЭ_Map</a> / {'Калькулятор баллов '+EXAMNAME[ex] if hub else '<a href="'+HUBS[ex]+'">Калькулятор баллов '+EXAMNAME[ex]+'</a> / '+E(p["name"])}</nav>
  <div class="stage">
    <section class="hero"><span class="tag">Шкала {YEAR[ex]}</span><h1>{E(h1)}</h1><p class="lead">{E(lead)}</p></section>
    <div class="col-calc">{calc_html(p)}</div>
    <section class="card" id="tblcard"><h2 id="tblTitle">{E(tbl_title)}</h2>
      <div id="tbl" class="{'tbl' if p['kind']=='test' else ''}">{table_html(p)}</div>
      <p class="src">{E(src)}</p></section>
    <section class="cta"><div><h2>Класс на пробниках?</h2><p>ЕГЭ_Map считает это за вас. 3 ученика бесплатно.</p></div>
      <div class="acts"><a class="pill lime" href="/app.html">Попробовать</a><a class="pill ghost" style="background:transparent;color:#fff;box-shadow:inset 0 0 0 1.5px rgba(255,255,255,.4)" href="/app.html?demo=1">Демо-класс</a></div></section>
  </div>
  <section class="blk card faq"><h2>Вопросы</h2>{faq_html}</section>
  <section class="blk">{chips}</section>
  <section class="blk card embedcard"><div><h2 style="margin:0">Калькулятор на свой сайт</h2><p class="src" style="margin:4px 0 0">Бесплатно, готовый код.</p></div><a class="pill dark" href="{EMBED_URL}">Получить код</a></section>
  <footer class="ft">© ЕГЭ_Map · <a href="/">Для учителей</a> · <a href="/parents.html">Родителям</a> · <a href="/app.html?legal=privacy">Политика обработки данных</a> · Расчёт в вашем браузере, данные не сохраняются</footer>
</main>
<div class="sbar" id="sbar"><span>Учитель? Результаты класса — в ЕГЭ_Map</span><a class="pill lime" href="/app.html?demo=1">Демо →</a><button type="button" id="sbarX" aria-label="Закрыть">×</button></div>
<script>window.EGE_CALC={init};</script>
<script>{JS.replace('%%PROFILES%%',js_profiles())}</script>
</body>
</html>
"""

def widget_page():
    p=PROFILES["ege"]["rus"]
    return "/widget.html",f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Калькулятор баллов ЕГЭ и ОГЭ — ЕГЭ_Map</title>
<meta name="robots" content="noindex">
<link rel="canonical" href="{SITE}{HUBS['ege']}">
<link rel="stylesheet" href="/fonts/fonts.css">
<style>{CSS_BASE}body{{background:transparent;padding:24px 10px 12px}}{CSS_CALC}</style>
</head>
<body>
{calc_html(p,embed=True)}
<script>(function(){{var q=new URLSearchParams(location.search),e=q.get("exam"),s=q.get("subj");window.EGE_CALC={{exam:(e==="oge"?"oge":"ege"),subj:/^(rus|lit|math|bio|geo|phys|chem|inf)$/.test(s)?s:"rus"}};}})();</script>
<script>(function(){{var m=new URLSearchParams(location.search).get("mode"),st=document.querySelector(".cw-sticker"),lg=document.querySelector(".cw-logo");
 if(m==="landing"){{st.href="/app.html";st.target="_top";st.removeAttribute("rel");st.innerHTML="3 ученика<br>бесплатно<small>для учителей ↗</small>";st.setAttribute("aria-label","ЕГЭ_Map: 3 ученика бесплатно");lg.href="/";lg.target="_top";lg.removeAttribute("rel")}}
 else if(m==="plain"||m==="app"){{st.remove();document.body.style.padding="12px 10px";if(m==="app"){{lg.removeAttribute("href");lg.removeAttribute("target");lg.removeAttribute("rel")}}else{{lg.href="/";lg.target="_top";lg.removeAttribute("rel")}}}}}})();</script>
<script>{JS.replace('%%PROFILES%%',js_profiles())}</script>
</body>
</html>
"""

def embed_page():
    title="Встроить калькулятор баллов ЕГЭ и ОГЭ на сайт"
    desc="Бесплатный виджет-калькулятор баллов ЕГЭ и ОГЭ для школьного сайта, блога или страницы репетитора. Скопируйте код и вставьте на страницу."
    canon=SITE+EMBED_URL
    return EMBED_URL,f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{desc}">
<link rel="canonical" href="{canon}">
<meta name="theme-color" content="#00FDFF">
<link rel="icon" href="/favicon.ico" sizes="any">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<meta property="og:type" content="website"><meta property="og:site_name" content="ЕГЭ_Map"><meta property="og:locale" content="ru_RU">
<meta property="og:url" content="{canon}"><meta property="og:title" content="{title}"><meta property="og:description" content="{desc}">
<meta property="og:image" content="{SITE}/og-image.png?v=2"><meta name="twitter:card" content="summary_large_image">
<link rel="stylesheet" href="/fonts/fonts.css">
<style>{CSS_BASE}{CSS_PAGE}
.eg{{display:grid;grid-template-columns:minmax(0,1fr) 400px;gap:28px;margin-top:18px;align-items:start}}
.eg select{{height:46px;border-radius:14px;border:1.5px solid var(--line);background:#fff;padding:0 14px;font:600 15px 'Onest',sans-serif;width:100%}}
.eg label{{display:block;font:500 11px 'IBM Plex Mono',monospace;letter-spacing:.06em;text-transform:uppercase;color:var(--mut2);margin:14px 0 6px}}
.eg textarea{{width:100%;height:150px;border-radius:14px;border:1.5px solid var(--line);background:#fff;padding:12px;font:500 12.5px/1.5 'IBM Plex Mono',monospace;resize:vertical}}
.eg iframe{{width:100%;height:680px;border:0;border-radius:30px;background:var(--cy)}}
@media(max-width:860px){{.eg{{grid-template-columns:1fr}}}}
</style>
<meta name="robots" content="index,follow">
</head>
<body>
<header class="top"><div class="wrap"><a href="/" aria-label="ЕГЭ_Map — на главную"><img src="/logo-lockup.svg" alt="ЕГЭ_Map"></a><a class="pill lime" href="/app.html?demo=1">Для учителей: демо-класс</a></div></header>
<main class="wrap">
  <nav class="crumbs"><a href="/">ЕГЭ_Map</a> / Калькулятор на свой сайт</nav>
  <section class="hero" style="margin-top:16px"><span class="tag">Виджет</span><h1>Калькулятор баллов на вашем сайте</h1><p class="lead">Выберите, вставьте код. Бесплатно.</p></section>
  <div class="eg">
    <div class="card" style="margin:0">
      <label for="ex" style="margin-top:0">Экзамен</label><select id="ex"><option value="ege">ЕГЭ</option><option value="oge">ОГЭ</option></select>
      <label for="sj">Предмет по умолчанию</label><select id="sj">{''.join(f'<option value="{s[0]}">{E(s[2])}</option>' for s in SUBJ)}</select>
      <label for="code">Код для вставки</label><textarea id="code" readonly></textarea>
      <div style="display:flex;gap:10px;margin-top:12px;flex-wrap:wrap"><button class="pill lime" id="copy" type="button">Скопировать код</button><span id="msg" class="src" style="align-self:center;margin:0"></span></div>
      <p class="src">Ссылка внизу кода помогает посетителям найти полную версию.</p>
    </div>
    <div><iframe id="pv" title="Предпросмотр" loading="lazy"></iframe></div>
  </div>
  <footer class="ft">© ЕГЭ_Map · <a href="{HUBS['ege']}">Калькулятор ЕГЭ</a> · <a href="{HUBS['oge']}">Калькулятор ОГЭ</a> · <a href="/">Для учителей</a></footer>
</main>
<script>(function(){{
 var ex=document.getElementById("ex"),sj=document.getElementById("sj"),code=document.getElementById("code"),pv=document.getElementById("pv");
 function url(){{return "https://ege-map.ru/widget.html?exam="+ex.value+"&subj="+sj.value}}
 function upd(){{var u=url();pv.src=u.replace("https://ege-map.ru","");
  code.value='<iframe src="'+u+'" width="380" height="680" style="border:0;border-radius:30px;max-width:100%" loading="lazy" title="Калькулятор баллов '+(ex.value==="oge"?"ОГЭ":"ЕГЭ")+'"></iframe>\\n<p style="font:13px sans-serif"><a href="https://ege-map.ru/kalkulyator-ballov-'+ex.value+'.html" target="_blank" rel="noopener">Калькулятор баллов '+(ex.value==="oge"?"ОГЭ":"ЕГЭ")+' от ЕГЭ_Map</a></p>';}}
 ex.onchange=sj.onchange=upd;upd();
 document.getElementById("copy").onclick=function(){{var m=document.getElementById("msg");code.select();
  (navigator.clipboard?navigator.clipboard.writeText(code.value):Promise.reject()).then(function(){{m.textContent="Скопировано"}},function(){{document.execCommand("copy");m.textContent="Скопировано"}});}};
}})();</script>
</body>
</html>
"""

written=[]
def save(url,content):
    open(os.path.join(ROOT,url.lstrip('/')),'w',encoding='utf-8').write(content); written.append(url)
for ex in ("ege","oge"):
    save(*page(PROFILES[ex]["rus"],hub=True))
    for sid,*_ in SUBJ: save(*page(PROFILES[ex][sid]))
save(*widget_page()); save(*embed_page())

urls=[("/","1.0","weekly"),("/parents.html","0.7","monthly"),(HUBS["ege"],"0.9","monthly"),(HUBS["oge"],"0.9","monthly"),(EMBED_URL,"0.4","yearly")]
urls+=[(PROFILES[e][s[0]]["url"],"0.8","monthly") for e in ("ege","oge") for s in SUBJ]
sm='<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'+''.join(f'  <url>\n    <loc>{SITE}{u}</loc>\n    <lastmod>{UPDATED_ISO}</lastmod>\n    <changefreq>{c}</changefreq>\n    <priority>{pr}</priority>\n  </url>\n' for u,pr,c in urls)+'</urlset>\n'
open(os.path.join(ROOT,'sitemap.xml'),'w',encoding='utf-8').write(sm)
print(len(written),"pages")

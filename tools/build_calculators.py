#!/usr/bin/env python3
"""Генератор страниц-калькуляторов баллов ЕГЭ (SEO). Шкалы берутся из app.html (единый источник).
Запуск из корня проекта: python3 tools/build_calculators.py  — перезаписывает kalkulyator-*.html / perevod-ballov-ege-*.html и sitemap.xml."""
import re, json, html, os, sys
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
app=open(os.path.join(ROOT,'app.html'),encoding='utf-8').read()
SITE="https://ege-map.ru"
UPDATED_ISO="2026-10-06"; UPDATED_RU="6 октября 2026 г."
YEAR="2026"

def arr(name):
    m=re.search(r'const '+name+r' = \[(.*?)\];',app,re.S); assert m,name
    return [int(x) for x in re.findall(r'-?\d+',m.group(1))]
def marks(name):
    m=re.search(r'const '+name+r' = \[(.*?)\];',app,re.S); assert m,name
    return [dict(mark=int(a),frm=int(b),to=int(c)) for a,b,c in re.findall(r'mark:(\d+),\s*from:(\d+),\s*to:(\d+)',m.group(1))]

# slug, название, «по …», шкала
SUBJ=[
 dict(id="rus", slug="russkiy-yazyk", name="Русский язык", by="по русскому языку", scale=arr("EGE_SCALE")),
 dict(id="lit", slug="literatura", name="Литература", by="по литературе", scale=arr("LIT_SCALE")),
 dict(id="bio", slug="biologiya", name="Биология", by="по биологии", scale=arr("BIO_EGE_SCALE")),
 dict(id="geo", slug="geografiya", name="География", by="по географии", scale=arr("GEO_EGE_SCALE")),
 dict(id="phys", slug="fizika", name="Физика", by="по физике", scale=arr("PHYS_EGE_SCALE")),
 dict(id="chem", slug="himiya", name="Химия", by="по химии", scale=arr("CHEM_EGE_SCALE")),
 dict(id="inf", slug="informatika", name="Информатика", by="по информатике", scale=arr("INF_EGE_SCALE")),
 dict(id="math", slug="matematika-baza", name="Математика (базовый уровень)", by="по математике (базовый уровень)", marks=marks("MATH_EGE_MARK_SCALE")),
]
for s in SUBJ:
    s["kind"]="mark" if "marks" in s else "test"
    s["url"]="/perevod-ballov-ege-"+s["slug"]+".html"
    s["max"]=(s["marks"][-1]["to"] if s["kind"]=="mark" else len(s["scale"])-1)
    if s["kind"]=="test":
        assert s["scale"][0]==0 and s["scale"][-1]==100 and all(b>=a for a,b in zip(s["scale"],s["scale"][1:])),s["id"]
HUB_URL="/kalkulyator-ballov-ege.html"

def min_primary(scale,t):
    for p,v in enumerate(scale):
        if v>=t: return p
    return None
def pl(n,a,b,c):
    n=abs(n); return a if n%10==1 and n%100!=11 else b if 2<=n%10<=4 and not 12<=n%100<=14 else c
def E(x): return html.escape(str(x),quote=True)

CSS="""
:root{--cy:#00FDFF;--cy-t:#E4FDFE;--lime:#D7F205;--ink:#0C0C0A;--mut:#4F5A59;--mut2:#6F7B7A;--line:rgba(12,12,10,.12);--paper:#F2F4F3}
*{box-sizing:border-box}[hidden]{display:none!important}html{scroll-behavior:smooth}
body{margin:0;background:var(--paper);color:var(--ink);font-family:'Onest',system-ui,sans-serif;line-height:1.55;-webkit-font-smoothing:antialiased}
a{color:inherit}.wrap{max-width:1080px;margin:0 auto;padding:0 20px}
.mono{font-family:'IBM Plex Mono',ui-monospace,monospace}
header.top{background:#fff;border-bottom:2px solid var(--cy);position:sticky;top:0;z-index:5}
header.top .wrap{height:64px;display:flex;align-items:center;justify-content:space-between;gap:12px}
header.top img{height:34px;display:block}
.pill{display:inline-flex;align-items:center;justify-content:center;gap:8px;height:44px;padding:0 22px;border-radius:999px;font-weight:700;font-size:14px;text-decoration:none;border:0;cursor:pointer;transition:transform .15s,background .15s}
.pill.lime{background:var(--lime);color:var(--ink)}.pill.lime:hover{background:#C3E600}
.pill.dark{background:var(--ink);color:#fff}.pill.dark:hover{background:#000}
.pill.ghost{background:#fff;box-shadow:inset 0 0 0 1.5px var(--line)}.pill.ghost:hover{box-shadow:inset 0 0 0 1.5px var(--ink)}
nav.crumbs{font-size:13px;color:var(--mut2);padding:18px 0 0}nav.crumbs a{text-decoration:none}nav.crumbs a:hover{text-decoration:underline}
.hero{margin-top:14px;background:var(--cy);border-radius:34px;padding:34px 34px 38px}
.tag{display:inline-block;font:500 10.5px/1 'IBM Plex Mono',monospace;letter-spacing:.08em;text-transform:uppercase;background:rgba(255,255,255,.6);padding:8px 12px;border-radius:999px}
h1{margin:16px 0 10px;font-size:clamp(28px,5vw,46px);line-height:1.04;letter-spacing:-.035em;font-weight:800;text-wrap:balance}
.lead{margin:0;max-width:640px;color:rgba(12,12,10,.72);font-size:16px}
.calc{margin-top:22px;background:#fff;border-radius:26px;padding:22px;box-shadow:0 18px 40px -18px rgba(12,12,10,.25)}
.grid2{display:grid;grid-template-columns:1.1fr 1fr;gap:22px}
label.l{display:block;font:500 11px/1.3 'IBM Plex Mono',monospace;letter-spacing:.06em;text-transform:uppercase;color:var(--mut2);margin-bottom:8px}
.stepper{display:flex;align-items:center;gap:10px}
.stepper button{width:48px;height:48px;border-radius:50%;border:0;background:var(--paper);font-size:24px;font-weight:700;cursor:pointer;color:var(--ink);transition:background .15s}
.stepper button:hover{background:var(--cy-t)}
.stepper input[type=number]{width:100%;min-width:0;height:56px;border-radius:16px;border:1.5px solid var(--line);background:var(--paper);text-align:center;font:700 28px 'IBM Plex Mono',monospace;color:var(--ink);outline:none}
.stepper input:focus,.rev input:focus{border-color:var(--ink)}
input[type=range]{width:100%;margin:16px 0 4px;accent-color:#0C0C0A}
.hint{font-size:12.5px;color:var(--mut2)}
.out{border-radius:20px;background:var(--cy-t);padding:18px 20px;display:flex;flex-direction:column;justify-content:center;min-height:170px}
.out .big{font:800 68px/1 'IBM Plex Mono',monospace;letter-spacing:-.03em}
.out .of{font:500 16px 'IBM Plex Mono',monospace;color:var(--mut2);margin-left:6px}
.bar{height:8px;border-radius:99px;background:rgba(12,12,10,.1);overflow:hidden;margin:14px 0 10px}.bar i{display:block;height:100%;border-radius:99px;background:var(--ink);width:0;transition:width .35s ease}
.next{font-size:14px;color:var(--mut)}
.rev{margin-top:20px;padding-top:18px;border-top:1px solid var(--line);display:flex;flex-wrap:wrap;gap:12px 16px;align-items:center}
.rev input{width:92px;height:44px;border-radius:12px;border:1.5px solid var(--line);background:var(--paper);text-align:center;font:700 18px 'IBM Plex Mono',monospace;outline:none}
.rev .ans{font-size:15px;font-weight:600}
section.blk{margin-top:30px}
h2{font-size:clamp(22px,3.4vw,30px);letter-spacing:-.03em;line-height:1.1;margin:0 0 12px;font-weight:800}
.card{background:#fff;border-radius:26px;padding:24px}
.tbl{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:6px}
.tbl button{display:flex;justify-content:space-between;gap:8px;padding:9px 12px;border-radius:12px;border:0;background:var(--paper);font:500 14px 'IBM Plex Mono',monospace;cursor:pointer;color:var(--ink);text-align:left;transition:background .15s}
.tbl button:hover{background:var(--cy-t)}.tbl button b{font-weight:700}
.tbl button.cur{background:var(--ink);color:#fff}
.marks{width:100%;border-collapse:collapse;font-size:15px}.marks th,.marks td{padding:10px 12px;text-align:left;border-bottom:1px solid var(--line)}.marks tr.cur td{background:var(--cy-t);font-weight:700}
.cta{background:var(--ink);color:#fff;border-radius:34px;padding:34px;display:grid;grid-template-columns:1.3fr 1fr;gap:22px;align-items:center}
.cta h2{color:#fff}.cta p{margin:0;color:rgba(255,255,255,.7)}
.cta .acts{display:flex;flex-direction:column;gap:10px}
.faq details{border-bottom:1px solid var(--line);padding:14px 0}.faq summary{cursor:pointer;font-weight:700;font-size:16px;list-style:none;display:flex;justify-content:space-between;gap:12px}
.faq summary::after{content:"+";font:500 22px/1 'IBM Plex Mono',monospace;color:var(--mut2)}.faq details[open] summary::after{content:"−"}
.faq p{margin:10px 0 0;color:var(--mut)}
.chips{display:flex;flex-wrap:wrap;gap:8px}.chips a{padding:9px 16px;border-radius:999px;background:#fff;text-decoration:none;font-weight:600;font-size:14px;box-shadow:inset 0 0 0 1.5px var(--line)}.chips a:hover{box-shadow:inset 0 0 0 1.5px var(--ink)}.chips a.on{background:var(--ink);color:#fff;box-shadow:none}
footer.ft{margin-top:40px;padding:26px 0 40px;font-size:13px;color:var(--mut2);border-top:1px solid var(--line)}footer.ft a{text-decoration:none;border-bottom:1px solid var(--line)}
.sel{height:48px;border-radius:14px;border:1.5px solid var(--line);background:var(--paper);padding:0 14px;font:600 15px 'Onest',sans-serif;width:100%;margin-bottom:16px}
@media(max-width:760px){.hero{padding:24px 18px 26px;border-radius:26px}.grid2,.cta{grid-template-columns:1fr}.out .big{font-size:56px}.cta{padding:26px 20px;border-radius:26px}.card{padding:18px}.calc{padding:16px}}
@media(prefers-reduced-motion:reduce){*{transition:none!important}}
"""

JS="""
(function(){
  var D=%%DATA%%, SUBJ=D.subjects, cur=D.start, p=D.p0;
  var $=function(i){return document.getElementById(i)};
  function sub(){return SUBJ[cur]}
  function clamp(v,a,b){v=Math.round(+v);if(isNaN(v))v=a;return Math.max(a,Math.min(b,v))}
  function calc(){
    var s=sub(), isM=s.kind==="mark";
    p=clamp(p,0,s.max);
    $("pin").max=s.max;$("pin").value=p;$("prng").max=s.max;$("prng").value=p;
    $("pmax").textContent=s.max;
    var out;
    if(isM){
      var m=s.marks.filter(function(x){return p>=x.frm&&p<=x.to})[0];
      $("res").textContent=m.mark;$("of").textContent="из 5";$("lbl").textContent="Отметка за экзамен";
      $("bar").style.width=(m.mark-1)/4*100+"%";
      var nx=s.marks.filter(function(x){return x.frm>p})[0];
      $("next").textContent=nx?"До отметки «"+nx.mark+"» не хватает "+(nx.frm-p)+" "+plural(nx.frm-p,"балла","баллов","баллов")+".":"Это максимальная отметка.";
      Array.prototype.forEach.call(document.querySelectorAll("[data-m]"),function(r){r.classList.toggle("cur",+r.dataset.m===m.mark)});
    }else{
      var t=s.scale[p];
      $("res").textContent=t;$("of").textContent="из 100";$("lbl").textContent="Тестовый балл";
      $("bar").style.width=t+"%";
      $("next").textContent=p<s.max?"Ещё один первичный балл даст "+(s.scale[p+1]-t)+" "+plural(s.scale[p+1]-t,"тестовый","тестовых","тестовых")+" ("+s.scale[p+1]+").":"Это максимальный результат.";
      Array.prototype.forEach.call(document.querySelectorAll("[data-p]"),function(r){r.classList.toggle("cur",+r.dataset.p===p)});
    }
    rev();
  }
  function plural(n,a,b,c){n=Math.abs(n);return n%10===1&&n%100!==11?a:(n%10>=2&&n%10<=4&&!(n%100>=12&&n%100<=14))?b:c}
  function rev(){
    var s=sub(); if(!$("tin"))return;
    if(s.kind==="mark"){
      var mk=clamp($("tin").value,2,5), x=s.marks.filter(function(q){return q.mark===mk})[0];
      $("tans").textContent="Нужно набрать от "+x.frm+" до "+x.to+" первичных баллов.";return;
    }
    var t=clamp($("tin").value,0,100), need=null;
    for(var i=0;i<s.scale.length;i++){if(s.scale[i]>=t){need=i;break}}
    $("tans").textContent=need===null?"Такого результата нет":"Нужно "+need+" "+plural(need,"первичный балл","первичных балла","первичных баллов")+(s.scale[need]!==t?" (даст "+s.scale[need]+")":"")+".";
  }
  $("pin").addEventListener("input",function(){p=$("pin").value;calc()});
  $("prng").addEventListener("input",function(){p=$("prng").value;calc()});
  $("minus").onclick=function(){p--;calc()};$("plus").onclick=function(){p++;calc()};
  if($("tin")) $("tin").addEventListener("input",rev);
  Array.prototype.forEach.call(document.querySelectorAll("[data-p]"),function(r){r.onclick=function(){p=+r.dataset.p;calc();$("pin").focus({preventScroll:true})}});
  if($("subj")){
    $("subj").addEventListener("change",function(){cur=$("subj").value;
      var s=sub(); document.querySelectorAll("[data-tbl]").forEach(function(t){t.hidden=t.dataset.tbl!==cur});
      if($("tin")){$("tin").value=s.kind==="mark"?5:80;$("tlbl").textContent=s.kind==="mark"?"Хочу отметку":"Хочу набрать (тестовых)";$("tin").max=s.kind==="mark"?5:100}
      p=Math.min(p,s.max);calc()});
  }
  calc();
})();
"""

def table_html(s,hidden=False):
    h=' hidden' if hidden else ''
    if s["kind"]=="mark":
        rows=''.join(f'<tr data-m="{m["mark"]}"><td><b>{m["mark"]}</b></td><td class="mono">{m["frm"]}–{m["to"]}</td></tr>' for m in s["marks"])
        return f'<table class="marks" data-tbl="{s["id"]}"{h}><thead><tr><th>Отметка</th><th>Первичные баллы</th></tr></thead><tbody>{rows}</tbody></table>'
    cells=''.join(f'<button type="button" data-p="{i}" aria-label="{i} первичных — {v} тестовых"><span>{i}</span><b>{v}</b></button>' for i,v in enumerate(s["scale"]))
    return f'<div class="tbl" data-tbl="{s["id"]}"{h}>{cells}</div>'

def faq_for(s):
    if s["kind"]=="mark":
        ms=s["marks"]
        q=[(f"Сколько баллов нужно для оценки «5» на ЕГЭ {s['by']}?",f"Для отметки «5» нужно набрать от {ms[3]['frm']} до {ms[3]['to']} первичных баллов из {s['max']}. Для «4» — от {ms[2]['frm']}, для «3» — от {ms[1]['frm']}."),
           ("Чем отличается первичный балл от отметки?","Первичный балл — это сумма баллов за верно выполненные задания. Отметка по пятибалльной шкале выставляется по таблице перевода: каждому диапазону первичных баллов соответствует своя отметка."),
           ("Есть ли тестовый балл у базовой математики?","Нет. Результат ЕГЭ по математике базового уровня выставляется только в виде отметки от 2 до 5. Тестовые баллы (до 100) есть у профильного уровня.")]
    else:
        sc=s["scale"]; th=[60,70,80,90,100]
        parts=[]
        for t in th:
            mp=min_primary(sc,t)
            if mp is not None: parts.append(f"для {t} — {mp} ({sc[mp]})")
        q=[(f"Как перевести первичные баллы ЕГЭ {s['by']} в тестовые?",f"Введите первичный балл в калькулятор выше или найдите его в таблице: максимальный первичный балл {s['max']}, ему соответствует 100 тестовых баллов. Шкала перевода у каждого предмета своя, здесь используется шкала {YEAR} года."),
           (f"Сколько первичных баллов нужно для 70, 80, 90 и 100 баллов {s['by']}?","Минимальное число первичных баллов (в скобках — тестовый балл, который это даёт): "+"; ".join(parts)+"."),
           ("Меняется ли шкала перевода из года в год?","Да. Рособрнадзор утверждает шкалу каждый год, и значения могут немного отличаться. Результат расчёта ориентировочный: официальный итог вы увидите в личном кабинете участника ЕГЭ."),
           ("Сохраняются ли введённые баллы?","Нет. Расчёт выполняется прямо в вашем браузере, введённые числа никуда не отправляются.")]
    return q

def page(kind,s=None):
    hub=kind=="hub"
    if hub:
        title=f"Калькулятор баллов ЕГЭ {YEAR}: перевод первичных баллов в тестовые"
        desc="Онлайн-калькулятор баллов ЕГЭ: переведите первичные баллы в тестовые по русскому языку, литературе, биологии, географии, физике, химии и информатике, а также в отметку по базовой математике. Таблицы шкал "+YEAR+" года."
        url=HUB_URL; h1=f"Калькулятор баллов ЕГЭ {YEAR}"
        lead="Выберите предмет, введите первичный балл и сразу увидите тестовый. Можно и наоборот: узнать, сколько первичных нужно для нужного результата."
        start=SUBJ[0]["id"]; sj=SUBJ[0]
    else:
        sj=s; start=s["id"]; url=s["url"]
        if s["kind"]=="mark":
            title=f"Перевод баллов ЕГЭ по математике (база) в оценку {YEAR}: калькулятор и таблица"
            desc=f"Калькулятор: сколько баллов нужно на ЕГЭ по математике базового уровня для оценки 3, 4 и 5. Таблица перевода первичных баллов (до {s['max']}) в отметку."
            h1="Перевод баллов ЕГЭ по математике (базовый уровень) в оценку"
        else:
            title=f"Перевод баллов ЕГЭ {s['by']} {YEAR}: калькулятор и таблица"
            desc=f"Калькулятор перевода первичных баллов ЕГЭ {s['by']} в тестовые. Максимум — {s['max']} первичных баллов (100 тестовых). Полная таблица шкалы {YEAR} года."
            h1=f"Перевод баллов ЕГЭ {s['by']}: первичные в тестовые"
        lead=("Введите первичный балл — калькулятор покажет "+("отметку." if s["kind"]=="mark" else "тестовый балл по шкале "+YEAR+" года.")+" Ниже полная таблица и ответы на частые вопросы.")
    canon=SITE+url
    data={"start":start,"p0":(10 if hub or sj["kind"]=="test" else 12),"subjects":{}}
    subs=SUBJ if hub else [sj]
    for x in subs:
        d={"kind":x["kind"],"max":x["max"]}
        if x["kind"]=="test": d["scale"]=x["scale"]
        else: d["marks"]=x["marks"]
        data["subjects"][x["id"]]=d
    if not hub: data["p0"]=min(data["p0"],sj["max"])
    faqs=faq_for(sj if not hub else SUBJ[0]) if not hub else [
        ("Как перевести первичные баллы ЕГЭ в тестовые?","Выберите предмет и введите первичный балл в калькулятор выше: он покажет тестовый балл по шкале Рособрнадзора "+YEAR+" года. Таблица шкалы приведена прямо под калькулятором."),
        ("Какие предметы есть в калькуляторе?","Русский язык, литература, биология, география, физика, химия, информатика (тестовые баллы до 100) и математика базового уровня (отметка от 2 до 5)."),
        ("Меняется ли шкала перевода из года в год?","Да. Рособрнадзор утверждает шкалу ежегодно, значения могут немного отличаться. Результат расчёта ориентировочный: официальный итог виден в личном кабинете участника ЕГЭ."),
        ("Сохраняются ли введённые баллы?","Нет. Расчёт выполняется в вашем браузере, введённые числа никуда не отправляются.")]
    # JSON-LD
    ld=[{"@context":"https://schema.org","@type":"BreadcrumbList","itemListElement":[
        {"@type":"ListItem","position":1,"name":"ЕГЭ_Map","item":SITE+"/"},
        {"@type":"ListItem","position":2,"name":"Калькулятор баллов ЕГЭ","item":SITE+HUB_URL}]+([] if hub else [{"@type":"ListItem","position":3,"name":sj["name"],"item":canon}])},
        {"@context":"https://schema.org","@type":"FAQPage","mainEntity":[{"@type":"Question","name":q,"acceptedAnswer":{"@type":"Answer","text":a}} for q,a in faqs]}]
    ld[0]["itemListElement"]=[x for x in ld[0]["itemListElement"]]
    # calculator markup
    select=""
    if hub:
        opts=''.join(f'<option value="{x["id"]}">{E(x["name"])}</option>' for x in SUBJ)
        select=f'<label class="l" for="subj">Предмет</label><select id="subj" class="sel">{opts}</select>'
    isM=(not hub and sj["kind"]=="mark")
    rev_lbl="Хочу отметку" if isM else "Хочу набрать (тестовых)"
    rev_val=5 if isM else 80
    rev_max=5 if isM else 100
    if hub: tables=''.join(table_html(x,hidden=(x["id"]!=start)) for x in SUBJ)
    else: tables=table_html(sj)
    others=''.join(f'<a href="{x["url"]}"{" class=on" if (not hub and x["id"]==sj["id"]) else ""}>{E(x["name"])}</a>' for x in SUBJ)
    faq_html=''.join(f'<details><summary>{E(q)}</summary><p>{E(a)}</p></details>' for q,a in faqs)
    tbl_title="Таблица перевода: первичные баллы → "+("отметка" if isM else "тестовые") if not hub else "Таблица перевода баллов"
    tbl_note=("Нажмите на строку, чтобы подставить значение в калькулятор." if not isM else "")
    page_html=f"""<!DOCTYPE html>
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
<style>{CSS}</style>
<script type="application/ld+json">{json.dumps(ld,ensure_ascii=False)}</script>
</head>
<body>
<header class="top"><div class="wrap">
  <a href="/" aria-label="ЕГЭ_Map — на главную"><img src="/logo-lockup.svg" alt="ЕГЭ_Map"></a>
  <a class="pill lime" href="/app.html?demo=1">Для учителей: демо-класс</a>
</div></header>
<main class="wrap">
  <nav class="crumbs" aria-label="Навигация"><a href="/">ЕГЭ_Map</a> / {'Калькулятор баллов ЕГЭ' if hub else '<a href="'+HUB_URL+'">Калькулятор баллов ЕГЭ</a> / '+E(sj["name"])}</nav>
  <section class="hero">
    <span class="tag">Шкала ЕГЭ {YEAR}</span>
    <h1>{E(h1)}</h1>
    <p class="lead">{E(lead)}</p>
    <div class="calc" role="group" aria-label="Калькулятор">
      {select}
      <div class="grid2">
        <div>
          <label class="l" for="pin">Первичный балл (0–<span id="pmax">{sj['max']}</span>)</label>
          <div class="stepper"><button type="button" id="minus" aria-label="Меньше">−</button><input id="pin" type="number" inputmode="numeric" min="0" max="{sj['max']}" value="{data['p0']}"><button type="button" id="plus" aria-label="Больше">+</button></div>
          <input id="prng" type="range" min="0" max="{sj['max']}" value="{data['p0']}" aria-label="Первичный балл, ползунок">
          <div class="hint">Сумма баллов за все задания по критериям оценивания.</div>
        </div>
        <div class="out" aria-live="polite">
          <div class="mono" id="lbl" style="font-size:11px;letter-spacing:.06em;text-transform:uppercase;color:var(--mut2)">{'Отметка за экзамен' if isM else 'Тестовый балл'}</div>
          <div><span class="big" id="res">0</span><span class="of" id="of">{'из 5' if isM else 'из 100'}</span></div>
          <div class="bar"><i id="bar"></i></div>
          <div class="next" id="next"></div>
        </div>
      </div>
      <div class="rev"><label class="l" id="tlbl" for="tin" style="margin:0">{rev_lbl}</label><input id="tin" type="number" inputmode="numeric" min="{2 if isM else 0}" max="{rev_max}" value="{rev_val}"><span class="ans" id="tans"></span></div>
    </div>
  </section>

  <section class="blk card">
    <h2>{tbl_title}</h2>
    <p class="hint" style="margin:0 0 14px">Слева в каждой ячейке — первичные баллы, справа — {'отметка' if isM else 'тестовые'}. {tbl_note}</p>
    {tables}
    <p class="hint" style="margin:14px 0 0">Шкала {YEAR} года (источник: шкалы перевода, утверждённые Рособрнадзором, <a href="https://fipi.ru" rel="noopener">ФИПИ</a>). Обновлено {UPDATED_RU} Расчёт ориентировочный, официальный результат вы увидите в личном кабинете участника экзамена.</p>
  </section>

  <section class="blk cta">
    <div>
      <h2>Вы учитель или репетитор?</h2>
      <p>В ЕГЭ_Map вносите баллы за пробники по заданиям, и приложение само переводит их по шкале, показывает зоны роста каждого ученика и класса и готовит отчёт для родителей. Три ученика — бесплатно.</p>
    </div>
    <div class="acts"><a class="pill lime" href="/app.html">Попробовать бесплатно</a><a class="pill ghost" style="background:transparent;color:#fff;box-shadow:inset 0 0 0 1.5px rgba(255,255,255,.4)" href="/app.html?demo=1">Посмотреть демо-класс</a></div>
  </section>

  <section class="blk faq card">
    <h2>Частые вопросы</h2>
    {faq_html}
  </section>

  <section class="blk">
    <h2>Другие предметы</h2>
    <div class="chips">{others}</div>
  </section>

  <footer class="ft">© ЕГЭ_Map · <a href="/">Для учителей</a> · <a href="/parents.html">Родителям</a> · <a href="/app.html?legal=privacy">Политика обработки данных</a>
  <div style="margin-top:8px">Калькулятор работает в вашем браузере: введённые данные не сохраняются и не передаются.</div></footer>
</main>
<script>{JS.replace('%%DATA%%',json.dumps(data,ensure_ascii=False,separators=(',',':')))}</script>
</body>
</html>
"""
    return url,page_html

out=[]
u,h=page("hub"); open(os.path.join(ROOT,u.lstrip('/')),'w',encoding='utf-8').write(h); out.append(u)
for s in SUBJ:
    u,h=page("s",s); open(os.path.join(ROOT,u.lstrip('/')),'w',encoding='utf-8').write(h); out.append(u)

# sitemap
urls=[("/","1.0","weekly"),("/parents.html","0.7","monthly"),(HUB_URL,"0.9","monthly")]+[(x["url"],"0.8","monthly") for x in SUBJ]
sm='<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'+''.join(f'  <url>\n    <loc>{SITE}{u}</loc>\n    <lastmod>{UPDATED_ISO}</lastmod>\n    <changefreq>{c}</changefreq>\n    <priority>{p}</priority>\n  </url>\n' for u,p,c in urls)+'</urlset>\n'
open(os.path.join(ROOT,'sitemap.xml'),'w',encoding='utf-8').write(sm)
print("\n".join(out))

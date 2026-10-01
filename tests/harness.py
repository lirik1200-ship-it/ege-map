import asyncio, json, sys, re, os
from playwright.async_api import async_playwright

HTML = open(os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','app.html'), encoding='utf-8').read()

FAKE_SUPABASE = r"""
window.__calls = [];
(function(){
  const db = {
    profiles: [{id:'u1', plan:'free', plan_expires_at:null, plan_base_limit:null, plan_topup_count:0, enabled_subjects:[]}],
    classes: [], students: [], exams: [], payments: []
  };
  let idc = 1;
  function chain(table){
    const st = {table, op:'select', filters:[], single:false, maybe:false, payload:null, order:null};
    const api = {};
    ['select','order','limit','in','neq','gt','lt','gte','lte','is','ilike','like'].forEach(m => api[m] = function(){ if(m==='order') st.order = arguments; return api; });
    api.eq = function(k,v){ st.filters.push([k,v]); return api; };
    api.insert = function(p){ st.op='insert'; st.payload=p; return api; };
    api.update = function(p){ st.op='update'; st.payload=p; return api; };
    api.upsert = function(p){ st.op='upsert'; st.payload=p; return api; };
    api.delete = function(){ st.op='delete'; return api; };
    api.single = function(){ st.single=true; return api; };
    api.maybeSingle = function(){ st.maybe=true; return api; };
    api.then = function(res, rej){
      try{
        window.__calls.push({table, op:st.op, payload:st.payload, filters:st.filters});
        let rows = db[table] || [];
        const match = r => st.filters.every(([k,v]) => r[k] === v);
        let out;
        if(st.op==='insert'){
          const arr = Array.isArray(st.payload) ? st.payload : [st.payload];
          const added = arr.map(p => Object.assign({id: table+(idc++), share_token:'tok'+idc}, p));
          db[table] = rows.concat(added); out = added;
        } else if(st.op==='upsert'){
          out = [st.payload]; db[table] = rows.concat([st.payload]);
        } else if(st.op==='update'){
          rows.filter(match).forEach(r => Object.assign(r, st.payload)); out = rows.filter(match);
        } else if(st.op==='delete'){
          db[table] = rows.filter(r => !match(r)); out = [];
        } else { out = rows.filter(match); }
        let data = out;
        if(st.single || st.maybe) data = out[0] || null;
        res({data, error:null});
      }catch(e){ res({data:null, error:{message:String(e)}}); }
    };
    return api;
  }
  const user = {id:'u1', email:'teacher@test.ru'};
  window.__db = db;
  window.supabase = { createClient(){ return {
    from: chain,
    rpc: (n,a)=>{ window.__calls.push({rpc:n,args:a}); return Promise.resolve({data:null,error:null}); },
    auth: {
      getSession: ()=>Promise.resolve({data:{session: window.__noSession?null:{user}}, error:null}),
      getUser: ()=>Promise.resolve({data:{user}, error:null}),
      signInWithPassword: (a)=>{ window.__calls.push({signIn:a}); return Promise.resolve({data:{}, error:null}); },
      signUp: (a)=>{ window.__calls.push({signUp:a}); return Promise.resolve({data:{session:null}, error:null}); },
      resetPasswordForEmail: (e,o)=>{ window.__calls.push({reset:e,o}); return Promise.resolve({error:null}); },
      signOut: ()=>Promise.resolve({error:null}),
      updateUser: ()=>Promise.resolve({error:null}),
      onAuthStateChange: ()=>({data:{subscription:{unsubscribe(){}}}})
    },
    functions: { invoke: (n,o)=>{ window.__calls.push({fn:n,body:o&&o.body}); return Promise.resolve({data:{action:'https://yoomoney.ru/quickpay/confirm', fields:{sum:'1'}}, error:null}); } }
  }; } };
})();
"""

CHART_STUB = "window.Chart=function(ctx,cfg){this.cfg=cfg;window.__charts=(window.__charts||0)+1;};Chart.prototype.destroy=function(){};Chart.prototype.update=function(){};Chart.register=function(){};Chart.defaults={font:{},plugins:{legend:{labels:{}}},color:'',borderColor:''};"

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path='/opt/pw-browsers/chromium_headless_shell-1194/chrome-linux/headless_shell') if False else await p.chromium.launch()
        ctx = await b.new_context(viewport={'width':1280,'height':900})
        page = await ctx.new_page()
        errors = []
        page.on('pageerror', lambda e: errors.append('PAGEERROR: '+str(e)))
        page.on('console', lambda m: errors.append('CONSOLE.'+m.type+': '+m.text) if m.type in ('error',) else None)

        async def route(r):
            u = r.request.url
            if u.startswith('file://') or u == 'http://app.test/':
                return await r.fulfill(body=HTML, content_type='text/html')
            if 'tailwindcss' in u: return await r.fulfill(body='window.tailwind={};', content_type='application/javascript')
            if 'chart.js' in u: return await r.fulfill(body=CHART_STUB, content_type='application/javascript')
            if 'supabase-js' in u: return await r.fulfill(body=FAKE_SUPABASE, content_type='application/javascript')
            if 'html2pdf' in u: return await r.fulfill(body='window.html2pdf=function(){return {set(){return this},from(){return this},save(){return Promise.resolve()},outputPdf(){return Promise.resolve(new Blob())}}};', content_type='application/javascript')
            if 'fonts.g' in u: return await r.fulfill(body='', content_type='text/css')
            return await r.abort()
        await page.route('**/*', route)
        await page.goto('http://app.test/')
        await page.wait_for_timeout(1200)

        res = {}
        res['screen_after_boot'] = await page.evaluate("state.screen+' / mode='+state.mode")
        res['boot_errors'] = list(errors)

        # все предметы/экзамены: переключение на каждый и отрисовка списка, группы, ввода, тарифов
        exams = await page.evaluate("Object.keys(EXAMS)")
        res['exams'] = exams
        per = {}
        for ex in exams:
            before = len(errors)
            try:
                await page.evaluate(f"switchExam('{ex}')")
                for scr in ['screen-list','screen-group','screen-entry','screen-pricing','screen-account','screen-help']:
                    await page.evaluate(f"route('{scr}')")
            except Exception as e:
                errors.append(f'EXC {ex}: {e}')
            per[ex] = errors[before:]
        res['per_exam_errors'] = {k:v for k,v in per.items() if v}


        # ---------- глубокий прогон с данными ----------
        SEED = """
        (function(){
          const tasks = KNOWN_TASKS.filter(t=>!EGE_TOPICS[t].derived);
          let seed = 12345;
          const rnd = ()=>{ seed=(seed*1103515245+12345)%2147483648; return seed/2147483648; };
          const cls = {id:'c_'+state.exam, name:'К-'+state.exam, exam_type:state.exam};
          window.__db.classes = window.__db.classes.filter(c=>c.exam_type!==state.exam).concat([cls]);
          window.__db.students = window.__db.students.filter(s=>s.exam_type!==state.exam);
          window.__db.exams = window.__db.exams.filter(e=>!String(e.student_id).startsWith('s_'+state.exam+'_'));
          for(let i=1;i<=15;i++){
            const sid='s_'+state.exam+'_'+i;
            window.__db.students.push({id:sid,name:'К'+String(i).padStart(2,'0'),share_token:'t'+sid,class_id:cls.id,exam_type:state.exam});
            for(let e=0;e<4;e++){
              const lvl=.3+i/15*.6+(rnd()-.5)*.1, results={}, essay={};
              tasks.forEach(t=>{ const m=maxScoreFor(t); results[t]= m<=1?(rnd()<lvl?1:0):Math.round(m*lvl); });
              CRITERIA_KEYS.forEach(k=>{ essay[k]=Math.round(ESSAY_CRITERIA[k].max*lvl); });
              const d=new Date(); d.setDate(d.getDate()-100+e*30);
              window.__db.exams.push({student_id:sid,exam_date:d.toISOString().slice(0,10),results,essay,comment:null});
            }
          }
        })();
        """
        BAD = re.compile(r"NaN|undefined|Infinity|\[object")
        deep_problems = {}
        for ex in exams:
            before = len(errors)
            probs = []
            try:
                await page.evaluate(f"switchExam('{ex}')")
                await page.evaluate(SEED)
                await page.evaluate("reloadData()")
                await page.evaluate("applyExamScope()")
                await page.evaluate("route('screen-list')")
                txt = await page.evaluate("document.querySelector('#screen-list').innerText")
                if BAD.search(txt): probs.append('list: '+BAD.search(txt).group(0))
                n = await page.evaluate("state.students.length")
                if n != 15: probs.append(f'students in scope={n}')
                ids = await page.evaluate("state.students.map(s=>s.id)")
                for sid in ids[:15]:
                    await page.evaluate(f"openStudent('{sid}')")
                    t = await page.evaluate("document.querySelector('#screen-student').innerText")
                    m = BAD.search(t)
                    if m: probs.append(f'student {sid}: {m.group(0)}'); break
                    pct = await page.evaluate("[...document.querySelectorAll('#screen-student [style*=\"width:\"]')].map(e=>parseFloat(e.style.width)).filter(v=>v>100.01).length")
                    if pct: probs.append(f'student {sid}: bar>100% x{pct}'); break
                await page.evaluate("route('screen-group')")
                t = await page.evaluate("document.querySelector('#screen-group').innerText")
                m = BAD.search(t)
                if m: probs.append('group: '+m.group(0))
                await page.evaluate("route('screen-entry')")
                t = await page.evaluate("document.querySelector('#screen-entry').innerText")
                m = BAD.search(t)
                if m: probs.append('entry: '+m.group(0))
            except Exception as e:
                probs.append('EXC '+str(e)[:200])
            new_err = errors[before:]
            if probs or new_err: deep_problems[ex] = probs + new_err
        res['deep_problems'] = deep_problems

        print(json.dumps(res, ensure_ascii=False, indent=1))
        await b.close()

asyncio.run(main())

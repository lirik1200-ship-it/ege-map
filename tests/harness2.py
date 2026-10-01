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


async def newpage(p, nosession=False, url='http://app.test/', init=''):
    b = await p.chromium.launch()
    ctx = await b.new_context(viewport={'width':1280,'height':900})
    page = await ctx.new_page()
    errors = []
    page.on('pageerror', lambda e: errors.append('PAGEERROR: '+str(e)))
    page.on('console', lambda m: errors.append('CONSOLE.'+m.type+': '+m.text) if m.type=='error' else None)
    async def route(r):
        u = r.request.url
        if u.startswith('http://app.test'): return await r.fulfill(body=HTML, content_type='text/html')
        if 'tailwindcss' in u: return await r.fulfill(body='window.tailwind={};', content_type='application/javascript')
        if 'chart.js' in u: return await r.fulfill(body=CHART_STUB, content_type='application/javascript')
        if 'supabase-js' in u: return await r.fulfill(body=FAKE_SUPABASE, content_type='application/javascript')
        if 'html2pdf' in u: return await r.fulfill(body='window.html2pdf=function(){return {set(){return this},from(){return this},save(){return Promise.resolve()}}};', content_type='application/javascript')
        if 'fonts.g' in u: return await r.fulfill(body='', content_type='text/css')
        return await r.abort()
    await page.route('**/*', route)
    await page.add_init_script("HTMLFormElement.prototype.submit=function(){window.__submitted={action:this.action,fields:[...this.elements].map(e=>e.name+'='+e.value)};};" + ("window.__noSession=true;" if nosession else "") + init)
    await page.goto(url)
    await page.wait_for_timeout(1000)
    return b, page, errors

async def main():
    out = {}
    async with async_playwright() as p:
        # 1. Тарифы/оплата, учитель на free
        b, page, errors = await newpage(p)
        await page.evaluate("route('screen-pricing')")
        out['pricing_free'] = await page.evaluate("""({
          buy:[...document.querySelectorAll('.buy-btn')].map(b=>b.dataset.buy+':'+b.textContent.trim()),
          topup: !!document.querySelector('#topup-buy'),
          txt: document.querySelector('#screen-pricing').innerText.slice(0,700)
        })""")
        await page.click('.buy-btn[data-buy="standard"]')
        await page.wait_for_timeout(300)
        out['buy_standard'] = await page.evaluate("({calls: window.__calls.filter(c=>c.fn), submitted: window.__submitted})")
        await page.select_option('#topup-qty', '3')
        out['topup_label'] = await page.evaluate("document.querySelector('#topup-buy').textContent")
        await page.click('#topup-buy'); await page.wait_for_timeout(300)
        out['topup_call'] = await page.evaluate("window.__calls.filter(c=>c.fn).slice(-1)[0]")
        out['err_pricing'] = errors
        await b.close()

        # 2. Тариф standard активен -> нижние пакеты недоступны
        b, page, errors = await newpage(p)
        await page.evaluate("window.__db.profiles[0]={id:'u1',plan:'standard',plan_expires_at:'2027-06-30T20:59:59Z',plan_base_limit:30,plan_topup_count:2,enabled_subjects:[]}")
        await page.evaluate("(async()=>{state.plan=await api.loadPlan();renderChrome();route('screen-pricing')})()")
        await page.wait_for_timeout(300)
        out['pricing_standard'] = await page.evaluate("({plan:state.plan.id,limit:state.plan.limit,topup:state.plan.topup,btns:[...document.querySelectorAll('#screen-pricing .grid > div')].map(d=>d.innerText.replace(/\\s+/g,' ').slice(0,90))})")
        out['err_std'] = errors
        await b.close()

        # 3. Возврат с оплаты
        b, page, errors = await newpage(p)
        await page.evaluate("window.__db.payments=[{label:'L-1',status:'paid'}]")
        await page.evaluate("history.pushState(null,'','/?paid=L-1')")
        await page.evaluate("checkReturnFromPayment()")
        await page.wait_for_timeout(800)
        out['return_paid'] = await page.evaluate("[...document.querySelectorAll('div')].filter(d=>/Оплата прошла|Проверяем/.test(d.textContent)&&d.children.length==0).map(d=>d.textContent)")
        out['url_after'] = await page.evaluate("location.search")
        out['err_return'] = errors
        await b.close()

        # 4. Регистрация / вход
        b, page, errors = await newpage(p, nosession=True)
        out['auth_screen'] = await page.evaluate("state.screen+' mode='+state.mode")
        out['auth_tabs'] = await page.evaluate("[...document.querySelectorAll('.auth-tab')].map(b=>b.textContent)")
        await page.click('.auth-tab[data-auth-mode="signup"]')
        out['signup_btn'] = await page.evaluate("document.querySelector('#auth-submit, #auth-btn, #screen-auth button[type=submit]')?.textContent")
        ids = await page.evaluate("[...document.querySelectorAll('#screen-auth input')].map(i=>i.id+':'+i.type)")
        out['auth_inputs'] = ids
        await b.close()

        # 5. Ссылка ученика с неверным токеном
        b, page, errors = await newpage(p, url='http://app.test/?s=bad-token')
        out['share_bad'] = await page.evaluate("state.screen+' | '+(document.querySelector('#error-detail')?.textContent||'')")
        out['err_share'] = errors
        await b.close()

        # 6. Лимит бесплатного тарифа: 3 из 3
        b, page, errors = await newpage(p)
        await page.evaluate("""(()=>{
          window.__db.classes=[{id:'c1',name:'11А',exam_type:'ege'}];
          window.__db.students=['А1','А2','А3'].map((n,i)=>({id:'s'+i,name:n,share_token:'t'+i,class_id:'c1',exam_type:'ege'}));
        })()""")
        await page.evaluate("reloadData().then(()=>{applyExamScope();renderStudentList();})")
        await page.wait_for_timeout(400)
        out['limit_ui'] = await page.evaluate("({add: !!document.querySelector('#add-students'), txt: document.querySelector('#screen-list').innerText.replace(/\\s+/g,' ').slice(0,420)})")
        out['err_limit'] = errors
        await b.close()

        # 7. Отчёт родителям
        b, page, errors = await newpage(p)
        await page.evaluate("""(()=>{
          window.__db.classes=[{id:'c1',name:'11А',exam_type:'ege'}];
          window.__db.students=[{id:'s0',name:'А1',share_token:'t0',class_id:'c1',exam_type:'ege'}];
          const r={};KNOWN_TASKS.forEach(t=>{r[t]=1});
          window.__db.exams=[{student_id:'s0',exam_date:'2026-09-10',results:r,essay:{},comment:null},{student_id:'s0',exam_date:'2026-09-20',results:r,essay:{},comment:null}];
        })()""")
        await page.evaluate("reloadData().then(()=>{applyExamScope();openStudent('s0');})")
        await page.wait_for_timeout(500)
        await page.click('#report-btn'); await page.wait_for_timeout(600)
        out['report'] = await page.evaluate("(document.querySelector('#report-root, .report, #screen-report')?.innerText||document.body.innerText).slice(0,200).replace(/\\s+/g,' ')")
        out['err_report'] = errors
        await b.close()

    print(json.dumps(out, ensure_ascii=False, indent=1))

asyncio.run(main())

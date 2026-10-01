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
    rpc: (n,a)=>{ window.__calls.push({rpc:n,args:a}); return Promise.resolve({data:n==='get_student_report'?{name:'К-07',exam_type:'ege',exams:[]}:null,error:null}); },
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
            if u.startswith('file://') or u.startswith('http://app.test/'):
                return await r.fulfill(body=HTML, content_type='text/html')
            if 'tailwindcss' in u: return await r.fulfill(body='window.tailwind={};', content_type='application/javascript')
            if 'chart.js' in u: return await r.fulfill(body=CHART_STUB, content_type='application/javascript')
            if 'supabase-js' in u: return await r.fulfill(body=FAKE_SUPABASE, content_type='application/javascript')
            if 'html2pdf' in u: return await r.fulfill(body='window.html2pdf=function(){return {set(){return this},from(){return this},save(){return Promise.resolve()},outputPdf(){return Promise.resolve(new Blob())}}};', content_type='application/javascript')
            if 'fonts.g' in u: return await r.fulfill(body='', content_type='text/css')
            return await r.abort()
        await page.route('**/*', route)
        await page.goto('http://app.test/?s=11111111-1111-1111-1111-111111111111')
        await page.wait_for_timeout(1200)

        res={}
        res['screen']=await page.evaluate("state.screen+' / '+state.mode")
        res['text']=(await page.evaluate("document.querySelector('#screen-student').innerText"))[:400]
        res['bot']=await page.evaluate("(document.querySelector('#screen-student a[href*=ege_map_bot]')||{}).href")
        res['errors']=errors
        print(json.dumps(res,ensure_ascii=False,indent=1))
        await b.close()
asyncio.run(main())

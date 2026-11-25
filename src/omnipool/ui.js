const $=(s,r=document)=>r.querySelector(s);let TXT={};fetch('/texte.json').then(r=>r.json()).then(j=>{TXT=j;render&&S&&render()}).catch(()=>{});
function h(t,a,...k){const e=document.createElement(t);for(const[x,v]of Object.entries(a||{})){if(x==="on")for(const[ev,f]of Object.entries(v))e.addEventListener(ev,f);else if(x==="class")e.className=v;else if(v!==false&&v!=null)e.setAttribute(x,v===true?"":v)}
for(const c of k.flat())e.append(c&&c.nodeType?c:document.createTextNode(c==null?"":String(c)));return e}
async function api(p,b){const r=await fetch("/api/"+p,{method:b===undefined?"GET":"POST",headers:{"X-Omnipool":"1","Content-Type":"application/json"},body:b===undefined?undefined:JSON.stringify(b)});return r.json()}
const EX=window.EXTRA||[];const TABS=["Assistant","Overview","Keys & Providers","Models","Connect","Settings","Events",...EX.map(x=>x.name)];let tab=Math.max(0,TABS.indexOf(sessionStorage.getItem("aob.tab")||"Assistant")),S=null,M=null,tmp={};
const I=k=>TXT[k]?h('span',{class:'info',tabindex:'0','data-tip':TXT[k]},'?'):'';
const ago=t=>!t?"-":(s=>s<90?Math.round(s)+" s":s<5400?Math.round(s/60)+" min":Math.round(s/3600)+" h")(Date.now()/1000-t);
const pct=(a,b)=>b?Math.round(100*a/b):0;
function bars(rows,fmt){const mx=Math.max(1,...rows.map(r=>r[1]));return h("div",{},rows.map(r=>h("div",{class:"row",style:"margin:3px 0"},h("span",{style:"width:130px"},r[0]),h("div",{class:"bar",style:"flex:1"},h("i",{style:"width:"+pct(r[1],mx)+"%"})),h("span",{class:"mu"},fmt?fmt(r):r[1]))))}
function head(){$("#pLauf").textContent=S.lauf.laeuft?"Run active":"Last run "+ago(S.lauf.ts);$("#pLauf").className="pill "+(S.lauf.laeuft?"warn":"ok");
$("#pBusy").textContent=S.busy?"Machine busy":"";$("#pBusy").className="pill warn"+(S.busy?"":" hide");$("#pAus").textContent=S.aus?"OFF":"";$("#pAus").className="pill bad"+(S.aus?"":" hide");$("#bAus").textContent=S.aus?"Back on":"All off"}
function uebersicht(){const ks={};S.keys.forEach(k=>ks[k.status]=(ks[k.status]||0)+1);const B=S.bericht;
return h("div",{},
h("section",{class:"hero"},
h("p",{class:"hero-eyebrow"},"API-OMNI-BRAIN: Local AI API Testing & Routing"),
h("h1",{class:"hero-title"},"One local API for every AI app."),
h("p",{class:"hero-sub"},"API-OMNI-BRAIN finds working free AI keys, tests them, picks the right model for each request, and routes everything through one local address. Stop juggling providers, endpoints, and rate limits."),
h("div",{class:"hero-steps"},
h("div",{class:"hero-step"},h("span",{class:"hero-num"},"1"),h("div",{},h("b",{},"Scan"),h("span",{},"Find free or existing keys on this machine."))),
h("div",{class:"hero-step"},h("span",{class:"hero-num"},"2"),h("div",{},h("b",{},"Connect"),h("span",{},"Point your app at one local address."))),
h("div",{class:"hero-step"},h("span",{class:"hero-num"},"3"),h("div",{},h("b",{},"Watch"),h("span",{},"See models, costs, and errors as they happen.")))),
h("p",{class:"hero-note"},"Runs on this machine. Only the AI providers you use need internet.")),
h("div",{class:"g"},
h("div",{class:"card"},h("h3",{},"Keys"),h("div",{class:"big"},S.keys.length),h("div",{class:"mu"},Object.entries(ks).map(([a,b])=>b+" "+a).join(" · ")||"no scan yet")),
h("div",{class:"card"},h("h3",{},"Models in catalog"),h("div",{class:"big"},S.modelle),h("div",{class:"mu"},S.geprobt+" content-verified"),bars(S.faehigkeiten.map(f=>[f[0],f[1]]))),
h("div",{class:"card"},h("h3",{},"Applications, last 24 h"),B.anwendungen.length?bars(B.anwendungen.map(a=>[a.app,a.n]),r=>{const a=B.anwendungen.find(x=>x.app===r[0]);return a.n+" requests, "+pct(a.ok,a.n)+" % ok, Ø "+a.lat+" s"}):h("div",{class:"di"},"no requests yet")),
h("div",{class:"card"},h("h3",{},"Providers, last 24 h"),B.anbieter.length?bars(B.anbieter.map(a=>[a.provider,a.tokens]),r=>{const a=B.anbieter.find(x=>x.provider===r[0]);return a.n+" requests, "+a.tokens+" Tokens"}):h("div",{class:"di"},"no requests yet"))),
h("div",{class:"g",style:"margin-top:14px"},h("div",{class:"card"},h("h3",{},"The Brain: Organs"),B.organe.map(o=>h("div",{class:"org"},h("b",{},o.name),h("span",{class:"mu"},o.info+(o.ts?" · "+ago(o.ts):"")))),
h("div",{class:"di",style:"margin-top:8px"},"Honestly: a well-made set of scripts and proto-AI parts (rules, bandit, judge model), not a learned mind. Needles and 0.8B are planned.")),
h("div",{class:"card"},h("h3",{},"Best choice per class"),h("table",{},h("tr",{},h("th",{},"Class"),h("th",{},"Model"),h("th",{},"p"),h("th",{},"n")),
Object.entries(S.wahl).flatMap(([k,r])=>r.slice(0,2).map((x,i)=>h("tr",{},h("td",{},i?"":k),h("td",{},x[0]+"/"+x[1].split("/").pop()),h("td",{},x[2]),h("td",{},x[3])))))),
B.ruhende.length?h("div",{class:"card"},h("h3",{},"Resting (immune system)"),B.ruhende.map(r=>h("div",{class:"org"},h("span",{},r.modell),h("span",{class:"mu"},r.grund+", still "+r.noch_s+" s")))):""),
h("div",{class:"card",style:"margin-top:var(--space-5)"},h("h3",{},"Get Started"),h("p",{class:"mu",style:"margin:0 0 var(--space-2)"},"Add a key, then connect your app. API-OMNI-BRAIN takes care of model choice and routing."),h("div",{class:"overview-actions"},
h("button",{class:"b",on:{click:()=>go("Keys & Providers")}},"Add Keys"),
h("button",{class:"s",on:{click:()=>go("Connect")}},"Connect Application"))))}
async function pruefen(){const t=$("#tok").value.trim();if(!t)return;tmp.res=await api("token/check",{token:t,provider:$("#prov").value});render()}
function keys(){const r=tmp.res,E=tmp.ent;
return h("div",{},h("div",{class:"card"},h("h3",{},"Add token"),h("div",{class:"row"},h("input",{type:"password",id:"tok",placeholder:"Paste token (never displayed or logged)",autocomplete:"off"}),
h("select",{id:"prov"},h("option",{value:"auto"},"Auto-detect provider"),S.anbieter.map(a=>h("option",{value:a.id},a.label+(a.art==="eigener"?" (custom)":"")))),h("button",{class:"b",on:{click:pruefen}},"Check")),
r?h("div",{},r.unbekannt?h("div",{class:"s-limit"},"Provider not recognized. Create as new provider below (enter address)."):
h("div",{class:r.ok?"s-ok":"s-invalid"},(r.ok?"Valid: ":"Rejected: ")+(r.provider||"")+" · Hash "+r.hash8+" · "+(r.modelle||0)+" Models"+(r.fehler?" · "+r.fehler:"")),
r.ok?h("button",{class:"b",on:{click:async()=>{const x=await api("token/save",{token:$("#tok").value.trim(),provider:r.provider});tmp={msg:x.duplicate?"Already exists ("+x.slot+")":"Saved in "+x.slot};load()}}},"Save"):""):"",
tmp.msg?h("div",{class:"s-ok"},tmp.msg):"",h("div",{class:"di"},"Key file: "+S.keys_file+" · Values stay there (mode 600); the interface shows only the slot and hash.")),
h("div",{class:"card",style:"margin-top:14px"},h("h3",{},"New or third-party provider (video, image, audio, search, custom services …)"),
h("div",{class:"row"},h("input",{type:"text",id:"base",placeholder:"API base URL, e.g. https://api.example.com/v1"}),h("input",{type:"text",id:"lab",placeholder:"Name (optional)"}),
h("button",{class:"b",on:{click:async()=>{tmp.ent=await api("anbieter/entdecke",{base:$("#base").value,token:$("#tok").value.trim(),label:$("#lab").value});render()}}},"Discover")),
E?(E.fehler?h("div",{class:"s-invalid"},E.fehler):h("div",{},h("div",{class:"s-ok"},"Found: "+E.id+" · Access "+E.auth.header+" · List "+E.liveness+" · "+E.modelle.length+" Models"),
h("div",{},"Capabilities: "+E.faehigkeiten.join(", ")+(E.hinweis?" ("+E.hinweis+")":"")),h("div",{class:"di"},"Only chat is tested for content; video/image/audio are checked for availability and access (jobs consume credit)."),
h("button",{class:"b",on:{click:async()=>{await api("anbieter/speichern",{profile:E,token:$("#tok").value.trim()});tmp={msg:"Provider "+E.id+" created"};load()}}},"Create and scan"))):""),
h("div",{class:"card",style:"margin-top:14px"},h("h3",{},"Existing Keys"),h("table",{},h("tr",{},["Slot","Provider","Hash","Status","Models","Checked","In Routing",""].map(x=>h("th",{},x))),
S.keys.map(k=>h("tr",{},h("td",{},k.slot),h("td",{},k.provider),h("td",{},k.hash8),h("td",{class:"s-"+k.status},k.status),h("td",{},k.n_models),h("td",{},ago(k.checked)),
h("td",{},h("input",{type:"checkbox",checked:!k.aus,on:{change:async e=>{await api("settings",{slot:k.slot,aus:!e.target.checked});load()}}})),
h("td",{},h("button",{class:"b",on:{click:async()=>{if(confirm("Key "+k.slot+" ("+k.hash8+") remove from the key file? It will be backed up first."))await api("token/remove",{slot:k.slot,hash8:k.hash8,eigener:S.anbieter.some(a=>a.id===k.provider&&a.art==="eigener")}),load()}}},"Remove"))))))) }
function modelle(){
  if(!M)return h("div",{class:"card",style:"padding:var(--space-6);text-align:center"},h("div",{class:"pill warn"},"Loading models …"));
  const f=(tmp.f||"").toLowerCase();
  const c=tmp.cap||"";
  const sortCol=tmp.sc||"provider";
  const sortDir=tmp.sd||"asc";
  const rawCaps=[...new Set(M.map(m=>m.faehigkeit))].sort();
  const capLabel=cap=>{
    const map={"chat":"Chat (Text)","code":"Code","embedding":"Embeddings","image":"Image Generation","video":"Video","audio":"Audio","search":"Search","tool":"Tool-Calling","vision":"Vision","reasoning":"Reasoning","unknown":"Unknown","sicherheit":"Safety"};
    return map[cap]||cap;
  };
  const classKeys=["code","json","de","reason","long","tool"];
  const classLabel={code:"Code",json:"JSON",de:"German",reason:"Reasoning",long:"Long Text",tool:"Tools"};
  let rows=M.filter(m=>(!c||m.faehigkeit===c)&&(m.provider+"/"+m.model).toLowerCase().includes(f));
  rows.sort((a,b)=>{
    let av=a[sortCol], bv=b[sortCol];
    if(sortCol==="provider"){av=a.provider;bv=b.provider}
    else if(sortCol==="model"){av=a.model;bv=b.model}
    else if(sortCol==="faehigkeit"){av=a.faehigkeit;bv=b.faehigkeit}
    else if(sortCol==="status"){av=a.status;bv=b.status}
    else if(classKeys.includes(sortCol)){
      av=a.klassen[sortCol]?a.klassen[sortCol][0]:-1;
      bv=b.klassen[sortCol]?b.klassen[sortCol][0]:-1;
    }
    if(av<bv)return sortDir==="asc"?-1:1;
    if(av>bv)return sortDir==="asc"?1:-1;
    return 0;
  });
  rows=rows.slice(0,400);
  const thClick=(col)=>()=>{tmp.sc=col;tmp.sd=tmp.sc===col&&tmp.sd==="asc"?"desc":"asc";render()};
  const statusPill=s=>s==="ok"?h("span",{class:"pill ok"},"Available"):s==="nicht_verfuegbar"?h("span",{class:"pill bad"},"Unavailable"):h("span",{class:"pill warn"},({neu:"New (untested)",fehler:"Failing",keine_klasse:"No class yet"})[s]||s);
  const classBar=(m,key)=>{
    const v=m.klassen[key];
    if(!v||v[0]<0)return h("td",{class:"mu",style:"text-align:center"},h("span",{style:"color:var(--ink-subtle)"},"–"));
    const p=v[0], n=v[1];
    const w=Math.max(0,Math.min(100,Math.round(100*p)));
    const hue=p>=0.7?120:p>=0.4?45:0;
    const color=`hsl(${hue},70%,45%)`;
    const bg=`hsl(${hue},70%,15%)`;
    return h("td",{style:"white-space:nowrap;text-align:center"},
      h("div",{style:"display:inline-flex;align-items:center;gap:6px;min-width:110px"},
        h("div",{class:"bar",style:"flex:1;height:6px;max-width:80px;background:"+bg},h("i",{style:`width:${w}%;background:${color};transition:width 300ms cubic-bezier(.2,.7,.3,1)`})),
        h("span",{class:"mu",style:"font-family:var(--font-mono);font-size:11px;color:var(--ink-dim)"},p.toFixed(2)+" / "+n)
      )
    );
  };
  const capChips=rawCaps.map(cap=>h("button",{type:"button",class:"pill "+(c===cap?"ok":""),style:"font-size:11px;padding:3px 10px",on:{click:()=>{tmp.cap=c===cap?"":cap;render()}},title:"Filter: "+capLabel(cap)},capLabel(cap)));
  return h("div",{},
    h("div",{class:"row",style:"gap:8px;flex-wrap:wrap;align-items:center;margin-bottom:12px"},
      h("input",{type:"text",placeholder:"Filter: Provider / Model …",value:tmp.f||"",style:"flex:1;min-width:200px",on:{input:e=>{tmp.f=e.target.value;clearTimeout(tmp.t);tmp.t=setTimeout(render,250)}},title:"Text search in provider and model names"}),
      h("span",{class:"info",tabindex:"0","data-tip":"Show only models with this primary capability. No multi-select needed – each model has exactly one primary capability."},"?"),
      h("div",{style:"display:flex;flex-wrap:wrap;gap:6px"},capChips)
    ),
    rows.length?h("div",{style:"overflow:auto"},h("table",{style:"width:100%"},
      h("thead",{},h("tr",{},[
        ["Provider","provider"],["Model","model"],["Capability","faehigkeit"],["Status","status"],
        ["Code (Success Probability)","code"],["JSON (Number of Tests)","json"],["German (Success Probability)","de"],["Reasoning (Success Probability)","reason"],["Long Text (Success Probability)","long"],["Tools (Success Probability)","tool"]
      ].map(([label,col])=>h("th",{style:"cursor:pointer;user-select:none;white-space:nowrap",on:{click:thClick(col)}},
        h("span",{style:"display:flex;align-items:center;gap:4px"},label,
          tmp.sc===col?h("span",{style:"font-size:10px;color:var(--ac)"},tmp.sd==="asc"?"▲":"▼"):""
        )
      )))),
      h("tbody",{},rows.map((m,i)=>h("tr",{style:i%2===0?"background:transparent":"background:rgba(255,255,255,.02)"},
        h("td",{style:"font-weight:500;color:var(--ink)"},m.provider),
        h("td",{style:"font-family:var(--font-mono);color:var(--ink-dim)"},m.model),
        h("td",{},h("span",{class:"pill",style:"font-size:11px;background:var(--info-bg);color:var(--info);border-color:rgba(96,165,250,.4)"},capLabel(m.faehigkeit))),
        h("td",{},statusPill(m.status),m.gone>=3?h("span",{class:"mu",style:"font-size:11px;margin-left:6px"},"(omitted)"):""),
        classBar(m,"code"),classBar(m,"json"),classBar(m,"de"),classBar(m,"reason"),classBar(m,"long"),classBar(m,"tool")
      )))
    )):h("div",{class:"empty",style:"margin-top:16px"},
      h("svg",{viewBox:"0 0 24 24",fill:"none",stroke:"currentColor",strokeWidth:"1.5"},h("path",{d:"M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"})),
      h("p",{},c?"No model with the capability „"+capLabel(c)+"“ found.":"No model matches the filter."),
      h("p",{class:"hint"},"Reset the filter or clear the search text to show all models.")
    ),
    h("div",{class:"di",style:"margin-top:12px;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px"},
      h("span",{},rows.length+" of "+M.filter(m=>!c||m.faehigkeit===c).length+" models shown (max. 400)"),
      h("span",{},"Click a column header to sort · Color bars: green ≥ 0.7 · yellow ≥ 0.4 · red < 0.4")
    )
  );
}
const SNIP={claude_code:(u,k)=>"export ANTHROPIC_BASE_URL="+u+"\nexport ANTHROPIC_API_KEY="+k+"\nexport ANTHROPIC_MODEL=omnipool-auto\n# free models are considerably weaker than Claude: useful, for example, for the fast slot:\n# export ANTHROPIC_DEFAULT_HAIKU_MODEL=omnipool-auto",
aider:(u,k)=>"aider --openai-api-base "+u+"/v1 --openai-api-key "+k+" --model openai/omnipool-code"};
function snip(a,u,k){return(SNIP[a]||((u,k)=>"Base address: "+u+"/v1\nAPI-Key:       "+k+"\nModel:        omnipool-auto   (or omnipool-code, -json, -de, -reason, -long, -tool, or provider/model)\n# Choose the 'OpenAI-compatible / Custom' provider and enter these three values"))(u,k)}
function verbinden(){
  const H=S.harness;
  const apps=Object.entries(H);
  if(!apps.length){
    return h("div",{},
      h("div",{class:"card",style:"text-align:center;padding:var(--space-6)"},
        h("h3",{},"No application yet"),
        h("p",{class:"mu",style:"margin:var(--space-3) 0"},"Add your first application below."),
        h("div",{class:"row",style:"justify-content:center;margin-top:var(--space-4)"},
          h("input",{type:"text",id:"na",placeholder:"Name, e.g. meinbot",style:"min-width:220px"}),
          h("button",{class:"b",on:{click:async()=>{const n=$("#na").value.trim();if(!n)return;await api("settings",{harness:{name:n,an:true,klasse:"auto"}});load()}}},"Add")
        )
      )
    );
  }
  const satz="Look at "+S.url+"/integrate and integrate API-OMNI-BRAIN into your workflow.";
  return h("div",{},
    h("div",{class:"card",style:"margin-bottom:var(--space-4)"},
      h("h3",{},"Easiest way: let your agent do it"),
      h("p",{class:"mu"},"Tell Claude Code, Hermes, Grokbot or any other agent this sentence. It reads the guide, registers itself and changes its own settings. You only approve it once here."),
      h("div",{class:"row"},h("code",{},satz),
        h("button",{class:"b s",on:{click:async e=>{await navigator.clipboard.writeText(satz);e.target.textContent="Copied"}}},"Copy"))),
    h("div",{class:"di",style:"margin-bottom:var(--space-3)"},
      "Each application gets its own key. API-OMNI-BRAIN never edits another program's configuration: either the agent changes its own settings (see above), or you copy a block below yourself."
    ),
    h("div",{class:"g",style:"margin-top:var(--space-3)"},
      apps.map(([name,v])=>{
        const key=v.key||"";
        const showKey=tmp["show_"+name]===true;
        const testOpen=tmp["test_"+name]===true;
        const cfg=snip(name,S.url,showKey?key:key.slice(0,10)+"…");
        const exampleReq=`curl -s -X POST "${S.url}/v1/chat/completions" \\
  -H "Authorization: Bearer ${showKey?key:"<IHR_ANWENDUNGS_SCHLÜSSEL>"}" \\
  -H "Content-Type: application/json" \\
  -d '{"model":"omnipool-auto","messages":[{"role":"user","content":"Hello, short test message"}],"max_tokens":50}'`;
        const steps=v.steps||[
          "Copy the configuration block below.",
          "Paste it into the application's settings (environment variables, config file, or UI).",
          "Restart the application for the changes to take effect.",
          "Test the connection with the „Show example request“ button."
        ];
        return h("div",{class:"card",style:"min-height:auto"},
          h("div",{class:"card-header"},
            h("h3",{},v.label||name),
            h("div",{class:"row",style:"gap:var(--space-2)"},
              h("label",{style:"display:flex;align-items:center;gap:6px;cursor:pointer"},
                h("input",{type:"checkbox",checked:v.an,on:{change:async e=>{await api("settings",{harness:{name:name,an:e.target.checked,klasse:v.klasse}});load()}}}),
                " shared"
              ),
              h("select",{on:{change:async e=>{await api("settings",{harness:{name:name,an:v.an,klasse:e.target.value}});load()}}},
                ["auto","code","json","de","reason","long","tool"].map(x=>h("option",{value:x,selected:x===v.klasse},x==="auto"?"Class: automatic":"always "+x))
              )
            )
          ),
          h("div",{class:"card-content"},
            h("div",{style:"margin-bottom:var(--space-4)"},
              h("p",{style:"font-weight:600;margin:0 0 var(--space-2) 0;font-size:var(--fs-sm)"},"Step by step"),
              h("ol",{style:"margin:0;padding-left:var(--space-5);color:var(--ink-dim);font-size:var(--fs-sm);line-height:var(--lh-relaxed)"},
                steps.map(s=>h("li",{},s))
              )
            ),
            h("div",{style:"margin-bottom:var(--space-4)"},
              h("div",{style:"display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;flex-wrap:wrap;gap:var(--space-2)"},
                h("p",{style:"font-weight:600;margin:0;font-size:var(--fs-sm)"},"Configuration"),
                h("div",{class:"row",style:"gap:6px"},
                  h("button",{class:"b s",style:"padding:4px 10px;font-size:var(--fs-xs)",on:{click:()=>{tmp["show_"+name]=!showKey;render()}}},showKey?"Hide key":"Show keys"),
                  h("button",{class:"b",style:"padding:4px 10px;font-size:var(--fs-xs)",on:{click:async()=>{
                    const full=snip(name,S.url,key);
                    await navigator.clipboard.writeText(full);
                    showToast("Configuration copied");
                  }}},"Copy"),
                  h("button",{class:"b s",style:"padding:4px 10px;font-size:var(--fs-xs)",on:{click:()=>{tmp["test_"+name]=!testOpen;render()}}},testOpen?"Hide example":"Show example request")
                )
              ),
              h("pre",{style:"margin:0;max-height:280px"},cfg),
              testOpen?h("div",{style:"margin-top:var(--space-3);padding:var(--space-3);background:var(--bg);border:1px solid var(--line);border-radius:var(--radius);animation:fadeIn var(--trans-fast) var(--ease)"},
                h("div",{style:"display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;flex-wrap:wrap;gap:var(--space-2)"},
                  h("p",{style:"font-weight:600;margin:0;font-size:var(--fs-sm)"},"Example request (display only)"),
                  h("button",{class:"b s",style:"padding:2px 8px;font-size:var(--fs-xs)",on:{click:async()=>{
                    await navigator.clipboard.writeText(exampleReq);
                    showToast("Example request copied");
                  }}},"Copy")
                ),
                h("pre",{style:"margin:0;max-height:200px;font-size:var(--fs-xs)"},exampleReq),
                h("p",{class:"di",style:"margin:var(--space-2) 0 0 0"},"This request is not sent. It only shows the format the application sends to API-OMNI-BRAIN.")
              ):""
            )
          )
        );
      })
    ),
    h("div",{class:"card",style:"margin-top:var(--space-4)"},
      h("h3",{},"Add another application"),
      h("div",{class:"row",style:"gap:var(--space-3)"},
        h("input",{type:"text",id:"na",placeholder:"Name, e.g. meinbot",style:"flex:1;min-width:200px"}),
        h("button",{class:"b",on:{click:async()=>{const n=$("#na").value.trim();if(!n)return;await api("settings",{harness:{name:n,an:true,klasse:"auto"}});load()}}},"Add")
      )
    ),
    h("div",{class:"card",style:"margin-top:var(--space-4)"},
      h("h3",{},"Pass through (Video, Image, Audio, Embeddings, Search …)"),
      h("pre",{},"curl -H 'Authorization: Bearer <your app key>' "+S.url+"/x/<provider>/<path of the provider API>"),
      h("div",{class:"di"},"API-OMNI-BRAIN uses an available provider key (with rotation and cooldown on limit) and returns the response unchanged. Only the application itself initiates jobs that cost credit.")
    )
  );
}
function einst(){const e=S.einstellungen;return h("div",{class:"g"},h("div",{class:"card"},h("h3",{},"Planner"),
h("div",{class:"row"},"Run all (min)",h("input",{type:"number",id:"lm",value:e.lauf_min,style:"width:90px"}),I("lauf_min")),
h("div",{class:"row"},"Models per run",h("input",{type:"number",id:"mm",value:e.max_modelle,style:"width:90px"}),I("max_modelle")),
h("div",{class:"row"},"NVIDIA priority (0 to 0.5)",h("input",{type:"number",id:"vn",step:"0.05",value:(e.vorrang||{nvidia:0.1}).nvidia,style:"width:90px"}),I("nvidia_priority")),
h("div",{class:"row"},h("label",{},h("input",{type:"checkbox",id:"me",checked:e.melden})),"Report results to AI evaluation system 'modellwahl' (only where available)"),I("melden"),
h("div",{class:"row"},"Key file",h("input",{type:"text",id:"kf",value:e.keys_file||S.keys_file,style:"flex:1"})),
h("div",{class:"row"},"Port (after restart)",h("input",{type:"number",id:"po",value:e.port,style:"width:110px"})),
h("button",{class:"b",on:{click:async()=>{await api("settings",{lauf_min:+$("#lm").value,max_modelle:+$("#mm").value,vorrang:{nvidia:+$("#vn").value},melden:$("#me").checked,keys_file:$("#kf").value,port:+$("#po").value});tmp.msg="Saved";load()}}},"Save"),tmp.msg?h("span",{class:"s-ok"}," "+tmp.msg):""),
h("div",{class:"card"},h("h3",{},"Security"),h("div",{class:"di"},"127.0.0.1 only. UI calls need the X-Omnipool header; applications need their own key. Keys are never displayed or logged (slot and hash only). Paid providers and paid models are not used (OpenRouter :free only). Emergency stop: button above, or file ~/.cache/omnipool/AUS.")),
h("div",{class:"card"},h("h3",{},"Advanced settings"),h("div",{class:"di"},"Additional options for advanced users. Here you can make special configurations not needed for daily use.")))}
function ereig(){const e=S.bericht.ereignisse;return h("div",{class:"card"},h("h3",{},"System events"),e.length?h("table",{},e.map(x=>h("tr",{},h("td",{class:"mu"},ago(x.ts)),h("td",{},["drift","radar_fehler","quarantaene_still"].includes(x.art)?"⚠️":"ℹ️"),h("td",{},x.text)))):h("div",{class:"empty",style:"padding:var(--space-6);text-align:center"},
h("svg",{viewBox:"0 0 24 24",fill:"none",stroke:"currentColor",strokeWidth:"1.5"},h("path",{d:"M12 9v2m0 4h.01m-6.73 2h13.46c1.5 0 2.25-1.68 1.73-3L13 7c-1.5-2-6-2-7.5 0l-6.22 6.78c-.52.85.22 1.98 1.73 1.98z"})),
h("p",{},"No system events available."),
h("p",{class:"hint"},"Events are updated on the next run.")))}
function showToast(msg){
  let el=document.getElementById("toast");
  if(!el){
    el=h("div",{id:"toast",style:"position:fixed;bottom:24px;right:24px;z-index:200;background:var(--bg-elev);border:1px solid var(--ac);color:var(--ac);padding:10px 16px;border-radius:var(--radius);box-shadow:var(--shadow-3);font-size:var(--fs-sm);font-weight:600;opacity:0;transform:translateY(10px);transition:all var(--trans-base) var(--ease)"});
    document.body.appendChild(el);
  }
  el.textContent=msg;
  el.style.opacity="1";
  el.style.transform="translateY(0)";
  clearTimeout(el._t);
  el._t=setTimeout(()=>{el.style.opacity="0";el.style.transform="translateY(10px)"},2200);
}
/* an application asked to be connected (POST /v1/register): the user decides here, nothing is active before */
function anfragen(){
  const p=Object.entries(S.harness||{}).filter(([n,v])=>v.angemeldet&&!v.an);
  if(!p.length)return h("div",{});
  return h("div",{class:"card",style:"border-color:var(--ac);margin-bottom:var(--space-4)"},
    h("h3",{},"An application wants to use API-OMNI-BRAIN"),
    p.map(([n,v])=>h("div",{class:"row"},
      h("b",{},v.label||n),
      h("span",{class:"mu"},(v.scope&&v.scope.length)?"would like to hand over: "+v.scope.join(", "):"no scope given"),
      h("button",{class:"b",on:{click:async()=>{await api("settings",{harness:{name:n,an:true,klasse:v.klasse||"auto"}});load()}}},"Approve"),
      h("button",{class:"b s",on:{click:async()=>{await api("settings",{harness:{name:n,an:false,klasse:v.klasse||"auto",ablehnen:true}});load()}}},"Deny"))));
}
function assistent(){return window.ASSIST?window.ASSIST.view():h("div",{class:"card"},"The assistant could not be loaded.")}
/* One stable shell: the banner slot and the nav are built once; main is only rebuilt when the tab changes or the data really changed. */
const BAN=h("div",{id:"ban"});let banKey="";
function banner(){const k=JSON.stringify(Object.entries(S.harness||{}).filter(([n,v])=>v.angemeldet&&!v.an));if(k===banKey)return;banKey=k;BAN.replaceChildren(anfragen())}
const VIEWS={"Assistant":assistent,"Overview":uebersicht,"Keys & Providers":keys,"Models":modelle,"Connect":verbinden,"Settings":einst,"Events":ereig};
const tname=()=>TABS[tab];
function navbar(){const n=$("#nav");if(n.children.length!==TABS.length)n.replaceChildren(...TABS.map((t,i)=>h("button",{on:{click:()=>go(i)}},t)));[...n.children].forEach((b,i)=>b.classList.toggle("on",i===tab))}
function go(x){const was=tab;tab=typeof x==="string"?TABS.indexOf(x):x;if(tab<0)tab=0;try{sessionStorage.setItem("aob.tab",tname())}catch(e){}
  if(tname()==="Models"&&!M)api("modelle").then(r=>{M=r;if(tname()==="Models")render()});render(tab!==was)}
function render(fresh){if(!S)return;head();banner();navbar();const m=$("#main"),y=window.scrollY;m.classList.toggle("fx",!!fresh);
  const v=(VIEWS[tname()]||(EX.find(x=>x.name===tname())||{fn:uebersicht}).fn)();m.replaceChildren(BAN,v);window.scrollTo(0,fresh?0:y)}
let FP="",lastAct=0;["pointerdown","keydown","wheel"].forEach(e=>addEventListener(e,()=>{lastAct=Date.now()},{passive:true}));
/* wahl = the router's current picks, re-drawn with jitter on every call: left out of the fingerprint, else every poll would look like a change and redraw the page */
/* auto=true is the background poll: it re-renders only if the data actually changed, never while the user is interacting */
async function load(auto){const s=await api("status");let m=M;if(tname()==="Models")m=await api("modelle");
  const first=!S,fp=JSON.stringify(s,(k,v)=>k==="wahl"?undefined:v)+(tname()==="Models"?JSON.stringify(m):"");S=s;M=m;
  if(auto&&!first&&(fp===FP||tname()==="Assistant")){FP=fp;head();banner();return}FP=fp;render(first)}
window.goTab=go;window.refreshStatus=()=>load();
$("#bAsk").onclick=()=>{go("Assistant");window.ASSIST&&window.ASSIST.fresh()};
$("#bScan").onclick=async()=>{await api("lauf",{});showToast("Scan started");load()};
$("#bAus").onclick=async()=>{await api("aus",{aus:!S.aus});showToast(S.aus?"Back on":"All off");load()};
load();
const POLL=["Overview","Keys & Providers","Connect","Events","Assistant"];
setInterval(()=>{if(document.hidden||Date.now()-lastAct<5000||!POLL.includes(tname()))return;const a=document.activeElement;if(a&&["INPUT","SELECT","TEXTAREA"].includes(a.tagName))return;if(String(getSelection()).length)return;load(true)},6000);

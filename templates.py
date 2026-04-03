"""HTML templates for scanner and flip analyzer pages."""

SCANNER_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>CS2 Arbitrage Bot</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Segoe UI',system-ui,sans-serif;background:#0a0e17;color:#e1e4e8;min-height:100vh;display:flex}
.sidebar{width:280px;background:#0d1117;border-right:1px solid #21262d;padding:20px;overflow-y:auto;flex-shrink:0;height:100vh;position:sticky;top:0}
.sidebar h2{font-size:14px;color:#8b949e;margin-bottom:16px}
.fg{margin-bottom:14px}
.fg label{display:block;font-size:11px;color:#8b949e;text-transform:uppercase;letter-spacing:.5px;margin-bottom:5px}
.fg select,.fg input{width:100%;padding:7px 9px;border-radius:6px;border:1px solid #30363d;background:#161b22;color:#e1e4e8;font-size:13px;outline:none}
.fg select:focus,.fg input:focus{border-color:#58a6ff}
.fr{display:flex;gap:8px;align-items:center}
.fr input{flex:1}
.fr .sep{color:#484f58;font-size:12px}
.tag-box{display:flex;flex-wrap:wrap;gap:4px;padding:6px 8px;border-radius:6px;border:1px solid #30363d;background:#161b22;min-height:34px}
.tag{display:inline-flex;align-items:center;gap:3px;padding:2px 7px;border-radius:4px;background:#21262d;font-size:11px;color:#c9d1d9}
.tag .rm{cursor:pointer;color:#f85149;font-weight:bold}
.tag-box input{border:0;background:transparent;color:#e1e4e8;outline:none;font-size:12px;flex:1;min-width:50px}
.flow-label{text-align:center;padding:10px;margin-bottom:14px;border-radius:8px;background:#161b22;border:1px solid #21262d;font-size:12px;color:#8b949e}
.flow-label strong{color:#3fb950}
.flow-label .arrow{color:#58a6ff;margin:0 6px}

.content{flex:1;overflow-y:auto;height:100vh}
.header{background:linear-gradient(135deg,#1a1f2e,#0d1117);border-bottom:1px solid #21262d;padding:14px 24px;display:flex;align-items:center;justify-content:space-between;position:sticky;top:0;z-index:10}
.header h1{font-size:20px;font-weight:700;background:linear-gradient(90deg,#58a6ff,#3fb950);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.ha{display:flex;gap:10px;align-items:center}
.dot{width:8px;height:8px;border-radius:50%;display:inline-block;margin-right:4px}
.dot.active{background:#3fb950;box-shadow:0 0 8px #3fb95066}
.dot.idle{background:#8b949e}
.dot.scanning{background:#d29922;animation:pulse 1s infinite}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.4}}
.btn{padding:7px 14px;border-radius:6px;border:1px solid #30363d;background:#21262d;color:#c9d1d9;cursor:pointer;font-size:13px;font-weight:500;transition:all .15s}
.btn:hover{background:#30363d;border-color:#58a6ff}
.btn:disabled{opacity:.5;cursor:not-allowed}
.btn-primary{background:#238636;border-color:#2ea043;color:#fff}
.btn-primary:hover{background:#2ea043}

.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;padding:16px 24px}
.sc{background:#161b22;border:1px solid #21262d;border-radius:8px;padding:14px}
.sc .l{font-size:11px;color:#8b949e;text-transform:uppercase;letter-spacing:.5px}
.sc .v{font-size:24px;font-weight:700;margin-top:2px}
.sc .v.g{color:#3fb950}.sc .v.b{color:#58a6ff}.sc .v.y{color:#d29922}.sc .v.p{color:#bc8cff}

.main{padding:0 24px 24px}
table{width:100%;border-collapse:collapse}
th{text-align:left;padding:8px 10px;font-size:10px;color:#8b949e;text-transform:uppercase;letter-spacing:.5px;border-bottom:1px solid #21262d;background:#161b22}
td{padding:9px 10px;font-size:13px;border-bottom:1px solid #21262d}
tr:hover td{background:#161b2288}
.tw{background:#0d1117;border:1px solid #21262d;border-radius:8px;overflow:hidden}

.pb{display:inline-block;padding:2px 8px;border-radius:12px;font-size:12px;font-weight:600}
.pb.hi{background:#23292f;color:#3fb950}
.pb.md{background:#2a2412;color:#d29922}
.mt{display:inline-flex;align-items:center;gap:4px;padding:3px 8px;border-radius:4px;font-size:11px;font-weight:600;text-transform:uppercase;text-decoration:none;cursor:pointer;transition:all .15s}
.mt:hover{filter:brightness(1.3)}
.mt.float{background:#1a3a2a;color:#3fb950}
.mt.empire{background:#2a1a3a;color:#bc8cff}
.il{color:#e1e4e8;text-decoration:none;transition:color .15s}
.il:hover{color:#58a6ff;text-decoration:underline}
.im{font-size:11px;color:#484f58;margin-top:1px}

.trend-up{color:#3fb950}.trend-stable{color:#58a6ff}.trend-down{color:#f85149}.trend-pumped{color:#f0883e}

.es{text-align:center;padding:48px 20px;color:#8b949e}
.es .icon{font-size:40px;margin-bottom:10px}
.es p{font-size:13px;max-width:380px;margin:0 auto;line-height:1.5}

.lp{margin-top:16px;background:#0d1117;border:1px solid #21262d;border-radius:8px;padding:12px;max-height:160px;overflow-y:auto;font-family:'Cascadia Code','Fira Code',monospace;font-size:11px;color:#8b949e}
.le{padding:2px 0}.le .t{color:#484f58}.le.found{color:#3fb950}.le.scan{color:#58a6ff}.le.error{color:#f85149}
</style>
</head>
<body>

<div class="sidebar">
  <h2>&#9776; Filters</h2>

  <div class="flow-label">
    <strong>Empire</strong> <span class="arrow">&#8594;</span> Buy <span class="arrow">&#8594;</span> 7d lock <span class="arrow">&#8594;</span> Sell <span class="arrow">&#8594;</span> <strong>CSFloat</strong>
  </div>

  <div class="fg">
    <label>Min Price / Max Price ($)</label>
    <div class="fr">
      <input type="number" id="minPrice" value="10" min="0" step="1">
      <span class="sep">&ndash;</span>
      <input type="number" id="maxPrice" value="200" min="0" step="1">
    </div>
  </div>

  <div class="fg">
    <label>Min ROI / Max ROI (%)</label>
    <div class="fr">
      <input type="number" id="minRoi" value="2" min="0" step="0.5">
      <span class="sep">&ndash;</span>
      <input type="number" id="maxRoi" value="1000" min="0" step="1">
    </div>
  </div>

  <div class="fg">
    <label>Min CSFloat Sales (7 day)</label>
    <input type="number" id="minVolume" value="5" min="0" step="1">
  </div>

  <div class="fg">
    <label>Min Score</label>
    <input type="number" id="minLiquidity" value="0" min="0" step="1">
  </div>

  <div class="fg">
    <label>Blacklist</label>
    <div class="tag-box" id="bb">
      <span class="tag">battle-scarred<span class="rm" onclick="removeTag(this)">&times;</span></span>
      <span class="tag">sticker<span class="rm" onclick="removeTag(this)">&times;</span></span>
      <span class="tag">capsule<span class="rm" onclick="removeTag(this)">&times;</span></span>
      <span class="tag">case<span class="rm" onclick="removeTag(this)">&times;</span></span>
      <span class="tag">graffiti<span class="rm" onclick="removeTag(this)">&times;</span></span>
      <span class="tag">patch<span class="rm" onclick="removeTag(this)">&times;</span></span>
      <input type="text" id="bi" placeholder="add..." onkeydown="addTag(event)">
    </div>
  </div>

  <button class="btn btn-primary" style="width:100%;margin-top:8px" onclick="triggerScan()">Scan Now</button>
</div>

<div class="content">
  <div class="header">
    <h1>CS2 Arbitrage Bot</h1>
    <div class="ha">
      <span class="dot idle" id="dot"></span>
      <span id="st" style="font-size:13px">Idle</span>
    </div>
  </div>

  <div class="stats">
    <div class="sc"><div class="l">Opportunities</div><div class="v g" id="cnt">-</div></div>
    <div class="sc"><div class="l">Best Profit</div><div class="v b" id="bp">-</div></div>
    <div class="sc"><div class="l">Total Scans</div><div class="v y" id="sc2">0</div></div>
    <div class="sc"><div class="l">All-Time Finds</div><div class="v p" id="tf">0</div></div>
  </div>

  <div class="main">
    <div class="tw">
      <table>
        <thead><tr>
          <th>#</th>
          <th>Item</th>
          <th>Empire Buy</th>
          <th>CSFloat Sell</th>
          <th>Net %</th>
          <th>Net $</th>
          <th>Trend</th>
          <th>7d/30d Avg</th>
          <th>Pump</th>
          <th>Sales 7d</th>
          <th>Score</th>
        </tr></thead>
        <tbody id="tb"></tbody>
      </table>
      <div class="es" id="es">
        <div class="icon">&#128269;</div>
        <p>Set filters and hit <strong>Scan Now</strong>. Buys on Empire below CSFloat true value, checks trend stability, pump detection, and liquidity.</p>
      </div>
    </div>

    <div class="lp" id="lp">
      <div class="le scan"><span class="t">[--:--:--]</span> Ready. Empire &#8594; CSFloat arbitrage scanner.</div>
    </div>
  </div>
</div>

<script>
function getBlacklist(){return Array.from(document.querySelectorAll('#bb .tag')).map(t=>t.textContent.replace('\u00d7','').trim())}
function removeTag(e){e.parentElement.remove()}
function addTag(e){if(e.key!=='Enter')return;const v=e.target.value.trim().toLowerCase();if(!v)return;const s=document.createElement('span');s.className='tag';s.innerHTML=v+'<span class="rm" onclick="removeTag(this)">&times;</span>';e.target.parentElement.insertBefore(s,e.target);e.target.value=''}

function getFilters(){return{min_price:parseFloat(document.getElementById('minPrice').value)||10,max_price:parseFloat(document.getElementById('maxPrice').value)||200,min_roi:parseFloat(document.getElementById('minRoi').value)||2,max_roi:parseFloat(document.getElementById('maxRoi').value)||1000,min_volume:parseInt(document.getElementById('minVolume').value)||0,min_liquidity:parseInt(document.getElementById('minLiquidity').value)||0,blacklist:getBlacklist()}}

function addLog(m,c=''){const p=document.getElementById('lp');const d=document.createElement('div');d.className='le '+c;d.innerHTML='<span class="t">['+new Date().toLocaleTimeString()+']</span> '+m;p.appendChild(d);p.scrollTop=p.scrollHeight}

function setStatus(s){document.getElementById('dot').className='dot '+s;document.getElementById('st').textContent=s==='scanning'?'Scanning...':s==='active'?'Active':'Idle'}

function trendBadge(t,pump){
  const cls='trend-'+(t||'stable');
  const icon=t==='up'?'&#9650;':t==='down'?'&#9660;':t==='pumped'?'&#9888;':'&#9644;';
  return '<span class="'+cls+'">'+icon+' '+t+'</span>';
}

async function triggerScan(){
  setStatus('scanning');
  addLog('Scanning Empire listings vs CSFloat prices...','scan');
  const f=getFilters();
  addLog('$'+f.min_price+'-$'+f.max_price+' | ROI '+f.min_roi+'%+ | Min '+f.min_volume+' sales/7d','scan');
  try{
    const r=await fetch('/api/scan',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({filters:f})});
    const d=await r.json();
    addLog('Done. <strong>'+d.found+'</strong> opportunities found.',d.found>0?'found':'scan');
    await fetchResults();
  }catch(e){addLog('Error: '+e.message,'error');setStatus('idle')}
}

async function fetchResults(){
  try{
    const r=await fetch('/api/results');
    const d=await r.json();
    setStatus(d.scanning?'scanning':d.results.length>0?'active':'idle');
    document.getElementById('cnt').textContent=d.results.length;
    document.getElementById('sc2').textContent=d.scan_count;
    document.getElementById('tf').textContent=d.total_opportunities;
    const tb=document.getElementById('tb');
    const es=document.getElementById('es');
    if(!d.results.length){tb.innerHTML='';es.style.display='block';document.getElementById('bp').textContent='-';return}
    es.style.display='none';
    document.getElementById('bp').textContent=d.results[0].net_profit_pct+'%';
    tb.innerHTML=d.results.map((r,i)=>{
      const pumpColor=Math.abs(r.pump_pct)>10?'trend-pumped':'';
      return '<tr>'+
        '<td>'+(i+1)+'</td>'+
        '<td><a href="'+r.buy_url+'" target="_blank" class="il">'+r.name+'</a></td>'+
        '<td><a href="'+r.buy_url+'" target="_blank" class="mt empire">$'+r.buy_price.toFixed(2)+' &#8599;</a></td>'+
        '<td><a href="'+r.sell_url+'" target="_blank" class="mt float">$'+r.sell_price.toFixed(2)+' &#8599;</a></td>'+
        '<td><span class="pb '+(r.net_profit_pct>=5?'hi':'md')+'">'+r.net_profit_pct+'%</span></td>'+
        '<td style="color:#3fb950">$'+r.net_profit_dollar.toFixed(2)+'</td>'+
        '<td>'+trendBadge(r.trend,r.pump_pct)+'</td>'+
        '<td><span class="im">7d: $'+(r.avg_7d||'-')+'</span><br><span class="im">30d: $'+(r.avg_30d||'-')+'</span></td>'+
        '<td class="'+pumpColor+'">'+r.pump_pct+'%</td>'+
        '<td>'+r.sales_7d+'</td>'+
        '<td>'+r.score+'</td>'+
        '</tr>';
    }).join('');
  }catch(e){}
}

setInterval(fetchResults,5000);
fetchResults();
</script>
</body>
</html>"""


FLIP_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Flip Analyzer</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
:root{
  --bg:#070a11;
  --bg-2:#0d1320;
  --panel:#0f1726;
  --panel-2:#121c2e;
  --line:#1f2a3f;
  --line-soft:#182236;
  --text:#d8e0ef;
  --muted:#7d8aa6;
  --accent:#49c2ff;
  --accent-2:#6cf2c5;
  --good:#4fe39a;
  --warn:#f2b04f;
  --bad:#ff7373;
}
body{
  font-family:'Inter','Segoe UI',system-ui,sans-serif;
  background:
    radial-gradient(1200px 700px at 12% -10%, #1d325a55 0%, transparent 55%),
    radial-gradient(900px 600px at 110% 10%, #154d5f44 0%, transparent 45%),
    var(--bg);
  color:var(--text);
  min-height:100vh;
  padding:32px 24px;
}
a{color:#8eb0da;text-decoration:none;transition:color .15s}
a:hover{color:#c7ddff}
.nav{margin-bottom:28px;font-size:12px;color:var(--muted);letter-spacing:.3px}
.container{
  max-width:980px;
  margin:0 auto;
  background:linear-gradient(180deg, #0a111d88 0%, #0a111d44 100%);
  border:1px solid var(--line-soft);
  border-radius:14px;
  padding:20px 20px 18px 20px;
  box-shadow:0 20px 60px #00000055;
}
h1{
  font-size:20px;
  font-weight:700;
  color:#e8f0ff;
  margin-bottom:24px;
  letter-spacing:-.2px;
}
.input-row{display:flex;gap:10px;margin-bottom:20px}
.input-row input{flex:1;padding:10px 14px;border-radius:8px;border:1px solid var(--line);background:var(--panel);color:var(--text);font-size:13px;outline:none;transition:border-color .15s,box-shadow .15s}
.input-row input:focus{border-color:#2a4f79;box-shadow:0 0 0 3px #1c355322}
.input-row button{padding:10px 22px;border-radius:8px;border:1px solid #2a4f79;background:linear-gradient(180deg,#12304f,#0f2740);color:#d7ebff;font-size:13px;font-weight:600;cursor:pointer;white-space:nowrap;transition:all .15s;letter-spacing:.3px}
.input-row button:hover{filter:brightness(1.08)}
.input-row button:disabled{opacity:.3;cursor:not-allowed}
.result{display:none}
.verdict-box{padding:18px 20px;border-radius:8px;margin-bottom:16px;border:1px solid #222}
.verdict-box.BUY{background:#0a1a0f;border-color:#1a3a20}
.verdict-box.SKIP{background:#1a0f0f;border-color:#3a1a1a}
.verdict-box.RISKY{background:#1a1508;border-color:#3a2e12}
.verdict-box.BORDERLINE{background:#151515;border-color:#2a2a2a}
.verdict-label{font-size:20px;font-weight:700;margin-bottom:3px;letter-spacing:-.3px}
.verdict-label.BUY{color:#4a9}
.verdict-label.SKIP{color:#c55}
.verdict-label.RISKY{color:#c93}
.verdict-label.BORDERLINE{color:#777}
.verdict-detail{font-size:13px;color:#777}
.cards{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-bottom:16px}
.card{background:linear-gradient(180deg,var(--panel) 0%, var(--panel-2) 100%);border:1px solid var(--line);border-radius:10px;padding:14px}
.card h3{font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.8px;margin-bottom:10px}
.card .row{display:flex;justify-content:space-between;padding:4px 0;font-size:12px;border-bottom:1px solid var(--line-soft)}
.card .row:last-child{border:0}
.card .row .label{color:#555}
.card .row .val{font-weight:500;color:#999}
.card .row .val.pos{color:#4a9}
.card .row .val.neg{color:#c55}
.card .row .val.warn{color:#c93}
.liq-box{background:linear-gradient(180deg,var(--panel) 0%, var(--panel-2) 100%);border:1px solid var(--line);border-radius:10px;padding:16px;margin-bottom:16px;display:flex;align-items:center;gap:20px}
.liq-score{font-size:38px;font-weight:700;min-width:70px;text-align:center}
.liq-score.A{color:#4a9}.liq-score.B{color:#69a}.liq-score.C{color:#c93}.liq-score.D{color:#b74}.liq-score.F{color:#c55}
.liq-details{flex:1;font-size:12px;color:#555;line-height:1.9}
.liq-grade{font-size:16px;font-weight:600;margin-left:8px;color:#888}
.pump-box{background:linear-gradient(180deg,var(--panel) 0%, var(--panel-2) 100%);border:1px solid var(--line);border-radius:10px;padding:16px;margin-bottom:16px}
.pump-box h3{font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.8px;margin-bottom:10px}
.history{margin-top:20px}
.history-item{background:#151515;border:1px solid #1e1e1e;border-radius:6px;padding:10px 14px;margin-bottom:6px;cursor:pointer;transition:border-color .15s}
.history-item:hover{border-color:#333}
.history-item .name{font-size:13px;font-weight:500;color:#aaa}
.history-item .meta{font-size:11px;color:#555;margin-top:2px}
.wear-tabs{display:flex;gap:6px;margin:10px 0 18px 0}
.wear-btn{padding:7px 12px;border-radius:6px;border:1px solid var(--line);background:var(--panel);color:var(--muted);font-size:12px;cursor:pointer;transition:all .15s;font-weight:600}
.wear-btn:hover{border-color:#2a4f79;color:#b7caea}
.wear-btn.active{background:#10263f;border-color:#2f78bf;color:#8fd0ff}
.time-btn{cursor:pointer}
.time-btn:hover{border-color:#555 !important;color:#999 !important}
.time-btn.active{border-color:#4a9 !important;color:#4a9 !important}
/* Tab navigation */
.tabs-nav{display:flex;gap:4px;margin-bottom:24px;border-bottom:1px solid var(--line);padding-bottom:0}
.tab-btn{padding:9px 18px;border:none;background:none;color:var(--muted);font-size:13px;font-weight:600;cursor:pointer;border-bottom:2px solid transparent;margin-bottom:-1px;transition:color .15s,border-color .15s;letter-spacing:.2px}
.tab-btn:hover{color:#b9c8e2}
.tab-btn.active{color:var(--accent-2);border-bottom-color:var(--accent-2)}
.tab-panel{display:none}
.tab-panel.active{display:block}
/* Arbitrage Scanner styles */
.arb-toolbar{display:flex;gap:12px;align-items:center;margin-bottom:16px;flex-wrap:wrap}
.arb-btn{padding:9px 20px;border-radius:8px;border:1px solid var(--line);background:var(--panel);color:#b8c8e4;font-size:13px;font-weight:600;cursor:pointer;transition:all .15s;letter-spacing:.3px}
.arb-btn:hover{border-color:#2b6297;color:#e4efff}
.arb-btn:disabled{opacity:.4;cursor:not-allowed}
.arb-btn.primary{background:linear-gradient(180deg,#11324f,#0d2740);border-color:#2c689d;color:#dbf0ff}
.arb-btn.primary:hover{filter:brightness(1.08)}
.arb-spinner{display:none;width:16px;height:16px;border:2px solid #333;border-top-color:#4a9;border-radius:50%;animation:spin .7s linear infinite;flex-shrink:0}
@keyframes spin{to{transform:rotate(360deg)}}
.arb-count{font-size:12px;color:#92a5c6;padding:6px 12px;background:var(--panel);border:1px solid var(--line);border-radius:6px}
.arb-filter-row{display:flex;align-items:center;gap:8px;font-size:12px;color:var(--muted)}
.arb-filter-row input{width:70px;padding:6px 8px;border-radius:6px;border:1px solid var(--line);background:var(--panel);color:#bfd0ec;font-size:12px;outline:none}
.arb-filter-row input:focus{border-color:#2a4f79}
.arb-table-wrap{background:linear-gradient(180deg,var(--panel) 0%, var(--panel-2) 100%);border:1px solid var(--line);border-radius:10px;overflow:hidden}
.arb-table{width:100%;border-collapse:collapse}
.arb-table th{text-align:left;padding:10px 12px;font-size:10px;color:#8ea2c7;text-transform:uppercase;letter-spacing:.6px;border-bottom:1px solid var(--line);background:#0f1828;white-space:nowrap}
.arb-table td{padding:10px 12px;font-size:12px;border-bottom:1px solid var(--line-soft);vertical-align:middle}
.arb-table tr:last-child td{border-bottom:none}
.arb-table tr:hover td{background:#152138}
.arb-table tr.good-margin td{background:#102535}
.arb-table tr.good-margin:hover td{background:#16304a}
.arb-volatile{display:inline-block;padding:2px 7px;border-radius:3px;font-size:10px;font-weight:600;background:#2a1f00;color:#d4a017;letter-spacing:.3px;text-transform:uppercase}
.arb-link{display:inline-flex;align-items:center;gap:4px;padding:5px 10px;border-radius:6px;border:1px solid #2f78bf;background:#102b46;color:#bfe1ff;font-size:11px;font-weight:600;text-decoration:none;transition:all .15s;white-space:nowrap}
.arb-link:hover{filter:brightness(1.08)}
.arb-empty{text-align:center;padding:48px 20px;color:#6d7e9e;font-size:13px}
.arb-profit-pos{color:var(--good);font-weight:600}
.arb-margin-hi{display:inline-block;padding:2px 8px;border-radius:5px;background:#123a32;color:#90f3cf;font-size:11px;font-weight:700}
.arb-margin-md{display:inline-block;padding:2px 8px;border-radius:5px;background:#3a2b12;color:#ffd189;font-size:11px;font-weight:700}
.fade-inputs{display:none;gap:8px;align-items:center;margin-bottom:0}
.fade-inputs input{flex:1;padding:10px 14px;border-radius:6px;border:1px solid #252525;background:#181818;color:#ccc;font-size:13px;outline:none;max-width:140px;transition:border-color .15s}
.fade-inputs input:focus{border-color:#c93}
.fade-label{font-size:11px;color:#666;white-space:nowrap}
.empire-box{background:linear-gradient(180deg,var(--panel) 0%, var(--panel-2) 100%);border:1px solid var(--line);border-radius:10px;padding:16px;margin-bottom:16px;display:none}
.empire-box h3{font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.8px;margin-bottom:10px}
.empire-row{display:flex;gap:24px;font-size:13px}
.empire-row .e-val{font-weight:600;color:#bc8cff}
.empire-row .e-lbl{font-size:11px;color:#555;margin-bottom:2px}
.empire-item{display:flex;flex-direction:column}
.chart-src-btn{padding:5px 10px;border-radius:4px;border:1px solid #333;background:#181818;color:#777;font-size:11px;cursor:pointer;transition:all .15s}
.chart-src-btn.active{border-color:#bc8cff !important;color:#bc8cff !important}
.chart-src-btn:hover{border-color:#555;color:#999}

/* Pro desk-style override: flat, dense, non-gimmicky */
:root{
  --bg:#0a0a0c !important;
  --panel:#101015 !important;
  --panel-2:#101015 !important;
  --line:#26262d !important;
  --line-soft:#1f1f25 !important;
  --text:#d4d7de !important;
  --muted:#8a8f9b !important;
}
body{
  background:#0a0a0c !important;
  color:var(--text) !important;
  font-family:"IBM Plex Sans","Inter","Segoe UI",system-ui,sans-serif !important;
  padding:20px 16px !important;
}
.container{
  max-width:1200px !important;
  background:#0f1014 !important;
  border:1px solid #23232b !important;
  border-radius:4px !important;
  box-shadow:none !important;
  padding:14px !important;
}
h1{
  font-size:16px !important;
  font-weight:700 !important;
  margin-bottom:14px !important;
  letter-spacing:0 !important;
  color:#eceff5 !important;
}
.tabs-nav{margin-bottom:12px !important}
.tab-btn{
  font-size:12px !important;
  font-weight:600 !important;
  padding:8px 12px !important;
}
.tab-btn.active{
  color:#f1f3f7 !important;
  border-bottom-color:#f1f3f7 !important;
}
.input-row{gap:8px !important;margin-bottom:10px !important}
.input-row input,
.arb-filter-row input,
.arb-filter-row select{
  background:#14151b !important;
  border:1px solid #2a2b33 !important;
  color:#d6d9e0 !important;
  border-radius:3px !important;
  box-shadow:none !important;
}
.input-row input{padding:8px 10px !important;font-size:12px !important}
.arb-filter-row input,.arb-filter-row select{
  height:28px !important;
  padding:4px 8px !important;
  font-size:12px !important;
}
.input-row button,
.arb-btn,
.arb-btn.primary,
.arb-link{
  background:#191b22 !important;
  border:1px solid #303340 !important;
  color:#e6e8ee !important;
  border-radius:3px !important;
  text-transform:none !important;
  filter:none !important;
  box-shadow:none !important;
}
.input-row button,.arb-btn,.arb-btn.primary{
  font-size:12px !important;
  font-weight:600 !important;
  padding:7px 12px !important;
}
.arb-toolbar{gap:8px !important;margin-bottom:10px !important}
.arb-filter-row{gap:6px !important;font-size:11px !important}
.cards{gap:8px !important;margin-bottom:10px !important}
.card,.liq-box,.pump-box,.arb-table-wrap,.empire-box{
  background:#111319 !important;
  border:1px solid #252730 !important;
  border-radius:4px !important;
}
.card{padding:10px !important}
.card h3,.pump-box h3,.empire-box h3{
  color:#9096a3 !important;
  font-size:10px !important;
  letter-spacing:.5px !important;
}
.card .row{padding:3px 0 !important;font-size:11px !important}
.arb-table th{
  background:#151822 !important;
  color:#949bab !important;
  border-bottom:1px solid #2a2d38 !important;
  font-size:10px !important;
  padding:8px 10px !important;
}
.arb-table td{
  border-bottom:1px solid #222530 !important;
  font-size:12px !important;
  padding:8px 10px !important;
}
.arb-table tr:hover td{background:#171b27 !important}
.arb-table tr.good-margin td{background:#151c27 !important}
.arb-table tr.good-margin:hover td{background:#1a2331 !important}
.arb-profit-pos{color:#9fe5bb !important;font-weight:700 !important}
.arb-margin-hi{background:#213a2d !important;color:#b6f0cf !important}
.arb-margin-md{background:#3a311f !important;color:#f1d39f !important}
.arb-empty{color:#7e8593 !important}
.wear-btn{
  border-radius:3px !important;
  padding:6px 10px !important;
  font-size:11px !important;
}
.wear-btn.active{
  background:#1a1f2b !important;
  border-color:#3c455a !important;
  color:#eff2f8 !important;
}
</style>
</head>
<body>
<div class="container">
  <h1>CS2 Skin Analyzer</h1>
  <div class="tabs-nav">
    <button class="tab-btn active" onclick="switchTab('analyzer',this)">Flip Analyzer</button>
    <button class="tab-btn" onclick="switchTab('arbitrage',this)">Arbitrage Scanner</button>
  </div>
  <div id="tab-analyzer" class="tab-panel active">

  <div style="position:relative;margin-bottom:10px">
    <input type="text" id="itemName" placeholder="Start typing item name..." autocomplete="off" oninput="onSearch(this.value)" style="width:100%;box-sizing:border-box;font-size:14px;padding:11px 14px;border-radius:6px;border:1px solid #252525;background:#181818;color:#ccc;outline:none">
    <div id="suggestions" style="display:none;position:absolute;top:100%;left:0;right:0;background:#181818;border:1px solid #282828;border-radius:0 0 6px 6px;max-height:280px;overflow-y:auto;z-index:100"></div>
  </div>
  <div id="wearTabs" class="wear-tabs">
    <button class="wear-btn active" onclick="switchWear('FN')">FN</button>
    <button class="wear-btn" onclick="switchWear('MW')">MW</button>
    <button class="wear-btn" onclick="switchWear('FT')">FT</button>
    <button class="wear-btn" onclick="switchWear('WW')">WW</button>
    <button class="wear-btn" onclick="switchWear('BS')">BS</button>
  </div>
  <div class="input-row">
    <input type="number" id="buyPrice" placeholder="Buy price $" style="max-width:140px" step="0.01">
    <input type="number" id="floatMin" placeholder="Float min (e.g. 0.00)" style="max-width:140px" step="0.0001" min="0" max="1">
    <input type="number" id="floatMax" placeholder="Float max (e.g. 0.07)" style="max-width:140px" step="0.0001" min="0" max="1">
    <button id="analyzeBtn" onclick="runAnalyze()">Analyze</button>
  </div>
  <div class="fade-inputs" id="fadeInputs">
    <span class="fade-label">Fade %</span>
    <input type="number" id="fadeMin" placeholder="Min % (e.g. 90)" step="1" min="50" max="100">
    <span class="fade-label">–</span>
    <input type="number" id="fadeMax" placeholder="Max % (e.g. 100)" step="1" min="50" max="100">
    <span class="fade-label" style="color:#555;font-size:10px">overrides float filter</span>
  </div>

  <div class="result" id="result">
    <div class="verdict-box" id="verdictBox">
      <div class="verdict-label" id="verdictLabel"></div>
      <div class="verdict-detail" id="verdictDetail"></div>
    </div>

    <div class="liq-box" id="liveBox" style="display:none">
      <div>
        <div style="font-size:10px;color:#555;text-transform:uppercase;letter-spacing:.5px">Live CSFloat</div>
        <div style="font-size:28px;font-weight:600;color:#ddd" id="livePrice"></div>
      </div>
      <div style="flex:1;text-align:center">
        <div style="font-size:10px;color:#555;text-transform:uppercase;letter-spacing:.5px">After 2% Fee</div>
        <div style="font-size:20px;font-weight:500;color:#999" id="liveNet"></div>
      </div>
      <div style="text-align:right">
        <div style="font-size:10px;color:#555;text-transform:uppercase;letter-spacing:.5px">Live Profit</div>
        <div style="font-size:20px;font-weight:600" id="liveProfit"></div>
      </div>
    </div>

    <div class="empire-box" id="empireBox">
      <h3>Empire Live Listings</h3>
      <div class="empire-row" id="empireRow"></div>
    </div>

    <div style="background:#151515;border:1px solid #222;border-radius:8px;padding:16px;margin-bottom:16px">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
        <h3 style="font-size:11px;color:#555;text-transform:uppercase;letter-spacing:.8px;margin:0">Price History</h3>
        <div style="display:flex;gap:6px;align-items:center">
          <button class="chart-src-btn active" id="srcFloat" onclick="setChartSource('float')">CSFloat Hist</button>
          <button class="chart-src-btn" id="srcEmpire" onclick="setChartSource('empire')" style="display:none">Empire Now</button>
          <span style="color:#333;font-size:11px">|</span>
          <div id="timeRangeButtons" style="display:flex;gap:6px">
            <button class="time-btn" onclick="drawChartRange(7)" style="padding:5px 10px;border-radius:4px;border:1px solid #333;background:#181818;color:#777;font-size:11px;cursor:pointer;transition:all .15s">7d</button>
            <button class="time-btn" onclick="drawChartRange(30)" style="padding:5px 10px;border-radius:4px;border:1px solid #333;background:#181818;color:#777;font-size:11px;cursor:pointer;transition:all .15s">30d</button>
            <button class="time-btn active" onclick="drawChartRange(60)" style="padding:5px 10px;border-radius:4px;border:1px solid #4a9;background:#181818;color:#4a9;font-size:11px;cursor:pointer;transition:all .15s">60d</button>
          </div>
        </div>
      </div>
      <canvas id="priceChart" width="850" height="220" style="width:100%;cursor:crosshair"></canvas>
      <div id="chartTooltip" style="display:none;position:absolute;background:#141414;border:1px solid #2a2a2a;border-radius:4px;padding:6px 10px;font-size:11px;color:#aaa;pointer-events:none;z-index:50"></div>
    </div>

    <div class="cards" id="windowCards"></div>

    <div class="liq-box" id="liqBox">
      <div class="liq-score" id="liqScore"></div>
      <div class="liq-details" id="liqDetails"></div>
    </div>

    <div class="pump-box" id="pumpBox">
      <h3>Trend Analysis</h3>
      <div id="trendNotes"></div>
    </div>

    <div class="pump-box" id="legendBox">
      <h3>Legend</h3>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;font-size:12px;color:#777;line-height:1.8">
        <div>
          <div style="color:#aaa;font-weight:600;margin-bottom:4px">Liquidity Grades</div>
          <div><span style="color:#4a9;font-weight:600">A (80-100)</span> — sells daily, instant flip</div>
          <div><span style="color:#69a;font-weight:600">B (60-79)</span> — sells often, 1-3 day wait</div>
          <div><span style="color:#c93;font-weight:600">C (40-59)</span> — moderate, may take a week</div>
          <div><span style="color:#b74;font-weight:600">D (20-39)</span> — slow mover, risky hold</div>
          <div><span style="color:#c55;font-weight:600">F (0-19)</span> — dead item, avoid</div>
        </div>
        <div>
          <div style="color:#aaa;font-weight:600;margin-bottom:4px">Trend Signals</div>
          <div><span style="color:#c55">PUMPED (+15%)</span> — artificial spike, will correct</div>
          <div><span style="color:#c55">DROPPING (-10%)</span> — falling fast, new supply?</div>
          <div><span style="color:#c93">Rising/Declining</span> — moderate movement</div>
          <div><span style="color:#4a9">Stable</span> — safe to flip within 7d lock</div>
          <div><span style="color:#c93">Market feed stale/degraded</span> — Pricempire/CSFloat freshness issues reduce confidence</div>
          <div style="margin-top:6px;color:#aaa;font-weight:600">Verdict</div>
          <div><span style="color:#4a9">BUY</span> — net margin, stable trend, and acceptable liquidity</div>
          <div><span style="color:#c93">RISKY</span> — profitable on paper, but high volatility/dips/pump risk</div>
          <div><span style="color:#c55">SKIP</span> — weak margin or downside signals outweigh upside</div>
        </div>
      </div>
    </div>
  </div>

  <div class="history" id="history">
    <h3 style="font-size:11px;color:#555;text-transform:uppercase;letter-spacing:.8px;margin-bottom:8px">Recent Analyses</h3>
  </div>
  </div><!-- end tab-analyzer -->

  <!-- Arbitrage Scanner Tab -->
  <div id="tab-arbitrage" class="tab-panel">
    <div class="arb-toolbar">
      <button class="arb-btn primary" id="arbScanBtn" onclick="arbScan()">&#9654; Scan Now</button>
      <div class="arb-spinner" id="arbSpinner"></div>
      <div class="arb-filter-row">
        <label for="arbSource">Source</label>
        <select id="arbSource" style="width:110px;padding:6px 8px;border-radius:4px;border:1px solid #252525;background:#181818;color:#aaa;font-size:12px;outline:none">
          <option value="listed" selected>Listed</option>
          <option value="auctions">Auctions</option>
          <option value="both">Both</option>
        </select>
        <label for="arbDirection">Direction</label>
        <select id="arbDirection" style="width:155px;padding:6px 8px;border-radius:4px;border:1px solid #252525;background:#181818;color:#aaa;font-size:12px;outline:none">
          <option value="empire_to_float" selected>Empire -> CSFloat</option>
          <option value="float_to_empire">CSFloat -> Empire</option>
        </select>
        <label for="arbPages">Pages</label>
        <select id="arbPages" style="width:90px;padding:6px 8px;border-radius:4px;border:1px solid #252525;background:#181818;color:#aaa;font-size:12px;outline:none">
          <option value="1">Fast</option>
          <option value="3" selected>Better</option>
        </select>
        <label for="arbMinMargin">Min Margin %</label>
        <input type="number" id="arbMinMargin" value="2" min="0" step="0.5">
      </div>
      <div class="arb-filter-row">
        <label for="arbMinPrice">Min $</label>
        <input type="number" id="arbMinPrice" value="0" min="0" step="0.01">
        <label for="arbMaxPrice">Max $</label>
        <input type="number" id="arbMaxPrice" value="200" min="0" step="0.01">
        <label for="arbFloatMin">Float min</label>
        <input type="number" id="arbFloatMin" placeholder="" step="0.0001" min="0" max="1">
        <label for="arbFloatMax">Float max</label>
        <input type="number" id="arbFloatMax" placeholder="" step="0.0001" min="0" max="1">
        <label for="arbCheckVol">Volatile 7d</label>
        <input type="checkbox" id="arbCheckVol">
      </div>
      <div class="arb-count" id="arbCount" style="display:none"></div>
    </div>
    <div class="arb-table-wrap">
      <table class="arb-table">
        <thead>
          <tr>
            <th>#</th>
            <th>Item Name</th>
            <th>Wear</th>
            <th>Empire Listed</th>
            <th>CSFloat Listed</th>
            <th>Net Profit</th>
            <th>Margin %</th>
            <th>Volatile</th>
            <th>Link</th>
          </tr>
        </thead>
        <tbody id="arbTbody"></tbody>
      </table>
      <div class="arb-empty" id="arbEmpty">Hit <strong>Scan Now</strong> to fetch live Empire listings and compare against CSFloat prices.</div>
    </div>
  </div><!-- end tab-arbitrage -->

</div>

<script>
const history = JSON.parse(localStorage.getItem('flipHistory') || '[]');
renderHistory();

let livePriceOverride = null;

function renderHistory() {
  const el = document.getElementById('history');
  el.innerHTML = '<h3 style="font-size:11px;color:#555;text-transform:uppercase;letter-spacing:.8px;margin-bottom:8px">Recent Analyses</h3>' +
    history.slice(0, 10).map(h =>
      '<div class="history-item" onclick="loadHistory(\'' + h.item.replace(/'/g, "\\'") + '\',' + h.price + ')">' +
      '<div class="name">' + h.item + '</div>' +
      '<div class="meta">$' + h.price + ' | ' + h.verdict + ' | ' + h.time + '</div></div>'
    ).join('');
}

function loadHistory(item, price) {
  document.getElementById('itemName').value = item;
  document.getElementById('buyPrice').value = price;
  updateFadeInputVisibility(item);
  runAnalyze();
}

function windowCard(label, w, buyPrice, livePrice) {
  if (!w) return '';
  const low_net = (w.low * 0.98).toFixed(2);
  const high_net = (w.high * 0.98).toFixed(2);
  const med_net = (w.avg * 0.98).toFixed(2);
  let midRows = '<div class="row"><span class="label">Median sale (net 2%)</span><span class="val">$' + med_net + '</span></div>';
  if (w.mean_sale != null && w.mean_sale !== undefined) {
    midRows += '<div class="row"><span class="label">Mean sale (net 2%)</span><span class="val">$' + (w.mean_sale * 0.98).toFixed(2) + '</span></div>';
  } else if (w.basis === 'graph') {
    midRows += '<div class="row" style="font-size:11px;color:#7d8aa6;line-height:1.4">From daily graph buckets — prefer per-sale when API returns history.</div>';
  }
  return '<div class="card"><h3>' + label + '</h3>' +
    '<div class="row"><span class="label">Lowest sale (net 2%)</span><span class="val">$' + low_net + '</span></div>' +
    '<div class="row"><span class="label">Highest sale (net 2%)</span><span class="val">$' + high_net + '</span></div>' +
    midRows +
    (livePrice ? '<div class="row"><span class="label">Live buy now</span><span class="val" style="color:#4a9">$' + livePrice.toFixed(2) + '</span></div>' : '') +
    '</div>';
}

async function runAnalyze() {
  const overrideVal = livePriceOverride;
  // Consume override once; manual analyses won't keep using stale arb data.
  livePriceOverride = null;

  const item = document.getElementById('itemName').value.trim();
  const price = parseFloat(document.getElementById('buyPrice').value);
  if (!item || !price) return;

  const btn = document.getElementById('analyzeBtn');
  btn.disabled = true; btn.textContent = 'Analyzing...';

  // Detect wear from item name if not already set
  const detectedWear = detectWear(item);
  currentWear = detectedWear;
  updateWearTabs(detectedWear);
  document.getElementById('wearTabs').style.display = 'flex';

  // Show/hide fade inputs
  const fadeVisible = document.getElementById('fadeInputs').style.display !== 'none' && document.getElementById('fadeInputs').style.display !== '';
  const fade_min = parseFloat(document.getElementById('fadeMin').value) || null;
  const fade_max = parseFloat(document.getElementById('fadeMax').value) || null;

  try {
    const resp = await fetch('/api/analyze', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        item, price, wear: currentWear,
        float_min: parseFloat(document.getElementById('floatMin').value) || null,
        float_max: parseFloat(document.getElementById('floatMax').value) || null,
        fade_min_pct: fade_min,
        fade_max_pct: fade_max,
        live_price_override: overrideVal,
      })
    });
    const d = await resp.json();
    if (d.error) { alert(d.error); return; }

    document.getElementById('result').style.display = 'block';

    // Verdict
    const vb = document.getElementById('verdictBox');
    vb.className = 'verdict-box ' + d.verdict;
    document.getElementById('verdictLabel').className = 'verdict-label ' + d.verdict;
    document.getElementById('verdictLabel').textContent = d.verdict;
    document.getElementById('verdictDetail').textContent = d.verdict_detail;

    // Live price
    const lb = document.getElementById('liveBox');
    if (d.live_price) {
      lb.style.display = 'flex';
      document.getElementById('livePrice').textContent = '$' + d.live_price.toFixed(2);
      document.getElementById('liveNet').textContent = '$' + d.live_net.toFixed(2);
      const lp = document.getElementById('liveProfit');
      lp.textContent = '$' + d.live_profit.toFixed(2) + ' (' + d.live_pct + '%)';
      lp.style.color = d.live_pct >= 2 ? '#4a9' : d.live_pct >= 0 ? '#c93' : '#c55';
    } else { lb.style.display = 'none'; }

    // Empire box
    const empBox = document.getElementById('empireBox');
    const empRow = document.getElementById('empireRow');
    if (d.empire) {
      empBox.style.display = 'block';
      document.getElementById('srcEmpire').style.display = 'inline-block';
      const gap = d.w30 ? ((d.w30.avg - d.empire.avg) / d.empire.avg * 100).toFixed(1) : null;
      empRow.innerHTML =
        '<div class="empire-item"><div class="e-lbl">Floor</div><div class="e-val">$' + d.empire.floor.toFixed(2) + '</div></div>' +
        '<div class="empire-item"><div class="e-lbl">Avg</div><div class="e-val">$' + d.empire.avg.toFixed(2) + '</div></div>' +
        '<div class="empire-item"><div class="e-lbl">High</div><div class="e-val">$' + d.empire.high.toFixed(2) + '</div></div>' +
        '<div class="empire-item"><div class="e-lbl">Listings</div><div class="e-val">' + d.empire.count + '</div></div>' +
        (gap ? '<div class="empire-item"><div class="e-lbl">vs CSFloat 30d</div><div class="e-val" style="color:' + (parseFloat(gap) > 3 ? '#4a9' : '#c93') + '">' + (gap > 0 ? '+' : '') + gap + '%</div></div>' : '');
      chartEmpire = d.empire;
    } else {
      empBox.style.display = 'none';
      chartEmpire = null;
      document.getElementById('srcEmpire').style.display = 'none';
    }

    // Window cards
    document.getElementById('windowCards').innerHTML =
      windowCard('7 Days', d.w7, price, d.live_price) +
      windowCard('30 Days', d.w30, price, d.live_price) +
      windowCard('60 Days', d.w60, price, d.live_price);

    // Liquidity
    const liq = d.liquidity;
    if (liq && liq.score !== undefined) {
      document.getElementById('liqScore').textContent = liq.score;
      document.getElementById('liqScore').className = 'liq-score ' + liq.grade;
      document.getElementById('liqDetails').innerHTML =
        'Grade <span class="liq-grade">' + liq.grade + '</span>';
    }

    // Chart
    if (d.chart && d.chart.length) drawChart(d.chart, price, d.live_price);

    // Trend notes
    const tn = document.getElementById('trendNotes');
    const notes = d.trend_notes || [];
    tn.innerHTML = notes.map(n => {
      const colors = {danger:'#c55',warn:'#c93',safe:'#4a9',info:'#69a'};
      return '<div style="font-size:13px;font-weight:500;margin-bottom:6px;color:' + (colors[n.type]||'#666') + '">' + n.text + '</div>';
    }).join('');

    // Save history
    history.unshift({item, price, verdict: d.verdict, time: new Date().toLocaleTimeString()});
    if (history.length > 20) history.pop();
    localStorage.setItem('flipHistory', JSON.stringify(history));
    renderHistory();
  } catch(e) { alert('Error: ' + e.message); }
  finally { btn.disabled = false; btn.textContent = 'Analyze'; }
}

// Price chart with time range filtering
let chartData = null, chartBuyPrice = null, chartLivePrice = null, chartDaysRange = 60, hoveredIdx = -1;
let chartEmpire = null, chartSource = 'float';

function setChartSource(src) {
  chartSource = src;
  document.getElementById('srcFloat').classList.toggle('active', src === 'float');
  document.getElementById('srcEmpire').classList.toggle('active', src === 'empire');
  document.getElementById('timeRangeButtons').style.opacity = src === 'float' ? '1' : '0.3';
  if (src === 'empire') drawEmpireChart();
  else drawChartRange(chartDaysRange);
}

function drawChart(data, buyPrice, livePrice) {
  chartData = data;
  chartBuyPrice = buyPrice;
  chartLivePrice = livePrice;
  chartDaysRange = 60;
  chartSource = 'float';
  document.getElementById('srcFloat').classList.add('active');
  document.getElementById('srcEmpire').classList.remove('active');
  document.getElementById('timeRangeButtons').style.opacity = '1';
  drawChartRange(60);
}

function drawEmpireChart() {
  const canvas = document.getElementById('priceChart');
  const ctx = canvas.getContext('2d');
  const dpr = window.devicePixelRatio || 1;
  canvas.width = canvas.clientWidth * dpr;
  canvas.height = 220 * dpr;
  ctx.scale(dpr, dpr);
  const W = canvas.clientWidth, H = 220;
  const pad = {t:20,r:60,b:30,l:60};
  const cw = W - pad.l - pad.r, ch = H - pad.t - pad.b;

  if (!chartEmpire || !chartEmpire.prices || !chartEmpire.prices.length) {
    ctx.clearRect(0, 0, W, H);
    ctx.fillStyle = '#444'; ctx.font = '13px sans-serif'; ctx.textAlign = 'center';
    ctx.fillText('No Empire listing data', W/2, H/2);
    return;
  }

  const prices = chartEmpire.prices;
  const minP = Math.min(...prices, chartBuyPrice) * 0.97;
  const maxP = Math.max(...prices, chartBuyPrice, chartLivePrice || 0) * 1.03;
  const yScale = v => pad.t + ch - ((v - minP) / (maxP - minP)) * ch;
  const barW = Math.max(4, Math.floor(cw / prices.length) - 2);
  const xPos = i => pad.l + (i + 0.5) * (cw / prices.length);

  ctx.clearRect(0, 0, W, H);

  // Grid
  ctx.strokeStyle = '#1e1e1e'; ctx.lineWidth = 1;
  for (let i = 0; i <= 4; i++) {
    const y = pad.t + (ch / 4) * i;
    ctx.beginPath(); ctx.moveTo(pad.l, y); ctx.lineTo(W - pad.r, y); ctx.stroke();
    const val = maxP - ((maxP - minP) / 4) * i;
    ctx.fillStyle = '#444'; ctx.font = '10px monospace'; ctx.textAlign = 'right';
    ctx.fillText('$' + val.toFixed(0), pad.l - 8, y + 4);
  }

  // Bars (Empire listing prices)
  prices.forEach((p, i) => {
    const x = xPos(i) - barW/2;
    const y = yScale(p);
    const bh = pad.t + ch - y;
    ctx.fillStyle = p <= chartBuyPrice ? '#c5552266' : '#bc8cff44';
    ctx.fillRect(x, y, barW, bh);
    ctx.strokeStyle = p <= chartBuyPrice ? '#c55' : '#bc8cff';
    ctx.lineWidth = 1;
    ctx.strokeRect(x, y, barW, bh);
  });

  // Buy price line
  ctx.strokeStyle = '#c5555588'; ctx.lineWidth = 1.5; ctx.setLineDash([4,4]);
  ctx.beginPath(); ctx.moveTo(pad.l, yScale(chartBuyPrice)); ctx.lineTo(W - pad.r, yScale(chartBuyPrice)); ctx.stroke();
  ctx.fillStyle = '#c55'; ctx.font = '10px monospace'; ctx.textAlign = 'left';
  ctx.fillText('BUY $' + chartBuyPrice.toFixed(0), W - pad.r + 4, yScale(chartBuyPrice) + 4);
  ctx.setLineDash([]);

  // Live CSFloat line
  if (chartLivePrice) {
    ctx.strokeStyle = '#4a944a88'; ctx.lineWidth = 1.5; ctx.setLineDash([4,4]);
    ctx.beginPath(); ctx.moveTo(pad.l, yScale(chartLivePrice)); ctx.lineTo(W - pad.r, yScale(chartLivePrice)); ctx.stroke();
    ctx.fillStyle = '#4a9'; ctx.font = '10px monospace'; ctx.textAlign = 'left';
    ctx.fillText('FLOAT $' + chartLivePrice.toFixed(0), W - pad.r + 4, yScale(chartLivePrice) + 4);
    ctx.setLineDash([]);
  }

  // Label
  ctx.fillStyle = '#555'; ctx.font = '10px monospace'; ctx.textAlign = 'center';
  ctx.fillText('Empire live listings (' + prices.length + ')', W/2, H - 6);

  // Tooltip
  canvas.onmousemove = (e) => {
    const rect = canvas.getBoundingClientRect();
    const mx = e.clientX - rect.left;
    const idx = Math.floor((mx - pad.l) / (cw / prices.length));
    if (idx < 0 || idx >= prices.length) { document.getElementById('chartTooltip').style.display = 'none'; return; }
    const tt = document.getElementById('chartTooltip');
    tt.style.display = 'block';
    tt.style.left = (e.pageX + 12) + 'px';
    tt.style.top = (e.pageY - 40) + 'px';
    tt.innerHTML = 'Listing ' + (idx+1) + '<br>Price: $' + prices[idx].toFixed(2) + (prices[idx] <= chartBuyPrice ? '<br><span style="color:#c55">Below buy price</span>' : '');
  };
  canvas.onmouseleave = () => { document.getElementById('chartTooltip').style.display = 'none'; };
}

function drawChartRange(days) {
  chartDaysRange = days;
  const canvas = document.getElementById('priceChart');
  const ctx = canvas.getContext('2d');
  const dpr = window.devicePixelRatio || 1;
  canvas.width = canvas.clientWidth * dpr;
  canvas.height = 220 * dpr;
  ctx.scale(dpr, dpr);
  const W = canvas.clientWidth, H = 220;
  const pad = {t:20,r:60,b:30,l:60};
  const cw = W - pad.l - pad.r, ch = H - pad.t - pad.b;

  // Filter data by days
  let pts = [...chartData].reverse().slice(0, days);
  if (pts.length === 0) pts = [...chartData].reverse();
  const prices = pts.map(p => p.avg);
  const minP = Math.min(...prices, chartBuyPrice) * 0.95;
  const maxP = Math.max(...prices, chartBuyPrice, chartLivePrice || 0) * 1.05;

  const xScale = (i) => pad.l + (i / (pts.length - 1)) * cw;
  const yScale = (v) => pad.t + ch - ((v - minP) / (maxP - minP)) * ch;

  ctx.clearRect(0, 0, W, H);

  // Grid
  ctx.strokeStyle = '#1e1e1e'; ctx.lineWidth = 1;
  for (let i = 0; i <= 4; i++) {
    const y = pad.t + (ch / 4) * i;
    ctx.beginPath(); ctx.moveTo(pad.l, y); ctx.lineTo(W - pad.r, y); ctx.stroke();
    const val = maxP - ((maxP - minP) / 4) * i;
    ctx.fillStyle = '#444'; ctx.font = '10px monospace'; ctx.textAlign = 'right';
    ctx.fillText('$' + val.toFixed(0), pad.l - 8, y + 4);
  }

  ctx.textAlign = 'center';
  const step = Math.ceil(pts.length / 6);
  for (let i = 0; i < pts.length; i += step) {
    ctx.fillStyle = '#444'; ctx.font = '9px monospace';
    ctx.fillText(pts[i].day.slice(5), xScale(i), H - 6);
  }

  // BUY price line
  ctx.strokeStyle = '#c5555544'; ctx.lineWidth = 1; ctx.setLineDash([4,4]);
  ctx.beginPath(); ctx.moveTo(pad.l, yScale(chartBuyPrice)); ctx.lineTo(W - pad.r, yScale(chartBuyPrice)); ctx.stroke();
  ctx.fillStyle = '#c55'; ctx.font = '10px monospace'; ctx.textAlign = 'left';
  ctx.fillText('BUY $' + chartBuyPrice.toFixed(0), W - pad.r + 4, yScale(chartBuyPrice) + 4);
  ctx.setLineDash([]);

  // LIVE price line
  if (chartLivePrice) {
    ctx.strokeStyle = '#4a944a44'; ctx.lineWidth = 1; ctx.setLineDash([4,4]);
    ctx.beginPath(); ctx.moveTo(pad.l, yScale(chartLivePrice)); ctx.lineTo(W - pad.r, yScale(chartLivePrice)); ctx.stroke();
    ctx.fillStyle = '#4a9'; ctx.font = '10px monospace'; ctx.textAlign = 'left';
    ctx.fillText('LIVE $' + chartLivePrice.toFixed(0), W - pad.r + 4, yScale(chartLivePrice) + 4);
    ctx.setLineDash([]);
  }

  // Price area
  ctx.beginPath();
  ctx.moveTo(xScale(0), yScale(prices[0]));
  for (let i = 1; i < pts.length; i++) ctx.lineTo(xScale(i), yScale(prices[i]));
  ctx.lineTo(xScale(pts.length - 1), pad.t + ch);
  ctx.lineTo(xScale(0), pad.t + ch);
  ctx.closePath();
  const grad = ctx.createLinearGradient(0, pad.t, 0, pad.t + ch);
  grad.addColorStop(0, '#ffffff08'); grad.addColorStop(1, '#ffffff00');
  ctx.fillStyle = grad; ctx.fill();

  // Price line
  ctx.strokeStyle = '#888'; ctx.lineWidth = 1.5;
  ctx.beginPath();
  ctx.moveTo(xScale(0), yScale(prices[0]));
  for (let i = 1; i < pts.length; i++) ctx.lineTo(xScale(i), yScale(prices[i]));
  ctx.stroke();

  // Dots
  for (let i = 0; i < pts.length; i++) {
    ctx.fillStyle = i === hoveredIdx ? '#4a9' : '#999';
    ctx.beginPath();
    ctx.arc(xScale(i), yScale(prices[i]), i === hoveredIdx ? 4 : 2, 0, Math.PI * 2);
    ctx.fill();
  }

  // Volume bars
  const maxVol = Math.max(...pts.map(p => p.sales));
  for (let i = 0; i < pts.length; i++) {
    const barH = (pts[i].sales / maxVol) * 18;
    ctx.fillStyle = '#ffffff0a';
    ctx.fillRect(xScale(i) - 2, pad.t + ch - barH, 4, barH);
  }

  // Mouse events
  canvas.onmousemove = (e) => {
    const rect = canvas.getBoundingClientRect();
    const mx = e.clientX - rect.left;
    const idx = Math.round(((mx - pad.l) / cw) * (pts.length - 1));
    if (idx < 0 || idx >= pts.length) {
      hoveredIdx = -1;
      document.getElementById('chartTooltip').style.display = 'none';
      return;
    }
    hoveredIdx = idx;
    const p = pts[idx];
    const tt = document.getElementById('chartTooltip');
    tt.style.display = 'block';
    tt.style.left = (e.pageX + 12) + 'px';
    tt.style.top = (e.pageY - 40) + 'px';
    tt.innerHTML = '<strong>' + p.day + '</strong><br>Avg: $' + p.avg.toFixed(2) + '<br>Sales: ' + p.sales;
    // Redraw to highlight dot
    drawChartRange(chartDaysRange);
  };
  canvas.onmouseleave = () => {
    hoveredIdx = -1;
    document.getElementById('chartTooltip').style.display = 'none';
    drawChartRange(chartDaysRange);
  };

  // Update button states
  document.querySelectorAll('.time-btn').forEach(btn => {
    btn.classList.remove('active');
    if (btn.textContent === days + 'd') btn.classList.add('active');
  });
}

function updateFadeInputVisibility(itemName) {
  const fi = document.getElementById('fadeInputs');
  if (itemName.toLowerCase().includes('fade')) {
    fi.style.display = 'flex';
  } else {
    fi.style.display = 'none';
    document.getElementById('fadeMin').value = '';
    document.getElementById('fadeMax').value = '';
  }
}

// Search autocomplete
let searchTimer = null;
function onSearch(q) {
  clearTimeout(searchTimer);
  updateFadeInputVisibility(q);
  const box = document.getElementById('suggestions');
  if (q.length < 2) { box.style.display = 'none'; return; }
  searchTimer = setTimeout(async () => {
    try {
      const r = await fetch('/api/search?q=' + encodeURIComponent(q));
      const d = await r.json();
      if (!d.results.length) { box.style.display = 'none'; return; }
      box.style.display = 'block';
      box.innerHTML = d.results.map(r =>
        '<div style="padding:8px 12px;cursor:pointer;font-size:12px;border-bottom:1px solid #1e1e1e;display:flex;justify-content:space-between;color:#aaa" ' +
        'onmousedown="pickItem(\'' + r.name.replace(/'/g, "\\'") + '\',' + r.price + ')">' +
        '<span>' + r.name + '</span><span style="color:#666">$' + r.price.toFixed(2) + '</span></div>'
      ).join('');
    } catch(e) {}
  }, 400);
}
function pickItem(name, price) {
  document.getElementById('itemName').value = name;
  document.getElementById('buyPrice').value = price.toFixed(2);
  document.getElementById('suggestions').style.display = 'none';
}
document.addEventListener('click', e => {
  if (!e.target.closest('.input-row')) document.getElementById('suggestions').style.display = 'none';
});

document.getElementById('itemName').addEventListener('keydown', e => { if (e.key === 'Enter') runAnalyze(); });
document.getElementById('buyPrice').addEventListener('keydown', e => { if (e.key === 'Enter') runAnalyze(); });

let currentWear = 'FN';
let currentPhase = null;
const wearConditions = ['FN', 'MW', 'FT', 'WW', 'BS'];
const dopplerPhases = ['Black Pearl', 'Sapphire', 'Ruby', 'Emerald', 'Lore', 'Phase 1', 'Phase 2', 'Phase 3', 'Phase 4'];

function detectWear(itemName) {
  const wearMap = {
    'Factory New': 'FN', 'FN': 'FN',
    'Minimal Wear': 'MW', 'MW': 'MW',
    'Field-Tested': 'FT', 'FT': 'FT',
    'Well-Worn': 'WW', 'WW': 'WW',
    'Battle-Scarred': 'BS', 'BS': 'BS'
  };
  for (const [key, val] of Object.entries(wearMap)) {
    if (itemName.includes(key)) return val;
  }
  return 'FN';
}

function detectPhase(itemName) {
  for (const phase of dopplerPhases) {
    if (itemName.includes(phase)) return phase;
  }
  return null;
}

function normalizeDopplerName(itemName) {
  // Normalize Doppler and Gamma Doppler knife names to show phases properly
  if (itemName.includes('Doppler') || itemName.includes('doppler')) {
    const phase = detectPhase(itemName);
    if (phase) {
      currentPhase = phase;
      return itemName;
    }
  }
  return itemName;
}

function switchWear(wear) {
  currentWear = wear;
  document.querySelectorAll('.wear-btn').forEach(b => b.classList.remove('active'));
  event.target.classList.add('active');

  // Rebuild item name with new wear while preserving phase
  let itemName = document.getElementById('itemName').value.trim();
  const wearMap = {
    'Factory New': 'FN', 'FN': 'FN',
    'Minimal Wear': 'MW', 'MW': 'MW',
    'Field-Tested': 'FT', 'FT': 'FT',
    'Well-Worn': 'WW', 'WW': 'WW',
    'Battle-Scarred': 'BS', 'BS': 'BS'
  };

  // Remove old wear condition
  for (const [key] of Object.entries(wearMap)) {
    if (itemName.includes(key)) {
      itemName = itemName.replace(key, '').trim();
    }
  }

  // Add new wear condition
  const wearFull = Object.keys(wearMap).find(k => wearMap[k] === wear);
  itemName = (itemName + ' ' + wearFull).trim();
  document.getElementById('itemName').value = itemName;

  runAnalyze();
}

function pickItem(name, price) {
  document.getElementById('itemName').value = name;
  document.getElementById('buyPrice').value = price.toFixed(2);
  document.getElementById('suggestions').style.display = 'none';
  const wear = detectWear(name);
  currentWear = wear;
  updateWearTabs(wear);
  document.getElementById('wearTabs').style.display = 'flex';
  updateFadeInputVisibility(name);
}

function updateWearTabs(wear) {
  document.querySelectorAll('.wear-btn').forEach((btn, idx) => {
    if (wearConditions[idx] === wear) {
      btn.classList.add('active');
    } else {
      btn.classList.remove('active');
    }
  });
}

// Tab switching
function switchTab(name, btn) {
  document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  document.getElementById('tab-' + name).classList.add('active');
  btn.classList.add('active');
}

// Arbitrage Scanner
let arbResults = [];
let arbMeta = null;

function goToAnalyzer() {
  // Switch tabs without needing a button reference.
  const analyzerBtn = Array.from(document.querySelectorAll('.tab-btn')).find(b => {
    const oc = b.getAttribute('onclick') || '';
    return oc.includes("switchTab('analyzer'");
  });
  if (analyzerBtn) switchTab('analyzer', analyzerBtn);
  else {
    document.getElementById('tab-analyzer').classList.add('active');
    document.getElementById('tab-arbitrage').classList.remove('active');
  }
}

function analyzeFromArb(name, empireUsd, csfloatFloor, direction) {
  // Reuse existing pickItem() logic so wear detection + fade inputs + analysis math all run.
  const el = document.getElementById('arbDirection');
  const dir = (direction || (el ? el.value : '')).toLowerCase();
  const isFloatToEmpire = dir === 'float_to_empire';

  // Swap buy/sell inputs so the profit math uses the scan direction.
  pickItem(name, isFloatToEmpire ? csfloatFloor : empireUsd);
  livePriceOverride = isFloatToEmpire ? empireUsd : csfloatFloor;
  goToAnalyzer();
}

async function arbScan() {
  const btn = document.getElementById('arbScanBtn');
  const spinner = document.getElementById('arbSpinner');
  const countEl = document.getElementById('arbCount');
  btn.disabled = true;
  spinner.style.display = 'block';
  countEl.style.display = 'none';
  document.getElementById('arbEmpty').style.display = 'block';
  document.getElementById('arbEmpty').textContent = 'Scanning Empire and CSFloat... this may take 30-60 seconds.';
  document.getElementById('arbTbody').innerHTML = '';

  try {
    const getOptFloat = (id) => {
      const v = document.getElementById(id).value.trim();
      if (!v) return null;
      const n = parseFloat(v);
      return Number.isFinite(n) ? n : null;
    };

    const params = new URLSearchParams();
    params.set('source', document.getElementById('arbSource').value);
    params.set('direction', document.getElementById('arbDirection').value);
    params.set('pages', document.getElementById('arbPages').value);
    // CSFloat is strict on rate limits; keep request count very modest.
    const maxItems = (document.getElementById('arbPages').value === '1') ? 5 : 10;
    params.set('max_items', maxItems);
    params.set('min_price', parseFloat(document.getElementById('arbMinPrice').value) || 0);
    params.set('max_price', parseFloat(document.getElementById('arbMaxPrice').value) || 200);

    const floatMin = getOptFloat('arbFloatMin');
    const floatMax = getOptFloat('arbFloatMax');
    if (floatMin !== null) params.set('float_min', floatMin);
    if (floatMax !== null) params.set('float_max', floatMax);

    const checkVol = document.getElementById('arbCheckVol').checked ? 'true' : 'false';
    params.set('check_volatile', checkVol);

    const resp = await fetch('/api/arbitrage?' + params.toString());
    if (!resp.ok) throw new Error('HTTP ' + resp.status);
    const data = await resp.json();
    arbResults = Array.isArray(data) ? data : (data.results || []);
    arbMeta = Array.isArray(data) ? null : data.meta;
    renderArbTable();
  } catch(e) {
    document.getElementById('arbEmpty').textContent = 'Error: ' + e.message;
  } finally {
    btn.disabled = false;
    spinner.style.display = 'none';
  }
}

function renderArbTable() {
  const minMargin = parseFloat(document.getElementById('arbMinMargin').value) || 0;
  const filtered = arbResults.filter(r => r.margin_pct >= minMargin);
  const tbody = document.getElementById('arbTbody');
  const empty = document.getElementById('arbEmpty');
  const countEl = document.getElementById('arbCount');

  if (!filtered.length) {
    tbody.innerHTML = '';
    empty.style.display = 'block';
    if (arbMeta && !arbMeta.keys_present) {
      empty.textContent = 'CSGOEmpire/CSFloat API keys missing (backend returned 0 results).';
    } else if (arbMeta && arbMeta.empire_items_fetched === 0) {
      empty.textContent = 'CSGOEmpire returned 0 items for this scan (try Pages=3, or change Source).';
      } else if (arbMeta && arbMeta.csfloat_listings_found === 0 && arbMeta.csfloat_items_enqueued > 0) {
        empty.textContent = 'CSFloat rate-limited or returning no listings right now. Wait ~60s and scan again.';
    } else if (arbMeta && arbMeta.profitable_pre_margin === 0) {
      empty.textContent = 'No profitable matches. Empire items scanned: ' + arbMeta.empire_items_fetched + '.';
    } else if (arbResults.length) {
      empty.textContent = 'No items meet the minimum margin filter (' + minMargin + '%). Found ' + arbResults.length + ' total profitable items before filter.';
    } else {
      empty.textContent = 'No profitable arbitrage opportunities found in this scan.';
    }
    countEl.style.display = 'none';
    return;
  }

  empty.style.display = 'none';
  countEl.style.display = 'inline-block';
  countEl.textContent = filtered.length + ' profitable item' + (filtered.length !== 1 ? 's' : '') + ' found';

  tbody.innerHTML = filtered.map((r, i) => {
    const rowCls = r.margin_pct > 2 ? ' class="good-margin"' : '';
    const marginBadge = r.margin_pct > 2
      ? '<span class="arb-margin-hi">+' + r.margin_pct.toFixed(2) + '%</span>'
      : '<span class="arb-margin-md">+' + r.margin_pct.toFixed(2) + '%</span>';
    const volatileBadge = r.volatile ? '<span class="arb-volatile">Volatile</span>' : '<span style="color:#333;font-size:11px">&#8212;</span>';
    const itemUrl = 'https://csfloat.com/search?market_hash_name=' + encodeURIComponent(r.name);
    const nameArg = JSON.stringify(r.name);
    return '<tr' + rowCls + '>' +
      '<td style="color:#444">' + (i + 1) + '</td>' +
      '<td><a href="#" style="color:#aaa;text-decoration:none;transition:color .15s" onclick="analyzeFromArb(' + nameArg + ',' + r.empire_usd + ',' + r.csfloat_floor + '); return false;">' + r.name + '</a></td>' +
      '<td style="color:#666;font-size:11px">' + (r.wear || '&#8212;') + '</td>' +
      '<td style="color:#c55">$' + r.empire_usd.toFixed(2) + '</td>' +
      '<td style="color:#888">$' + r.csfloat_floor.toFixed(2) + '</td>' +
      '<td class="arb-profit-pos">+$' + r.net_profit.toFixed(2) + '</td>' +
      '<td>' + marginBadge + '</td>' +
      '<td>' + volatileBadge + '</td>' +
      '<td><a href="' + r.csfloat_url + '" target="_blank" class="arb-link">Buy on Float &#8599;</a></td>' +
      '</tr>';
  }).join('');
}

document.getElementById('arbMinMargin').addEventListener('input', function() {
  if (arbResults.length) renderArbTable();
});
</script>
</body>
</html>"""

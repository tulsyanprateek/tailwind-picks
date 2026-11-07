"""Momentum Radar dashboard: trading-terminal layout (ticker tape, big chart, watchlist, tabs)."""
from __future__ import annotations

import json
import math

from .charts import LIB_URL
from .html_common import esc, page
from .utils import inr, pct

FAILED_BANNER = "STRATEGY FAILED OUT OF SAMPLE"

FONTS = ('<link rel="preconnect" href="https://fonts.googleapis.com">'
         '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
         '<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900'
         '&family=Space+Grotesk:wght@500;600;700&display=swap" rel="stylesheet">')

VERDICT = {"BUY": ("BUY", "All checks pass, top 5"), "HOLD": ("HOLD", "Keep if you own it"),
           "SELL": ("SELL", "A check failed"), "WAIT": ("WAIT", "Good stock, weak market")}

DASH_CSS = """
:root{--bg:#0b0e14;--panel:#121722;--panel2:#171d2a;--line:#1f2736;--text:#e6e9f0;--muted:#8a94a7;
--green:#22c55e;--red:#ef4444;--amber:#f5b942;--blue:#3b82f6;--violet:#a78bfa}
html,body{font-family:Inter,ui-sans-serif,-apple-system,"Segoe UI",Roboto,sans-serif;font-feature-settings:"tnum" 1,"cv11" 1}
body{background:var(--bg)}
.wrap{max-width:1280px;padding:0 14px 28px}
h1,h2,.bname,.headline,.sym,.big{font-family:"Space Grotesk",Inter,sans-serif}
.tape{position:sticky;top:0;z-index:5;margin:0 -14px 12px;overflow:hidden;border-bottom:1px solid var(--line);
background:rgba(11,14,20,.92);backdrop-filter:blur(8px)}
.tape-in{display:inline-flex;gap:28px;padding:8px 0;white-space:nowrap;animation:tape 40s linear infinite}
.tape:hover .tape-in{animation-play-state:paused}
@keyframes tape{from{transform:translateX(0)}to{transform:translateX(-50%)}}
.ti{font-size:12.5px;font-weight:600;color:#cdd3df}.ti b{color:#fff;margin-right:6px}.ti .up{color:var(--green)}.ti .dn{color:var(--red)}
.status{display:flex;flex-wrap:wrap;align-items:center;gap:10px 14px;padding:12px 14px;border-radius:14px;margin-bottom:12px;
border:1px solid var(--line);background:var(--panel)}
.status .big{font-size:22px;font-weight:700;letter-spacing:-.01em}
.status.red .big{color:#fda4af}.status.green .big{color:#86efac}.status.blue .big{color:#93c5fd}
.status .txt{flex:1 1 260px;color:#c7cedb;font-size:14px}
.pill{display:inline-flex;align-items:center;gap:6px;font-size:12px;font-weight:600;padding:5px 10px;border-radius:999px;
background:var(--panel2);border:1px solid var(--line);color:#d5dbe6}
.dot{width:7px;height:7px;border-radius:50%}.dot.g{background:var(--green);box-shadow:0 0 8px var(--green)}
.dot.r{background:var(--red);box-shadow:0 0 8px var(--red)}
.layout{display:grid;grid-template-columns:minmax(0,1fr) 330px;gap:12px;align-items:start}
.main,.side{background:var(--panel);border:1px solid var(--line);border-radius:14px;overflow:hidden}
.symhead{display:flex;flex-wrap:wrap;align-items:center;gap:10px 14px;padding:12px 14px;border-bottom:1px solid var(--line)}
.clogo{position:relative;flex:none;width:38px;height:38px;border-radius:10px;background:#fff;display:grid;place-items:center;
overflow:hidden;font-weight:800;color:#0b1020;font-size:13px}
.clogo img{position:absolute;inset:5px;width:28px;height:28px;object-fit:contain}
.clogo.idx{background:linear-gradient(135deg,var(--blue),var(--violet));color:#fff}
.sid{min-width:0}.sym{font-size:19px;font-weight:700;letter-spacing:-.01em;line-height:1.1}
.sym small{font-family:Inter;font-size:11px;font-weight:600;color:var(--muted);margin-left:6px;padding:2px 6px;border:1px solid var(--line);border-radius:6px}
.co{color:var(--muted);font-size:12.5px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:260px}
.px{margin-left:auto;text-align:right}.px b{display:block;font-size:22px;font-weight:700;font-family:"Space Grotesk"}
.px span{font-size:13px;font-weight:600}.up{color:var(--green)}.dn{color:var(--red)}
.vd{font-family:"Space Grotesk";font-weight:700;font-size:13px;padding:6px 12px;border-radius:8px;letter-spacing:.04em}
.vd.BUY{background:rgba(34,197,94,.15);color:var(--green)}.vd.HOLD{background:rgba(245,185,66,.15);color:var(--amber)}
.vd.SELL{background:rgba(239,68,68,.15);color:var(--red)}.vd.WAIT{background:rgba(148,163,184,.15);color:#cbd5e1}
.vd.STRONG{background:rgba(34,197,94,.15);color:var(--green)}.vd.WEAK{background:rgba(239,68,68,.15);color:var(--red)}
.brands{display:flex;flex-wrap:wrap;gap:6px;width:100%}
.brands span{font-size:11.5px;font-weight:600;padding:3px 9px;border-radius:999px;background:rgba(167,139,250,.12);color:#d9d0ff}
.toolbar{display:flex;flex-wrap:wrap;align-items:center;gap:4px;padding:8px 10px;border-bottom:1px solid var(--line)}
.tb{background:transparent;border:0;color:var(--muted);font:600 12.5px Inter;padding:6px 9px;border-radius:7px;cursor:pointer}
.tb:hover{background:var(--panel2);color:var(--text)}.tb.on{color:#fff;background:var(--panel2)}
.tb.tog.on{color:#93c5fd}.sep{width:1px;height:18px;background:var(--line);margin:0 6px}
.ohlc{padding:6px 14px 0;font-size:12px;color:var(--muted)}.ohlc b{color:var(--text);font-weight:600;margin-right:8px}
#chart{height:440px}
.tabs{display:flex;gap:2px;padding:0 10px;border-top:1px solid var(--line);border-bottom:1px solid var(--line);overflow-x:auto}
.tab{background:none;border:0;border-bottom:2px solid transparent;color:var(--muted);font:600 13px Inter;padding:11px 10px;cursor:pointer;white-space:nowrap}
.tab.on{color:#fff;border-bottom-color:var(--blue)}
.tp{display:none;padding:14px}.tp.on{display:block}
.sigt{width:100%;font-size:13px}.sigt th{background:transparent;position:static;color:var(--muted);font-weight:600}
.sigt td{white-space:normal;vertical-align:middle}.sigt td:nth-child(2){white-space:nowrap}
.hint{font-size:11px;color:var(--muted)}
.sig{display:inline-block;min-width:52px;text-align:center;font-size:11px;font-weight:800;padding:3px 8px;border-radius:6px}
.sig.BUY{background:rgba(34,197,94,.15);color:var(--green)}.sig.HOLD{background:rgba(245,185,66,.15);color:var(--amber)}
.sig.SELL{background:rgba(239,68,68,.15);color:var(--red)}.sig.WAIT{background:rgba(148,163,184,.15);color:#cbd5e1}
.pgrid{display:grid;grid-template-columns:repeat(4,1fr);gap:8px}
.pgrid div{background:var(--panel2);border:1px solid var(--line);border-radius:10px;padding:10px}
.pgrid .l{font-size:11px;color:var(--muted)}.pgrid .v{font-size:18px;font-weight:700;font-family:"Space Grotesk"}
.pgrid .s{font-size:11px;color:var(--muted)}.v.blue{color:#60a5fa}.v.red{color:#f87171}.v.green{color:#4ade80}
.ph{font-size:11.5px;text-transform:uppercase;letter-spacing:.08em;color:#60a5fa;font-weight:700;margin:0 0 8px}
.rules{margin:0;padding-left:18px;font-size:13.5px;color:#c7cedb}.rules li{margin:5px 0}
pre.order{background:#0a0d13;border:1px solid var(--line);border-radius:10px;padding:12px;font-size:12px;white-space:pre-wrap;margin:10px 0}
#rs{height:220px}
.about{font-size:13.5px;color:#c7cedb}.meta{font-size:12.5px;color:var(--muted)}
.risk{font-size:12.5px;color:#fde68a;background:rgba(245,185,66,.08);border-radius:10px;padding:8px 10px;margin-top:8px}
.side-h{display:flex;justify-content:space-between;align-items:center;padding:12px 14px;border-bottom:1px solid var(--line);
font-family:"Space Grotesk";font-weight:700}.side-h span{font:600 11.5px Inter;color:var(--muted)}
.wl-head,.wl-row{display:grid;grid-template-columns:minmax(0,1fr) 76px 58px 48px;gap:6px;align-items:center;padding:8px 12px}
.wl-head{font-size:11px;color:var(--muted);font-weight:600;border-bottom:1px solid var(--line)}
.wl-head span:not(:first-child),.wl-row>span:not(:first-child){text-align:right}
.wl-row{cursor:pointer;border-bottom:1px solid rgba(255,255,255,.03);font-size:13px}
.wl-row:hover{background:var(--panel2)}.wl-row.on{background:rgba(59,130,246,.12);box-shadow:inset 3px 0 0 var(--blue)}
.wl-sym{display:flex;align-items:center;gap:8px;min-width:0}.wl-sym img,.wl-sym i{flex:none;width:22px;height:22px;border-radius:6px;background:#fff}
.wl-sym i{display:grid;place-items:center;font:800 9px Inter;color:#0b1020;font-style:normal}
.wl-sym b{display:block;font-weight:700;font-size:13px}.wl-sym em{display:block;font-style:normal;font-size:11px;color:var(--muted);
white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.mini{font-size:10.5px;font-weight:800;padding:2px 0;border-radius:5px;text-align:center}
.mini.BUY{color:var(--green);background:rgba(34,197,94,.12)}.mini.HOLD{color:var(--amber);background:rgba(245,185,66,.12)}
.mini.SELL{color:var(--red);background:rgba(239,68,68,.12)}.mini.WAIT{color:#cbd5e1;background:rgba(148,163,184,.12)}
.mini.STRONG{color:var(--green);background:rgba(34,197,94,.12)}.mini.WEAK{color:var(--red);background:rgba(239,68,68,.12)}
.cards{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-top:12px}
.card2{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:14px}
.card2 h3{margin:0 0 8px;font-family:"Space Grotesk";font-size:15px}
.tiles{display:grid;grid-template-columns:repeat(3,1fr);gap:8px}
.tile{background:var(--panel2);border-radius:10px;padding:10px}.tl{font-size:11px;color:var(--muted)}
.tv{font-family:"Space Grotesk";font-size:20px;font-weight:700}.tv.green{color:var(--green)}.tv.red{color:var(--red)}
.tn{font-size:11px;color:var(--muted)}
#eq{height:200px;margin-top:10px}
.lg{display:flex;flex-wrap:wrap;gap:12px;font-size:11.5px;color:var(--muted);margin-top:6px}
.lg i{display:inline-block;width:12px;height:3px;border-radius:2px;vertical-align:middle;margin-right:5px}
.more{color:#60a5fa;text-decoration:none;font-weight:600;font-size:13.5px}
.copied{color:var(--green);font-size:12px;margin-left:8px}
.funnel{display:flex;flex-wrap:wrap;align-items:stretch;gap:6px;margin:0 0 12px}
.fh{flex-basis:100%;font-size:11.5px;text-transform:uppercase;letter-spacing:.08em;color:var(--muted);font-weight:700}
.fs{position:relative;flex:1 1 120px;background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:8px 10px;
font-size:12px;color:var(--muted)}.fs b{display:block;font-family:"Space Grotesk";font-size:20px;color:var(--text)}
.fs:last-child{border-color:rgba(59,130,246,.5);background:rgba(59,130,246,.08)}
.how-got{background:rgba(59,130,246,.07);border:1px solid rgba(59,130,246,.2);border-radius:10px;padding:10px 12px;font-size:13.5px;color:#c7cedb}
.how-got b{color:#fff}
#ind-rsi{height:150px}#ind-macd{height:150px}.ind-c{margin-top:14px}
@media(max-width:600px){.fs{flex:1 1 calc(33% - 6px);padding:6px 8px;font-size:10.5px}.fs b{font-size:17px}}
.topbar{margin-top:12px}
@media(max-width:980px){.layout{grid-template-columns:1fr}.side{order:-1}.cards{grid-template-columns:1fr}
.wl{display:flex;overflow-x:auto;scroll-snap-type:x mandatory}.wl-head{display:none}
.wl-row{flex:0 0 150px;grid-template-columns:1fr 1fr;border-right:1px solid var(--line);border-bottom:0;scroll-snap-align:start}
.wl-row .wl-sym{grid-column:1/-1}.wl-row>span:nth-child(2){text-align:left}.wl-row .mini{grid-column:1/-1}
#chart{height:330px}.pgrid{grid-template-columns:1fr 1fr}.px b{font-size:19px}}
"""

APP_JS = r"""
(function(){
var A=window.__APP;if(!A||!A.order||!A.order.length)return;
function $(id){return document.getElementById(id)}
function f(x){return x==null?'':Number(x).toLocaleString('en-IN',{minimumFractionDigits:2,maximumFractionDigits:2})}
if(!window.LightweightCharts){$('chart').innerHTML='<div style="padding:40px;text-align:center;color:#8a94a7">Charts need an internet connection.</div>';}
var L=window.LightweightCharts,ch,cs,vs,m50,m200,lines=[],cur=null,tf=250,opt={ma50:1,ma200:1,vol:1,plan:1},rsCh=null,tab='sig';
function base(el){return L.createChart(el,{width:el.clientWidth,height:el.clientHeight,
 layout:{background:{type:'solid',color:'transparent'},textColor:'#8a94a7',fontSize:11,fontFamily:'Inter, sans-serif'},
 grid:{vertLines:{color:'rgba(255,255,255,0.035)'},horzLines:{color:'rgba(255,255,255,0.035)'}},
 rightPriceScale:{borderColor:'rgba(255,255,255,0.08)'},timeScale:{borderColor:'rgba(255,255,255,0.08)'},
 crosshair:{mode:1,vertLine:{color:'rgba(255,255,255,0.25)',labelBackgroundColor:'#1f2736'},horzLine:{color:'rgba(255,255,255,0.25)',labelBackgroundColor:'#1f2736'}},
 localization:{priceFormatter:function(p){return Number(p).toLocaleString('en-IN',{maximumFractionDigits:2})}}});}
function ln(c,w){return ch.addLineSeries({color:c,lineWidth:w,priceLineVisible:false,lastValueVisible:false,crosshairMarkerVisible:false})}
function init(){if(!L)return;var el=$('chart');ch=base(el);
 cs=ch.addCandlestickSeries({upColor:'#22c55e',downColor:'#ef4444',borderVisible:false,wickUpColor:'#22c55e',wickDownColor:'#ef4444'});
 vs=ch.addHistogramSeries({priceScaleId:'vol',priceFormat:{type:'volume'},lastValueVisible:false,priceLineVisible:false});
 ch.priceScale('vol').applyOptions({scaleMargins:{top:0.82,bottom:0}});
 m50=ln('#f5b942',1.5);m200=ln('#a78bfa',2);
 ch.subscribeCrosshairMove(function(p){var b=p&&p.seriesData?p.seriesData.get(cs):null;legend(b)});
 var t;window.addEventListener('resize',function(){clearTimeout(t);t=setTimeout(function(){ch.applyOptions({width:el.clientWidth,height:el.clientHeight});
  if(rsCh){var r=$('rs');rsCh.applyOptions({width:r.clientWidth})}if(tab==='ind')drawInd();ch.timeScale().fitContent()},150)});}
function legend(b){var d=A.data[cur];if(!d)return;var l=d.c[d.c.length-1];
 var x=b?[b.open,b.high,b.low,b.close]:[l[1],l[2],l[3],l[4]];
 $('ohlc').innerHTML='O <b>'+f(x[0])+'</b>H <b>'+f(x[1])+'</b>L <b>'+f(x[2])+'</b>C <b>'+f(x[3])+'</b>'+
 '<span style="color:#f5b942">MA 50</span> &nbsp;<span style="color:#a78bfa">MA 200</span>';}
function draw(){if(!L)return;var d=A.data[cur],c=d.c.slice(-tf),t0=c[0][0];
 cs.setData(c.map(function(x){return{time:x[0],open:x[1],high:x[2],low:x[3],close:x[4]}}));
 vs.setData(opt.vol&&!d.index?c.map(function(x){return{time:x[0],value:x[5],color:x[4]>=x[1]?'rgba(34,197,94,0.3)':'rgba(239,68,68,0.3)'}}):[]);
 function cut(a){return a.filter(function(x){return x[0]>=t0}).map(function(x){return{time:x[0],value:x[1]}})}
 m50.setData(opt.ma50?cut(d.ma50):[]);m200.setData(opt.ma200?cut(d.ma200):[]);
 lines.forEach(function(p){cs.removePriceLine(p)});lines=[];
 function pl(v,c,t){if(v)lines.push(cs.createPriceLine({price:v,color:c,lineWidth:1,lineStyle:2,axisLabelVisible:true,title:t}))}
 if(opt.plan){pl(d.limit,'#3b82f6','Buy');pl(d.stop,'#ef4444','Stop');pl(d.aim,'#22c55e','Target')}
 ch.timeScale().fitContent();legend(null);}
function drawRS(){var d=A.data[cur],el=$('rs');if(!L||!el)return;if(rsCh){rsCh.remove();rsCh=null}
 if(!d.rs){el.innerHTML='';return}rsCh=base(el);
 var b=rsCh.addBaselineSeries({baseValue:{type:'price',price:100},topLineColor:'#22c55e',topFillColor1:'rgba(34,197,94,0.25)',topFillColor2:'rgba(34,197,94,0.02)',
  bottomLineColor:'#ef4444',bottomFillColor1:'rgba(239,68,68,0.02)',bottomFillColor2:'rgba(239,68,68,0.25)',lineWidth:2,priceLineVisible:false});
 b.setData(d.rs.slice(-tf).map(function(x){return{time:x[0],value:x[1]}}));rsCh.timeScale().fitContent();}
var indC=[];
function drawInd(){indC.forEach(function(c){c.remove()});indC=[];var d=A.data[cur];if(!L||!d.rsi){$('ind-rsi').innerHTML='';$('ind-macd').innerHTML='';return}
 var cut=function(a){return a.slice(-tf).map(function(x){return{time:x[0],value:x[1]}})};
 var r=base($('ind-rsi'));var rl=r.addLineSeries({color:'#a78bfa',lineWidth:1.5,priceLineVisible:false});rl.setData(cut(d.rsi));
 rl.createPriceLine({price:70,color:'rgba(239,68,68,0.6)',lineStyle:2,lineWidth:1,axisLabelVisible:true,title:''});
 rl.createPriceLine({price:50,color:'rgba(148,163,184,0.5)',lineStyle:2,lineWidth:1,axisLabelVisible:false,title:''});
 rl.createPriceLine({price:30,color:'rgba(34,197,94,0.6)',lineStyle:2,lineWidth:1,axisLabelVisible:true,title:''});
 r.timeScale().fitContent();indC.push(r);
 var m=base($('ind-macd'));var h=m.addHistogramSeries({priceLineVisible:false,lastValueVisible:false});
 h.setData(d.macdh.slice(-tf).map(function(x){return{time:x[0],value:x[1],color:x[1]>=0?'rgba(34,197,94,0.5)':'rgba(239,68,68,0.5)'}}));
 var ml=m.addLineSeries({color:'#3b82f6',lineWidth:1.5,priceLineVisible:false,lastValueVisible:false});ml.setData(cut(d.macd));
 var ms=m.addLineSeries({color:'#f5b942',lineWidth:1.5,priceLineVisible:false,lastValueVisible:false});ms.setData(cut(d.macds));
 m.timeScale().fitContent();indC.push(m);}
function select(s){cur=s;['head','sig','plan','about','ind'].forEach(function(k){var t=$('t-'+k+'-'+s);$('p-'+k).innerHTML=t?t.innerHTML:''});
 document.querySelectorAll('.wl-row').forEach(function(r){r.classList.toggle('on',r.dataset.s===s)});
 $('tab-plan').style.display=A.data[s].index?'none':'';if(A.data[s].index&&tab==='plan')setTab('sig');
 draw();if(tab==='rs')drawRS();if(tab==='ind')drawInd();}
function setTab(t){tab=t;document.querySelectorAll('.tab').forEach(function(b){b.classList.toggle('on',b.dataset.t===t)});
 document.querySelectorAll('.tp').forEach(function(p){p.classList.toggle('on',p.id==='tp-'+t)});if(t==='rs')drawRS();if(t==='ind')drawInd();}
document.querySelectorAll('.wl-row').forEach(function(r){r.addEventListener('click',function(){select(r.dataset.s);
 if(window.innerWidth<980)$('mainpanel').scrollIntoView({behavior:'smooth'})})});
document.querySelectorAll('.tab').forEach(function(b){b.addEventListener('click',function(){setTab(b.dataset.t)})});
document.querySelectorAll('[data-tf]').forEach(function(b){b.addEventListener('click',function(){tf=+b.dataset.tf;
 document.querySelectorAll('[data-tf]').forEach(function(x){x.classList.toggle('on',x===b)});draw();if(tab==='rs')drawRS();if(tab==='ind')drawInd()})});
document.querySelectorAll('[data-opt]').forEach(function(b){b.addEventListener('click',function(){var k=b.dataset.opt;opt[k]=opt[k]?0:1;
 b.classList.toggle('on',!!opt[k]);draw()})});
init();select(A.order[0]);
if(L&&A.equity&&$('eq')){var e=base($('eq'));e.applyOptions({rightPriceScale:{mode:1},handleScroll:false,handleScale:false,
 localization:{priceFormatter:function(p){return '₹'+Math.round(p).toLocaleString('en-IN')}}});
 var a=e.addAreaSeries({lineColor:'#3b82f6',topColor:'rgba(59,130,246,0.3)',bottomColor:'rgba(59,130,246,0)',lineWidth:2,priceLineVisible:false});
 a.setData(A.equity.t.map(function(t,i){return{time:t,value:A.equity.s[i]}}));
 var n=e.addLineSeries({color:'#8a94a7',lineWidth:1.5,priceLineVisible:false,lastValueVisible:false});
 n.setData(A.equity.t.map(function(t,i){return{time:t,value:A.equity.n[i]}}));e.timeScale().fitContent();}
})();
function copyText(id,btn){var t=document.getElementById(id).innerText;var s=btn.nextElementSibling;
function done(){s.textContent='Copied';setTimeout(function(){s.textContent=''},1500)}
if(navigator.clipboard&&window.isSecureContext){navigator.clipboard.writeText(t).then(done)}else{var a=document.createElement('textarea');
a.value=t;document.body.appendChild(a);a.select();try{document.execCommand('copy');done()}catch(e){}a.remove()}}
"""


def _chg(c: list) -> tuple[float, float]:
    if len(c) < 2:
        return math.nan, math.nan
    last, prev = c[-1][4], c[-2][4]
    return last, (last / prev - 1) * 100


def _logo(sym: str, logo: str, cls: str = "clogo") -> str:
    img = f'<img alt="" src="{logo}">' if logo else ""
    return f'<span class="{cls}">{esc(sym[:2])}{img}</span>'


def _signal_table(rows) -> str:
    body = "".join(f'<tr><td>{esc(n)}<div class="hint">{esc(h)}</div></td><td>{esc(r)}</td>'
                   f'<td><span class="sig {esc(s)}">{esc(s)}</span></td></tr>' for n, r, s, h in rows)
    return ('<table class="sigt"><thead><tr><th>Indicator</th><th>Today</th><th>Signal</th></tr></thead>'
            f'<tbody>{body}</tbody></table>')


def _plan(w, watch: bool, pick=None) -> str:
    lv = w.levels
    if not lv:
        return ""
    qty = lv["qty"]
    qty_txt = f'{qty} share{"" if qty == 1 else "s"}, {inr(lv["amount"])}' if qty else "1 share costs more than your per-stock amount"
    aim = (f'<div><div class="l">Target</div><div class="v green">{inr(lv["aim"], 2)}</div>'
           f'<div class="s">+{lv["aim_pct"]:.0f}%, typical win</div></div>') if lv.get("aim") else ""
    order = ""
    if pick is not None:
        order = (f'<pre class="order" id="o-{esc(w.symbol)}">{esc(pick.order_text)}</pre>'
                 f'<button onclick="copyText(\'o-{esc(w.symbol)}\',this)">Copy Kite order</button><span class="copied"></span>')
    return (f'<div class="ph">{"If the market turns strong" if watch else "Your plan"}</div><div class="pgrid">'
            f'<div><div class="l">Buy up to</div><div class="v blue">{inr(lv["buy"], 2)}</div><div class="s">limit order</div></div>'
            f'<div><div class="l">Stop loss</div><div class="v red">{inr(lv["stop"], 2)}</div><div class="s">-{lv["stop_pct"]:.0f}%</div></div>'
            f'{aim}<div><div class="l">Quantity</div><div class="v">{qty}</div><div class="s">{qty_txt}</div></div></div>'
            '<div class="ph" style="margin-top:14px">Sell when any of these happens</div><ul class="rules">'
            f'<li>Price falls to <b>{inr(lv["stop"], 2)}</b> (stop loss, Kite sells it for you)</li>'
            '<li>It drops out of the <b>Top 10</b> on a check-in day (1st or 15th)</li>'
            '<li>The market turns weak on a check-in day: <b>sell everything</b></li></ul>' + order)


def _templates(w, d: dict, watch: bool, pick=None) -> str:
    last, chg = _chg(d["c"])
    brands = "".join(f"<span>{esc(b)}</span>" for b in w.brands)
    head = (f'{_logo(w.symbol, w.logo)}<div class="sid"><div class="sym">{esc(w.symbol)}<small>NSE</small></div>'
            f'<div class="co">{esc(w.company)}</div></div>'
            f'<div class="px"><b>{inr(last, 2)}</b><span class="{"up" if chg >= 0 else "dn"}">{chg:+.2f}% today</span></div>'
            f'<span class="vd {esc(w.overall)}">{esc(VERDICT.get(w.overall, (w.overall,))[0])}</span>'
            + (f'<div class="brands">{brands}</div>' if brands else ""))
    about = ((f'<div class="meta">{esc(w.meta)}</div>' if w.meta else "")
             + (f'<p class="about">{esc(w.about)} <span class="meta">(Yahoo Finance)</span></p>' if w.about else "")
             + '<ul class="rules">' + "".join(f"<li>{esc(r)}</li>" for r in w.reasons) + "</ul>"
             + f'<div class="risk">{esc(w.risk)}</div>')
    sid = esc(w.symbol)
    n_buy = sum(1 for r in w.signals if r[2] == "BUY")
    n_stock = len(w.signals) - 1
    n_pass = sum(1 for r in w.signals[1:-1] if r[2] == "BUY")
    sig = (f'<div class="how-got"><b>How {esc(w.symbol)} got on the radar</b><br>'
           f'Passed {n_pass} of {n_stock - 1} trend checks and ranks <b>#{w.rank}</b> by momentum '
           f'(its rise over 3, 6 and 12 months against all Nifty 100 stocks). '
           f'{esc(VERDICT.get(w.overall, ("", ""))[1])}.</div>'
           f'<p class="meta" style="margin:10px 0 8px">These are the rules Momentum Radar actually uses '
           f'({n_buy} of {len(w.signals)} say BUY).</p>' + _signal_table(w.signals))
    ind_t = (f'<p class="meta" style="margin:0 0 8px"><b>{w.second_agree} of {len(w.second)}</b> popular indicators agree '
             'with BUY. These are a second opinion for checking: they are not part of the tested rules.</p>'
             + _signal_table(w.second))
    return (f'<template id="t-head-{sid}">{head}</template><template id="t-sig-{sid}">{sig}</template>'
            f'<template id="t-plan-{sid}">{_plan(w, watch, pick)}</template><template id="t-about-{sid}">{about}</template>'
            f'<template id="t-ind-{sid}">{ind_t}</template>')


def _nifty_templates(d: dict, regime_on: bool) -> str:
    last, chg = _chg(d["c"])
    above, fast_ok = d["last"] > d["slow_last"], d["fast_last"] > d["slow_last"]
    rows = [("Nifty vs 200-day average", f'{(d["last"] / d["slow_last"] - 1) * 100:+.1f}%', "BUY" if above else "SELL",
             "Above = long-term trend up"),
            ("50-day vs 200-day average", "Above" if fast_ok else "Below", "BUY" if fast_ok else "SELL",
             "Above = trend confirmed"),
            ("Result", "Strong" if regime_on else "Weak", "BUY" if regime_on else "WAIT",
             "Both must be BUY before buying any stock")]
    word = "STRONG" if regime_on else "WEAK"
    head = (f'<span class="clogo idx">N50</span><div class="sid"><div class="sym">NIFTY 50<small>INDEX</small></div>'
            f'<div class="co">The overall market</div></div>'
            f'<div class="px"><b>{inr(last, 2, symbol=False)}</b><span class="{"up" if chg >= 0 else "dn"}">{chg:+.2f}% today</span></div>'
            f'<span class="vd {word}">MARKET {word}</span>')
    sig = ('<p class="meta" style="margin:0 0 8px">We only buy stocks when the whole market is strong.</p>'
           + _signal_table(rows))
    about = ('<p class="about">The Nifty 50 is the index of India\'s 50 biggest companies. When it is in an uptrend, most '
             'stocks rise with it. When it is weak, even strong stocks tend to fall, so Momentum Radar waits.</p>')
    return (f'<template id="t-head-NIFTY">{head}</template><template id="t-sig-NIFTY">{sig}</template>'
            f'<template id="t-plan-NIFTY"></template><template id="t-about-NIFTY">{about}</template>'
            '<template id="t-ind-NIFTY"><p class="meta">Second-opinion indicators are shown for stocks only.</p></template>')


def build_dashboard_html(ctx: dict, cfg: dict) -> str:
    st = ctx["backtest_status"]
    regime_on, tomorrow = ctx["regime_on"], ctx["checkin_next"]
    checkin_day, data_day = ctx["next_checkin"], ctx["data_date"]
    picks, holdings = ctx["picks"], ctx["holdings"]
    failed = st is not None and not st["passed"]
    charts = ctx.get("charts", {}) or {}
    rows = ctx.get("watch_why") or []
    pick_map = ctx.get("pick_map") or {p.symbol: p for p in picks}
    brand = (cfg.get("brand", {}).get("name", "Momentum Radar"), cfg.get("brand", {}).get("tagline", ""))
    keep_n = cfg["portfolio"]["keep_if_rank_within"]

    # ---- status strip
    if failed:
        big, tone, txt = "Do not trade this", "red", "The 12-year test shows no edge since 2021."
    elif not regime_on:
        big, tone = "Don't buy now", "red"
        txt = ("The overall market is weak. Tomorrow, sell stocks you bought with this method and keep the money aside."
               if tomorrow else f"The overall market is weak. Keep your money aside. If you own stocks from this method, "
                                f"sell them on {checkin_day:%a %d %b}.")
    elif tomorrow:
        big, tone = "Action tomorrow", "blue"
        sells = [h.symbol for h in holdings if h.action == "SELL"]
        parts = []
        if sells:
            parts.append("Sell " + ", ".join(sells))
        if picks:
            parts.append("Buy " + ", ".join(f"{p.symbol} ({p.qty})" for p in picks))
        if not holdings:
            parts.append(f"Sell anything not in the Top {keep_n}")
        txt = f"Before 9:15 am on {checkin_day:%a %d %b}: " + ". ".join(parts) + "."
    else:
        big, tone, txt = "Hold, no action today", "green", f"Next check-in {checkin_day:%a %d %b}. Stop losses on Kite work on their own."
    status = (f'<div class="status {tone}"><span class="big">{esc(big)}</span><span class="txt">{esc(txt)}</span>'
              f'<span class="pill"><i class="dot {"g" if regime_on else "r"}"></i>Market {"strong" if regime_on else "weak"}</span>'
              f'<span class="pill">Next check-in {checkin_day:%a %d %b}</span><span class="pill">Prices {data_day:%d %b %Y}</span></div>')
    fn = ctx.get("funnel")
    funnel = ""
    if fn:
        steps = [(fn["scanned"], "Nifty 100 stocks scanned"), (fn["uptrend"], "in a healthy uptrend"),
                 (fn["momentum"], "in the top 30% for momentum"), (fn["both"], "pass both"),
                 (fn["top"], "on the watchlist"), (fn["buy"], "to buy" if fn["market_on"] else "to buy (market weak)")]
        funnel = ('<div class="funnel"><span class="fh">How today&#39;s radar was built</span>'
                  + "".join(f'<span class="fs"><b>{n}</b>{esc(t)}</span>' for n, t in steps) + "</div>")
    banner = ""
    if failed:
        banner = (f'<div class="banner red"><span class="big">{FAILED_BANNER}</span>'
                  f'<p>{esc("; ".join(st.get("reasons", [])))}. Do not trade these picks with real money.</p></div>')

    # ---- ticker tape + watchlist
    order, tape, wl, tpl = [], [], [], []
    nifty = charts.get("NIFTY")
    if nifty:
        last, chg = _chg(nifty["c"])
        order.append("NIFTY")
        tape.append(f'<span class="ti"><b>NIFTY 50</b>{inr(last, 2, symbol=False)} <span class="{"up" if chg >= 0 else "dn"}">{chg:+.2f}%</span></span>')
        word = "STRONG" if regime_on else "WEAK"
        wl.append(f'<div class="wl-row" data-s="NIFTY"><span class="wl-sym"><i>N50</i><span><b>NIFTY 50</b><em>Market</em></span></span>'
                  f'<span>{inr(last, 0, symbol=False)}</span><span class="{"up" if chg >= 0 else "dn"}">{chg:+.2f}%</span>'
                  f'<span class="mini {word}">{word[:4]}</span></div>')
        tpl.append(_nifty_templates(nifty, regime_on))
    for w in rows:
        d = charts.get(w.symbol)
        if not d:
            continue
        last, chg = _chg(d["c"])
        order.append(w.symbol)
        tape.append(f'<span class="ti"><b>{esc(w.symbol)}</b>{inr(last, 2, symbol=False)} '
                    f'<span class="{"up" if chg >= 0 else "dn"}">{chg:+.2f}%</span></span>')
        sub = w.brands[0] if w.brands else w.company
        img = f'<img alt="" src="{w.logo}">' if w.logo else f"<i>{esc(w.symbol[:2])}</i>"
        wl.append(f'<div class="wl-row" data-s="{esc(w.symbol)}"><span class="wl-sym">{img}<span><b>{w.rank}. {esc(w.symbol)}</b>'
                  f'<em>{esc(sub)}</em></span></span><span>{inr(last, 2, symbol=False)}</span>'
                  f'<span class="{"up" if chg >= 0 else "dn"}">{chg:+.2f}%</span><span class="mini {esc(w.overall)}">{esc(w.overall)}</span></div>')
        tpl.append(_templates(w, d, not regime_on, pick_map.get(w.symbol)))
    if order and len(order) > 1:
        order = order[1:2] + [o for o in order if o != order[1]]   # start on the top stock, Nifty stays selectable
    tape_html = (f'<div class="tape"><div class="tape-in">{"".join(tape)}{"".join(tape)}</div></div>') if tape else ""

    side = (f'<aside class="side"><div class="side-h">Watchlist <span>Top {keep_n} by momentum</span></div>'
            '<div class="wl-head"><span>Symbol</span><span>Last</span><span>Chg</span><span>Signal</span></div>'
            f'<div class="wl">{"".join(wl)}</div></aside>')
    main = ('<section class="main" id="mainpanel"><div class="symhead" id="p-head"></div>'
            '<div class="toolbar"><button class="tb" data-tf="63">3M</button><button class="tb" data-tf="126">6M</button>'
            '<button class="tb on" data-tf="250">1Y</button><button class="tb" data-tf="500">2Y</button><span class="sep"></span>'
            '<button class="tb tog on" data-opt="ma50">MA 50</button><button class="tb tog on" data-opt="ma200">MA 200</button>'
            '<button class="tb tog on" data-opt="vol">Volume</button><button class="tb tog on" data-opt="plan">Buy / Stop / Target</button></div>'
            '<div class="ohlc" id="ohlc"></div><div id="chart"></div>'
            '<div class="tabs"><button class="tab on" data-t="sig">Radar rules</button><button class="tab" data-t="ind">Indicators</button>'
            '<button class="tab" id="tab-plan" data-t="plan">Plan</button>'
            '<button class="tab" data-t="rs">vs Nifty</button><button class="tab" data-t="about">About</button></div>'
            '<div class="tp on" id="tp-sig"><div id="p-sig"></div></div>'
            '<div class="tp" id="tp-ind"><div id="p-ind"></div><div class="ind-c"><div class="tl">RSI (14): above 70 stretched, below 50 weak</div>'
            '<div id="ind-rsi"></div><div class="tl" style="margin-top:10px">MACD (12, 26, 9): bars above zero = rising momentum</div>'
            '<div id="ind-macd"></div></div></div><div class="tp" id="tp-plan"><div id="p-plan"></div></div>'
            '<div class="tp" id="tp-rs"><p class="meta" style="margin:0 0 6px">Above 100 = beating the Nifty 50 over this period.</p>'
            '<div id="rs"></div></div><div class="tp" id="tp-about"><div id="p-about"></div></div></section>') if order else ""
    layout = f'<div class="layout">{main}{side}</div>' if order else '<p class="muted">No data.</p>'

    # ---- bottom cards: proof, holdings, how
    proof = ""
    if st is not None:
        proof = (f'<div class="card2"><h3>Does it work?</h3><div class="tiles">'
                 f'<div class="tile"><div class="tl">12-year test</div><div class="tv {"red" if failed else "green"}">'
                 f'{"FAILED" if failed else "PASSED"}</div><div class="tn">{inr(st["oos_expectancy_inr"])} per trade</div></div>'
                 f'<div class="tile"><div class="tl">Per year since 2021</div><div class="tv">{pct(st.get("oos_cagr"), 0, signed=True)}</div>'
                 f'<div class="tn">Nifty {pct(st.get("nifty_oos_cagr"), 0, signed=True)}</div></div>'
                 f'<div class="tile"><div class="tl">Worst fall</div><div class="tv red">{pct(st.get("oos_max_dd_pct"), 0)}</div>'
                 f'<div class="tn">Nifty {pct(st.get("nifty_oos_max_dd_pct"), 0)}</div></div></div>'
                 + ('<div id="eq"></div><div class="lg"><span><i style="background:#3b82f6"></i>₹1,00,000 with Momentum Radar</span>'
                    '<span><i style="background:#8a94a7"></i>Nifty 50</span></div>' if st.get("equity_weekly") else "")
                 + '<a class="more" href="backtest.html">Full 12-year test &rarr;</a></div>')
    hold = ""
    if holdings:
        hold = ('<div class="card2"><h3>Your holdings</h3>' + "".join(
            f'<div style="display:flex;justify-content:space-between;gap:8px;padding:6px 0;border-bottom:1px solid var(--line)">'
            f'<b>{esc(h.symbol)}</b><span class="sig {"SELL" if h.action in ("SELL", "STOP HIT") else "HOLD"}">{esc(h.action)}</span></div>'
            f'<div class="meta" style="margin:4px 0 8px">{esc(h.detail)}</div>' for h in holdings) + "</div>")
    how = ('<div class="card2"><h3>How Momentum Radar works</h3><ul class="rules">'
           '<li>Buy only when the whole market is strong</li><li>Pick the 5 fastest-rising Nifty 100 stocks</li>'
           f'<li>{cfg["trade"].get("stop_pct", 15):g}% stop loss on each</li><li>Review on the 1st and 15th</li></ul>'
           '<p style="margin:10px 0 0"><a class="more" href="how.html">Read the full explanation &rarr;</a></p></div>')
    notes = [esc(n) for n in ctx.get("notes", [])]
    notes.append("The 12-year test uses today's Nifty 100 members (survivorship bias): real results are likely lower.")
    notes.append("Charts by TradingView Lightweight Charts (open source). Logos from company websites. Business info from Yahoo Finance.")
    notes_html = ('<details class="notes" style="margin-top:16px"><summary>Notes</summary><ul class="small muted">'
                  + "".join(f"<li>{n}</li>" for n in notes) + "</ul></details>")

    body = (f"{status}{banner}{funnel}{layout}<div class=\"cards\">{proof}{hold}{how}</div>{notes_html}"
            f'<div class="small muted" style="margin-top:10px">Updated {ctx["generated"]:%d %b %Y, %I:%M %p} IST</div>'
            + "".join(tpl))
    app = {"order": order, "data": {}, "equity": (st or {}).get("equity_weekly")}
    for k in order:
        d = dict(charts[k])
        if k == "NIFTY":
            d["index"] = True
            d.pop("rs", None)
        app["data"][k] = d
    head = f'<script src="{LIB_URL}"></script>' if order else ""
    js = "window.__APP=" + json.dumps(app, separators=(",", ":")) + ";" + APP_JS
    html = page("Dashboard", body, js, brand=brand, head_extra=head, active="index.html")
    html = html.replace("</style>", DASH_CSS + "</style>", 1)
    return html.replace('<div class="wrap">', '<div class="wrap">' + tape_html, 1)

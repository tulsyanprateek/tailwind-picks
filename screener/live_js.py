"""Browser script for live prices and the freshness bar on the dashboard."""

LIVE_CSS = """
.fresh{display:flex;align-items:center;gap:10px;background:var(--panel);border:1px solid var(--line);border-radius:12px;
padding:9px 12px;margin-bottom:12px}
.fdot{flex:none;width:10px;height:10px;border-radius:50%;background:#64748b}
.fresh.live .fdot{background:var(--green);animation:pulse 1.6s infinite}.fresh.closed .fdot{background:#60a5fa}
.fresh.old .fdot{background:var(--amber)}.fresh.old{border-color:rgba(245,185,66,.5)}
@keyframes pulse{0%{box-shadow:0 0 0 0 rgba(34,197,94,.6)}100%{box-shadow:0 0 0 9px rgba(34,197,94,0)}}
.ftxt{flex:1;min-width:0}.ftxt b{display:block;font-size:13.5px}.ftxt span{display:block;font-size:11.5px;color:var(--muted)}
.fbtn{flex:none;background:var(--panel2);color:#d5dbe6;border:1px solid var(--line);font-size:12.5px;padding:6px 10px}
.flash{animation:flash 1s}@keyframes flash{0%{background:rgba(59,130,246,.35)}100%{background:transparent}}
"""

LIVE_JS = r"""
(function(){
var C=window.__LIVE||{};var box=document.getElementById('fresh');if(!box)return;
var A=document.getElementById('fresh-a'),last=null,failed=false;
function ist(d){return new Date(d.getTime()+(d.getTimezoneOffset()+330)*60000)}
function fmtT(d){var i=ist(d),h=i.getHours(),m=i.getMinutes();return ((h%12)||12)+':'+(m<10?'0':'')+m+(h<12?' am':' pm')}
var DN=['Sun','Mon','Tue','Wed','Thu','Fri','Sat'],MN=['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
function fmtD(d){var i=ist(d);return DN[i.getDay()]+' '+i.getDate()+' '+MN[i.getMonth()]}
function ago(ms){var m=Math.round(ms/60000);if(m<1)return 'just now';if(m<60)return m+' min ago';var h=Math.round(m/60);if(h<48)return h+' h ago';return Math.round(h/24)+' days ago'}
function marketOpen(now){var i=ist(now),d=i.getDay(),t=i.getHours()*60+i.getMinutes();return d>=1&&d<=5&&t>=555&&t<=930}
function lastClose(now){var i=ist(now);var c=new Date(i);c.setHours(15,30,0,0);if(i<c)c.setDate(c.getDate()-1);
 while(c.getDay()===0||c.getDay()===6)c.setDate(c.getDate()-1);return new Date(c.getTime()-(now.getTimezoneOffset()+330)*60000)}
function num(v,d,s){return (s?'₹':'')+Number(v).toLocaleString('en-IN',{minimumFractionDigits:d,maximumFractionDigits:d})}
function paint(){var now=new Date();box.className='fresh';
 if(!last){if(failed){box.classList.add('old');A.textContent='Showing closing prices of '+C.close+'. Live prices could not be loaded.'}return}
 var t=new Date(last.as_of),age=now-t;
 if(marketOpen(now)){if(age<=20*60000){box.classList.add('live');A.textContent='LIVE · prices from '+fmtT(t)+' ('+ago(age)+')'}
  else{box.classList.add('old');A.textContent='No new prices since '+fmtD(t)+', '+fmtT(t)+' (market holiday or delay)'}}
 else if(t>=new Date(lastClose(now).getTime()-20*60000)){box.classList.add('closed');A.textContent='Market closed · final prices of '+fmtD(t)}
 else{box.classList.add('old');A.textContent='Prices may be old · last update '+fmtD(t)+', '+fmtT(t)}}
function apply(){var q=last.quotes||{};
 document.querySelectorAll('[data-lp]').forEach(function(e){var x=q[e.dataset.lp];if(!x)return;var v=num(x.price,+e.dataset.d,e.dataset.s);
  if(e.textContent!==v){e.textContent=v;e.classList.remove('flash');void e.offsetWidth;e.classList.add('flash')}});
 document.querySelectorAll('[data-lc]').forEach(function(e){var x=q[e.dataset.lc];if(!x||x.chg==null)return;
  e.textContent=(x.chg>=0?'+':'')+x.chg.toFixed(+e.dataset.d)+'%';e.classList.toggle('up',x.chg>=0);e.classList.toggle('dn',x.chg<0)});}
function load(){if(!C.url){failed=true;paint();return}
 fetch(C.url+'?t='+Math.floor(Date.now()/60000),{cache:'no-store'}).then(function(r){if(!r.ok)throw 0;return r.json()}).then(function(j){
  last=j;failed=false;apply();paint();
  if(j.page_generated&&C.gen&&new Date(j.page_generated)-new Date(C.gen)>60000){var k='tp-reload';
   try{if(sessionStorage.getItem(k)!==j.page_generated){sessionStorage.setItem(k,j.page_generated);location.replace(location.pathname+'?v='+Date.now())}}catch(e){}}
 }).catch(function(){failed=true;paint()})}
load();setInterval(load,60000);setInterval(paint,20000);
document.addEventListener('visibilitychange',function(){if(!document.hidden)load()});
})();
"""

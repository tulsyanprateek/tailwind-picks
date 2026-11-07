"""Chart data (candles, averages, strength vs Nifty) for the interactive charts on the page.

The page draws them with TradingView's open-source Lightweight Charts library.
"""
from __future__ import annotations

import math

import pandas as pd

from . import indicators as ind

LIB_URL = "https://cdn.jsdelivr.net/npm/lightweight-charts@4.2.0/dist/lightweight-charts.standalone.production.js"


def _t(d: pd.Timestamp) -> str:
    return d.strftime("%Y-%m-%d")


def _line(s: pd.Series) -> list:
    return [[_t(d), round(float(v), 2)] for d, v in s.items() if not math.isnan(v)]


def stock_payload(df: pd.DataFrame, index_df: pd.DataFrame, data_ts: pd.Timestamp,
                  sessions: int = 250, stop: float | None = None, limit: float | None = None) -> dict:
    full = df.loc[:data_ts]
    ma50 = ind.sma(full["Close"], 50).iloc[-sessions:]
    ma200 = ind.sma(full["Close"], 200).iloc[-sessions:]
    d = full.iloc[-sessions:]
    candles = [[_t(t), round(r.Open, 2), round(r.High, 2), round(r.Low, 2), round(r.Close, 2), int(r.Volume)]
               for t, r in d.iterrows()]
    nifty = index_df["Close"].reindex(d.index).ffill()
    rs = (d["Close"] / d["Close"].iloc[0]) / (nifty / nifty.iloc[0]) * 100
    return {"c": candles, "ma50": _line(ma50), "ma200": _line(ma200), "rs": _line(rs),
            "stop": stop, "limit": limit}


def index_payload(index_df: pd.DataFrame, data_ts: pd.Timestamp, cfg: dict, sessions: int = 250) -> dict:
    full = index_df.loc[:data_ts]
    fast = ind.sma(full["Close"], cfg["regime"]["sma_fast"]).iloc[-sessions:]
    slow = ind.sma(full["Close"], cfg["regime"]["sma_slow"]).iloc[-sessions:]
    d = full.iloc[-sessions:]
    candles = [[_t(t), round(r.Open, 2), round(r.High, 2), round(r.Low, 2), round(r.Close, 2), 0]
               for t, r in d.iterrows()]
    return {"c": candles, "ma50": _line(fast), "ma200": _line(slow),
            "last": round(float(d["Close"].iloc[-1]), 2),
            "slow_last": round(float(slow.iloc[-1]), 2), "fast_last": round(float(fast.iloc[-1]), 2)}


CHART_JS = r"""
(function(){
var D=window.__CHARTS||{};
function ready(){
 if(!window.LightweightCharts){document.querySelectorAll('.chart').forEach(function(e){e.innerHTML='<div class="nochart">Charts need an internet connection.</div>'});return;}
 var L=window.LightweightCharts;
 var all=[];
 function mk(el){var ch=L.createChart(el,{width:el.clientWidth,height:el.clientHeight,layout:{background:{type:'solid',color:'transparent'},textColor:'#8b95a7',fontSize:11},
  grid:{vertLines:{visible:false},horzLines:{color:'rgba(255,255,255,0.05)'}},rightPriceScale:{borderVisible:false},
  timeScale:{borderVisible:false,fixLeftEdge:true,fixRightEdge:true},crosshair:{mode:0},handleScroll:false,handleScale:false});all.push([ch,el]);return ch;}
 function line(ch,data,color,w){var s=ch.addLineSeries({color:color,lineWidth:w||1.5,priceLineVisible:false,lastValueVisible:false,crosshairMarkerVisible:false});
  s.setData(data.map(function(x){return{time:x[0],value:x[1]}}));return s;}
 document.querySelectorAll('.chart').forEach(function(el){
  var d=D[el.dataset.k],kind=el.dataset.kind;if(!d)return;var ch=mk(el);
  if(kind==='equity'){
   var a=ch.addAreaSeries({lineColor:'#60a5fa',topColor:'rgba(96,165,250,0.35)',bottomColor:'rgba(96,165,250,0)',lineWidth:2,priceLineVisible:false});
   a.setData(d.t.map(function(t,i){return{time:t,value:d.s[i]}}));
   line(ch,d.t.map(function(t,i){return[t,d.n[i]]}),'#94a3b8',1.5);
   ch.applyOptions({rightPriceScale:{mode:1},localization:{priceFormatter:function(p){return '₹'+Math.round(p).toLocaleString('en-IN')}}});ch.timeScale().fitContent();return;}
  if(kind==='rs'){
   var b=ch.addBaselineSeries({baseValue:{type:'price',price:100},topLineColor:'#34d399',topFillColor1:'rgba(52,211,153,0.28)',topFillColor2:'rgba(52,211,153,0.02)',
    bottomLineColor:'#fb7185',bottomFillColor1:'rgba(251,113,133,0.02)',bottomFillColor2:'rgba(251,113,133,0.28)',lineWidth:2,priceLineVisible:false});
   b.setData(d.rs.map(function(x){return{time:x[0],value:x[1]}}));ch.timeScale().fitContent();return;}
  var c=ch.addCandlestickSeries({upColor:'#34d399',downColor:'#fb7185',borderVisible:false,wickUpColor:'#34d399',wickDownColor:'#fb7185'});
  c.setData(d.c.map(function(x){return{time:x[0],open:x[1],high:x[2],low:x[3],close:x[4]}}));
  if(kind!=='index'){var v=ch.addHistogramSeries({priceScaleId:'',priceFormat:{type:'volume'},lastValueVisible:false,priceLineVisible:false});
   v.priceScale().applyOptions({scaleMargins:{top:0.82,bottom:0}});
   v.setData(d.c.map(function(x){return{time:x[0],value:x[5],color:x[4]>=x[1]?'rgba(52,211,153,0.35)':'rgba(251,113,133,0.35)'}}));}
  line(ch,d.ma50,'#fbbf24',1.5);line(ch,d.ma200,'#a78bfa',2);
  if(d.stop)c.createPriceLine({price:d.stop,color:'#fb7185',lineWidth:1,lineStyle:2,axisLabelVisible:true,title:'Stop loss'});
  if(d.limit)c.createPriceLine({price:d.limit,color:'#60a5fa',lineWidth:1,lineStyle:2,axisLabelVisible:true,title:'Buy limit'});
  ch.timeScale().fitContent();
 });
 function fit(){all.forEach(function(p){p[0].applyOptions({width:p[1].clientWidth,height:p[1].clientHeight});p[0].timeScale().fitContent();});}
 fit();var t;window.addEventListener('resize',function(){clearTimeout(t);t=setTimeout(fit,150);});
}
if(document.readyState==='loading'){document.addEventListener('DOMContentLoaded',ready)}else{ready()}
})();
"""

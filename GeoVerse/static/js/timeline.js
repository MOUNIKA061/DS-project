// timeline.js
// Renders a timeline map using Leaflet and the /api/timeline endpoint.
const TIMELINE_POLL = 5000;
const USERID = window.USERID || document.getElementById('timeline-root')?.dataset?.userid;

let map, markersLayer, polyline, markers = [], currentData = [];

function fmtTime(ts){ return new Date(ts*1000).toLocaleString(); }

function colorForSource(src){
  if(!src) return '#3388ff';
  src = src.toLowerCase();
  if(src === 'online') return '#16a34a'; // green
  if(src === 'offline' || src === 'queued') return '#f59e0b'; // amber
  if(src === 'synced') return '#2563eb'; // blue
  return '#6b7280';
}

function clearMap(){
  if(markersLayer){ markersLayer.clearLayers(); }
  markers = [];
  if(polyline){ polyline.remove(); polyline = null; }
}

function buildList(timeline){
  const list = document.getElementById('timeline-list');
  list.innerHTML = '';
  // newest first in list
  for(let i=timeline.length-1;i>=0;i--){
    const p = timeline[i];
    const li = document.createElement('li');
    li.className = 'timeline-item';
    li.tabIndex = 0;
    li.dataset.ts = p.timestamp;
    li.innerHTML = `<div class="ti-time">${fmtTime(p.timestamp)}</div>
                    <div class="ti-coords">${Number(p.lat).toFixed(5)}, ${Number(p.lon).toFixed(5)}</div>
                    <div class="ti-src">${p.source || 'online'}</div>`;
    li.addEventListener('click', ()=>{
      // find marker by timestamp and focus
      const m = markers.find(x=>x.ts == p.timestamp && x.lat == p.lat && x.lon == p.lon);
      if(m){ map.setView([m.lat, m.lon], 15, {animate:true}); m.leaflet.openPopup(); }
    });
    // keyboard accessibility: Enter/Space to activate, arrows to move
    li.addEventListener('keydown', (ev)=>{
      if(ev.key === 'Enter' || ev.key === ' '){ ev.preventDefault(); li.click(); }
      if(ev.key === 'ArrowDown'){ ev.preventDefault(); if(li.nextElementSibling) li.nextElementSibling.focus(); }
      if(ev.key === 'ArrowUp'){ ev.preventDefault(); if(li.previousElementSibling) li.previousElementSibling.focus(); }
    });
    list.appendChild(li);
  }
}

function showToast(msg, timeout=2500){
  const t = document.getElementById('timeline-toast');
  if(!t) return;
  t.textContent = msg; t.style.display = 'block';
  t.classList.remove('toast-fade');
  setTimeout(()=>{ t.classList.add('toast-fade'); }, 100);
  setTimeout(()=>{ t.style.display = 'none'; t.classList.remove('toast-fade'); }, timeout+300);
}

function renderTimeline(timeline){
  clearMap();
  if(!timeline || timeline.length===0) return;
  // ensure chronological order (oldest->newest)
  timeline.sort((a,b)=>a.timestamp - b.timestamp);
  currentData = timeline;
  const latlngs = [];
  for(const p of timeline){
    const color = colorForSource(p.source);
    const marker = L.circleMarker([p.lat, p.lon], {radius:6, color:color, fillColor:color, fillOpacity:0.9});
    marker.bindPopup(`<b>${fmtTime(p.timestamp)}</b><br/>${Number(p.lat).toFixed(6)}, ${Number(p.lon).toFixed(6)}<br/>status: ${p.source}`);
    marker.ts = p.timestamp; marker.lat = p.lat; marker.lon = p.lon;
    marker.addTo(markersLayer);
    markers.push({ts:p.timestamp, lat:p.lat, lon:p.lon, leaflet:marker});
    latlngs.push([p.lat, p.lon]);
  }
  polyline = L.polyline(latlngs, {color:'#3b82f6', weight:3, opacity:0.8}).addTo(map);
  // highlight latest
  const last = timeline[timeline.length-1];
  if(last){
    const lastMarker = markers[markers.length-1];
    if(lastMarker && lastMarker.leaflet){ lastMarker.leaflet.setStyle({radius:9, weight:2}); }
  }
  buildList(timeline);
}

function renderFullTimeline(timeline){
  // show the full DLL timeline chronologically (oldest -> newest)
  const list = document.getElementById('full-timeline');
  if(!list) return;
  list.innerHTML = '';
  const sorted = (timeline || []).slice().sort((a,b)=>a.timestamp - b.timestamp);
  for(const p of sorted){
    const li = document.createElement('li');
    li.className = 'timeline-item';
    li.innerHTML = `<div class="ti-time">${fmtTime(p.timestamp)}</div>
                    <div class="ti-coords">${Number(p.lat).toFixed(6)}, ${Number(p.lon).toFixed(6)}</div>
                    <div class="ti-src">${p.source || 'online'}</div>`;
    li.addEventListener('click', ()=>{
      map.setView([p.lat, p.lon], 14, {animate:true});
    });
    list.appendChild(li);
  }
}

async function loadTimeline(){
  try{
    const res = await fetch(`/api/timeline?userid=${USERID}`);
    const j = await res.json();
    if(j.error) return;
    renderTimeline(j.timeline || []);
    renderFullTimeline(j.timeline || []);
  }catch(e){ console.error('loadTimeline', e); }
}

function parseInputToEpoch(v){
  if(!v) return NaN;
  v = v.trim();
  if(v === 'now') return Math.floor(Date.now()/1000);
  // relative hours like -24
  if(v.startsWith('-')){
    const h = parseFloat(v.slice(1));
    if(!isNaN(h)) return Math.floor(Date.now()/1000) - Math.floor(h*3600);
  }
  // numeric epoch (seconds or milliseconds)
  if(/^\d+$/.test(v)){
    if(v.length >= 13) return Math.floor(Number(v)/1000);
    return Number(v);
  }
  // Try Date.parse for flexible formats
  const parsed = Date.parse(v);
  if(!isNaN(parsed)) return Math.floor(parsed/1000);

  // Try common MM-DD-YYYY or MM/DD/YYYY with optional time
  let m = v.match(/^(\d{1,2})[-\/](\d{1,2})[-\/](\d{4})(?:[ T]+(\d{1,2}):(\d{2})(?::(\d{2}))?)?$/);
  if(m){
    const month = Number(m[1]), day = Number(m[2]), year = Number(m[3]);
    const hh = Number(m[4]||0), mm = Number(m[5]||0), ss = Number(m[6]||0);
    const dt = new Date(year, month-1, day, hh, mm, ss);
    return Math.floor(dt.getTime()/1000);
  }

  // Try YYYY-MM-DD with optional time
  let m2 = v.match(/^(\d{4})[-\/](\d{1,2})[-\/](\d{1,2})(?:[ T]+(\d{1,2}):(\d{2})(?::(\d{2}))?)?$/);
  if(m2){
    const year = Number(m2[1]), month = Number(m2[2]), day = Number(m2[3]);
    const hh = Number(m2[4]||0), mm = Number(m2[5]||0), ss = Number(m2[6]||0);
    const dt = new Date(year, month-1, day, hh, mm, ss);
    return Math.floor(dt.getTime()/1000);
  }

  return NaN;
}

async function doSearch(){
  const rawEl = document.getElementById('search-ts');
  if(!rawEl) return;
  const raw = rawEl.value.trim();
  const noResultsEl = document.getElementById('no-results');
  noResultsEl.style.display = 'none';

  if(!raw){ await loadTimeline(); return; }

  // If user typed strict pattern MM-DD-YYYY HH:MM:SS (24-hour), prefer exact search
  const strict = raw.match(/^(\d{1,2})-(\d{1,2})-(\d{4}) (\d{2}):(\d{2}):(\d{2})$/);
  let ts = parseInputToEpoch(raw);
  if(Number.isNaN(ts)){
    return alert('Unrecognized timestamp. Use MM-DD-YYYY HH:MM:SS or try one of the accepted formats.');
  }

  // For strict exact-input, try tight window first (+/-5s), otherwise behave same as before
  const tight = 5;
  const wide = 300;
  const res = await fetch(`/api/search?userid=${USERID}&start=${ts-tight}&end=${ts+tight}`);
  const j = await res.json();
  if(j.error) return;
  if(j.results && j.results.length>0){
    renderTimeline(j.results || []);
    return;
  }

  // If strict pattern used and no results, try a wider fallback and show toast
  const fr = await fetch(`/api/search?userid=${USERID}&start=${ts-wide}&end=${ts+wide}`);
  const fj = await fr.json();
  if(!fj.error && fj.results && fj.results.length>0){
    document.getElementById('debug-json').textContent = JSON.stringify(fj.results, null, 2); document.getElementById('debug-json').style.display = 'block';
    renderTimeline(fj.results || []);
    showToast('No exact match — showing nearby results');
    return;
  }

  document.getElementById('no-results').style.display = 'block';
}

function initMap(){
  map = L.map('map').setView([17.3850,78.4867], 12);
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {maxZoom:19}).addTo(map);
  markersLayer = L.layerGroup().addTo(map);
}

function init(){
  initMap();
  loadTimeline();
  document.getElementById('refresh-btn').addEventListener('click', loadTimeline);
  document.getElementById('search-btn').addEventListener('click', doSearch);
  document.getElementById('nearest-btn').addEventListener('click', async ()=>{
    const raw = document.getElementById('search-ts').value.trim();
    if(!raw) return alert('Enter a timestamp to find nearest');
    const ts = parseInputToEpoch(raw);
    if(Number.isNaN(ts)) return alert('Unrecognized timestamp');
    const res = await fetch(`/api/search-nearest?userid=${USERID}&ts=${ts}`);
    const j = await res.json();
    if(j.error) return alert(j.error);
    if(!j.results || j.results.length===0){ document.getElementById('no-results').style.display = 'block'; return; }
    document.getElementById('debug-json').textContent = JSON.stringify(j.results, null, 2); document.getElementById('debug-json').style.display = 'block';
    renderTimeline(j.results || []);
    showToast('Nearest result shown');
  });
  setInterval(loadTimeline, TIMELINE_POLL);
}

window.addEventListener('DOMContentLoaded', init);

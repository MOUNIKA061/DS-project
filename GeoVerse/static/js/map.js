// Minimal map wiring: fetch timeline and plot points
let map = L.map('map').setView([0,0], 2);
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
  maxZoom: 19,
}).addTo(map);

let markers = [];
let polyline = null;

async function loadTimeline(){
  const res = await fetch(`/api/timeline?userid=${USERID}`);
  const j = await res.json();
  if(j.error){ alert(j.error); return; }
  const pts = j.timeline;
  // clear
  markers.forEach(m=>map.removeLayer(m)); markers = [];
  if(polyline) map.removeLayer(polyline);
  const latlngs = pts.map(p => [p.lat, p.lon]);
  for(const p of pts){
    const color = p.source === 'offline' ? 'orange' : (p.source === 'synced' ? 'purple' : 'blue');
    const m = L.circleMarker([p.lat, p.lon], {radius:6, color:color}).addTo(map);
    m.bindPopup(`time:${new Date(p.timestamp*1000).toLocaleString()}<br>src:${p.source}`);
    markers.push(m);
  }
  if(latlngs.length>0){
    polyline = L.polyline(latlngs, {color: 'green'}).addTo(map);
    map.fitBounds(polyline.getBounds(), {padding:[20,20]});
  }
}

document.getElementById('gen-online').addEventListener('click', async ()=>{
  await fetch('/api/generate', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({userid: USERID, online: true, count:1})});
  await loadTimeline();
});

document.getElementById('gen-offline').addEventListener('click', async ()=>{
  await fetch('/api/generate', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({userid: USERID, online: false, count:1})});
  await loadTimeline();
});

document.getElementById('sync').addEventListener('click', async ()=>{
  await fetch('/api/sync', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({userid: USERID})});
  await loadTimeline();
});

loadTimeline();

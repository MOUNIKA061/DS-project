// Dashboard polling and UI wiring
const USERID = window.USERID || (window.USERID = document.getElementById('dashboard-root')?.dataset?.userid);
const POLL_INTERVAL = 5000; // 5s

function el(id){ return document.getElementById(id); }

async function fetchLatest(){
  const res = await fetch(`/api/latest-location?userid=${USERID}&count=5`);
  const j = await res.json();
  if(j.error){ console.error(j.error); return; }
  const latest = j.latest || [];
  if(latest.length>0){
    const cur = latest[latest.length-1];
    el('lat').textContent = Number(cur.lat).toFixed(6);
    el('lon').textContent = Number(cur.lon).toFixed(6);
    el('ts').textContent = new Date(cur.timestamp*1000).toLocaleString();
    el('loc-status').textContent = (cur.source || 'online');
  }
  // also show last 5 list
  const list = el('recent-list');
  if(list){
    list.innerHTML = '';
    latest.slice().reverse().forEach(p=>{
      const li = document.createElement('li');
      li.textContent = `${new Date(p.timestamp*1000).toLocaleTimeString()} — ${Number(p.lat).toFixed(4)}, ${Number(p.lon).toFixed(4)} (${p.source})`;
      list.appendChild(li);
    });
  }
}

async function fetchQueue(){
  const res = await fetch(`/api/offline-queue-count?userid=${USERID}`);
  const j = await res.json();
  if(j.error){ console.error(j.error); return; }
  el('queue-count').textContent = j.count;
  const syncBtn = el('sync-btn');
  if(j.count > 0){
    syncBtn.style.display = 'inline-block';
    syncBtn.classList.add('attention');
  } else {
    syncBtn.style.display = 'none';
    syncBtn.classList.remove('attention');
  }
}

async function fetchStatus(){
  const res = await fetch(`/api/user-status?userid=${USERID}`);
  const j = await res.json();
  if(j.error){ console.error(j.error); return; }
  const online = j.online;
  el('user-id').textContent = USERID;
  setStatusIndicator(online);
  el('toggle-online').textContent = online ? 'Go Offline' : 'Go Online';
}

async function syncOffline(){
  const btn = el('sync-btn');
  btn.disabled = true;
  btn.textContent = 'Syncing...';
  const res = await fetch('/api/sync-offline-data', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({userid: USERID})});
  const j = await res.json();
  console.log('synced', j);
  showToast(`Synced ${ (j.synced || []).length } items`);
  await fetchLatest();
  await fetchQueue();
  btn.disabled = false;
  btn.textContent = 'Sync Offline Data';
}

async function toggleOnline(){
  const current = el('status-indicator').textContent.includes('Online');
  const res = await fetch('/api/set-online', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({userid: USERID, online: !current})});
  const j = await res.json();
  if(j.ok){
    await fetchStatus();
    showToast(j.online ? 'Set to Online' : 'Set to Offline');
  }
}

function showToast(msg, timeout=2000){
  const t = el('toast');
  if(!t) return;
  t.textContent = msg; t.style.display = 'block';
  t.classList.remove('toast-fade');
  setTimeout(()=>{ t.classList.add('toast-fade'); }, 100);
  setTimeout(()=>{ t.style.display = 'none'; t.classList.remove('toast-fade'); }, timeout+300);
}

function setStatusIndicator(online){
  const ind = el('status-indicator');
  const dot = el('status-dot');
  if(ind) ind.textContent = online ? '🟢 Online' : '🔴 Offline';
  if(dot){
    dot.classList.toggle('online', online);
    dot.classList.toggle('offline', !online);
    if(online){ dot.classList.add('pulse'); setTimeout(()=>dot.classList.remove('pulse'), 1200); }
  }
}

function init(){
  // wire buttons
  el('sync-btn').addEventListener('click', syncOffline);
  el('go-timeline').addEventListener('click', ()=>{ location.href = `/dashboard?userid=${USERID}&view=timeline`; });
  el('toggle-online').addEventListener('click', toggleOnline);
  // copy userid
  const copyBtn = el('copy-userid');
  if(copyBtn){
    copyBtn.addEventListener('click', async ()=>{
      try{
        await navigator.clipboard.writeText(USERID);
        showToast('UserID copied to clipboard');
      }catch(e){
        const ta = document.createElement('textarea'); ta.value = USERID; document.body.appendChild(ta); ta.select(); document.execCommand('copy'); ta.remove(); showToast('UserID copied');
      }
    });
  }
  // initial load
  fetchLatest(); fetchQueue(); fetchStatus();
  setInterval(()=>{ fetchLatest(); fetchQueue(); fetchStatus(); }, POLL_INTERVAL);
}

window.addEventListener('DOMContentLoaded', init);

async function fetchJson(url, token) {
  const r = await fetch(url, { headers: { 'Authorization': `Bearer ${token}` } });
  if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
  return r.json();
}

function val(id) { return document.getElementById(id).value.trim(); }

document.getElementById('loadSummary').addEventListener('click', async () => {
  const base = val('apiBase');
  const token = val('adminToken');
  const since = val('since');
  const until = val('until');
  const qp = new URLSearchParams();
  if (since) qp.set('since', since);
  if (until) qp.set('until', until);
  try {
    const data = await fetchJson(`${base}/analytics/summary?${qp.toString()}`, token);
    document.getElementById('summary').textContent = JSON.stringify(data, null, 2);
  } catch (e) {
    document.getElementById('summary').textContent = `Error: ${e.message}`;
  }
});

document.getElementById('loadEvents').addEventListener('click', async () => {
  const base = val('apiBase');
  const token = val('adminToken');
  const since = val('since');
  const until = val('until');
  const qp = new URLSearchParams();
  qp.set('limit', '50');
  if (since) qp.set('since', since);
  if (until) qp.set('until', until);
  try {
    const data = await fetchJson(`${base}/analytics/events?${qp.toString()}`, token);
    document.getElementById('events').textContent = JSON.stringify(data, null, 2);
  } catch (e) {
    document.getElementById('events').textContent = `Error: ${e.message}`;
  }
});

// Support threads
document.getElementById('loadThreads').addEventListener('click', async () => {
  const base = val('apiBase');
  const token = val('adminToken');
  try {
    const data = await fetchJson(`${base}/admin/support/threads?limit=100`, token);
    document.getElementById('threads').textContent = JSON.stringify(data, null, 2);
    const first = (data.threads || [])[0];
    if (first) document.getElementById('threadId').value = first.conversation_id;
  } catch (e) {
    document.getElementById('threads').textContent = `Error: ${e.message}`;
  }
});

document.getElementById('loadMessages').addEventListener('click', async () => {
  const base = val('apiBase');
  const token = val('adminToken');
  const id = val('threadId');
  if (!id) {
    document.getElementById('messages').textContent = 'Enter conversation_id';
    return;
  }
  try {
    const data = await fetchJson(`${base}/admin/support/messages?conversation_id=${encodeURIComponent(id)}`, token);
    document.getElementById('messages').textContent = JSON.stringify(data, null, 2);
  } catch (e) {
    document.getElementById('messages').textContent = `Error: ${e.message}`;
  }
});

/* eslint-env browser */
/* global d3 */

document.addEventListener('DOMContentLoaded', () => {
    const main = document.getElementById('main-content');

    function showAlert(message) {
        let container = document.getElementById('app-alert');
        if (!container) {
            container = document.createElement('div');
            container.id = 'app-alert';
            container.style.position = 'fixed';
            container.style.bottom = '16px';
            container.style.right = '16px';
            container.style.background = 'rgba(0,0,0,0.8)';
            container.style.color = '#fff';
            container.style.padding = '8px 12px';
            container.style.borderRadius = '6px';
            container.style.zIndex = '9999';
            document.body.appendChild(container);
        }
        container.textContent = typeof message === 'string' ? message : JSON.stringify(message);
        container.style.display = 'block';
        clearTimeout(container._timeout);
        container._timeout = setTimeout(() => { container.style.display = 'none'; }, 5000);
    }
    function loadContent(section) {
        switch(section) {
            case 'duplicates':
                main.innerHTML = `
                    <h2>Duplicate Search</h2>
                    <p>Find duplicate files on your hard drive.</p>
                    <label>Path: <input id="dup-path" type="text" placeholder="/path/to/scan" style="width:60%"></label>
                    <label>Min size (bytes): <input id="dup-min" type="number" value="1"></label>
                    <label>Max files to process: <input id="dup-max" type="number" placeholder="(optional)"></label>
                    <button id="dup-run">Run</button>
                    <label style="margin-left:1rem"><input id="use-ai-suggestions" type="checkbox"> Use AI suggestions</label>
                    <div id="dup-actions" style="margin-top:1rem"></div>
                    <div id="dup-result"></div>
                `;
                document.getElementById('dup-run').onclick = async () => {
                    const path = document.getElementById('dup-path').value || undefined;
                    const min = parseInt(document.getElementById('dup-min').value || '1', 10);
                    const maxFiles = parseInt(document.getElementById('dup-max').value || '', 10);
                    const body = {};
                    if (path) body.paths = [path];
                    body.min_size = min;
                    if (!Number.isNaN(maxFiles)) body.max_files = maxFiles;
                    const res = await fetch('http://127.0.0.1:5000/api/duplicates', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(body)});
                    const j = await res.json();
                    const actions = document.getElementById('dup-actions');
                    actions.innerHTML = '';
                    if (j.count && j.count > 0) {
                        const btn = document.createElement('button');
                        btn.textContent = 'Create Preview';
                        // editable suggestions UI container
                        const editorContainer = document.createElement('div');
                        editorContainer.style.marginTop = '8px';
                        const editBtn = document.createElement('button');
                        editBtn.textContent = 'Edit Suggestions';
                        editBtn.style.marginLeft = '8px';
                        let currentSuggestions = null;

                        editBtn.onclick = () => {
                            if (!currentSuggestions) return showAlert('No suggestions available to edit');
                            // toggle editor
                            if (editorContainer.innerHTML) {
                                editorContainer.innerHTML = '';
                                return;
                            }
                            const ta = document.createElement('textarea');
                            ta.style.width = '100%';
                            ta.style.height = '200px';
                            ta.value = JSON.stringify(currentSuggestions, null, 2);
                            const save = document.createElement('button');
                            save.textContent = 'Save Suggestions';
                            save.onclick = () => {
                                try {
                                    const parsed = JSON.parse(ta.value);
                                    currentSuggestions = parsed;
                                    editorContainer.innerHTML = '';
                                    showAlert('Suggestions updated');
                                } catch (e) {
                                    showAlert('Invalid JSON: ' + e.message);
                                }
                            };
                            const cancel = document.createElement('button');
                            cancel.textContent = 'Cancel';
                            cancel.style.marginLeft = '8px';
                            cancel.onclick = () => { editorContainer.innerHTML = ''; };
                            editorContainer.appendChild(ta);
                            editorContainer.appendChild(save);
                            editorContainer.appendChild(cancel);
                        };

                        btn.onclick = async () => {
                            // choose endpoint: AI suggestions or heuristic
                            const useAI = document.getElementById('use-ai-suggestions') && document.getElementById('use-ai-suggestions').checked;
                            const endpoint = useAI ? '/api/organise/suggest' : '/api/organise';
                            const sres = await fetch(endpoint, {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({duplicates: j.duplicates})});
                            const sj = await sres.json();
                            currentSuggestions = sj.suggestions || [];
                            // show a small preview and allow editing before creating op
                            actions.innerHTML = `<div>Suggestions received (${currentSuggestions.length}) — you may edit before preview.</div>`;
                            actions.appendChild(editBtn);
                            actions.appendChild(editorContainer);
                            const createOp = document.createElement('button');
                            createOp.textContent = 'Create Preview (from suggestions)';
                            createOp.style.marginLeft = '8px';
                            createOp.onclick = async () => {
                                createOp.disabled = true;
                                try {
                                    const pres = await fetch('/api/organise/preview', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({suggestions: currentSuggestions})});
                                    const pj = await pres.json();
                                    actions.innerHTML += `<div>Preview created: <strong>${pj.op.id}</strong></div>`;
                                    // show execute/undo controls
                                    const exec = document.createElement('button');
                                    exec.textContent = 'Execute';
                                    exec.onclick = async () => {
                                        exec.disabled = true;
                                        const er = await fetch('/api/organise/execute', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({op_id: pj.op.id})});
                                        const ej = await er.json();
                                        actions.innerHTML += `<pre>${JSON.stringify(ej, null, 2)}</pre>`;
                                        const undo = document.createElement('button');
                                        undo.textContent = 'Undo';
                                        undo.onclick = async () => {
                                            undo.disabled = true;
                                            const ur = await fetch('/api/organise/undo', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({op_id: pj.op.id})});
                                            const uj = await ur.json();
                                            actions.innerHTML += `<pre>${JSON.stringify(uj, null, 2)}</pre>`;
                                            undo.disabled = false;
                                        };
                                        actions.appendChild(undo);
                                        exec.disabled = false;
                                    };
                                    actions.appendChild(exec);
                                } catch (e) {
                                    showAlert('Preview creation failed: ' + e.message);
                                } finally {
                                    createOp.disabled = false;
                                }
                            };
                            actions.appendChild(createOp);
                        };
                        actions.appendChild(btn);
                        actions.appendChild(editBtn);
                        const recycleBtn = document.createElement('button');
                        recycleBtn.textContent = 'Move to Recycle Bin (safe)';
                        recycleBtn.style.marginLeft = '8px';
                        recycleBtn.onclick = async () => {
                            const pres = await fetch('http://127.0.0.1:5000/api/organise/remove-preview', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({duplicates: j.duplicates})});
                            const pj = await pres.json();
                            actions.innerHTML = `<div>Recycle preview created: <strong>${pj.op.id}</strong></div>`;
                            const exec = document.createElement('button');
                            exec.textContent = 'Execute (move to recycle)';
                            exec.onclick = async () => {
                                const er = await fetch('http://127.0.0.1:5000/api/organise/execute', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({op_id: pj.op.id})});
                                const ej = await er.json();
                                actions.innerHTML += `<pre>${JSON.stringify(ej, null, 2)}</pre>`;
                                const undo = document.createElement('button');
                                undo.textContent = 'Undo';
                                undo.onclick = async () => {
                                    const ur = await fetch('http://127.0.0.1:5000/api/organise/undo', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({op_id: pj.op.id})});
                                    const uj = await ur.json();
                                    actions.innerHTML += `<pre>${JSON.stringify(uj, null, 2)}</pre>`;
                                };
                                actions.appendChild(undo);
                            };
                            actions.appendChild(exec);
                        };
                        actions.appendChild(recycleBtn);
                    }
                    // render duplicates
                    const out = document.getElementById('dup-result');
                    out.innerHTML = '';
                    j.duplicates.forEach((g, i) => {
                        const div = document.createElement('div');
                        div.style.borderTop = '1px solid #eee';
                        div.style.padding = '0.5rem 0';
                        const title = document.createElement('div');
                        title.textContent = `Group ${i+1} (hash: ${g.hash})`;
                        div.appendChild(title);
                        const ul = document.createElement('ul');
                        g.files.forEach(f => {
                            const li = document.createElement('li');
                            li.textContent = `${f.path} (${f.size} bytes)`;
                            ul.appendChild(li);
                        });
                        div.appendChild(ul);
                        out.appendChild(div);
                    });
                };
                break;
            case 'visualisation':
                main.innerHTML = `
                    <h2>Visualisation</h2>
                    <p>Visualise your hard drive structure and usage.</p>
                    <label>Path: <input id="vis-path" type="text" placeholder="/path/to/scan" style="width:60%"></label>
                    <label>Depth: <input id="vis-depth" type="number" value="2"></label>
                    <button id="vis-run">Run</button>
                    <button id="vis-bg">Run Background Scan</button>
                    <div id="vis-progress" style="margin-top:0.5rem"></div>
                    <div id="vis-result"></div>
                `;
                function toHierarchy(node) {
                    return {name: node.path || node.name || '/', value: node.size || 0, children: (node.children||[]).map(toHierarchy)}
                }

                function renderTreemap(data, container) {
                    container.innerHTML = '';
                    const width = Math.max(700, container.clientWidth || 800);
                    const height = 500;
                    const rootData = toHierarchy(data);
                    const root = d3.hierarchy(rootData).sum(d => d.value || 0).sort((a,b)=>b.value - a.value);
                    d3.treemap().size([width, height]).padding(1)(root);

                    const svg = d3.create('svg').attr('width', width).attr('height', height);
                    const color = d3.scaleOrdinal(d3.schemeCategory10);

                    const cell = svg.selectAll('g').data(root.descendants().filter(d => d.depth > 0)).enter().append('g')
                        .attr('transform', d => `translate(${d.x0},${d.y0})`)
                        .style('cursor', 'pointer');

                    cell.append('rect')
                        .attr('width', d => Math.max(0, d.x1 - d.x0))
                        .attr('height', d => Math.max(0, d.y1 - d.y0))
                        .attr('fill', d => color(d.depth))
                        .attr('stroke', '#fff');

                    cell.append('text')
                        .attr('x', 4)
                        .attr('y', 14)
                        .attr('font-size', '12px')
                        .text(d => (d.data.name ? d.data.name.split('/').pop() : '') + (d.value ? ` (${d.value})` : ''));

                    cell.on('click', (event, d) => {
                        event.stopPropagation();
                        if (d.children) {
                            renderTreemap(d.data, container);
                        } else {
                            // leaf clicked: show info
                            const info = document.getElementById('vis-progress');
                            info.textContent = `Selected: ${d.data.name} (${d.value} bytes)`;
                        }
                    });

                    container.appendChild(svg.node());
                }
                document.getElementById('vis-run').onclick = async () => {
                    const path = document.getElementById('vis-path').value || undefined;
                    const depth = parseInt(document.getElementById('vis-depth').value || '2', 10);
                    const body = {};
                    if (path) body.path = path;
                    body.depth = depth;
                    const res = await fetch('http://127.0.0.1:5000/api/visualisation', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(body)});
                    const j = await res.json();
                    const out = document.getElementById('vis-result');
                    if (j.visualisation) renderTreemap(j.visualisation, out);
                    else out.textContent = JSON.stringify(j, null, 2);
                };
                document.getElementById('vis-bg').onclick = async () => {
                    const path = document.getElementById('vis-path').value || undefined;
                    const body = {paths: path ? [path] : undefined};
                    const res = await fetch('/api/scan/start', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(body)});
                    const j = await res.json();
                    const jobId = j.job_id;
                    const prog = document.getElementById('vis-progress');

                    // close any previous EventSource
                    try {
                        if (window._diskOrganiserEvtSrc && typeof window._diskOrganiserEvtSrc.close === 'function') {
                            window._diskOrganiserEvtSrc.close();
                        }
                    } catch (e) {
                        // ignore
                    }

                    // render progress bar + text + cancel
                    prog.innerHTML = `
                        <div class="progress"><div class="progress-bar" id="vis-progress-bar" style="width:0%"></div></div>
                        <div class="progress-text" id="vis-progress-text">Job <strong>${jobId}</strong> started (backend: ${j.backend})</div>
                        <div style="margin-top:6px"><button id="scan-cancel">Cancel</button></div>
                    `;

                    const cancelBtn = document.getElementById('scan-cancel');
                    cancelBtn.onclick = async () => {
                        if (!confirm('Cancel this scan?')) return;
                        await fetch('/api/scan/cancel', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({job_id: jobId})});
                        showAlert('Cancel requested');
                    };

                    // connect SSE for live updates with automatic reconnect
                    let evtSrc = null;
                    let reconnectDelay = 1000;
                    const out = document.getElementById('vis-result');
                    out.innerHTML = '';

                    const connect = () => {
                        try {
                            evtSrc = new EventSource(`/api/scan/events/${jobId}`);
                            window._diskOrganiserEvtSrc = evtSrc;
                            evtSrc.onopen = () => {
                                reconnectDelay = 1000;
                                const t = document.getElementById('vis-progress-text');
                                if (t) t.textContent = `Job ${jobId} connected`;
                            };
                            evtSrc.onmessage = (ev) => {
                                try {
                                    const data = JSON.parse(ev.data || '{}');
                                    const bar = document.getElementById('vis-progress-bar');
                                    const text = document.getElementById('vis-progress-text');
                                    if (data.progress) {
                                        const p = data.progress;
                                        if (typeof p.processed === 'number' && typeof p.total === 'number' && p.total > 0) {
                                            const pct = Math.min(100, Math.round((p.processed / p.total) * 100));
                                            if (bar) { bar.style.width = pct + '%'; bar.classList.remove('indeterminate'); }
                                            if (text) text.textContent = `Job ${jobId} ${data.status || ''} — ${p.processed}/${p.total} (${pct}%)`;
                                        } else if (typeof p.processed === 'number') {
                                            if (bar) { bar.classList.add('indeterminate'); }
                                            if (text) text.textContent = `Job ${jobId} ${data.status || ''} — scanned ${p.processed}`;
                                        } else if (p.file) {
                                            if (bar) { bar.classList.add('indeterminate'); }
                                            if (text) text.textContent = `Job ${jobId} ${data.status || ''} — hashing ${p.file}`;
                                        } else {
                                            if (text) text.textContent = `Job ${jobId} ${data.status || ''}`;
                                        }
                                    } else if (data.status) {
                                        if (text) text.textContent = `Job ${jobId} ${data.status}`;
                                    }
                                    if (data.result) {
                                        out.innerHTML = `<pre>${JSON.stringify(data.result, null, 2)}</pre>`;
                                        const bar = document.getElementById('vis-progress-bar');
                                        if (bar) { bar.style.width = '100%'; bar.classList.remove('indeterminate'); }
                                        try { if (evtSrc) evtSrc.close(); } catch (e) {}
                                    }
                                } catch (e) {
                                    // ignore parse errors
                                }
                            };
                            evtSrc.onerror = (e) => {
                                console.error('SSE error', e);
                                try { if (evtSrc) evtSrc.close(); } catch (err) {}
                                setTimeout(() => { reconnectDelay = Math.min(30000, reconnectDelay * 2); connect(); }, reconnectDelay);
                            };
                        } catch (e) {
                            console.error('EventSource failed', e);
                        }
                    };
                    connect();
                };
                break;
            case 'organise':
                main.innerHTML = `
                    <h2>Organise</h2>
                    <p>Review created operations, view details, undo or remove backups.</p>
                    <button id="ops-refresh">Refresh Ops</button>
                    <div id="ops-list" style="margin-top:1rem"></div>
                    <div id="ops-detail" style="margin-top:1rem"></div>
                `;
                async function loadOps() {
                    const res = await fetch('http://127.0.0.1:5000/api/ops');
                    const j = await res.json();
                    const list = document.getElementById('ops-list');
                    list.innerHTML = '';
                    const ops = j.ops || {};
                    for (const opId of Object.keys(ops)) {
                        const op = ops[opId];
                        const card = document.createElement('div');
                        card.style.border = '1px solid #ddd';
                        card.style.padding = '8px';
                        card.style.marginBottom = '8px';
                        const title = document.createElement('div');
                        title.innerHTML = `<strong>Op:</strong> ${opId} — <em>${op.status}</em>`;
                        card.appendChild(title);
                        const meta = document.createElement('div');
                        meta.textContent = JSON.stringify(op.metadata || {});
                        card.appendChild(meta);
                        const view = document.createElement('button');
                        view.textContent = 'View Details';
                        view.onclick = async () => {
                            const dres = await fetch(`http://127.0.0.1:5000/api/op/${opId}`);
                            const dj = await dres.json();
                            const det = document.getElementById('ops-detail');
                            det.innerHTML = `<pre>${JSON.stringify(dj.op, null, 2)}</pre>`;
                        };
                        card.appendChild(view);
                        const undo = document.createElement('button');
                        undo.textContent = 'Undo';
                        undo.style.marginLeft = '8px';
                        undo.onclick = async () => {
                            const r = await fetch('http://127.0.0.1:5000/api/organise/undo', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({op_id: opId})});
                            const jr = await r.json();
                            showAlert(JSON.stringify(jr));
                            loadOps();
                        };
                        card.appendChild(undo);
                        const del = document.createElement('button');
                        del.textContent = 'Delete Backup';
                        del.style.marginLeft = '8px';
                        del.onclick = async () => {
                            const r = await fetch('http://127.0.0.1:5000/api/recycle/delete_op', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({op_id: opId})});
                            const jd = await r.json();
                            showAlert(JSON.stringify(jd));
                            loadOps();
                        };
                        card.appendChild(del);
                        list.appendChild(card);
                    }
                }
                document.getElementById('ops-refresh').onclick = loadOps;
                loadOps();
                break;
            case 'recycle':
                main.innerHTML = `
                    <h2>Recycle Bin</h2>
                    <label>Retention days: <input id="recycle-days" type="number" value="30"></label>
                    <button id="recycle-clean">Run Cleanup</button>
                    <div id="recycle-list" style="margin-top:1rem"></div>
                `;
                document.getElementById('recycle-clean').onclick = async () => {
                    const days = parseInt(document.getElementById('recycle-days').value || '30', 10);
                    const res = await fetch('http://127.0.0.1:5000/api/recycle/cleanup', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({retention_days: days})});
                    const j = await res.json();
                    showAlert(`Cleanup: ${JSON.stringify(j)}`);
                    loadRecycle();
                };
                async function loadRecycle() {
                    const res = await fetch('http://127.0.0.1:5000/api/recycle/list');
                    const j = await res.json();
                    const list = document.getElementById('recycle-list');
                    list.innerHTML = '';
                    const data = j.recycle || {};
                    for (const opId of Object.keys(data)) {
                        const op = data[opId];
                        const card = document.createElement('div');
                        card.style.border = '1px solid #ddd';
                        card.style.padding = '8px';
                        card.style.marginBottom = '8px';
                        const title = document.createElement('div');
                        title.innerHTML = `<strong>Op:</strong> ${opId} — <em>${op.status}</em>`;
                        card.appendChild(title);
                        const meta = document.createElement('div');
                        meta.textContent = JSON.stringify(op.metadata || {});
                        card.appendChild(meta);
                        const files = document.createElement('ul');
                        (op.files || []).forEach(f => {
                            const li = document.createElement('li');
                            li.textContent = `${f.path} — ${f.size} bytes`;
                            files.appendChild(li);
                        });
                        card.appendChild(files);
                        const undo = document.createElement('button');
                        undo.textContent = 'Undo (restore)';
                        undo.onclick = async () => {
                            const r = await fetch('http://127.0.0.1:5000/api/organise/undo', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({op_id: opId})});
                            const jr = await r.json();
                            showAlert(JSON.stringify(jr));
                            loadRecycle();
                        };
                        card.appendChild(undo);
                        const del = document.createElement('button');
                        del.textContent = 'Delete Backup (permanent)';
                        del.style.marginLeft = '8px';
                        del.onclick = async () => {
                            const r = await fetch('http://127.0.0.1:5000/api/recycle/delete_op', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({op_id: opId})});
                            const jd = await r.json();
                            showAlert(JSON.stringify(jd));
                            loadRecycle();
                        };
                        card.appendChild(del);
                        list.appendChild(card);
                    }
                }
                loadRecycle();
                break;
            case 'preferences':
                main.innerHTML = `
                    <h2>Preferences</h2>
                    <p>Set your model and UI preferences.</p>
                    <label>Model: <input id="pref-model" type="text" placeholder="ollama"></label>
                    <button id="pref-save">Save</button>
                    <pre id="pref-result"></pre>
                `;
                document.getElementById('pref-save').onclick = async () => {
                    const model = document.getElementById('pref-model').value;
                    const body = {model};
                    const res = await fetch('http://127.0.0.1:5000/api/model', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(body)});
                    const j = await res.json();
                    document.getElementById('pref-result').textContent = JSON.stringify(j, null, 2);
                };
                break;
            default:
                main.innerHTML = `<h2>Welcome</h2><p>Select a workflow above to get started.</p>`;
        }
    }
    document.getElementById('nav-duplicates').onclick = () => loadContent('duplicates');
    document.getElementById('nav-visualisation').onclick = () => loadContent('visualisation');
    document.getElementById('nav-recycle').onclick = () => loadContent('recycle');
    document.getElementById('nav-organise').onclick = () => loadContent('organise');
    document.getElementById('nav-preferences').onclick = () => loadContent('preferences');
    loadContent();
});

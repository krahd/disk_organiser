/* eslint-env browser */

// API base can be injected at runtime by setting `window._DISK_ORGANISER_API_BASE`.
// Defaults to empty string so relative paths are used (works in Docker/production).
const API_BASE =
  typeof window !== "undefined" && window._DISK_ORGANISER_API_BASE
    ? window._DISK_ORGANISER_API_BASE
    : "";

// lazy-load D3 only when visualisation is requested (avoids network fetch during tests)
function ensureD3() {
  return new Promise((resolve, reject) => {
    if (typeof window.d3 !== "undefined") return resolve(window.d3);
    const s = document.createElement("script");
    s.src = "https://d3js.org/d3.v7.min.js";
    s.onload = () => resolve(window.d3);
    s.onerror = () => reject(new Error("Failed to load d3"));
    document.head.appendChild(s);
  });
}

document.addEventListener("DOMContentLoaded", () => {
  const main = document.getElementById("main-content");

  // Helper: format bytes into human-readable strings
  function formatBytes(bytes) {
    try {
      const b = Number(bytes) || 0;
      if (b === 0) return "0 B";
      const units = ["B", "KB", "MB", "GB", "TB"];
      let value = b;
      let i = 0;
      while (value >= 1024 && i < units.length - 1) {
        value = value / 1024;
        i += 1;
      }
      if (i === 0) return `${Math.round(value)} ${units[i]}`;
      return `${value.toFixed(2)} ${units[i]}`;
    } catch (e) {
      return String(bytes);
    }
  }

  function showAlert(message) {
    let container = document.getElementById("app-alert");
    if (!container) {
      container = document.createElement("div");
      container.id = "app-alert";
      container.className = "app-alert";
      document.body.appendChild(container);
    }
    container.textContent = typeof message === "string" ? message : JSON.stringify(message);
    container.classList.add("visible");
    clearTimeout(container._timeout);
    container._timeout = setTimeout(() => {
      container.classList.remove("visible");
    }, 5000);
  }
  function loadContent(section) {
    switch (section) {
      case "duplicates":
        main.innerHTML = `
                    <h2>Duplicate Search</h2>
                    <p>Find duplicate files on your hard drive.</p>
                    <label>Path: <input id="dup-path" type="text" placeholder="/path/to/scan" class="input-wide"></label>
                    <label>Min size (bytes): <input id="dup-min" type="number" value="1"></label>
                    <label>Max files to process: <input id="dup-max" type="number" placeholder="(optional)"></label>
                    <label>Workers: <input id="dup-workers" type="number" placeholder="(optional)"></label>
                    <button id="dup-run" class="btn primary">Run</button>
                    <label class="ml-1rem"><input id="use-ai-suggestions" type="checkbox"> Use AI suggestions</label>
                    <div id="dup-actions" class="mt-1"></div>
                    <div id="dup-result"></div>
                `;
        document.getElementById("dup-run").onclick = async () => {
          const path = document.getElementById("dup-path").value || undefined;
          const min = parseInt(document.getElementById("dup-min").value || "1", 10);
          const maxFiles = parseInt(document.getElementById("dup-max").value || "", 10);
          const maxWorkers = parseInt(document.getElementById("dup-workers").value || "", 10);
          const body = {};
          if (path) body.paths = [path];
          body.min_size = min;
          if (!Number.isNaN(maxFiles)) body.max_files = maxFiles;
          if (!Number.isNaN(maxWorkers)) body.max_workers = maxWorkers;
          const res = await fetch(`${API_BASE}/api/duplicates`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body),
          });
          const j = await res.json();
          const actions = document.getElementById("dup-actions");
          actions.innerHTML = "";
          if (j.count && j.count > 0) {
            const btn = document.createElement("button");
            btn.textContent = "Create Preview";
            // editable suggestions UI container
            const editorContainer = document.createElement("div");
            editorContainer.className = "editor-container";
            const editBtn = document.createElement("button");
            editBtn.textContent = "Edit Suggestions";
            editBtn.className = "btn";
            let currentSuggestions = null;

            editBtn.onclick = () => {
              if (!currentSuggestions) return showAlert("No suggestions available to edit");
              // toggle editor
              if (editorContainer.innerHTML) {
                editorContainer.innerHTML = "";
                return;
              }
              const ta = document.createElement("textarea");
              ta.className = "editor-textarea";
              ta.value = JSON.stringify(currentSuggestions, null, 2);
              const save = document.createElement("button");
              save.textContent = "Save Suggestions";
              save.className = "btn primary";
              save.onclick = () => {
                try {
                  const parsed = JSON.parse(ta.value);
                  currentSuggestions = parsed;
                  editorContainer.innerHTML = "";
                  showAlert("Suggestions updated");
                } catch (e) {
                  showAlert("Invalid JSON: " + e.message);
                }
              };
              const cancel = document.createElement("button");
              cancel.textContent = "Cancel";
              cancel.className = "btn";
              cancel.onclick = () => {
                editorContainer.innerHTML = "";
              };
              editorContainer.appendChild(ta);
              editorContainer.appendChild(save);
              editorContainer.appendChild(cancel);
            };

            btn.onclick = async () => {
              // choose endpoint: AI suggestions or heuristic
              const useAI =
                document.getElementById("use-ai-suggestions") &&
                document.getElementById("use-ai-suggestions").checked;
              const endpoint = useAI ? "/api/organise/suggest" : "/api/organise";
              const sres = await fetch(endpoint, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ duplicates: j.duplicates }),
              });
              const sj = await sres.json();
              currentSuggestions = sj.suggestions || [];
              // show a small preview and allow editing before creating op
              actions.innerHTML = `<div>Suggestions received (${currentSuggestions.length}) — you may edit before preview.</div>`;
              actions.appendChild(editBtn);
              actions.appendChild(editorContainer);
              const createOp = document.createElement("button");
              createOp.textContent = "Create Preview (from suggestions)";
              createOp.className = "btn primary";
              createOp.onclick = async () => {
                createOp.disabled = true;
                try {
                  const pres = await fetch("/api/organise/preview", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ suggestions: currentSuggestions }),
                  });
                  const pj = await pres.json();
                  actions.innerHTML += `<div>Preview created: <strong>${pj.op.id}</strong></div>`;
                  // show preview / execute / undo controls
                  const previewBtn = document.createElement("button");
                  previewBtn.textContent = "Preview";
                  previewBtn.className = "btn";
                  previewBtn.onclick = async () => {
                    previewBtn.disabled = true;
                    try {
                      const pr = await fetch("/api/organise/execute", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ op_id: pj.op.id, dry_run: true }),
                      });
                      const pjres = await pr.json();
                      const preEl = document.createElement("pre");
                      preEl.textContent = JSON.stringify(pjres, null, 2);
                      actions.appendChild(preEl);
                    } catch (e) {
                      showAlert("Preview failed: " + e.message);
                    } finally {
                      previewBtn.disabled = false;
                    }
                  };
                  actions.appendChild(previewBtn);
                  const exec = document.createElement("button");
                  exec.textContent = "Execute";
                  exec.className = "btn primary";
                  exec.onclick = async () => {
                    exec.disabled = true;
                    const er = await fetch("/api/organise/execute", {
                      method: "POST",
                      headers: { "Content-Type": "application/json" },
                      body: JSON.stringify({ op_id: pj.op.id }),
                    });
                    const ej = await er.json();
                    actions.innerHTML += `<pre>${JSON.stringify(ej, null, 2)}</pre>`;
                    const undo = document.createElement("button");
                    undo.textContent = "Undo";
                    undo.onclick = async () => {
                      undo.disabled = true;
                      const ur = await fetch("/api/organise/undo", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ op_id: pj.op.id }),
                      });
                      const uj = await ur.json();
                      actions.innerHTML += `<pre>${JSON.stringify(uj, null, 2)}</pre>`;
                      undo.disabled = false;
                    };
                    actions.appendChild(undo);
                    exec.disabled = false;
                  };
                  actions.appendChild(exec);
                } catch (e) {
                  showAlert("Preview creation failed: " + e.message);
                } finally {
                  createOp.disabled = false;
                }
              };
              actions.appendChild(createOp);
            };
            actions.appendChild(btn);
            actions.appendChild(editBtn);
            const recycleBtn = document.createElement("button");
            recycleBtn.textContent = "Move to Recycle Bin (safe)";
            recycleBtn.className = "btn secondary";
            recycleBtn.onclick = async () => {
              const pres = await fetch(`${API_BASE}/api/organise/remove-preview`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ duplicates: j.duplicates }),
              });
              const pj = await pres.json();
              actions.innerHTML = `<div>Recycle preview created: <strong>${pj.op.id}</strong></div>`;
              const previewBtn = document.createElement("button");
              previewBtn.textContent = "Preview";
              previewBtn.className = "btn";
              previewBtn.onclick = async () => {
                previewBtn.disabled = true;
                try {
                  const pr = await fetch("/api/organise/execute", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ op_id: pj.op.id, dry_run: true }),
                  });
                  const pjres = await pr.json();
                  actions.innerHTML += `<pre>${JSON.stringify(pjres, null, 2)}</pre>`;
                } catch (e) {
                  showAlert("Preview failed: " + e.message);
                } finally {
                  previewBtn.disabled = false;
                }
              };
              actions.appendChild(previewBtn);
              const exec = document.createElement("button");
              exec.textContent = "Execute (move to recycle)";
              exec.className = "btn primary";
              exec.onclick = async () => {
                const er = await fetch(`${API_BASE}/api/organise/execute`, {
                  method: "POST",
                  headers: { "Content-Type": "application/json" },
                  body: JSON.stringify({ op_id: pj.op.id }),
                });
                const ej = await er.json();
                actions.innerHTML += `<pre>${JSON.stringify(ej, null, 2)}</pre>`;
                const undo = document.createElement("button");
                undo.textContent = "Undo";
                undo.onclick = async () => {
                  const ur = await fetch(`${API_BASE}/api/organise/undo`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ op_id: pj.op.id }),
                  });
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
          const out = document.getElementById("dup-result");
          out.innerHTML = "";
          j.duplicates.forEach((g, i) => {
            const div = document.createElement("div");
            div.className = "dup-group";
            const title = document.createElement("div");
            title.textContent = `Group ${i + 1} (hash: ${g.hash})`;
            div.appendChild(title);
            const ul = document.createElement("ul");
            g.files.forEach((f) => {
              const li = document.createElement("li");
              li.textContent = `${f.path} (${f.size} bytes)`;
              ul.appendChild(li);
            });
            div.appendChild(ul);
            out.appendChild(div);
          });
        };
        break;
      case "visualisation":
        main.innerHTML = `
                    <h2>Visualisation</h2>
                    <p>Visualise your hard drive structure and usage.</p>
                    <label>Path: <input id="vis-path" type="text" placeholder="/path/to/scan" class="input-wide"></label>
                    <label>Depth: <input id="vis-depth" type="number" value="2"></label>
                    <label>Workers: <input id="vis-workers" type="number" placeholder="(optional)"></label>
                    <button id="vis-run" class="btn primary">Run</button>
                    <button id="vis-bg" class="btn">Run Background Scan</button>
                    <div id="vis-progress" class="mt-06"></div>
                    <div id="vis-result"></div>
                `;
        let latestVisualInsights = {};
        let latestVisualSummary = null;
        function toHierarchy(node) {
          return {
            name: node.path || node.name || "/",
            value: node.size || 0,
            children: (node.children || []).map(toHierarchy),
          };
        }

        async function renderTreemap(data, container) {
          await ensureD3();
          container.innerHTML = "";
          const width = Math.max(700, container.clientWidth || 800);
          const height = 500;
          const rootData = toHierarchy(data);
          const root = d3
            .hierarchy(rootData)
            .sum((d) => d.value || 0)
            .sort((a, b) => b.value - a.value);
          d3.treemap().size([width, height]).padding(1)(root);

          const svg = d3.create("svg").attr("width", width).attr("height", height);
          const color = d3.scaleOrdinal(d3.schemeCategory10);

          const cell = svg
            .selectAll("g")
            .data(root.descendants().filter((d) => d.depth > 0))
            .enter()
            .append("g")
            .attr("transform", (d) => `translate(${d.x0},${d.y0})`)
            .attr("tabindex", 0)
            .attr("role", "button")
            .attr("aria-label", (d) =>
              d.data.name ? `${d.data.name} ${formatBytes(d.value || 0)}` : ""
            )
            .classed("treemap-cell", true)
            .style("cursor", "pointer");

          cell
            .append("rect")
            .attr("width", (d) => Math.max(0, d.x1 - d.x0))
            .attr("height", (d) => Math.max(0, d.y1 - d.y0))
            .attr("fill", (d) => color(d.depth))
            .attr("stroke", "#fff");

          cell
            .append("text")
            .attr("x", 4)
            .attr("y", 14)
            .attr("font-size", "12px")
            .text(
              (d) =>
                (d.data.name ? d.data.name.split("/").pop() : "") +
                (d.value ? ` (${formatBytes(d.value)})` : "")
            );

          cell.on("click", (event, d) => {
            event.stopPropagation();
            // if this node has children, drill down into it
            if (d.children) {
              renderTreemap(d.data, container);
              return;
            }

            // prepare panel content
            const panelContent = document.createElement("div");
            const title = document.createElement("div");
            title.innerHTML = `<strong>${d.data.name}</strong>`;
            const sizeEl = document.createElement("div");
            sizeEl.textContent = `Size: ${formatBytes(d.value)}`;
            panelContent.appendChild(title);
            panelContent.appendChild(sizeEl);

            const folderInsight =
              latestVisualInsights[d.data.name] || latestVisualInsights[d.data.path];
            if (folderInsight) {
              const insight = document.createElement("div");
              insight.className = "insight-panel mt-6";
              insight.innerHTML = `
                <div><strong>Folder insight</strong></div>
                <div>${folderInsight.files || 0} files, ${
                folderInsight.semantic_groups || 0
              } semantic groups</div>
                <div>${folderInsight.stale || 0} stale candidates</div>
              `;
              panelContent.appendChild(insight);
            }
            if (latestVisualSummary) {
              const summary = document.createElement("div");
              summary.className = "small-muted mt-6";
              summary.textContent = `Analysis snapshot: ${
                latestVisualSummary.file_count || 0
              } files, ${latestVisualSummary.stale_candidates || 0} stale candidates, ${
                latestVisualSummary.near_duplicate_clusters || 0
              } semantic clusters.`;
              panelContent.appendChild(summary);
            }

            const resultEl = document.createElement("div");
            resultEl.className = "mt-6";

            const findBtn = document.createElement("button");
            findBtn.textContent = "Find duplicates in this folder";
            findBtn.className = "btn";
            findBtn.onclick = async () => {
              findBtn.disabled = true;
              try {
                const res = await fetch("/api/duplicates", {
                  method: "POST",
                  headers: { "Content-Type": "application/json" },
                  body: JSON.stringify({ paths: [d.data.name], min_size: 1 }),
                });
                const j = await res.json();
                resultEl.innerHTML = "";
                if (j.duplicates && j.duplicates.length) {
                  const summary = document.createElement("div");
                  summary.textContent = `Found ${j.count || j.duplicates.length} duplicate groups`;
                  resultEl.appendChild(summary);

                  const createBtn = document.createElement("button");
                  createBtn.textContent = "Create Preview (heuristic)";
                  createBtn.className = "btn primary mt-6";
                  createBtn.onclick = async () => {
                    createBtn.disabled = true;
                    try {
                      const sres = await fetch("/api/organise", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ duplicates: j.duplicates }),
                      });
                      const sj = await sres.json();
                      const pres = await fetch("/api/organise/preview", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ suggestions: sj.suggestions || [] }),
                      });
                      const pj = await pres.json();
                      resultEl.innerHTML += `<div class="mt-6">Preview created: <strong>${
                        pj.op && pj.op.id
                      }</strong></div>`;
                    } catch (e) {
                      showAlert("Preview creation failed: " + (e.message || e));
                    } finally {
                      createBtn.disabled = false;
                    }
                  };
                  resultEl.appendChild(createBtn);

                  // render duplicate groups
                  j.duplicates.forEach((g, i) => {
                    const gdiv = document.createElement("div");
                    gdiv.className = "dup-group";
                    const hdr = document.createElement("div");
                    hdr.innerHTML = `<strong>Group ${i + 1} (hash: ${g.hash})</strong>`;
                    gdiv.appendChild(hdr);
                    const ul = document.createElement("ul");
                    (g.files || []).forEach((f) => {
                      const li = document.createElement("li");
                      li.textContent = `${f.path} — ${formatBytes(f.size || f.bytes || 0)}`;
                      ul.appendChild(li);
                    });
                    gdiv.appendChild(ul);
                    resultEl.appendChild(gdiv);
                  });
                } else {
                  resultEl.textContent = "No duplicates found";
                }
              } catch (e) {
                showAlert("Duplicate search failed: " + (e.message || e));
              } finally {
                findBtn.disabled = false;
              }
            };

            panelContent.appendChild(findBtn);
            panelContent.appendChild(resultEl);
            openSidePanel(`Details — ${d.data.name}`, panelContent);
          });

          // keyboard: activate cell with Enter or Space
          cell.on("keydown", function (event, d) {
            if (event.key === "Enter" || event.key === " ") {
              event.preventDefault();
              d3.select(this).dispatch("click");
            }
          });

          container.appendChild(svg.node());
        }
        document.getElementById("vis-run").onclick = async () => {
          const path = document.getElementById("vis-path").value || undefined;
          const depth = parseInt(document.getElementById("vis-depth").value || "2", 10);
          const body = {};
          if (path) body.path = path;
          body.depth = depth;
          const res = await fetch(`${API_BASE}/api/visualisation`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ ...body, include_insights: true }),
          });
          const j = await res.json();
          const out = document.getElementById("vis-result");
          latestVisualInsights = j.insights || {};
          latestVisualSummary = j.analysis_summary || null;
          if (j.visualisation) await renderTreemap(j.visualisation, out);
          else out.textContent = JSON.stringify(j, null, 2);
        };
        document.getElementById("vis-bg").onclick = async () => {
          const path = document.getElementById("vis-path").value || undefined;
          const maxWorkers = parseInt(
            document.getElementById("vis-workers")
              ? document.getElementById("vis-workers").value
              : "",
            10
          );
          const body = { paths: path ? [path] : undefined };
          if (!Number.isNaN(maxWorkers)) body.max_workers = maxWorkers;
          const res = await fetch("/api/scan/start", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body),
          });
          const j = await res.json();
          const jobId = j.job_id;
          const prog = document.getElementById("vis-progress");

          // close any previous EventSource
          try {
            if (
              window._diskOrganiserEvtSrc &&
              typeof window._diskOrganiserEvtSrc.close === "function"
            ) {
              window._diskOrganiserEvtSrc.close();
            }
          } catch (e) {
            // ignore
          }

          // render progress bar + text + cancel
          prog.innerHTML = `
                  <div class="progress"><div class="progress-bar" id="vis-progress-bar"></div></div>
                  <div class="progress-text" id="vis-progress-text">Job <strong>${jobId}</strong> started (backend: ${j.backend})</div>
                  <div class="mt-6"><button id="scan-cancel" class="btn">Cancel</button></div>
                `;

          const cancelBtn = document.getElementById("scan-cancel");
          cancelBtn.onclick = async () => {
            if (!confirm("Cancel this scan?")) return;
            await fetch("/api/scan/cancel", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ job_id: jobId }),
            });
            showAlert("Cancel requested");
          };

          // connect SSE for live updates with automatic reconnect
          let evtSrc = null;
          let reconnectDelay = 1000;
          const out = document.getElementById("vis-result");
          out.innerHTML = "";

          const connect = () => {
            try {
              evtSrc = new EventSource(`/api/scan/events/${jobId}`);
              window._diskOrganiserEvtSrc = evtSrc;
              evtSrc.onopen = () => {
                reconnectDelay = 1000;
                const t = document.getElementById("vis-progress-text");
                if (t) t.textContent = `Job ${jobId} connected`;
              };
              evtSrc.onmessage = (ev) => {
                try {
                  const data = JSON.parse(ev.data || "{}");
                  const bar = document.getElementById("vis-progress-bar");
                  const text = document.getElementById("vis-progress-text");
                  if (data.progress) {
                    const p = data.progress;
                    if (
                      typeof p.processed === "number" &&
                      typeof p.total === "number" &&
                      p.total > 0
                    ) {
                      const pct = Math.min(100, Math.round((p.processed / p.total) * 100));
                      if (bar) {
                        bar.style.width = pct + "%";
                        bar.classList.remove("indeterminate");
                      }
                      if (text)
                        text.textContent = `Job ${jobId} ${data.status || ""} — ${p.processed}/${
                          p.total
                        } (${pct}%)`;
                    } else if (typeof p.processed === "number") {
                      if (bar) {
                        bar.classList.add("indeterminate");
                      }
                      if (text)
                        text.textContent = `Job ${jobId} ${data.status || ""} — scanned ${
                          p.processed
                        }`;
                    } else if (p.file) {
                      if (bar) {
                        bar.classList.add("indeterminate");
                      }
                      if (text)
                        text.textContent = `Job ${jobId} ${data.status || ""} — hashing ${p.file}`;
                    } else {
                      if (text) text.textContent = `Job ${jobId} ${data.status || ""}`;
                    }
                  } else if (data.status) {
                    if (text) text.textContent = `Job ${jobId} ${data.status}`;
                  }
                  if (data.result) {
                    out.innerHTML = `<pre>${JSON.stringify(data.result, null, 2)}</pre>`;
                    const bar = document.getElementById("vis-progress-bar");
                    if (bar) {
                      bar.style.width = "100%";
                      bar.classList.remove("indeterminate");
                    }
                    try {
                      if (evtSrc) evtSrc.close();
                    } catch (e) {}
                  }
                } catch (e) {
                  // ignore parse errors
                }
              };
              evtSrc.onerror = (e) => {
                console.error("SSE error", e);
                try {
                  if (evtSrc) evtSrc.close();
                } catch (err) {}
                setTimeout(() => {
                  reconnectDelay = Math.min(30000, reconnectDelay * 2);
                  connect();
                }, reconnectDelay);
              };
            } catch (e) {
              console.error("EventSource failed", e);
            }
          };
          connect();
        };
        break;
      case "organise":
        main.innerHTML = `
                    <h2>Organise</h2>
                    <p>Analyse a drive, review grouped actions, refine them in natural language, then execute a selected subset.</p>
                    <div class="analysis-toolbar">
                      <label>Path: <input id="analysis-path" type="text" placeholder="/path/to/analyse" class="input-wide"></label>
                      <label>Max files: <input id="analysis-max-files" type="number" placeholder="2000"></label>
                      <label><input id="analysis-create-snapshot" type="checkbox"> Create local snapshot before execute</label>
                      <button id="analysis-run" class="btn primary">Analyse</button>
                    </div>
                    <div id="analysis-progress" class="mt-1"></div>
                    <div id="analysis-summary" class="mt-1"></div>
                    <div id="analysis-preview" class="mt-1"></div>
                    <div id="analysis-chat" class="mt-1"></div>
                    <hr class="section-rule">
                    <div class="ops-head">
                      <h3>Existing operations</h3>
                      <button id="ops-refresh" class="btn">Refresh Ops</button>
                    </div>
                    <div id="ops-list" class="mt-1"></div>
                    <div id="ops-detail" class="mt-1"></div>
                `;
        const analysisState = {
          opId: null,
          preview: null,
          selected: new Set(),
          activeJobId: null,
          eventSource: null,
        };

        async function parseApiPayload(response) {
          let payload = {};
          try {
            payload = await response.json();
          } catch (e) {
            payload = {};
          }
          if (!response.ok) {
            const apiError = payload && payload.error ? payload.error : null;
            const apiMessage = apiError
              ? apiError.message || apiError.error || JSON.stringify(apiError)
              : payload.error || payload.message;
            const err = new Error(apiMessage || `Request failed (${response.status})`);
            err.status = response.status;
            err.code = apiError ? apiError.code : undefined;
            err.details = apiError ? apiError.details : undefined;
            throw err;
          }
          return payload;
        }

        function resetAnalysisEventSource() {
          try {
            if (
              analysisState.eventSource &&
              typeof analysisState.eventSource.close === "function"
            ) {
              analysisState.eventSource.close();
            }
          } catch (e) {
            // ignore close failures
          }
          analysisState.eventSource = null;
        }

        function selectedActionIndexes() {
          return Array.from(analysisState.selected)
            .map((value) => Number(value))
            .sort((a, b) => a - b);
        }

        function renderAnalysisPreview(preview) {
          analysisState.preview = preview;
          analysisState.opId = preview && preview.op ? preview.op.id : null;
          const previewEl = document.getElementById("analysis-preview");
          const summaryEl = document.getElementById("analysis-summary");
          const chatEl = document.getElementById("analysis-chat");
          previewEl.innerHTML = "";
          chatEl.innerHTML = "";
          if (!preview || !preview.actions) {
            summaryEl.textContent = "No actions proposed.";
            return;
          }

          analysisState.selected = new Set(preview.actions.map((_action, index) => index));
          const summary = preview.summary || {};
          summaryEl.innerHTML = `
            <div class="analysis-summary-card">
              <div><strong>${
                summary.actions || preview.actions.length
              }</strong> actions across <strong>${
            Object.keys(summary.groups || {}).length
          }</strong> groups</div>
              <div>${formatBytes(summary.bytes || summary.total_bytes || 0)} affected</div>
            </div>
          `;
          if (preview.backup_status) {
            const backup = preview.backup_status;
            const banner = document.createElement("div");
            banner.className = `backup-banner ${
              backup.latest_backup ? "backup-ok" : "backup-warn"
            }`;
            banner.textContent = backup.latest_backup
              ? `Latest Time Machine backup: ${backup.latest_backup}`
              : backup.warning || "No recent macOS backup detected.";
            summaryEl.appendChild(banner);
          }
          if (preview.rejected && preview.rejected.length) {
            const rejected = document.createElement("div");
            rejected.className = "small-muted mt-8";
            rejected.textContent = `${preview.rejected.length} model actions were rejected by validation.`;
            summaryEl.appendChild(rejected);
          }

          const capabilities =
            preview.analysis_capabilities ||
            (preview.op && preview.op.metadata ? preview.op.metadata.analysis_capabilities : null);
          if (capabilities) {
            const ocr = capabilities.ocr || {};
            const embeddings = capabilities.embeddings || {};
            const missing = [];
            if (!ocr.available) {
              missing.push("OCR (install pytesseract, pdf2image, Pillow)");
            }
            if (!embeddings.available) {
              missing.push("embedding similarity (install sentence-transformers, numpy)");
            }
            const ocrMissing =
              Array.isArray(ocr.missing) && ocr.missing.length
                ? `Missing: ${ocr.missing.join(", ")}`
                : "Dependencies installed.";
            const embedMissing =
              Array.isArray(embeddings.missing) && embeddings.missing.length
                ? `Missing: ${embeddings.missing.join(", ")}`
                : "Dependencies installed.";
            const cap = document.createElement("div");
            cap.className = `capability-banner ${
              missing.length ? "capability-warn" : "capability-ok"
            }`;
            const headline = missing.length
              ? "Optional enhancements unavailable"
              : "All optional analysis enhancements available";
            const detail = missing.length
              ? `Disabled: ${missing.join("; ")}.`
              : "OCR and embedding similarity are available for harder near-duplicate cases.";
            cap.innerHTML = `
              <strong>${headline}</strong>
              <div class="small-muted mt-6">${detail}</div>
              <div class="small-muted mt-6"><strong>OCR:</strong> ${
                ocr.available ? "available" : "unavailable"
              }${ocr.disabled ? " (disabled)" : ""}. ${ocrMissing}</div>
              <div class="small-muted mt-6"><strong>Embedding:</strong> ${
                embeddings.available ? "available" : "unavailable"
              }${embeddings.disabled ? " (disabled)" : ""}. ${embedMissing}</div>
            `;
            summaryEl.appendChild(cap);
          }

          const grouped = preview.grouped || {};
          Object.keys(grouped).forEach((groupName) => {
            const section = document.createElement("section");
            section.className = "analysis-group";
            const header = document.createElement("div");
            header.className = "analysis-group-header";
            header.innerHTML = `<h3>${groupName}</h3><span>${grouped[groupName].length} actions</span>`;
            section.appendChild(header);

            grouped[groupName].forEach((action) => {
              const actionIndex = preview.actions.findIndex(
                (candidate) =>
                  candidate.from === action.from &&
                  candidate.to === action.to &&
                  (candidate.action || candidate.type) === (action.action || action.type)
              );
              const card = document.createElement("label");
              card.className = "analysis-action";
              const checkbox = document.createElement("input");
              checkbox.type = "checkbox";
              checkbox.checked = analysisState.selected.has(actionIndex);
              checkbox.onchange = () => {
                if (checkbox.checked) analysisState.selected.add(actionIndex);
                else analysisState.selected.delete(actionIndex);
              };
              const body = document.createElement("div");
              body.className = "analysis-action-body";
              const nearDupSignals =
                action.near_duplicate_signals ||
                (action.metadata && Array.isArray(action.metadata.signals)
                  ? action.metadata.signals
                  : []);
              const signalHtml = nearDupSignals.length
                ? `<div class="analysis-signal-row">${nearDupSignals
                    .map((signal) => `<span class="analysis-signal-pill">${signal}</span>`)
                    .join("")}</div>`
                : "";
              body.innerHTML = `
                <div class="analysis-action-top">
                  <span class="action-pill">${action.action || action.type}</span>
                  <span class="confidence-pill">${Math.round(
                    (action.confidence || 0) * 100
                  )}%</span>
                </div>
                <div class="analysis-path-line"><strong>From:</strong> ${action.from || ""}</div>
                <div class="analysis-path-line"><strong>To:</strong> ${action.to || ""}</div>
                ${signalHtml}
                <div class="analysis-reason">${action.reason || "No reason provided."}</div>
              `;
              card.appendChild(checkbox);
              card.appendChild(body);
              section.appendChild(card);
            });
            previewEl.appendChild(section);
          });

          const controls = document.createElement("div");
          controls.className = "analysis-controls";
          const executeBtn = document.createElement("button");
          executeBtn.className = "btn primary";
          executeBtn.textContent = "Execute Selected";
          executeBtn.onclick = async () => {
            if (!analysisState.opId) return;
            executeBtn.disabled = true;
            try {
              const response = await fetch(`${API_BASE}/api/organise/execute`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                  op_id: analysisState.opId,
                  selected_actions: selectedActionIndexes(),
                  create_snapshot: document.getElementById("analysis-create-snapshot").checked,
                }),
              });
              const payload = await response.json();
              showAlert(`Executed ${payload.executed ? payload.executed.length : 0} actions`);
              loadOps();
            } catch (e) {
              showAlert(`Execution failed: ${e.message || e}`);
            } finally {
              executeBtn.disabled = false;
            }
          };
          const previewUndoBtn = document.createElement("button");
          previewUndoBtn.className = "btn";
          previewUndoBtn.textContent = "Preview Undo";
          previewUndoBtn.onclick = async () => {
            if (!analysisState.opId) return;
            const response = await fetch(`${API_BASE}/api/organise/undo`, {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ op_id: analysisState.opId, dry_run: true }),
            });
            const payload = await response.json();
            openPreviewModal({
              op: { id: analysisState.opId },
              actions: payload.actions || [],
              summary: payload.summary || {},
            });
          };
          controls.appendChild(executeBtn);
          controls.appendChild(previewUndoBtn);
          previewEl.appendChild(controls);

          chatEl.innerHTML = `
            <div class="chat-refine-card">
              <h3>Refine with natural language</h3>
              <textarea id="analysis-chat-message" placeholder="Example: don't delete anything from Downloads, and avoid symlinks."></textarea>
              <div class="mt-8">
                <button id="analysis-chat-send" class="btn">Refine Actions</button>
              </div>
            </div>
          `;
          document.getElementById("analysis-chat-send").onclick = async () => {
            const message = document.getElementById("analysis-chat-message").value;
            if (!analysisState.opId || !message.trim()) return;
            const button = document.getElementById("analysis-chat-send");
            button.disabled = true;
            try {
              const response = await fetch(`${API_BASE}/api/chat`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ op_id: analysisState.opId, message }),
              });
              const payload = await parseApiPayload(response);
              renderAnalysisPreview(payload);
            } catch (e) {
              showAlert(`Chat refinement failed: ${e.message || e}`);
            } finally {
              button.disabled = false;
            }
          };
        }

        async function runAnalysis() {
          const path = document.getElementById("analysis-path").value || undefined;
          const maxFiles = parseInt(document.getElementById("analysis-max-files").value || "", 10);
          const progressEl = document.getElementById("analysis-progress");
          resetAnalysisEventSource();
          try {
            const startResponse = await fetch(`${API_BASE}/api/analyse/start`, {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({
                path,
                max_files: Number.isNaN(maxFiles) ? undefined : maxFiles,
              }),
            });
            const startPayload = await parseApiPayload(startResponse);
            const jobId = startPayload.job_id;
            analysisState.activeJobId = jobId;
            progressEl.innerHTML = `
              <div class="progress"><div class="progress-bar indeterminate" id="analysis-progress-bar"></div></div>
              <div class="progress-text" id="analysis-progress-text">Building file contexts…</div>
              <div class="mt-6"><button id="analysis-cancel" class="btn">Cancel Analysis</button></div>
            `;
            const cancelBtn = document.getElementById("analysis-cancel");
            if (cancelBtn) {
              cancelBtn.onclick = async () => {
                if (!analysisState.activeJobId) return;
                cancelBtn.disabled = true;
                try {
                  const cancelResponse = await fetch(`${API_BASE}/api/scan/cancel`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ job_id: analysisState.activeJobId }),
                  });
                  await parseApiPayload(cancelResponse);
                  showAlert("Analysis cancellation requested");
                } catch (e) {
                  showAlert(`Cancel request failed: ${e.message || e}`);
                } finally {
                  cancelBtn.disabled = false;
                }
              };
            }

            const evt = new EventSource(`${API_BASE}/api/scan/events/${jobId}`);
            analysisState.eventSource = evt;
            evt.onmessage = async (event) => {
              const data = JSON.parse(event.data || "{}");
              const text = document.getElementById("analysis-progress-text");
              if (data.progress && data.progress.processed && text) {
                text.textContent = `Analysed ${data.progress.processed} files`;
              }
              if (data.status === "cancelled") {
                resetAnalysisEventSource();
                analysisState.activeJobId = null;
                if (text) text.textContent = "Analysis cancelled";
                return;
              }
              if (data.status === "failed") {
                resetAnalysisEventSource();
                analysisState.activeJobId = null;
                if (text) text.textContent = "Analysis failed";
                showAlert(`Analysis failed: ${data.error || "Unknown error"}`);
                return;
              }
              if (data.status === "finished") {
                resetAnalysisEventSource();
                if (text) text.textContent = "Reasoning over the drive…";
                try {
                  const reasonResponse = await fetch(`${API_BASE}/api/analyse/reason`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ job_id: jobId }),
                  });
                  const preview = await parseApiPayload(reasonResponse);
                  renderAnalysisPreview(preview);
                } catch (e) {
                  if (e && e.code === "job_cancelled") {
                    showAlert("Reasoning skipped: analysis was cancelled. Run analysis again.");
                  } else if (e && e.code === "job_not_ready") {
                    showAlert("Reasoning deferred: analysis is still running. Please wait.");
                  } else if (e && e.code === "not_found") {
                    showAlert("Reasoning failed: analysis job not found. Run analysis again.");
                  } else {
                    showAlert(`Reasoning failed: ${e.message || e}`);
                  }
                } finally {
                  analysisState.activeJobId = null;
                }
              }
            };
            evt.onerror = () => {
              /* SSE reconnect is not needed here; the result request will fail if the job did not finish. */
            };
          } catch (e) {
            analysisState.activeJobId = null;
            progressEl.innerHTML = `<div class="progress-text">Failed to start analysis.</div>`;
            showAlert(`Analysis start failed: ${e.message || e}`);
          }
        }

        async function loadOps() {
          const res = await fetch(`${API_BASE}/api/ops`);
          const j = await res.json();
          const list = document.getElementById("ops-list");
          list.innerHTML = "";
          const ops = j.ops || {};
          for (const opId of Object.keys(ops)) {
            const op = ops[opId];
            const card = document.createElement("div");
            card.className = "card";
            const title = document.createElement("div");
            title.innerHTML = `<strong>Op:</strong> ${opId} — <em>${op.status}</em>`;
            card.appendChild(title);
            const meta = document.createElement("div");
            meta.textContent = JSON.stringify(op.metadata || {});
            card.appendChild(meta);
            const view = document.createElement("button");
            view.textContent = "View Details";
            view.className = "btn";
            view.onclick = async () => {
              const dres = await fetch(`${API_BASE}/api/ops/${opId}/preview`);
              const dj = await dres.json();
              const det = document.getElementById("ops-detail");
              det.innerHTML = `<pre>${JSON.stringify(dj, null, 2)}</pre>`;
            };
            card.appendChild(view);
            const undo = document.createElement("button");
            undo.textContent = "Undo";
            undo.className = "btn";
            undo.onclick = async () => {
              const r = await fetch(`${API_BASE}/api/organise/undo`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ op_id: opId }),
              });
              const jr = await r.json();
              showAlert(JSON.stringify(jr));
              loadOps();
            };
            const previewUndo = document.createElement("button");
            previewUndo.textContent = "Preview Undo";
            previewUndo.className = "btn";
            previewUndo.onclick = async () => {
              const r = await fetch(`${API_BASE}/api/organise/undo`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ op_id: opId, dry_run: true }),
              });
              const jr = await r.json();
              const det = document.getElementById("ops-detail");
              det.innerHTML = `<pre>${JSON.stringify(jr, null, 2)}</pre>`;
            };
            card.appendChild(undo);
            card.appendChild(previewUndo);
            const del = document.createElement("button");
            del.textContent = "Delete Backup";
            del.className = "btn secondary";
            del.onclick = async () => {
              const r = await fetch(`${API_BASE}/api/recycle/delete_op`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ op_id: opId }),
              });
              const jd = await r.json();
              showAlert(JSON.stringify(jd));
              loadOps();
            };
            const previewDelete = document.createElement("button");
            previewDelete.textContent = "Preview Delete";
            previewDelete.className = "btn";
            previewDelete.onclick = async () => {
              const r = await fetch(`${API_BASE}/api/recycle/delete_op`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ op_id: opId, dry_run: true }),
              });
              const jd = await r.json();
              const det = document.getElementById("ops-detail");
              det.innerHTML = `<pre>${JSON.stringify(jd, null, 2)}</pre>`;
            };
            card.appendChild(previewDelete);
            card.appendChild(del);
            list.appendChild(card);
          }
        }
        document.getElementById("analysis-run").onclick = runAnalysis;
        document.getElementById("ops-refresh").onclick = loadOps;
        loadOps();
        break;
      case "recycle":
        main.innerHTML = `
                    <h2>Recycle Bin</h2>
                    <label>Retention days: <input id="recycle-days" type="number" value="30"></label>
                    <button id="recycle-clean" class="btn">Run Cleanup</button>
                    <div id="recycle-list" class="mt-1"></div>
                `;
        document.getElementById("recycle-clean").onclick = async () => {
          const days = parseInt(document.getElementById("recycle-days").value || "30", 10);
          const res = await fetch(`${API_BASE}/api/recycle/cleanup`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ retention_days: days }),
          });
          const j = await res.json();
          showAlert(`Cleanup: ${JSON.stringify(j)}`);
          loadRecycle();
        };
        async function loadRecycle() {
          const res = await fetch(`${API_BASE}/api/recycle/list`);
          const j = await res.json();
          const list = document.getElementById("recycle-list");
          list.innerHTML = "";
          const data = j.recycle || {};
          for (const opId of Object.keys(data)) {
            const op = data[opId];
            const card = document.createElement("div");
            card.className = "card";
            const title = document.createElement("div");
            title.innerHTML = `<strong>Op:</strong> ${opId} — <em>${op.status}</em>`;
            card.appendChild(title);
            const meta = document.createElement("div");
            meta.textContent = JSON.stringify(op.metadata || {});
            card.appendChild(meta);
            const files = document.createElement("ul");
            (op.files || []).forEach((f) => {
              const li = document.createElement("li");
              li.textContent = `${f.path} — ${f.size} bytes`;
              files.appendChild(li);
            });
            card.appendChild(files);
            const undo = document.createElement("button");
            undo.textContent = "Undo (restore)";
            undo.className = "btn";
            undo.onclick = async () => {
              const r = await fetch(`${API_BASE}/api/organise/undo`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ op_id: opId }),
              });
              const jr = await r.json();
              showAlert(JSON.stringify(jr));
              loadRecycle();
            };
            const previewUndo = document.createElement("button");
            previewUndo.textContent = "Preview Undo";
            previewUndo.className = "btn";
            previewUndo.onclick = async () => {
              const r = await fetch(`${API_BASE}/api/organise/undo`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ op_id: opId, dry_run: true }),
              });
              const jr = await r.json();
              showAlert(JSON.stringify(jr));
              loadRecycle();
            };
            card.appendChild(undo);
            card.appendChild(previewUndo);
            const del = document.createElement("button");
            del.textContent = "Delete Backup (permanent)";
            del.className = "btn secondary";
            del.onclick = async () => {
              const r = await fetch(`${API_BASE}/api/recycle/delete_op`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ op_id: opId }),
              });
              const jd = await r.json();
              showAlert(JSON.stringify(jd));
              loadRecycle();
            };
            const previewDelete = document.createElement("button");
            previewDelete.textContent = "Preview Delete";
            previewDelete.className = "btn";
            previewDelete.onclick = async () => {
              const r = await fetch(`${API_BASE}/api/recycle/delete_op`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ op_id: opId, dry_run: true }),
              });
              const jd = await r.json();
              showAlert(JSON.stringify(jd));
              loadRecycle();
            };
            card.appendChild(previewDelete);
            card.appendChild(del);
            list.appendChild(card);
          }
        }
        loadRecycle();
        break;
      case "preferences":
        main.innerHTML = `
                    <h2>Preferences</h2>
                    <p>Set your provider defaults and manage the local Ollama runtime.</p>
                    <label>Provider:
                      <select id="pref-model">
                        <option value="modelito">modelito</option>
                        <option value="ci_dummy">ci_dummy</option>
                      </select>
                    </label>
                    <label class="ml-8">Ollama model: <input id="pref-ollama-model" type="text" placeholder="llama3.2:3b"></label>
                    <button id="pref-save">Save</button>
                    <pre id="pref-result"></pre>
                    <h3 class="mt-12">Ollama</h3>
                    <div>
                      <button id="ollama-refresh" class="btn">Refresh Status</button>
                      <button id="ollama-install" class="btn ml-8">Install Ollama</button>
                      <button id="ollama-start" class="btn ml-8">Start Ollama</button>
                      <button id="ollama-stop" class="btn ml-8">Stop Ollama</button>
                    </div>
                    <div class="mt-6">
                      <label>Model name: <input id="ollama-model-name" type="text" placeholder="llama3.2:3b"></label>
                      <button id="ollama-pull" class="btn ml-8">Pull</button>
                      <button id="ollama-serve" class="btn ml-8">Serve</button>
                      <button id="ollama-delete" class="btn secondary ml-8">Delete Model</button>
                    </div>
                    <div id="ollama-status" class="mt-8 small-muted"></div>
                    <pre id="ollama-result"></pre>
                `;
        // Scan index admin UI
        const prefExtra = document.createElement("div");
        prefExtra.innerHTML = `
                    <h3>Scan Index</h3>
                    <button id="index-stats" class="btn">Get Index Stats</button>
                    <button id="index-rebuild" class="btn">Rebuild Index (sample hashes)</button>
                    <button id="index-rebuild-bg" class="btn ml-8">Rebuild Index (Background)</button>
                    <div class="mt-6">
                      <label>Prune retention days: <input id="index-prune-days" type="number" value="365"></label>
                      <label class="ml-8">Max entries: <input id="index-prune-max" type="number" placeholder="(optional)"></label>
                      <button id="index-prune" class="btn">Prune Index</button>
                    </div>
                    <pre id="index-result" class="mt-8"></pre>
                                        <h3 class="mt-12">Scheduled Maintenance</h3>
                                        <label><input id="maint-enabled" type="checkbox"> Enable scheduled maintenance</label>
                                        <div class="mt-6">
                                            <label>Prune days: <input id="maint-prune-days" type="number" value="30"></label>
                                            <label class="ml-8">Max entries: <input id="maint-prune-max" type="number" placeholder="(optional)"></label>
                                            <label class="ml-8">Interval hours: <input id="maint-interval-hours" type="number" value="24"></label>
                                        </div>
                                        <div class="mt-6">
                                            <button id="maint-save" class="btn">Save Maintenance Settings</button>
                                            <button id="maint-run" class="btn ml-8">Run Now</button>
                                            <button id="maint-status" class="btn ml-8">Show Last Run</button>
                                        </div>
                                        <pre id="maint-result" class="mt-8"></pre>
                `;
        document.getElementById("pref-result").parentNode.appendChild(prefExtra);
        const prefResultEl = document.getElementById("pref-result");
        const ollamaResultEl = document.getElementById("ollama-result");
        const ollamaStatusEl = document.getElementById("ollama-status");
        const getOllamaModelName = () => {
          const explicit = document.getElementById("ollama-model-name").value.trim();
          if (explicit) return explicit;
          return document.getElementById("pref-ollama-model").value.trim();
        };
        const renderOllamaStatus = (status) => {
          if (!status || typeof status !== "object") {
            ollamaStatusEl.textContent = "Unable to load Ollama status.";
            return;
          }
          const localModels = Array.isArray(status.local_models) ? status.local_models : [];
          const runningModels = Array.isArray(status.running_models) ? status.running_models : [];
          const detail = status.detail ? ` | Detail: ${status.detail}` : "";
          ollamaStatusEl.textContent = `SDK: ${
            status.sdk_available ? "available" : "missing"
          } | Installed: ${status.installed ? "yes" : "no"} | Running: ${
            status.running ? "yes" : "no"
          } | Models: ${localModels.length ? localModels.join(", ") : "none"} | Active: ${
            runningModels.length ? runningModels.join(", ") : "none"
          }${detail}`;
          if (!document.getElementById("ollama-model-name").value && localModels.length) {
            document.getElementById("ollama-model-name").value = localModels[0];
          }
        };
        const loadOllamaStatus = async () => {
          const r = await fetch(`${API_BASE}/api/ollama/status`);
          const j = await r.json();
          renderOllamaStatus(j);
          ollamaResultEl.textContent = JSON.stringify(j, null, 2);
          return j;
        };
        const postOllamaAction = async (path, body = {}) => {
          const r = await fetch(`${API_BASE}${path}`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body),
          });
          const j = await r.json();
          renderOllamaStatus(j.ollama || j);
          ollamaResultEl.textContent = JSON.stringify(j, null, 2);
          return j;
        };
        document.getElementById("index-stats").onclick = async () => {
          const r = await fetch("/api/scan_index/stats");
          const j = await r.json();
          document.getElementById("index-result").textContent = JSON.stringify(j, null, 2);
        };
        document.getElementById("index-rebuild").onclick = async () => {
          if (!confirm("Rebuild sample-hashes for scan index? This may take time.")) return;
          const r = await fetch("/api/scan_index/rebuild", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ paths: [window.location.pathname || "/"], min_size: 1 }),
          });
          const j = await r.json();
          document.getElementById("index-result").textContent = JSON.stringify(j, null, 2);
        };

        document.getElementById("index-rebuild-bg").onclick = async () => {
          if (!confirm("Start background rebuild of scan index?")) return;
          const r = await fetch("/api/scan_index/rebuild_async", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ paths: [window.location.pathname || "/"], min_size: 1 }),
          });
          const j = await r.json();
          const jobId = j.job_id;
          const resEl = document.getElementById("index-result");
          resEl.innerHTML = `<div class="progress"><div class="progress-bar" id="index-progress-bar"></div></div><div id="index-progress-text">Job ${jobId} started (backend: ${j.backend})</div>`;

          // connect to SSE for updates
          try {
            if (
              window._diskOrganiserEvtSrc &&
              typeof window._diskOrganiserEvtSrc.close === "function"
            )
              window._diskOrganiserEvtSrc.close();
          } catch (e) {}
          const evt = new EventSource(`/api/scan/events/${jobId}`);
          window._diskOrganiserEvtSrc = evt;
          evt.onmessage = (ev) => {
            try {
              const data = JSON.parse(ev.data || "{}");
              if (data.progress) {
                const p = data.progress;
                const bar = document.getElementById("index-progress-bar");
                const txt = document.getElementById("index-progress-text");
                if (typeof p.processed === "number" && typeof p.upserted === "number") {
                  bar.classList.add("indeterminate");
                  if (txt)
                    txt.textContent = `Job ${jobId} ${data.status || ""} — scanned ${
                      p.processed
                    }, upserted ${p.upserted}`;
                }
              }
              if (data.result) {
                resEl.innerHTML += `<pre>${JSON.stringify(data.result, null, 2)}</pre>`;
                try {
                  evt.close();
                } catch (e) {}
              }
            } catch (e) {
              /* ignore parse errors */
            }
          };
          evt.onerror = () => {
            /* ignore errors, SSE will reconnect */
          };
        };
        document.getElementById("index-prune").onclick = async () => {
          const days = parseInt(document.getElementById("index-prune-days").value || "365", 10);
          const maxEntries = parseInt(document.getElementById("index-prune-max").value || "", 10);
          const body = { retention_days: days };
          if (!Number.isNaN(maxEntries)) body.max_entries = maxEntries;
          const r = await fetch("/api/scan_index/prune", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body),
          });
          const j = await r.json();
          document.getElementById("index-result").textContent = JSON.stringify(j, null, 2);
        };
        document.getElementById("maint-save").onclick = async () => {
          try {
            const prefsRes = await fetch("/api/preferences");
            const pj = await prefsRes.json();
            const prefs = pj.preferences || {};
            prefs.maintenance = {
              enabled: !!document.getElementById("maint-enabled").checked,
              prune_days: parseInt(document.getElementById("maint-prune-days").value || "30", 10),
              prune_max_entries:
                parseInt(document.getElementById("maint-prune-max").value || "", 10) || undefined,
              interval_hours: parseFloat(
                document.getElementById("maint-interval-hours").value || "24"
              ),
            };
            if (Number.isNaN(prefs.maintenance.prune_max_entries))
              delete prefs.maintenance.prune_max_entries;
            const r = await fetch("/api/preferences", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ preferences: prefs }),
            });
            const j = await r.json();
            document.getElementById("maint-result").textContent = JSON.stringify(j, null, 2);
          } catch (e) {
            document.getElementById("maint-result").textContent = String(e);
          }
        };
        document.getElementById("maint-run").onclick = async () => {
          const days = parseInt(document.getElementById("maint-prune-days").value || "30", 10);
          const maxEntries = parseInt(document.getElementById("maint-prune-max").value || "", 10);
          const body = { retention_days: days };
          if (!Number.isNaN(maxEntries)) body.max_entries = maxEntries;
          const r = await fetch("/api/maintenance/run", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body),
          });
          const j = await r.json();
          document.getElementById("maint-result").textContent = JSON.stringify(j, null, 2);
        };
        document.getElementById("maint-status").onclick = async () => {
          const r = await fetch("/api/maintenance/status");
          const j = await r.json();
          document.getElementById("maint-result").textContent = JSON.stringify(j, null, 2);
        };
        document.getElementById("ollama-refresh").onclick = loadOllamaStatus;
        document.getElementById("ollama-install").onclick = async () => {
          await postOllamaAction("/api/ollama/install", {});
        };
        document.getElementById("ollama-start").onclick = async () => {
          await postOllamaAction("/api/ollama/start", {});
        };
        document.getElementById("ollama-stop").onclick = async () => {
          await postOllamaAction("/api/ollama/stop", {});
        };
        document.getElementById("ollama-pull").onclick = async () => {
          const model = getOllamaModelName();
          if (!model) {
            ollamaResultEl.textContent = JSON.stringify({ error: "missing model" }, null, 2);
            return;
          }
          await postOllamaAction("/api/ollama/pull", { model });
        };
        document.getElementById("ollama-serve").onclick = async () => {
          const model = getOllamaModelName();
          await postOllamaAction("/api/ollama/serve", model ? { model } : {});
        };
        document.getElementById("ollama-delete").onclick = async () => {
          const model = getOllamaModelName();
          if (!model) {
            ollamaResultEl.textContent = JSON.stringify({ error: "missing model" }, null, 2);
            return;
          }
          await postOllamaAction("/api/ollama/delete", { model });
        };
        // initialize preferences UI from server
        (async () => {
          try {
            const [modelRes, prefsRes, ollamaRes] = await Promise.all([
              fetch("/api/model"),
              fetch("/api/preferences"),
              fetch("/api/ollama/status"),
            ]);
            const modelJson = await modelRes.json();
            const prefsJson = await prefsRes.json();
            const ollamaJson = await ollamaRes.json();
            const prefs = prefsJson.preferences || {};
            document.getElementById("pref-model").value = modelJson.model || "modelito";
            if (prefs.ollama_model) {
              document.getElementById("pref-ollama-model").value = prefs.ollama_model;
              document.getElementById("ollama-model-name").value = prefs.ollama_model;
            }
            const maint = prefs.maintenance || {};
            document.getElementById("maint-enabled").checked = !!maint.enabled;
            document.getElementById("maint-prune-days").value = maint.prune_days || 30;
            document.getElementById("maint-prune-max").value = maint.prune_max_entries || "";
            document.getElementById("maint-interval-hours").value = maint.interval_hours || 24;
            renderOllamaStatus(ollamaJson);
            ollamaResultEl.textContent = JSON.stringify(ollamaJson, null, 2);
          } catch (e) {
            // ignore
          }
        })();
        document.getElementById("pref-save").onclick = async () => {
          const model = document.getElementById("pref-model").value;
          const ollamaModel = document.getElementById("pref-ollama-model").value.trim();
          const prefsRes = await fetch("/api/preferences");
          const prefsJson = await prefsRes.json();
          const prefs = prefsJson.preferences || {};
          if (ollamaModel) prefs.ollama_model = ollamaModel;
          else delete prefs.ollama_model;
          const [modelRes, prefSaveRes] = await Promise.all([
            fetch(`${API_BASE}/api/model`, {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ model }),
            }),
            fetch(`${API_BASE}/api/preferences`, {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ preferences: prefs }),
            }),
          ]);
          const modelJson = await modelRes.json();
          const savedPrefsJson = await prefSaveRes.json();
          prefResultEl.textContent = JSON.stringify(
            { model: modelJson.model, preferences: savedPrefsJson.preferences },
            null,
            2
          );
          if (ollamaModel) document.getElementById("ollama-model-name").value = ollamaModel;
          await loadOllamaStatus();
        };
        break;
      default:
        main.innerHTML = `<h2>Welcome</h2><p>Select a workflow above to get started.</p>`;
    }
  }
  // Modal helpers (formatting, open/close, grouping UX)
  function formatBytes(n) {
    if (typeof n !== "number") return "" + n;
    if (n === 0) return "0 B";
    if (n < 1024) return n + " B";
    const units = ["KB", "MB", "GB", "TB"];
    let u = -1;
    do {
      n = n / 1024;
      u++;
    } while (n >= 1024 && u < units.length - 1);
    return n.toFixed(2) + " " + units[u];
  }

  function openPreviewModal(preview) {
    const modal = document.getElementById("preview-modal");
    const body = document.getElementById("preview-modal-body");
    const footer = document.getElementById("preview-modal-footer");
    body.innerHTML = "";
    footer.innerHTML = "";
    const title = document.getElementById("preview-modal-title");
    title.textContent =
      preview && preview.op && preview.op.id ? `Preview — ${preview.op.id}` : "Preview";

    // summary
    const summary = document.createElement("div");
    summary.className = "small-muted";
    const s =
      preview && (preview.summary || (preview.result && preview.result.summary))
        ? preview.summary || (preview.result && preview.result.summary)
        : null;
    if (s)
      summary.textContent = `Actions: ${s.actions || 0} — Files: ${
        s.files || 0
      } — Total: ${formatBytes(s.bytes || 0)}`;
    body.appendChild(summary);

    // actions
    const acts =
      (preview && preview.actions) || (preview && preview.result && preview.result.actions) || [];

    // group actions by explicit `group` if present, otherwise by action type
    const groups = {};
    const hasGroup = acts.some((a) => a && a.group !== undefined && a.group !== null);
    acts.forEach((a) => {
      const key = hasGroup ? a.group || "default" : a.action || a.type || "other";
      groups[key] = groups[key] || [];
      groups[key].push(a);
    });

    function groupIconFor(name) {
      const k = String(name || "").toLowerCase();
      if (k.includes("move")) return "➡️";
      if (k.includes("delete") || k.includes("remove") || k.includes("del")) return "🗑️";
      if (k.includes("backup")) return "🗂️";
      if (k.includes("create") || k.includes("dir") || k.includes("folder")) return "📁";
      if (k.includes("copy")) return "📄";
      return "🔧";
    }

    Object.keys(groups).forEach((groupName) => {
      const groupActs = groups[groupName] || [];
      const details = document.createElement("details");
      details.className = "preview-group";
      details.open = true;

      const summaryHdr = document.createElement("summary");
      summaryHdr.className = "group-header";
      const icon = document.createElement("span");
      icon.className = "group-icon";
      icon.textContent = groupIconFor(groupName);
      const hdrText = document.createElement("span");
      const totalBytes = groupActs.reduce((acc, it) => acc + (it.size || it.bytes || 0), 0);
      hdrText.textContent = ` ${groupName} — ${groupActs.length} items — ${formatBytes(
        totalBytes
      )}`;
      summaryHdr.appendChild(icon);
      summaryHdr.appendChild(hdrText);
      details.appendChild(summaryHdr);

      const table = document.createElement("table");
      table.className = "preview-actions";
      const thead = document.createElement("thead");
      thead.innerHTML = `<tr><th class="action-type">Type</th><th>Path</th><th>Target</th><th class="action-size">Size</th><th>Status</th></tr>`;
      table.appendChild(thead);
      const tbody = document.createElement("tbody");
      groupActs.forEach((a) => {
        const tr = document.createElement("tr");
        const typeTd = document.createElement("td");
        typeTd.className = "action-type";
        typeTd.textContent = a.action || a.type || "";
        const fromTd = document.createElement("td");
        fromTd.className = "action-path";
        fromTd.textContent = a.src || a.path || a.from || "";
        const toTd = document.createElement("td");
        toTd.className = "action-path";
        toTd.textContent = a.dst || a.to || "";
        const sizeTd = document.createElement("td");
        sizeTd.className = "action-size";
        sizeTd.textContent = formatBytes(a.size || a.bytes || 0);
        const statusTd = document.createElement("td");
        const status = a.status || (a.ok ? "ok" : a.err ? "error" : "pending");
        const span = document.createElement("span");
        span.className =
          "status-preview " +
          (status === "ok"
            ? "status-ok"
            : status === "warning"
            ? "status-warn"
            : status === "error" || status === "err"
            ? "status-err"
            : "");
        span.textContent = status;
        statusTd.appendChild(span);
        tr.appendChild(typeTd);
        tr.appendChild(fromTd);
        tr.appendChild(toTd);
        tr.appendChild(sizeTd);
        tr.appendChild(statusTd);
        tbody.appendChild(tr);
      });
      table.appendChild(tbody);
      details.appendChild(table);
      body.appendChild(details);
    });

    // footer buttons
    const close = document.createElement("button");
    close.textContent = "Close";
    close.onclick = closePreviewModal;
    close.classList.add("btn");
    footer.appendChild(close);

    // optional execute button
    const execute = document.createElement("button");
    execute.textContent = "Execute";
    execute.onclick = async () => {
      execute.disabled = true;
      try {
        const opId = preview && preview.op && preview.op.id;
        if (!opId) throw new Error("Missing op id");
        const r = await fetch("/api/organise/execute", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ op_id: opId }),
        });
        const j = await r.json();
        showAlert("Executed: " + (j.status || "ok"));
        closePreviewModal();
      } catch (e) {
        showAlert("Execute failed: " + e.message);
      } finally {
        execute.disabled = false;
      }
    };
    execute.classList.add("btn", "primary");
    footer.appendChild(execute);

    // show modal
    modal.classList.remove("hidden");
    modal.setAttribute("aria-hidden", "false");
  }

  function closePreviewModal() {
    const modal = document.getElementById("preview-modal");
    modal.classList.add("hidden");
    modal.setAttribute("aria-hidden", "true");
  }

  // bind modal close via backdrop or close button
  document.addEventListener("click", (ev) => {
    const modal = document.getElementById("preview-modal");
    if (!modal || modal.classList.contains("hidden")) return;
    const closeBtn = document.getElementById("preview-modal-close");
    if (ev.target === document.getElementById("preview-modal-backdrop") || ev.target === closeBtn)
      closePreviewModal();
  });

  // expose modal helpers on window for tests
  try {
    window.openPreviewModal = openPreviewModal;
    window.closePreviewModal = closePreviewModal;
    window.formatBytes = formatBytes;
  } catch (e) {}

  // Side-panel helpers (details panel)
  function openSidePanel(titleText, contentNode) {
    const panel = document.getElementById("side-panel");
    const body = document.getElementById("side-panel-body");
    const title = document.getElementById("side-panel-title");
    if (!panel || !body || !title) return;
    title.textContent = titleText || "Details";
    body.innerHTML = "";
    if (typeof contentNode === "string") body.innerHTML = contentNode;
    else if (contentNode instanceof Node) body.appendChild(contentNode);
    panel.classList.remove("hidden");
    panel.setAttribute("aria-hidden", "false");
    // focus close button for keyboard users
    const closeBtn = document.getElementById("side-panel-close");
    if (closeBtn) closeBtn.focus();
  }

  function closeSidePanel() {
    const panel = document.getElementById("side-panel");
    if (!panel) return;
    panel.classList.add("hidden");
    panel.setAttribute("aria-hidden", "true");
    // return focus to main content
    const main = document.getElementById("main-content");
    if (main) main.focus();
  }

  // close button binding
  try {
    const spClose = document.getElementById("side-panel-close");
    if (spClose) spClose.addEventListener("click", closeSidePanel);
  } catch (e) {}

  // global key handler: Esc closes modals and side-panel
  document.addEventListener("keydown", (ev) => {
    if (ev.key === "Escape" || ev.key === "Esc") {
      const panel = document.getElementById("side-panel");
      if (panel && !panel.classList.contains("hidden")) {
        closeSidePanel();
        return;
      }
      const modal = document.getElementById("preview-modal");
      if (modal && !modal.classList.contains("hidden")) closePreviewModal();
    }
  });

  // helper: mark active nav button
  function setActiveNav(section) {
    try {
      document.querySelectorAll(".site-nav .nav-btn").forEach((b) => {
        b.classList.remove("active");
        try {
          b.setAttribute("aria-pressed", "false");
          b.removeAttribute("aria-current");
        } catch (e) {}
      });
      const el = document.getElementById("nav-" + section);
      if (el) {
        el.classList.add("active");
        try {
          el.setAttribute("aria-pressed", "true");
          el.setAttribute("aria-current", "page");
        } catch (e) {}
      }
    } catch (e) {
      // ignore when DOM not ready
    }
  }

  document.getElementById("nav-duplicates").onclick = () => {
    setActiveNav("duplicates");
    loadContent("duplicates");
  };
  document.getElementById("nav-visualisation").onclick = () => {
    setActiveNav("visualisation");
    loadContent("visualisation");
  };
  document.getElementById("nav-recycle").onclick = () => {
    setActiveNav("recycle");
    loadContent("recycle");
  };
  document.getElementById("nav-organise").onclick = () => {
    setActiveNav("organise");
    loadContent("organise");
  };
  document.getElementById("nav-preferences").onclick = () => {
    setActiveNav("preferences");
    loadContent("preferences");
  };
  // initial load (no nav active)
  loadContent();
});

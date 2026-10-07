const fs = require("fs");
const path = require("path");
const { createObservationDemo } = require("../project-observation-demo");
const fixture = require("./project-observation-fixture.json");
const copy = (value) => JSON.parse(JSON.stringify(value));
const settle = () => new Promise((resolve) => setTimeout(resolve, 0));
const deferred = () => {
  let resolve;
  let reject;
  const promise = new Promise((yes, no) => {
    resolve = yes;
    reject = no;
  });
  return { promise, resolve, reject };
};
const response = (value, status = 200) => ({
  ok: status === 200,
  status,
  json: async () => copy(value),
});
const id = (name) => document.getElementById(`observation-${name}`);
let fetchMock;
let demo;
let pageListeners;
function input(name, value, event = "input") {
  const node = id(name);
  if (node.type === "checkbox") node.checked = value;
  else node.value = value;
  node.dispatchEvent(new Event(event, { bubbles: true }));
}
function submit() {
  id("form").dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
}
// These are transport fixtures, not a JavaScript planner. The HTTP suite proves
// exact Python-adapter equality; here only the displayed fields are projected.
function reviewed(
  folder = fixture.decision.destination_folder,
  members = fixture.decision.member_paths,
  root = fixture.decision.destination_root_id
) {
  const value = copy(fixture);
  value.decision_revision = 2;
  value.decision = {
    ...value.decision,
    member_paths: copy(members),
    destination_root_id: root,
    destination_folder: folder,
  };
  value.draft.members = members
    .map((member) => {
      const entry = fixture.choices.find((choice) => choice.entry.id === member.entry_id).entry;
      return {
        ...copy(fixture.draft.members[0]),
        entry_id: entry.id,
        observation: copy(entry),
        project_path: member.project_path,
        source: { root_id: entry.root_id, relative_path: entry.relative_path },
        intended: { root_id: root, relative_path: `${folder}/${member.project_path}` },
        placement:
          root === entry.root_id && `${folder}/${member.project_path}` === entry.relative_path
            ? "current_address_requires_identity"
            : "proposed_address_requires_review",
      };
    })
    .sort((a, b) => a.entry_id.localeCompare(b.entry_id));
  value.draft.member_ids = value.draft.members.map((member) => member.entry_id);
  value.draft.observation_scope.selected_entry_count = members.length;
  value.draft.capacity.known_recorded_path_logical_bytes = value.draft.members.reduce(
    (total, member) => total + (member.observation.logical_bytes || 0),
    0
  );
  value.draft.capacity.unknown_size_member_ids = value.draft.members
    .filter((member) => member.observation.logical_bytes === null)
    .map((member) => member.entry_id);
  return value;
}
beforeEach(async () => {
  document.documentElement.innerHTML = fs
    .readFileSync(path.join(__dirname, "../project-observation-demo.html"), "utf8")
    .replace(/<!doctype html>/i, "");
  pageListeners = [];
  const add = window.addEventListener.bind(window);
  jest.spyOn(window, "addEventListener").mockImplementation((name, listener, ...args) => {
    if (["pageshow", "pagehide"].includes(name)) pageListeners.push([name, listener]);
    add(name, listener, ...args);
  });
  fetchMock = jest.fn().mockResolvedValue(response(fixture));
  demo = createObservationDemo(document, fetchMock);
  await demo.ready;
});
afterEach(() => {
  for (const [name, listener] of pageListeners) window.removeEventListener(name, listener);
  jest.restoreAllMocks();
});

test("fixed source and reference render with every authority and evidence gap", () => {
  expect(document.body.textContent).toContain(
    "Synthetic observations; no drives or providers connected"
  );
  expect(id("scope").textContent).toContain(
    "8 fixed selectable examples from 32 observation records across 2 recorded roots"
  );
  expect(id("clock").textContent).toContain("not today");
  expect(id("members").querySelectorAll('input[type="checkbox"]')).toHaveLength(8);
  expect(id("members").querySelectorAll("input:checked")).toHaveLength(3);
  expect(id("path-3").disabled).toBe(true);
  for (const label of [
    "Physical drive identity",
    "Current content versions",
    "Application dependencies",
    "Backup targets and coverage",
    "Independent copy count",
    "Restore scope and usability",
  ]) {
    const metric = [...id("review-content").querySelectorAll(".metric")].find((node) =>
      node.textContent.includes(label)
    );
    expect(metric.querySelector("dd").textContent).toBe("Unknown");
  }
  expect(id("review-content").textContent).toContain(fixture.observation_digest);
  expect(id("review-content").textContent).toContain("Source safe to erase: false");
  expect(id("review-content").textContent).toContain("Logical copy bytes: Unknown");
});

test("submits only exact explicit intent plus all three reference guards", async () => {
  input("member-1", false);
  input("member-3", true);
  input("path-0", "Design/final.blend");
  input("folder", "Reviewed Aurora");
  input("root", fixture.roots[0].id, "change");
  const members = [0, 2, 3].map((index) => ({
    entry_id: fixture.choices[index].entry.id,
    project_path: id(`path-${index}`).value,
  }));
  fetchMock.mockResolvedValueOnce(
    response(reviewed("Reviewed Aurora", members, fixture.roots[0].id))
  );
  submit();
  await settle();
  const [url, options] = fetchMock.mock.calls[1];
  expect(url).toBe("/api/observation/review");
  expect(JSON.parse(options.body)).toEqual({
    expected_source_revision: 1,
    expected_observation_digest: fixture.observation_digest,
    expected_reference_decision_digest: fixture.reference_decision_digest,
    member_paths: members,
    destination_root_id: fixture.roots[0].id,
    destination_folder: "Reviewed Aurora",
  });
  expect(options).toMatchObject({
    method: "POST",
    credentials: "omit",
    cache: "no-store",
    redirect: "error",
    headers: { "X-Demo-Token": "__DEMO_PROCESS_TOKEN__", "Content-Type": "application/json" },
  });
  expect(id("path-1").disabled).toBe(true);
  expect(id("path-3").disabled).toBe(false);
  expect(id("status").textContent).toContain("Draft reviewed");
  expect(document.activeElement).toBe(id("review-heading"));
});

test("editing invalidates displayed reference without computing review rules", () => {
  input("path-0", "Design/revised.blend");
  expect(id("review-content").children).toHaveLength(0);
  expect(id("caption").textContent).toContain("Intent changed");
  expect(fetchMock).toHaveBeenCalledTimes(1);
});

test("dismiss restores exact reference decision and focus", () => {
  input("member-0", false);
  input("member-3", true);
  input("folder", "Changed");
  input("path-2", "Changed.toml");
  id("dismiss").click();
  expect(id("member-0").checked).toBe(true);
  expect(id("member-3").checked).toBe(false);
  expect(id("folder").value).toBe(fixture.decision.destination_folder);
  expect(id("path-2").value).toBe("pyproject.toml");
  expect(id("caption").textContent).toContain("Reference observation draft");
  expect(document.activeElement).toBe(id("review-button"));
});

for (const action of ["edit", "dismiss", "reload"])
  test(`late review cannot overwrite ${action}`, async () => {
    const wait = deferred();
    fetchMock.mockReturnValueOnce(wait.promise);
    submit();
    expect(id("review-button").disabled).toBe(true);
    if (action === "edit") input("folder", "Latest intent");
    if (action === "dismiss") id("dismiss").click();
    if (action === "reload") {
      id("reload").click();
      await settle();
    }
    wait.resolve(response(reviewed()));
    await settle();
    if (action === "edit") {
      expect(id("folder").value).toBe("Latest intent");
      expect(id("review-content").children).toHaveLength(0);
    } else expect(id("caption").textContent).toContain("Reference observation draft");
    expect(id("error").hidden).toBe(true);
  });

test("late error cannot displace newer accepted intent", async () => {
  const old = deferred();
  fetchMock.mockReturnValueOnce(old.promise);
  submit();
  input("folder", "New intent");
  fetchMock.mockResolvedValueOnce(response(reviewed("New intent")));
  submit();
  await settle();
  old.reject(new Error("Old failure"));
  await settle();
  expect(id("status").textContent).toContain("Draft reviewed");
  expect(id("review-content").textContent).toContain("New intent/");
  expect(id("error").hidden).toBe(true);
});

test("repeated submits use one pending request and failure retains edits for retry", async () => {
  input("folder", "Retry me");
  const wait = deferred();
  fetchMock.mockReturnValueOnce(wait.promise);
  submit();
  submit();
  expect(fetchMock).toHaveBeenCalledTimes(2);
  wait.reject(new Error("Temporary response failure"));
  await settle();
  expect(id("folder").value).toBe("Retry me");
  expect(id("review-content").children).toHaveLength(0);
  expect(id("review-button").disabled).toBe(false);
  fetchMock.mockResolvedValueOnce(response(reviewed("Retry me")));
  submit();
  await settle();
  expect(id("status").textContent).toContain("Draft reviewed");
});

for (const status of [403, 409, 400])
  test(`HTTP ${status} invalidates result and preserves edits`, async () => {
    input("folder", "Retained intent");
    fetchMock.mockResolvedValueOnce(response({ error: "Invalid explicit path" }, status));
    submit();
    await settle();
    expect(id("review-content").children).toHaveLength(0);
    expect(id("error").hidden).toBe(false);
    expect(id("folder").value).toBe("Retained intent");
    expect(id("error").textContent).toContain(
      status === 403 ? "renew" : status === 409 ? "reference changed" : "Invalid explicit path"
    );
  });

test("failed reference clears controls and can reload", async () => {
  fetchMock.mockRejectedValueOnce(new Error("Reference unavailable"));
  id("reload").click();
  await settle();
  expect(id("fields").disabled).toBe(true);
  expect(id("members").children).toHaveLength(0);
  expect(id("review-content").children).toHaveLength(0);
  expect(id("dismiss").disabled).toBe(true);
  id("reload").click();
  await settle();
  expect(id("fields").disabled).toBe(false);
});

test("persisted navigation invalidates pending review and reloads source", async () => {
  const wait = deferred();
  fetchMock.mockReturnValueOnce(wait.promise);
  submit();
  window.dispatchEvent(new PageTransitionEvent("pageshow", { persisted: true }));
  await settle();
  wait.resolve(response(reviewed()));
  await settle();
  expect(fetchMock.mock.calls[2][0]).toBe("/api/observation/reference");
  expect(id("caption").textContent).toContain("Reference observation draft");
});

const corruptions = {
  "invalid decision digest": (value) => {
    value.draft.decision_digest = "not-a-digest";
  },
  "recorded size summary": (value) => {
    value.draft.capacity.known_recorded_path_logical_bytes++;
  },
  "unknown size summary": (value) => {
    value.draft.capacity.unknown_size_member_ids.push(value.draft.member_ids[0]);
  },
  "recorded scan scope": (value) => {
    value.draft.observation_scope.scan.status = "complete";
  },
  "scope selected count": (value) => {
    value.draft.observation_scope.selected_entry_count++;
  },
  "recorded freshness": (value) => {
    value.draft.recorded_scan_freshness = "invented";
  },
  limitations: (value) => {
    value.draft.limitations = [];
  },
  "duplicate projected members": (value) => {
    value.draft.members[1] = copy(value.draft.members[0]);
    value.draft.member_ids[1] = value.draft.member_ids[0];
  },
  "changed immutable observation": (value) => {
    value.draft.members[0].observation.status = "stale";
  },
  "changed recorded hash": (value) => {
    value.draft.members[0].observation.hash.status = "unknown";
  },
  "inconsistent placement": (value) => {
    value.draft.members[0].placement = "current_address_requires_identity";
  },
  "source revision": (value) => {
    value.source_revision++;
  },
  "source digest": (value) => {
    value.observation_digest = value.draft.observation_digest = "0".repeat(64);
  },
  "reference decision digest": (value) => {
    value.reference_decision_digest = "0".repeat(64);
  },
  "decision echo": (value) => {
    value.decision.destination_folder = "Other";
  },
  "source path": (value) => {
    value.draft.members[0].source.relative_path = "Other";
  },
  "intended path": (value) => {
    value.draft.members[0].intended.relative_path = "Other";
  },
  "known physical identity": (value) => {
    value.draft.members[0].volume_id = "invented-volume";
  },
  "known content version": (value) => {
    value.draft.members[0].content_version = "invented-version";
  },
  "known dependencies": (value) => {
    value.draft.members[0].dependency_coverage = "complete";
  },
  "copy bytes": (value) => {
    value.draft.capacity.known_logical_copy_bytes = 0;
  },
  "required bytes": (value) => {
    value.draft.capacity.required_destination_bytes = 0;
  },
  "free bytes": (value) => {
    value.draft.capacity.observed_free_bytes = 100;
  },
  "physical allocation": (value) => {
    value.draft.capacity.physical_allocation_prediction = 0;
  },
  "backup targets": (value) => {
    value.draft.protection.configured_target_ids = [];
  },
  "independent copies": (value) => {
    value.draft.protection.independent_copy_count = 2;
  },
  "restore satisfaction": (value) => {
    value.draft.protection.project_restore_satisfied = true;
  },
  "live backup": (value) => {
    value.live_backup_verified = true;
  },
  execution: (value) => {
    value.draft.executable = true;
  },
  erase: (value) => {
    value.source_safe_to_erase = true;
  },
  "synthetic flag": (value) => {
    value.synthetic = false;
  },
};
for (const [name, corrupt] of Object.entries(corruptions))
  test(`rejects changed response ${name}`, async () => {
    const value = reviewed();
    corrupt(value);
    fetchMock.mockResolvedValueOnce(response(value));
    submit();
    await settle();
    expect(id("status").textContent).toContain("Review unavailable");
    expect(id("review-content").children).toHaveLength(0);
    expect(id("error").hidden).toBe(false);
  });

test("HTML-looking intended names render as text, with no injected element", async () => {
  const folder = '<img src=x onerror="alert(1)">';
  input("folder", folder);
  fetchMock.mockResolvedValueOnce(response(reviewed(folder)));
  submit();
  await settle();
  expect(id("status").textContent).toContain("Draft reviewed");
  expect(id("review-content").textContent).toContain(folder);
  expect(document.querySelector("img")).toBeNull();
});

test("same recorded address stays unresolved with Unknown space", async () => {
  input("member-1", false);
  input("member-2", false);
  input("root", fixture.choices[0].entry.root_id, "change");
  input("folder", "Project Aurora");
  const members = [{ entry_id: fixture.choices[0].entry.id, project_path: "design_v1.blend" }];
  fetchMock.mockResolvedValueOnce(
    response(reviewed("Project Aurora", members, fixture.choices[0].entry.root_id))
  );
  submit();
  await settle();
  expect(id("review-content").textContent).toContain(
    "Same recorded address; physical identity is still Unknown"
  );
  expect(id("review-content").textContent).not.toContain("KEEP CURRENT");
  expect(id("review-content").textContent).toContain("No safe no-op is established");
});

test("overlap scopes retain an unselected occupant instead of claiming all selected members", async () => {
  input("member-1", false);
  input("path-0", "design_v2.blend");
  input("root", fixture.choices[0].entry.root_id, "change");
  input("folder", "Project Aurora");
  const members = [0, 2].map((index) => ({
    entry_id: fixture.choices[index].entry.id,
    project_path: id(`path-${index}`).value,
  }));
  const value = reviewed("Project Aurora", members, fixture.choices[0].entry.root_id);
  const occupant = fixture.recorded_paths.find(
    (record) =>
      record.root_id === fixture.choices[0].entry.root_id &&
      record.relative_path === "Project Aurora/design_v2.blend"
  );
  value.draft.blockers = [
    {
      code: "observed_target_path_overlap",
      member_ids: [members[0].entry_id, occupant.entry_id],
      root_ids: [occupant.root_id],
    },
  ];
  fetchMock.mockResolvedValueOnce(response(value));
  submit();
  await settle();
  const issue = [...id("review-content").querySelectorAll("li")].find((node) =>
    node.textContent.includes("overlaps a recorded entry")
  );
  expect(issue.textContent).not.toContain("All selected members");
  expect(issue.textContent).toContain("Project Aurora/design_v2.blend");
  expect(issue.textContent).toContain("outside selectable membership");
  expect(issue.textContent).not.toContain("pyproject.toml");
});

for (const field of ["choices", "roots"])
  test(`rejects duplicate immutable reference ${field}`, async () => {
    const value = copy(fixture);
    const last = value[field].length - 1;
    value[field][last] = copy(value[field][last - 1]);
    fetchMock.mockResolvedValueOnce(response(value));
    id("reload").click();
    await settle();
    expect(id("status").textContent).toContain("Reference unavailable");
    expect(id("members").children).toHaveLength(0);
    expect(id("fields").disabled).toBe(true);
  });

for (const kind of ["root label", "fixture clock"])
  test(`rejects changed reference ${kind}`, async () => {
    const value = copy(fixture);
    if (kind === "root label") value.roots[0].path = "/invented/root";
    else value.fixture_as_of = "2099-01-01T00:00:00Z";
    fetchMock.mockResolvedValueOnce(response(value));
    id("reload").click();
    await settle();
    expect(id("status").textContent).toContain("Reference unavailable");
    expect(id("review-content").children).toHaveLength(0);
  });

test("Aurora member cards use an intrinsic minimum instead of fixed narrow zoom columns", () => {
  const css = fs.readFileSync(path.join(__dirname, "../project-review-demo.css"), "utf8");
  const rule = css.match(/#observation-members\s*\{([^}]+)\}/);
  expect(rule).not.toBeNull();
  expect(rule[1]).toContain("repeat(auto-fit, minmax(min(100%, 26rem), 1fr))");
});

test("Save review is unavailable for the initial reference", () => {
  expect(id("save")).not.toBeNull();
  expect(id("save").disabled).toBe(true);
  expect(id("save-status").textContent).toContain("Review the current intent first");
});

describe("Save current explicit review", () => {
  let blobs;
  let downloads;
  let createURL;
  let revokeURL;
  let originalCreate;
  let originalRevoke;
  const readBlob = (blob) =>
    new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(reader.result);
      reader.onerror = reject;
      reader.readAsText(blob);
    });
  async function accept(folder = fixture.decision.destination_folder, value = reviewed(folder)) {
    input("folder", folder);
    fetchMock.mockResolvedValueOnce(response(value));
    submit();
    await settle();
    expect(id("status").textContent).toContain("Draft reviewed");
    expect(id("save").disabled).toBe(false);
    return value;
  }
  async function report() {
    id("save").click();
    return JSON.parse(await readBlob(blobs[blobs.length - 1]));
  }
  beforeEach(() => {
    blobs = [];
    downloads = [];
    originalCreate = Object.getOwnPropertyDescriptor(window.URL, "createObjectURL");
    originalRevoke = Object.getOwnPropertyDescriptor(window.URL, "revokeObjectURL");
    createURL = jest.fn((blob) => {
      blobs.push(blob);
      return `blob:synthetic-download-${blobs.length}`;
    });
    revokeURL = jest.fn();
    Object.defineProperty(window.URL, "createObjectURL", {
      configurable: true,
      writable: true,
      value: createURL,
    });
    Object.defineProperty(window.URL, "revokeObjectURL", {
      configurable: true,
      writable: true,
      value: revokeURL,
    });
    jest.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(function () {
      downloads.push({ href: this.href, filename: this.download });
    });
  });
  afterEach(() => {
    window.dispatchEvent(new PageTransitionEvent("pagehide"));
    if (originalCreate) Object.defineProperty(window.URL, "createObjectURL", originalCreate);
    else delete window.URL.createObjectURL;
    if (originalRevoke) Object.defineProperty(window.URL, "revokeObjectURL", originalRevoke);
    else delete window.URL.revokeObjectURL;
  });
  test("exports a versioned safe display report of the exact accepted decision and evidence", async () => {
    const value = await accept("Reviewed layout");
    const saved = await report();
    expect(saved).toMatchObject({
      schema_version: "disk-administration-observation-review-export/v1",
      report_kind: "synthetic_display_report",
      canonical_observation_export: false,
      replayable: false,
      synthetic: true,
      read_only: true,
      executable: false,
      execution_authority: null,
      undo_available: false,
      source_safe_to_erase: false,
      live_backup_verified: false,
      live_restore_verified: false,
      source_revision: 1,
      decision_revision: 2,
      observation_digest: value.observation_digest,
      reference_decision_digest: value.reference_decision_digest,
      decision_digest: value.draft.decision_digest,
      decision: value.decision,
    });
    expect(saved.review.members.map((member) => member.entry_id)).toEqual(value.draft.member_ids);
    expect(saved.review.members.map((member) => member.intended.relative_path)).toEqual(
      value.draft.members.map((member) => member.intended.relative_path)
    );
    expect(saved.review.capacity).toMatchObject({
      known_recorded_path_logical_bytes: 66,
      known_logical_copy_bytes: null,
      required_destination_bytes: null,
      observed_free_bytes: null,
      physical_allocation_prediction: null,
      reclaimed_bytes: 0,
      unknown_size_members: [],
    });
    expect(saved.review.protection).toEqual(value.draft.protection);
    expect(
      saved.review.blockers.map(({ recorded_path_labels, explanation, ...issue }) => issue)
    ).toEqual(value.draft.blockers);
    expect(saved.review.limitations).toEqual(value.draft.limitations);
    expect(saved.review.source_scope).toEqual({
      recorded_roots: fixture.roots.map(({ id, path, status }) => ({ id, path, status })),
      scan_id: value.draft.observation_scope.scan.id,
      scan_status: "partial",
      entry_count: 32,
      recorded_error_count: 2,
      recorded_exclusion_count: 0,
    });
    expect(blobs[0].type).toBe("application/json");
    expect(downloads[0].filename).toMatch(/^disk-organiser-aurora-review-r2-[a-f0-9]{12}\.json$/);
    expect(id("save-status").textContent).toContain("Download requested");
    expect(id("save-status").textContent).not.toContain("saved successfully");
  });
  test("excludes tokens, headers, unrelated nested state and large undisplayed fingerprints", async () => {
    const value = reviewed();
    value.token = "TOP_SECRET";
    value.headers = { "X-Demo-Token": "HEADER_SECRET" };
    value.decision.headers = "DECISION_SECRET";
    value.draft.extra = "DRAFT_SECRET";
    value.draft.capacity.token = "CAPACITY_SECRET";
    value.draft.protection.headers = "PROTECTION_SECRET";
    value.draft.blockers[0].credentials = "ISSUE_SECRET";
    await accept(fixture.decision.destination_folder, value);
    document.body.dataset.secret = "DOM_SECRET";
    const saved = await report();
    const text = JSON.stringify(saved);
    for (const forbidden of [
      "TOP_SECRET",
      "HEADER_SECRET",
      "DECISION_SECRET",
      "DRAFT_SECRET",
      "CAPACITY_SECRET",
      "PROTECTION_SECRET",
      "ISSUE_SECRET",
      "DOM_SECRET",
      "__DEMO_PROCESS_TOKEN__",
      '"fingerprint":',
      "object_id",
      "ctime_ns",
      "inode",
      "credentials",
      "headers",
      "token",
    ])
      expect(text).not.toContain(forbidden);
    expect(Number.isSafeInteger(value.draft.members[0].observation.ctime_ns)).toBe(false);
    expect(saved.review.members[0].volume_id).toBeNull();
    expect(Object.keys(saved.review.members[0])).toEqual([
      "entry_id",
      "project_path",
      "placement",
      "source_retained",
      "volume_id",
      "content_version",
      "dependency_coverage",
      "source",
      "intended",
      "recorded_kind",
      "recorded_logical_bytes",
      "recorded_status",
      "recorded_hash_status",
    ]);
  });
  for (const action of [
    "edit",
    "membership",
    "path",
    "dismiss",
    "reload",
    "pagehide",
    "persisted navigation",
  ])
    test(`cannot export after ${action}`, async () => {
      await accept();
      if (action === "edit") input("folder", "Unreviewed");
      if (action === "membership") input("member-3", true);
      if (action === "path") input("path-0", "Unreviewed.blend");
      if (action === "dismiss") id("dismiss").click();
      if (action === "reload") {
        id("reload").click();
        await settle();
      }
      if (action === "pagehide") window.dispatchEvent(new PageTransitionEvent("pagehide"));
      if (action === "persisted navigation") {
        window.dispatchEvent(new PageTransitionEvent("pageshow", { persisted: true }));
        await settle();
      }
      expect(id("save").disabled).toBe(true);
      id("save").dispatchEvent(new Event("click"));
      expect(createURL).not.toHaveBeenCalled();
    });
  test("detects a control value change even without an input event", async () => {
    await accept();
    id("folder").value = "Unannounced change";
    id("save").click();
    expect(createURL).not.toHaveBeenCalled();
    expect(id("save").disabled).toBe(true);
    expect(id("review-content").children).toHaveLength(0);
  });
  test("pending, failed and late responses cannot export an old accepted result", async () => {
    await accept();
    const wait = deferred();
    fetchMock.mockReturnValueOnce(wait.promise);
    submit();
    expect(id("save").disabled).toBe(true);
    id("save").dispatchEvent(new Event("click"));
    expect(createURL).not.toHaveBeenCalled();
    input("folder", "Newer draft");
    wait.resolve(response(reviewed()));
    await settle();
    expect(id("save").disabled).toBe(true);
    fetchMock.mockResolvedValueOnce(response({ error: "Stale" }, 409));
    submit();
    await settle();
    expect(id("save").disabled).toBe(true);
    id("save").dispatchEvent(new Event("click"));
    expect(createURL).not.toHaveBeenCalled();
  });
  test("a late reference after a newer reload cannot enable saving", async () => {
    await accept();
    const old = deferred();
    fetchMock.mockReturnValueOnce(old.promise);
    id("reload").click();
    id("reload").click();
    await settle();
    old.resolve(response(fixture));
    await settle();
    expect(id("save").disabled).toBe(true);
    expect(createURL).not.toHaveBeenCalled();
  });
  test("repeated clicks create exact same report and revoke each URL once", async () => {
    await accept();
    id("save").click();
    id("save").click();
    expect(downloads).toHaveLength(2);
    expect(document.querySelectorAll("a[download]")).toHaveLength(0);
    expect(await readBlob(blobs[0])).toBe(await readBlob(blobs[1]));
    await settle();
    expect(revokeURL.mock.calls.map(([url]) => url).sort()).toEqual([
      "blob:synthetic-download-1",
      "blob:synthetic-download-2",
    ]);
    id("dismiss").click();
    expect(revokeURL).toHaveBeenCalledTimes(2);
  });
  test("editing immediately after activation releases its URL and prevents another export", async () => {
    await accept();
    id("save").click();
    input("folder", "Edited after click");
    expect(revokeURL).toHaveBeenCalledWith("blob:synthetic-download-1");
    await settle();
    expect(revokeURL).toHaveBeenCalledTimes(1);
    id("save").click();
    expect(downloads).toHaveLength(1);
  });
  test("page cleanup revokes an outstanding URL once", async () => {
    await accept();
    id("save").click();
    window.dispatchEvent(new PageTransitionEvent("pagehide"));
    expect(revokeURL).toHaveBeenCalledTimes(1);
    await settle();
    expect(revokeURL).toHaveBeenCalledTimes(1);
  });
  test("object URL creation failure retains the accepted review for retry", async () => {
    await accept();
    createURL.mockImplementationOnce(() => {
      throw new Error("Synthetic creation failure");
    });
    id("save").click();
    expect(id("save-status").textContent).toContain("could not be started");
    expect(id("save").disabled).toBe(false);
    expect(revokeURL).not.toHaveBeenCalled();
    await report();
    expect(downloads).toHaveLength(1);
  });
  test("activation failure removes the anchor and releases the URL", async () => {
    await accept();
    HTMLAnchorElement.prototype.click.mockImplementationOnce(() => {
      throw new Error("Synthetic activation failure");
    });
    id("save").click();
    expect(id("save-status").textContent).toContain("could not be started");
    expect(document.querySelectorAll("a[download]")).toHaveLength(0);
    expect(revokeURL).toHaveBeenCalledTimes(1);
    await report();
    expect(downloads).toHaveLength(1);
  });
  test("cleanup failure is reported and retried on page cleanup", async () => {
    await accept();
    revokeURL.mockImplementationOnce(() => {
      throw new Error("Synthetic cleanup failure");
    });
    id("save").click();
    await settle();
    expect(id("save-status").textContent).toContain("cleanup failed");
    window.dispatchEvent(new PageTransitionEvent("pagehide"));
    expect(revokeURL).toHaveBeenCalledTimes(2);
  });
  test("HTML-looking names remain JSON data and cannot alter the safe filename", async () => {
    const folder = '<img src=x onerror="alert(1)">';
    await accept(folder);
    const saved = await report();
    expect(saved.decision.destination_folder).toBe(folder);
    expect(downloads[0].filename).not.toContain("img");
    expect(document.querySelector("img")).toBeNull();
  });
  test("new successful intent replaces the export, never the older snapshot", async () => {
    await accept("First decision");
    const first = await report();
    await accept("Second decision");
    const second = await report();
    expect(first.decision.destination_folder).toBe("First decision");
    expect(second.decision.destination_folder).toBe("Second decision");
    expect(JSON.stringify(second)).not.toContain("First decision");
  });
  test("an edit during activation cannot revive save status or release a URL twice", async () => {
    await accept();
    HTMLAnchorElement.prototype.click.mockImplementationOnce(() =>
      input("folder", "Changed during activation")
    );
    id("save").click();
    await settle();
    expect(id("save-status").textContent).toContain("Review the current intent first");
    expect(id("save").disabled).toBe(true);
    expect(revokeURL).toHaveBeenCalledTimes(1);
  });
  test("page cleanup during a failed activation releases the URL only once", async () => {
    await accept();
    HTMLAnchorElement.prototype.click.mockImplementationOnce(() => {
      window.dispatchEvent(new PageTransitionEvent("pagehide"));
      throw new Error("Activation interrupted");
    });
    id("save").click();
    await settle();
    expect(revokeURL).toHaveBeenCalledTimes(1);
    expect(id("save").disabled).toBe(true);
  });
  test("Blob creation failure offers retry without a URL or accepted-state loss", async () => {
    await accept();
    jest.spyOn(window, "Blob").mockImplementationOnce(() => {
      throw new Error("Synthetic Blob failure");
    });
    id("save").click();
    expect(id("save-status").textContent).toContain("could not be started");
    expect(createURL).not.toHaveBeenCalled();
    expect(id("save").disabled).toBe(false);
    window.Blob.mockRestore();
    await report();
    expect(downloads).toHaveLength(1);
  });
  for (const control of ["folder", "root", "member", "path"])
    test(`silent ${control} changes during a pending review cannot be bound to an old report`, async () => {
      await accept();
      const wait = deferred();
      fetchMock.mockReturnValueOnce(wait.promise);
      submit();
      if (control === "folder") id("folder").value = "Silently newer intent";
      if (control === "root") id("root").value = fixture.roots[0].id;
      if (control === "member") id("member-3").checked = true;
      if (control === "path") id("path-0").value = "Silent/path.blend";
      wait.resolve(response(reviewed()));
      await settle();
      expect(id("save").disabled).toBe(true);
      expect(id("review-content").children).toHaveLength(0);
      id("save").dispatchEvent(new Event("click"));
      expect(createURL).not.toHaveBeenCalled();
    });
});

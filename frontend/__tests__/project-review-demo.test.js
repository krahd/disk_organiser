const fs = require("fs");
const path = require("path");
const { createDemo } = require("../project-review-demo");
const fixtures = require("./project-review-fixtures.json");

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
const reviewed = (name = "harbour-reference", folder = "Reviewed home") => {
  const value = copy(fixtures[name]);
  value.review.revision = 2;
  for (const change of value.review.proposed_changes)
    change.destination.relative_path = `${folder}/${change.member_id}`;
  return value;
};
let fetchMock;
let demo;
function input(id, value, event = "input") {
  const node = document.getElementById(id);
  if (node.type === "checkbox") node.checked = value;
  else node.value = value;
  node.dispatchEvent(new Event(event, { bubbles: true }));
}
function submit() {
  document
    .getElementById("decision-form")
    .dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
}
beforeEach(async () => {
  const html = fs.readFileSync(path.join(__dirname, "../project-review-demo.html"), "utf8");
  document.documentElement.innerHTML = html.replace(/<!doctype html>/i, "");
  fetchMock = jest.fn().mockResolvedValue(response(fixtures["harbour-reference"]));
  demo = createDemo(document, fetchMock);
  await demo.ready;
});

test("renders the permanent simulation boundary, suggested membership and dependencies", () => {
  expect(document.body.textContent).toContain(
    "Simulated project; no drives or providers connected"
  );
  expect(document.getElementById("member-edit").checked).toBe(true);
  expect(document.getElementById("member-extra").checked).toBe(false);
  expect(document.getElementById("members").textContent).toContain(
    "Depends on: Media/clip.mov, Notes/brief.txt"
  );
  expect(document.getElementById("fixture-date").textContent).toContain("2026-10-06T22:00:00Z");
  expect(document.getElementById("fixture-date").textContent).toContain("not today");
  expect(document.body.textContent).toContain("No rule blockers in this synthetic proposal");
  expect(document.body.textContent).toContain("Configuration only");
  expect(document.body.textContent).toContain("Fabricated content verification");
  expect(document.body.textContent).toContain("No execution authority");
});

test("only the allowlisted decision fields are submitted; server handles all review rules", async () => {
  input("member-extra", true);
  input("member-media", false);
  input("destination-volume", "shelf", "change");
  input("destination-folder", "My project");
  fetchMock.mockResolvedValueOnce(response(reviewed()));
  submit();
  await settle();
  const [url, options] = fetchMock.mock.calls[1];
  expect(url).toBe("/api/review");
  expect(options.method).toBe("POST");
  expect(options.credentials).toBe("omit");
  expect(options.redirect).toBe("error");
  expect(options.headers["X-Demo-Token"]).toBe("__DEMO_PROCESS_TOKEN__");
  expect(JSON.parse(options.body)).toEqual({
    scenario_id: "harbour-reference",
    expected_revision: 1,
    expected_digest: fixtures["harbour-reference"].reference_digest,
    member_ids: ["edit", "notes", "extra"],
    destination_volume_id: "shelf",
    destination_folder: "My project",
  });
  expect(document.getElementById("state-extra").textContent).toBe("Added");
  expect(document.getElementById("state-media").textContent).toBe("Removed");
  expect(document.activeElement.id).toBe("review-heading");
});

test("any edit removes the previously accepted review, without recomputing rules in JavaScript", () => {
  input("destination-folder", "Another home");
  expect(document.getElementById("review-content").children).toHaveLength(0);
  expect(document.getElementById("review-caption").textContent).toContain("Draft changed");
  expect(fetchMock).toHaveBeenCalledTimes(1);
});

test("dismiss restores the exact reference decision and focus", () => {
  input("member-notes", false);
  input("member-extra", true);
  input("destination-folder", "Unwanted");
  document.getElementById("dismiss").click();
  expect(document.getElementById("member-notes").checked).toBe(true);
  expect(document.getElementById("member-extra").checked).toBe(false);
  expect(document.getElementById("destination-folder").value).toBe("Client projects/Harbour");
  expect(document.getElementById("review-caption").textContent).toContain("Reference proposal");
  expect(document.activeElement.id).toBe("review-button");
  expect(fetchMock).toHaveBeenCalledTimes(1);
});

test("a late review cannot overwrite a newer edit", async () => {
  const wait = deferred();
  fetchMock.mockReturnValueOnce(wait.promise);
  submit();
  input("destination-folder", "Latest draft");
  wait.resolve(response(reviewed()));
  await settle();
  expect(document.getElementById("destination-folder").value).toBe("Latest draft");
  expect(document.getElementById("review-content").children).toHaveLength(0);
  expect(document.getElementById("status").textContent).toContain("Draft changed");
});

test("a late review cannot revive a dismissed proposal", async () => {
  const wait = deferred();
  fetchMock.mockReturnValueOnce(wait.promise);
  input("destination-folder", "Late proposal");
  submit();
  document.getElementById("dismiss").click();
  wait.resolve(response(reviewed("harbour-reference", "Late proposal")));
  await settle();
  expect(document.getElementById("review-caption").textContent).toContain("Reference proposal");
  expect(document.getElementById("review-content").textContent).not.toContain("Late proposal");
  expect(document.getElementById("status").textContent).toContain("dismissed");
});

test("a late error cannot replace a newer successful review", async () => {
  const old = deferred();
  fetchMock.mockReturnValueOnce(old.promise);
  submit();
  input("destination-folder", "New result");
  fetchMock.mockResolvedValueOnce(response(reviewed("harbour-reference", "New result")));
  submit();
  await settle();
  old.reject(new Error("Old failure"));
  await settle();
  expect(document.getElementById("review-content").textContent).toContain("New result");
  expect(document.getElementById("error").hidden).toBe(true);
});

test("a late review cannot replace the newer scenario", async () => {
  const wait = deferred();
  fetchMock.mockReturnValueOnce(wait.promise);
  submit();
  fetchMock.mockResolvedValueOnce(response(fixtures["harbour-uncertain"]));
  input("scenario", "harbour-uncertain", "change");
  await settle();
  wait.resolve(response(reviewed()));
  await settle();
  expect(document.body.textContent).toContain("A member is a placeholder");
  expect(document.body.textContent).toContain("Sample-scoped exercise");
  expect(document.body.textContent).toContain("Required including reserveUnknown");
});

test("overlapping scenario loads accept only the newest choice", async () => {
  const first = deferred();
  fetchMock.mockReturnValueOnce(first.promise);
  input("scenario", "harbour-uncertain", "change");
  fetchMock.mockResolvedValueOnce(response(fixtures["harbour-reference"]));
  input("scenario", "harbour-reference", "change");
  await settle();
  first.resolve(response(fixtures["harbour-uncertain"]));
  await settle();
  expect(document.body.textContent).not.toContain("A member is a placeholder");
  expect(document.getElementById("decision-fields").disabled).toBe(false);
});

test("repeated submits produce at most one pending request", async () => {
  const wait = deferred();
  fetchMock.mockReturnValueOnce(wait.promise);
  submit();
  submit();
  submit();
  expect(fetchMock).toHaveBeenCalledTimes(2);
  wait.resolve(response(reviewed()));
  await settle();
  expect(document.getElementById("review-button").disabled).toBe(false);
});

test("failed review retains the editable draft and clears stale results", async () => {
  input("destination-folder", "Retry me");
  fetchMock.mockRejectedValueOnce(new Error("Disconnected"));
  submit();
  await settle();
  expect(document.getElementById("error").textContent).toBe("Disconnected");
  expect(document.getElementById("destination-folder").value).toBe("Retry me");
  expect(document.getElementById("review-content").children).toHaveLength(0);
  expect(document.getElementById("review-button").disabled).toBe(false);
});

test("stale server reference asks for reload without silently retrying", async () => {
  fetchMock.mockResolvedValueOnce(response({ error: "stale" }, 409));
  submit();
  await settle();
  expect(document.getElementById("error").textContent).toContain("reference changed");
  expect(fetchMock).toHaveBeenCalledTimes(2);
});

test("unsafe response capabilities fail closed", async () => {
  const value = reviewed();
  value.review.executable = true;
  fetchMock.mockResolvedValueOnce(response(value));
  submit();
  await settle();
  expect(document.getElementById("error").textContent).toContain("Unexpected demo response");
  expect(document.getElementById("review-content").children).toHaveLength(0);
});

test("mismatched review identities are rejected", async () => {
  const value = reviewed();
  value.reference_digest = "0".repeat(64);
  fetchMock.mockResolvedValueOnce(response(value));
  submit();
  await settle();
  expect(document.getElementById("error").textContent).toContain("Unexpected review reference");
});

test("response paths, labels, evidence and errors are never interpreted as HTML or URLs", async () => {
  const attack = '<img src="https://example.invalid" onerror="window.attacked=true">';
  const value = reviewed("harbour-reference", attack);
  value.review.limitations.push(attack);
  value.review.protection.restore_alerts.push({
    target_id: attack,
    snapshot_id: attack,
    at: attack,
    reasons: [attack],
    required_check: "bytes",
    member_ids: ["edit"],
    event_ids: [attack],
  });
  fetchMock.mockResolvedValueOnce(response(value));
  submit();
  await settle();
  expect(document.querySelector("img")).toBeNull();
  expect(document.getElementById("review-content").textContent).toContain(attack);
  expect(window.attacked).toBeUndefined();
  fetchMock.mockResolvedValueOnce(response({ error: attack }, 400));
  submit();
  await settle();
  expect(document.getElementById("error").textContent).toBe(attack);
  expect(document.querySelector("img")).toBeNull();
});

test("reload discards the draft without browser storage", async () => {
  const storage = jest.spyOn(Storage.prototype, "setItem");
  input("destination-folder", "Transient draft");
  document.getElementById("reload").click();
  await settle();
  expect(document.getElementById("destination-folder").value).toBe("Client projects/Harbour");
  expect(storage).not.toHaveBeenCalled();
  storage.mockRestore();
});

test("the UI has no file, execution, restore, upload or evidence-editing control", () => {
  expect(document.querySelector("input[type=file]")).toBeNull();
  expect(Array.from(document.querySelectorAll("input")).map((node) => node.id)).toEqual([
    "member-edit",
    "member-media",
    "member-notes",
    "member-extra",
    "destination-folder",
  ]);
  const buttons = Array.from(document.querySelectorAll("button")).map((node) => node.textContent);
  expect(buttons).toEqual(["Reload scenario", "Review proposed layout", "Dismiss proposal"]);
});

test("successive edit and review cycles all use the immutable fixture base", async () => {
  for (const folder of ["First reviewed home", "Second reviewed home", "Third reviewed home"]) {
    input("destination-folder", folder);
    fetchMock.mockResolvedValueOnce(response(reviewed("harbour-reference", folder)));
    submit();
    await settle();
    expect(document.getElementById("review-content").textContent).toContain(folder);
    const payload = JSON.parse(fetchMock.mock.calls[fetchMock.mock.calls.length - 1][1].body);
    expect(payload.expected_revision).toBe(1);
    expect(payload.expected_digest).toBe(fixtures["harbour-reference"].reference_digest);
  }
  expect(fetchMock).toHaveBeenCalledTimes(4);
});

test("dismissal also invalidates a late error", async () => {
  const wait = deferred();
  fetchMock.mockReturnValueOnce(wait.promise);
  submit();
  document.getElementById("dismiss").click();
  wait.reject(new Error("Failure from dismissed request"));
  await settle();
  expect(document.getElementById("error").hidden).toBe(true);
  expect(document.getElementById("status").textContent).toContain("dismissed");
  expect(document.getElementById("review-caption").textContent).toContain("Reference proposal");
});

test("renders declared keep-current without calling unchanged members copies", async () => {
  const value = reviewed();
  for (const change of value.review.proposed_changes) {
    change.proposal = "keep_current";
    change.destination = {
      volume_id: change.source.volume_id,
      relative_path: change.source.relative_path,
    };
  }
  Object.assign(value.review.capacity, {
    known_logical_copy_bytes: 0,
    required_destination_bytes: 0,
    reserve_bytes: 0,
  });
  fetchMock.mockResolvedValueOnce(response(value));
  submit();
  await settle();
  const content = document.getElementById("review-content");
  expect(content.textContent).toContain("Keep current: no copies are proposed");
  expect(content.textContent).toContain("No additional copy space or reserve is required");
  expect(content.querySelectorAll(".comparison strong").length).toBe(6);
  expect(
    [...content.querySelectorAll(".comparison strong")].filter((node) =>
      node.textContent.startsWith("KEEP CURRENT")
    )
  ).toHaveLength(3);
  expect(content.textContent).not.toContain("PROPOSED ·");
  expect(content.textContent).toContain("Execution: false. Authority: null");
});

test("renders mixed kept and copied paths with scoped capacity wording", async () => {
  const value = reviewed();
  const change = value.review.proposed_changes[0];
  change.proposal = "keep_current";
  change.destination = {
    volume_id: change.source.volume_id,
    relative_path: change.source.relative_path,
  };
  fetchMock.mockResolvedValueOnce(response(value));
  submit();
  await settle();
  const text = document.getElementById("review-content").textContent;
  expect(text).toContain("KEEP CURRENT ·");
  expect(text).toContain("PROPOSED ·");
  expect(text).toContain("Logical data counts only proposed copies");
  expect(text).not.toContain("Keep current: no copies are proposed");
});

test("uncertain current locations remain unresolved with unknown required capacity", async () => {
  const value = reviewed();
  value.review.proposed_changes[0].proposal = "unresolved_current_location";
  value.review.capacity.required_destination_bytes = null;
  value.review.blockers.push({ code: "current_location_identity_unproven", member_ids: ["edit"] });
  fetchMock.mockResolvedValueOnce(response(value));
  submit();
  await settle();
  const content = document.getElementById("review-content");
  expect(content.textContent).toContain("UNRESOLVED ·");
  expect(content.textContent).toContain("declared identity is incomplete or uncertain");
  expect(content.textContent).toContain("no copy or no-op established");
  const metric = [...content.querySelectorAll(".metric")].find((node) =>
    node.textContent.includes("Required including reserve")
  );
  expect(metric.textContent).toContain("Unknown");
  expect(content.textContent).not.toContain("Keep current: no copies are proposed");
});

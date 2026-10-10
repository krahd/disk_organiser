/* Fixed data-only protocol for a trusted bundled page. No native invocation channel. */
(function (root, factory) {
  "use strict";
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  else Object.defineProperty(root, "NativeLibraryProtocol", { value: api });
})(typeof globalThis === "object" ? globalThis : this, function () {
  "use strict";
  const VERSION = "catalogue-data-bridge/v2",
    UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/,
    DECIMAL = /^(0|[1-9][0-9]{0,15})$/,
    MAX = 9007199254740991n,
    BYTES = 4194304,
    LIMIT = 128;
  const fail = () => {
    throw Error("Native library operation is unavailable.");
  };
  function integer(text, maximum = MAX) {
    if (typeof text !== "string" || !DECIMAL.test(text) || BigInt(text) > maximum) fail();
    return text;
  }
  function uuid(text) {
    if (typeof text !== "string" || !UUID.test(text)) fail();
    return text;
  }
  function exact(value, keys) {
    if (!value || typeof value !== "object" || Array.isArray(value)) fail();
    const descriptors = Object.getOwnPropertyDescriptors(value),
      names = Reflect.ownKeys(descriptors);
    if (
      names.length !== keys.length ||
      names.some(
        (k) =>
          typeof k !== "string" ||
          !keys.includes(k) ||
          !("value" in descriptors[k]) ||
          typeof descriptors[k].value !== "string"
      )
    )
      fail();
    return value;
  }
  function bounded(text) {
    if (
      typeof text !== "string" ||
      !text.length ||
      text.length > BYTES ||
      text.charCodeAt(0) === 0xfeff
    )
      fail();
    // TextEncoder replaces lone surrogates: reject them before encoding instead.
    for (let i = 0; i < text.length; i++) {
      const c = text.charCodeAt(i);
      if (c >= 0xd800 && c <= 0xdbff) {
        const next = text.charCodeAt(++i);
        if (!(next >= 0xdc00 && next <= 0xdfff)) fail();
      } else if (c >= 0xdc00 && c <= 0xdfff) fail();
    }
    if (new TextEncoder().encode(text).length > BYTES) fail();
    return text;
  }
  function create(port) {
    const records = new Map();
    let fence = null,
      blocked = false;
    function request(value, keys = []) {
      exact(value, ["version", "session", "operation", ...keys]);
      if (value.version !== VERSION) fail();
      uuid(value.session);
      uuid(value.operation);
      port.check(value.version, value.session);
      for (const [key, text] of Object.entries(value))
        if (key !== "text" && (key.length > 24 || new TextEncoder().encode(text).length > 64))
          fail();
      return value;
    }
    function reply(r, values) {
      const result = { version: VERSION, session: r.session, operation: r.operation, ...values };
      const metadata = Object.entries(result).filter(([key]) => key !== "text");
      if (
        metadata.length > 12 ||
        metadata.some(
          ([key, value]) =>
            typeof value !== "string" ||
            key.length > 24 ||
            new TextEncoder().encode(value).length > 64
        ) ||
        metadata.reduce((n, [k, v]) => n + new TextEncoder().encode(k + v).length, 0) > 1024
      )
        fail();
      return Object.freeze(result);
    }
    function state() {
      const s = port.state();
      integer(s.revision);
      integer(s.epoch);
      integer(s.selections, 2000n);
      if (
        !["clean", "dirty"].includes(s.dirty) ||
        !["none", "label-edit", "snapshot-review", "catalogue-review", "other-edit"].includes(
          s.dialog
        ) ||
        !["none", "uncommitted"].includes(s.draft)
      )
        fail();
      return s;
    }
    function reserve(r, kind) {
      if (records.has(r.operation) || records.size >= LIMIT || blocked) fail();
      const item = { kind, request: r, terminal: false };
      records.set(r.operation, item);
      return item;
    }
    function record(r, kind) {
      const item = records.get(r.operation);
      if (!item || item.kind !== kind || item.request.session !== r.session) fail();
      return item;
    }
    function loss(r, value) {
      const s = state();
      return reply(r, {
        revision: s.revision,
        epoch: s.epoch,
        dirty: s.dirty,
        selections: s.selections,
        dialog: s.dialog,
        draft: s.draft,
        state: value,
      });
    }
    function requireStorage() {
      if (port.mode() !== "owned-storage" || blocked) fail();
    }
    function requireIdle(s) {
      if (s.busy || s.dialog !== "none" || s.draft !== "none") fail();
    }
    function held(r, kind) {
      const item = record(r, kind);
      if (fence !== item || item.terminal || blocked) fail();
      return item;
    }
    function release(item) {
      if (fence === item) {
        port.fence(false);
        fence = null;
      }
      item.terminal = true;
    }
    function preparedState(item) {
      const s = state();
      if (s.revision !== item.revision || s.epoch !== item.epoch) fail();
      return s;
    }
    function saved(r, apply) {
      const item = record(r, "save"),
        s = state();
      if (apply && r.revision !== item.revision) fail();
      if (!item.applied && apply) {
        if (s.revision === item.revision) port.clean(item.revision);
        item.applied = true;
        item.terminal = true;
      }
      return reply(r, {
        revision: item.revision,
        current_revision: state().revision,
        state: !item.applied
          ? "not-applied"
          : state().revision === item.revision
          ? "current-saved"
          : "earlier-saved",
      });
    }
    function replacement(r, item) {
      if (item.committed) return reply(r, item.committed);
      const s = state();
      return reply(r, {
        candidate: r.candidate,
        revision: s.revision,
        epoch: s.epoch,
        state: "not-committed",
        view: blocked ? "blocked" : "ready",
      });
    }
    return Object.freeze({
      get fenced() {
        return fence !== null;
      },
      requireMutable() {
        if (fence || blocked) fail();
      },
      status(value) {
        const r = request(value);
        if (records.get(r.operation)?.kind === "close") held(r, "close");
        return loss(r, blocked || state().busy || fence ? "busy" : "idle");
      },
      exportCatalogue(value) {
        const r = request(value, ["fence"]);
        requireStorage();
        const s = state();
        requireIdle(s);
        if (r.fence) {
          uuid(r.fence);
          if (!fence || fence.kind !== "close" || fence.request.operation !== r.fence) fail();
        } else if (fence) fail();
        const text = bounded(port.export());
        const item = reserve(r, "save");
        item.revision = s.revision;
        item.applied = false;
        return reply(r, { revision: s.revision, epoch: s.epoch, state: "exported", text });
      },
      acknowledgeSaved(value) {
        const r = request(value, ["revision"]);
        integer(r.revision);
        requireStorage();
        return saved(r, true);
      },
      savedResult(value) {
        const r = request(value);
        requireStorage();
        return saved(r, false);
      },
      prepareClose(value) {
        const r = request(value);
        if (fence || state().busy) fail();
        const item = reserve(r, "close");
        fence = item;
        try {
          port.fence(true);
          return loss(r, "fenced");
        } catch (error) {
          release(item);
          throw error;
        }
      },
      releaseClose(value) {
        const r = request(value),
          item = record(r, "close");
        if (!item.terminal) {
          held(r, "close");
          release(item);
        }
        return reply(r, { state: "released" });
      },
      prepareOpen(value) {
        const r = request(value);
        requireStorage();
        const s = state();
        requireIdle(s);
        if (fence) fail();
        const item = reserve(r, "open");
        item.revision = s.revision;
        item.epoch = s.epoch;
        item.candidates = new Set();
        item.candidate = null;
        fence = item;
        try {
          port.fence(true);
          return loss(r, "fenced");
        } catch (error) {
          release(item);
          throw error;
        }
      },
      prepareReplacement(value) {
        const r = request(value, ["candidate", "revision", "epoch", "text"]);
        requireStorage();
        uuid(r.candidate);
        integer(r.revision);
        integer(r.epoch);
        const item = held(r, "open");
        preparedState(item);
        if (
          r.revision !== item.revision ||
          r.epoch !== item.epoch ||
          item.candidate ||
          item.candidates.has(r.candidate) ||
          item.candidates.size >= LIMIT
        )
          fail();
        const parsed = port.parse(bounded(r.text));
        item.candidates.add(r.candidate);
        item.candidate = { id: r.candidate, parsed };
        return reply(r, {
          candidate: r.candidate,
          revision: r.revision,
          epoch: r.epoch,
          state: "prepared",
        });
      },
      retireCandidate(value) {
        const r = request(value, ["candidate"]);
        uuid(r.candidate);
        const item = record(r, "open");
        if (item.committed) {
          if (item.committed.candidate !== r.candidate) fail();
          return reply(r, item.committed);
        }
        held(r, "open");
        if (!item.candidates.has(r.candidate)) fail();
        if (item.candidate?.id === r.candidate) item.candidate = null;
        return reply(r, { candidate: r.candidate, state: "retired" });
      },
      commitReplacement(value) {
        const r = request(value, ["candidate", "revision", "epoch"]);
        uuid(r.candidate);
        integer(r.revision);
        integer(r.epoch);
        const item = record(r, "open");
        if (item.committed) {
          if (
            item.committed.candidate !== r.candidate ||
            item.revision !== r.revision ||
            item.epoch !== r.epoch
          )
            fail();
          return reply(r, item.committed);
        }
        held(r, "open");
        preparedState(item);
        if (
          item.candidate?.id !== r.candidate ||
          r.revision !== item.revision ||
          r.epoch !== item.epoch
        )
          fail();
        if (BigInt(r.revision) >= MAX || BigInt(r.epoch) >= MAX) fail();
        // Logical commit must be a nonthrowing assignment after all preparation.
        // Record its fact before rendering; rendering failure is not rollback.
        port.commit(item.candidate.parsed);
        const s = state();
        item.committed = {
          candidate: r.candidate,
          revision: s.revision,
          epoch: s.epoch,
          state: "committed",
          view: "ready",
        };
        item.candidate = null;
        try {
          port.render();
          release(item);
        } catch {
          blocked = true;
          item.committed.view = "blocked";
        }
        return reply(r, item.committed);
      },
      replacementResult(value) {
        const r = request(value, ["candidate"]);
        uuid(r.candidate);
        const item = record(r, "open");
        if (
          !item.candidates.has(r.candidate) ||
          (item.committed && item.committed.candidate !== r.candidate)
        )
          fail();
        return replacement(r, item);
      },
      cancelOpen(value) {
        const r = request(value),
          item = record(r, "open");
        if (item.committed) return reply(r, item.committed);
        if (!item.terminal) {
          held(r, "open");
          item.candidate = null;
          release(item);
        }
        return reply(r, { state: "cancelled" });
      },
    });
  }
  return Object.freeze({ VERSION, BYTES, LIMIT, create });
});

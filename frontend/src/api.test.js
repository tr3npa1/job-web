import { test, afterEach } from "node:test";
import assert from "node:assert/strict";
import { api } from "./api.js";
const originalFetch = globalThis.fetch;
afterEach(() => {
  globalThis.fetch = originalFetch;
});

test("sends authenticated JSON mutations", async () => {
  globalThis.fetch = async (url, options) => {
    assert.equal(url, "/api/jobs");
    assert.equal(options.credentials, "same-origin");
    assert.equal(options.headers["X-Requested-With"], "job-web");
    assert.deepEqual(JSON.parse(options.body), { JobRole: "Developer" });
    return new Response(JSON.stringify({ id: 1 }), { status: 201 });
  };
  assert.deepEqual(await api("/jobs", "POST", { JobRole: "Developer" }), {
    id: 1,
  });
});

test("preserves authorization status", async () => {
  globalThis.fetch = async () =>
    new Response(JSON.stringify({ error: "Please sign in." }), { status: 401 });
  await assert.rejects(
    api("/me"),
    (error) => error.status === 401 && error.message === "Please sign in.",
  );
});

test("rejects invalid JSON even on a successful HTTP response", async () => {
  globalThis.fetch = async () => new Response("<html>Proxy error</html>");
  await assert.rejects(api("/jobs"), /invalid response/);
});

test("rejects unexpected JSON shapes", async () => {
  globalThis.fetch = async () => new Response("null");
  await assert.rejects(api("/jobs"), /invalid response/);
});

test("reports connection failures", async () => {
  globalThis.fetch = async () => {
    throw new TypeError("Network error");
  };
  await assert.rejects(api("/jobs"), /Cannot reach/);
});

test("reports aborted requests", async () => {
  globalThis.fetch = async () => {
    throw new DOMException("Aborted", "AbortError");
  };
  await assert.rejects(api("/jobs"), /timed out/);
});

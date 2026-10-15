import test from "node:test";
import assert from "node:assert/strict";
import { request } from "./api.js";

test("sends JSON without losing a zero seed", async () => {
  let captured;
  globalThis.fetch = async (url, options) => {
    captured = { url, ...options };
    return { ok: true, json: async () => ({ job_id: "r", status: "QUEUED" }) };
  };
  assert.equal(
    (await request("/runs/launch", "POST", { run_id: "r", seed: 0 })).status,
    "QUEUED",
  );
  assert.equal(captured.url, "/api/v1/runs/launch");
  assert.equal(JSON.parse(captured.body).seed, 0);
});
test("preserves server validation details", async () => {
  globalThis.fetch = async () => ({
    ok: false,
    status: 422,
    json: async () => ({
      detail: [{ loc: ["body", "rationale"], msg: "Field required" }],
    }),
  });
  await assert.rejects(
    request("/experiments/decisions", "POST", {}),
    /rationale: Field required/,
  );
});
test("explains proxy failures and registration conflicts", async () => {
  globalThis.fetch = async () => ({
    ok: false,
    status: 500,
    json: async () => {
      throw new Error("not json");
    },
  });
  await assert.rejects(request("/system/info"), /Backend is unavailable/);
  globalThis.fetch = async () => ({
    ok: false,
    status: 409,
    json: async () => ({ detail: "Model name/version already exists" }),
  });
  await assert.rejects(
    request("/registry/register", "POST", {}),
    /version already exists/,
  );
});
test("uploads multipart images with browser-generated boundary", async () => {
  let captured;
  const body = new FormData();
  body.append("file", new Blob(["png"]), "test.png");
  globalThis.fetch = async (url, options) => {
    captured = options;
    return {
      ok: true,
      json: async () => ({ model_id: "model_1", version: "v1.0.0" }),
    };
  };
  const result = await request(
    "/inference/predict?model_id=model_1",
    "POST",
    body,
  );
  assert.equal(captured.headers, undefined);
  assert.equal(captured.body, body);
  assert.equal(result.model_id, "model_1");
});

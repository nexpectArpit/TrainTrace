const BASE = "/api/v1";
export async function request(path, method = "GET", body) {
  const response = await fetch(BASE + path, {
    method,
    headers:
      body instanceof FormData
        ? undefined
        : { "Content-Type": "application/json" },
    body:
      body === undefined
        ? undefined
        : body instanceof FormData
          ? body
          : JSON.stringify(body),
  });
  if (!response.ok) {
    let error;
    try {
      error = await response.json();
    } catch {
      error = { detail: "Backend is unavailable. Check the API service." };
    }
    const detail = Array.isArray(error.detail)
      ? error.detail
          .map((e) => `${e.loc?.slice(1).join(".")}: ${e.msg}`)
          .join("; ")
      : error.detail;
    throw new Error(detail || `Request failed (${response.status})`);
  }
  return response.json();
}

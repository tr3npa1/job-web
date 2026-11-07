export async function api(path, method = "GET", body = {}) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 15000);
  try {
    let response;
    try {
      response = await fetch(`/api${path}`, {
        method,
        signal: controller.signal,
        credentials: "same-origin",
        headers:
          method === "GET"
            ? {}
            : {
                "Content-Type": "application/json",
                "X-Requested-With": "job-web",
              },
        ...(method === "GET" ? {} : { body: JSON.stringify(body) }),
      });
    } catch (error) {
      if (error.name === "AbortError")
        throw new Error("The request timed out. Please try again.");
      throw new Error(
        "Cannot reach the server. Check your connection and try again.",
      );
    }
    let data;
    try {
      data = await response.json();
    } catch {
      throw new Error(
        "The server returned an invalid response. Please try again.",
      );
    }
    if (!response.ok) {
      const error = new Error(data?.error || "Request failed.");
      error.status = response.status;
      throw error;
    }
    if (!data || typeof data !== "object" || Array.isArray(data)) {
      throw new Error(
        "The server returned an invalid response. Please try again.",
      );
    }
    return data;
  } finally {
    clearTimeout(timeout);
  }
}

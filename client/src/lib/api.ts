async function apiFetch(path: string, options?: RequestInit) {
  const res = await fetch(`/api${path}`, {
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: res.statusText }));
    throw new Error(err.error || "Request failed");
  }
  return res.json();
}

export const api = {
  get: (path: string) => apiFetch(path),
  post: (path: string, body: any) => apiFetch(path, { method: "POST", body: JSON.stringify(body) }),
  put: (path: string, body: any) => apiFetch(path, { method: "PUT", body: JSON.stringify(body) }),
  patch: (path: string, body?: any) => apiFetch(path, { method: "PATCH", body: body ? JSON.stringify(body) : undefined }),
  del: (path: string) => apiFetch(path, { method: "DELETE" }),
  postForm: (path: string, formData: FormData) => fetch(`/api${path}`, {
    method: "POST", body: formData, credentials: "include",
  }).then(async res => {
    if (!res.ok) throw new Error((await res.json().catch(() => ({}))).error || res.statusText);
    return res.json();
  }),
  putForm: (path: string, formData: FormData) => fetch(`/api${path}`, {
    method: "PUT", body: formData, credentials: "include",
  }).then(async res => {
    if (!res.ok) throw new Error((await res.json().catch(() => ({}))).error || res.statusText);
    return res.json();
  }),
};

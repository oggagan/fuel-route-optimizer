const BASE = import.meta.env.VITE_API_BASE || "";

export async function planRoute(start, finish) {
  const res = await fetch(`${BASE}/api/route`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ start, finish }),
  });
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.error || `Request failed (${res.status})`);
  }
  return data;
}

export const config = { runtime: 'edge' };

// Serve pre-computed geo markers from public/data/geo_markers.json.
export default async function handler(req: Request): Promise<Response> {
  const origin = new URL(req.url).origin;
  try {
    const res = await fetch(`${origin}/data/geo_markers.json`, {
      signal: AbortSignal.timeout(3000),
    });
    if (!res.ok) return Response.json({ markers: [], total: 0 });
    const data = await res.json();
    return Response.json(data);
  } catch {
    return Response.json({ markers: [], total: 0 });
  }
}

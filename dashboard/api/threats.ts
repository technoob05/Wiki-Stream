export const config = { runtime: 'edge' };

// In production: serve the pre-built static intelligence data from public/data/.
// In local dev this endpoint is handled by the Vite plugin (api.ts) and this
// file is never invoked.
export default async function handler(req: Request): Promise<Response> {
  const origin = new URL(req.url).origin;
  try {
    const res = await fetch(`${origin}/data/threats.json`, {
      signal: AbortSignal.timeout(3000),
    });
    if (!res.ok) return Response.json({ detail: 'No intelligence data available.' }, { status: 404 });
    const data = await res.json();
    return Response.json(data);
  } catch {
    return Response.json({ detail: 'No intelligence data available.' }, { status: 404 });
  }
}

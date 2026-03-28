export const config = { runtime: 'edge' };

// Serve pre-bundled forensic report from public/data/report.md
export default async function handler(req: Request): Promise<Response> {
  const origin = new URL(req.url).origin;
  try {
    const res = await fetch(`${origin}/data/report.md`, { signal: AbortSignal.timeout(3000) });
    if (!res.ok) return Response.json({ detail: 'Report not available.' }, { status: 404 });
    const content = await res.text();
    return Response.json({ content });
  } catch {
    return Response.json({ detail: 'Report not available.' }, { status: 404 });
  }
}

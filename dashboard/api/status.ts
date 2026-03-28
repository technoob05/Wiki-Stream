export const config = { runtime: 'edge' };

// Determine has_reports by checking if the bundled threats.json exists and has data.
export default async function handler(req: Request): Promise<Response> {
  const origin = new URL(req.url).origin;
  try {
    const res = await fetch(`${origin}/data/threats.json`, { signal: AbortSignal.timeout(3000) });
    if (!res.ok) return Response.json({ status: 'online', has_reports: false, last_updated: null });
    const data = await res.json() as { timestamp?: string; total?: number };
    const lastUpdated = data.timestamp ? new Date(data.timestamp).getTime() / 1000 : null;
    return Response.json({ status: 'online', has_reports: (data.total ?? 0) > 0, last_updated: lastUpdated });
  } catch {
    return Response.json({ status: 'online', has_reports: false, last_updated: null });
  }
}

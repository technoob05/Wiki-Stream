export const config = { runtime: 'edge' };

export default async function handler(): Promise<Response> {
  try {
    const r = await fetch('https://api.wheretheiss.at/v1/satellites/25544', {
      headers: { 'User-Agent': 'WikiStream/2.0 (educational)' },
      signal: AbortSignal.timeout(5000),
    });
    if (!r.ok) return Response.json({ detail: 'ISS unavailable' }, { status: 503 });
    const data = await r.json() as Record<string, unknown>;
    return Response.json({
      lat: data.latitude, lon: data.longitude,
      altitude: data.altitude, velocity: data.velocity,
      visibility: data.visibility, timestamp: data.timestamp,
    });
  } catch {
    return Response.json({ detail: 'ISS unavailable' }, { status: 503 });
  }
}

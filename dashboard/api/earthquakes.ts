export const config = { runtime: 'edge' };

export default async function handler(): Promise<Response> {
  try {
    const r = await fetch(
      'https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/significant_month.geojson',
      { signal: AbortSignal.timeout(8000) }
    );
    if (!r.ok) return Response.json({ detail: 'Earthquake data unavailable' }, { status: 503 });
    const data = await r.json() as { features: any[] };
    const quakes = (data.features || [])
      .map((f: any) => ({
        lat: f.geometry.coordinates[1],
        lon: f.geometry.coordinates[0],
        depth: f.geometry.coordinates[2],
        magnitude: f.properties.mag,
        place: f.properties.place,
        time: f.properties.time,
        url: f.properties.url,
      }))
      .filter((q: { magnitude: number | null }) => q.magnitude != null);
    return Response.json({ quakes, total: quakes.length });
  } catch {
    return Response.json({ detail: 'Earthquake data unavailable' }, { status: 503 });
  }
}

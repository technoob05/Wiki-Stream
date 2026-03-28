export const config = { runtime: 'edge' };

export default async function handler(req: Request): Promise<Response> {
  const url = new URL(req.url);
  const lat = parseFloat(url.searchParams.get('lat') ?? '');
  const lon = parseFloat(url.searchParams.get('lon') ?? '');
  if (isNaN(lat) || isNaN(lon)) {
    return Response.json({ detail: 'lat and lon required' }, { status: 400 });
  }

  const [nominatim, weather, nearby] = await Promise.allSettled([
    fetch(
      `https://nominatim.openstreetmap.org/reverse?lat=${lat.toFixed(5)}&lon=${lon.toFixed(5)}&format=json&zoom=10`,
      { headers: { 'User-Agent': 'WikiStream/2.0 (educational)' }, signal: AbortSignal.timeout(5000) }
    ),
    fetch(
      `https://api.open-meteo.com/v1/forecast?latitude=${lat.toFixed(4)}&longitude=${lon.toFixed(4)}&current_weather=true&timezone=auto`,
      { signal: AbortSignal.timeout(5000) }
    ),
    fetch(
      `https://en.wikipedia.org/w/api.php?action=query&list=geosearch&gscoord=${lat.toFixed(4)}|${lon.toFixed(4)}&gsradius=50000&gslimit=6&format=json`,
      { signal: AbortSignal.timeout(5000) }
    ),
  ]);

  const result: Record<string, unknown> = { lat, lon };

  if (nominatim.status === 'fulfilled' && nominatim.value.ok) {
    try {
      const d = await nominatim.value.json() as any;
      if (d?.address) {
        const a = d.address;
        result.place = a.city || a.town || a.village || a.county || a.state
          || (d.display_name as string | undefined)?.split(',')[0] || null;
        result.country = a.country ?? null;
        result.countryCode = (a.country_code as string | undefined)?.toUpperCase() ?? null;
        result.displayName = d.display_name ?? null;
      }
    } catch { /* ignore */ }
  }

  if (weather.status === 'fulfilled' && weather.value.ok) {
    try {
      const d = await weather.value.json() as any;
      if (d?.current_weather) {
        result.weather = {
          temp: Math.round(d.current_weather.temperature),
          windspeed: Math.round(d.current_weather.windspeed),
          weathercode: d.current_weather.weathercode,
        };
      }
    } catch { /* ignore */ }
  }

  if (nearby.status === 'fulfilled' && nearby.value.ok) {
    try {
      const d = await nearby.value.json() as any;
      if (d?.query?.geosearch?.length) {
        result.nearbyArticles = (d.query.geosearch as any[]).map((a: any) => ({
          title: a.title, lat: a.lat, lon: a.lon, dist: Math.round(a.dist),
        }));
      }
    } catch { /* ignore */ }
  }

  return Response.json(result);
}

export const config = { runtime: 'edge' };

export default async function handler(req: Request): Promise<Response> {
  const url = new URL(req.url);
  const title = url.searchParams.get('title');
  if (!title) return Response.json({ detail: 'title required' }, { status: 400 });

  try {
    const r = await fetch(
      `https://en.wikipedia.org/api/rest_v1/page/summary/${encodeURIComponent(title)}`,
      { signal: AbortSignal.timeout(5000) }
    );
    const data = await r.json() as any;
    if (!r.ok || (data.type as string | undefined)?.includes('not_found') || data.title === 'Not found.') {
      return Response.json({ detail: 'Article not found' }, { status: 404 });
    }
    return Response.json({
      title: data.title,
      extract: data.extract,
      thumbnail: data.thumbnail?.source ?? null,
      url: data.content_urls?.desktop?.page
        ?? `https://en.wikipedia.org/wiki/${encodeURIComponent(title)}`,
      coordinates: data.coordinates ?? null,
      description: data.description ?? null,
    });
  } catch {
    return Response.json({ detail: 'Service unavailable' }, { status: 503 });
  }
}

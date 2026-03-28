export const config = { runtime: 'edge' };

export default async function handler(req: Request): Promise<Response> {
  const url = new URL(req.url);
  const user = url.searchParams.get('user');
  const title = url.searchParams.get('title');

  if (!user || !title) {
    return Response.json({ detail: 'user and title required' }, { status: 400 });
  }

  const origin = url.origin;
  try {
    const res = await fetch(`${origin}/data/edit_details.json`, {
      signal: AbortSignal.timeout(4000),
    });
    if (!res.ok) {
      return Response.json({ detail: 'Edit detail data not available.' }, { status: 404 });
    }
    const data: Record<string, unknown> = await res.json();
    const key = `${user}::${title}`;
    const detail = data[key];
    if (!detail) {
      return Response.json({ detail: 'Edit forensic data not found.' }, { status: 404 });
    }
    return Response.json(detail);
  } catch {
    return Response.json({ detail: 'Edit detail data not available.' }, { status: 404 });
  }
}

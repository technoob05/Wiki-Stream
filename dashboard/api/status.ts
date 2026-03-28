export const config = { runtime: 'edge' };

// In production (Vercel), there are no local intelligence reports.
// Return an online-but-empty state so the UI shows its "no data" screen.
export default function handler(): Response {
  return Response.json({ status: 'online', has_reports: false, last_updated: null });
}

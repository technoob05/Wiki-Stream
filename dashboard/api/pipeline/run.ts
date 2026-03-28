export const config = { runtime: 'edge' };

// Pipeline requires a local Python environment — not available in cloud deployments.
export default function handler(): Response {
  return Response.json(
    { message: 'Pipeline is not available in cloud deployment. Run `python experiments/00_pipeline_manager.py` locally, then re-deploy.' },
    { status: 503 }
  );
}

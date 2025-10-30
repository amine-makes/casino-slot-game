// Netlify Edge Function: Proxy /api/* to external backend
// Uses BACKEND_ORIGIN env var, e.g. https://your-backend.example.com

export default async (request, context) => {
  const backend = Deno.env.get("BACKEND_ORIGIN");
  if (!backend) {
    return new Response("BACKEND_ORIGIN not configured", { status: 500 });
  }
  const reqUrl = new URL(request.url);
  const pathAndQuery = reqUrl.pathname + reqUrl.search;
  // Ensure single slash between origin and path
  const target = backend.replace(/\/$/, "") + pathAndQuery;

  // Clone headers and add forwarding hints
  const headers = new Headers(request.headers);
  headers.set("X-Forwarded-Host", reqUrl.host);
  headers.set("X-Forwarded-Proto", reqUrl.protocol.replace(":", ""));

  // Build fetch options
  const init = {
    method: request.method,
    headers,
    body: undefined,
  };
  if (!['GET', 'HEAD'].includes(request.method)) {
    // Preserve body for non-GET/HEAD
    const buf = await request.arrayBuffer();
    init.body = buf;
  }

  const resp = await fetch(target, init);

  // Pass-through response with headers and status
  const outHeaders = new Headers(resp.headers);
  return new Response(resp.body, {
    status: resp.status,
    headers: outHeaders,
  });
};

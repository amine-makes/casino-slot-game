// Netlify Edge Function: Proxy /api/* to your backend
export default async (request, context) => {
  const backend = Deno.env.get('BACKEND_ORIGIN');
  if (!backend) {
    return new Response(
      JSON.stringify({
        error: "BACKEND_ORIGIN not configured",
        hint: "Set BACKEND_ORIGIN env var in Netlify to your backend URL",
      }),
      { status: 500, headers: { "content-type": "application/json" } }
    );
  }

  const reqUrl = new URL(request.url);
  const pathAndQuery = reqUrl.pathname + reqUrl.search; // e.g. /api/health?x=1
  const target = backend.replace(/\/$/, "") + pathAndQuery;

  const headers = new Headers(request.headers);
  headers.delete("host");
  headers.set("x-forwarded-host", reqUrl.host);
  headers.set("x-forwarded-proto", reqUrl.protocol.replace(":", ""));

  const hasBody = request.method !== "GET" && request.method !== "HEAD";
  const body = hasBody ? await request.arrayBuffer() : undefined;

  const upstream = await fetch(target, {
    method: request.method,
    headers,
    body,
    redirect: "manual",
  });

  return new Response(upstream.body, {
    status: upstream.status,
    headers: upstream.headers,
  });
};

export const config = { path: "/api/*" };


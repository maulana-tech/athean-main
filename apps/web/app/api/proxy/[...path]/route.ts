import { NextRequest, NextResponse } from "next/server";

const API_UPSTREAM = process.env.API_UPSTREAM ?? "http://43.129.54.139:8000";

async function proxy(req: NextRequest, params: { path?: string[] }) {
  const pathSegments = params.path ?? [];
  const upstreamPath = pathSegments.join("/");
  const url = new URL(req.url);
  const upstreamUrl = `${API_UPSTREAM}/${upstreamPath}${url.search}`;

  const upstreamHeaders = new Headers();
  const forwardHeaders = new Set([
    "authorization",
    "content-type",
    "accept",
    "accept-encoding",
    "user-agent",
    "cookie",
  ]);
  for (const [key, value] of req.headers.entries()) {
    if (forwardHeaders.has(key.toLowerCase())) {
      upstreamHeaders.set(key, value);
    }
  }
  if (!upstreamHeaders.has("user-agent")) {
    upstreamHeaders.set("user-agent", "Athean-Proxy/1.0");
  }

  const init: RequestInit = {
    method: req.method,
    headers: upstreamHeaders,
    redirect: "follow",
  };
  if (req.method !== "GET" && req.method !== "HEAD") {
    init.body = await req.arrayBuffer();
  }

  let upstream;
  try {
    upstream = await fetch(upstreamUrl, init);
  } catch (err) {
    return NextResponse.json(
      { error: "upstream fetch failed", upstream: upstreamUrl, detail: err instanceof Error ? err.message : String(err) },
      { status: 502 },
    );
  }

  const respHeaders = new Headers();
  upstream.headers.forEach((v, k) => {
    if (!["content-encoding", "content-length", "transfer-encoding", "connection"].includes(k.toLowerCase())) {
      respHeaders.set(k, v);
    }
  });
  respHeaders.set("access-control-allow-origin", "*");

  return new NextResponse(upstream.body, {
    status: upstream.status,
    headers: respHeaders,
  });
}

export async function GET(req: NextRequest, ctx: { params: { path?: string[] } }) {
  return proxy(req, ctx.params);
}
export async function POST(req: NextRequest, ctx: { params: { path?: string[] } }) {
  return proxy(req, ctx.params);
}
export async function PUT(req: NextRequest, ctx: { params: { path?: string[] } }) {
  return proxy(req, ctx.params);
}
export async function DELETE(req: NextRequest, ctx: { params: { path?: string[] } }) {
  return proxy(req, ctx.params);
}
export async function PATCH(req: NextRequest, ctx: { params: { path?: string[] } }) {
  return proxy(req, ctx.params);
}
export async function OPTIONS() {
  return new NextResponse(null, {
    status: 204,
    headers: { "access-control-allow-origin": "*", "access-control-max-age": "86400" },
  });
}

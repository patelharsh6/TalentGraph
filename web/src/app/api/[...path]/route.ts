import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL || "http://127.0.0.1:8000";
const API_KEY = process.env.TALENTGRAPH_API_KEY || "dev-key-change-in-prod";

async function proxyRequest(req: NextRequest, { params }: { params: { path: string[] } }) {
  try {
    const subpath = params.path.join("/");
    // Support paths that already start with api/ or not
    const backendPath = subpath.startsWith("api/") ? subpath : `api/${subpath}`;
    const url = new URL(backendPath, BACKEND_URL);
    url.search = req.nextUrl.search;

    const headers = new Headers();
    // Copy incoming headers that are safe to forward
    req.headers.forEach((val, key) => {
      const lower = key.toLowerCase();
      if (lower !== "host" && lower !== "x-api-key" && lower !== "connection") {
        headers.set(key, val);
      }
    });

    // Securely inject the API key on the server side
    headers.set("X-API-Key", API_KEY);

    const init: RequestInit = {
      method: req.method,
      headers,
    };

    if (req.method !== "GET" && req.method !== "HEAD") {
      init.body = await req.arrayBuffer();
    }

    const response = await fetch(url.toString(), init);

    const resHeaders = new Headers();
    response.headers.forEach((val, key) => {
      const lower = key.toLowerCase();
      if (lower !== "content-encoding" && lower !== "content-length") {
        resHeaders.set(key, val);
      }
    });

    const body = await response.arrayBuffer();
    return new NextResponse(body, {
      status: response.status,
      statusText: response.statusText,
      headers: resHeaders,
    });
  } catch (error: any) {
    return NextResponse.json(
      {
        type: "https://talentgraph.dev/problems/proxy_error",
        title: "Backend Proxy Error",
        status: 502,
        detail: error?.message || "Failed to communicate with TalentGraph backend API",
      },
      { status: 502 }
    );
  }
}

export const GET = proxyRequest;
export const POST = proxyRequest;
export const PUT = proxyRequest;
export const DELETE = proxyRequest;

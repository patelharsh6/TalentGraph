import { NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL || "http://127.0.0.1:8000";

export async function GET() {
  let backendStatus = "unknown";
  try {
    const res = await fetch(`${BACKEND_URL}/healthz`, { cache: "no-store" });
    backendStatus = res.ok ? "ok" : `degraded (${res.status})`;
  } catch (err: any) {
    backendStatus = `unreachable: ${err?.message || "error"}`;
  }

  return NextResponse.json({
    status: "ok",
    web: "healthy",
    backend_url: BACKEND_URL,
    backend_status: backendStatus,
    timestamp: new Date().toISOString(),
  });
}


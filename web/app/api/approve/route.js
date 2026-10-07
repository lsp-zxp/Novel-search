import { NextResponse } from "next/server";

const endpoint = process.env.AGENT_API_URL || "http://127.0.0.1:8000";

export async function POST(request) {
  try {
    const body = await request.json();
    const response = await fetch(`${endpoint}/approve`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      cache: "no-store",
    });
    const data = await response.json();
    return NextResponse.json(data, { status: response.status });
  } catch {
    return NextResponse.json(
      { error: "审批失败，请确认Agent服务仍在运行。" },
      { status: 502 },
    );
  }
}

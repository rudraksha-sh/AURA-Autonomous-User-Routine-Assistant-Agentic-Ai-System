import { isIP } from "node:net";
import { NextRequest, NextResponse } from "next/server";

export function proxy(request: NextRequest) {
  if (process.env.AURA_RENDER_INGRESS !== "1") return NextResponse.next();

  const secret = process.env.AURA_PROXY_SHARED_SECRET;
  const address = request.headers.get("cf-connecting-ip") ?? "";
  if (!secret || secret.length < 32 || !isIP(address)) {
    return NextResponse.json({ message: "API ingress unavailable." }, {
      status: 503, headers: { "Cache-Control": "no-store" },
    });
  }

  const headers = new Headers(request.headers);
  for (const name of ["forwarded", "x-forwarded-for", "x-real-ip", "x-aura-proxy-token", "x-aura-client-ip"]) {
    headers.delete(name);
  }
  headers.set("x-aura-proxy-token", secret);
  headers.set("x-aura-client-ip", address);
  return NextResponse.next({ request: { headers } });
}

export const config = { matcher: "/api/:path*" };

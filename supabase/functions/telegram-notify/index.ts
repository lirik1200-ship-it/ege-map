import { createClient } from "jsr:@supabase/supabase-js@2";

const SUPABASE_URL = Deno.env.get("SUPABASE_URL")!;
const ANON_KEY = Deno.env.get("SUPABASE_ANON_KEY")!;
const SERVICE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;

const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
};

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: CORS });
  if (req.method !== "POST") return new Response("method not allowed", { status: 405, headers: CORS });

  const authHeader = req.headers.get("Authorization") ?? "";
  const asCaller = createClient(SUPABASE_URL, ANON_KEY, { global: { headers: { Authorization: authHeader } } });

  let body: any;
  try { body = await req.json(); } catch { return new Response(JSON.stringify({ ok: false, error: "bad_json" }), { status: 400, headers: CORS }); }
  const { studentId, text } = body ?? {};
  if (!studentId || !text) return new Response(JSON.stringify({ ok: false, error: "missing_fields" }), { status: 400, headers: CORS });

  const { data: student, error } = await asCaller
    .from("students")
    .select("id, telegram_chat_id")
    .eq("id", studentId)
    .maybeSingle();

  if (error || !student) return new Response(JSON.stringify({ ok: false, error: "not_found_or_forbidden" }), { status: 403, headers: CORS });
  if (!student.telegram_chat_id) return new Response(JSON.stringify({ ok: true, skipped: "not_subscribed" }), { headers: CORS });

  const service = createClient(SUPABASE_URL, SERVICE_KEY);
  const { data: secret } = await service.from("app_secrets").select("value").eq("key", "telegram_bot_token").single();
  if (!secret) return new Response(JSON.stringify({ ok: false, error: "no_bot_token" }), { status: 500, headers: CORS });

  const res = await fetch(`https://api.telegram.org/bot${secret.value}/sendMessage`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ chat_id: student.telegram_chat_id, text, parse_mode: "HTML" }),
  });
  const tgResult = await res.json();
  return new Response(JSON.stringify({ ok: tgResult.ok === true, telegram: tgResult }), { headers: CORS });
});

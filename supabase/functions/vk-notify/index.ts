// Отправка уведомления о пробнике подписчикам ВКонтакте. Вызывается из приложения учителя (нужен JWT).
import { createClient } from "jsr:@supabase/supabase-js@2";

const SUPABASE_URL = Deno.env.get("SUPABASE_URL")!;
const ANON_KEY = Deno.env.get("SUPABASE_ANON_KEY")!;
const SERVICE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;

const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
};
const json = (o: unknown, status = 200) => new Response(JSON.stringify(o), { status, headers: CORS });

// В ВК нет HTML: ссылки превращаем в «текст: адрес», теги убираем
function toPlain(html: string): string {
  return html
    .replace(/<a\s+[^>]*href="([^"]+)"[^>]*>([\s\S]*?)<\/a>/gi, (_m, u, t) => `${t}: ${u}`)
    .replace(/<[^>]+>/g, "")
    .replace(/&lt;/g, "<").replace(/&gt;/g, ">").replace(/&quot;/g, '"').replace(/&#39;/g, "'").replace(/&amp;/g, "&");
}

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: CORS });
  if (req.method !== "POST") return new Response("method not allowed", { status: 405, headers: CORS });

  const asCaller = createClient(SUPABASE_URL, ANON_KEY, { global: { headers: { Authorization: req.headers.get("Authorization") ?? "" } } });
  let body: any;
  try { body = await req.json(); } catch { return json({ ok: false, error: "bad_json" }, 400); }
  const { studentId, text } = body ?? {};
  if (!studentId || !text) return json({ ok: false, error: "missing_fields" }, 400);

  // Ученик должен принадлежать вызвавшему учителю (RLS)
  const { data: student, error } = await asCaller.from("students").select("id").eq("id", studentId).maybeSingle();
  if (error || !student) return json({ ok: false, error: "not_found_or_forbidden" }, 403);

  const service = createClient(SUPABASE_URL, SERVICE_KEY);
  const { data: subs } = await service.from("vk_subscriptions").select("id, vk_user_id").eq("student_id", studentId);
  if (!subs?.length) return json({ ok: true, skipped: "not_subscribed" });

  const { data: tok } = await service.from("app_secrets").select("value").eq("key", "vk_group_token").maybeSingle();
  if (!tok) return json({ ok: false, error: "no_vk_token" }, 500);

  const message = toPlain(String(text)).slice(0, 4000);
  let sent = 0;
  for (const s of subs) {
    const res = await fetch("https://api.vk.com/method/messages.send", {
      method: "POST",
      body: new URLSearchParams({
        user_id: String(s.vk_user_id),
        random_id: String(Math.floor(Math.random() * 2147483647)),
        message,
        access_token: tok.value as string,
        v: "5.199",
      }),
    });
    const r = await res.json();
    if (r.response) sent++;
    // 901/902: пользователь запретил сообщения — подписку удаляем
    else if ([901, 902].includes(r.error?.error_code)) await service.from("vk_subscriptions").delete().eq("id", s.id);
  }
  return json({ ok: sent > 0, sent });
});

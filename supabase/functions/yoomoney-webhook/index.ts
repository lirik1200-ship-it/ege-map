// HTTP-уведомления ЮMoney. JWT не проверяется (verify_jwt=false): подлинность проверяется по подписи
// с секретом из настроек кошелька (app_secrets.yoomoney_notification_secret).
// Текущий протокол: поле sign = HMAC-SHA256(секрет, все поля кроме sign,
// отсортированные по ключу, в виде key=rawurlencode(value) через &).
// Старый sha1_hash проверяется, если вдруг придёт.
import { createClient } from "jsr:@supabase/supabase-js@2";

const ok = (t = "ok") => new Response(t, { status: 200 });
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const enc = new TextEncoder();
const hex = (b: ArrayBuffer) => [...new Uint8Array(b)].map((x) => x.toString(16).padStart(2, "0")).join("");
const rawurlencode = (v: string) =>
  encodeURIComponent(v).replace(/[!'()*]/g, (c) => "%" + c.charCodeAt(0).toString(16).toUpperCase());

async function hmac256(key: string, msg: string) {
  const k = await crypto.subtle.importKey("raw", enc.encode(key), { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
  return hex(await crypto.subtle.sign("HMAC", k, enc.encode(msg)));
}
const sha1 = async (s: string) => hex(await crypto.subtle.digest("SHA-1", enc.encode(s)));
function safeEq(a: string, b: string) {
  if (!a || a.length !== b.length) return false;
  let r = 0;
  for (let i = 0; i < a.length; i++) r |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return r === 0;
}

async function verify(f: Record<string, string>, secret: string) {
  if (f.sign) {
    const msg = Object.keys(f).filter((k) => k !== "sign").sort()
      .map((k) => k + "=" + rawurlencode(f[k])).join("&");
    return safeEq(f.sign.toLowerCase(), await hmac256(secret, msg));
  }
  if (f.sha1_hash) {
    const s = [f.notification_type, f.operation_id, f.amount, f.currency, f.datetime,
      f.sender, f.codepro, secret, f.label].map((x) => x ?? "").join("&");
    return safeEq(f.sha1_hash.toLowerCase(), await sha1(s));
  }
  return false;
}

Deno.serve(async (req) => {
  if (req.method !== "POST") return new Response("method", { status: 405 });
  const f: Record<string, string> = {};
  new URLSearchParams(await req.text()).forEach((v, k) => (f[k] = v));

  const db = createClient(Deno.env.get("SUPABASE_URL")!, Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!);
  const { data: sec } = await db.from("app_secrets").select("value").eq("key", "yoomoney_notification_secret").maybeSingle();
  if (!sec?.value) { console.error("yoomoney: нет секрета"); return new Response("not configured", { status: 500 }); }

  if (!(await verify(f, sec.value.trim()))) {
    console.warn("yoomoney: неверная подпись", JSON.stringify(f));
    return new Response("bad signature", { status: 400 });
  }
  if (f.test_notification === "true") { console.log("yoomoney: тестовое уведомление принято, подпись сходится"); return ok("test ok"); }
  if (f.codepro === "true" || f.unaccepted === "true" || f.currency !== "643") {
    console.warn("yoomoney: платёж не зачислен/не в рублях", f.operation_id);
    return ok("skipped");
  }
  if (!UUID.test(f.label ?? "")) { console.log("yoomoney: перевод без метки", f.operation_id); return ok("no label"); }

  // Сколько заплатил покупатель (комиссия удерживается из amount, не с него)
  const paid = Number(f.withdraw_amount || f.amount);
  const { data, error } = await db.rpc("apply_payment", {
    p_label: f.label, p_op_id: f.operation_id, p_paid: paid, p_raw: f,
  });
  if (error) { console.error("yoomoney: apply_payment", error.message); return new Response("db error", { status: 500 }); }
  console.log("yoomoney:", f.operation_id, data);
  return ok(String(data));
});

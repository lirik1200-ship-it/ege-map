import { createClient } from "jsr:@supabase/supabase-js@2";

const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
};
const json = (b: unknown, s = 200) =>
  new Response(JSON.stringify(b), { status: s, headers: { ...CORS, "Content-Type": "application/json" } });
const ALLOWED_RETURN = ["https://ege-map.ru", "https://www.ege-map.ru"];

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: CORS });
  if (req.method !== "POST") return json({ error: "method" }, 405);

  const url = Deno.env.get("SUPABASE_URL")!;
  const service = createClient(url, Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!);
  const authHeader = req.headers.get("Authorization") ?? "";
  const { data: { user }, error: uErr } = await service.auth.getUser(authHeader.replace(/^Bearer\s+/i, ""));
  if (uErr || !user) return json({ error: "Войдите в аккаунт заново" }, 401);

  let body: { plan?: string; qty?: number; returnUrl?: string } = {};
  try { body = await req.json(); } catch { /* пусто */ }

  const { data: plan } = await service.from("plans").select("*").eq("code", body.plan ?? "").eq("active", true).maybeSingle();
  if (!plan) return json({ error: "Тариф не найден" }, 400);
  const qty = plan.kind === "topup" ? Math.floor(Number(body.qty) || 1) : 1;
  if (qty < 1 || qty > plan.max_qty) return json({ error: `Можно от 1 до ${plan.max_qty}` }, 400);
  const amount = Number(plan.price) * qty; // цена только из базы, не с клиента

  const { data: wallet } = await service.from("app_secrets").select("value").eq("key", "yoomoney_wallet").maybeSingle();
  if (!wallet?.value) return json({ error: "Оплата временно недоступна" }, 503);

  const { data: pay, error: pErr } = await service.from("payments")
    .insert({ teacher_id: user.id, plan: plan.code, qty, amount, status: "pending", provider: "yoomoney" })
    .select("label").single();
  if (pErr || !pay) return json({ error: "Не удалось создать платёж" }, 500);

  const ret = String(body.returnUrl ?? "");
  const base = ALLOWED_RETURN.find((o) => ret.startsWith(o + "/") || ret === o) ? ret : "https://ege-map.ru/app.html";
  const successURL = base + (base.includes("?") ? "&" : "?") + "paid=" + pay.label;
  const targets = plan.kind === "topup"
    ? `ЕГЭ_Map: докупка мест (${qty})`
    : `ЕГЭ_Map: пакет «${plan.title}» (${plan.seats} мест) до 30 июня`;

  return json({
    action: "https://yoomoney.ru/quickpay/confirm",
    fields: {
      receiver: wallet.value,
      "quickpay-form": "button",
      paymentType: "AC",
      sum: amount.toFixed(2),
      label: pay.label,
      targets,
      successURL,
    },
  });
});

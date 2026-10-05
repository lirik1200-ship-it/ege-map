// Бот сообщества ВКонтакте: принимает события Callback API.
// Подписка: ссылка ученика → диалог с сообществом (метка ref = share_token) → согласие кнопкой → запись в vk_subscriptions.
// Секреты (app_secrets): vk_group_token, vk_secret, vk_confirmation, vk_group_id (необязательно).
import { createClient } from "jsr:@supabase/supabase-js@2";

const SUPABASE_URL = Deno.env.get("SUPABASE_URL")!;
const SERVICE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
const service = createClient(SUPABASE_URL, SERVICE_KEY);

const VK_API = "https://api.vk.com/method";
const VK_VERSION = "5.199";
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const UUID_ANY = /[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/i;
const CONSENT_URL = "https://ege-map.ru/app.html?legal=consent";
const STOP_WORDS = ["стоп", "stop", "/stop", "отписаться", "отписка"];

async function secret(key: string): Promise<string | null> {
  const { data } = await service.from("app_secrets").select("value").eq("key", key).maybeSingle();
  return (data?.value as string) ?? null;
}

async function send(userId: number, message: string, keyboard?: unknown) {
  const token = await secret("vk_group_token");
  if (!token) return;
  const params = new URLSearchParams({
    user_id: String(userId),
    random_id: String(Math.floor(Math.random() * 2147483647)),
    message,
    access_token: token,
    v: VK_VERSION,
  });
  if (keyboard) params.set("keyboard", JSON.stringify(keyboard));
  await fetch(`${VK_API}/messages.send`, { method: "POST", body: params });
}

const consentText = (code: string) =>
  `Здравствуйте! Это сообщество ЕГЭ_Map.\n\n` +
  `Чтобы получать результаты пробников ученика с кодом ${code}, подтвердите согласие на обработку данных: ` +
  `мы сохраним ваш идентификатор ВКонтакте и код ученика (имя и фамилию ученика мы не получаем).\n\n` +
  `Нажимая «Согласен(на)», вы подтверждаете, что вам исполнилось 14 лет или вы родитель (законный представитель) ученика.\n` +
  `Текст согласия: ${CONSENT_URL}\n\n` +
  `Отписаться можно в любой момент: напишите «Стоп».`;

const welcomeText = (code: string) =>
  `Готово! Теперь сюда будет приходить короткая карточка после каждого пробника:\n` +
  `• балл и как он изменился к прошлому разу\n• прогноз к экзамену\n• темы, которые стоит повторить\n\n` +
  `Подписка оформлена на ученика с кодом ${code}. Имя и фамилию мы не храним. Отписаться: напишите «Стоп».`;

const HELP_TEXT =
  "Это сообщество сервиса ЕГЭ_Map. Чтобы подписаться на результаты пробников, откройте личную ссылку ученика от учителя и нажмите «Подключить ВКонтакте». " +
  "Если кнопка не сработала, пришлите сюда личную ссылку ученика целиком. Чтобы отписаться, напишите «Стоп».";

Deno.serve(async (req) => {
  let body: any;
  try { body = await req.json(); } catch { return new Response("ok"); }

  // Подпись Callback API: секретный ключ, заданный в настройках сообщества, должен совпасть с vk_secret
  const expected = await secret("vk_secret");
  if (!expected || body?.secret !== expected) return new Response("forbidden", { status: 403 });
  const groupId = await secret("vk_group_id");
  if (groupId && String(body?.group_id) !== groupId) return new Response("ok");

  if (body.type === "confirmation") {
    return new Response((await secret("vk_confirmation")) ?? "", { headers: { "Content-Type": "text/plain" } });
  }

  if (body.type === "message_deny") {
    const uid = Number(body.object?.user_id);
    if (uid) await service.from("vk_subscriptions").delete().eq("vk_user_id", uid);
    return new Response("ok");
  }

  if (body.type !== "message_new") return new Response("ok");

  const m = body.object?.message ?? body.object ?? {};
  const uid = Number(m.from_id);
  if (!uid || uid < 0) return new Response("ok");
  const text = String(m.text ?? "").trim();
  let payload: any = null;
  try { payload = m.payload ? JSON.parse(m.payload) : null; } catch { /* не наш payload */ }
  const ref = String(m.ref ?? "").trim();

  // 1. Нажата кнопка «Согласен(на)»
  if (payload?.c === "yes" && UUID.test(String(payload.t ?? ""))) {
    const { data: student } = await service.from("students").select("id, name").eq("share_token", payload.t).maybeSingle();
    if (!student) { await send(uid, "Ссылка не найдена или устарела. Уточните у учителя новую ссылку."); return new Response("ok"); }
    await service.from("vk_subscriptions").upsert(
      { student_id: student.id, vk_user_id: uid, consent_at: new Date().toISOString() },
      { onConflict: "student_id,vk_user_id" },
    );
    await send(uid, welcomeText(student.name));
    return new Response("ok");
  }

  // 2. Отписка
  if (STOP_WORDS.includes(text.toLowerCase())) {
    await service.from("vk_subscriptions").delete().eq("vk_user_id", uid);
    await send(uid, "Уведомления отключены, ваши данные удалены. Снова подписаться можно по личной ссылке от учителя.");
    return new Response("ok");
  }

  // 3. Пришли по ссылке ученика: показываем согласие с кнопкой
  // Метка ref приходит, когда диалог открыт по ссылке; если диалог уже был, человек может вставить личную ссылку ученика целиком
  const token = (ref.match(UUID_ANY) || text.match(UUID_ANY) || [])[0] ?? "";
  if (token) {
    const { data: student } = await service.from("students").select("id, name").eq("share_token", token).maybeSingle();
    if (!student) { await send(uid, "Ссылка не найдена или устарела. Уточните у учителя новую ссылку."); return new Response("ok"); }
    const keyboard = {
      inline: true,
      buttons: [[{ action: { type: "text", label: "Согласен(на)", payload: JSON.stringify({ c: "yes", t: token }) }, color: "positive" }]],
    };
    await send(uid, consentText(student.name), keyboard);
    return new Response("ok");
  }

  await send(uid, HELP_TEXT);
  return new Response("ok");
});

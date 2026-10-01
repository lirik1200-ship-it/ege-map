import { createClient } from "jsr:@supabase/supabase-js@2";

const SUPABASE_URL = Deno.env.get("SUPABASE_URL")!;
const SERVICE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
const service = createClient(SUPABASE_URL, SERVICE_KEY);

async function getBotToken(): Promise<string> {
  const { data } = await service.from("app_secrets").select("value").eq("key", "telegram_bot_token").single();
  return data!.value as string;
}

async function tg(method: string, payload: unknown) {
  const token = await getBotToken();
  await fetch(`https://api.telegram.org/bot${token}/${method}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

const WELCOME_NO_TOKEN =
  "👋 Это бот <b>ЕГЭ_Map</b>. Чтобы подписаться на уведомления, перейдите по ссылке, которую дал вам учитель — она откроет меня автоматически.";

function welcomeText(name: string): string {
  const lines = [
    "✅ <b>Готово!</b>",
    "",
    "Это бот <b>ЕГЭ_Map</b> — сервиса, которым пользуется ваш учитель для учёта пробников ЕГЭ/ОГЭ. Теперь сюда будет приходить короткая карточка после каждого нового пробника:",
    "",
    "• текущий балл и как он изменился к прошлому разу",
    "• прогноз к экзамену в виде вилки",
    "• темы, которые стоит повторить перед следующим занятием",
    "",
    `Подписка оформлена на ученика с кодом ${name} — без имени и фамилии, мы их не храним. Отписаться — /stop.`,
  ];
  return lines.join("\n");
}

Deno.serve(async (req) => {
  let update: any;
  try { update = await req.json(); } catch { return new Response("ok"); }

  const msg = update?.message;
  const text: string | undefined = msg?.text;
  const chatId = msg?.chat?.id;
  if (!text || !chatId) return new Response("ok");

  if (text.startsWith("/start")) {
    const token = text.split(" ")[1]?.trim();
    if (!token) {
      await tg("sendMessage", { chat_id: chatId, parse_mode: "HTML", text: WELCOME_NO_TOKEN });
      return new Response("ok");
    }
    const { data: student, error } = await service
      .from("students")
      .update({ telegram_chat_id: String(chatId) })
      .eq("share_token", token)
      .select("name")
      .maybeSingle();

    if (error || !student) {
      await tg("sendMessage", { chat_id: chatId, text: "Ссылка не найдена или устарела. Уточните у учителя новую ссылку." });
    } else {
      await tg("sendMessage", { chat_id: chatId, parse_mode: "HTML", text: welcomeText(student.name) });
    }
    return new Response("ok");
  }

  if (text.startsWith("/stop")) {
    await service.from("students").update({ telegram_chat_id: null }).eq("telegram_chat_id", String(chatId));
    await tg("sendMessage", { chat_id: chatId, text: "Уведомления отключены. Снова подписаться можно по той же ссылке от учителя." });
  }

  return new Response("ok");
});

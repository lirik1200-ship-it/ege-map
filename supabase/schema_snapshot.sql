-- СНИМОК схемы public проекта ritcwzuelbffwmooxbbp на 2026-10-01 (справочный, не для слепого запуска).
-- Источник правды — живая база; перед правками перечитывать её (Supabase MCP: list_tables, execute_sql).
-- Таблицы создавались вручную/через миграции в панели, CREATE TABLE здесь — в виде списка колонок.

/* ТАБЛИЦЫ (RLS включён везде)
profiles   id uuid pk, plan text default 'free', plan_expires_at timestamptz, plan_limit int (устар. ручной override),
           plan_base_limit int, plan_topup_count int default 0, enabled_subjects jsonb default '[]', created_at
classes    id uuid, teacher_id uuid default auth.uid(), name, exam_type default 'ege', archived bool, created_at
students   id uuid, teacher_id default auth.uid(), name (= обезличенный код), share_token uuid default gen_random_uuid(),
           class_id uuid, exam_type default 'ege', group_name (устар.), telegram_chat_id text, created_at
exams      id uuid, student_id uuid, exam_date date, results jsonb, essay jsonb, comment text, created_at; unique(student_id, exam_date)
plans      code pk, title, kind ('package'|'topup'), seats, price, max_qty, sort, active
payments   id bigint, teacher_id, plan, qty, amount, status ('pending'|'paid'), provider, provider_payment_id, label uuid, paid_at, raw jsonb, created_at
app_secrets key, value, updated_at  -- RLS без политик: читается только service_role (Edge Functions). Ключи: telegram_bot_token, yoomoney_wallet, yoomoney_notification_secret
works, work_scores -- пустые, остались от откаченного раздела «Текущие работы»; решение (удалить/оставить) не принято
*/

-- ПОЛИТИКИ RLS
-- classes:  ALL для authenticated, teacher_id = auth.uid()
-- students: ALL для authenticated, teacher_id = auth.uid()
-- exams:    ALL для authenticated, если student принадлежит auth.uid()
-- profiles: SELECT своего профиля; UPDATE своего профиля, но GRANT UPDATE выдан только на колонку enabled_subjects (проверено 2026-10-01) — тариф с клиента подменить нельзя
-- plans:    SELECT для anon, authenticated где active
-- payments: SELECT своих (teacher_id = auth.uid()); запись только service_role
-- works / work_scores: ALL для своих (роль public)

-- ДАННЫЕ plans
-- start 10/990, standard 30/2490, class_plus 60/3990, school 150/6990 (package, max_qty 1); topup 1/149 (max_qty 5)

-- ФУНКЦИИ
CREATE OR REPLACE FUNCTION public.apply_payment(p_label uuid, p_op_id text, p_paid numeric, p_raw jsonb)
 RETURNS text LANGUAGE plpgsql SECURITY DEFINER SET search_path TO 'public'
AS $function$
declare pay public.payments; pl public.plans; prof public.profiles;
        active boolean; new_base int; new_plan text; new_topup int; new_exp timestamptz;
begin
  select * into pay from public.payments where label = p_label for update;
  if not found then return 'unknown_label'; end if;
  if pay.status = 'paid' then return 'already_paid'; end if;
  if p_paid < pay.amount then
    update public.payments set raw = p_raw where id = pay.id;
    return 'amount_mismatch';
  end if;
  select * into pl from public.plans where code = pay.plan;
  if not found then return 'unknown_plan'; end if;

  select * into prof from public.profiles where id = pay.teacher_id for update;
  active := prof.plan_expires_at is not null and prof.plan_expires_at > now();
  new_exp := greatest(public.season_end(now()), case when active then prof.plan_expires_at end);

  if pl.kind = 'package' then
    new_base := greatest(pl.seats, case when active then coalesce(prof.plan_base_limit,0) else 0 end);
    new_plan := case when active and coalesce(prof.plan_base_limit,0) > pl.seats then prof.plan else pl.code end;
    new_topup := case when active then coalesce(prof.plan_topup_count,0) else 0 end;
  else
    new_plan := case when active then prof.plan else 'free' end;
    new_base := case when active then prof.plan_base_limit else null end;
    new_topup := case when active then coalesce(prof.plan_topup_count,0) else 0 end + pay.qty;
  end if;

  update public.profiles set plan = new_plan, plan_base_limit = new_base,
    plan_topup_count = new_topup, plan_expires_at = new_exp
  where id = pay.teacher_id;
  update public.payments set status = 'paid', paid_at = now(), provider = 'yoomoney',
    provider_payment_id = p_op_id, raw = p_raw
  where id = pay.id;
  return 'ok';
end $function$;

CREATE OR REPLACE FUNCTION public.season_end(ts timestamptz DEFAULT now())
 RETURNS timestamptz LANGUAGE sql IMMUTABLE SET search_path TO 'public'
AS $function$
  select make_timestamptz(
    extract(year from ts at time zone 'Europe/Moscow')::int
      + case when extract(month from ts at time zone 'Europe/Moscow') >= 6 then 1 else 0 end,
    6, 30, 23, 59, 59, 'Europe/Moscow');
$function$;

CREATE OR REPLACE FUNCTION public.enforce_student_limit()
 RETURNS trigger LANGUAGE plpgsql SET search_path TO 'public'
AS $function$ declare cur_plan text; expires timestamptz; base_lim int; topup int; lim int; cnt int; begin select plan, plan_expires_at, plan_base_limit, plan_topup_count into cur_plan, expires, base_lim, topup from public.profiles where id = new.teacher_id; if cur_plan is null then cur_plan := 'free'; end if; if expires is not null and expires < now() then cur_plan := 'free'; base_lim := null; topup := 0; end if; lim := coalesce(base_lim, case cur_plan when 'start' then 10 when 'standard' then 30 when 'class_plus' then 60 when 'school' then 150 when 'school_plus' then 300 else 3 end) + coalesce(topup, 0); select count(*) into cnt from public.students where teacher_id = new.teacher_id; if cnt >= lim then raise exception 'Достигнут лимит тарифа: % учеников', lim; end if; return new; end; $function$;
CREATE TRIGGER students_limit BEFORE INSERT ON public.students FOR EACH ROW EXECUTE FUNCTION enforce_student_limit();

CREATE OR REPLACE FUNCTION public.get_student_report(token uuid)
 RETURNS jsonb LANGUAGE sql SECURITY DEFINER SET search_path TO 'public'
AS $function$
  select jsonb_build_object(
    'name', s.name,
    'exam_type', coalesce(s.exam_type,'ege'),
    'exams', coalesce((
      select jsonb_agg(jsonb_build_object('date', e.exam_date, 'results', e.results, 'essay', e.essay, 'comment', e.comment)
             order by e.exam_date)
      from exams e where e.student_id = s.id), '[]'::jsonb))
  from students s where s.share_token = token;
$function$;
-- anon вызывает по замыслу (ссылка ученика); при нулевом числе пробников возвращает exams = []

CREATE OR REPLACE FUNCTION public.delete_my_account()
 RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path TO 'public', 'auth'
AS $function$
declare uid uuid := auth.uid();
begin
  if uid is null then raise exception 'not authenticated'; end if;
  delete from public.exams where student_id in (select id from public.students where teacher_id = uid);
  delete from public.students where teacher_id = uid;
  delete from public.classes where teacher_id = uid;
  delete from public.profiles where id = uid;
  delete from auth.users where id = uid;
end $function$;

CREATE OR REPLACE FUNCTION public.handle_new_user()
 RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path TO 'public'
AS $function$
begin
  insert into public.profiles (id) values (new.id) on conflict (id) do nothing;
  return new;
exception when others then
  raise warning 'handle_new_user failed for %: %', new.id, sqlerrm;
  return new;
end $function$;
-- Триггер на auth.users вызывает handle_new_user; EXECUTE у anon/authenticated отозван 2026-09-30.

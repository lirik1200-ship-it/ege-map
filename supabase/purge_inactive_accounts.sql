-- Автоудаление неактивных аккаунтов: нет входа 6 месяцев (если входа не было совсем — считается с даты регистрации).
-- Всё связанное (ученики, пробники, классы, подписки ВК, платежи, профиль) удаляется каскадом от auth.users.
-- Аккаунты с оплатой за последние 6 месяцев не трогаем. Запуск: ежедневно в 03:00 UTC (pg_cron).
create extension if not exists pg_cron with schema pg_catalog;

create or replace function public.purge_inactive_accounts()
returns integer
language plpgsql
security definer
set search_path to 'public', 'auth'
as $$
declare n integer;
begin
  with gone as (
    delete from auth.users u
    where coalesce(u.last_sign_in_at, u.created_at) < now() - interval '6 months'
      and not exists (
        select 1 from public.payments p
        where p.teacher_id = u.id and p.status = 'paid' and p.created_at > now() - interval '6 months')
    returning 1)
  select count(*) into n from gone;
  return n;
end $$;

-- вызывается только по расписанию, не через API
revoke all on function public.purge_inactive_accounts() from public, anon, authenticated;

select cron.unschedule('purge-inactive-accounts')
  where exists (select 1 from cron.job where jobname = 'purge-inactive-accounts');
select cron.schedule('purge-inactive-accounts', '0 3 * * *', $$select public.purge_inactive_accounts()$$);

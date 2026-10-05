-- Подписчики ВКонтакте (родители и ученики), согласие записывается при нажатии кнопки в диалоге с сообществом.
-- Доступ только у service_role (Edge Functions): учитель не видит и не может менять идентификаторы подписчиков.
create table if not exists public.vk_subscriptions (
  id bigint generated always as identity primary key,
  student_id uuid not null references public.students(id) on delete cascade,
  vk_user_id bigint not null,
  consent_at timestamptz not null default now(),
  created_at timestamptz not null default now(),
  unique (student_id, vk_user_id)
);
alter table public.vk_subscriptions enable row level security;
revoke all on public.vk_subscriptions from anon, authenticated;
comment on table public.vk_subscriptions is 'VK ID подписчиков и момент согласия. RLS без политик: читают только Edge Functions (service_role).';

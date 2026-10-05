# ЕГЭ_Map — контекст для Claude Code

Веб-приложение для учителей: учёт пробников ЕГЭ/ОГЭ по заданиям, прогноз, отчёты родителям, кабинет ученика по ссылке, уведомления ВКонтакте (Telegram-бот на паузе). Сайт https://ege-map.ru (GitHub Pages, CNAME). Язык интерфейса и общения — русский.

## Структура репозитория
- `app.html` — всё приложение в одном файле (vanilla JS, Tailwind CDN, Chart.js, supabase-js, html2pdf.js). Не разбивать на модули без запроса.
- Лендинг (статический, без сборки; правки лендинга и приложения — раздельно):
  - `index.html` — для учителей и репетиторов; `parents.html` — «Родителям» (пример отчёта, бот, приватность); `report-sample.html` — пример отчёта (iframe в лендинге).
  - `support.js` — рантайм для `index.html`/`parents.html`, **сгенерирован, не редактировать**; `image-slot.js` — веб-компонент `<image-slot>`.
  - Графика: `logo-lockup.svg`, `logo-lockup-dark.svg`, `author.jpg` (аватар в приложении), `author-web.jpg` (лендинг), `og-image.png`, `favicon.svg`, `favicon-32.png`, `apple-touch-icon.png`, `max-icon.png`. Папки `screenshots/` больше нет.
- `supabase/functions/*` — Edge Functions (Deno): `create-payment`, `yoomoney-webhook` (verify_jwt=false, проверка подписи HMAC-SHA256), `vk-webhook` (verify_jwt=false, проверка секретного ключа), `vk-notify`, `telegram-notify`/`telegram-webhook` (на паузе: включаются `app_secrets.telegram_enabled='true'`). Настройка ВК: `docs/vk-setup.md`; правовые тексты и чек-лист: `docs/legal-checklist.md`.
- `vendor/` и `fonts/` — библиотеки (Tailwind Play 3.4.17, Chart.js 4.4.1, supabase-js 2.117.2, html2pdf 0.10.1, React 18.3.1, Babel 7.29.0) и шрифты Onest/IBM Plex Mono лежат на нашем сайте, к CDN и Google страницы не обращаются (152-ФЗ, IP посетителей). В `support.js` три адреса unpkg заменены на `./vendor/…` (хэши SRI те же): после пересборки рантайма повторить. Обновлять библиотеки вручную.
- `robots.txt`, `sitemap.xml` — при добавлении страниц дописывать в sitemap. `og-image.png` подключён как `og-image.png?v=2` (при смене картинки поднимать версию).
- Калькулятор баллов (виджет «настоящий калькулятор»: табло, клавиши, предметы внизу, ЕГЭ/ОГЭ): страницы `kalkulyator-ballov-{ege,oge}.html`, `perevod-ballov-{ege,oge}-*.html` (16), `widget.html` (iframe для чужих сайтов, noindex), `vstroit-kalkulyator.html` (код для вставки). Всё генерируется `python3 tools/build_calculators.py` из шкал в `app.html` (EGE_SCALE, …, *_OGE_MARK_SCALE) и перезаписывает `sitemap.xml`; руками не править. Год шкал — переменные YEAR/UPDATED_* в начале скрипта. Профильной математики ЕГЭ нет: её шкалы нет в приложении. `widget.html?exam=ege|oge&subj=rus|lit|math|bio|geo|phys|chem|inf&mode=` — режимы: без параметра (чужие сайты, наклейка и логотип ведут на ege-map.ru), `landing` (наклейка «3 ученика бесплатно» → приложение), `plain` (без наклейки, логотип → сайт), `app` (окно на странице входа app.html, без внешних ссылок). Калькулятор встроен: секция `#kalkulyator` в index.html и parents.html (iframe), в app.html — кнопка в шапке и в левой карточке страницы входа (`openCalc()`, окно `#calc-modal`).
- `docs/` лежит только локально и в публичный репозиторий не пушится (`.gitignore`): там юридический чек-лист, тарифы, открытые вопросы.
- `supabase/purge_inactive_accounts.sql` — автоудаление аккаунтов без входа 6 месяцев (pg_cron, ежедневно 03:00 UTC, уже применено в базе). Кнопка «Удалить аккаунт» — в «Личном кабинете» (`delete_my_account`).
- `supabase/schema_snapshot.sql` — справочный снимок схемы и функций. Правда — в живой базе (проект `ritcwzuelbffwmooxbbp`).
- `docs/tarify.md`, `docs/TODO.md` — тарифы, список дел.
- `tests/harness*.py` — прогон приложения в headless Playwright с подменой CDN-библиотек и Supabase (запуск: `python3 tests/harness.py`; harness2 — оплата/auth/лимит/share/отчёт; harness3 — демо-класс; harness4 — пустой кабинет ученика).

## Как устроены index.html и parents.html
«Design Component»: разметка внутри `<x-dc>…</x-dc>`, логика — в `<script type="text/x-dc" data-dc-script>` (класс `Component extends DCLogic`, без `render()`).
- Подстановки `{{ path }}` — только пути к значениям, без выражений; всё вычисляемое — в `renderVals()`.
- Циклы `<sc-for list="{{ items }}" as="item">` (`$index`), условия `<sc-if value="{{ flag }}">`. События camelCase (`onClick="{{ handler }}"`), `class` → `className`.
- Стили только инлайн; ховер/фокус — `style-hover`/`style-focus`/`style-active`. В `<helmet><style>` — только `@font-face`, `@keyframes`, сбросы и медиазапросы (брейкпоинты 980px / 640px через `[data-m="…"]` с `!important`).
- `data-props` на теге скрипта — JSON пропов (`appUrl` = `app.html`; фолбэк `this.props.appUrl || "app.html"` в логике — при переезде приложения менять оба места).

## Ссылки между лендингом и приложением
- Демо: `app.html?demo=1` (демо-режим без базы, 14 учеников). Тарифы: `app.html?buy=start|standard|class_plus|school|school_plus` — выбор ждёт в sessionStorage до входа, затем открывается оплата (`resumeBuyFromLanding`).
- `SITE_URL = "https://ege-map.ru"` в app.html — куда ведёт «Назад на сайт» из демо без referrer.
- Бот ВКонтакте: `https://vk.me/ege_map`. Контакты берутся из `AUTHOR` в app.html; формы заявки на лендинге нет.

## Бренд
- Шрифты: Onest (текст), IBM Plex Mono (метки, цифры). Цвета: `#00FDFF`, фон `#E4FDFE`, лайм `#D7F205`, текст `#0C0C0A`, вторичный `#4F5A59` / `#6F7B7A`.
- Кнопки — пилюли `999px`, высота 42–56px; карточки — радиус 18–34px. Название всегда «ЕГЭ_Map» латиницей.

## Ключевые решения
- Ученики анонимны: только коды (11А-01); расшифровка хранится локально в браузере учителя. Не добавлять сбор ФИО.
- Тарифы «платишь за места»; лимит = `plan_base_limit + plan_topup_count`, срок до 30 июня. Цены: таблица `plans` + `PLANS` в app.html (сверять оба).
- Оплата: ЮMoney Quickpay → HTTP-уведомление → `apply_payment()` (идемпотентна, проверка суммы). Секреты только в `app_secrets` (telegram_bot_token, vk_group_token, vk_secret, vk_confirmation, vk_group_id, yoomoney_wallet, yoomoney_notification_secret) — НИКОГДА не класть в репозиторий и в код.
- Профиль: клиенту разрешён UPDATE только колонки `enabled_subjects`. Не расширять GRANT.
- Демо-класс (15 вымышленных учеников) — только на клиенте, в БД не пишется, в лимит не входит.
- Кабинет ученика по ссылке `?s=<share_token>` работает сразу после создания ученика; без пробников показывает «Пробников пока нет» + кнопку подключения бота (`BOT_LINK`).
- Раздел «Текущие работы» откачен намеренно («пока не готовы») — не возвращать без запроса.
- Контент банка заданий — только ФИПИ, демоверсии, общественное достояние, авторское; не копировать у конкурентов.
- Правила критериев сочинения/изложения сверены с демоверсиями ЕГЭ 2027; для ОГЭ часть правил по аналогии (помечено).

## Проверка перед коммитом
1. Синтаксис скриптов: извлечь inline `<script>` и прогнать `new Function(code)` в Node.
2. `python3 tests/harness.py` и `harness2.py` — без ошибок консоли и без NaN/undefined в тексте экранов (16 экзаменов).
3. После изменений схемы/функций — Supabase advisors (security).

## Права и деплой
- Пуш в `main` публикует сайт через GitHub Pages. Edge Functions деплоятся отдельно (Supabase CLI/MCP), не пушем.
- Автор и пользователь — один человек (учитель, эксперт ЕГЭ по литературе). Экономить токены, не пересказывать историю.

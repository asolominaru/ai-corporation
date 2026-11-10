# FINANCE.md — Financial Decision System

## 1. Главный принцип (§49)

Компания производит деньги, а не задачи. Система НЕ оптимизируется по количеству выполненных задач. Целевые метрики всей системы:

**REVENUE · GROSS PROFIT · CONTRIBUTION MARGIN · CASH · CUSTOMER VALUE · RETENTION · CAPITAL EFFICIENCY · FOUNDER ATTENTION EFFICIENCY**

Каждый отдел знает свой финансовый вклад. Каждый крупный проект имеет карточку экономики (`project_economics`): revenue potential, direct cost, AI cost, human hours, founder hours, expected margin, actual margin, payback, strategic value, probability of success.

## 2. Законченный продукт отдела

Не таблица расходов, а **Financial Decision System**, которая ежедневно/еженедельно отвечает на 11 вопросов:

1. Сколько у нас денег? 2. Откуда пришли? 3. На чём зарабатываем? 4. Где теряем? 5. Где растут расходы? 6. Какие продукты маржинальнее? 7. Какие клиенты прибыльные? 8. Какие проекты съедают время собственника? 9. Какие агенты/модели стоят слишком дорого? 10. Что остановить? 11. Куда выгоднее следующий рубль и следующий час?

Ответы — материализованные представления (SQL views) поверх таблиц + LLM-интерпретация в weekly pack. Вопросы 1–9 — детерминированные запросы, не LLM.

## 3. Роли → агенты (функции, не модели)

| Агент | Роли | Фаза |
|---|---|---|
| `ai-cfo` | CFO + FP&A + Investment Analyst | P2 (finance-lite), полный P5 |
| `management-accountant` | Management Accountant + Cost Controller | P5 |
| `unit-economics-analyst` | Unit Economics Analyst | P5 |
| `cash-controller` | Cash & Treasury Controller | P2 (13-недельный forecast) |
| `time-attention-analyst` | Time & Attention Analyst | P5 |
| `financial-auditor` | Financial Auditor (входит в Risk/Audit Council) | P5 |

На MVP роли CFO выполняет расширенный AI CEO + детерминированные отчёты; выделенный `ai-cfo` появляется, когда транзакций достаточно для полноценного FP&A.

## 4. Management P&L (§51)

Отдельный P&L по каждому business unit (Я / Проявленность / Ярдники / ВФОРУМЕ / R&D), строки: Revenue, COGS, AI Costs, Contractors, Human Labour, Marketing, Sales, Infrastructure → Gross Profit → Contribution Margin → Operating Profit. По каждой строке: план / факт / forecast.

Источник данных: `financial_transactions` (единая классификация, см. DATABASE.md §A) + `cost_logs` (AI costs пишутся автоматически из model_runs — это единственная полностью автоматическая строка на старте). Остальные строки на MVP — еженедельный импорт (csv/ручной ввод через форму), пока нет банковских интеграций. Честное ограничение: без интеграции с банком P&L на 80% ручной — это принято, автоматизация банковских фидов отложена.

## 5. 13-Week Cash Flow (§52)

Rolling forecast, 13 недель, еженедельный пересчёт (workflow, часть weekly meeting):

Строки: opening cash → confirmed inflows → probable inflows (взвешенные по probability из deals) → fixed costs → variable costs → payroll → taxes → AI/API (из cost_logs) → servers → marketing → contractors → investments → closing cash.

Три сценария: BASE / NEGATIVE / UPSIDE. Правило алерта: если в NEGATIVE closing cash любой недели < 1,5 × ежемесячных fixed costs → YELLOW; < 1,0 → RED + alert немедленно, не дожидаясь совещания.

## 6. Time & Attention Ledger (§53)

Таблица `time_entries`: кто (founder / top_manager / human / ai_run), по какому проекту, сколько часов, источник. Учёт времени собственника — обязателен; учёт остальных — по мере появления.

Как собирается на MVP без слежки: approvals, owner_decisions и owner_review в системе имеют timestamps — founder hours по ним считаются автоматически; остальное — 2-минутный еженедельный опрос в Telegram («чем занималась по проектам на этой неделе», кнопки + часы). Никаких трекеров — доверие важнее точности.

Главная метрика: **FOUNDER ATTENTION ROI = Contribution Margin / Founder Hours**.

Вывод системы (автоматически, в weekly pack):
```
Проект A: 12 ч внимания собственника → CM 900 000 ₽  (75 000 ₽/час)
Проект B: 41 ч → CM 180 000 ₽                        ( 4 390 ₽/час)
→ Вопрос: «Почему мы продолжаем B?» + recommendation (STOP/REDESIGN/DELEGATE)
```
Opportunity cost считается против лучшей альтернативы портфеля.

## 7. Unit Economics Engine (§54)

Автоматический расчёт (SQL + агрегации): CAC, LTV, LTV/CAC, CAC payback, ARPU, gross margin, contribution margin, retention, churn, expansion revenue, revenue per customer, **revenue per founder hour**, revenue per employee, **AI cost per outcome**.

Для сервисных продуктов (ретриты, группы, обучение): project margin, client margin, hours per delivery, margin per delivery hour.

На MVP реально вычислимы: CAC (при атрибуции контент→lead→deal), gross/contribution margin, AI cost per outcome, revenue per founder hour. LTV/retention требуют истории повторных продаж — честно помечаются «недостаточно данных» вместо выдуманных цифр.

## 8. Financial Kill Rules (§55)

У каждого проекта в `project_economics.kill_criteria` — машинно-проверяемые условия:

- после X тестов нет willingness to pay;
- CAC > допустимого порога;
- gross margin < порога;
- founder hours > порога на единицу результата;
- acquisition не масштабируется;
- infrastructure/API costs съедают economics;
- прогноз payback > допустимого горизонта.

Проверка — еженедельно (детерминированный код). Срабатывание → система обязана выдать рекомендацию одним из шести действий: **STOP / REDESIGN / RAISE PRICE / AUTOMATE / DELEGATE / SCALE** — с расчётом. Решение принимает собственник (decision в weekly pack).

## 9. Связь с остальной системой

- AI Costs: model_runs → cost_logs → P&L строка «AI Costs» — автоматически, по tenant/BU/project.
- Founder hours: approvals + weekly опрос → time_entries → FOUNDER ATTENTION ROI — в Control Tower, уровень 1.
- Kill rules срабатывания → инциденты типа `financial` → weekly pack + отдельный alert при RED.
- Cash flow риск → блок DECISIONS REQUIRED FROM ANASTASIA с готовыми опциями.

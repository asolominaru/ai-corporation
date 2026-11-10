# REVENUE_SYSTEM.md — от customer insight до денег

Центральный цикл компании (§71) — всё остальное ему обслуживает:

```
CUSTOMER → RESEARCH → INSIGHT → PRODUCT MEANING → POSITIONING
→ MARKETING → QUALIFIED DEMAND → SALES → MONEY → DELIVERY
→ CUSTOMER RESULT → RETENTION → MORE REVENUE → DATA
→ FINANCE / PRODUCT / R&D ↺
```

## 1. Customer & Market Intelligence (§56–57)

Функция существует ДО Marketing и Sales. Запрещённый вопрос: «как продать наш продукт?» — пока не доказано: КОМУ, КАКУЮ ПРОБЛЕМУ, НАСКОЛЬКО БОЛЬНО, КАК РЕШАЮТ СЕЙЧАС, ПОЧЕМУ ЭТОГО НЕДОСТАТОЧНО, СКОЛЬКО ГОТОВЫ ПЛАТИТЬ, КТО ПРИНИМАЕТ РЕШЕНИЕ, ЧТО МЕШАЕТ ПОКУПКЕ.

Источники: интервью, звонки продаж, переписки, анкеты, причины отказов, поведение пользователей, support, отзывы, поисковые запросы, конкуренты, публичные обсуждения.

Каждый insight — запись в `customer_insights` с обязательными полями: SOURCE, SEGMENT, PROBLEM, FREQUENCY, SEVERITY, CURRENT_SOLUTION, WILLINGNESS_TO_PAY, EVIDENCE_LEVEL. **Мнение одного клиента ≠ рынок**: `evidence_level` (single_case / few_cases / pattern) и приоритизация только при pattern.

Роли → агенты (P3–P5): `head-of-customer-intelligence` (Head + Insight Synthesizer), `market-researcher` (Market + Competitor + Pricing), `customer-researcher` (Customer Research + JTBD + Behaviour).

## 2. Product Meaning & Positioning (§58)

Роль Head of Positioning / Value Architect. Для каждого продукта — карточка `positioning`: ICP, JTBD, CORE PROBLEM, PROMISE, PROOF, DIFFERENTIATION, ALTERNATIVES, REASONS TO BELIEVE, VALUE METRIC, PRICE LOGIC.

Восемь вопросов, на которые карточка обязана отвечать: что продаём на самом деле; почему покупателю важно; почему сейчас; почему мы; с чем сравнивают; почему конкурент хуже/лучше; какую категорию создаём или занимаем; что покупатель скажет о нас одним предложением.

Без заполненной карточки продукт не получает marketing-задач. Это gate, а не рекомендация.

## 3. Marketing (§59)

Marketing не производит контент. **Marketing производит QUALIFIED DEMAND.** Контент — инструмент (и живёт в редакции, см. EDITORIAL.md). Законченный продукт отдела: QUALIFIED LEADS, MEETINGS, PIPELINE, REVENUE — не охваты и не посты. Обязательна связка attribution с CRM: каждый lead несёт источник (content_item_id / канал / кампания).

Роли (P3+): CMO, Head of Growth, Positioning Strategist, Demand Generation, Brand Director, Content & Editorial (уже есть в редакции), Performance Analyst, Partnerships, Marketing Analyst. На MVP это 1–2 агента: `growth-demand` + аналитика внутри него.

## 4. Sales (§60) и Value Selling (§61)

Sales — revenue department. Система продаж:

```
ICP → account research → trigger → contact → discovery → problem
→ economic value → proposal → objections → negotiation → contract
→ payment → expansion
```

**Value selling — обязательный расчёт перед предложением** (заполняется в `deals.value_hypothesis`):

| Поле | Вопрос |
|---|---|
| current_cost_of_problem | сколько проблема стоит клиенту сейчас (деньги) |
| lost_revenue | что клиент теряет, не решая |
| human_hours | сколько часов уходит |
| risk | цена риска |
| expected_value | ожидаемый эффект решения |
| payback | срок окупаемости для клиента |

Форма предложения: не «AI-платформа стоит 300 000», а «сейчас этот процесс стоит компании X млн / Y часов; после внедрения — Z; экономический эффект — N». Предложение без заполненной value hypothesis не уходит клиенту — workflow блокируется.

## 5. Revenue Operations (§62)

Единый RevOps layer: MARKETING + SALES + CLIENT SUCCESS + FINANCE. **Один customer ID, одна CRM, одна история**: first touch → content → lead → meeting → offer → payment → delivery → renewal → upsell.

Технически уже заложено в ER-модели: `customers` — единственный источник правды о клиенте; `leads.content_item_id` — атрибуция маркетинга; `deals` — деньги; `content_items` ↔ `leads` ↔ `deals` образуют цепочку без дублей. Запрещено заводить параллельные таблицы клиентов в отделах — нарушение считается архитектурным дефектом на review.

## 6. Топ-команда (§63)

Каждая роль имеет «главный продукт» — законченный результат, по которому её судят:

| Роль | Главный продукт | Ключевые KPI |
|---|---|---|
| AI CEO / GM | достижение целей компании | revenue, profit, cash, return on resources |
| CFO | финансово устойчивый прибыльный бизнес | cash runway, margin, forecast accuracy |
| CRO / Revenue Director | предсказуемая выручка | pipeline coverage, win rate, forecast accuracy |
| CMO | предсказуемый поток квалифицированного спроса | qualified leads, CAC, pipeline from marketing |
| CPO | продукт, за который платят и продолжают платить | retention, activation, WTP evidence |
| CTO | работающая система, быстро создающая ценность | release success rate, time to production, AI cost |
| COO | предсказуемое исполнение | SLA, blocked tasks, cycle time |
| CISO | управляемый уровень риска | incidents, unresolved findings, alert latency |
| Chief Decision Scientist | решения на вероятностях и данных | калибровка прогнозов, decision quality |
| Chief of Staff / Orchestrator | ни одно решение не теряется между отделами | decision follow-through rate |

На MVP один агент может держать несколько ролей (AI CEO + Chief of Staff — один агент `ai-ceo` + `operations-controller`), но «главный продукт» роли не размывается: KPI считается по роли, а не по агенту.

## 7. Money-first порядок совещания (§64)

См. GOVERNANCE.md §2 — порядок повестки изменён: CASH → REVENUE/PROFIT → PIPELINE → CUSTOMER SIGNALS → PRODUCT → MARKETING → DELIVERY → DEVELOPMENT → SECURITY → R&D → CAPITAL & ATTENTION ALLOCATION → OWNER DECISIONS. Главный вопрос недели: **«Где следующий лучший рубль и следующий лучший час создадут максимальную ценность?»**

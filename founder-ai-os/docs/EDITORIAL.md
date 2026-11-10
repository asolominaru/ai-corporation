# EDITORIAL.md — AI-редакция «Сила малых групп»

Бизнес-приоритет №1 (P1 в roadmap). Проект относится к направлению ПРОЯВЛЕННОСТЬ. Это полноценная редакция, а не демонстрация агентов.

## 1. Цель

Постоянно превращать профессиональный опыт Анастасии в сильный авторский контент, который формирует позиционирование и интеллектуальную территорию, привлекает собственников и бизнес-сообщества, приводит клиентов на ретриты, группы и обучение, создаёт материалы будущей книги и методологическую базу, генерирует лиды в CRM.

## 2. Источники и контур конфиденциальности

Источники: Google Drive, голосовые заметки, транскрипты, встречи форум-групп, ретриты, анкеты участников, супервизии, методологические материалы, мысли Анастасии, старые публикации, исследования, кейсы, вопросы участников, конфликты в группах, обратная связь, международные исследования (YPO/EO и смежные практики, психология малых групп, оргпсихология, групповая динамика, product/management research).

**Классификация при ingestion (обязательное поле `privacy_class`):**

| Класс | Примеры | Правило |
|---|---|---|
| public | старые публикации, открытые исследования | любые модели |
| internal | методология, заметки Анастасии, анкеты (обезличенные) | утверждённые API-провайдеры |
| confidential | транскрипты форум-групп, супервизии, кейсы участников | **обезличивание ДО любого LLM-вызова**; модели только privacy_class=confidential-совместимые; публикация данных участника/группы — только с явным разрешением (фиксируется в CRM) |

Обезличивание — детерминированный пайплайн (NER + словари имён + ручная разметка), а не «промпт про анонимизацию». LLM получает уже обезличенный текст. Это принципиально: confidentiality enforced by pipeline, not by prompt.

## 3. Роли — это функции, а не обязательно модели

13 ролей: Editor-in-Chief, Knowledge Miner, Story Miner, Researcher, Methodology Agent, Writer, Editor, Anastasia Voice Agent, Fact Checker, Content Critic, Ethics/Confidentiality Reviewer, Distribution Agent, Growth Analyst.

Маппинг на 7 агентов (разделение контекста и проверки сохраняется, где критично):

| Агент | Роли | Почему вместе / почему раздельно |
|---|---|---|
| `editor-in-chief` | Editor-in-Chief / Content Director | приоритеты, редакционный календарь, приёмка |
| `knowledge-miner` | Knowledge Miner + Story Miner + Researcher | одна функция добычи: факты, истории, исследования |
| `smg-writer` | Writer + Methodology Agent | черновик + методологическая точность |
| `anastasia-voice` | Anastasia Voice Agent + Editor | стилистическая правка голосом Анастасии |
| `quality-critic` | Content Critic + Fact Checker + anti-AI filter | независимая проверка качества; **не та модель, что писала** |
| `confidentiality-reviewer` | Ethics / Confidentiality Reviewer | **отдельный агент всегда**: veto-право, неподотчётен редактору |
| `distribution-growth` | Distribution Agent + Growth Analyst | публикация, CTA, атрибуция, аналитика |

Правило независимости: писатель (`smg-writer`/`anastasia-voice`), критик (`quality-critic`) и проверяющий конфиденциальность (`confidentiality-reviewer`) — три раздельных контура; veto confidentiality-reviewer'а не отменяется никем, кроме собственника.

## 4. Конвейер

```
RAW KNOWLEDGE → INGESTION → CLASSIFICATION (privacy_class, тема, тип)
→ INSIGHT MINING → STORY MINING → RESEARCH → IDEA
→ EDITORIAL PRIORITY (content score) → DRAFT → ANASTASIA VOICE
→ CRITIC → FACT CHECK → CONFIDENTIALITY CHECK → APPROVAL (owner)
→ PUBLICATION → DISTRIBUTION → CTA → CRM → ANALYTICS
```

Workflow: [workflows/editorial-pipeline.yaml](../workflows/editorial-pipeline.yaml).

Approval собственника — обязательный шаг перед публикацией (категория `public_statement`). Редакция готовит материал «под ключ», собственник тратит минуты на approve/edit/reject, а не редактирует сырьё.

## 5. Редакционный календарь

Статусы материала (`content_items.status`, enum):

`idea → research → approved_topic → draft → editing → fact_check → confidentiality_review → owner_review → scheduled → published → measuring → repurpose`

Переходы — только через orchestrator (каждый переход = task или review-результат, всё в аудите). Календарь визуализируется в Control Tower (уровень departments → content).

## 6. Content Score

Для каждого материала на этапе EDITORIAL PRIORITY и после CRITIC:

| Ось | Шкала |
|---|---|
| Originality | 0–10 |
| Expertise Depth | 0–10 |
| Evidence Quality | 0–10 |
| Relevance | 0–10 |
| Emotional Impact | 0–10 |
| Brand Fit | 0–10 |
| Commercial Potential | 0–10 |
| Reputational Risk | 0–10 (обратная: ≥7 → обязательный owner review независимо от остального) |

Score — инструмент приоритизации, не замена человека. Итоговое решение о публикации — всегда за собственником.

## 7. Anti-AI filter

Автоматическая проверка (quality-critic) по чек-листу: ИИ-канцелярит, штампы, банальные выводы, ненужные вводные, искусственный пафос, чрезмерные списки, повторы, нехарактерная для Анастасии лексика, недоказанные заявления.

Реализация: детерминированные проверки (словари штампов, статистика списков/повторов — обычный код) + LLM-оценка (лексика, пафос, банальность). Content Critic имеет право вернуть материал на переработку (статус → `draft`, цикл rework, максимум 2 — дальше эскалация к editor-in-chief).

Калибровка голоса: корпус эталонных текстов Анастасии (10–20 лучших публикаций) лежит в knowledge base с acl_tag `voice-reference`; voice-агент и critic используют его как референс.

## 8. Content Flywheel

Один сильный источник превращается в серию: Telegram post → длинная статья → серия постов → кейсовый материал → короткое видео → сценарий выступления → фрагмент книги → обучающий материал → commercial insight → R&D hypothesis.

Механика: у каждого `content_item` есть `source_id` и `parent_id`. Статус `repurpose` = материал возвращается в календарь как источник нового формата. Метрика flywheel: `assets_per_source` — сколько опубликованных единиц родил один источник (цель ≥ 3).

## 9. Завершённый продукт материала

Не «ИИ написал пост», а **опубликованный качественный материал** с заполненной карточкой:

SOURCE, THEME, AUDIENCE, PRODUCT (ретрит/группа/обучение/книга), FUNNEL_STAGE, CTA, PUBLICATION_DATE, CHANNEL → и после публикации: LEADS, REACTIONS, MEETINGS, PIPELINE, SALES + сохранённый интеллектуальный материал в Knowledge Base.

Атрибуция: каждый CTA — UTM/помеченная ссылка или кодовое слово; lead в CRM несёт `content_item_id`. KPI редакции — leads/meetings/pipeline/revenue, не количество постов.

## 10. MVP-объём редакции (P1)

Честно о том, что входит, а что нет:

**Входит:** ingestion из Google Drive + ручная загрузка транскриптов; обезличивание; классификация; календарь со всеми статусами; конвейер до owner approval; публикация в Telegram (полуавтомат — по approve собственника); карточка результата; базовый content score; anti-AI filter v1.

**Не входит:** авто-публикация в другие каналы, видео, книга как отдельный трек, полная revenue-атрибуция (сначала CTA→lead→CRM, атрибуция продаж — в P3 вместе с Sales). Полный knowledge layer с pgvector — упрощённо: ingestion + metadata + поиск по тегам; embeddings добавляются, когда объём источников превысит возможности тегового поиска.

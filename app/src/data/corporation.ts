export interface Department {
  id: string
  name: string
  nameEn: string
  /** hsl triple, e.g. "43 90% 55%" */
  color: string
}

export interface Agent {
  id: string
  name: string
  role: string
  roleEn: string
  model: string
  departmentId: string
  stageName: string
  stageNameEn: string
  x: number
  y: number
}

export type TaskTypeId = 'rnd' | 'product' | 'marketing'

export interface TaskType {
  id: TaskTypeId
  label: string
  labelEn: string
  route: string[]
  presets: string[]
  presetsEn: string[]
}

export const ENTRY_POINT = { x: 480, y: 6 }

export const DEPARTMENTS: Department[] = [
  { id: 'dir', name: 'Дирекция', nameEn: 'Directorate', color: '43 90% 55%' },
  { id: 'rnd', name: 'R&D · Новые продукты', nameEn: 'R&D · New products', color: '199 89% 60%' },
  { id: 'dev', name: 'Продукт', nameEn: 'Product', color: '160 84% 45%' },
  { id: 'marketing', name: 'Маркетинг', nameEn: 'Marketing', color: '262 83% 66%' },
  { id: 'qa', name: 'Контроль качества', nameEn: 'Quality Control', color: '346 77% 60%' },
  { id: 'delivery', name: 'Доставка', nameEn: 'Delivery', color: '187 80% 50%' },
]

/** Продуктовые линии компании, которые дорабатывает отдел «Продукт» */
export const PRODUCTS = [
  { id: 'yardniki', name: 'ЯРДНИКИ', nameEn: 'YARDNIKI' },
  { id: 'manifest', name: 'ПРОЯВЛЕННОСТЬ', nameEn: 'VISIBILITY' },
  { id: 'brand', name: 'BRAND FACTORY', nameEn: 'BRAND FACTORY' },
  { id: 'repost', name: 'РЕПОСТ', nameEn: 'REPOST' },
] as const

export const CEO = {
  name: 'Анастасия Соломина',
  nameEn: 'Anastasia Solomina',
  role: 'CEO · основатель',
  roleEn: 'CEO · founder',
}

export const AGENTS: Agent[] = [
  { id: 'ceo', name: 'КОРД', role: 'ИИ-советник директора', roleEn: 'AI advisor to the CEO', model: 'Kimi K2', departmentId: 'dir', stageName: 'декомпозиция задачи', stageNameEn: 'task decomposition', x: 480, y: 92 },
  { id: 'scout', name: 'СКАУТ', role: 'Разведка трендов и рынков', roleEn: 'Trend & market scout', model: 'Perplexity Sonar Pro', departmentId: 'rnd', stageName: 'веб-разведка', stageNameEn: 'web reconnaissance', x: 148, y: 140 },
  { id: 'researcher', name: 'ИСКАТЕЛЬ', role: 'Продуктовый исследователь', roleEn: 'Product researcher', model: 'GPT-5', departmentId: 'rnd', stageName: 'сбор информации', stageNameEn: 'information gathering', x: 300, y: 218 },
  { id: 'analyst', name: 'ВЕСТА', role: 'Аналитик монетизации', roleEn: 'Monetization analyst', model: 'Claude Sonnet 4.5', departmentId: 'rnd', stageName: 'анализ данных', stageNameEn: 'data analysis', x: 172, y: 330 },
  { id: 'arch', name: 'АРХИТЕКТОР', role: 'Системный архитектор', roleEn: 'System architect', model: 'GPT-5.1 Codex', departmentId: 'dev', stageName: 'проектирование решения', stageNameEn: 'solution design', x: 660, y: 218 },
  { id: 'eng', name: 'ИНЖЕНЕР', role: 'Ведущий разработчик', roleEn: 'Lead engineer', model: 'Qwen3-Coder', departmentId: 'dev', stageName: 'реализация', stageNameEn: 'implementation', x: 788, y: 330 },
  { id: 'copy', name: 'АВТОР', role: 'Копирайтер', roleEn: 'Copywriter', model: 'Gemini 3 Pro', departmentId: 'marketing', stageName: 'создание текста', stageNameEn: 'copywriting', x: 330, y: 430 },
  { id: 'edit', name: 'РЕДАКТОР', role: 'Шеф-редактор', roleEn: 'Editor-in-chief', model: 'Claude Haiku 4.5', departmentId: 'marketing', stageName: 'редактура и вычитка', stageNameEn: 'editing & proofreading', x: 470, y: 386 },
  { id: 'qa', name: 'РЕЦЕНЗЕНТ', role: 'Контролёр качества', roleEn: 'Quality controller', model: 'DeepSeek R2', departmentId: 'qa', stageName: 'проверка качества', stageNameEn: 'quality check', x: 600, y: 470 },
  { id: 'rel', name: 'РЕЛИЗ', role: 'Релиз-менеджер', roleEn: 'Release manager', model: 'Llama 4 Maverick', departmentId: 'delivery', stageName: 'публикация результата', stageNameEn: 'publishing result', x: 480, y: 566 },
]

export const AGENT_BY_ID: Record<string, Agent> = Object.fromEntries(AGENTS.map((a) => [a.id, a]))
export const DEPT_BY_ID: Record<string, Department> = Object.fromEntries(DEPARTMENTS.map((d) => [d.id, d]))

export const TASK_TYPES: TaskType[] = [
  {
    id: 'rnd',
    label: 'R&D · новый продукт',
    labelEn: 'R&D · new product',
    route: ['ceo', 'scout', 'researcher', 'analyst', 'qa', 'rel'],
    presets: [
      'Новая обучающая платформа — оценка монетизации',
      'Сервис по подписке: спрос и модель дохода',
      'Обучающий продукт: упаковка и запуск',
    ],
    presetsEn: [
      'New learning platform — monetization estimate',
      'Subscription service: demand and revenue model',
      'Educational product: packaging and launch',
    ],
  },
  {
    id: 'product',
    label: 'Доработка продукта',
    labelEn: 'Product upgrade',
    route: ['ceo', 'arch', 'eng', 'qa', 'rel'],
    presets: [
      'Новая фича для удержания клиентов',
      'Улучшение воронки оплаты',
      'Рефакторинг ключевого модуля',
    ],
    presetsEn: [
      'New customer retention feature',
      'Payment funnel improvement',
      'Key module refactoring',
    ],
  },
  {
    id: 'marketing',
    label: 'Маркетинг',
    labelEn: 'Marketing',
    route: ['ceo', 'copy', 'edit', 'qa', 'rel'],
    presets: [
      'Запуск рекламной кампании продукта',
      'Серия постов для соцсетей',
      'Продающая лендинг-страница',
    ],
    presetsEn: [
      'Product ad campaign launch',
      'Social media post series',
      'Sales landing page',
    ],
  },
]

/** Все рёбра, используемые маршрутами задач */
export const EDGES: Array<{ from: string; to: string }> = (() => {
  const set = new Set<string>()
  const edges: Array<{ from: string; to: string }> = []
  for (const t of TASK_TYPES) {
    for (let i = 0; i < t.route.length - 1; i++) {
      const key = `${t.route[i]}->${t.route[i + 1]}`
      if (!set.has(key)) {
        set.add(key)
        edges.push({ from: t.route[i], to: t.route[i + 1] })
      }
    }
  }
  return edges
})()

export interface Vec {
  x: number
  y: number
}

export function nodePos(agentId: string | null): Vec {
  if (!agentId) return ENTRY_POINT
  const a = AGENT_BY_ID[agentId]
  return { x: a.x, y: a.y }
}

/** Контрольная точка квадратичной кривой: смещение перпендикулярно середине */
export function edgeControl(p0: Vec, p1: Vec): Vec {
  const mx = (p0.x + p1.x) / 2
  const my = (p0.y + p1.y) / 2
  const dx = p1.x - p0.x
  const dy = p1.y - p0.y
  const len = Math.hypot(dx, dy) || 1
  const k = len * 0.14
  return { x: mx - (dy / len) * k, y: my + (dx / len) * k }
}

export function bezierAt(p0: Vec, c: Vec, p1: Vec, t: number): Vec {
  const u = 1 - t
  return {
    x: u * u * p0.x + 2 * u * t * c.x + t * t * p1.x,
    y: u * u * p0.y + 2 * u * t * c.y + t * t * p1.y,
  }
}

export function edgePathD(p0: Vec, p1: Vec): string {
  const c = edgeControl(p0, p1)
  return `M ${p0.x} ${p0.y} Q ${c.x} ${c.y} ${p1.x} ${p1.y}`
}

/** Системные промпты агентов для режима реальных моделей */
export const SYSTEM_PROMPTS: Record<string, string> = {
  ceo: 'Ты — ИИ-советник директора компании (основатель и CEO — Анастасия Соломина). Декомпозируй поступившую задачу: сформулируй цель, ожидаемый вклад в монетизацию и план из 3–4 шагов для команды.',
  scout: 'Ты — разведчик трендов R&D-отдела. Найди в интернете свежее по задаче: 3–5 пунктов о рынке, конкурентах и моделях монетизации (платформы, сервисы, обучающие продукты).',
  researcher: 'Ты — продуктовый исследователь R&D-отдела. Собери и структурируй информацию по задаче: целевая аудитория, форматы продуктов, что уже покупают.',
  analyst: 'Ты — аналитик монетизации R&D-отдела. Оцени собранные данные: потенциал дохода, модели монетизации, риски и что запустить первым.',
  arch: 'Ты — системный архитектор ИИ-корпорации. Спроектируй техническое решение: компоненты, интерфейсы, ограничения.',
  eng: 'Ты — ведущий разработчик ИИ-корпорации. Опиши реализацию: ключевая логика, фрагменты кода, что готово к проверке.',
  copy: 'Ты — копирайтер ИИ-корпорации. Напиши черновик текста по задаче: заголовок и основная часть.',
  edit: 'Ты — шеф-редактор ИИ-корпорации. Отредактируй текст: стиль, точность, структура, логика подачи.',
  qa: 'Ты — контролёр качества ИИ-корпорации. Проверь результат предыдущих этапов, найди ошибки и дай вердикт: «принято» или «доработать» с обоснованием.',
  rel: 'Ты — релиз-менеджер ИИ-корпорации. Подготовь итог к публикации: финальное резюме всей проделанной работы.',
}

export function buildStagePrompt(agentId: string, title: string, prevOutput: string | null): string {
  const stage = AGENT_BY_ID[agentId].stageName
  return [
    `Задача корпорации: «${title}»`,
    `Твой этап: ${stage}.`,
    prevOutput
      ? `Результат предыдущего этапа:\n${prevOutput}`
      : 'Это первый этап — контекста от коллег пока нет.',
    'Ответь кратко (2–4 предложения): что конкретно ты сделал на своём этапе.',
  ].join('\n')
}

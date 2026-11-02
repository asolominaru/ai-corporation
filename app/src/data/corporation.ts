export interface Department {
  id: string
  name: string
  /** hsl triple, e.g. "43 90% 55%" */
  color: string
}

export interface Agent {
  id: string
  name: string
  role: string
  model: string
  departmentId: string
  stageName: string
  x: number
  y: number
}

export type TaskTypeId = 'research' | 'dev' | 'content'

export interface TaskType {
  id: TaskTypeId
  label: string
  route: string[]
  presets: string[]
}

export const ENTRY_POINT = { x: 480, y: 6 }

export const DEPARTMENTS: Department[] = [
  { id: 'dir', name: 'Дирекция', color: '43 90% 55%' },
  { id: 'analytics', name: 'Аналитика', color: '199 89% 60%' },
  { id: 'dev', name: 'Разработка', color: '160 84% 45%' },
  { id: 'content', name: 'Контент', color: '262 83% 66%' },
  { id: 'qa', name: 'Контроль качества', color: '346 77% 60%' },
  { id: 'delivery', name: 'Доставка', color: '187 80% 50%' },
]

export const AGENTS: Agent[] = [
  { id: 'ceo', name: 'КОРД', role: 'Директор-координатор', model: 'Kimi K2', departmentId: 'dir', stageName: 'декомпозиция задачи', x: 480, y: 92 },
  { id: 'scout', name: 'СКАУТ', role: 'Веб-разведчик', model: 'Perplexity Sonar Pro', departmentId: 'analytics', stageName: 'веб-разведка', x: 148, y: 140 },
  { id: 'researcher', name: 'ИСКАТЕЛЬ', role: 'Исследователь', model: 'GPT-5', departmentId: 'analytics', stageName: 'сбор информации', x: 300, y: 218 },
  { id: 'analyst', name: 'ВЕСТА', role: 'Аналитик', model: 'Claude Sonnet 4.5', departmentId: 'analytics', stageName: 'анализ данных', x: 172, y: 330 },
  { id: 'arch', name: 'АРХИТЕКТОР', role: 'Системный архитектор', model: 'GPT-5.1 Codex', departmentId: 'dev', stageName: 'проектирование решения', x: 660, y: 218 },
  { id: 'eng', name: 'ИНЖЕНЕР', role: 'Ведущий разработчик', model: 'Qwen3-Coder', departmentId: 'dev', stageName: 'реализация', x: 788, y: 330 },
  { id: 'copy', name: 'АВТОР', role: 'Копирайтер', model: 'Gemini 3 Pro', departmentId: 'content', stageName: 'создание текста', x: 330, y: 430 },
  { id: 'edit', name: 'РЕДАКТОР', role: 'Шеф-редактор', model: 'Claude Haiku 4.5', departmentId: 'content', stageName: 'редактура и вычитка', x: 470, y: 386 },
  { id: 'qa', name: 'РЕЦЕНЗЕНТ', role: 'Контролёр качества', model: 'DeepSeek R2', departmentId: 'qa', stageName: 'проверка качества', x: 600, y: 470 },
  { id: 'rel', name: 'РЕЛИЗ', role: 'Релиз-менеджер', model: 'Llama 4 Maverick', departmentId: 'delivery', stageName: 'публикация результата', x: 480, y: 566 },
]

export const AGENT_BY_ID: Record<string, Agent> = Object.fromEntries(AGENTS.map((a) => [a.id, a]))
export const DEPT_BY_ID: Record<string, Department> = Object.fromEntries(DEPARTMENTS.map((d) => [d.id, d]))

export const TASK_TYPES: TaskType[] = [
  {
    id: 'research',
    label: 'Исследование',
    route: ['ceo', 'scout', 'researcher', 'analyst', 'qa', 'rel'],
    presets: [
      'Обзор рынка ИИ-агентов за Q3',
      'Сравнение конкурентов по ценам',
      'Анализ отзывов клиентов за месяц',
    ],
  },
  {
    id: 'dev',
    label: 'Разработка',
    route: ['ceo', 'arch', 'eng', 'qa', 'rel'],
    presets: [
      'Микросервис уведомлений в Telegram',
      'Оптимизация времени ответа API',
      'Дашборд метрик для отдела продаж',
    ],
  },
  {
    id: 'content',
    label: 'Контент',
    route: ['ceo', 'copy', 'edit', 'qa', 'rel'],
    presets: [
      'Статья о запуске нового продукта',
      'Серия постов для соцсетей',
      'Пресс-релиз к годовщине компании',
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
  ceo: 'Ты — директор-координатор ИИ-корпорации. Декомпозируй поступившую задачу: сформулируй цель, критерии результата и план из 3–4 шагов для команды.',
  scout: 'Ты — веб-разведчик ИИ-корпорации. Найди в интернете свежие факты по задаче: 3–5 пунктов с указанием, что подтверждено источниками.',
  researcher: 'Ты — исследователь ИИ-корпорации. Собери и структурируй ключевую информацию по задаче, отметь пробелы в данных.',
  analyst: 'Ты — аналитик ИИ-корпорации. Проанализируй собранные данные: выводы, закономерности, риски.',
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

export type Lang = 'ru' | 'en'

interface Strings {
  subtitle: string
  systemsOk: string
  tasksInFlight: string
  agentsBusy: string
  completed: string
  avgCycle: string
  orgChart: (n: number) => string
  eventLog: string
  clear: string
  inbox: string
  simulation: string
  liveModels: string
  examplePrefix: string
  launchTask: string
  autoOn: string
  autoOff: string
  gatewayOnline: string
  gatewayOffline: string
  gatewayChecking: string
  hintSim: string
  hintRealBlocked: string
  hintReal: string
  idle: string
  department: string
  modelLabel: string
  status: string
  busyTask: (id: number) => string
  free: string
  modelThinking: string
  closeAgent: string
  currentStage: (stage: string) => string
  canvasAria: string
  // журнал
  logStarted: string
  logModeSim: string
  logModeReal: string
  logNewTask: (id: number, title: string, routeLabel: string) => string
  logAccepted: (agent: string, id: number, stage: string) => string
  logError: (agent: string, id: number, msg: string) => string
  logStageDone: (agent: string, stage: string, next: string) => string
  logTransfer: (agent: string, id: number, next: string) => string
  logDone: (id: number, sec: string) => string
  logCleared: string
  logAwaitApproval: (id: number, title: string) => string
  logRework: (id: number, agent: string) => string
  approvalTitle: string
  approve: string
  rework: string
  taskWord: string
  kanbanInProgress: string
  kanbanApproval: string
  kanbanDone: string
  kanbanEmpty: string
}

export const STRINGS: Record<Lang, Strings> = {
  ru: {
    subtitle: 'центр управления агентами',
    systemsOk: 'Системы в норме',
    tasksInFlight: 'задач в работе',
    agentsBusy: 'агентов занято',
    completed: 'выполнено',
    avgCycle: 'средний цикл',
    orgChart: (n) => `Оргструктура · ${n} агентов`,
    eventLog: 'Журнал событий',
    clear: 'Очистить',
    inbox: 'ВХОД',
    simulation: 'Симуляция',
    liveModels: 'Реальные модели',
    examplePrefix: 'Например',
    launchTask: 'Запустить задачу',
    autoOn: 'Авто-режим вкл',
    autoOff: 'Авто-режим выкл',
    gatewayOnline: 'шлюз :4000 онлайн',
    gatewayOffline: 'шлюз недоступен',
    gatewayChecking: 'проверка шлюза…',
    hintSim:
      'Симуляция: корпорация показывает поток задач без реальных вызовов. Авто-режим берёт задачи из очереди каждые несколько секунд.',
    hintRealBlocked:
      'Шлюз не отвечает. Запустите его командой: litellm-server/start.sh — и вставьте ключи в litellm-server/.env',
    hintReal:
      'Реальный режим: каждый этап выполняет настоящая модель через LiteLLM-шлюз. Ответы агентов появляются в журнале. Каждый запуск тратит токены.',
    idle: 'свободен',
    department: 'Отдел',
    modelLabel: 'Модель',
    status: 'Статус',
    busyTask: (id) => `Занят · задача #${id}`,
    free: 'Свободен',
    modelThinking: 'модель думает…',
    closeAgent: 'Закрыть карточку агента',
    currentStage: (stage) => `этап «${stage}»`,
    canvasAria: 'Схема потока задач между агентами ИИ-корпорации',
    logStarted: 'Центр управления запущен. Все агенты на связи.',
    logModeSim: 'Включён режим симуляции.',
    logModeReal:
      'Режим реальных моделей: этапы выполняют настоящие LLM через шлюз :4000. Авто-режим выключен во избежание лишних расходов.',
    logNewTask: (id, title, routeLabel) => `Новая задача #${id}: «${title}» — маршрут: ${routeLabel}`,
    logAccepted: (agent, id, stage) => `${agent} принял задачу #${id} — этап «${stage}»`,
    logError: (agent, id, msg) => `${agent} не смог выполнить этап (задача #${id}): ${msg}`,
    logStageDone: (agent, stage, next) => `${agent} завершил «${stage}», передаёт → ${next}`,
    logTransfer: (agent, id, next) => `${agent} передаёт задачу #${id} → ${next}`,
    logDone: (id, sec) => `Задача #${id} принята CEO за ${sec} с цикла — результат опубликован`,
    logCleared: 'Журнал очищен.',
    logAwaitApproval: (id, title) => `Задача #${id} «${title}» прошла конвейер — ждёт финальной приёмки у CEO`,
    logRework: (id, agent) => `Задача #${id} возвращена CEO на доработку → ${agent}`,
    approvalTitle: 'Финальная приёмка · CEO',
    approve: 'Принять',
    rework: 'На доработку',
    taskWord: 'Текст задачи',
    kanbanInProgress: 'В работе',
    kanbanApproval: 'На приёмке · CEO',
    kanbanDone: 'Выполнено',
    kanbanEmpty: 'пусто',
  },
  en: {
    subtitle: 'agent control center',
    systemsOk: 'All systems nominal',
    tasksInFlight: 'tasks in flight',
    agentsBusy: 'agents busy',
    completed: 'completed',
    avgCycle: 'avg cycle',
    orgChart: (n) => `Org chart · ${n} agents`,
    eventLog: 'Event log',
    clear: 'Clear',
    inbox: 'INBOX',
    simulation: 'Simulation',
    liveModels: 'Live models',
    examplePrefix: 'E.g.',
    launchTask: 'Launch task',
    autoOn: 'Auto on',
    autoOff: 'Auto off',
    gatewayOnline: 'gateway :4000 online',
    gatewayOffline: 'gateway offline',
    gatewayChecking: 'checking gateway…',
    hintSim:
      'Simulation: the corporation demonstrates the task flow without real API calls. Auto mode picks a task from the queue every few seconds.',
    hintRealBlocked:
      'Gateway is not responding. Start it with: litellm-server/start.sh — and add your keys to litellm-server/.env',
    hintReal:
      'Live mode: every stage is executed by a real model through the LiteLLM gateway. Agent replies appear in the log. Each run spends tokens.',
    idle: 'idle',
    department: 'Department',
    modelLabel: 'Model',
    status: 'Status',
    busyTask: (id) => `Busy · task #${id}`,
    free: 'Idle',
    modelThinking: 'model is thinking…',
    closeAgent: 'Close agent card',
    currentStage: (stage) => `stage "${stage}"`,
    canvasAria: 'Task flow between AI corporation agents',
    logStarted: 'Control center started. All agents online.',
    logModeSim: 'Simulation mode enabled.',
    logModeReal:
      'Live model mode: stages are executed by real LLMs via the :4000 gateway. Auto mode is off to avoid unnecessary spend.',
    logNewTask: (id, title, routeLabel) => `New task #${id}: "${title}" — route: ${routeLabel}`,
    logAccepted: (agent, id, stage) => `${agent} accepted task #${id} — stage "${stage}"`,
    logError: (agent, id, msg) => `${agent} failed the stage (task #${id}): ${msg}`,
    logStageDone: (agent, stage, next) => `${agent} finished "${stage}", handing off → ${next}`,
    logTransfer: (agent, id, next) => `${agent} passes task #${id} → ${next}`,
    logDone: (id, sec) => `Task #${id} accepted by the CEO after a ${sec}s cycle — result published`,
    logCleared: 'Log cleared.',
    logAwaitApproval: (id, title) => `Task #${id} "${title}" passed the pipeline — awaiting final acceptance by the CEO`,
    logRework: (id, agent) => `Task #${id} sent back by the CEO → ${agent}`,
    approvalTitle: 'Final acceptance · CEO',
    approve: 'Accept',
    rework: 'Send back',
    taskWord: 'Task text',
    kanbanInProgress: 'In progress',
    kanbanApproval: 'CEO acceptance',
    kanbanDone: 'Done',
    kanbanEmpty: 'empty',
  },
}

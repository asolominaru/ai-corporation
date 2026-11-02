import { useCallback, useEffect, useRef, useState } from 'react'
import {
  AGENT_BY_ID,
  DEPT_BY_ID,
  SYSTEM_PROMPTS,
  TASK_TYPES,
  buildStagePrompt,
  type TaskTypeId,
} from '@/data/corporation'
import { callAgent, checkGateway } from '@/lib/gateway'

export type Mode = 'sim' | 'real'

export interface ActiveTask {
  id: number
  title: string
  type: TaskTypeId
  route: string[]
  /** индекс агента, который сейчас работает / к которому летит пакет */
  hopIndex: number
  phase: 'transfer' | 'work'
  from: string | null
  t0: number
  duration: number
  createdAt: number
  /** real-режим: запрос к модели уже отправлен */
  callStarted?: boolean
}

export interface LogEntry {
  id: number
  at: number
  agentId: string | null
  kind: 'in' | 'step' | 'done' | 'error' | 'system'
  text: string
}

export interface Metrics {
  launched: number
  done: number
  avgMs: number
}

interface RealCall {
  status: 'ok' | 'error'
  text: string
}

const TRANSFER_MS = 750
const MAX_LOG = 80
const AUTO_EVERY_MS = 8000
const AUTO_MAX_ACTIVE = 3

function workDuration(): number {
  return 1400 + Math.random() * 1400
}

export function useCorporationSim() {
  const [now, setNow] = useState(() => Date.now())
  const [tasks, setTasks] = useState<ActiveTask[]>([])
  const [log, setLog] = useState<LogEntry[]>([
    {
      id: 0,
      at: Date.now(),
      agentId: null,
      kind: 'system',
      text: 'Центр управления запущен. Все агенты на связи.',
    },
  ])
  const [metrics, setMetrics] = useState<Metrics>({ launched: 0, done: 0, avgMs: 0 })
  const [auto, setAuto] = useState(true)
  const [mode, setModeState] = useState<Mode>('sim')
  const [proxyOk, setProxyOk] = useState<boolean | null>(null)

  const idRef = useRef(1)
  const taskIdRef = useRef(1)
  const lastAutoRef = useRef(Date.now())
  const durationsRef = useRef<number[]>([])
  const tasksRef = useRef<ActiveTask[]>([])
  const realCallsRef = useRef<Map<number, RealCall>>(new Map())
  const lastOutputRef = useRef<Map<number, string>>(new Map())
  const modeRef = useRef<Mode>('sim')

  const pushLog = useCallback((entry: Omit<LogEntry, 'id' | 'at'>) => {
    setLog((prev) => [{ ...entry, id: idRef.current++, at: Date.now() }, ...prev].slice(0, MAX_LOG))
  }, [])

  const setMode = useCallback(
    (m: Mode) => {
      setModeState(m)
      modeRef.current = m
      if (m === 'real') {
        setAuto(false)
        pushLog({
          agentId: null,
          kind: 'system',
          text: 'Режим реальных моделей: этапы выполняют настоящие LLM через шлюз :4000. Авто-режим выключен во избежание лишних расходов.',
        })
      } else {
        pushLog({ agentId: null, kind: 'system', text: 'Включён режим симуляции.' })
      }
    },
    [pushLog],
  )

  // проверка доступности шлюза в real-режиме
  useEffect(() => {
    if (mode !== 'real') return
    let stop = false
    const probe = async () => {
      const ok = await checkGateway()
      if (!stop) setProxyOk(ok)
    }
    probe()
    const iv = setInterval(probe, 10000)
    return () => {
      stop = true
      clearInterval(iv)
    }
  }, [mode])

  const launchTask = useCallback(
    (title: string, type: TaskTypeId) => {
      const t = TASK_TYPES.find((x) => x.id === type)
      if (!t) return
      const nowMs = Date.now()
      const id = taskIdRef.current++
      const task: ActiveTask = {
        id,
        title,
        type,
        route: t.route,
        hopIndex: 0,
        phase: 'transfer',
        from: null,
        t0: nowMs,
        duration: TRANSFER_MS,
        createdAt: nowMs,
      }
      tasksRef.current = [...tasksRef.current, task]
      setTasks(tasksRef.current)
      setMetrics((m) => ({ ...m, launched: m.launched + 1 }))
      pushLog({
        agentId: null,
        kind: 'in',
        text: `Новая задача #${id}: «${title}» — маршрут: ${t.label.toLowerCase()}`,
      })
    },
    [pushLog],
  )

  // основной цикл
  useEffect(() => {
    const iv = setInterval(() => {
      const nowMs = Date.now()
      setNow(nowMs)

      let changed = false
      const next: ActiveTask[] = []
      for (const task of tasksRef.current) {
        const agentId = task.route[task.hopIndex]
        const agent = AGENT_BY_ID[agentId]

        if (task.phase === 'transfer') {
          const p = (nowMs - task.t0) / task.duration
          if (p < 1) {
            next.push(task)
            continue
          }
          // прибыл к агенту
          changed = true
          pushLog({
            agentId,
            kind: 'step',
            text: `${agent.name} принял задачу #${task.id} — этап «${agent.stageName}»`,
          })
          const workTask: ActiveTask = { ...task, phase: 'work', t0: nowMs, duration: workDuration() }
          if (modeRef.current === 'real') {
            workTask.callStarted = true
            const prevOutput = lastOutputRef.current.get(task.id) ?? null
            callAgent(agentId, SYSTEM_PROMPTS[agentId], buildStagePrompt(agentId, task.title, prevOutput)).then(
              (res) => {
                realCallsRef.current.set(task.id, { status: res.ok ? 'ok' : 'error', text: res.text })
              },
            )
          }
          next.push(workTask)
          continue
        }

        // phase === 'work'
        if (modeRef.current === 'real' && task.callStarted) {
          const call = realCallsRef.current.get(task.id)
          if (!call) {
            // модель ещё думает
            next.push(task)
            continue
          }
          realCallsRef.current.delete(task.id)
          changed = true
          if (call.status === 'ok') {
            lastOutputRef.current.set(task.id, call.text.slice(0, 1200))
            const excerpt = call.text.length > 220 ? call.text.slice(0, 220) + '…' : call.text
            pushLog({ agentId, kind: 'step', text: `${agent.name}: ${excerpt}` })
          } else {
            lastOutputRef.current.set(task.id, `Этап «${agent.stageName}» завершился ошибкой: ${call.text}`)
            pushLog({
              agentId,
              kind: 'error',
              text: `${agent.name} не смог выполнить этап (задача #${task.id}): ${call.text.slice(0, 180)}`,
            })
          }
          finishHop(task, agentId, nowMs, next)
          continue
        }

        // симуляция
        const p = (nowMs - task.t0) / task.duration
        if (p < 1) {
          next.push(task)
          continue
        }
        changed = true
        finishHop(task, agentId, nowMs, next)
      }

      function finishHop(task: ActiveTask, agentId: string, nowMs: number, acc: ActiveTask[]) {
        const agent = AGENT_BY_ID[agentId]
        if (task.hopIndex === task.route.length - 1) {
          const total = nowMs - task.createdAt
          durationsRef.current.push(total)
          if (durationsRef.current.length > 30) durationsRef.current.shift()
          const avg = Math.round(durationsRef.current.reduce((a, b) => a + b, 0) / durationsRef.current.length)
          setMetrics((m) => ({ ...m, done: m.done + 1, avgMs: avg }))
          lastOutputRef.current.delete(task.id)
          pushLog({
            agentId,
            kind: 'done',
            text: `Задача #${task.id} выполнена за ${(total / 1000).toFixed(1)} с — ${agent.name} опубликовал результат`,
          })
          // задача завершена — не переносим в next
        } else {
          const nextAgent = AGENT_BY_ID[task.route[task.hopIndex + 1]]
          if (modeRef.current === 'sim') {
            pushLog({
              agentId,
              kind: 'step',
              text: `${agent.name} завершил «${agent.stageName}», передаёт → ${nextAgent.name}`,
            })
          } else {
            pushLog({ agentId, kind: 'step', text: `${agent.name} передаёт задачу #${task.id} → ${nextAgent.name}` })
          }
          acc.push({
            ...task,
            phase: 'transfer',
            from: agentId,
            hopIndex: task.hopIndex + 1,
            t0: nowMs,
            duration: TRANSFER_MS,
            callStarted: false,
          })
        }
      }

      if (changed) {
        tasksRef.current = next
        setTasks(next)
      }

      // авто-режим (только симуляция — реальные вызовы стоят денег)
      if (auto && modeRef.current === 'sim' && nowMs - lastAutoRef.current > AUTO_EVERY_MS) {
        lastAutoRef.current = nowMs
        if (tasksRef.current.length < AUTO_MAX_ACTIVE) {
          const type = TASK_TYPES[Math.floor(Math.random() * TASK_TYPES.length)]
          const title = type.presets[Math.floor(Math.random() * type.presets.length)]
          launchTask(title, type.id)
        }
      }
    }, 60)
    return () => clearInterval(iv)
  }, [auto, launchTask, pushLog])

  const busyByAgent: Record<string, { taskId: number; progress: number | null }> = {}
  for (const task of tasks) {
    if (task.phase === 'work') {
      const agentId = task.route[task.hopIndex]
      busyByAgent[agentId] = {
        taskId: task.id,
        progress: task.callStarted ? null : Math.min(1, (now - task.t0) / task.duration),
      }
    }
  }

  return {
    now,
    tasks,
    log,
    metrics,
    auto,
    setAuto,
    mode,
    setMode,
    proxyOk,
    launchTask,
    busyByAgent,
    clearLog: useCallback(() => {
      setLog([{ id: idRef.current++, at: Date.now(), agentId: null, kind: 'system', text: 'Журнал очищен.' }])
    }, []),
    deptColor: (agentId: string) => DEPT_BY_ID[AGENT_BY_ID[agentId].departmentId].color,
  }
}

import {
  AGENTS,
  AGENT_BY_ID,
  DEPT_BY_ID,
  EDGES,
  ENTRY_POINT,
  bezierAt,
  edgeControl,
  edgePathD,
  nodePos,
} from '@/data/corporation'
import type { ActiveTask } from '@/hooks/useCorporationSim'
import { cn } from '@/lib/utils'
import { X } from 'lucide-react'

interface Props {
  now: number
  tasks: ActiveTask[]
  busyByAgent: Record<string, { taskId: number; progress: number | null }>
  selected: string | null
  onSelect: (id: string | null) => void
}

const NODE_W = 128
const NODE_H = 46

export default function FlowCanvas({ now, tasks, busyByAgent, selected, onSelect }: Props) {
  const selectedAgent = selected ? AGENT_BY_ID[selected] : null
  const selectedBusy = selected ? busyByAgent[selected] : undefined
  const selectedTask = selectedBusy ? tasks.find((t) => t.id === selectedBusy.taskId) : undefined

  return (
    <div className="relative min-h-[340px] min-w-0 flex-1 bg-[radial-gradient(ellipse_at_top,hsl(222_30%_10%)_0%,hsl(222_32%_6%)_60%)]">
      <svg
        viewBox="0 0 960 620"
        className="h-full w-full"
        role="img"
        aria-label="Схема потока задач между агентами ИИ-корпорации"
      >
        <defs>
          <filter id="glow" x="-80%" y="-80%" width="260%" height="260%">
            <feGaussianBlur stdDeviation="4" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        {/* точка входа задач */}
        <g>
          <rect
            x={ENTRY_POINT.x - 34}
            y={ENTRY_POINT.y}
            width="68"
            height="22"
            rx="11"
            fill="hsl(220 18% 14%)"
            stroke="hsl(43 90% 55% / 0.5)"
          />
          <text
            x={ENTRY_POINT.x}
            y={ENTRY_POINT.y + 15}
            textAnchor="middle"
            className="fill-muted-foreground"
            fontSize="11"
            fontFamily="JetBrains Mono, monospace"
          >
            ВХОД
          </text>
        </g>

        {/* рёбра маршрутов */}
        {EDGES.map((e) => {
          const p0 = nodePos(e.from)
          const p1 = nodePos(e.to)
          const active = tasks.some(
            (t) => t.phase === 'transfer' && t.from === e.from && t.route[t.hopIndex] === e.to,
          )
          return (
            <path
              key={`${e.from}->${e.to}`}
              d={edgePathD(p0, p1)}
              fill="none"
              stroke={active ? 'hsl(43 90% 55% / 0.55)' : 'hsl(220 16% 20%)'}
              strokeWidth={active ? 2 : 1.2}
              strokeDasharray={active ? '6 5' : undefined}
            />
          )
        })}

        {/* пакеты задач в пути */}
        {tasks
          .filter((t) => t.phase === 'transfer')
          .map((t) => {
            const p0 = nodePos(t.from)
            const p1 = nodePos(t.route[t.hopIndex])
            const pos = bezierAt(p0, edgeControl(p0, p1), p1, Math.min(1, (now - t.t0) / t.duration))
            return (
              <g key={t.id} className="packet" filter="url(#glow)">
                <circle cx={pos.x} cy={pos.y} r="7" fill="hsl(43 90% 55% / 0.35)" />
                <circle cx={pos.x} cy={pos.y} r="3.5" fill="hsl(43 90% 55%)" />
              </g>
            )
          })}

        {/* узлы-агенты */}
        {AGENTS.map((agent) => {
          const dept = DEPT_BY_ID[agent.departmentId]
          const busy = busyByAgent[agent.id]
          const isSelected = selected === agent.id
          const x = agent.x - NODE_W / 2
          const y = agent.y - NODE_H / 2
          const r = 40
          const circ = 2 * Math.PI * r
          return (
            <g
              key={agent.id}
              onClick={() => onSelect(isSelected ? null : agent.id)}
              className="cursor-pointer"
              role="button"
              tabIndex={0}
              onKeyDown={(ev) => {
                if (ev.key === 'Enter' || ev.key === ' ') {
                  ev.preventDefault()
                  onSelect(isSelected ? null : agent.id)
                }
              }}
              aria-label={`Агент ${agent.name}, ${agent.role}`}
            >
              {busy && (
                <>
                  <circle
                    cx={agent.x}
                    cy={agent.y}
                    r={r - 6}
                    fill="none"
                    stroke={`hsl(${dept.color} / 0.6)`}
                    strokeWidth="2"
                    className="agent-pulse"
                  />
                  <circle
                    cx={agent.x}
                    cy={agent.y}
                    r={r}
                    fill="none"
                    stroke={`hsl(${dept.color} / 0.25)`}
                    strokeWidth="3"
                  />
                  {busy.progress === null ? (
                    <circle
                      cx={agent.x}
                      cy={agent.y}
                      r={r}
                      fill="none"
                      stroke={`hsl(${dept.color})`}
                      strokeWidth="3"
                      strokeLinecap="round"
                      strokeDasharray="14 10"
                      className="ring-spin"
                    />
                  ) : (
                    <circle
                      cx={agent.x}
                      cy={agent.y}
                      r={r}
                      fill="none"
                      stroke={`hsl(${dept.color})`}
                      strokeWidth="3"
                      strokeLinecap="round"
                      strokeDasharray={circ}
                      strokeDashoffset={circ * (1 - busy.progress)}
                      transform={`rotate(-90 ${agent.x} ${agent.y})`}
                    />
                  )}
                </>
              )}
              <rect
                x={x}
                y={y}
                width={NODE_W}
                height={NODE_H}
                rx="10"
                fill={busy ? `hsl(${dept.color} / 0.14)` : 'hsl(222 26% 10%)'}
                stroke={
                  isSelected
                    ? 'hsl(43 90% 55%)'
                    : busy
                      ? `hsl(${dept.color})`
                      : `hsl(${dept.color} / 0.35)`
                }
                strokeWidth={isSelected ? 2.5 : 1.5}
              />
              <text
                x={agent.x}
                y={agent.y - 4}
                textAnchor="middle"
                fontSize="13"
                fontWeight="700"
                className="fill-foreground"
                fontFamily="Manrope, sans-serif"
              >
                {agent.name}
              </text>
              <text
                x={agent.x}
                y={agent.y + 13}
                textAnchor="middle"
                fontSize="10"
                className="fill-muted-foreground"
                fontFamily="JetBrains Mono, monospace"
              >
                {busy ? `${agent.stageName}…` : agent.model}
              </text>
            </g>
          )
        })}
      </svg>

      {/* карточка выбранного агента */}
      {selectedAgent && (
        <div
          className={cn(
            'absolute right-4 top-4 w-72 rounded-lg border border-border bg-popover p-4 shadow-xl',
          )}
          role="dialog"
          aria-label={`Карточка агента ${selectedAgent.name}`}
        >
          <div className="mb-2 flex items-start justify-between">
            <div>
              <div className="text-base font-bold">{selectedAgent.name}</div>
              <div className="text-xs text-muted-foreground">{selectedAgent.role}</div>
            </div>
            <button
              type="button"
              onClick={() => onSelect(null)}
              className="rounded-md p-1 text-muted-foreground transition-colors hover:bg-accent hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              aria-label="Закрыть карточку агента"
            >
              <X size={16} />
            </button>
          </div>
          <dl className="space-y-1.5 text-sm">
            <div className="flex justify-between gap-2">
              <dt className="text-muted-foreground">Отдел</dt>
              <dd
                className="font-semibold"
                style={{ color: `hsl(${DEPT_BY_ID[selectedAgent.departmentId].color})` }}
              >
                {DEPT_BY_ID[selectedAgent.departmentId].name}
              </dd>
            </div>
            <div className="flex justify-between gap-2">
              <dt className="text-muted-foreground">Модель</dt>
              <dd className="font-mono text-xs">{selectedAgent.model}</dd>
            </div>
            <div className="flex justify-between gap-2">
              <dt className="text-muted-foreground">Статус</dt>
              <dd className="font-semibold">
                {selectedBusy ? `Занят · задача #${selectedBusy.taskId}` : 'Свободен'}
              </dd>
            </div>
            {selectedTask && (
              <div className="mt-2 rounded-md bg-secondary p-2 text-xs text-secondary-foreground">
                «{selectedTask.title}» — этап «{selectedAgent.stageName}»,{' '}
                {selectedBusy!.progress === null
                  ? 'модель думает…'
                  : `${Math.round(selectedBusy!.progress! * 100)}%`}
              </div>
            )}
          </dl>
        </div>
      )}
    </div>
  )
}

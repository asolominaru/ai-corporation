import { Check, CircleDashed, Undo2 } from 'lucide-react'
import type { ActiveTask, DoneTask } from '@/hooks/useCorporationSim'
import { AGENT_BY_ID, DEPT_BY_ID, TASK_TYPES, type TaskTypeId } from '@/data/corporation'
import { STRINGS, type Lang } from '@/i18n'

interface Props {
  tasks: ActiveTask[]
  doneTasks: DoneTask[]
  lang: Lang
  onApprove: (id: number) => void
  onReject: (id: number) => void
}

function typeLabel(type: TaskTypeId, lang: Lang): string {
  const t = TASK_TYPES.find((x) => x.id === type)
  return t ? (lang === 'ru' ? t.label : t.labelEn) : type
}

function Column({
  title,
  count,
  accent,
  children,
}: {
  title: string
  count: number
  accent?: boolean
  children: React.ReactNode
}) {
  return (
    <div
      className={`flex min-h-0 min-w-0 flex-1 flex-col rounded-lg border bg-card/50 ${
        accent ? 'border-primary/50' : 'border-border'
      }`}
    >
      <div className="flex items-center gap-2 border-b border-border px-3 py-1.5">
        {accent && count > 0 && (
          <span className="relative flex h-2 w-2">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-primary opacity-60" />
            <span className="relative inline-flex h-2 w-2 rounded-full bg-primary" />
          </span>
        )}
        <span className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground">{title}</span>
        <span className="rounded-full bg-muted px-1.5 py-0.5 font-mono text-[10px] leading-none text-muted-foreground">
          {count}
        </span>
      </div>
      <div className="flex min-h-0 flex-1 flex-col gap-1.5 overflow-y-auto p-2">{children}</div>
    </div>
  )
}

export default function KanbanBoard({ tasks, doneTasks, lang, onApprove, onReject }: Props) {
  const s = STRINGS[lang]
  const inProgress = tasks.filter((t) => t.phase !== 'approval')
  const pending = tasks.filter((t) => t.phase === 'approval')

  return (
    <div className="flex h-44 shrink-0 gap-2 border-t border-border bg-background/60 px-4 py-2.5">
      <Column title={s.kanbanInProgress} count={inProgress.length}>
        {inProgress.length === 0 && (
          <span className="px-1 py-1 text-xs text-muted-foreground/60">{s.kanbanEmpty}</span>
        )}
        {inProgress.map((t) => {
          const agent = AGENT_BY_ID[t.route[t.hopIndex]]
          const dept = DEPT_BY_ID[agent.departmentId]
          const stage = lang === 'ru' ? agent.stageName : agent.stageNameEn
          return (
            <div key={t.id} className="rounded-md border border-border bg-card px-2.5 py-1.5">
              <div className="truncate text-xs">
                <span className="font-mono text-[10px] text-muted-foreground">#{t.id}</span> {t.title}
              </div>
              <div className="mt-1 flex items-center gap-1.5 text-[10px] text-muted-foreground">
                <span className="h-1.5 w-1.5 shrink-0 rounded-full" style={{ background: `hsl(${dept.color})` }} />
                <span className="truncate">
                  {agent.name} · {stage}
                </span>
              </div>
            </div>
          )
        })}
      </Column>

      <Column title={s.kanbanApproval} count={pending.length} accent>
        {pending.length === 0 && (
          <span className="px-1 py-1 text-xs text-muted-foreground/60">{s.kanbanEmpty}</span>
        )}
        {pending.map((t) => (
          <div key={t.id} className="rounded-md border border-primary/40 bg-card px-2.5 py-1.5">
            <div className="truncate text-xs">
              <span className="font-mono text-[10px] text-muted-foreground">#{t.id}</span> {t.title}
            </div>
            <div className="mt-1.5 flex gap-1.5">
              <button
                type="button"
                onClick={() => onApprove(t.id)}
                className="flex items-center gap-1 rounded-md bg-emerald-500/15 px-2 py-0.5 text-[10px] font-semibold text-emerald-400 transition-colors hover:bg-emerald-500/30 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              >
                <Check size={11} />
                {s.approve}
              </button>
              <button
                type="button"
                onClick={() => onReject(t.id)}
                className="flex items-center gap-1 rounded-md bg-destructive/15 px-2 py-0.5 text-[10px] font-semibold text-destructive transition-colors hover:bg-destructive/30 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              >
                <Undo2 size={11} />
                {s.rework}
              </button>
            </div>
          </div>
        ))}
      </Column>

      <Column title={s.kanbanDone} count={doneTasks.length}>
        {doneTasks.length === 0 && (
          <span className="px-1 py-1 text-xs text-muted-foreground/60">{s.kanbanEmpty}</span>
        )}
        {doneTasks.map((t) => (
          <div key={`${t.id}-${t.completedAt}`} className="rounded-md border border-border bg-card px-2.5 py-1.5">
            <div className="flex items-center gap-1.5 truncate text-xs">
              <Check size={12} className="shrink-0 text-emerald-400" />
              <span className="truncate">
                <span className="font-mono text-[10px] text-muted-foreground">#{t.id}</span> {t.title}
              </span>
            </div>
            <div className="mt-1 flex items-center gap-1.5 text-[10px] text-muted-foreground">
              <CircleDashed size={10} className="shrink-0" />
              <span className="truncate">
                {typeLabel(t.type, lang)} · {(t.totalMs / 1000).toFixed(1)} {lang === 'ru' ? 'с' : 's'}
              </span>
            </div>
          </div>
        ))}
      </Column>
    </div>
  )
}

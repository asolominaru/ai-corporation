import { AGENT_BY_ID, DEPARTMENTS, TASK_TYPES, type TaskTypeId } from '@/data/corporation'
import type { ActiveTask, DoneTask, Metrics } from '@/hooks/useCorporationSim'
import { STRINGS, type Lang } from '@/i18n'

interface Props {
  tasks: ActiveTask[]
  doneTasks: DoneTask[]
  metrics: Metrics
  byTypeLaunched: Record<TaskTypeId, number>
  reworks: number
  lang: Lang
}

function Panel({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="rounded-lg border border-border bg-card/50 p-3">
      <h3 className="mb-2.5 text-[10px] font-bold uppercase tracking-widest text-muted-foreground">{title}</h3>
      {children}
    </section>
  )
}

export default function DashboardView({ tasks, doneTasks, metrics, byTypeLaunched, reworks, lang }: Props) {
  const s = STRINGS[lang]
  const pending = tasks.filter((t) => t.phase === 'approval').length

  // загрузка отделов: активные задачи по текущему агенту
  const deptLoad = DEPARTMENTS.map((dept) => {
    const count = tasks.filter((t) => {
      if (t.phase === 'approval') return dept.id === 'dir'
      return AGENT_BY_ID[t.route[t.hopIndex]].departmentId === dept.id
    }).length
    return { dept, count }
  })
  const maxLoad = Math.max(1, ...deptLoad.map((d) => d.count))

  const maxLaunched = Math.max(1, ...TASK_TYPES.map((t) => byTypeLaunched[t.id]))

  const cycles = doneTasks.slice(0, 20).reverse()
  const maxCycle = Math.max(1, ...cycles.map((t) => t.totalMs))

  const kpis: Array<{ label: string; value: string | number; accent?: boolean }> = [
    { label: s.tasksInFlight, value: tasks.length },
    { label: s.completed, value: metrics.done },
    { label: s.dashPending, value: pending, accent: pending > 0 },
    { label: s.dashReworks, value: reworks },
  ]

  return (
    <div className="scroll-slim min-h-0 flex-1 overflow-y-auto bg-[radial-gradient(ellipse_at_top,hsl(222_30%_10%)_0%,hsl(222_32%_6%)_60%)] p-4">
      {/* KPI */}
      <div className="mb-4 grid grid-cols-2 gap-2 lg:grid-cols-4">
        {kpis.map((k) => (
          <div key={k.label} className="rounded-lg border border-border bg-card/50 px-3 py-2.5">
            <div
              className={`font-mono text-2xl font-bold tabular-nums ${k.accent ? 'text-primary' : 'text-foreground'}`}
            >
              {k.value}
            </div>
            <div className="text-[10px] uppercase tracking-widest text-muted-foreground">{k.label}</div>
          </div>
        ))}
      </div>

      <div className="grid gap-3 lg:grid-cols-2">
        {/* загрузка отделов */}
        <Panel title={s.dashDeptLoad}>
          <div className="space-y-2">
            {deptLoad.map(({ dept, count }) => (
              <div key={dept.id} className="flex items-center gap-2">
                <span className="w-36 shrink-0 truncate text-xs text-muted-foreground">
                  {lang === 'ru' ? dept.name : dept.nameEn}
                </span>
                <div className="h-2.5 min-w-0 flex-1 rounded-full bg-muted/60">
                  <div
                    className="h-full rounded-full transition-all duration-500"
                    style={{ width: `${(count / maxLoad) * 100}%`, background: `hsl(${dept.color})` }}
                  />
                </div>
                <span className="w-6 shrink-0 text-right font-mono text-xs tabular-nums">{count}</span>
              </div>
            ))}
          </div>
        </Panel>

        {/* задачи по типам */}
        <Panel title={s.dashByType}>
          <div className="space-y-2">
            {TASK_TYPES.map((t) => (
              <div key={t.id} className="flex items-center gap-2">
                <span className="w-36 shrink-0 truncate text-xs text-muted-foreground">
                  {lang === 'ru' ? t.label : t.labelEn}
                </span>
                <div className="h-2.5 min-w-0 flex-1 rounded-full bg-muted/60">
                  <div
                    className="h-full rounded-full bg-primary/80 transition-all duration-500"
                    style={{ width: `${(byTypeLaunched[t.id] / maxLaunched) * 100}%` }}
                  />
                </div>
                <span className="w-6 shrink-0 text-right font-mono text-xs tabular-nums">
                  {byTypeLaunched[t.id]}
                </span>
              </div>
            ))}
          </div>
        </Panel>

        {/* длительность циклов */}
        <Panel title={`${s.dashCycles} · ${s.avgCycle} ${(metrics.avgMs / 1000).toFixed(1)} ${lang === 'ru' ? 'с' : 's'}`}>
          {cycles.length === 0 ? (
            <span className="text-xs text-muted-foreground/60">{s.dashNoData}</span>
          ) : (
            <div className="flex h-24 items-end gap-1">
              {cycles.map((t) => (
                <div
                  key={`${t.id}-${t.completedAt}`}
                  title={`#${t.id} · ${(t.totalMs / 1000).toFixed(1)} ${lang === 'ru' ? 'с' : 's'}`}
                  className="min-w-0 flex-1 rounded-t bg-emerald-500/70 transition-all duration-500 hover:bg-emerald-400"
                  style={{ height: `${Math.max(6, (t.totalMs / maxCycle) * 100)}%` }}
                />
              ))}
            </div>
          )}
        </Panel>
      </div>
    </div>
  )
}

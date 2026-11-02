import { AGENTS, DEPARTMENTS, CEO } from '@/data/corporation'
import { STRINGS, type Lang } from '@/i18n'
import { cn } from '@/lib/utils'

interface Props {
  busyByAgent: Record<string, { taskId: number; progress: number | null }>
  selected: string | null
  onSelect: (id: string | null) => void
  lang: Lang
}

export default function OrgPanel({ busyByAgent, selected, onSelect, lang }: Props) {
  const s = STRINGS[lang]
  return (
    <aside className="flex h-60 w-full shrink-0 flex-col border-b border-border bg-card/40 lg:h-auto lg:w-72 lg:border-b-0 lg:border-r">
      <div className="border-b border-border px-4 py-3">
        <h2 className="text-xs font-bold uppercase tracking-widest text-muted-foreground">
          {s.orgChart(AGENTS.length)}
        </h2>
      </div>
      <div className="scroll-slim flex-1 overflow-y-auto p-2">
        {DEPARTMENTS.map((dept) => {
          const agents = AGENTS.filter((a) => a.departmentId === dept.id)
          return (
            <div key={dept.id} className="mb-2">
              <div className="flex items-center gap-2 px-2 py-1.5">
                <span
                  className="h-2 w-2 rounded-sm"
                  style={{ background: `hsl(${dept.color})` }}
                  aria-hidden="true"
                />
                <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  {lang === 'ru' ? dept.name : dept.nameEn}
                </span>
              </div>
              {dept.id === 'dir' && (
                <div className="mb-1 flex w-full items-center gap-2.5 rounded-md border border-primary/30 bg-primary/5 px-2.5 py-2 text-left">
                  <span className="flex h-2.5 w-2.5 shrink-0 items-center justify-center rounded-full border border-primary" aria-hidden="true" />
                  <span className="min-w-0 flex-1 leading-tight">
                    <span className="block truncate text-sm font-semibold">
                      {lang === 'ru' ? CEO.name : CEO.nameEn}
                    </span>
                    <span className="block truncate text-xs text-muted-foreground">
                      {lang === 'ru' ? CEO.role : CEO.roleEn}
                    </span>
                  </span>
                  <span className="font-mono text-[11px] text-primary">human</span>
                </div>
              )}
              {agents.map((agent) => {
                const busy = busyByAgent[agent.id]
                const isSelected = selected === agent.id
                return (
                  <button
                    key={agent.id}
                    type="button"
                    onClick={() => onSelect(isSelected ? null : agent.id)}
                    className={cn(
                      'flex w-full items-center gap-2.5 rounded-md px-2.5 py-2 text-left transition-colors duration-150',
                      'hover:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
                      isSelected && 'bg-accent',
                    )}
                  >
                    <span
                      className={cn('h-2.5 w-2.5 shrink-0 rounded-full', busy && 'agent-pulse')}
                      style={{
                        background: busy ? `hsl(${dept.color})` : 'hsl(217 14% 40%)',
                      }}
                      aria-hidden="true"
                    />
                    <span className="min-w-0 flex-1 leading-tight">
                      <span className="block truncate text-sm font-semibold">{agent.name}</span>
                      <span className="block truncate text-xs text-muted-foreground">
                        {lang === 'ru' ? agent.role : agent.roleEn}
                      </span>
                    </span>
                    {busy ? (
                      <span
                        className="font-mono text-[11px] font-semibold tabular-nums"
                        style={{ color: `hsl(${dept.color})` }}
                      >
                        {busy.progress === null ? '…' : `${Math.round(busy.progress * 100)}%`}
                      </span>
                    ) : (
                      <span className="font-mono text-[11px] text-muted-foreground">{s.idle}</span>
                    )}
                  </button>
                )
              })}
            </div>
          )
        })}
      </div>
    </aside>
  )
}

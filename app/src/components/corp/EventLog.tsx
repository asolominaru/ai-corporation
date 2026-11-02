import { CheckCircle2, Inbox, ArrowRightCircle, Info, Trash2, AlertTriangle } from 'lucide-react'
import { AGENT_BY_ID, DEPT_BY_ID } from '@/data/corporation'
import { STRINGS, type Lang } from '@/i18n'
import type { LogEntry } from '@/hooks/useCorporationSim'

interface Props {
  log: LogEntry[]
  onClear: () => void
  lang: Lang
}

const ICONS = {
  in: Inbox,
  step: ArrowRightCircle,
  done: CheckCircle2,
  error: AlertTriangle,
  system: Info,
} as const

export default function EventLog({ log, onClear, lang }: Props) {
  const s = STRINGS[lang]
  return (
    <aside className="flex h-64 w-full shrink-0 flex-col border-t border-border bg-card/40 lg:h-auto lg:w-80 lg:border-l lg:border-t-0">
      <div className="flex items-center justify-between border-b border-border px-4 py-3">
        <h2 className="text-xs font-bold uppercase tracking-widest text-muted-foreground">
          {s.eventLog}
        </h2>
        <button
          type="button"
          onClick={onClear}
          className="flex items-center gap-1 rounded-md px-2 py-1 text-xs text-muted-foreground transition-colors hover:bg-accent hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          <Trash2 size={13} />
          {s.clear}
        </button>
      </div>
      <div className="scroll-slim flex-1 overflow-y-auto p-2">
        {log.map((entry) => {
          const Icon = ICONS[entry.kind]
          const agent = entry.agentId ? AGENT_BY_ID[entry.agentId] : null
          const color = entry.kind === 'error' ? null : agent ? DEPT_BY_ID[agent.departmentId].color : null
          return (
            <div key={entry.id} className="flex gap-2.5 rounded-md px-2 py-2 hover:bg-accent/50">
              <span
                className="mt-0.5 shrink-0"
                style={color ? { color: `hsl(${color})` } : undefined}
              >
                <Icon
                  size={15}
                  className={color ? undefined : entry.kind === 'error' ? 'text-destructive' : 'text-muted-foreground'}
                />
              </span>
              <div className="min-w-0 leading-snug">
                <div className="text-[13px]">{entry.text}</div>
                <div className="font-mono text-[11px] text-muted-foreground">
                  {new Date(entry.at).toLocaleTimeString(lang === 'ru' ? 'ru-RU' : 'en-GB')}
                </div>
              </div>
            </div>
          )
        })}
      </div>
    </aside>
  )
}

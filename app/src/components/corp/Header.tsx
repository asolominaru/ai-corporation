import { Activity, CheckCircle2, Cpu, Timer } from 'lucide-react'
import type { Metrics } from '@/hooks/useCorporationSim'
import { STRINGS, type Lang } from '@/i18n'
import { cn } from '@/lib/utils'

interface Props {
  metrics: Metrics
  activeCount: number
  busyCount: number
  now: number
  lang: Lang
  onLangChange: (l: Lang) => void
}

function Chip({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return (
    <div className="flex items-center gap-2 rounded-md border border-border bg-card px-3 py-1.5">
      <span className="text-primary">{icon}</span>
      <div className="leading-tight">
        <div className="font-mono text-sm font-semibold text-foreground">{value}</div>
        <div className="text-[11px] text-muted-foreground">{label}</div>
      </div>
    </div>
  )
}

export default function Header({ metrics, activeCount, busyCount, now, lang, onLangChange }: Props) {
  const s = STRINGS[lang]
  const time = new Date(now).toLocaleTimeString(lang === 'ru' ? 'ru-RU' : 'en-GB')
  return (
    <header className="flex h-16 shrink-0 items-center gap-4 border-b border-border bg-card/60 px-5">
      <div className="flex items-center gap-3">
        <svg width="34" height="34" viewBox="0 0 34 34" aria-hidden="true">
          <polygon
            points="17,2 30,9.5 30,24.5 17,32 4,24.5 4,9.5"
            fill="none"
            stroke="hsl(43 90% 55%)"
            strokeWidth="2"
          />
          <circle cx="17" cy="17" r="4" fill="hsl(43 90% 55%)" />
        </svg>
        <div className="leading-tight">
          <h1 className="text-lg font-extrabold tracking-wide">ИИ-КОРПОРАЦИЯ</h1>
          <p className="text-xs text-muted-foreground">{s.subtitle}</p>
        </div>
      </div>

      <div className="mx-2 h-8 w-px bg-border" aria-hidden="true" />

      <div className="flex items-center gap-2">
        <span className="relative flex h-2.5 w-2.5">
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-60" />
          <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-emerald-400" />
        </span>
        <span className="text-sm text-muted-foreground">{s.systemsOk}</span>
      </div>

      <div className="ml-auto hidden items-center gap-2.5 md:flex">
        <Chip icon={<Activity size={16} />} label={s.tasksInFlight} value={String(activeCount)} />
        <Chip icon={<Cpu size={16} />} label={s.agentsBusy} value={String(busyCount)} />
        <Chip icon={<CheckCircle2 size={16} />} label={s.completed} value={String(metrics.done)} />
        <Chip
          icon={<Timer size={16} />}
          label={s.avgCycle}
          value={metrics.avgMs ? `${(metrics.avgMs / 1000).toFixed(1)} с` : '—'}
        />
      </div>

      <div
        className="ml-auto flex rounded-md border border-border bg-secondary p-0.5 md:ml-2"
        role="group"
        aria-label="Язык интерфейса / Interface language"
      >
        {(['ru', 'en'] as const).map((l) => (
          <button
            key={l}
            type="button"
            onClick={() => onLangChange(l)}
            aria-pressed={lang === l}
            className={cn(
              'rounded px-2 py-1 font-mono text-[11px] font-semibold uppercase transition-colors duration-150',
              'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
              lang === l ? 'bg-primary text-primary-foreground' : 'text-muted-foreground hover:text-foreground',
            )}
          >
            {l}
          </button>
        ))}
      </div>

      <div className="font-mono text-lg font-semibold tabular-nums text-primary">{time}</div>
    </header>
  )
}

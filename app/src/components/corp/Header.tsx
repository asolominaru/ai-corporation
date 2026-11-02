import { Activity, CheckCircle2, Cpu, Timer } from 'lucide-react'
import type { Metrics } from '@/hooks/useCorporationSim'

interface Props {
  metrics: Metrics
  activeCount: number
  busyCount: number
  now: number
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

export default function Header({ metrics, activeCount, busyCount, now }: Props) {
  const time = new Date(now).toLocaleTimeString('ru-RU')
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
          <p className="text-xs text-muted-foreground">центр управления агентами</p>
        </div>
      </div>

      <div className="mx-2 h-8 w-px bg-border" aria-hidden="true" />

      <div className="flex items-center gap-2">
        <span className="relative flex h-2.5 w-2.5">
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-60" />
          <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-emerald-400" />
        </span>
        <span className="text-sm text-muted-foreground">Системы в норме</span>
      </div>

      <div className="ml-auto hidden items-center gap-2.5 md:flex">
        <Chip icon={<Activity size={16} />} label="задач в работе" value={String(activeCount)} />
        <Chip icon={<Cpu size={16} />} label="агентов занято" value={String(busyCount)} />
        <Chip icon={<CheckCircle2 size={16} />} label="выполнено" value={String(metrics.done)} />
        <Chip
          icon={<Timer size={16} />}
          label="средний цикл"
          value={metrics.avgMs ? `${(metrics.avgMs / 1000).toFixed(1)} с` : '—'}
        />
      </div>
      <div className="ml-auto font-mono text-lg font-semibold tabular-nums text-primary md:ml-2">{time}</div>
    </header>
  )
}

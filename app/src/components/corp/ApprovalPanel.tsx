import { Check, Undo2 } from 'lucide-react'
import type { ActiveTask } from '@/hooks/useCorporationSim'
import { STRINGS, type Lang } from '@/i18n'
import { CEO } from '@/data/corporation'

interface Props {
  tasks: ActiveTask[]
  lang: Lang
  onApprove: (id: number) => void
  onReject: (id: number) => void
}

export default function ApprovalPanel({ tasks, lang, onApprove, onReject }: Props) {
  const pending = tasks.filter((t) => t.phase === 'approval')
  if (pending.length === 0) return null
  const s = STRINGS[lang]

  return (
    <div className="shrink-0 border-t border-primary/40 bg-primary/5 px-4 py-2.5">
      <div className="mb-1.5 flex items-center gap-2">
        <span className="relative flex h-2 w-2">
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-primary opacity-60" />
          <span className="relative inline-flex h-2 w-2 rounded-full bg-primary" />
        </span>
        <span className="text-xs font-bold uppercase tracking-widest text-primary">
          {s.approvalTitle} — {lang === 'ru' ? CEO.name : CEO.nameEn}
        </span>
      </div>
      <div className="flex flex-wrap gap-2">
        {pending.map((t) => (
          <div
            key={t.id}
            className="flex items-center gap-2 rounded-md border border-border bg-card px-3 py-1.5"
          >
            <span className="max-w-64 truncate text-sm">
              <span className="font-mono text-xs text-muted-foreground">#{t.id}</span> {t.title}
            </span>
            <button
              type="button"
              onClick={() => onApprove(t.id)}
              className="flex items-center gap-1 rounded-md bg-emerald-500/15 px-2.5 py-1 text-xs font-semibold text-emerald-400 transition-colors hover:bg-emerald-500/30 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              <Check size={13} />
              {s.approve}
            </button>
            <button
              type="button"
              onClick={() => onReject(t.id)}
              className="flex items-center gap-1 rounded-md bg-destructive/15 px-2.5 py-1 text-xs font-semibold text-destructive transition-colors hover:bg-destructive/30 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              <Undo2 size={13} />
              {s.rework}
            </button>
          </div>
        ))}
      </div>
    </div>
  )
}

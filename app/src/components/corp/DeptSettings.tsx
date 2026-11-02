import { RotateCcw, X } from 'lucide-react'
import { AGENTS, DEPT_BY_ID, MODEL_CATALOG, SYSTEM_PROMPTS } from '@/data/corporation'
import type { AgentOverrides } from '@/hooks/useCorporationSim'
import { STRINGS, type Lang } from '@/i18n'

interface Props {
  deptId: string
  lang: Lang
  overrides: AgentOverrides
  onOverride: (agentId: string, patch: { model?: string; prompt?: string }) => void
  onClose: () => void
}

export default function DeptSettings({ deptId, lang, overrides, onOverride, onClose }: Props) {
  const s = STRINGS[lang]
  const dept = DEPT_BY_ID[deptId]
  const agents = AGENTS.filter((a) => a.departmentId === deptId)

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
      onClick={onClose}
      role="presentation"
    >
      <div
        className="scroll-slim max-h-[85vh] w-full max-w-xl overflow-y-auto rounded-xl border border-border bg-popover shadow-2xl"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-label={s.deptSettings}
      >
        <div className="sticky top-0 z-10 flex items-center gap-2.5 border-b border-border bg-popover px-4 py-3">
          <span className="h-2.5 w-2.5 rounded-sm" style={{ background: `hsl(${dept.color})` }} aria-hidden="true" />
          <h2 className="flex-1 text-sm font-bold">
            {s.deptSettings} · {lang === 'ru' ? dept.name : dept.nameEn}
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="rounded-md p-1 text-muted-foreground transition-colors hover:bg-accent hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            aria-label={s.close}
          >
            <X size={16} />
          </button>
        </div>

        <div className="space-y-3 p-4">
          {agents.map((agent) => {
            const ov = overrides[agent.id]
            const modelValue = ov?.model ?? agent.model
            const options = MODEL_CATALOG.some((o) => o.label === modelValue)
              ? MODEL_CATALOG
              : [{ label: modelValue, litellm: '' }, ...MODEL_CATALOG]
            const promptValue = ov?.prompt ?? SYSTEM_PROMPTS[agent.id]
            const isCustom = Boolean(ov?.model || ov?.prompt)
            return (
              <div key={agent.id} className="rounded-lg border border-border bg-card/50 p-3">
                <div className="mb-2 flex items-center gap-2">
                  <span className="min-w-0 flex-1 leading-tight">
                    <span className="block truncate text-sm font-semibold">{agent.name}</span>
                    <span className="block truncate text-xs text-muted-foreground">
                      {lang === 'ru' ? agent.role : agent.roleEn}
                    </span>
                  </span>
                  {isCustom && (
                    <button
                      type="button"
                      onClick={() => onOverride(agent.id, { model: '', prompt: '' })}
                      className="flex items-center gap-1 rounded-md bg-muted px-2 py-1 text-[10px] font-semibold text-muted-foreground transition-colors hover:bg-accent hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                    >
                      <RotateCcw size={11} />
                      {s.resetDefault}
                    </button>
                  )}
                </div>
                <label className="mb-1 block text-[10px] font-bold uppercase tracking-widest text-muted-foreground">
                  {s.modelLabel}
                </label>
                <select
                  value={modelValue}
                  onChange={(e) => onOverride(agent.id, { model: e.target.value === agent.model ? '' : e.target.value })}
                  className="mb-2 w-full rounded-md border border-border bg-background px-2.5 py-1.5 font-mono text-xs focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                >
                  {options.map((o) => (
                    <option key={o.label} value={o.label}>
                      {o.label}
                    </option>
                  ))}
                </select>
                <label className="mb-1 block text-[10px] font-bold uppercase tracking-widest text-muted-foreground">
                  {s.promptLabel}
                </label>
                <textarea
                  value={promptValue}
                  rows={3}
                  onChange={(e) =>
                    onOverride(agent.id, {
                      prompt: e.target.value === SYSTEM_PROMPTS[agent.id] ? '' : e.target.value,
                    })
                  }
                  className="w-full resize-y rounded-md border border-border bg-background px-2.5 py-1.5 text-xs leading-relaxed focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                />
              </div>
            )
          })}
          <p className="text-[11px] leading-relaxed text-muted-foreground">{s.modelNote}</p>
        </div>
      </div>
    </div>
  )
}

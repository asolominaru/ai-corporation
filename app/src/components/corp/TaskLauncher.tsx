import { useState } from 'react'
import { Bot, Pause, Play, SendHorizonal, Sparkles } from 'lucide-react'
import { TASK_TYPES, PRODUCTS, type TaskTypeId } from '@/data/corporation'
import type { Mode } from '@/hooks/useCorporationSim'
import { STRINGS, type Lang } from '@/i18n'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

interface Props {
  auto: boolean
  onToggleAuto: (v: boolean) => void
  onLaunch: (title: string, type: TaskTypeId) => void
  mode: Mode
  onModeChange: (m: Mode) => void
  proxyOk: boolean | null
  lang: Lang
}

export default function TaskLauncher({ auto, onToggleAuto, onLaunch, mode, onModeChange, proxyOk, lang }: Props) {
  const s = STRINGS[lang]
  const [type, setType] = useState<TaskTypeId>('rnd')
  const [product, setProduct] = useState<string>(PRODUCTS[0].id)
  const [title, setTitle] = useState('')

  const current = TASK_TYPES.find((t) => t.id === type)!
  const presets = lang === 'ru' ? current.presets : current.presetsEn
  const realBlocked = mode === 'real' && proxyOk === false

  const submit = () => {
    let value = title.trim() || presets[Math.floor(Math.random() * presets.length)]
    if (type === 'product') {
      const p = PRODUCTS.find((x) => x.id === product)!
      value = `${lang === 'ru' ? p.name : p.nameEn}: ${value}`
    }
    onLaunch(value, type)
    setTitle('')
  }

  return (
    <div className="shrink-0 border-t border-border bg-card/60 px-4 py-3">
      <div className="flex flex-wrap items-center gap-3">
        <div className="flex rounded-md border border-border bg-secondary p-0.5" role="group" aria-label="Режим работы">
          <button
            type="button"
            onClick={() => onModeChange('sim')}
            aria-pressed={mode === 'sim'}
            className={cn(
              'flex items-center gap-1.5 rounded px-3 py-1.5 text-xs font-semibold transition-colors duration-150',
              'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
              mode === 'sim' ? 'bg-primary text-primary-foreground' : 'text-muted-foreground hover:text-foreground',
            )}
          >
            <Sparkles size={13} />
            {s.simulation}
          </button>
          <button
            type="button"
            onClick={() => onModeChange('real')}
            aria-pressed={mode === 'real'}
            className={cn(
              'flex items-center gap-1.5 rounded px-3 py-1.5 text-xs font-semibold transition-colors duration-150',
              'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
              mode === 'real' ? 'bg-primary text-primary-foreground' : 'text-muted-foreground hover:text-foreground',
            )}
          >
            <Bot size={13} />
            {s.liveModels}
          </button>
        </div>

        <div className="flex rounded-md border border-border bg-secondary p-0.5" role="group" aria-label="Тип задачи">
          {TASK_TYPES.map((t) => (
            <button
              key={t.id}
              type="button"
              onClick={() => setType(t.id)}
              aria-pressed={type === t.id}
              className={cn(
                'rounded px-3 py-1.5 text-xs font-semibold transition-colors duration-150',
                'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
                type === t.id
                  ? 'bg-accent text-accent-foreground'
                  : 'text-muted-foreground hover:text-foreground',
              )}
            >
              {lang === 'ru' ? t.label : t.labelEn}
            </button>
          ))}
        </div>

        {type === 'product' && (
          <div
            className="flex rounded-md border border-primary/40 bg-secondary p-0.5"
            role="group"
            aria-label={lang === 'ru' ? 'Продукт' : 'Product'}
          >
            {PRODUCTS.map((p) => (
              <button
                key={p.id}
                type="button"
                onClick={() => setProduct(p.id)}
                aria-pressed={product === p.id}
                className={cn(
                  'rounded px-2.5 py-1.5 font-mono text-[11px] font-semibold transition-colors duration-150',
                  'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
                  product === p.id
                    ? 'bg-primary text-primary-foreground'
                    : 'text-muted-foreground hover:text-foreground',
                )}
              >
                {lang === 'ru' ? p.name : p.nameEn}
              </button>
            ))}
          </div>
        )}

        <input
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') submit()
          }}
          placeholder={`${s.examplePrefix}: ${presets[0]}`}
          aria-label={s.taskWord}
          className="min-w-40 flex-1 rounded-md border border-input bg-background px-3 py-2 text-sm outline-none transition-colors placeholder:text-muted-foreground focus:border-ring focus:ring-1 focus:ring-ring"
        />

        <Button type="button" onClick={submit} disabled={realBlocked} className="gap-2 font-semibold">
          <SendHorizonal size={15} />
          {s.launchTask}
        </Button>

        {mode === 'sim' ? (
          <Button
            type="button"
            variant="outline"
            onClick={() => onToggleAuto(!auto)}
            aria-pressed={auto}
            className={cn('gap-2', auto && 'border-primary/60 text-primary')}
          >
            {auto ? <Pause size={15} /> : <Play size={15} />}
            {auto ? s.autoOn : s.autoOff}
          </Button>
        ) : (
          <span
            className={cn(
              'flex items-center gap-2 rounded-md border px-3 py-1.5 text-xs',
              proxyOk ? 'border-emerald-500/40 text-emerald-600' : 'border-destructive/50 text-destructive',
            )}
            role="status"
          >
            <span
              className={cn('h-2 w-2 rounded-full', proxyOk ? 'bg-emerald-500' : 'bg-destructive')}
              aria-hidden="true"
            />
            {proxyOk === null ? s.gatewayChecking : proxyOk ? s.gatewayOnline : s.gatewayOffline}
          </span>
        )}
      </div>
      <p className="mt-1.5 text-[11px] text-muted-foreground">
        {mode === 'sim' ? s.hintSim : realBlocked ? s.hintRealBlocked : s.hintReal}
      </p>
    </div>
  )
}

import { useState } from 'react'
import { Bot, Pause, Play, SendHorizonal, Sparkles } from 'lucide-react'
import { TASK_TYPES, type TaskTypeId } from '@/data/corporation'
import type { Mode } from '@/hooks/useCorporationSim'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

interface Props {
  auto: boolean
  onToggleAuto: (v: boolean) => void
  onLaunch: (title: string, type: TaskTypeId) => void
  mode: Mode
  onModeChange: (m: Mode) => void
  proxyOk: boolean | null
}

export default function TaskLauncher({ auto, onToggleAuto, onLaunch, mode, onModeChange, proxyOk }: Props) {
  const [type, setType] = useState<TaskTypeId>('research')
  const [title, setTitle] = useState('')

  const current = TASK_TYPES.find((t) => t.id === type)!
  const realBlocked = mode === 'real' && proxyOk === false

  const submit = () => {
    const value = title.trim() || current.presets[Math.floor(Math.random() * current.presets.length)]
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
            Симуляция
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
            Реальные модели
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
              {t.label}
            </button>
          ))}
        </div>

        <input
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') submit()
          }}
          placeholder={`Например: ${current.presets[0]}`}
          aria-label="Текст задачи"
          className="min-w-40 flex-1 rounded-md border border-input bg-background px-3 py-2 text-sm outline-none transition-colors placeholder:text-muted-foreground focus:border-ring focus:ring-1 focus:ring-ring"
        />

        <Button type="button" onClick={submit} disabled={realBlocked} className="gap-2 font-semibold">
          <SendHorizonal size={15} />
          Запустить задачу
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
            Авто-режим {auto ? 'вкл' : 'выкл'}
          </Button>
        ) : (
          <span
            className={cn(
              'flex items-center gap-2 rounded-md border px-3 py-1.5 text-xs',
              proxyOk ? 'border-emerald-500/40 text-emerald-400' : 'border-destructive/50 text-destructive',
            )}
            role="status"
          >
            <span
              className={cn('h-2 w-2 rounded-full', proxyOk ? 'bg-emerald-400' : 'bg-destructive')}
              aria-hidden="true"
            />
            {proxyOk === null ? 'проверка шлюза…' : proxyOk ? 'шлюз :4000 онлайн' : 'шлюз недоступен'}
          </span>
        )}
      </div>
      <p className="mt-1.5 text-[11px] text-muted-foreground">
        {mode === 'sim'
          ? 'Симуляция: корпорация показывает поток задач без реальных вызовов. Авто-режим берёт задачи из очереди каждые несколько секунд.'
          : realBlocked
            ? 'Шлюз не отвечает. Запустите его командой: litellm-server/start.sh — и вставьте ключи в litellm-server/.env'
            : 'Реальный режим: каждый этап выполняет настоящая модель через LiteLLM-шлюз. Ответы агентов появляются в журнале. Каждый запуск тратит токены.'}
      </p>
    </div>
  )
}

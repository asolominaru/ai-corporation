import { useState } from 'react'
import { LayoutDashboard, Workflow } from 'lucide-react'
import Header from '@/components/corp/Header'
import OrgPanel from '@/components/corp/OrgPanel'
import FlowCanvas from '@/components/corp/FlowCanvas'
import DashboardView from '@/components/corp/DashboardView'
import DeptSettings from '@/components/corp/DeptSettings'
import EventLog from '@/components/corp/EventLog'
import TaskLauncher from '@/components/corp/TaskLauncher'
import KanbanBoard from '@/components/corp/KanbanBoard'
import { useCorporationSim } from '@/hooks/useCorporationSim'
import { STRINGS } from '@/i18n'
import { cn } from '@/lib/utils'

type View = 'flow' | 'dash'

export default function Home() {
  const sim = useCorporationSim()
  const [selected, setSelected] = useState<string | null>(null)
  const [view, setView] = useState<View>('flow')
  const [settingsDept, setSettingsDept] = useState<string | null>(null)
  const s = STRINGS[sim.lang]

  const tabs: Array<{ id: View; label: string; icon: React.ReactNode }> = [
    { id: 'flow', label: s.viewFlow, icon: <Workflow size={13} /> },
    { id: 'dash', label: s.viewDash, icon: <LayoutDashboard size={13} /> },
  ]

  return (
    <div className="flex h-dvh min-h-0 flex-col bg-background text-foreground">
      <Header
        metrics={sim.metrics}
        activeCount={sim.tasks.length}
        busyCount={Object.keys(sim.busyByAgent).length}
        now={sim.now}
        lang={sim.lang}
        onLangChange={sim.setLang}
      />
      <div className="flex min-h-0 flex-1 flex-col lg:flex-row">
        <OrgPanel
          busyByAgent={sim.busyByAgent}
          selected={selected}
          onSelect={setSelected}
          onConfigure={setSettingsDept}
          lang={sim.lang}
        />
        <main className="flex min-w-0 flex-1 flex-col">
          {/* переключатель вида */}
          <div className="flex shrink-0 items-center gap-1 border-b border-border bg-card/30 px-4 py-1.5">
            {tabs.map((t) => (
              <button
                key={t.id}
                type="button"
                onClick={() => setView(t.id)}
                className={cn(
                  'flex items-center gap-1.5 rounded-md px-2.5 py-1 text-xs font-semibold transition-colors',
                  'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
                  view === t.id
                    ? 'bg-primary/15 text-primary'
                    : 'text-muted-foreground hover:bg-accent hover:text-foreground',
                )}
              >
                {t.icon}
                {t.label}
              </button>
            ))}
          </div>
          {view === 'flow' ? (
            <FlowCanvas
              now={sim.now}
              tasks={sim.tasks}
              busyByAgent={sim.busyByAgent}
              selected={selected}
              onSelect={setSelected}
              lang={sim.lang}
              overrides={sim.overrides}
            />
          ) : (
            <DashboardView
              tasks={sim.tasks}
              doneTasks={sim.doneTasks}
              metrics={sim.metrics}
              byTypeLaunched={sim.byTypeLaunched}
              reworks={sim.reworks}
              lang={sim.lang}
            />
          )}
          <KanbanBoard
            tasks={sim.tasks}
            doneTasks={sim.doneTasks}
            lang={sim.lang}
            onApprove={sim.approveTask}
            onReject={sim.rejectTask}
          />
          <TaskLauncher
            auto={sim.auto}
            onToggleAuto={sim.setAuto}
            onLaunch={sim.launchTask}
            mode={sim.mode}
            onModeChange={sim.setMode}
            proxyOk={sim.proxyOk}
            lang={sim.lang}
          />
        </main>
        <EventLog log={sim.log} onClear={sim.clearLog} lang={sim.lang} />
      </div>
      {settingsDept && (
        <DeptSettings
          deptId={settingsDept}
          lang={sim.lang}
          overrides={sim.overrides}
          onOverride={sim.setAgentOverride}
          onClose={() => setSettingsDept(null)}
        />
      )}
    </div>
  )
}

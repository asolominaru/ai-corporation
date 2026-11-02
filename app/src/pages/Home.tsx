import { useState } from 'react'
import Header from '@/components/corp/Header'
import OrgPanel from '@/components/corp/OrgPanel'
import FlowCanvas from '@/components/corp/FlowCanvas'
import EventLog from '@/components/corp/EventLog'
import TaskLauncher from '@/components/corp/TaskLauncher'
import ApprovalPanel from '@/components/corp/ApprovalPanel'
import { useCorporationSim } from '@/hooks/useCorporationSim'

export default function Home() {
  const sim = useCorporationSim()
  const [selected, setSelected] = useState<string | null>(null)

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
        <OrgPanel busyByAgent={sim.busyByAgent} selected={selected} onSelect={setSelected} lang={sim.lang} />
        <main className="flex min-w-0 flex-1 flex-col">
          <FlowCanvas
            now={sim.now}
            tasks={sim.tasks}
            busyByAgent={sim.busyByAgent}
            selected={selected}
            onSelect={setSelected}
            lang={sim.lang}
          />
          <ApprovalPanel tasks={sim.tasks} lang={sim.lang} onApprove={sim.approveTask} onReject={sim.rejectTask} />
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
    </div>
  )
}

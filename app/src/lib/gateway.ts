const GATEWAY_BASE = 'http://localhost:4000'
const GATEWAY_KEY = 'sk-corp-local'

export async function checkGateway(): Promise<boolean> {
  try {
    const res = await fetch(`${GATEWAY_BASE}/health/liveliness`, {
      signal: AbortSignal.timeout(3000),
    })
    return res.ok
  } catch {
    return false
  }
}

export interface AgentCallResult {
  ok: boolean
  text: string
}

export async function callAgent(
  agentId: string,
  system: string,
  user: string,
  modelOverride?: string,
): Promise<AgentCallResult> {
  try {
    const res = await fetch(`${GATEWAY_BASE}/v1/chat/completions`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${GATEWAY_KEY}`,
      },
      body: JSON.stringify({
        model: modelOverride ?? `agent-${agentId}`,
        messages: [
          { role: 'system', content: system },
          { role: 'user', content: user },
        ],
        max_tokens: 400,
      }),
      signal: AbortSignal.timeout(120000),
    })
    const data = await res.json()
    if (!res.ok) {
      const msg =
        data?.error?.message?.split('\n')[0] ?? `HTTP ${res.status}`
      return { ok: false, text: msg }
    }
    const text = data?.choices?.[0]?.message?.content?.trim()
    return text ? { ok: true, text } : { ok: false, text: 'пустой ответ модели' }
  } catch (e) {
    return { ok: false, text: e instanceof Error ? e.message : 'сеть недоступна' }
  }
}

type OpenAgentInput = {
  url?: string | null
}

export const buildOpenAgentUrl = (agent: OpenAgentInput): string => {
  const rawUrl = String(agent?.url || '').trim()
  if (!rawUrl) return ''
  return rawUrl
}

import { apiGet } from '../http'
import type { ChatUserAccessibleAgentsResponse, ChatUserCatalogResponse } from './types'

type FetchChatUsersParams = {
  page?: number
  page_size?: number
  q?: string
  source?: string[]
  binding?: 'bound' | 'unbound' | ''
}

export const fetchChatUsers = async (params: FetchChatUsersParams = {}) => {
  const search = new URLSearchParams()
  if (params.page) search.set('page', String(params.page))
  if (params.page_size) search.set('page_size', String(params.page_size))
  if (params.q?.trim()) search.set('q', params.q.trim())
  if (params.source?.length) {
    params.source
      .map((item) => item.trim())
      .filter(Boolean)
      .forEach((item) => search.append('source', item))
  }
  if (params.binding?.trim()) search.set('binding', params.binding.trim())
  const query = search.toString()
  return apiGet<ChatUserCatalogResponse>(`/admin/chat-users${query ? `?${query}` : ''}`)
}

export const fetchChatUserAccessibleAgents = async (chatUserId: string) => {
  return apiGet<ChatUserAccessibleAgentsResponse>(`/admin/chat-users/${chatUserId}/agents`)
}

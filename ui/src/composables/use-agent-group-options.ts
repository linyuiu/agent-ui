import { ref } from 'vue'
import { fetchAgentGroups } from '../services/groups'

export const useAgentGroupOptions = () => {
  const groupOptions = ref<string[]>([])

  const loadGroupOptions = async () => {
    try {
      const groups = await fetchAgentGroups()
      groupOptions.value = groups.map((group) => group.name)
    } catch {
      groupOptions.value = []
    }
  }

  return {
    groupOptions,
    loadGroupOptions,
  }
}

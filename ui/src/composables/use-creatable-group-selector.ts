import { computed, type Ref } from 'vue'

type GroupRecord = {
  name: string
}

type UseCreatableGroupSelectorParams = {
  groupOptions: Ref<string[]>
  selectedGroups: Ref<string[]>
  query: Ref<string>
  creating: Ref<boolean>
  error: Ref<string>
  createGroup: (payload: { name: string }) => Promise<GroupRecord>
  locale?: string
}

export const useCreatableGroupSelector = ({
  groupOptions,
  selectedGroups,
  query,
  creating,
  error,
  createGroup,
  locale = 'zh-Hans-CN',
}: UseCreatableGroupSelectorParams) => {
  const normalizeName = (value: string) => value.trim()

  const sortOptions = () => {
    groupOptions.value = [...groupOptions.value].sort((a, b) => a.localeCompare(b, locale))
  }

  const ensureGroupOption = (name: string) => {
    if (!groupOptions.value.includes(name)) {
      groupOptions.value = [...groupOptions.value, name]
      sortOptions()
    }
  }

  const filteredGroups = computed(() => {
    const keyword = query.value.trim().toLowerCase()
    return groupOptions.value.filter((group) => {
      if (!keyword) return true
      return group.toLowerCase().includes(keyword)
    })
  })

  const selectGroup = (name: string) => {
    if (!selectedGroups.value.includes(name)) {
      selectedGroups.value = [...selectedGroups.value, name]
    }
    query.value = ''
  }

  const removeGroup = (name: string) => {
    selectedGroups.value = selectedGroups.value.filter((item) => item !== name)
  }

  const createOrSelectFromQuery = async () => {
    const name = normalizeName(query.value)
    if (!name) return null

    if (groupOptions.value.includes(name)) {
      selectGroup(name)
      return name
    }

    creating.value = true
    error.value = ''
    try {
      const created = await createGroup({ name })
      const resolvedName = normalizeName(created.name) || name
      ensureGroupOption(resolvedName)
      selectGroup(resolvedName)
      return resolvedName
    } catch (err) {
      const message = err instanceof Error ? err.message : '新增分组失败'
      if ((message.includes('exists') || message.includes('已存在')) && groupOptions.value.includes(name)) {
        selectGroup(name)
        error.value = ''
        return name
      }
      error.value = message
      return null
    } finally {
      creating.value = false
    }
  }

  return {
    filteredGroups,
    selectGroup,
    removeGroup,
    createOrSelectFromQuery,
  }
}

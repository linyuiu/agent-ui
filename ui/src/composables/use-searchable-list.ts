import { computed, type Ref } from 'vue'

type ListRef<T> = Readonly<Ref<readonly T[]>>

export const includesKeyword = (keyword: string, ...fields: unknown[]) => {
  return fields.some((field) => String(field ?? '').toLowerCase().includes(keyword))
}

export const useSearchableList = <T>(
  items: ListRef<T>,
  search: Readonly<Ref<string>>,
  matcher: (item: T, keyword: string) => boolean,
) => {
  const filtered = computed<T[]>(() => {
    const keyword = search.value.trim().toLowerCase()
    if (!keyword) return [...items.value]
    return items.value.filter((item) => matcher(item, keyword))
  })

  return {
    filtered,
  }
}

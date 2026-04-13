import { ref } from 'vue'

type AsyncOrSyncHandler = () => void | Promise<void>

type UseImeFriendlyEnterOptions = {
  preventDefault?: boolean
}

export const useImeFriendlyEnter = (
  onEnter: AsyncOrSyncHandler,
  options: UseImeFriendlyEnterOptions = {}
) => {
  const isComposing = ref(false)
  const pendingEnter = ref(false)

  const handleCompositionStart = () => {
    isComposing.value = true
  }

  const handleCompositionEnd = async () => {
    isComposing.value = false
    if (!pendingEnter.value) return
    pendingEnter.value = false
    await onEnter()
  }

  const handleEnterKeydown = async (event: KeyboardEvent) => {
    if (event.isComposing || isComposing.value) {
      pendingEnter.value = true
      return
    }

    pendingEnter.value = false
    if (options.preventDefault) {
      event.preventDefault()
    }
    await onEnter()
  }

  return {
    handleCompositionStart,
    handleCompositionEnd,
    handleEnterKeydown,
  }
}

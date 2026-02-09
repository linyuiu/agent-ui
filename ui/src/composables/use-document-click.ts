import { onBeforeUnmount, onMounted } from 'vue'

export const useDocumentClick = (handler: (event: MouseEvent) => void) => {
  onMounted(() => {
    document.addEventListener('click', handler)
  })

  onBeforeUnmount(() => {
    document.removeEventListener('click', handler)
  })
}

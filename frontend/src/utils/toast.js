import { reactive } from 'vue'

// 全局轻提示：替代 alert，App.vue 负责渲染
export const toasts = reactive([])
let seed = 0

export function toast(message, type = 'info', duration = 3200) {
  const id = ++seed
  toasts.push({ id, message, type })
  setTimeout(() => dismissToast(id), duration)
  return id
}

export function dismissToast(id) {
  const i = toasts.findIndex((t) => t.id === id)
  if (i >= 0) toasts.splice(i, 1)
}

toast.success = (m, d) => toast(m, 'success', d)
toast.error = (m, d) => toast(m, 'error', d ?? 4200)
toast.info = (m, d) => toast(m, 'info', d)

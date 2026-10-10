import { synthesizeTTS } from '../api'

let activeAudio = null
let activeUrl = null

export function stopSpeech() {
  if (typeof window !== 'undefined' && 'speechSynthesis' in window) window.speechSynthesis.cancel()
  if (activeAudio) { activeAudio.pause(); activeAudio = null }
  if (activeUrl) { URL.revokeObjectURL(activeUrl); activeUrl = null }
}

export async function speakText(text, signal) {
  const clean = (text || '').replace(/[#*`]/g, '').trim()
  if (!clean || signal?.aborted) return
  if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
    await new Promise((resolve, reject) => {
      const utterance = new SpeechSynthesisUtterance(clean)
      utterance.lang = 'zh-CN'
      utterance.rate = 1.08
      const voices = window.speechSynthesis.getVoices()
      utterance.voice = voices.find((voice) => voice.lang?.toLowerCase().startsWith('zh') && voice.localService)
        || voices.find((voice) => voice.lang?.toLowerCase().startsWith('zh')) || null
      const finish = () => { signal?.removeEventListener('abort', abort); resolve() }
      const abort = () => { window.speechSynthesis.cancel(); finish() }
      utterance.onend = finish
      utterance.onerror = (event) => {
        signal?.removeEventListener('abort', abort)
        if (signal?.aborted || event.error === 'canceled' || event.error === 'interrupted') resolve()
        else reject(new Error('浏览器朗读暂不可用'))
      }
      signal?.addEventListener('abort', abort, { once: true })
      window.speechSynthesis.speak(utterance)
    })
    return
  }
  activeUrl = await synthesizeTTS(clean)
  if (signal?.aborted) { stopSpeech(); return }
  activeAudio = new Audio(activeUrl)
  await new Promise((resolve, reject) => {
    const abort = () => { stopSpeech(); resolve() }
    activeAudio.onended = () => { signal?.removeEventListener('abort', abort); resolve() }
    activeAudio.onerror = () => { signal?.removeEventListener('abort', abort); reject(new Error('语音暂不可用')) }
    signal?.addEventListener('abort', abort, { once: true })
    activeAudio.play().catch(reject)
  })
  stopSpeech()
}

// 语音输入：Web Speech API 持续监听，识别结果实时写回输入框。
import { ref, onBeforeUnmount } from 'vue'
import { toast } from '../utils/toast'

const ERROR_TEXT = {
  network: '语音识别服务不可用（需访问浏览器厂商的在线服务），请改用文字输入',
  'not-allowed': '麦克风权限被拒绝，请在浏览器设置中允许',
  'service-not-allowed': '语音识别服务不可用，请使用 Chrome / Edge'
}

export function useVoiceInput(onText) {
  const recognizing = ref(false)
  const SR = typeof window !== 'undefined' && (window.SpeechRecognition || window.webkitSpeechRecognition)
  const supported = Boolean(SR)
  let recognition = null
  let prefix = ''

  if (SR) {
    recognition = new SR()
    recognition.lang = 'zh-CN'
    recognition.continuous = true
    recognition.interimResults = true
    recognition.onresult = (e) => {
      let text = ''
      for (let i = 0; i < e.results.length; i++) text += e.results[i][0].transcript
      onText(prefix + text)
    }
    recognition.onend = () => { recognizing.value = false }
    recognition.onerror = (e) => {
      recognizing.value = false
      if (e.error === 'no-speech' || e.error === 'aborted') return
      toast.error(ERROR_TEXT[e.error] || '语音输入暂不可用，仍可打字回答')
    }
  }

  function toggle(currentText = '') {
    if (!recognition) return
    if (recognizing.value) {
      recognition.stop()
      recognizing.value = false
      return
    }
    prefix = currentText ? `${currentText} ` : ''
    try {
      recognition.start()
      recognizing.value = true
    } catch {
      recognizing.value = false
      toast.error('无法启动语音识别，请检查浏览器兼容性')
    }
  }

  function stop() {
    if (recognizing.value) recognition?.stop()
    recognizing.value = false
  }

  onBeforeUnmount(() => recognition?.abort())

  return { supported, recognizing, toggle, stop }
}

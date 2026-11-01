// 系统音频捕获：通过 getDisplayMedia 听取会议软件中的面试官声音，
// AudioWorklet 采集 16kHz PCM，每 3 秒切片并行送 ASR，边录边识别。
import { ref, onBeforeUnmount } from 'vue'
import { recognizeASR } from '../api'
import { toast } from '../utils/toast'

const CAPTURE_INTERVAL = 3000
const SAMPLE_RATE = 16000
const CHANNELS = 1

function writeString(view, offset, str) {
  for (let i = 0; i < str.length; i++) view.setUint8(offset + i, str.charCodeAt(i))
}

function encodeWav(samples, sampleRate, channels) {
  const bytesPerSample = 2
  const blockAlign = channels * bytesPerSample
  const dataSize = samples.length * bytesPerSample
  const buffer = new ArrayBuffer(44 + dataSize)
  const view = new DataView(buffer)
  writeString(view, 0, 'RIFF')
  view.setUint32(4, 36 + dataSize, true)
  writeString(view, 8, 'WAVE')
  writeString(view, 12, 'fmt ')
  view.setUint32(16, 16, true)
  view.setUint16(20, 1, true)
  view.setUint16(22, channels, true)
  view.setUint32(24, sampleRate, true)
  view.setUint32(28, sampleRate * blockAlign, true)
  view.setUint16(32, blockAlign, true)
  view.setUint16(34, bytesPerSample * 8, true)
  writeString(view, 36, 'data')
  view.setUint32(40, dataSize, true)
  let offset = 44
  for (let i = 0; i < samples.length; i++) {
    const s = Math.max(-1, Math.min(1, samples[i]))
    view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7fff, true)
    offset += 2
  }
  return new Blob([buffer], { type: 'audio/wav' })
}

export function useSystemAudio() {
  const listening = ref(false)
  const asrText = ref('')
  const asrBusy = ref(false)
  let pendingCount = 0
  let displayStream = null
  let audioContext = null
  let mediaSource = null
  let workletNode = null
  let captureTimer = null

  function stopDisplayStream() {
    displayStream?.getTracks().forEach((t) => t.stop())
    displayStream = null
  }

  async function processChunk(samples) {
    let peak = 0
    for (let i = 0; i < samples.length; i++) {
      const abs = Math.abs(samples[i])
      if (abs > peak) peak = abs
    }
    if (peak < 0.01) return // 静音段跳过
    pendingCount++
    asrBusy.value = true
    try {
      const text = await recognizeASR(encodeWav(samples, SAMPLE_RATE, CHANNELS))
      if (text) asrText.value += text
    } catch (e) {
      toast.error(e.message || '语音识别失败')
    } finally {
      pendingCount--
      asrBusy.value = pendingCount > 0
    }
  }

  async function start() {
    asrText.value = ''
    if (!navigator.mediaDevices?.getDisplayMedia) {
      toast.error('当前浏览器不支持系统音频捕获，请使用 Chrome / Edge')
      return
    }
    const AudioCtx = window.AudioContext || window.webkitAudioContext
    if (!AudioCtx) {
      toast.error('当前浏览器不支持 AudioContext，请升级浏览器')
      return
    }
    try {
      // 必须请求 video，浏览器才会弹出共享选择框
      displayStream = await navigator.mediaDevices.getDisplayMedia({
        video: true,
        audio: { echoCancellation: false, noiseSuppression: false, autoGainControl: false }
      })
    } catch (e) {
      if (e.name === 'NotAllowedError') toast.info('已取消共享。请重新选择并勾选“共享系统音频”')
      else if (e.name === 'NotReadableError') toast.error('屏幕捕获被占用，请先停止会议软件的屏幕共享后重试')
      else toast.error(`无法获取屏幕共享：${e.message}`)
      return
    }
    const audioTracks = displayStream.getAudioTracks()
    if (!audioTracks.length) {
      toast.error('未检测到系统音频，请在共享弹窗中勾选“共享系统音频”')
      stopDisplayStream()
      return
    }
    audioTracks[0].addEventListener('ended', () => stop())
    displayStream.getVideoTracks().forEach((t) => t.stop())

    audioContext = new AudioCtx({ sampleRate: SAMPLE_RATE })
    try {
      await audioContext.audioWorklet.addModule(new URL('../worklets/recorder-processor.js', import.meta.url))
    } catch {
      toast.error('录音模块加载失败，仍可文字作答')
      stop()
      return
    }
    mediaSource = audioContext.createMediaStreamSource(new MediaStream(audioTracks))
    workletNode = new AudioWorkletNode(audioContext, 'recorder-processor', {
      numberOfInputs: 1, numberOfOutputs: 1, channelCount: CHANNELS
    })
    mediaSource.connect(workletNode) // 不连 destination，避免回放
    workletNode.port.onmessage = (e) => {
      const { samples, length } = e.data || {}
      if (samples && length) processChunk(samples)
    }
    listening.value = true
    pendingCount = 0
    captureTimer = setInterval(() => workletNode?.port.postMessage('flush'), CAPTURE_INTERVAL)
    toast.success('已开始监听面试官声音')
  }

  function stop() {
    listening.value = false
    clearInterval(captureTimer)
    captureTimer = null
    if (workletNode) {
      try { workletNode.port.postMessage('flush') } catch { /* ignore */ }
      try { workletNode.disconnect() } catch { /* ignore */ }
      workletNode = null
    }
    try { mediaSource?.disconnect() } catch { /* ignore */ }
    mediaSource = null
    try { audioContext?.close() } catch { /* ignore */ }
    audioContext = null
    pendingCount = 0
    asrBusy.value = false
    stopDisplayStream()
  }

  function toggle() {
    return listening.value ? stop() : start()
  }

  onBeforeUnmount(stop)

  return { listening, asrText, asrBusy, start, stop, toggle }
}

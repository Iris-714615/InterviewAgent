/**
 * AudioWorklet 录音处理器
 * 在音频线程运行,主线程不卡顿
 * 作用:持续采集系统音频 PCM,主线程通过 port 请求时返回当前累积的样本
 */
class RecorderProcessor extends AudioWorkletProcessor {
  constructor() {
    super()
    this._chunks = []      // 累积的 Float32Array
    this._totalLength = 0  // 累积样本数
    // 主线程通过 port 请求数据
    this.port.onmessage = (e) => {
      if (e.data === 'flush') {
        // 返回当前累积的所有样本,并清空
        if (this._totalLength === 0) {
          this.port.postMessage({ samples: null, length: 0 })
          return
      }
        const merged = new Float32Array(this._totalLength)
        let offset = 0
        for (const chunk of this._chunks) {
          merged.set(chunk, offset)
          offset += chunk.length
        }
        this._chunks = []
        this._totalLength = 0
        this.port.postMessage({ samples: merged, length: merged.length }, [merged.buffer])
      }
    }
  }

  // 每次有音频数据时调用(128 帧一批)
  process(inputs) {
    const input = inputs[0]
    if (input && input[0] && input[0].length > 0) {
      // 复制一份存起来(原始 buffer 会被回收)
      const copy = new Float32Array(input[0])
      this._chunks.push(copy)
      this._totalLength += copy.length
    }
    return true
  }
}

registerProcessor('recorder-processor', RecorderProcessor)

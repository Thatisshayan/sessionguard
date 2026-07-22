import { useEffect, useRef, useCallback, useState } from 'react'

interface JobProgressData {
  job_id: number
  progress: number
  stage: string
  session_id?: number
}

interface JobCompleteData {
  job_id: number
  status: string
  session_id?: number
}

interface JobProgressMessage {
  type: 'job_progress'
  data: JobProgressData
}

interface JobCompleteMessage {
  type: 'job_complete'
  data: JobCompleteData
}

type WsMessage = JobProgressMessage | JobCompleteMessage

export function useJobWebSocket(
  onProgress?: (data: JobProgressData) => void,
  onComplete?: (data: JobCompleteData) => void
) {
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimer = useRef<ReturnType<typeof setTimeout>>()
  const [connected, setConnected] = useState(false)
  const onProgressRef = useRef(onProgress)
  const onCompleteRef = useRef(onComplete)

  useEffect(() => { onProgressRef.current = onProgress }, [onProgress])
  useEffect(() => { onCompleteRef.current = onComplete }, [onComplete])

  const connect = useCallback(() => {
    const base = import.meta.env.VITE_API_URL ?? 'http://127.0.0.1:8000'
    const wsUrl = base.replace(/^http/, 'ws') + '/ws/global'

    const ws = new WebSocket(wsUrl)
    wsRef.current = ws

    ws.onopen = () => setConnected(true)
    ws.onclose = () => {
      setConnected(false)
      reconnectTimer.current = setTimeout(connect, 5000)
    }

    ws.onmessage = (event) => {
      try {
        const msg: WsMessage = JSON.parse(event.data)
        if (msg.type === 'job_progress' && onProgressRef.current) {
          onProgressRef.current(msg.data)
        }
        if (msg.type === 'job_complete' && onCompleteRef.current) {
          onCompleteRef.current(msg.data)
        }
      } catch { /* ignore non-JSON */ }
    }
  }, [])

  useEffect(() => {
    connect()
    return () => {
      clearTimeout(reconnectTimer.current)
      wsRef.current?.close()
    }
  }, [connect])

  return { connected }
}

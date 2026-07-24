import { useEffect, useRef, useCallback, useState } from 'react'
import { useAuth } from '../context/AuthContext'

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
  const { accessToken } = useAuth()
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimer = useRef<ReturnType<typeof setTimeout>>()
  const [connected, setConnected] = useState(false)
  const onProgressRef = useRef(onProgress)
  const onCompleteRef = useRef(onComplete)

  useEffect(() => { onProgressRef.current = onProgress }, [onProgress])
  useEffect(() => { onCompleteRef.current = onComplete }, [onComplete])

  const connect = useCallback(() => {
    if (!accessToken) {
      setConnected(false)
      return
    }
    const base = import.meta.env.VITE_API_URL ?? 'http://127.0.0.1:8000'
    const url = new URL(base.replace(/^http/, 'ws') + '/ws/global')
    url.searchParams.set('token', accessToken)

    const ws = new WebSocket(url.toString())
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
  }, [accessToken])

  useEffect(() => {
    connect()
    return () => {
      clearTimeout(reconnectTimer.current)
      wsRef.current?.close()
    }
  }, [connect])

  return { connected }
}

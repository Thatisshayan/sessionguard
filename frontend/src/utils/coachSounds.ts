/**
 * src/utils/coachSounds.ts — Web Audio alert tones. No external files.
 */
const getCtx = (): AudioContext => {
  const w = window as any
  if (!w._sgAudio) w._sgAudio = new (window.AudioContext || w.webkitAudioContext)()
  return w._sgAudio
}
function beep(freq: number, dur: number, vol: number, type: OscillatorType = 'sine') {
  try {
    const c = getCtx(); const osc = c.createOscillator(); const gain = c.createGain()
    osc.connect(gain); gain.connect(c.destination); osc.type = type
    osc.frequency.setValueAtTime(freq, c.currentTime)
    gain.gain.setValueAtTime(vol, c.currentTime)
    gain.gain.exponentialRampToValueAtTime(0.001, c.currentTime + dur)
    osc.start(c.currentTime); osc.stop(c.currentTime + dur)
  } catch { /* blocked */ }
}
export function playCritical() {
  beep(880, 0.15, 0.4, 'square')
  setTimeout(() => beep(660, 0.15, 0.4, 'square'), 180)
  setTimeout(() => beep(440, 0.30, 0.5, 'square'), 360)
}
export function playWarning() {
  beep(660, 0.15, 0.3, 'triangle')
  setTimeout(() => beep(550, 0.25, 0.3, 'triangle'), 200)
}
export function playPositive() {
  beep(523, 0.1, 0.2, 'sine')
  setTimeout(() => beep(659, 0.1, 0.2, 'sine'), 120)
  setTimeout(() => beep(784, 0.2, 0.25, 'sine'), 240)
}
export function playCoachSound(type: string) {
  if (type === 'critical') playCritical()
  else if (type === 'warning') playWarning()
  else if (type === 'positive') playPositive()
  else beep(700, 0.2, 0.15, 'sine')
}

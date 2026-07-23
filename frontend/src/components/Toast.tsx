/**
 * src/components/Toast.tsx
 * -------------------------
 * Toast notification wrapper using sonner.
 * Provides toast.success, toast.error, toast.info helpers.
 * Maturity: Working Prototype
 */

import { Toaster, toast } from 'sonner'

export { toast }

export function ToastProvider() {
  return (
    <Toaster
      position="bottom-right"
      richColors
      closeButton
      duration={4000}
      toastOptions={{
        style: {
          background: 'var(--bg-surface)',
          border: '1px solid var(--bg-border)',
          color: 'var(--text-primary)',
          fontSize: 13,
        },
      }}
    />
  )
}

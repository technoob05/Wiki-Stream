import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'

// Error boundary to catch crashes
import { Component } from 'react'
class ErrorBoundary extends Component<{children: React.ReactNode}, {error: any}> {
  state = { error: null as any }
  static getDerivedStateFromError(error: any) { return { error } }
  render() {
    if (this.state.error) {
      return (
        <div style={{ color: '#ef4444', padding: 40, fontFamily: 'monospace', background: '#0a0a0c', minHeight: '100vh' }}>
          <h1 style={{ color: '#06b6d4' }}>Wiki-Stream Crash Report</h1>
          <pre style={{ color: '#f97316', whiteSpace: 'pre-wrap', marginTop: 20 }}>{String(this.state.error)}</pre>
          <pre style={{ color: '#6b7280', whiteSpace: 'pre-wrap', marginTop: 10, fontSize: 12 }}>{this.state.error?.stack}</pre>
        </div>
      )
    }
    return this.props.children
  }
}

import App from './App.tsx'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  </StrictMode>,
)

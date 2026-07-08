import { useState } from 'react'

function App() {
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)

  const check = async () => {
    setLoading(true)
    try {
      const response = await fetch('/api')
      const data = await response.json()
      setResult({ success: true, data })
    } catch (error) {
      setResult({ success: false, error: error.message })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ padding: '40px', fontFamily: 'sans-serif', textAlign: 'center' }}>
      <h1>App test</h1>
      <button onClick={check} disabled={loading}>
        {loading ? 'Checking...' : 'Sanity Check'}
      </button>

      {result && (
        <p style={{ marginTop: '20px', color: result.success ? 'green' : 'red' }}>
          {result.success ? JSON.stringify(result.data) : `Error: ${result.error}`}
        </p>
      )}
    </div>
  )
}

export default App
import { useState } from 'react'

function App() {
  const [file, setFile] = useState(null)
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)

  // Handle file selection from the input field
  const handleFileChange = (e) => {
    if (e.target.files) {
      setFile(e.target.files[0])
    }
  }

  const handleUpload = async () => {
    if (!file) {
      alert("Please select an Excel file first!")
      return
    }

    setLoading(true)
    setResult(null) // Reset previous results

    // 1. Create FormData and append the file
    // Crucial: The first argument 'file' MUST match your FastAPI parameter name exactly!
    const formData = new FormData()
    formData.append('file', file)

    try {
      // 2. Point this to your FastAPI endpoint URL
      const response = await fetch('/api/upload', {
        method: 'POST',
        body: formData, // Do NOT set Content-Type header manually; browser handles it
      })

      if (!response.ok) {
        throw new Error(`Server responded with status ${response.status}`)
      }

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
      <h1>Assessment Processor</h1>
      
      {/* File input container */}
      <div style={{ marginBottom: '20px' }}>
        <input 
          type="file" 
          accept=".xlsx, .xls" 
          onChange={handleFileChange} 
          disabled={loading}
        />
      </div>

      {/* Upload Button */}
      <button onClick={handleUpload} disabled={loading || !file}>
        {loading ? 'Processing Spreadsheet...' : 'Upload & Process'}
      </button>

      {/* Results / Error Display */}
      {result && (
        <div style={{ marginTop: '20px', color: result.success ? 'green' : 'red' }}>
          {result.success ? (
            <div>
              <h3>Upload Successful!</h3>
              <pre style={{ textAlign: 'left', display: 'inline-block', background: '#f4f4f4', padding: '15px', borderRadius: '5px' }}>
                {JSON.stringify(result.data, null, 2)}
              </pre>
            </div>
          ) : (
            <p>Error: {result.error}</p>
          )}
        </div>
      )}
    </div>
  )
}

export default App
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
  setLoading(true);
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch('/api/download-zip', { method: 'POST', body: formData });

  if (!response.ok) {
    const errorData = await response.json(); // if it failed, it's usually JSON error text
    setResult({ success: false, error: errorData.detail || "Upload failed" });
    setLoading(false);
    return;
  }

  // if we are here, it's the ZIP file
  const blob = await response.blob();
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'student_reports.zip';
  document.body.appendChild(a);
  a.click();
  a.remove();
  
  setLoading(false);
};

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
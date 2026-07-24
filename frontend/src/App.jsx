import { useState } from 'react'
import './App.css';

function App() {
  const [file, setFile] = useState(null)
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)

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
      const errorData = await response.json();
      setResult({ success: false, error: errorData.detail || "Upload failed" });
      setLoading(false);
      return;
    }

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
    <div>
      {/*top header bar*/ }
      <header className="app-header">
        <h1>Mt. SAC Chem Workbook Tool</h1>
      </header>

      {/* Centered card */}
      <div className="content-container">
        <div className="boarder-all" style={{ textAlign: 'center' }}>
          <h2 style={{ marginTop: 0, color: '#333' }}>Assessment Processor</h2>
          
          <div className="wr-input-control">
            <input 
              type="file" 
              accept=".xlsx, .xls" 
              onChange={handleFileChange} 
              disabled={loading}
            />
          </div>

          <button className="wr-btn" onClick={handleUpload} disabled={loading || !file}>
            {loading ? 'Processing Spreadsheet...' : 'Upload & Process'}
          </button>

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
      </div>
    </div>
  )
}

export default App;
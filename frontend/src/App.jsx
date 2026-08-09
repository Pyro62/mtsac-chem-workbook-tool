import { useState } from 'react'
import './App.css';

function App() {
  const [testFile, setTestFile] = useState(null)
  const [studentFile, setStudentFile] = useState(null)
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)

  const handleTestFileChange = (e) => {
    if (e.target.files) {
      setTestFile(e.target.files[0])
    }
  }

  const handleStudentFileChange = (e) => {
    if (e.target.files) {
      setStudentFile(e.target.files[0])
    }
  }

  const handleUpload = async () => {
    setLoading(true);
    const formData = new FormData();
    formData.append('test_file', testFile);
    formData.append('student_file', studentFile);

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
      <header className="app-header">
        <h1>Mt. SAC Chem Workbook Tool</h1>
      </header>

      <div className="content-container">
        <div className="boarder-all" style={{ textAlign: 'center' }}>
          <h2 style={{ marginTop: 0, color: '#333' }}>Assessment Processor</h2>
          
          <div className="wr-input-control">
            <label>Assessment File</label>
            <input 
              type="file" 
              accept=".xlsx, .xls" 
              onChange={handleTestFileChange} 
              disabled={loading}
            />
          </div>

          <div className="wr-input-control">
            <label>Student Info File</label>
            <input 
              type="file" 
              accept=".xlsx, .xls" 
              onChange={handleStudentFileChange} 
              disabled={loading}
            />
          </div>

          <button className="wr-btn" onClick={handleUpload} disabled={loading || !testFile || !studentFile}>
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
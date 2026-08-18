import { useState } from 'react'
import './App.css';

const validateExcelFile = (file) => {
  const validExtensions = ['.xls', '.xlsx'];
  const validMimeTypes = [
    'application/vnd.ms-excel', // .xls
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' // .xlsx
  ];

  const fileName = file.name.toLowerCase();
  const hasValidExtension = validExtensions.some(ext => fileName.endsWith(ext));
  const hasValidMimeType = validMimeTypes.includes(file.type);

  // Some browsers/OSes report an empty or generic MIME type for xls/xlsx,
  // so we accept the file if EITHER check passes, but reject if the
  // extension is clearly wrong (that catches renamed files reliably enough
  // for a client-side check).
  return hasValidExtension && (hasValidMimeType || file.type === '');
};
function App() {
  const [testFile, setTestFile] = useState(null)
  const [studentFile, setStudentFile] = useState(null)
  const [concatenate, setConcatenate] = useState(false)
  const [printReady, setPrintReady] = useState(false)
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [fileError, setFileError] = useState('');

  const handleTestFileChange = (e) => {
  const file = e.target.files?.[0];
  if (!file) {
    setTestFile(null);
    return;
  }
  if (!validateExcelFile(file)) {
    setFileError('Assessment File must be a .xls or .xlsx spreadsheet.');
    setTestFile(null);
    e.target.value = ''; // reset the input so they can re-pick
    return;
  }
  setFileError('');
  setTestFile(file);
};


  const handleStudentFileChange = (e) => {
  const file = e.target.files?.[0];
  if (!file) {
    setStudentFile(null);
    return;
  }
  if (!validateExcelFile(file)) {
    setFileError('Student Info File must be a .xls or .xlsx spreadsheet.');
    setStudentFile(null);
    e.target.value = '';
    return;
  }
  setFileError('');
  setStudentFile(file);
};

  // --- Handlers for Linked Checkbox Behavior ---
  const handleConcatenateChange = (e) => {
    const isChecked = e.target.checked
    setConcatenate(isChecked)
    // Unchecking concatenate also turns off printReady since printReady requires concatenated PDF
    if (!isChecked) {
      setPrintReady(false)
    }
  }

  const handlePrintReadyChange = (e) => {
    const isChecked = e.target.checked
    setPrintReady(isChecked)
    // Checking printReady forces concatenate to true
    if (isChecked) {
      setConcatenate(true)
    }
  }

  const handleUpload = async () => {
    setLoading(true);
    setResult(null);

    const formData = new FormData();
    formData.append('test_file', testFile);
    if (studentFile) {
      formData.append('student_file', studentFile);
    }
    
    // Append boolean flags as stringified values for FastAPI Form(...)
    formData.append('concatenate_files', concatenate);
    formData.append('print_ready', printReady);

    try {
      const response = await fetch('/api/download-zip', { method: 'POST', body: formData });

      if (!response.ok) {
        const errorData = await response.json();
        
        // Safe extraction of error string (prevents React object rendering crash)
        let formattedError = "Upload failed";
        if (typeof errorData.detail === 'string') {
          formattedError = errorData.detail;
        } else if (Array.isArray(errorData.detail)) {
          formattedError = errorData.detail.map(e => `${e.loc.join('.')}: ${e.msg}`).join(', ');
        } else if (typeof errorData.detail === 'object') {
          formattedError = JSON.stringify(errorData.detail);
        }

        setResult({ success: false, error: formattedError });
        setLoading(false);
        return;
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;

      // Infer default extension based on merge flags
      const isMerged = concatenate || printReady;
      const defaultFilename = isMerged ? 'student_reports.pdf' : 'student_reports.zip';

      // Use Content-Disposition filename from backend if present
      const contentDisposition = response.headers.get('Content-Disposition');
      let downloadFilename = defaultFilename;
      if (contentDisposition && contentDisposition.includes('filename=')) {
        downloadFilename = contentDisposition.split('filename=')[1].replace(/["']/g, '');
      }

      a.download = downloadFilename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);

      setResult({ success: true, data: { message: "Processing completed successfully!" } });
    } catch (err) {
      setResult({ success: false, error: err.message || "An unexpected error occurred." });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <header className="app-header">
        <h1>Mt. SAC Chem Workbook Tool</h1>
      </header>

      <div className="content-container">
        <div className="boarder-all" style={{ textAlign: 'center' }}>
          <h2 style={{ marginTop: 0, color: '#333' }}>ZipGrade  Assessment Processor</h2>
          
          <div className="wr-input-control">
            <label>Assessment File *</label>
            <input 
              type="file" 
              accept=".xlsx, .xls" 
              onChange={handleTestFileChange} 
              disabled={loading}
            />
          </div>

          <div className="wr-input-control">
            <label>Student Info File (Optional)</label>
            <input 
              type="file" 
              accept=".xlsx, .xls" 
              onChange={handleStudentFileChange} 
              disabled={loading}
            />
          </div>

          {fileError && (
          <p style={{ color: 'red', marginTop: '8px' }}>{fileError}</p>
          )}

          {/* Option Checkboxes */}
          <div style={{ margin: '15px 0', textAlign: 'left', display: 'inline-block' }}>
            <div style={{ marginBottom: '8px' }}>
              <label style={{ cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <input 
                  type="checkbox" 
                  checked={concatenate} 
                  onChange={handleConcatenateChange} 
                  disabled={loading}
                />
                Concatenate into single PDF
              </label>
            </div>

            <div>
              <label style={{ cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <input 
                  type="checkbox" 
                  checked={printReady} 
                  onChange={handlePrintReadyChange} 
                  disabled={loading}
                />
                Print Ready (Add blank page after each document)
              </label>
            </div>
          </div>

          <br />

          <button className="wr-btn" onClick={handleUpload} disabled={loading || !testFile}>
            {loading ? 'Processing Spreadsheet...' : 'Upload & Process'}
          </button>

          {result && (
            <div style={{ marginTop: '20px', color: result.success ? 'green' : 'red' }}>
              {result.success ? (
                <div>
                  <h3>Processing Successful!</h3>
                  <p>Your download should start automatically.</p>
                </div>
              ) : (
                <p>Error: {result.error}</p>
              )}
            </div>
          )}
        </div>
      </div>
    <a
      href="https://docs.google.com/forms/d/e/1FAIpQLSfNlUE8bO5rEcW01lfkG7QwK2qhhKJmzoK2uuIZO0uAA_acjg/viewform?usp=header"
      target="_blank"
      rel="noopener noreferrer"
      style={{
        position: 'fixed',
        bottom: '20px',
        left: '20px',
        zIndex: 9999,
        backgroundColor: '#0056b3',
        color: '#ffffff',
        padding: '8px 14px',
        borderRadius: '20px',
        textDecoration: 'none',
        fontSize: '13px',
        fontWeight: '600',
        boxShadow: '0 2px 8px rgba(0,0,0,0.15)',
        display: 'flex',
        alignItems: 'center',
        gap: '6px'
      }}
    >
      💬 Feedback
    </a>
    </div>
  )
}

export default App;
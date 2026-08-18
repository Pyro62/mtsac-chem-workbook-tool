import { useState, useRef } from 'react';
import './App.css';

const validateExcelFile = (file) => {
  const validExtensions = ['.xls', '.xlsx'];
  const validMimeTypes = [
    'application/vnd.ms-excel',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
  ];

  const fileName = file.name.toLowerCase();
  const hasValidExtension = validExtensions.some((ext) => fileName.endsWith(ext));
  const hasValidMimeType = validMimeTypes.includes(file.type);

  return hasValidExtension && (hasValidMimeType || file.type === '');
};

function App() {
  const [testFile, setTestFile] = useState(null);
  const [studentFile, setStudentFile] = useState(null);
  const [concatenate, setConcatenate] = useState(false);
  const [printReady, setPrintReady] = useState(false);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [fileError, setFileError] = useState('');

  // Refs to directly control the file input elements
  const testFileInputRef = useRef(null);
  const studentFileInputRef = useRef(null);

  // --- Clear Functions ---
  const clearTestFile = () => {
    setTestFile(null);
    setFileError('');
    if (testFileInputRef.current) {
      testFileInputRef.current.value = ''; // Resets the actual input UI
    }
  };

  const clearStudentFile = () => {
    setStudentFile(null);
    setFileError('');
    if (studentFileInputRef.current) {
      studentFileInputRef.current.value = ''; // Resets the actual input UI
    }
  };

  const handleTestFileChange = (e) => {
    const file = e.target.files?.[0];
    if (!file) {
      clearTestFile();
      return;
    }

    if (!validateExcelFile(file)) {
      setFileError('Assessment File must be a .xls or .xlsx spreadsheet.');
      clearTestFile();
      return;
    }

    setFileError('');
    setTestFile(file);
  };

  const handleStudentFileChange = (e) => {
    const file = e.target.files?.[0];
    if (!file) {
      clearStudentFile();
      return;
    }

    if (!validateExcelFile(file)) {
      setFileError('Student Info File must be a .xls or .xlsx spreadsheet.');
      clearStudentFile();
      return;
    }

    setFileError('');
    setStudentFile(file);
  };

  // --- Handlers for Linked Checkbox Behavior ---
  const handleConcatenateChange = (e) => {
    const isChecked = e.target.checked;
    setConcatenate(isChecked);
    if (!isChecked) {
      setPrintReady(false);
    }
  };

  const handlePrintReadyChange = (e) => {
    const isChecked = e.target.checked;
    setPrintReady(isChecked);
    if (isChecked) {
      setConcatenate(true);
    }
  };

  const handleUpload = async () => {
    setLoading(true);
    setResult(null);

    const formData = new FormData();
    formData.append('test_file', testFile);
    if (studentFile) {
      formData.append('student_file', studentFile);
    }

    formData.append('concatenate_files', concatenate);
    formData.append('print_ready', printReady);

    try {
      const response = await fetch('/api/download-zip', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        let formattedError = 'Upload failed';
        try {
          const errorData = await response.json();
          if (typeof errorData.detail === 'string') {
            formattedError = errorData.detail;
          } else if (Array.isArray(errorData.detail)) {
            formattedError = errorData.detail
              .map((e) => `${e.loc.join('.')}: ${e.msg}`)
              .join(', ');
          } else if (typeof errorData.detail === 'object') {
            formattedError = JSON.stringify(errorData.detail);
          }
        } catch {
          formattedError = `Server error (${response.status}: ${response.statusText})`;
        }

        setResult({ success: false, error: formattedError });
        return;
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;

      const isMerged = concatenate || printReady;
      const defaultFilename = isMerged ? 'student_reports.pdf' : 'student_reports.zip';

      const contentDisposition = response.headers.get('Content-Disposition');
      let downloadFilename = defaultFilename;

      if (contentDisposition && contentDisposition.includes('filename=')) {
        const matches = /filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/.exec(contentDisposition);
        if (matches != null && matches[1]) {
          downloadFilename = matches[1].replace(/['"]/g, '');
        }
      }

      a.download = downloadFilename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);

      setResult({
        success: true,
        data: { message: 'Processing completed successfully!' },
      });
    } catch (err) {
      setResult({
        success: false,
        error: err.message || 'An unexpected network error occurred.',
      });
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
        <div className="boarder-all">
          <h2 className="wr-card-title">ZipGrade Assessment Processor</h2>

          {/* Assessment File Input */}
          <div className="wr-input-control">
            <label htmlFor="test-file-input">Assessment File *</label>
            <div className="wr-file-row">
              <input
                id="test-file-input"
                type="file"
                accept=".xlsx, .xls"
                onChange={handleTestFileChange}
                disabled={loading}
                ref={testFileInputRef}
              />
              {/* Only renders if testFile state is populated */}
              {testFile && (
                <button
                  type="button"
                  onClick={clearTestFile}
                  disabled={loading}
                  className="wr-clear-btn"
                  title="Clear Assessment File"
                  aria-label="Clear Assessment File"
                >
                  ✖
                </button>
              )}
            </div>
          </div>

          {/* Student Info File Input */}
          <div className="wr-input-control">
            <label htmlFor="student-file-input">Student Info File (Optional)</label>
            <div className="wr-file-row">
              <input
                id="student-file-input"
                type="file"
                accept=".xlsx, .xls"
                onChange={handleStudentFileChange}
                disabled={loading}
                ref={studentFileInputRef}
              />
              {/* Only renders if studentFile state is populated */}
              {studentFile && (
                <button
                  type="button"
                  onClick={clearStudentFile}
                  disabled={loading}
                  className="wr-clear-btn"
                  title="Clear Student Info File"
                  aria-label="Clear Student Info File"
                >
                  ✖
                </button>
              )}
            </div>
          </div>

          {fileError && (
            <p className="wr-error-text" role="alert">
              {fileError}
            </p>
          )}

          {/* Option Checkboxes */}
          <div className="wr-options">
            <div className="wr-options-item">
              <label htmlFor="concatenate-checkbox">
                <input
                  id="concatenate-checkbox"
                  type="checkbox"
                  checked={concatenate}
                  onChange={handleConcatenateChange}
                  disabled={loading}
                />
                Concatenate into single PDF
              </label>
            </div>

            <div className="wr-options-item">
              <label htmlFor="print-ready-checkbox">
                <input
                  id="print-ready-checkbox"
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

          <button
            className="wr-btn"
            onClick={handleUpload}
            disabled={loading || !testFile}
          >
            {loading ? 'Processing Spreadsheet...' : 'Upload & Process'}
          </button>

          {result && (
            <div
              className={`wr-result ${result.success ? 'wr-result--success' : 'wr-result--error'}`}
              role="status"
            >
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
        className="wr-feedback-link"
      >
        💬 Feedback
      </a>
    </div>
  );
}

export default App;
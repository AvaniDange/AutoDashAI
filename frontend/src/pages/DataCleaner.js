import React, { useState } from 'react';
import logo from "../img/logo.png"; 

const DataCleaner = () => {
  const [file, setFile] = useState(null);
  const [analysis, setAnalysis] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const API_BASE_URL = "http://127.0.0.1:8000";

  const handleFileUpload = (event) => {
    const selectedFile = event.target.files[0];
    if (selectedFile) {
      setFile(selectedFile);
      setAnalysis(null);
      setError(null);
    }
  };

  const fetchData = async (endpoint, expectBlob = false) => {
    if (!file) return;

    setLoading(true);
    setError(null);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        let errText;
        try {
          const errorData = await response.json();
          errText = errorData.detail || "Unknown backend error";
        } catch {
          errText = await response.text();
        }
        throw new Error(errText);
      }

      if (expectBlob) {
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.style.display = 'none';
        a.href = url;
        a.download = `cleaned_${file.name}`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        setAnalysis(prev => ({ ...prev, downloadSuccess: true }));
      } else {
        const textData = await response.text();
        const data = JSON.parse(textData);
        console.log("Cleaned Preview Data:", data.cleaned_analysis?.preview);
        setAnalysis(data);
      }

    } catch (err) {
      console.error("Frontend fetch error:", err);
      setError(err.message || "An unexpected error occurred");
    } finally {
      setLoading(false);
    }
  };

  const analyzeFile = () => fetchData("/api/analyze");
  const cleanFile = () => fetchData("/api/clean", true);
  const cleanAndAnalyze = () => fetchData("/api/clean-and-analyze");

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 bg-fixed w-full">
      <header className="bg-white shadow-sm w-full">
        <div className="w-full px-6 py-4 flex justify-between items-center">
          <div className="flex items-center space-x-2">
            <img src={logo} alt="AutoDashAI Logo" className="w-15 h-10" />
            <span className="text-2xl font-bold text-blue-600">AutoDashAI</span>
          </div>
          <nav className="flex items-center space-x-6">
            <a href="#" className="text-gray-600 hover:text-blue-600 transition">Help</a>
          </nav>
        </div>
      </header>

      <section className="py-8 px-6 max-w-6xl mx-auto">
        <div className="bg-white rounded-2xl shadow-lg border border-gray-100 p-8">

          {/* Upload */}
          <div className="border-2 border-dashed border-gray-300 rounded-2xl p-8 text-center mb-8">
            <div className="w-32 h-32 mx-auto mb-6 flex items-center justify-center bg-blue-100 rounded-full">
              <span className="text-4xl">📊</span>
            </div>
            <input
              type="file"
              accept=".csv,.xlsx,.xls"
              onChange={handleFileUpload}
              className="hidden"
              id="file-upload"
            />
            <label
              htmlFor="file-upload"
              className="cursor-pointer bg-gradient-to-r from-purple-600 to-blue-500 text-white px-8 py-3 rounded-lg font-semibold hover:from-purple-700 hover:to-blue-600 transition-all duration-300 inline-block mb-4"
            >
              📁 Choose File
            </label>
            {file && (
              <p className="text-gray-600 mt-2">
                Selected: <span className="font-semibold">{file.name}</span> 
                ({(file.size / 1024 / 1024).toFixed(2)} MB)
              </p>
            )}
            <p className="text-gray-500 text-sm mt-2">Supported formats: CSV, Excel</p>
          </div>

          {/* Error */}
          {error && (
            <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded-lg mb-6">
              {error}
            </div>
          )}

          {/* Download Success */}
          {analysis?.downloadSuccess && (
            <div className="bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded-lg mb-6 text-center">
              ✅ Data cleaned successfully! Your download should start automatically.
            </div>
          )}

          {/* Buttons */}
          {file && (
            <div className="flex flex-wrap gap-4 justify-center mb-8">
              <button
                onClick={analyzeFile}
                disabled={loading}
                className="bg-blue-600 text-white px-6 py-3 rounded-lg font-semibold hover:bg-blue-700 transition disabled:opacity-50"
              >
                {loading ? '🔍 Analyzing...' : '🔍 Analyze Data'}
              </button>
              <button
                onClick={cleanFile}
                disabled={loading}
                className="bg-green-600 text-white px-6 py-3 rounded-lg font-semibold hover:bg-green-700 transition disabled:opacity-50"
              >
                {loading ? '⚡ Cleaning...' : '⚡ Clean & Download'}
              </button>
              <button
                onClick={cleanAndAnalyze}
                disabled={loading}
                className="bg-gradient-to-r from-purple-600 to-blue-500 text-white px-6 py-3 rounded-lg font-semibold hover:from-purple-700 hover:to-blue-600 transition disabled:opacity-50"
              >
                {loading ? '🚀 Processing...' : '🚀 Clean & Analyze'}
              </button>
            </div>
          )}

          {/* Analysis Results */}
          {analysis && !analysis.downloadSuccess && (
            <div className="space-y-6">

              {/* Info Cards */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
                <div className="bg-blue-50 p-4 rounded-lg text-center">
                  <div className="text-2xl font-bold text-blue-600">
                    {analysis.basic_info?.rows || analysis.original_analysis?.rows}
                  </div>
                  <div className="text-gray-600">Total Rows</div>
                </div>
                <div className="bg-green-50 p-4 rounded-lg text-center">
                  <div className="text-2xl font-bold text-green-600">
                    {analysis.basic_info?.columns || analysis.original_analysis?.columns}
                  </div>
                  <div className="text-gray-600">Total Columns</div>
                </div>
                <div className="bg-purple-50 p-4 rounded-lg text-center">
                  <div className="text-2xl font-bold text-purple-600">
                    {analysis.improvement !== undefined ? analysis.improvement : (analysis.issues?.length || 0)}
                  </div>
                  <div className="text-gray-600">
                    {analysis.improvement !== undefined ? 'Issues Fixed' : 'Issues Found'}
                  </div>
                </div>
              </div>

              {/* Issues */}
              <div className="bg-yellow-50 border border-yellow-200 rounded-2xl p-6">
                <h3 className="text-xl font-semibold text-gray-800 mb-4">📋 Detected Issues</h3>
                <div className="space-y-2">
                  {(analysis.issues || analysis.original_analysis?.issues || []).map((issue, index) => (
                    <div key={index} className="flex items-start space-x-2 text-yellow-800">
                      <span>⚠️</span>
                      <span>{issue.replace(/\*\*(.*?)\*\*/g, '$1')}</span>
                    </div>
                  ))}
                </div>
              </div>

             {/* ✅ Original Data Preview (works for both analyze and clean-and-analyze) */}
{(analysis.original_analysis?.preview || analysis.basic_info?.preview) && (
  <div className="bg-gray-50 rounded-2xl p-6">
    <h3 className="text-xl font-semibold text-gray-800 mb-4">👀 Original Data Preview</h3>
    <div className="overflow-x-auto">
      <table className="min-w-full bg-white rounded-lg overflow-hidden">
        <thead className="bg-gray-100">
          <tr>
            {Object.keys(analysis.original_analysis?.preview?.[0] || analysis.basic_info?.preview?.[0] || {}).map((header) => (
              <th key={header} className="px-4 py-2 text-left font-semibold text-gray-700">{header}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {(analysis.original_analysis?.preview || analysis.basic_info?.preview || []).map((row, index) => (
            <tr key={index} className={index % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
              {Object.values(row).map((val, i) => (
                <td key={i} className="px-4 py-2 border-t text-gray-600">{String(val)}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  </div>
)}

              {/* ✅ Cleaned Data Preview */}
              {analysis.cleaned_analysis && (
                <div className="bg-green-50 border border-green-200 rounded-2xl p-6">
                  <h3 className="text-xl font-semibold text-green-800 mb-4">✨ Cleaned Data Preview</h3>
                  <p className="text-green-700 mb-4">
                    Fixed {analysis.improvement} issues! Data is now cleaned and ready for analysis.
                  </p>

                  <div className="overflow-x-auto">
                    <table className="min-w-full bg-white rounded-lg overflow-hidden">
                      <thead className="bg-green-100">
                        <tr>
                          {Object.keys(analysis.cleaned_analysis.preview?.[0] || {}).map((header) => (
                            <th key={header} className="px-4 py-2 text-left font-semibold text-green-700">{header}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {analysis.cleaned_analysis.preview?.map((row, index) => (
                          <tr key={index} className={index % 2 === 0 ? 'bg-white' : 'bg-green-50'}>
                            {Object.values(row).map((val, i) => (
                              <td key={i} className="px-4 py-2 border-t text-gray-700">{String(val)}</td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>

                  {analysis.cleaned_analysis.issues?.length > 0 && (
                    <div className="mt-4">
                      <h4 className="font-semibold text-gray-700 mb-2">Remaining Issues:</h4>
                      {analysis.cleaned_analysis.issues.map((issue, index) => (
                        <div key={index} className="text-orange-700">⚠️ {issue.replace(/\*\*(.*?)\*\*/g, '$1')}</div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      </section>

      <footer className="bg-gray-800 text-white py-12 px-6 w-full mt-12 text-center">
        <p className="text-gray-400 text-lg">© 2024 AutoDash AI. All rights reserved.</p>
      </footer>
    </div>
  );
};

export default DataCleaner;

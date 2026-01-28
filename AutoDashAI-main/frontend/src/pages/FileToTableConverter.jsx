import React, { useState } from "react";
import logo from "../img/logo.png";

const FileToTableConverter = () => {
  const [files, setFiles] = useState([]);
  const [results, setResults] = useState({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);


  const API_BASE_URL = "http://127.0.0.1:8000";

  const handleFileUpload = (e) => {
    const selectedFiles = Array.from(e.target.files);
    setFiles(selectedFiles);
    setResults({});
    setError(null);
  };

  const handleExtract = async () => {
    if (!files.length) return;
    setLoading(true);
    setError(null);

    const formData = new FormData();
    files.forEach(file => {
      formData.append("files", file);
    });

    try {
      const res = await fetch(API_BASE_URL + "/process-files", {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Backend error: " + res.status);
      }

      const data = await res.json();
      setResults(data);
    } catch (err) {
      setError(err.message);
      console.error("Extraction error:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleDragOver = (e) => {
    e.preventDefault();
  };

  const handleDrop = (e) => {
    e.preventDefault();
    const droppedFiles = Array.from(e.dataTransfer.files);
    setFiles(droppedFiles);
    setResults({});
    setError(null);
  };

  const clearFiles = () => {
    setFiles([]);
    setResults({});
    setError(null);
  };

  // Download via backend: send JSON dataframe and request a CSV/XLSX
  const handleDownload = async (filename, dataframe, format) => {
    try {
      const payload = {
        dataframe: dataframe,
        format: format,
        filename: filename.replace(/\.[^/.]+$/, "") + "_extracted"
      };

      const res = await fetch(API_BASE_URL + "/download", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify(payload)
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Download error: " + res.status);
      }

      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = payload.filename + (format === "csv" ? ".csv" : ".xlsx");
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error("Download failed:", err);
      setError("Download failed: " + err.message);
    }
  };

  return React.createElement("div", { className: "min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 w-full" },
    // Header
    React.createElement("header", { className: "bg-white shadow-sm w-full" },
      React.createElement("div", { className: "w-full px-6 py-4 flex justify-between items-center" },
        React.createElement("div", { className: "flex items-center space-x-2" },
          React.createElement("img", { src: logo, alt: "AutoDashAI Logo", className: "w-15 h-10" }),
          React.createElement("span", { className: "text-2xl font-bold text-blue-600" }, "AutoDashAI")
        ),
        React.createElement("nav", { className: "flex items-center space-x-6" },
          React.createElement("a", { href: "#", className: "text-gray-600 hover:text-blue-600" }, "Help")
        )
      )
    ),

    // Main Content
    React.createElement("section", { className: "py-10 px-6 max-w-6xl mx-auto" },
      // Upload Section
      React.createElement("div", { className: "bg-white rounded-2xl shadow-lg border border-gray-100 p-8" },
        // File Drop Zone
        React.createElement("div", {
          className: "border-2 border-dashed border-gray-300 rounded-2xl p-8 text-center mb-8 transition-colors hover:border-blue-400",
          onDragOver: handleDragOver,
          onDrop: handleDrop
        },
          React.createElement("div", { className: "w-32 h-32 mx-auto mb-6 flex items-center justify-center bg-blue-100 rounded-full" },
            React.createElement("span", { className: "text-4xl" }, "\uD83D\uDCC4")
          ),
          React.createElement("input", {
            type: "file",
            accept: ".pdf,.docx,.xlsx,.csv,.png,.jpg,.jpeg,.txt",
            onChange: handleFileUpload,
            className: "hidden",
            id: "file-upload",
            multiple: true
          }),
          React.createElement("label", {
            htmlFor: "file-upload",
            className: "cursor-pointer bg-gradient-to-r from-purple-600 to-blue-500 text-white px-8 py-3 rounded-lg font-semibold hover:from-purple-700 hover:to-blue-600 transition-all duration-300 inline-block mb-4"
          }, "\uD83D\uDCC1 Choose Files"),
          React.createElement("p", { className: "text-gray-500 text-sm mt-2" }, "Drag & drop files here or click to browse"),

          // Selected Files List
          files.length > 0 && React.createElement("div", { className: "mt-4" },
            React.createElement("p", { className: "text-gray-600 font-semibold mb-2" }, "Selected Files (" + files.length + "):"),
            React.createElement("div", { className: "space-y-1 max-h-32 overflow-y-auto" },
              files.map((file, index) =>
                React.createElement("p", { key: index, className: "text-gray-600 text-sm" },
                  "\u2022 " + file.name + " (" + (file.size / 1024).toFixed(1) + " KB)")
              )
            )
          )
        ),

        // Error Display
        error && React.createElement("div", { className: "bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded-lg mb-6" },
          React.createElement("strong", null, "Error:"), " " + error
        ),

        // Action Buttons
        React.createElement("div", { className: "flex justify-center space-x-4" },
          React.createElement("button", {
            onClick: handleExtract,
            disabled: loading || files.length === 0,
            className: "bg-blue-600 text-white px-8 py-3 rounded-lg font-semibold hover:bg-blue-700 transition disabled:opacity-50 flex items-center space-x-2"
          },
            loading ? [
              React.createElement("span", { key: "loading-icon" }, "\u23F3"),
              React.createElement("span", { key: "loading-text" }, "Processing " + files.length + " files...")
            ] : [
              React.createElement("span", { key: "extract-icon" }, "\uD83D\uDE80"),
              React.createElement("span", { key: "extract-text" }, "Extract Data")
            ]
          ),
          files.length > 0 && React.createElement("button", {
            onClick: clearFiles,
            className: "bg-gray-500 text-white px-6 py-3 rounded-lg font-semibold hover:bg-gray-600 transition"
          }, "Clear Files")
        ),

        // Results Display
        Object.keys(results).length > 0 && React.createElement("div", { className: "mt-8 space-y-8" },
          React.createElement("h3", { className: "text-2xl font-semibold text-gray-800 text-center mb-6" }, "Extraction Results"),

          Object.entries(results).map(([filename, result]) =>
            React.createElement("div", {
              key: filename,
              className: "border border-gray-200 rounded-xl p-6 bg-white shadow-sm"
            },
              React.createElement("h4", { className: "text-lg font-semibold text-gray-800 mb-4" },
                filename,
                result.success && React.createElement("span", {
                  className: "ml-2 text-sm px-2 py-1 rounded-full " +
                    (result.has_structured_data ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800')
                }, result.has_structured_data ? '\u2705 Data Extracted' : '\uD83D\uDCDD Text Only')
              ),

              // Error Display for individual file
              !result.success && React.createElement("div", { className: "bg-red-50 border border-red-200 rounded-lg p-4 mb-4" },
                React.createElement("p", { className: "text-red-700" },
                  React.createElement("strong", null, "Error:"), " " + result.error)
              ),

              // Structured Data Display
              result.success && result.has_structured_data && React.createElement(React.Fragment, null,
                React.createElement("div", { className: "mb-4 text-sm text-gray-600" },
                  React.createElement("p", null,
                    React.createElement("strong", null, "Rows:"), " " + result.rows + " | ",
                    React.createElement("strong", null, "Columns:"), " " + result.columns),
                  React.createElement("p", null,
                    React.createElement("strong", null, "Columns:"), " " + (result.columns ? result.columns.join(', ') : ''))
                ),
                result.preview && result.preview.length > 0 && React.createElement("div", null,
                  React.createElement("h5", { className: "font-semibold text-gray-700 mb-3" }, "Data Preview:"),
                  React.createElement("div", { className: "overflow-x-auto border border-gray-200 rounded-lg" },
                    React.createElement("table", { className: "min-w-full bg-white" },
                      React.createElement("thead", { className: "bg-gray-50" },
                        React.createElement("tr", null,
                          Object.keys(result.preview[0]).map((header) =>
                            React.createElement("th", {
                              key: header,
                              className: "px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider border-b"
                            }, header)
                          )
                        )
                      ),
                      React.createElement("tbody", { className: "divide-y divide-gray-200" },
                        result.preview.map((row, i) =>
                          React.createElement("tr", { key: i, className: "hover:bg-gray-50" },
                            Object.values(row).map((val, j) =>
                              React.createElement("td", {
                                key: j,
                                className: "px-4 py-3 text-sm text-gray-600 whitespace-nowrap"
                              }, val !== null && val !== undefined ? String(val) : 'N/A')
                            )
                            )
                        )
                      )
                    )
                  )
                ),

                // Download buttons
                React.createElement("div", { className: "mt-4 flex space-x-3" },
                  React.createElement("button", {
                    onClick: () => handleDownload(filename, result.dataframe || result.preview, "csv"),
                    className: "bg-green-600 text-white px-4 py-2 rounded-lg font-semibold hover:bg-green-700"
                  }, "Download CSV"),
                  React.createElement("button", {
                    onClick: () => handleDownload(filename, result.dataframe || result.preview, "excel"),
                    className: "bg-indigo-600 text-white px-4 py-2 rounded-lg font-semibold hover:bg-indigo-700"
                  }, "Download Excel")
                )
              ),

              // Text Content Display
              result.success && result.has_text_content && !result.has_structured_data && React.createElement("div", { className: "bg-yellow-50 border border-yellow-200 rounded-lg p-4" },
                React.createElement("h5", { className: "font-semibold text-yellow-800 mb-2" }, "Text Content:"),
                React.createElement("p", { className: "text-gray-700 whitespace-pre-wrap text-sm" }, result.text_content)
              ),

              // No data extracted
              result.success && !result.has_structured_data && !result.has_text_content && React.createElement("div", { className: "bg-gray-50 border border-gray-200 rounded-lg p-4" },
                React.createElement("p", { className: "text-gray-700" }, "No structured data or text content could be extracted from this file.")
              )
            )
          )
        )
      )
    ),

    // Footer
    React.createElement("footer", { className: "bg-gray-800 text-white py-10 text-center mt-12" },
      React.createElement("p", { className: "text-gray-400 text-lg" }, "\u00A9 2025 AutoDashAI. All rights reserved.")
    )
  );
};

export default FileToTableConverter;

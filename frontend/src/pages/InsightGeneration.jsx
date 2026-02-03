import React, { useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Upload, FileText, ArrowLeft, Loader, BrainCircuit, Image, X } from 'lucide-react';

const InsightGeneration = () => {
    const navigate = useNavigate();
    const [file, setFile] = useState(null);
    const [preview, setPreview] = useState(null);
    const [loading, setLoading] = useState(false);
    const [insights, setInsights] = useState(null);
    const [error, setError] = useState(null);
    const fileInputRef = useRef(null);

    const API_BASE_URL = "http://127.0.0.1:8000";

    const handleFileChange = (e) => {
        const selectedFile = e.target.files[0];
        if (selectedFile) {
            setFile(selectedFile);
            setError(null);
            setInsights(null);

            // Create preview for images
            if (selectedFile.type.startsWith('image/')) {
                const reader = new FileReader();
                reader.onloadend = () => {
                    setPreview(reader.result);
                };
                reader.readAsDataURL(selectedFile);
            } else {
                setPreview(null);
            }
        }
    };

    const clearFile = () => {
        setFile(null);
        setPreview(null);
        setInsights(null);
        setError(null);
        if (fileInputRef.current) {
            fileInputRef.current.value = '';
        }
    };

    const generateInsights = async () => {
        if (!file) return;

        setLoading(true);
        setError(null);

        const formData = new FormData();
        formData.append('file', file);

        try {
            const response = await fetch(`${API_BASE_URL}/api/insights/generate`, {
                method: 'POST',
                body: formData,
            });

            if (!response.ok) {
                const errData = await response.json().catch(() => ({}));
                throw new Error(errData.detail || "Failed to generate insights");
            }

            const data = await response.json();
            setInsights(data.insights);

        } catch (err) {
            console.error("Insight generation error:", err);
            setError(err.message || "Something went wrong. Please try again.");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="min-h-screen bg-gray-50 flex flex-col font-sans text-gray-800">
            {/* Header */}
            <header className="bg-white shadow-sm flex items-center px-8 py-5">
                <button onClick={() => navigate('/homepage')} className="mr-6 p-2 rounded-full hover:bg-gray-100 transition-colors">
                    <ArrowLeft className="w-6 h-6 text-gray-600" />
                </button>
                <div className="flex items-center gap-3">
                    <div className="p-2 bg-purple-100 rounded-lg text-purple-600">
                        <BrainCircuit size={28} />
                    </div>
                    <div>
                        <h1 className="text-2xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-purple-600 to-indigo-600">
                            AI Insight Generation
                        </h1>
                        <p className="text-sm text-gray-500">Upload a dashboard image or PDF to get AI-powered insights.</p>
                    </div>
                </div>
            </header>

            {/* Main Content */}
            <main className="flex-1 max-w-5xl w-full mx-auto p-8">

                {/* Upload Section */}
                <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-10 mb-8 transition-all hover:shadow-md">

                    {!file ? (
                        <div className="flex flex-col items-center justify-center border-2 border-dashed border-purple-200 rounded-xl p-12 bg-purple-50/30 hover:bg-purple-50/50 transition-colors cursor-pointer group relative">
                            <input
                                ref={fileInputRef}
                                type="file"
                                accept="image/png, image/jpeg, image/jpg, image/webp, application/pdf"
                                onChange={handleFileChange}
                                className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                            />
                            <div className="bg-white p-4 rounded-full shadow-md mb-4 group-hover:scale-110 transition-transform duration-300">
                                <Image className="w-8 h-8 text-purple-600" />
                            </div>
                            <h3 className="text-lg font-semibold text-gray-700 mb-2">
                                Click to upload or drag & drop
                            </h3>
                            <p className="text-gray-500 text-sm">
                                Supported formats: PNG, JPEG, WebP, PDF
                            </p>
                        </div>
                    ) : (
                        <div className="space-y-6">
                            {/* Preview Area */}
                            <div className="relative bg-gray-100 rounded-xl p-4 flex flex-col items-center">
                                <button
                                    onClick={clearFile}
                                    className="absolute top-2 right-2 p-1.5 bg-red-100 text-red-600 rounded-full hover:bg-red-200 transition-colors"
                                >
                                    <X size={18} />
                                </button>

                                {preview ? (
                                    <img
                                        src={preview}
                                        alt="Dashboard preview"
                                        className="max-h-80 rounded-lg shadow-md object-contain"
                                    />
                                ) : (
                                    <div className="flex items-center gap-3 py-8">
                                        <FileText className="w-10 h-10 text-purple-600" />
                                        <span className="text-gray-700 font-medium">{file.name}</span>
                                    </div>
                                )}

                                <p className="mt-3 text-sm text-gray-500">
                                    {file.name} ({(file.size / 1024 / 1024).toFixed(2)} MB)
                                </p>
                            </div>

                            {/* Generate Button */}
                            <div className="flex justify-center">
                                <button
                                    onClick={generateInsights}
                                    disabled={loading}
                                    className={`
                                        flex items-center gap-2 px-8 py-3 rounded-xl text-white font-medium shadow-lg hover:shadow-xl transition-all transform active:scale-95
                                        ${loading ? "bg-gray-400 cursor-not-allowed" : "bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-700 hover:to-indigo-700"}
                                    `}
                                >
                                    {loading ? (
                                        <>
                                            <Loader className="animate-spin w-5 h-5" />
                                            Analyzing with AI...
                                        </>
                                    ) : (
                                        <>
                                            <BrainCircuit className="w-5 h-5" />
                                            Generate Insights
                                        </>
                                    )}
                                </button>
                            </div>
                        </div>
                    )}

                    {error && (
                        <div className="mt-4 p-4 bg-red-50 text-red-600 rounded-lg text-center border border-red-100">
                            {error}
                        </div>
                    )}
                </div>

                {/* Results Section */}
                {insights && (
                    <div className="space-y-6">
                        <h2 className="text-xl font-bold text-gray-800 flex items-center gap-2">
                            <FileText className="w-5 h-5 text-gray-500" />
                            Key Findings from Your Dashboard
                        </h2>

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                            {insights.map((insight, index) => (
                                <div key={index} className="bg-white p-6 rounded-2xl shadow-sm border border-gray-100 hover:shadow-md transition-shadow relative overflow-hidden group">
                                    <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity">
                                        <BrainCircuit size={64} className="text-purple-600" />
                                    </div>
                                    <h3 className="text-lg font-bold text-gray-800 mb-2 group-hover:text-purple-600 transition-colors">{insight.title}</h3>
                                    <p className="text-gray-600 leading-relaxed text-sm">
                                        {insight.description}
                                    </p>
                                </div>
                            ))}
                        </div>
                    </div>
                )}
            </main>
        </div>
    );
};

export default InsightGeneration;

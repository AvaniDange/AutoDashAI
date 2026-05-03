import React, { useState, useRef, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { auth } from '../firebase';
import {
    Upload, FileText, ArrowLeft, Loader, BrainCircuit, Image,
    X, FileSpreadsheet, File, Clock, Sparkles, ChevronRight, BookmarkCheck,
    Languages, Lightbulb, TrendingUp, Target, UserCircle2, RefreshCw
} from 'lucide-react';

const INSIGHT_LANGUAGES = [
    { value: 'English', label: 'English', flag: '🌐' },
    { value: 'Hindi', label: 'हिंदी', flag: '🇮🇳' },
    { value: 'Marathi', label: 'मराठी', flag: '🇮🇳' },
    { value: 'Gujarati', label: 'ગુજરાતી', flag: '🇮🇳' },
    { value: 'Tamil', label: 'தமிழ்', flag: '🇮🇳' },
    { value: 'Telugu', label: 'తెలుగు', flag: '🇮🇳' },
    { value: 'Kannada', label: 'ಕನ್ನಡ', flag: '🇮🇳' },
    { value: 'Bengali', label: 'বাংলা', flag: '🇮🇳' },
    { value: 'Punjabi', label: 'ਪੰਜਾਬੀ', flag: '🇮🇳' },
    { value: 'Malayalam', label: 'മലയാളം', flag: '🇮🇳' },
    { value: 'Odia', label: 'ଓଡ଼ିଆ', flag: '🇮🇳' },
    { value: 'Assamese', label: 'অসমীয়া', flag: '🇮🇳' },
];

const InsightGeneration = () => {
    const navigate = useNavigate();
    const [file, setFile] = useState(null);
    const [preview, setPreview] = useState(null);
    const [loading, setLoading] = useState(false);
    const [insights, setInsights] = useState(null);
    const [error, setError] = useState(null);
    const [dragActive, setDragActive] = useState(false);
    const fileInputRef = useRef(null);
    const [selectedLanguage, setSelectedLanguage] = useState(() => {
        try { return localStorage.getItem('vidhur_insight_lang') || 'English'; }
        catch { return 'English'; }
    });
    const [viewMode, setViewMode] = useState('picker'); // 'picker' | 'upload' | 'saved'

    // Saved visualizations
    const [savedViz, setSavedViz] = useState([]);
    const [loadingSaved, setLoadingSaved] = useState(false);
    const [savedInsightsLoading, setSavedInsightsLoading] = useState(null);
    const [successToast, setSuccessToast] = useState('');

    const API_BASE_URL = "http://127.0.0.1:8000";
    const userEmail = auth.currentUser?.email || '';

    // Fetch saved visualizations on mount
    const fetchSavedVisualizations = useCallback(async () => {
        if (!userEmail) return;
        setLoadingSaved(true);
        try {
            const res = await fetch(`${API_BASE_URL}/api/visualizations/list?email=${encodeURIComponent(userEmail)}`);
            const data = await res.json();
            if (data.success) {
                setSavedViz(data.visualizations || []);
            }
        } catch (err) {
            console.error("Failed to load saved visualizations:", err);
        } finally {
            setLoadingSaved(false);
        }
    }, [userEmail, API_BASE_URL]);

    useEffect(() => {
        fetchSavedVisualizations();
    }, [fetchSavedVisualizations]);

    // Persist language selection
    useEffect(() => {
        try { localStorage.setItem('vidhur_insight_lang', selectedLanguage); }
        catch { /* ignore */ }
    }, [selectedLanguage]);

    // File type helpers
    const ACCEPTED_TYPES = [
        'image/png', 'image/jpeg', 'image/jpg', 'image/webp',
        'application/pdf',
        'text/csv', 'application/csv',
        'application/vnd.ms-excel',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'application/msword',
    ];

    const ACCEPT_STRING = ".png,.jpg,.jpeg,.webp,.pdf,.csv,.xlsx,.xls,.docx,.doc";

    const getFileIcon = (type, name) => {
        if (type?.startsWith('image/')) return <Image className="w-6 h-6" />;
        if (name?.endsWith('.csv') || name?.endsWith('.xlsx') || name?.endsWith('.xls') || type?.includes('spreadsheet') || type?.includes('excel') || type?.includes('csv'))
            return <FileSpreadsheet className="w-6 h-6" />;
        if (name?.endsWith('.pdf') || type === 'application/pdf') return <FileText className="w-6 h-6" />;
        return <File className="w-6 h-6" />;
    };

    const getFileCategory = (type, name) => {
        if (type?.startsWith('image/')) return 'Image';
        if (name?.endsWith('.csv') || type?.includes('csv')) return 'CSV Data';
        if (name?.endsWith('.xlsx') || name?.endsWith('.xls') || type?.includes('spreadsheet') || type?.includes('excel')) return 'Excel Data';
        if (name?.endsWith('.pdf') || type === 'application/pdf') return 'PDF Document';
        if (name?.endsWith('.docx') || name?.endsWith('.doc') || type?.includes('word')) return 'Word Document';
        return 'File';
    };

    const handleFileChange = (e) => {
        const selectedFile = e.target.files[0];
        if (selectedFile) processFile(selectedFile);
    };

    const processFile = (selectedFile) => {
        setFile(selectedFile);
        setError(null);
        setInsights(null);

        if (selectedFile.type.startsWith('image/')) {
            const reader = new FileReader();
            reader.onloadend = () => setPreview(reader.result);
            reader.readAsDataURL(selectedFile);
        } else {
            setPreview(null);
        }
    };

    const clearFile = () => {
        setFile(null);
        setPreview(null);
        setInsights(null);
        setError(null);
        if (fileInputRef.current) fileInputRef.current.value = '';
    };

    // Drag and drop
    const handleDrag = (e) => {
        e.preventDefault();
        e.stopPropagation();
        if (e.type === 'dragenter' || e.type === 'dragover') setDragActive(true);
        else if (e.type === 'dragleave') setDragActive(false);
    };

    const handleDrop = (e) => {
        e.preventDefault();
        e.stopPropagation();
        setDragActive(false);
        if (e.dataTransfer.files && e.dataTransfer.files[0]) {
            processFile(e.dataTransfer.files[0]);
        }
    };

    // Generate insights from uploaded file
    const generateInsights = async () => {
        if (!file) return;
        setLoading(true);
        setError(null);

        const formData = new FormData();
        formData.append('file', file);
        formData.append('language', selectedLanguage);

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

    // Generate insights from a saved visualization
    const generateFromSaved = async (viz) => {
        setSavedInsightsLoading(viz.filename);
        setError(null);
        setInsights(null);

        try {
            const response = await fetch(`${API_BASE_URL}/api/visualizations/insights`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email: userEmail, filename: viz.filename, language: selectedLanguage }),
            });

            if (!response.ok) {
                const errData = await response.json().catch(() => ({}));
                throw new Error(errData.detail || "Failed to generate insights");
            }

            const data = await response.json();
            setInsights(data.insights);
            setFile(null);
            setPreview(viz.thumbnail);

            // Scroll to results
            setTimeout(() => {
                document.getElementById('insights-results')?.scrollIntoView({ behavior: 'smooth' });
            }, 100);
        } catch (err) {
            console.error("Saved insight error:", err);
            setError(err.message || "Failed to analyze saved visualization.");
        } finally {
            setSavedInsightsLoading(null);
        }
    };

    const showToast = (msg) => {
        setSuccessToast(msg);
        setTimeout(() => setSuccessToast(''), 3000);
    };

    const getInsightIcon = (index) => {
        const icons = [
            <Sparkles size={16} />,
            <TrendingUp size={16} />,
            <Target size={16} />,
            <Lightbulb size={16} />,
            <BrainCircuit size={16} />,
            <Sparkles size={16} />,
        ];
        return icons[index % icons.length];
    };

    const getInsightGradient = (index) => {
        const gradients = [
            'from-purple-500/20 to-indigo-500/20 border-purple-500/20',
            'from-emerald-500/20 to-teal-500/20 border-emerald-500/20',
            'from-amber-500/20 to-orange-500/20 border-amber-500/20',
            'from-blue-500/20 to-cyan-500/20 border-blue-500/20',
            'from-pink-500/20 to-rose-500/20 border-pink-500/20',
            'from-violet-500/20 to-fuchsia-500/20 border-violet-500/20',
        ];
        return gradients[index % gradients.length];
    };

    const getIconColor = (index) => {
        const colors = ['text-purple-400', 'text-emerald-400', 'text-amber-400', 'text-blue-400', 'text-pink-400', 'text-violet-400'];
        return colors[index % colors.length];
    };

    return (
        <div className="min-h-screen w-full bg-gray-50 flex flex-col font-sans text-gray-900 border-x border-gray-200">

            {/* Success Toast */}
            {successToast && (
                <div className="fixed top-6 right-6 z-50 bg-emerald-50 text-emerald-700 px-6 py-3 rounded-xl shadow-lg border border-emerald-200 flex items-center gap-2">
                    <BookmarkCheck size={20} className="text-emerald-500" />
                    <span className="font-semibold">{successToast}</span>
                </div>
            )}

            {/* Header */}
            <header className="bg-white border-b border-gray-200 flex items-center px-8 py-5 sticky top-0 z-40">
                <button
                    onClick={() => {
                        if (viewMode !== 'picker') setViewMode('picker');
                        else navigate('/homepage');
                    }}
                    className="mr-6 p-2 rounded-xl hover:bg-gray-100 transition-colors group"
                >
                    <ArrowLeft className="w-5 h-5 text-gray-500 group-hover:text-gray-900 transition-colors" />
                </button>
                <div className="flex items-center gap-4 flex-1">
                    <div className="p-3 bg-indigo-50 rounded-2xl border border-indigo-100">
                        <BrainCircuit size={28} className="text-indigo-600" />
                    </div>
                    <div>
                        <h1 className="text-2xl font-black tracking-tight text-gray-900">
                            Vidhur Insight Engine
                        </h1>
                        <p className="text-sm text-gray-500 font-medium mt-0.5">
                            Deep AI-powered business insights for your visualizations
                        </p>
                    </div>
                </div>
                {/* Profile Icon → Home */}
                <button
                    onClick={() => navigate('/homepage')}
                    className="p-2.5 rounded-xl bg-gray-100 hover:bg-gray-200 transition-colors text-gray-600 hover:text-indigo-600"
                    title="Go to Home"
                >
                    <UserCircle2 size={22} />
                </button>
            </header>

            {/* Main Content */}
            <main className="flex-1 w-full max-w-6xl mx-auto p-8 space-y-8">

                {viewMode === 'picker' && (
                    <div className="flex flex-col items-center justify-center py-20 px-4">
                        <h2 className="text-3xl font-black text-gray-900 mb-4 text-center">What would you like to analyze?</h2>
                        <p className="text-gray-500 mb-12 text-center max-w-lg">Choose a snapshot from your dashboard history to analyze, or upload an entirely new visualization or document.</p>
                        
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 w-full max-w-4xl">
                            {/* Option 1: Saved Dashboards */}
                            <button
                                onClick={() => setViewMode('saved')}
                                className="flex flex-col items-center text-center p-10 bg-white border border-gray-200 rounded-3xl shadow-sm hover:shadow-xl hover:border-indigo-300 transition-all group"
                            >
                                <div className="w-20 h-20 bg-indigo-50 rounded-2xl flex items-center justify-center mb-6 group-hover:scale-110 transition-transform">
                                    <BookmarkCheck size={40} className="text-indigo-600" />
                                </div>
                                <h3 className="text-xl font-bold text-gray-900 mb-2">Use Saved Dashboard</h3>
                                <p className="text-gray-500 text-sm leading-relaxed">
                                    Generate insights from previously saved dashboard visualizations stored in your account.
                                </p>
                            </button>

                            {/* Option 2: Upload New Visualization */}
                            <button
                                onClick={() => setViewMode('upload')}
                                className="flex flex-col items-center text-center p-10 bg-white border border-gray-200 rounded-3xl shadow-sm hover:shadow-xl hover:border-indigo-300 transition-all group"
                            >
                                <div className="w-20 h-20 bg-indigo-50 rounded-2xl flex items-center justify-center mb-6 group-hover:scale-110 transition-transform">
                                    <Upload size={40} className="text-indigo-600" />
                                </div>
                                <h3 className="text-xl font-bold text-gray-900 mb-2">Upload New Visualization</h3>
                                <p className="text-gray-500 text-sm leading-relaxed">
                                    Upload a new chart, spreadsheet, or document to immediately get AI generated business insights.
                                </p>
                            </button>
                        </div>
                    </div>
                )}

                {viewMode === 'upload' && (
                    <section className="bg-white rounded-3xl border border-gray-200 shadow-sm p-8">
                        <div className="flex justify-between items-center mb-6">
                            <h2 className="text-xl font-bold text-gray-900 flex items-center gap-2">
                                <Sparkles size={20} className="text-indigo-500" /> Upload Visualization
                            </h2>
                        </div>

                        {!file ? (
                            <div
                                className={`flex flex-col items-center justify-center border-2 border-dashed rounded-2xl p-14 transition-all duration-300 cursor-pointer group relative ${dragActive
                                        ? 'border-indigo-500 bg-indigo-50 scale-[1.01]'
                                        : 'border-gray-300 hover:border-indigo-400 hover:bg-gray-50'
                                    }`}
                                onDragEnter={handleDrag}
                                onDragLeave={handleDrag}
                                onDragOver={handleDrag}
                                onDrop={handleDrop}
                            >
                                <input
                                    ref={fileInputRef}
                                    type="file"
                                    accept={ACCEPT_STRING}
                                    onChange={handleFileChange}
                                    className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                                />
                                <div className={`p-5 rounded-2xl mb-5 transition-all duration-500 ${dragActive
                                        ? 'bg-indigo-100 scale-110'
                                        : 'bg-indigo-50 group-hover:bg-indigo-100 group-hover:scale-110'
                                    }`}>
                                    <Upload className="w-8 h-8 text-indigo-600" />
                                </div>
                                <h3 className="text-xl font-bold text-gray-900 mb-2">
                                    {dragActive ? 'Drop your file here!' : 'Click to upload or drag & drop'}
                                </h3>
                                <p className="text-gray-500 text-sm font-medium mb-4">
                                    Drop your charts, screenshots, or data files here
                                </p>

                                {/* File type badges */}
                                <div className="flex flex-wrap justify-center gap-2 mt-2">
                                    {['PNG', 'JPEG', 'PDF', 'Excel', 'CSV', 'DOCX'].map(fmt => (
                                        <span key={fmt} className="px-3 py-1 rounded-full bg-gray-100 text-xs font-bold text-gray-500 uppercase tracking-wide">
                                            {fmt}
                                        </span>
                                    ))}
                                </div>
                            </div>
                        ) : (
                            <div className="space-y-6">
                                {/* File Preview */}
                                <div className="relative bg-gray-50 rounded-2xl p-6 flex flex-col items-center border border-gray-200">
                                    <button
                                        onClick={clearFile}
                                        className="absolute top-4 right-4 p-2 bg-white text-gray-500 rounded-xl hover:bg-red-50 hover:text-red-600 shadow-sm transition-all"
                                    >
                                        <X size={18} />
                                    </button>

                                    {preview ? (
                                        <img
                                            src={preview}
                                            alt="Preview"
                                            className="max-h-72 rounded-xl shadow-md object-contain border border-gray-200"
                                        />
                                    ) : (
                                        <div className="flex items-center gap-4 py-10">
                                            <div className="p-4 bg-indigo-50 rounded-2xl text-indigo-600">
                                                {getFileIcon(file.type, file.name)}
                                            </div>
                                            <div>
                                                <span className="text-gray-900 font-bold text-lg block">{file.name}</span>
                                                <span className="text-gray-500 text-sm">{getFileCategory(file.type, file.name)}</span>
                                            </div>
                                        </div>
                                    )}

                                    <div className="mt-4 flex items-center gap-3">
                                        <span className="px-3 py-1 rounded-full bg-indigo-50 text-indigo-700 text-xs font-bold uppercase tracking-wide">
                                            {getFileCategory(file.type, file.name)}
                                        </span>
                                        <span className="text-sm text-gray-500 font-medium">
                                            {(file.size / 1024 / 1024).toFixed(2)} MB
                                        </span>
                                    </div>
                                </div>

                                {/* Language + Generate Button */}
                                <div className="flex flex-col sm:flex-row items-center justify-center gap-4 pt-4">
                                    <div className="flex items-center gap-2 bg-gray-50 border border-gray-200 rounded-2xl px-4 py-3 shadow-sm">
                                        <Languages size={18} className="text-gray-500" />
                                        <select
                                            value={selectedLanguage}
                                            onChange={(e) => setSelectedLanguage(e.target.value)}
                                            className="bg-transparent text-sm font-bold text-gray-900 outline-none cursor-pointer w-32"
                                        >
                                            {INSIGHT_LANGUAGES.map(lang => (
                                                <option key={lang.value} value={lang.value}>
                                                    {lang.flag} {lang.label}
                                                </option>
                                            ))}
                                        </select>
                                    </div>

                                    <button
                                        onClick={generateInsights}
                                        disabled={loading}
                                        className={`
                                            flex items-center gap-3 px-8 py-3.5 rounded-2xl text-white font-bold text-base shadow-lg transition-all active:scale-95
                                            ${loading
                                                ? 'bg-gray-400 cursor-not-allowed shadow-none'
                                                : 'bg-indigo-600 hover:bg-indigo-700 hover:shadow-indigo-500/25 shadow-indigo-600/20'
                                            }
                                        `}
                                    >
                                        {loading ? (
                                            <>
                                                <Loader className="animate-spin w-5 h-5" />
                                                Analyzing...
                                            </>
                                        ) : (
                                            <>
                                                <BrainCircuit className="w-5 h-5" />
                                                Give Analysis
                                            </>
                                        )}
                                    </button>
                                </div>
                            </div>
                        )}

                        {error && (
                            <div className="mt-6 p-4 bg-red-50 text-red-600 rounded-xl text-center border border-red-100 font-medium">
                                {error}
                            </div>
                        )}
                    </section>
                )}

                {viewMode === 'saved' && userEmail && (
                    <section className="bg-white rounded-3xl border border-gray-200 shadow-sm p-8">
                        <div className="flex items-center justify-between mb-6">
                            <div className="flex items-center gap-2">
                                <BookmarkCheck size={20} className="text-indigo-600" />
                                <h2 className="text-xl font-bold text-gray-900">Saved Dashboards</h2>
                            </div>
                            
                            <div className="flex items-center gap-4">
                                {/* Language selector on saved page too */}
                                <div className="flex items-center gap-2 bg-gray-50 border border-gray-200 rounded-xl px-3 py-2">
                                    <Languages size={14} className="text-gray-500" />
                                    <select
                                        value={selectedLanguage}
                                        onChange={(e) => setSelectedLanguage(e.target.value)}
                                        className="bg-transparent text-xs font-bold text-gray-900 outline-none cursor-pointer"
                                    >
                                        {INSIGHT_LANGUAGES.map(lang => (
                                            <option key={lang.value} value={lang.value}>
                                                {lang.label}
                                            </option>
                                        ))}
                                    </select>
                                </div>

                                {savedViz.length > 0 && (
                                    <span className="text-xs font-bold text-gray-500 bg-gray-100 px-3 py-1.5 rounded-full">
                                        {savedViz.length} dashboards
                                    </span>
                                )}
                            </div>
                        </div>

                        {loadingSaved ? (
                            <div className="flex items-center justify-center py-16">
                                <Loader className="animate-spin w-6 h-6 text-indigo-600 mr-3" />
                                <span className="text-gray-500 font-medium">Loading saved dashboards...</span>
                            </div>
                        ) : savedViz.length === 0 ? (
                            <div className="text-center py-16">
                                <div className="p-5 bg-gray-50 rounded-2xl inline-block mb-5 border border-gray-100">
                                    <Image className="w-10 h-10 text-gray-400" />
                                </div>
                                <h3 className="text-lg font-bold text-gray-900 mb-2">No Saved Dashboards Yet</h3>
                                <p className="text-gray-500 text-sm max-w-md mx-auto leading-relaxed">
                                    When you create dashboards, use the <strong className="text-gray-700">"Save Visualization"</strong> button to save snapshots here.
                                </p>
                                <button
                                    onClick={() => navigate('/data-cleaning')}
                                    className="mt-6 px-6 py-2.5 bg-indigo-50 text-indigo-700 rounded-xl text-sm font-bold hover:bg-indigo-100 transition-colors inline-flex items-center gap-2"
                                >
                                    Create a Dashboard
                                    <ChevronRight size={16} />
                                </button>
                            </div>
                        ) : (
                            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
                                {savedViz.map((viz, index) => (
                                    <div
                                        key={index}
                                        className="bg-white rounded-2xl border border-gray-200 overflow-hidden group hover:border-indigo-300 hover:shadow-lg transition-all duration-300 flex flex-col"
                                    >
                                        {/* Thumbnail */}
                                        <div className="aspect-video bg-gray-100 overflow-hidden border-b border-gray-100">
                                            <img
                                                src={viz.thumbnail}
                                                alt={viz.title}
                                                className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
                                            />
                                        </div>

                                        {/* Info */}
                                        <div className="p-5 flex flex-col flex-1">
                                            <h4 className="font-bold text-gray-900 truncate mb-1">
                                                {viz.title}
                                            </h4>
                                            <div className="flex items-center gap-1.5 text-xs text-gray-500 mb-5">
                                                <Clock size={12} />
                                                {viz.saved_at ? new Date(viz.saved_at).toLocaleDateString(undefined, {
                                                    month: 'short',
                                                    day: 'numeric',
                                                    hour: '2-digit',
                                                    minute: '2-digit',
                                                }) : 'Unknown date'}
                                            </div>

                                            <div className="mt-auto">
                                                <button
                                                    onClick={() => generateFromSaved(viz)}
                                                    disabled={savedInsightsLoading === viz.filename}
                                                    className={`w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl text-sm font-bold transition-all ${savedInsightsLoading === viz.filename
                                                            ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                                                            : 'bg-indigo-50 text-indigo-700 hover:bg-indigo-600 hover:text-white group-hover:bg-indigo-600 group-hover:text-white'
                                                        }`}
                                                >
                                                    {savedInsightsLoading === viz.filename ? (
                                                        <>
                                                            <Loader className="animate-spin w-4 h-4" />
                                                            Analyzing...
                                                        </>
                                                    ) : (
                                                        <>
                                                            <BrainCircuit size={16} />
                                                            Get Insights
                                                        </>
                                                    )}
                                                </button>
                                            </div>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                        {error && viewMode === 'saved' && (
                            <div className="mt-6 p-4 bg-red-50 text-red-600 rounded-xl text-center border border-red-100 font-medium">
                                {error}
                            </div>
                        )}
                    </section>
                )}

                {/* ──── Section 3: Enhanced Results ──── */}
                {insights && (
                    <section id="insights-results" className="pb-8 pt-4">
                        <div className="flex items-center gap-3 mb-6 bg-white p-4 rounded-2xl border border-gray-200 shadow-sm">
                            <div className="w-10 h-10 rounded-xl bg-indigo-600 flex items-center justify-center shadow-lg shadow-indigo-600/20">
                                <span className="text-white font-black text-lg">V</span>
                            </div>
                            <div>
                                <h2 className="text-lg font-bold text-gray-900">Vidhur's Analysis</h2>
                                <p className="text-xs text-gray-500 font-medium">Deep business insights powered by AI</p>
                            </div>
                            {/* Inline language selector for re-generation */}
                            <div className="ml-auto flex items-center gap-2">
                                <div className="flex items-center gap-2 bg-gray-50 border border-gray-200 rounded-xl px-3 py-2">
                                    <Languages size={14} className="text-gray-500" />
                                    <select
                                        value={selectedLanguage}
                                        onChange={(e) => setSelectedLanguage(e.target.value)}
                                        className="bg-transparent text-xs font-bold text-gray-900 outline-none cursor-pointer"
                                    >
                                        {INSIGHT_LANGUAGES.map(lang => (
                                            <option key={lang.value} value={lang.value}>
                                                {lang.flag} {lang.label}
                                            </option>
                                        ))}
                                    </select>
                                </div>
                                <button
                                    onClick={() => {
                                        if (file) generateInsights();
                                        else if (preview) {
                                            setInsights(null);
                                            setViewMode('saved');
                                        }
                                    }}
                                    disabled={loading}
                                    className="flex items-center gap-2 px-4 py-2 rounded-xl bg-indigo-600 text-white text-xs font-bold hover:bg-indigo-700 transition-all active:scale-95 disabled:opacity-50"
                                    title="Re-generate insights in the selected language"
                                >
                                    <RefreshCw size={14} />
                                    Re-generate
                                </button>
                            </div>
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                            {insights.map((insight, index) => (
                                <div
                                    key={index}
                                    className="bg-white p-6 rounded-2xl border border-gray-200 shadow-sm hover:shadow-md hover:border-indigo-200 transition-all duration-300 relative overflow-hidden"
                                >
                                    {/* Title */}
                                    <div className="flex items-start gap-3 mb-4">
                                        <div className="p-2 bg-indigo-50 rounded-xl text-indigo-600 shrink-0 mt-0.5">
                                            {getInsightIcon(index)}
                                        </div>
                                        <h3 className="text-lg font-bold text-gray-900 leading-tight">
                                            {insight.title}
                                        </h3>
                                    </div>

                                    {/* Description */}
                                    <p className="text-gray-600 leading-relaxed text-sm font-medium pl-11 mb-5">
                                        {insight.description}
                                    </p>

                                    {/* Why It Matters */}
                                    {insight.why_it_matters && (
                                        <div className="ml-11 mb-4 p-4 bg-orange-50 rounded-xl border border-orange-100">
                                            <p className="text-xs font-black text-orange-600 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                                                <Lightbulb size={14} />
                                                Why This Matters
                                            </p>
                                            <p className="text-gray-700 text-sm leading-relaxed font-medium">
                                                {insight.why_it_matters}
                                            </p>
                                        </div>
                                    )}

                                    {/* Action Steps */}
                                    {insight.action_steps && (
                                        <div className="ml-11 p-4 bg-emerald-50 rounded-xl border border-emerald-100">
                                            <p className="text-xs font-black text-emerald-600 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                                                <Target size={14} />
                                                What To Do Next
                                            </p>
                                            <p className="text-gray-700 text-sm leading-relaxed font-medium">
                                                {insight.action_steps}
                                            </p>
                                        </div>
                                    )}
                                </div>
                            ))}
                        </div>
                    </section>
                )}
            </main>
        </div>
    );
};

export default InsightGeneration;

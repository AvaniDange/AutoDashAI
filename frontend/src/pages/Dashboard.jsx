import React, { useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import ChartGrid from '../components/ChartGrid';
import ChatInterface from '../components/ChatInterface';
import { LayoutDashboard, ArrowLeft, Download, BrainCircuit, X, Filter, Moon, Sun, ChevronRight, Layers, Languages } from 'lucide-react';
import html2canvas from 'html2canvas';
import jsPDF from 'jspdf';

const Dashboard = () => {
    const location = useLocation();
    const navigate = useNavigate();
    const { session_id, charts: initialCharts, kpis: initialKpis, slicers: initialSlicers, pages: initialPages } = location.state || {};

    const [charts, setCharts] = useState(initialCharts || []);
    const [kpis, setKpis] = useState(initialKpis || []);
    const [slicers, setSlicers] = useState(initialSlicers || []);
    const [pages, setPages] = useState(initialPages || []);
    const [activePageIdx, setActivePageIdx] = useState(0);
    const [theme, setTheme] = useState('light');
    const [sidebarOpen, setSidebarOpen] = useState(true);

    const [messages, setMessages] = useState([]);
    const [loading, setLoading] = useState(false);
    const [insights, setInsights] = useState(null);
    const [showInsights, setShowInsights] = useState(false);
    const [loadingInsights, setLoadingInsights] = useState(false);
    const [insightLanguage, setInsightLanguage] = useState('English');

    const API_BASE_URL = window.location.origin.includes('localhost')
        ? `http://localhost:8000`
        : `http://127.0.0.1:8000`;

    const handleSendMessage = async (text) => {
        const userMsg = { role: 'user', content: text };
        setMessages(prev => [...prev, userMsg]);
        setLoading(true);

        try {
            const response = await fetch(`${API_BASE_URL}/api/dashboard/chat`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ session_id, message: text })
            });

            const data = await response.json();

            if (data.success) {
                if (data.charts) setCharts(data.charts);
                if (data.kpis) setKpis(data.kpis);
                if (data.slicers) setSlicers(data.slicers);
                if (data.pages) setPages(data.pages);
                if (data.theme) setTheme(data.theme);
                if (data.active_page_idx !== undefined) setActivePageIdx(data.active_page_idx);

                const botMsg = { role: 'assistant', content: data.reply };
                setMessages(prev => [...prev, botMsg]);
            } else {
                setMessages(prev => [...prev, { role: 'assistant', content: "Sorry, I couldn't process that." }]);
            }
        } catch (error) {
            console.error("Chat error:", error);
            setMessages(prev => [...prev, {
                role: 'assistant',
                content: `Network error: I cannot reach the backend server at ${API_BASE_URL}. Please ensure the backend is running.`
            }]);
        } finally {
            setLoading(false);
        }
    };

    const handleSlicerChange = async (column, value) => {
        // This will be implemented in the next backend update for filter logic
        console.log(`Filter ${column} by ${value}`);
        // For now, let's just trigger a chat message to the agent to filter
        handleSendMessage(`Filter data where ${column} is ${value}`);
    };

    const handleDownloadPDF = async () => {
        const dashboardElement = document.getElementById('dashboard-content');
        if (!dashboardElement) return;

        try {
            const canvas = await html2canvas(dashboardElement, {
                scale: 2, // Improve quality
                useCORS: true,
                logging: false,
                backgroundColor: '#f9fafb' // match bg-gray-50
            });

            const imgData = canvas.toDataURL('image/png');
            const pdf = new jsPDF({
                orientation: 'landscape',
                unit: 'px',
                format: [canvas.width, canvas.height]
            });

            pdf.addImage(imgData, 'PNG', 0, 0, canvas.width, canvas.height);
            pdf.save(`dashboard-report-${session_id.slice(0, 8)}.pdf`);
        } catch (error) {
            console.error("PDF generation failed", error);
        }
    };

    const handleGetInsights = async () => {
        setLoadingInsights(true);
        try {
            const response = await fetch(`${API_BASE_URL}/api/dashboard/insights/${session_id}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ language: insightLanguage })
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ detail: "Server error" }));
                throw new Error(errorData.detail || "Failed to generate insights");
            }

            const data = await response.json();
            if (data.success) {
                setInsights(data.insights);
                setShowInsights(true);
            } else {
                alert(data.message || "Failed to get insights. Try again.");
            }
        } catch (error) {
            console.error("Insights error:", error);
            alert(`Insight Error: ${error.message}`);
        } finally {
            setLoadingInsights(false);
        }
    };

    if (!session_id) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-gray-50">
                <div className="text-center">
                    <h2 className="text-2xl font-bold text-gray-800">No Active Session</h2>
                    <p className="text-gray-600 mb-4">Please upload a file to start.</p>
                    <button
                        onClick={() => navigate('/data-cleaning')}
                        className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700"
                    >
                        Go to Upload
                    </button>
                </div>
            </div>
        );
    }

    return (
        <div className={`h-screen flex flex-col ${theme === 'dark' ? 'bg-slate-950 text-white' : 'bg-gray-50'} overflow-hidden transition-colors duration-500`}>
            {/* Top Navbar */}
            <header className={`${theme === 'dark' ? 'bg-slate-900 border-slate-800' : 'bg-white border-gray-200'} border-b flex items-center justify-between px-6 py-3 shrink-0 z-30 transition-colors`}>
                <div className="flex items-center gap-4">
                    <button onClick={() => navigate('/data-cleaning')} className={`p-2 rounded-lg ${theme === 'dark' ? 'hover:bg-slate-800 text-slate-400' : 'hover:bg-gray-100 text-gray-600'}`}>
                        <ArrowLeft size={20} />
                    </button>
                    <div className="flex items-center gap-3">
                        <div className={`p-2 rounded-xl ${theme === 'dark' ? 'bg-indigo-500/20 text-indigo-400' : 'bg-blue-100 text-blue-600'}`}>
                            <LayoutDashboard size={22} />
                        </div>
                        <div>
                            <h1 className={`text-lg font-bold ${theme === 'dark' ? 'text-slate-100' : 'text-gray-800'}`}>Analytics Suite</h1>
                            <div className="flex items-center gap-2">
                                <span className="text-[10px] bg-indigo-500/10 text-indigo-500 px-1.5 py-0.5 rounded font-bold uppercase tracking-wider">Session</span>
                                <p className="text-[10px] text-gray-500 font-mono">{session_id.slice(0, 12)}</p>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Page Tabs */}
                {pages.length > 0 && (
                    <div className={`flex items-center p-1 rounded-xl ${theme === 'dark' ? 'bg-slate-800' : 'bg-gray-100'}`}>
                        {pages.map((page, idx) => (
                            <button
                                key={page.id}
                                onClick={() => setActivePageIdx(idx)}
                                className={`px-4 py-1.5 rounded-lg text-sm font-semibold transition-all ${activePageIdx === idx
                                    ? (theme === 'dark' ? 'bg-indigo-600 text-white shadow-lg' : 'bg-white text-blue-600 shadow-sm')
                                    : (theme === 'dark' ? 'text-slate-400 hover:text-slate-200' : 'text-gray-500 hover:text-gray-700')
                                    }`}
                            >
                                {page.name}
                            </button>
                        ))}
                        <button className={`p-1.5 rounded-lg ml-1 ${theme === 'dark' ? 'text-slate-500 hover:text-slate-300' : 'text-gray-400 hover:text-gray-600'}`}>
                            <Layers size={16} />
                        </button>
                    </div>
                )}

                <div className="flex items-center gap-3">
                    <button
                        onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
                        className={`p-2.5 rounded-xl transition-all ${theme === 'dark' ? 'bg-slate-800 text-yellow-400 border border-slate-700 hover:bg-slate-700' : 'bg-gray-100 text-gray-600 border border-transparent hover:bg-gray-200'}`}
                    >
                        {theme === 'dark' ? <Sun size={20} /> : <Moon size={20} />}
                    </button>
                    <select
                        value={insightLanguage}
                        onChange={(e) => setInsightLanguage(e.target.value)}
                        className={`px-3 py-2.5 rounded-xl text-sm font-bold border transition-all outline-none cursor-pointer ${theme === 'dark'
                            ? 'bg-slate-800 border-slate-700 text-slate-200'
                            : 'bg-gray-100 border-gray-200 text-gray-700'}`}
                    >
                        <option value="English">🌐 English</option>
                        <option value="Hindi">🇮🇳 हिंदी</option>
                        <option value="Marathi">🇮🇳 मराठी</option>
                        <option value="Gujarati">🇮🇳 ગુજરાતી</option>
                        <option value="Tamil">🇮🇳 தமிழ்</option>
                        <option value="Telugu">🇮🇳 తెలుగు</option>
                        <option value="Kannada">🇮🇳 ಕನ್ನಡ</option>
                        <option value="Bengali">🇮🇳 বাংলা</option>
                    </select>
                    <button
                        onClick={handleGetInsights}
                        disabled={loadingInsights}
                        className="flex items-center gap-2 px-5 py-2.5 bg-indigo-600 text-white rounded-xl hover:bg-indigo-700 transition-all shadow-lg active:scale-95 disabled:opacity-50 font-bold text-sm"
                    >
                        <BrainCircuit size={18} />
                        {loadingInsights ? 'Analyzing...' : 'AI Insights'}
                    </button>
                    <button
                        onClick={handleDownloadPDF}
                        className={`flex items-center gap-2 px-4 py-2.5 rounded-xl transition-all font-bold text-sm border ${theme === 'dark'
                            ? 'bg-slate-900 border-slate-700 text-slate-300 hover:bg-slate-800'
                            : 'bg-white border-gray-200 text-gray-700 hover:bg-gray-50'
                            }`}
                    >
                        <Download size={18} />
                        Export
                    </button>
                </div>
            </header>

            {/* Main Content Area */}
            <div className="flex-1 flex overflow-hidden">
                {/* Left Sidebar: Slicers (Power BI style) */}
                <aside className={`transition-all duration-300 border-r ${sidebarOpen ? 'w-64' : 'w-12'
                    } ${theme === 'dark' ? 'bg-slate-900 border-slate-800 shadow-xl' : 'bg-white border-gray-200 shadow-sm'
                    } shrink-0 flex flex-col relative`}>

                    <button
                        onClick={() => setSidebarOpen(!sidebarOpen)}
                        className={`absolute -right-3 top-6 p-1 rounded-full shadow-md z-40 transition-colors ${theme === 'dark' ? 'bg-slate-800 text-slate-400 border border-slate-700 hover:text-white' : 'bg-white text-gray-400 border border-gray-200 hover:text-blue-600'
                            }`}
                    >
                        <ChevronRight size={16} className={`transition-transform duration-300 ${sidebarOpen ? 'rotate-180' : ''}`} />
                    </button>

                    <div className="p-4 flex items-center justify-between">
                        {sidebarOpen && <h3 className={`text-sm font-black uppercase tracking-widest ${theme === 'dark' ? 'text-slate-500' : 'text-gray-400'}`}>Filters</h3>}
                        <Filter size={18} className={theme === 'dark' ? 'text-slate-500' : 'text-gray-400'} />
                    </div>

                    {sidebarOpen && (
                        <div className="overflow-y-auto flex-1 px-4 space-y-6">
                            {slicers.map((slicer, idx) => (
                                <div key={idx} className="space-y-3">
                                    <label className={`text-xs font-bold ${theme === 'dark' ? 'text-slate-300' : 'text-gray-600'}`}>
                                        {slicer.column}
                                    </label>
                                    <select
                                        onChange={(e) => handleSlicerChange(slicer.column, e.target.value)}
                                        className={`w-full p-2.5 text-sm rounded-xl border focus:ring-2 outline-none transition-all ${theme === 'dark'
                                            ? 'bg-slate-800 border-slate-700 text-slate-200 focus:ring-indigo-500/30'
                                            : 'bg-gray-50 border-gray-200 text-gray-700 focus:ring-blue-500/30'
                                            }`}
                                    >
                                        <option value="">All {slicer.column}s</option>
                                        {slicer.options.map(opt => (
                                            <option key={opt} value={opt}>{opt}</option>
                                        ))}
                                    </select>
                                </div>
                            ))}
                            {slicers.length === 0 && (
                                <p className="text-xs text-gray-500 mt-4 italic">No automatic filters available for this dataset.</p>
                            )}
                        </div>
                    )}
                </aside>

                {/* Center: Charts Grid */}
                <main className={`flex-1 overflow-y-auto transition-colors duration-500 ${theme === 'dark' ? 'bg-slate-950 scatter-bg-dark' : 'bg-gray-50'}`}>
                    <div id="dashboard-content" className="p-8 max-w-[1600px] mx-auto space-y-8">
                        {/* KPI Grid - Re-styled for Premium BI look */}
                        {kpis && kpis.length > 0 && (
                            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-5">
                                {kpis.map((kpi, idx) => (
                                    <div key={idx} className={`p-5 rounded-[2rem] transition-all shadow-md group border flex flex-col justify-between min-h-[140px] ${theme === 'dark'
                                        ? 'bg-slate-900 border-slate-800 hover:border-indigo-500/50 hover:shadow-indigo-500/5'
                                        : 'bg-white border-white hover:border-blue-500/10 hover:shadow-lg'
                                        }`}>
                                        <div className="flex justify-between items-start mb-2">
                                            <h4 className={`text-[10px] font-black uppercase tracking-[0.15em] ${theme === 'dark' ? 'text-slate-500' : 'text-gray-400'}`}>
                                                {kpi.title}
                                            </h4>
                                            <div className={`p-1.5 rounded-lg transition-colors ${theme === 'dark' ? 'bg-slate-800 text-slate-400' : 'bg-gray-50 text-gray-400'
                                                }`}>
                                                <Layers size={12} />
                                            </div>
                                        </div>
                                        <div className="flex flex-col gap-1">
                                            <span className={`text-2xl font-black tracking-tight leading-none ${theme === 'dark' ? 'text-white' : 'text-gray-900'}`}>
                                                {kpi.value}
                                            </span>
                                            <div className="flex items-center gap-1.5 mt-1">
                                                <span className={`text-[10px] font-black px-2 py-0.5 rounded-md ${kpi.change.includes('-')
                                                    ? (theme === 'dark' ? 'bg-red-500/10 text-red-400' : 'bg-red-50 text-red-600')
                                                    : kpi.change === 'Metric' || kpi.change === 'Dataset Size'
                                                        ? (theme === 'dark' ? 'bg-indigo-500/10 text-indigo-400' : 'bg-blue-50 text-blue-600')
                                                        : (theme === 'dark' ? 'bg-emerald-500/10 text-emerald-400' : 'bg-emerald-50 text-emerald-600')
                                                    }`}>
                                                    {kpi.change}
                                                </span>
                                                {kpi.context && <span className={`text-[9px] font-bold ${theme === 'dark' ? 'text-slate-600' : 'text-gray-400'}`}>
                                                    {kpi.context}
                                                </span>}
                                            </div>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}

                        <ChartGrid charts={charts} theme={theme} />
                    </div>
                </main>

                {/* Right: AI Assistant Panel */}
                <div className={`w-[400px] border-l ${theme === 'dark' ? 'bg-slate-900 border-slate-800 shadow-2xl' : 'bg-white border-gray-200 shadow-2xl'
                    } z-20 flex flex-col transition-colors`}>
                    <ChatInterface
                        messages={messages}
                        onSendMessage={handleSendMessage}
                        loading={loading}
                        theme={theme}
                    />
                </div>
            </div>

            {/* Insights Modal */}
            {showInsights && (
                <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center z-50 p-4 animate-in fade-in duration-300">
                    <div className={`rounded-[2.5rem] shadow-2xl max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col border transition-colors duration-500 ${theme === 'dark' ? 'bg-slate-900 border-slate-800' : 'bg-white border-gray-100'
                        }`}>
                        <div className={`flex items-center justify-between p-8 border-b ${theme === 'dark' ? 'border-slate-800' : 'border-gray-100'
                            }`}>
                            <div className="flex items-center gap-4">
                                <div className={`p-3 rounded-2xl ${theme === 'dark' ? 'bg-indigo-500/20 text-indigo-400' : 'bg-purple-100 text-purple-600'
                                    }`}>
                                    <BrainCircuit className="w-8 h-8" />
                                </div>
                                <div>
                                    <h2 className={`text-2xl font-black ${theme === 'dark' ? 'text-slate-100' : 'text-gray-900'
                                        }`}>Data Intelligence</h2>
                                    <p className={`text-sm font-bold ${theme === 'dark' ? 'text-slate-500' : 'text-gray-400'
                                        }`}>AI-powered analysis of your dashboard</p>
                                </div>
                            </div>
                            <button onClick={() => setShowInsights(false)} className={`p-2 rounded-xl transition-colors ${theme === 'dark' ? 'hover:bg-slate-800 text-slate-500' : 'hover:bg-gray-100 text-gray-400'
                                }`}>
                                <X size={28} />
                            </button>
                        </div>
                        <div className="p-8 overflow-y-auto">
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                {insights && insights.map((insight, index) => (
                                    <div key={index} className={`p-6 rounded-[2rem] border transition-all hover:scale-[1.02] ${theme === 'dark'
                                        ? 'bg-slate-800/50 border-slate-700 hover:border-indigo-500/50'
                                        : 'bg-gradient-to-br from-indigo-50/50 to-purple-50/50 border-indigo-100 hover:border-indigo-200'
                                        }`}>
                                        <h3 className={`text-base font-black mb-3 ${theme === 'dark' ? 'text-indigo-400' : 'text-indigo-900'
                                            }`}>{insight.title}</h3>
                                        <p className={`text-sm leading-relaxed font-medium ${theme === 'dark' ? 'text-slate-300' : 'text-indigo-700'
                                            }`}>{insight.description}</p>
                                    </div>
                                ))}
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default Dashboard;

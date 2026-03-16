import React, { useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import ChartGrid from '../components/ChartGrid';
import ChatInterface from '../components/ChatInterface';
import { LayoutDashboard, ArrowLeft, Download, BrainCircuit, X, Filter, Moon, Sun, ChevronRight, Layers } from 'lucide-react';
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
    const [theme, setTheme] = useState('dark'); // Force dark theme for Power BI look
    const [sidebarOpen, setSidebarOpen] = useState(true);

    const [messages, setMessages] = useState([]);
    const [loading, setLoading] = useState(false);
    const [insights, setInsights] = useState(null);
    const [showInsights, setShowInsights] = useState(false);
    const [loadingInsights, setLoadingInsights] = useState(false);

    const isDark = theme === 'dark';
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
                // Removed theme update to prevent changing dark theme
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
        handleSendMessage(`Filter data where ${column} is ${value}`);
    };

    const handleDownloadPDF = async () => {
        const dashboardElement = document.getElementById('dashboard-content');
        if (!dashboardElement) return;

        try {
            const canvas = await html2canvas(dashboardElement, {
                scale: 2,
                useCORS: true,
                logging: false,
                backgroundColor: isDark ? '#020617' : '#F3F2F1'
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
                method: 'POST'
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
            <div className="min-h-screen flex items-center justify-center bg-[#F3F2F1]">
                <div className="text-center p-12 bg-white rounded-none shadow-sm border border-[#EDEBE9]">
                    <h2 className="text-xl font-bold text-[#323130]">No Active Session</h2>
                    <p className="text-[#605E5C] mb-6">Please upload a file to start.</p>
                    <button
                        onClick={() => navigate('/data-cleaning')}
                        className="bg-[#118DFF] text-white px-8 py-2.5 font-semibold hover:bg-[#12239E] transition-all"
                    >
                        Go to Upload
                    </button>
                </div>
            </div>
        );
    }

    return (
        <div className={`h-screen flex flex-col ${isDark ? 'bg-slate-950 text-white' : 'bg-[#F3F2F1] text-[#323130]'} overflow-hidden`}>
            {/* Top Navbar: Microsoft Style */}
            <header className={`${isDark ? 'bg-slate-900 border-slate-800' : 'bg-white border-[#EDEBE9]'} border-b flex items-center justify-between px-6 py-2.5 shrink-0 z-30`}>
                <div className="flex items-center gap-6">
                    <button onClick={() => navigate('/data-cleaning')} className={`p-2 transition-colors ${isDark ? 'hover:bg-slate-800 text-slate-400' : 'hover:bg-[#F3F2F1] text-[#605E5C]'}`}>
                        <ArrowLeft size={18} />
                    </button>
                    <div className="flex items-center gap-4">
                        <div className={`p-2 rounded-sm ${isDark ? 'bg-indigo-500/20 text-indigo-400' : 'bg-[#118DFF]/10 text-[#118DFF]'}`}>
                            <LayoutDashboard size={20} />
                        </div>
                        <div>
                            <h1 className={`text-sm font-bold tracking-tight ${isDark ? 'text-slate-100' : 'text-[#323130]'}`}>Classic Models | <span className="text-[#00B7C3]">Sales Dashboard</span></h1>
                            <p className="text-[10px] text-[#A19F9D] font-medium leading-none mt-1">Status: Live · Session {session_id.slice(0, 8)}</p>
                        </div>
                    </div>
                </div>

                {/* Page Tabs: Power BI Tab Style */}
                {pages.length > 0 && (
                    <div className="flex items-center h-full">
                        {pages.map((page, idx) => (
                            <button
                                key={page.id}
                                onClick={() => setActivePageIdx(idx)}
                                className={`h-full px-6 flex items-center text-xs font-semibold transition-all border-b-2 ${activePageIdx === idx
                                    ? (isDark ? 'border-indigo-500 text-white' : 'border-[#118DFF] text-[#118DFF] bg-[#118DFF]/5')
                                    : 'border-transparent text-[#605E5C] hover:bg-[#F3F2F1]'
                                    }`}
                            >
                                {page.name}
                            </button>
                        ))}
                    </div>
                )}

                <div className="flex-1"></div>

                <div className="flex items-center gap-3">
                    <button
                        onClick={() => setShowInsights(true)}
                        className={`flex items-center gap-2 px-3 py-1.5 text-xs font-bold transition-all border-2 ${isDark
                            ? 'bg-[#00B7C3]/10 border-[#00B7C3] text-[#00B7C3] hover:bg-[#00B7C3]/20'
                            : 'bg-[#118DFF]/10 border-[#118DFF] text-[#118DFF] hover:bg-[#118DFF]/20'
                            }`}
                    >
                        <BrainCircuit size={16} />
                        AI Insights
                    </button>
                    <button
                        onClick={handleDownloadPDF}
                        className={`flex items-center gap-2 px-3 py-1.5 text-xs font-bold transition-all border-2 ${isDark
                            ? 'bg-slate-800 border-slate-700 text-slate-400 hover:text-slate-200'
                            : 'bg-white border-[#EDEBE9] text-[#605E5C] hover:bg-[#F3F2F1]'
                            }`}
                    >
                        <Download size={16} />
                        Export PDF
                    </button>
                </div>
            </header>

            {/* Main Content Area */}
            <div className="flex-1 flex overflow-hidden">
                {/* Left Sidebar: Power BI Style Filters */}
                <aside className={`transition-all duration-300 border-r ${sidebarOpen ? 'w-64' : 'w-0'
                    } ${isDark ? 'bg-slate-900 border-slate-800' : 'bg-white border-[#EDEBE9]'} shrink-0 flex flex-col relative overflow-visible`}>

                    <button
                        onClick={() => setSidebarOpen(!sidebarOpen)}
                        className={`absolute -right-3 top-10 p-1 rounded-full shadow-sm z-40 transition-all border ${isDark ? 'bg-slate-800 text-slate-400 border-slate-700 hover:text-white' : 'bg-white text-[#605E5C] border-[#EDEBE9] hover:bg-[#F3F2F1]'
                            }`}
                    >
                        <ChevronRight size={14} className={`transition-transform duration-300 ${sidebarOpen ? 'rotate-180' : ''}`} />
                    </button>

                    <div className="p-4 border-b border-transparent flex items-center justify-between overflow-hidden">
                        <h3 className={`text-xs font-bold uppercase tracking-wider ${isDark ? 'text-slate-400' : 'text-[#605E5C]'}`}>Filters</h3>
                        <Filter size={16} className={isDark ? 'text-slate-500' : 'text-[#A19F9D]'} />
                    </div>

                    <div className="overflow-y-auto flex-1 p-4 space-y-6 overflow-x-hidden">
                        {/* Date Range Filter */}
                        <div className="space-y-2">
                            <label className={`text-[11px] font-semibold ${isDark ? 'text-slate-300' : 'text-[#323130]'}`}>
                                Date Range
                            </label>
                            <input
                                type="date"
                                defaultValue="2003-01-06"
                                className={`w-full p-2 text-xs border outline-none transition-all rounded-sm ${isDark
                                    ? 'bg-slate-800 border-slate-700 text-slate-200 focus:border-[#00B7C3]'
                                    : 'bg-white border-[#EDEBE9] text-[#323130] focus:border-[#00B7C3]'
                                    }`}
                            />
                            <input
                                type="date"
                                defaultValue="2004-12-23"
                                className={`w-full p-2 text-xs border outline-none transition-all rounded-sm ${isDark
                                    ? 'bg-slate-800 border-slate-700 text-slate-200 focus:border-[#00B7C3]'
                                    : 'bg-white border-[#EDEBE9] text-[#323130] focus:border-[#00B7C3]'
                                    }`}
                            />
                        </div>

                        {/* Other Slicers */}
                        {slicers.map((slicer, idx) => (
                            <div key={idx} className="space-y-2">
                                <label className={`text-[11px] font-semibold ${isDark ? 'text-slate-300' : 'text-[#323130]'}`}>
                                    {slicer.column}
                                </label>
                                <select
                                    onChange={(e) => handleSlicerChange(slicer.column, e.target.value)}
                                    className={`w-full p-2 text-xs border outline-none transition-all rounded-sm ${isDark
                                        ? 'bg-slate-800 border-slate-700 text-slate-200 focus:border-indigo-500'
                                        : 'bg-white border-[#EDEBE9] text-[#323130] focus:border-[#118DFF]'
                                        }`}
                                >
                                    <option value="">All {slicer.column}s</option>
                                    {slicer.options.map(opt => (
                                        <option key={opt} value={opt}>{opt}</option>
                                    ))}
                                </select>
                            </div>
                        ))}
                    </div>
                </aside>

                {/* Center: Dashboard with KPIs + Charts */}
                <main className={`flex-1 overflow-y-auto ${isDark ? 'bg-[#1F1F1F]' : 'bg-[#F3F2F1]'}`}>
                    <div id="dashboard-content" className="p-6 space-y-6">
                        {/* KPI Row */}
                        {kpis && kpis.length > 0 && (
                            <div className="grid grid-cols-3 gap-4">
                                {kpis.map((kpi, idx) => (
                                    <div key={idx} className={`p-5 rounded-sm border transition-all ${isDark
                                        ? 'bg-slate-900 border-slate-800'
                                        : 'bg-white border-[#EDEBE9]'
                                        }`}>
                                        <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">
                                            {kpi.title}
                                        </h4>
                                        <span className="text-3xl font-bold text-white block mb-2">
                                            {kpi.value}
                                        </span>
                                        {/* Mini sparkline */}
                                        <div className="h-10 w-full mb-2">
                                            {kpi.sparkline && kpi.sparkline.length > 0 && (
                                                <svg className="w-full h-full" viewBox="0 0 100 40" preserveAspectRatio="none">
                                                    <polyline
                                                        fill="none"
                                                        stroke="#00B7C3"
                                                        strokeWidth="2"
                                                        points={kpi.sparkline.map((d, i) =>
                                                            `${(i / (kpi.sparkline.length - 1)) * 100},${40 - (d.value / Math.max(...kpi.sparkline.map(v => v.value)) * 35)}`
                                                        ).join(' ')}
                                                    />
                                                </svg>
                                            )}
                                        </div>
                                        <span className="text-xs text-emerald-400 font-semibold">{kpi.change}</span>
                                    </div>
                                ))}
                            </div>
                        )}

                        {/* Charts - Let ChartGrid handle the grid layout */}
                        <ChartGrid charts={charts} theme={theme} />
                    </div>
                </main>

                {/* Right: AI Chat Interface (Restored) */}
                <div className={`w-[380px] border-l ${isDark ? 'bg-slate-900 border-slate-800 shadow-2xl' : 'bg-white border-[#EDEBE9] shadow-xl'
                    } z-20 flex flex-col`}>
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
                    <div className={`rounded-none shadow-2xl max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col border transition-colors duration-500 ${isDark ? 'bg-slate-900 border-slate-800' : 'bg-white border-[#EDEBE9]'}`}>
                        <div className={`flex items-center justify-between p-8 border-b ${isDark ? 'border-slate-800' : 'border-[#EDEBE9]'}`}>
                            <div className="flex items-center gap-4">
                                <div className={`p-3 rounded-sm ${isDark ? 'bg-indigo-500/20 text-indigo-400' : 'bg-[#118DFF]/10 text-[#118DFF]'}`}>
                                    <BrainCircuit className="w-8 h-8" />
                                </div>
                                <div>
                                    <h2 className={`text-xl font-bold ${isDark ? 'text-slate-100' : 'text-[#323130]'}`}>Data Intelligence</h2>
                                    <p className={`text-xs font-medium ${isDark ? 'text-slate-500' : 'text-[#605E5C]'}`}>Automated analysis for {session_id.slice(0, 8)}</p>
                                </div>
                            </div>
                            <button onClick={() => setShowInsights(false)} className={`p-2 transition-colors ${isDark ? 'hover:bg-slate-800 text-slate-500' : 'hover:bg-[#F3F2F1] text-[#605E5C]'}`}>
                                <X size={24} />
                            </button>
                        </div>
                        <div className="p-8 overflow-y-auto">
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                {insights && insights.map((insight, index) => (
                                    <div key={index} className={`p-6 rounded-none border transition-all ${isDark
                                        ? 'bg-slate-800/50 border-slate-700 hover:border-indigo-500/50'
                                        : 'bg-white border-[#EDEBE9] hover:border-[#118DFF]'
                                        }`}>
                                        <h3 className={`text-sm font-bold mb-3 ${isDark ? 'text-indigo-400' : 'text-[#118DFF]'}`}>{insight.title}</h3>
                                        <p className={`text-xs leading-relaxed font-medium ${isDark ? 'text-slate-300' : 'text-[#605E5C]'}`}>{insight.description}</p>
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

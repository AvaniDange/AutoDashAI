import React, { useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import ChartGrid from '../components/ChartGrid';
import ChatInterface from '../components/ChatInterface';
import { LayoutDashboard, ArrowLeft, Download, BrainCircuit, X } from 'lucide-react';
import html2canvas from 'html2canvas';
import jsPDF from 'jspdf';

const Dashboard = () => {
    const location = useLocation();
    const navigate = useNavigate();
    const { session_id, charts: initialCharts, kpis: initialKpis } = location.state || {}; // Expect state from navigation

    const [charts, setCharts] = useState(initialCharts || []);
    const [kpis] = useState(initialKpis || []);
    const [messages, setMessages] = useState([]);
    const [loading, setLoading] = useState(false);
    const [insights, setInsights] = useState(null);
    const [showInsights, setShowInsights] = useState(false);
    const [loadingInsights, setLoadingInsights] = useState(false);

    const API_BASE_URL = "http://127.0.0.1:8000";

    const handleSendMessage = async (text) => {
        // Optimistic UI update
        const userMsg = { role: 'user', content: text };
        setMessages(prev => [...prev, userMsg]);
        setLoading(true);

        try {
            const response = await fetch(`${API_BASE_URL}/api/dashboard/chat`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    session_id: session_id,
                    message: text
                })
            });

            const data = await response.json();

            if (data.success) {
                setCharts(data.charts);
                const botMsg = { role: 'assistant', content: data.reply };
                setMessages(prev => [...prev, botMsg]);
            } else {
                const errMsg = { role: 'assistant', content: "Sorry, I couldn't process that." };
                setMessages(prev => [...prev, errMsg]);
            }
        } catch (error) {
            console.error("Chat error:", error);
            const errMsg = { role: 'assistant', content: "Network error. Please try again." };
            setMessages(prev => [...prev, errMsg]);
        } finally {
            setLoading(false);
        }
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
        <div className="h-screen flex flex-col bg-gray-50 overflow-hidden">
            {/* Navbar */}
            <header className="bg-white shadow-sm flex items-center justify-between px-6 py-4 shrink-0 z-10">
                <div className="flex items-center gap-4">
                    <button onClick={() => navigate('/data-cleaning')} className="p-2 hover:bg-gray-100 rounded-lg text-gray-600">
                        <ArrowLeft size={20} />
                    </button>
                    <div className="flex items-center gap-2">
                        <div className="p-2 bg-blue-100 rounded-lg text-blue-600">
                            <LayoutDashboard size={24} />
                        </div>
                        <div>
                            <h1 className="text-xl font-bold text-gray-800">Analytics Dashboard</h1>
                            <p className="text-xs text-gray-500">Session ID: {session_id.slice(0, 8)}...</p>
                        </div>
                    </div>
                </div>
                <div className="flex items-center gap-4 hidden md:flex">
                    <button
                        onClick={handleGetInsights}
                        disabled={loadingInsights}
                        className="flex items-center gap-2 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors shadow-sm font-medium disabled:opacity-50"
                    >
                        <BrainCircuit size={18} />
                        {loadingInsights ? 'Analyzing...' : 'Get Insights'}
                    </button>
                    <button
                        onClick={handleDownloadPDF}
                        className="flex items-center gap-2 px-4 py-2 bg-white border border-gray-200 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors shadow-sm font-medium"
                    >
                        <Download size={18} />
                        Download Report
                    </button>
                    <div className="w-px h-8 bg-gray-200 mx-2"></div>
                </div>
            </header>

            {/* Main Layout */}
            <div className="flex-1 flex overflow-hidden">
                {/* Left Pane: Charts - Given more space (3/4) and better padding */}
                <div className="flex-[3] overflow-y-auto p-8 bg-gray-50/50">
                    <div id="dashboard-content" className="max-w-[1600px] mx-auto space-y-8">

                        {/* KPI Summary Cards */}
                        {kpis && kpis.length > 0 && (
                            <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
                                {kpis.map((kpi, idx) => (
                                    <div key={idx} className="bg-white p-6 rounded-2xl shadow-sm border border-gray-100 hover:shadow-md transition-shadow">
                                        <h4 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-2">{kpi.title}</h4>
                                        <div className="flex items-end justify-between">
                                            <span className="text-3xl font-bold text-gray-800">{kpi.value}</span>
                                            <span className={`text-sm font-medium px-2 py-1 rounded-full ${kpi.change.includes('-')
                                                ? 'bg-red-50 text-red-600'
                                                : 'bg-green-50 text-green-600'
                                                }`}>
                                                {kpi.change}
                                            </span>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}

                        <ChartGrid charts={charts} />
                    </div>
                </div>

                {/* Right Pane: Chat - Fixed width, better separation */}
                <div className="w-[400px] border-l border-gray-200 bg-white shadow-2xl z-20 flex flex-col">
                    <ChatInterface
                        messages={messages}
                        onSendMessage={handleSendMessage}
                        loading={loading}
                    />
                </div>
            </div>

            {/* Insights Modal */}
            {showInsights && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
                    <div className="bg-white rounded-2xl shadow-2xl max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col">
                        <div className="flex items-center justify-between p-6 border-b border-gray-200">
                            <div className="flex items-center gap-3">
                                <div className="p-2 bg-purple-100 rounded-lg">
                                    <BrainCircuit className="w-6 h-6 text-purple-600" />
                                </div>
                                <h2 className="text-2xl font-bold text-gray-800">Dashboard Insights</h2>
                            </div>
                            <button onClick={() => setShowInsights(false)} className="p-2 hover:bg-gray-100 rounded-lg">
                                <X size={24} className="text-gray-600" />
                            </button>
                        </div>
                        <div className="p-6 overflow-y-auto">
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                {insights && insights.map((insight, index) => (
                                    <div key={index} className="bg-gradient-to-br from-purple-50 to-indigo-50 p-6 rounded-xl border border-purple-100 hover:shadow-lg transition-shadow">
                                        <h3 className="text-lg font-bold text-gray-800 mb-2">{insight.title}</h3>
                                        <p className="text-gray-700 text-sm leading-relaxed">{insight.description}</p>
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

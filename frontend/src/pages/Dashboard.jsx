import React, { useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import ChartGrid from '../components/ChartGrid';
import ChatInterface from '../components/ChatInterface';
import { LayoutDashboard, ArrowLeft } from 'lucide-react';

const Dashboard = () => {
    const location = useLocation();
    const navigate = useNavigate();
    const { session_id, charts: initialCharts, kpis: initialKpis } = location.state || {}; // Expect state from navigation

    const [charts, setCharts] = useState(initialCharts || []);
    const [kpis, setKpis] = useState(initialKpis || []);
    const [messages, setMessages] = useState([]);
    const [loading, setLoading] = useState(false);

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
            </header>

            {/* Main Layout */}
            <div className="flex-1 flex overflow-hidden">
                {/* Left Pane: Charts - Given more space (3/4) and better padding */}
                <div className="flex-[3] overflow-y-auto p-8 bg-gray-50/50">
                    <div className="max-w-[1600px] mx-auto space-y-8">

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
        </div>
    );
};

export default Dashboard;

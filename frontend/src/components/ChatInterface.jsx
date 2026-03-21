import React, { useState, useEffect, useRef } from 'react';
import { Send, User, Bot, Loader2 } from 'lucide-react';

const SUGGESTION_CHIPS = [
    '📊 Show top categories',
    '📈 Show trends over time',
    '🥧 Change to pie chart',
    '🔍 Filter by region',
    '🔄 Reset dashboard',
    '🌙 Dark mode',
];

const ChatInterface = ({ messages, onSendMessage, loading, theme }) => {
    const isDark = theme === 'dark';
    const [input, setInput] = useState('');
    const messagesEndRef = useRef(null);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    const handleSubmit = (e) => {
        e.preventDefault();
        if (input.trim() && !loading) {
            onSendMessage(input);
            setInput('');
        }
    };

    return (
        <div className={`flex flex-col h-full ${isDark ? 'bg-slate-900 shadow-none' : 'bg-white shadow-none'}`}>
            {/* Header */}
            <div className={`p-5 border-b flex items-center gap-3 ${isDark ? 'bg-slate-900 border-slate-800' : 'bg-white border-gray-100'}`}>
                <div className="w-10 h-10 rounded-2xl bg-gradient-to-tr from-indigo-500 to-purple-600 flex items-center justify-center text-white shadow-lg shadow-indigo-500/20">
                    <Bot size={22} />
                </div>
                <div>
                    <h3 className={`font-black text-sm ${isDark ? 'text-slate-100' : 'text-gray-800'}`}>BI Assistant</h3>
                    <div className="flex items-center gap-1.5 mt-0.5">
                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]"></span>
                        <span className="text-[10px] text-emerald-500 font-black uppercase tracking-widest">Active Insight</span>
                    </div>
                </div>
            </div>

            {/* Messages */}
            <div className={`flex-1 overflow-y-auto p-4 space-y-6 ${isDark ? 'bg-slate-950/20' : 'bg-gray-50/30'}`}>
                {messages.length === 0 && (
                    <div className="flex flex-col items-center justify-center h-full text-center px-6">
                        <div className={`w-14 h-14 rounded-3xl flex items-center justify-center mb-5 ${isDark ? 'bg-slate-800 text-indigo-400' : 'bg-blue-50 text-blue-500'}`}>
                            <Bot size={28} />
                        </div>
                        <p className={`font-black text-sm uppercase tracking-widest mb-2 ${isDark ? 'text-slate-400' : 'text-gray-800'}`}>Ready to Assist</p>
                        <p className={`text-xs ${isDark ? 'text-slate-500' : 'text-gray-500'} leading-relaxed max-w-[250px] mb-5`}>
                            Ask me anything about your data! Try one of these:
                        </p>
                        <div className="flex flex-wrap gap-2 justify-center max-w-[320px]">
                            {SUGGESTION_CHIPS.map((chip, idx) => (
                                <button
                                    key={idx}
                                    onClick={() => onSendMessage(chip)}
                                    disabled={loading}
                                    className={`px-3 py-1.5 rounded-xl text-xs font-bold transition-all active:scale-95 border ${isDark
                                        ? 'bg-slate-800 border-slate-700 text-slate-300 hover:bg-slate-700 hover:border-indigo-500/50'
                                        : 'bg-white border-gray-200 text-gray-600 hover:bg-indigo-50 hover:border-indigo-300 hover:text-indigo-700'
                                    }`}
                                >
                                    {chip}
                                </button>
                            ))}
                        </div>
                    </div>
                )}

                {messages.map((msg, idx) => (
                    <div
                        key={idx}
                        className={`flex gap-3 max-w-[92%] ${msg.role === 'user' ? 'ml-auto flex-row-reverse' : ''}`}
                    >
                        <div
                            className={`w-9 h-9 rounded-xl flex items-center justify-center shrink-0 shadow-lg ${msg.role === 'user'
                                ? 'bg-indigo-600 text-white'
                                : (isDark ? 'bg-slate-800 text-indigo-400 border border-slate-700' : 'bg-white text-indigo-600 border border-gray-100')
                                }`}
                        >
                            {msg.role === 'user' ? <User size={16} /> : <Bot size={16} />}
                        </div>

                        <div
                            className={`p-4 rounded-2xl text-sm leading-relaxed font-medium shadow-sm ${msg.role === 'user'
                                ? 'bg-indigo-600 text-white rounded-tr-sm'
                                : (isDark ? 'bg-slate-800 text-slate-200 border border-slate-700 rounded-tl-sm' : 'bg-white text-gray-700 border border-gray-100 rounded-tl-sm')
                                }`}
                        >
                            {msg.content}
                        </div>
                    </div>
                ))}
                <div ref={messagesEndRef} />
            </div>

            {/* Input */}
            <div className={`p-5 border-t ${isDark ? 'bg-slate-900 border-slate-800' : 'bg-white border-gray-100'}`}>
                <form onSubmit={handleSubmit} className="relative group">
                    <input
                        type="text"
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        placeholder="Type a command..."
                        className={`w-full px-6 py-4 pr-12 rounded-2xl border transition-all outline-none text-sm font-bold shadow-inner ${isDark
                                ? 'bg-slate-800 border-slate-700 text-white placeholder:text-slate-500 focus:border-indigo-500/50'
                                : 'bg-gray-50 border-gray-200 text-gray-800 placeholder:text-gray-400 focus:bg-white focus:border-indigo-500/50'
                            }`}
                    />
                    <button
                        type="submit"
                        disabled={!input.trim() || loading}
                        className={`absolute right-2.5 top-1/2 -translate-y-1/2 p-2.5 rounded-xl transition-all duration-200 ${input.trim()
                            ? 'bg-indigo-600 text-white hover:bg-indigo-700 shadow-xl shadow-indigo-500/20 active:scale-95'
                            : (isDark ? 'bg-slate-700 text-slate-500' : 'bg-gray-200 text-gray-400')
                            }`}
                    >
                        {loading ? <Loader2 size={18} className="animate-spin" /> : <Send size={18} />}
                    </button>
                </form>
                <div className="text-center mt-3">
                    <p className={`text-[10px] font-bold uppercase tracking-widest ${isDark ? 'text-slate-600' : 'text-gray-400'}`}>Gemini-Powered AI Engine</p>
                </div>
            </div>
        </div>
    );
};

export default ChatInterface;

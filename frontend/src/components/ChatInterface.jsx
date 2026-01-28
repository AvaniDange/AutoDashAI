import React, { useState, useEffect, useRef } from 'react';
import { Send, User, Bot, Loader2 } from 'lucide-react';

const ChatInterface = ({ messages, onSendMessage, loading }) => {
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
        <div className="flex flex-col h-full bg-white shadow-none">
            {/* Header */}
            <div className="p-5 border-b border-gray-100 flex items-center gap-3 bg-white">
                <div className="w-10 h-10 rounded-full bg-gradient-to-tr from-blue-500 to-purple-600 flex items-center justify-center text-white shadow-md">
                    <Bot size={20} />
                </div>
                <div>
                    <h3 className="font-bold text-gray-800 text-sm">Dashboard Assistant</h3>
                    <div className="flex items-center gap-1.5 mt-0.5">
                        <span className="w-1.5 h-1.5 rounded-full bg-green-500"></span>
                        <span className="text-xs text-green-600 font-medium">Online</span>
                    </div>
                </div>
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto p-4 space-y-6 bg-gray-50/30">
                {messages.length === 0 && (
                    <div className="flex flex-col items-center justify-center h-full text-center px-6">
                        <div className="w-12 h-12 bg-blue-50 rounded-2xl flex items-center justify-center mb-4 text-blue-500">
                            <Bot size={24} />
                        </div>
                        <p className="font-semibold text-gray-800">How can I help you?</p>
                        <p className="text-sm text-gray-500 mt-1 max-w-[200px]">Ask me to change chart types, filter data, or find insights.</p>
                    </div>
                )}

                {messages.map((msg, idx) => (
                    <div
                        key={idx}
                        className={`flex gap-3 max-w-[90%] ${msg.role === 'user' ? 'ml-auto flex-row-reverse' : ''}`}
                    >
                        <div
                            className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 shadow-sm ${msg.role === 'user'
                                ? 'bg-blue-600 text-white'
                                : 'bg-white text-blue-600 border border-gray-100'
                                }`}
                        >
                            {msg.role === 'user' ? <User size={14} /> : <Bot size={14} />}
                        </div>

                        <div
                            className={`p-3.5 rounded-2xl text-sm leading-relaxed shadow-sm ${msg.role === 'user'
                                ? 'bg-blue-600 text-white rounded-tr-sm'
                                : 'bg-white text-gray-700 border border-gray-100 rounded-tl-sm'
                                }`}
                        >
                            {msg.content}
                        </div>
                    </div>
                ))}
                <div ref={messagesEndRef} />
            </div>

            {/* Input */}
            <div className="p-4 bg-white border-t border-gray-100">
                <form onSubmit={handleSubmit} className="relative group">
                    <input
                        type="text"
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        placeholder="Ask me something..."
                        className="w-full px-5 py-3.5 pr-12 rounded-full bg-gray-50 border border-gray-200 focus:bg-white focus:border-blue-500 focus:ring-4 focus:ring-blue-50/50 transition-all outline-none text-sm placeholder:text-gray-400"
                    />
                    <button
                        type="submit"
                        disabled={!input.trim() || loading}
                        className={`absolute right-2 top-1/2 -translate-y-1/2 p-2 rounded-full transition-all duration-200 ${input.trim()
                            ? 'bg-blue-600 text-white hover:bg-blue-700 shadow-md transform hover:scale-105 active:scale-95'
                            : 'bg-gray-200 text-gray-400'
                            }`}
                    >
                        {loading ? <Loader2 size={18} className="animate-spin" /> : <Send size={18} />}
                    </button>
                </form>
                <div className="text-center mt-2">
                    <p className="text-[10px] text-gray-400">AI can make mistakes. Verify important info.</p>
                </div>
            </div>
        </div>
    );
};

export default ChatInterface;

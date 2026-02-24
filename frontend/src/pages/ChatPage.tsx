import React, { useState, useRef, useEffect } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import {
    Send,
    Bot,
    User,
    Trash2,
    Loader2,
    Copy,
    Check,
    History,
    Info
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import { chatApi } from '../api';

interface Message {
    role: 'user' | 'assistant';
    content: string;
    timestamp: Date;
}

export default function ChatPage() {
    const [messages, setMessages] = useState<Message[]>([]);
    const [input, setInput] = useState('');
    const [copiedId, setCopiedId] = useState<number | null>(null);
    const scrollRef = useRef<HTMLDivElement>(null);

    // Auto scroll to bottom
    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
    }, [messages]);

    const [error, setError] = useState<string | null>(null);
    const queryMutation = useMutation({
        mutationFn: (text: string) => chatApi.question(text).then(res => res.data),
        onSuccess: (data) => {
            setError(null);
            setMessages(prev => [
                ...prev,
                { role: 'assistant', content: data.answer, timestamp: new Date() }
            ]);
        },
        onError: (err: any) => {
            const detail = err.response?.data?.detail;
            const msg = (Array.isArray(detail) ? detail.map((d: any) => d?.msg ?? d).join(', ') : typeof detail === 'string' ? detail : err.message) || 'Query failed. Please try again.';
            setError(msg);
        },
    });

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        if (!input.trim() || queryMutation.isPending) return;

        const userMessage: Message = { role: 'user', content: input, timestamp: new Date() };
        setMessages(prev => [...prev, userMessage]);
        setInput('');
        queryMutation.mutate(input);
    };

    const copyToClipboard = (text: string, id: number) => {
        navigator.clipboard.writeText(text);
        setCopiedId(id);
        setTimeout(() => setCopiedId(null), 2000);
    };

    return (
        <div className="flex flex-col h-[calc(100vh-160px)] animate-in fade-in duration-500">
            {/* Header Info */}
            <div className="flex items-center justify-between mb-6">
                <div>
                    <h1 className="text-2xl font-bold text-slate-900 dark:text-white">RAG Chat</h1>
                    <p className="text-sm text-slate-500">Query your isolated knowledge base using AI.</p>
                </div>
                <button
                    onClick={() => setMessages([])}
                    className="btn btn-secondary text-red-600 hover:bg-red-50 dark:hover:bg-red-900/10 border-red-100 dark:border-red-900"
                >
                    <Trash2 className="w-4 h-4 mr-2" />
                    Clear Chat
                </button>
            </div>

            <div className="card flex-1 flex flex-col min-h-0 bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-800 shadow-xl overflow-hidden">
                {/* Messages viewport */}
                <div
                    ref={scrollRef}
                    className="flex-1 overflow-y-auto p-4 md:p-8 space-y-8 scroll-smooth"
                >
                    {messages.length === 0 ? (
                        <div className="h-full flex flex-col items-center justify-center text-center max-w-md mx-auto opacity-60">
                            <div className="w-16 h-16 bg-primary-100 dark:bg-primary-900/20 rounded-2xl flex items-center justify-center mb-6">
                                <Bot className="w-8 h-8 text-primary-600" />
                            </div>
                            <h3 className="text-xl font-bold dark:text-white mb-2">How can I help you today?</h3>
                            <p className="text-sm text-slate-500">Ask questions about your uploaded documents. I'll search through your knowledge base to provide cited answers.</p>

                            <div className="grid grid-cols-1 gap-3 w-full mt-8">
                                <button onClick={() => setInput("Summarize my recent documents")} className="px-4 py-3 bg-slate-50 dark:bg-slate-800 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-xl text-xs font-semibold text-slate-600 dark:text-slate-400 text-left transition-colors">
                                    "Summarize my recent documents"
                                </button>
                                <button onClick={() => setInput("What are the key takeaways?")} className="px-4 py-3 bg-slate-50 dark:bg-slate-800 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-xl text-xs font-semibold text-slate-600 dark:text-slate-400 text-left transition-colors">
                                    "What are the key takeaways?"
                                </button>
                            </div>
                        </div>
                    ) : (
                        messages.map((msg, i) => (
                            <div key={i} className={cn(
                                "flex max-w-4xl mx-auto items-start group",
                                msg.role === 'assistant' ? "flex-row" : "flex-row-reverse"
                            )}>
                                <div className={cn(
                                    "w-10 h-10 rounded-xl flex items-center justify-center shrink-0 shadow-sm transition-transform",
                                    msg.role === 'assistant' ? "bg-primary-600 text-white mr-4" : "bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 ml-4"
                                )}>
                                    {msg.role === 'assistant' ? <Bot className="w-6 h-6" /> : <User className="w-6 h-6 text-slate-600 dark:text-slate-400" />}
                                </div>

                                <div className={cn(
                                    "flex-1 min-w-0 flex flex-col",
                                    msg.role === 'user' ? "items-end" : "items-start"
                                )}>
                                    <div className={cn(
                                        "relative p-5 rounded-2xl shadow-sm border",
                                        msg.role === 'assistant'
                                            ? "bg-slate-50 dark:bg-slate-800 border-slate-100 dark:border-slate-700 prose dark:prose-invert max-w-full"
                                            : "bg-primary-600 text-white border-primary-500"
                                    )}>
                                        {msg.role === 'assistant' ? (
                                            <ReactMarkdown>{msg.content}</ReactMarkdown>
                                        ) : (
                                            <p className="text-[15px] leading-relaxed font-medium">{msg.content}</p>
                                        )}

                                        {msg.role === 'assistant' && (
                                            <button
                                                onClick={() => copyToClipboard(msg.content, i)}
                                                className="absolute top-2 right-2 p-1.5 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-md opacity-0 group-hover:opacity-100 transition-opacity"
                                            >
                                                {copiedId === i ? <Check className="w-3 h-3 text-emerald-500" /> : <Copy className="w-3 h-3 text-slate-400" />}
                                            </button>
                                        )}
                                    </div>
                                    <span className="text-[10px] font-bold text-slate-400 mt-2 uppercase tracking-tight">
                                        {msg.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                                    </span>
                                </div>
                            </div>
                        ))
                    )}

                    {queryMutation.isPending && (
                        <div className="flex max-w-4xl mx-auto items-start">
                            <div className="w-10 h-10 rounded-xl bg-primary-600 text-white mr-4 flex items-center justify-center shadow-lg animate-pulse">
                                <Bot className="w-6 h-6" />
                            </div>
                            <div className="bg-slate-50 dark:bg-slate-800 border border-slate-100 dark:border-slate-700 p-5 rounded-2xl flex items-center space-x-2">
                                <div className="w-1.5 h-1.5 bg-primary-400 rounded-full animate-bounce [animation-delay:-0.3s]"></div>
                                <div className="w-1.5 h-1.5 bg-primary-400 rounded-full animate-bounce [animation-delay:-0.15s]"></div>
                                <div className="w-1.5 h-1.5 bg-primary-400 rounded-full animate-bounce"></div>
                            </div>
                        </div>
                    )}
                </div>

                {/* Input area */}
                <div className="p-4 md:p-6 border-t border-slate-100 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-950/20">
                    <form
                        onSubmit={handleSubmit}
                        className="max-w-4xl mx-auto relative flex items-center"
                    >
                        <input
                            type="text"
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            placeholder="Ask anything about your documents..."
                            className="w-full bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl pl-6 pr-14 py-4 focus:ring-4 focus:ring-primary-100 dark:focus:ring-primary-900/10 focus:border-primary-400 transition-all outline-none dark:text-white shadow-xl"
                        />
                        <button
                            type="submit"
                            disabled={!input.trim() || queryMutation.isPending}
                            className="absolute right-2 p-3 bg-primary-600 text-white rounded-xl hover:bg-primary-700 disabled:opacity-50 disabled:grayscale transition-all shadow-lg shadow-primary-500/30"
                        >
                            <Send className="w-5 h-5" />
                        </button>
                    </form>
                    {error && (
                        <p className="text-xs text-center text-red-500 mt-2">{error}</p>
                    )}
                    <p className="text-[10px] text-center text-slate-400 mt-4 leading-relaxed font-medium">
                        <Info className="w-3 h-3 inline mr-1" />
                        RAG SaaS helps you get answers from your isolated tenant knowledge base. Queries are secure and strictly scoped.
                    </p>
                </div>
            </div>
        </div>
    );
}

// Helper (normally imported)
function cn(...inputs: any[]) {
    return inputs.filter(Boolean).join(' ');
}

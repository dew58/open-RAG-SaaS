import React from 'react';
import { useQuery } from '@tanstack/react-query';
import {
    FileText,
    MessageSquare,
    Clock,
    Activity,
    TrendingUp,
    ArrowUpRight,
    Database
} from 'lucide-react';
import { clientApi, chatApi, documentApi } from '../api';

export default function DashboardOverview() {
    const { data: tenant } = useQuery({ queryKey: ['tenant'], queryFn: () => clientApi.me().then(res => res.data) });
    const { data: docs } = useQuery({ queryKey: ['documents'], queryFn: () => documentApi.list() });
    const { data: history } = useQuery({ queryKey: ['history'], queryFn: () => chatApi.history(1, 5).then(res => res.data) });

    const stats = [
        { label: 'Total Documents', value: docs?.length || 0, icon: FileText, color: 'text-blue-600', bg: 'bg-blue-100 dark:bg-blue-900/30' },
        { label: 'Total Queries', value: history?.totalCount || 0, icon: MessageSquare, color: 'text-primary-600', bg: 'bg-primary-100 dark:bg-primary-900/30' },
        { label: 'Avg Latency', value: '1.2s', icon: Activity, color: 'text-emerald-600', bg: 'bg-emerald-100 dark:bg-emerald-900/30' },
        { label: 'Available Keys', value: '2', icon: Database, color: 'text-amber-600', bg: 'bg-amber-100 dark:bg-amber-900/30' },
    ];

    return (
        <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                    <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Welcome, {tenant?.name || 'Loading...'}</h1>
                    <p className="text-slate-500 dark:text-slate-400">Here's what's happening with your RAG instance today.</p>
                </div>
                <div className="flex items-center space-x-3">
                    <span className="flex items-center text-xs font-semibold px-2 py-1 rounded bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300">
                        <Clock className="w-3 h-3 mr-1" />
                        Last synced: Just now
                    </span>
                </div>
            </div>

            {/* Stats Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
                {stats.map((stat, i) => (
                    <div key={i} className="card p-6 flex items-start justify-between group cursor-default">
                        <div>
                            <p className="text-sm font-medium text-slate-500 dark:text-slate-400 mb-1">{stat.label}</p>
                            <h3 className="text-2xl font-bold text-slate-900 dark:text-white tracking-tight">{stat.value}</h3>
                        </div>
                        <div className={cn("p-2 rounded-lg transition-transform group-hover:scale-110", stat.bg)}>
                            <stat.icon className={cn("w-6 h-6", stat.color)} />
                        </div>
                    </div>
                ))}
            </div>

            <div className="grid lg:grid-cols-3 gap-8">
                {/* Main Chart/Activity Placeholder */}
                <div className="lg:col-span-2 space-y-8">
                    <div className="card p-6 min-h-[400px] flex flex-col justify-between">
                        <div className="flex items-center justify-between mb-8">
                            <h3 className="font-bold text-lg dark:text-white flex items-center">
                                <TrendingUp className="w-5 h-5 mr-2 text-primary-600" />
                                Query Volume
                            </h3>
                            <select className="bg-slate-50 dark:bg-slate-800 border-none rounded-lg text-xs font-bold py-1 px-3">
                                <option>Last 7 Days</option>
                                <option>Last 30 Days</option>
                            </select>
                        </div>

                        <div className="flex-1 flex items-end justify-between space-x-2">
                            {[45, 67, 32, 89, 54, 76, 90].map((h, i) => (
                                <div key={i} className="flex-1 flex flex-col items-center group">
                                    <div
                                        className="w-full bg-primary-100 dark:bg-primary-900/20 rounded-t-md relative overflow-hidden group-hover:bg-primary-200 dark:group-hover:bg-primary-900/40 transition-colors"
                                        style={{ height: `${h}%` }}
                                    >
                                        <div className="absolute bottom-0 w-full bg-primary-600 transition-all duration-1000 ease-out" style={{ height: '30%' }}></div>
                                    </div>
                                    <span className="text-[10px] font-bold text-slate-400 mt-3">{"MTWTFSS"[i]}</span>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>

                {/* Right Sidebar: Recent Activity */}
                <div className="space-y-8">
                    <div className="card p-6">
                        <h3 className="font-bold text-lg dark:text-white mb-6">Recent Queries</h3>
                        <div className="space-y-6">
                            {history?.items?.length ? (
                                history.items.slice(0, 5).map((query: any, i: number) => (
                                    <div key={i} className="flex items-start">
                                        <div className="w-8 h-8 rounded-full bg-slate-100 dark:bg-slate-800 flex items-center justify-center shrink-0">
                                            <MessageSquare className="w-4 h-4 text-slate-500" />
                                        </div>
                                        <div className="ml-4 min-w-0">
                                            <p className="text-sm font-medium text-slate-900 dark:text-white truncate">
                                                {query.query_text}
                                            </p>
                                            <p className="text-xs text-slate-500 mt-1">
                                                {new Date(query.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                                            </p>
                                        </div>
                                    </div>
                                ))
                            ) : (
                                <p className="text-sm text-slate-500 text-center py-4 italic">No recent activity</p>
                            )}
                        </div>
                        <button className="w-full mt-6 py-2 px-4 border border-slate-200 dark:border-slate-800 rounded-lg text-sm font-semibold text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors flex items-center justify-center">
                            View All Logs
                            <ArrowUpRight className="ml-2 w-4 h-4" />
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}

// Inline helper for convenience in this file
function cn(...inputs: any[]) {
    return inputs.filter(Boolean).join(' ');
}

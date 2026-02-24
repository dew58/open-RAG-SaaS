import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
    FileSpreadsheet,
    Search,
    Filter,
    ChevronLeft,
    ChevronRight,
    Clock,
    MessageSquare,
    Cpu,
    ArrowUpRight,
    Loader2,
    Calendar
} from 'lucide-react';
import { chatApi, exportApi } from '../api';
import { format } from 'date-fns';

export default function HistoryPage() {
    const [page, setPage] = useState(1);
    const [searchTerm, setSearchTerm] = useState('');
    const limit = 10;

    const { data: history, isLoading } = useQuery({
        queryKey: ['history', page],
        queryFn: () => chatApi.history(page, limit).then(res => res.data),
        placeholderData: (previousData) => previousData
    });

    const handleExport = async () => {
        try {
            const response = await exportApi.queries();
            const url = window.URL.createObjectURL(new Blob([response.data]));
            const link = document.createElement('a');
            link.href = url;
            link.setAttribute('download', `query_logs_${format(new Date(), 'yyyy-MM-dd')}.xlsx`);
            document.body.appendChild(link);
            link.click();
            link.remove();
        } catch (error) {
            console.error('Export failed', error);
        }
    };

    const totalPages = history ? Math.ceil(history.totalCount / limit) : 1;

    return (
        <div className="space-y-8 animate-in fade-in duration-500">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                    <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Query History</h1>
                    <p className="text-slate-500 dark:text-slate-400">Audit logs and responses for all RAG interactions.</p>
                </div>
                <button
                    onClick={handleExport}
                    className="btn btn-secondary text-primary-600 border-primary-100 dark:border-primary-900/30"
                >
                    <FileSpreadsheet className="w-4 h-4 mr-2" />
                    Export to Excel
                </button>
            </div>

            <div className="card overflow-hidden">
                <div className="p-4 md:p-6 border-b border-slate-100 dark:border-slate-800 bg-white dark:bg-slate-900 flex flex-col md:flex-row md:items-center justify-between gap-4">
                    <div className="relative flex-1 max-w-md">
                        <Search className="absolute left-3 top-2.5 w-5 h-5 text-slate-400" />
                        <input
                            type="text"
                            placeholder="Filter by query text..."
                            className="input pl-10 h-11"
                            value={searchTerm}
                            onChange={(e) => setSearchTerm(e.target.value)}
                        />
                    </div>
                    <div className="flex items-center space-x-2">
                        <button className="btn btn-secondary py-2 border-slate-200 dark:border-slate-700">
                            <Calendar className="w-4 h-4 mr-2" />
                            Date Range
                        </button>
                        <button className="btn btn-secondary py-2 border-slate-200 dark:border-slate-700">
                            <Filter className="w-4 h-4 mr-2" />
                            All Models
                        </button>
                    </div>
                </div>

                <div className="overflow-x-auto">
                    {isLoading ? (
                        <div className="p-12 text-center text-slate-500">
                            <Loader2 className="w-8 h-8 animate-spin mx-auto mb-4 text-primary-600" />
                            Loading history...
                        </div>
                    ) : !history || history.items.length === 0 ? (
                        <div className="p-16 text-center">
                            <Clock className="w-12 h-12 text-slate-200 dark:text-slate-800 mx-auto mb-4" />
                            <h3 className="text-lg font-bold dark:text-white">No logs found</h3>
                            <p className="text-sm text-slate-500">Start chatting with your documents to see logs here.</p>
                        </div>
                    ) : (
                        <table className="w-full text-left">
                            <thead>
                                <tr className="bg-slate-50/50 dark:bg-slate-800/50 border-b border-slate-100 dark:border-slate-800">
                                    <th className="px-6 py-4 text-[11px] font-bold text-slate-400 uppercase tracking-widest">Query</th>
                                    <th className="px-6 py-4 text-[11px] font-bold text-slate-400 uppercase tracking-widest">Provider</th>
                                    <th className="px-6 py-4 text-[11px] font-bold text-slate-400 uppercase tracking-widest">Latency</th>
                                    <th className="px-6 py-4 text-[11px] font-bold text-slate-400 uppercase tracking-widest">Timestamp</th>
                                    <th className="px-6 py-4"></th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-50 dark:divide-slate-800/50">
                                {history.items.map((log: any) => (
                                    <tr key={log.id} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/20 transition-colors group">
                                        <td className="px-6 py-4">
                                            <div className="flex items-start max-w-md">
                                                <MessageSquare className="w-4 h-4 text-slate-400 mt-1 shrink-0" />
                                                <div className="ml-4 min-w-0">
                                                    <p className="text-sm font-bold text-slate-900 dark:text-white truncate" title={log.query_text}>
                                                        {log.query_text}
                                                    </p>
                                                    <p className="text-xs text-slate-500 line-clamp-1 mt-1 italic">
                                                        {log.answer_text}
                                                    </p>
                                                </div>
                                            </div>
                                        </td>
                                        <td className="px-6 py-4">
                                            <div className="flex items-center text-xs font-bold text-slate-600 dark:text-slate-400">
                                                <Cpu className="w-3.5 h-3.5 mr-2" />
                                                Gemini-Flash
                                            </div>
                                        </td>
                                        <td className="px-6 py-4">
                                            <span className="text-xs font-bold text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-900/20 px-2 py-0.5 rounded">
                                                1.4s
                                            </span>
                                        </td>
                                        <td className="px-6 py-4 text-sm text-slate-500 whitespace-nowrap">
                                            {format(new Date(log.created_at), 'MMM d, HH:mm')}
                                        </td>
                                        <td className="px-6 py-4 text-right">
                                            <button className="p-2 rounded-lg text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 opacity-0 group-hover:opacity-100 transition-all">
                                                <ArrowUpRight className="w-4 h-4" />
                                            </button>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    )}
                </div>

                {/* Pagination Footer */}
                {history && totalPages > 1 && (
                    <div className="px-6 py-4 border-t border-slate-100 dark:border-slate-800 flex items-center justify-between bg-white dark:bg-slate-900">
                        <p className="text-sm text-slate-500 font-medium font-medium">
                            Showing <span className="text-slate-900 dark:text-white">{((page - 1) * limit) + 1}</span> to <span className="text-slate-900 dark:text-white">{Math.min(page * limit, history.totalCount)}</span> of <span className="text-slate-900 dark:text-white">{history.totalCount}</span> results
                        </p>
                        <div className="flex items-center space-x-2">
                            <button
                                onClick={() => setPage(p => Math.max(1, p - 1))}
                                disabled={page === 1}
                                className="p-2 border border-slate-200 dark:border-slate-800 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-800 disabled:opacity-30"
                            >
                                <ChevronLeft className="w-5 h-5" />
                            </button>
                            <button
                                onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                                disabled={page === totalPages}
                                className="p-2 border border-slate-200 dark:border-slate-800 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-800 disabled:opacity-30"
                            >
                                <ChevronRight className="w-5 h-5" />
                            </button>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}

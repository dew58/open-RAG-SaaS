import React, { useState, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
    File,
    Upload,
    Trash2,
    Search,
    Filter,
    CheckCircle2,
    XCircle,
    Clock,
    HardDrive,
    MoreVertical,
    Download,
    AlertTriangle,
    FileText,
    Loader2
} from 'lucide-react';
import { useDropzone } from 'react-dropzone';
import { documentApi } from '../api';
import { formatDistanceToNow } from 'date-fns';

export default function DocumentsPage() {
    const [searchTerm, setSearchTerm] = useState('');
    const [uploadingFiles, setUploadingFiles] = useState<{ name: string, progress: number, error?: string }[]>([]);
    const queryClient = useQueryClient();

    // Queries
    const { data: documents, isLoading } = useQuery({
        queryKey: ['documents'],
        queryFn: () => documentApi.list()
    });

    // Mutations
    const uploadMutation = useMutation({
        mutationFn: (file: File) => documentApi.upload(file),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['documents'] });
        }
    });

    const deleteMutation = useMutation({
        mutationFn: (id: string) => documentApi.delete(id),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['documents'] });
        }
    });

    // File Drop Logic
    const onDrop = useCallback((acceptedFiles: File[]) => {
        acceptedFiles.forEach(file => {
            setUploadingFiles(prev => [...prev, { name: file.name, progress: 0 }]);

            // Real upload simulation / call
            uploadMutation.mutate(file, {
                onSuccess: () => {
                    setUploadingFiles(prev => prev.filter(f => f.name !== file.name));
                },
                onError: (err: any) => {
                    setUploadingFiles(prev => prev.map(f =>
                        f.name === file.name ? { ...f, error: err.response?.data?.detail || 'Upload failed' } : f
                    ));
                }
            });
        });
    }, [uploadMutation]);

    const { getRootProps, getInputProps, isDragActive } = useDropzone({
        onDrop,
        accept: {
            'application/pdf': ['.pdf'],
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
            'text/plain': ['.txt']
        }
    });

    const filteredDocs = documents?.filter((doc: any) =>
        (doc.original_filename ?? doc.filename ?? '').toLowerCase().includes(searchTerm.toLowerCase())
    ) || [];

    return (
        <div className="space-y-8 animate-in fade-in duration-500">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                    <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Knowledge Base</h1>
                    <p className="text-slate-500 dark:text-slate-400">Manage documents used for RAG indexing and retrieval.</p>
                </div>
                <div className="flex items-center space-x-2">
                    <div className="bg-primary-50 dark:bg-primary-900/20 text-primary-700 dark:text-primary-400 px-3 py-1 rounded-lg text-xs font-bold border border-primary-100 dark:border-primary-800 flex items-center">
                        <HardDrive className="w-3 h-3 mr-1.5" />
                        Storage: {documents ? (documents.length * 1.2).toFixed(1) : 0} MB / 500 MB
                    </div>
                </div>
            </div>

            <div className="grid lg:grid-cols-4 gap-8">
                {/* Left: Upload & Filters */}
                <div className="lg:col-span-1 space-y-6">
                    <div
                        {...getRootProps()}
                        className={cn(
                            "border-2 border-dashed rounded-2xl p-8 text-center cursor-pointer transition-all",
                            isDragActive
                                ? "border-primary-500 bg-primary-50 dark:bg-primary-900/20"
                                : "border-slate-200 dark:border-slate-800 hover:border-primary-400 bg-white dark:bg-slate-900"
                        )}
                    >
                        <input {...getInputProps()} />
                        <div className="w-12 h-12 bg-primary-100 dark:bg-primary-900/40 rounded-full flex items-center justify-center mx-auto mb-4">
                            <Upload className="w-6 h-6 text-primary-600 dark:text-primary-400" />
                        </div>
                        <h3 className="font-bold text-slate-900 dark:text-white mb-1">Upload Documents</h3>
                        <p className="text-xs text-slate-500">Drop PDF, DOCX or TXT here</p>
                    </div>

                    <div className="card p-6 space-y-6">
                        <h4 className="font-bold text-sm uppercase tracking-wider text-slate-400">Settings</h4>
                        <div className="space-y-4">
                            <label className="flex items-center space-x-3 cursor-pointer group">
                                <input type="checkbox" className="w-4 h-4 rounded text-primary-600 focus:ring-primary-500 border-slate-300 dark:border-slate-700 dark:bg-slate-950" defaultChecked />
                                <span className="text-sm font-medium text-slate-600 dark:text-slate-400 group-hover:text-slate-900 dark:group-hover:text-white">Auto-index on upload</span>
                            </label>
                            <label className="flex items-center space-x-3 cursor-pointer group">
                                <input type="checkbox" className="w-4 h-4 rounded text-primary-600 focus:ring-primary-500 border-slate-300 dark:border-slate-700 dark:bg-slate-950" defaultChecked />
                                <span className="text-sm font-medium text-slate-600 dark:text-slate-400 group-hover:text-slate-900 dark:group-hover:text-white">Enable OCR processing</span>
                            </label>
                        </div>
                    </div>
                </div>

                {/* Right: List */}
                <div className="lg:col-span-3 space-y-6">
                    {/* Active Uploads */}
                    {uploadingFiles.length > 0 && (
                        <div className="space-y-3">
                            {uploadingFiles.map((file, i) => (
                                <div key={i} className="card p-4 border-primary-100 dark:border-primary-900/30 bg-primary-50/50 dark:bg-primary-900/10 flex items-center justify-between">
                                    <div className="flex items-center min-w-0">
                                        <Loader2 className="w-5 h-5 text-primary-600 animate-spin mr-3 shrink-0" />
                                        <div className="min-w-0">
                                            <p className="text-sm font-bold text-slate-900 dark:text-white truncate">{file.name}</p>
                                            {file.error ? (
                                                <p className="text-xs text-red-500 font-medium">{file.error}</p>
                                            ) : (
                                                <p className="text-xs text-slate-500 font-medium">Processing & indexing...</p>
                                            )}
                                        </div>
                                    </div>
                                    {file.error && (
                                        <button onClick={() => setUploadingFiles(prev => prev.filter(f => f.name !== file.name))}>
                                            <XCircle className="w-5 h-5 text-slate-400" />
                                        </button>
                                    )}
                                </div>
                            ))}
                        </div>
                    )}

                    <div className="flex items-center space-x-4 mb-2">
                        <div className="relative flex-1">
                            <Search className="absolute left-3 top-2.5 w-5 h-5 text-slate-400" />
                            <input
                                type="text"
                                placeholder="Search knowledge base..."
                                className="input pl-10 h-11"
                                value={searchTerm}
                                onChange={(e) => setSearchTerm(e.target.value)}
                            />
                        </div>
                        <button className="btn btn-secondary h-11 px-4">
                            <Filter className="w-5 h-5" />
                        </button>
                    </div>

                    <div className="card overflow-hidden">
                        {isLoading ? (
                            <div className="p-12 text-center space-y-4">
                                <Loader2 className="w-8 h-8 text-primary-600 animate-spin mx-auto" />
                                <p className="text-sm text-slate-500 font-medium">Fetching documents...</p>
                            </div>
                        ) : filteredDocs.length === 0 ? (
                            <div className="p-16 text-center">
                                <div className="w-20 h-20 bg-slate-50 dark:bg-slate-800 rounded-2xl flex items-center justify-center mx-auto mb-6">
                                    <FileText className="w-10 h-10 text-slate-300 dark:text-slate-600" />
                                </div>
                                <h3 className="text-xl font-bold dark:text-white mb-2">No documents found</h3>
                                <p className="text-sm text-slate-500 max-w-xs mx-auto mb-8">Upload documents to start using the RAG features. We support PDF, DOCX, and TXT files.</p>
                                <button {...getRootProps()} className="btn btn-primary px-8">
                                    Upload First File
                                </button>
                            </div>
                        ) : (
                            <div className="overflow-x-auto">
                                <table className="w-full text-left">
                                    <thead>
                                        <tr className="border-b border-slate-100 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/50">
                                            <th className="px-6 py-4 text-[11px] font-bold text-slate-400 uppercase tracking-widest">Document</th>
                                            <th className="px-6 py-4 text-[11px] font-bold text-slate-400 uppercase tracking-widest">Type</th>
                                            <th className="px-6 py-4 text-[11px] font-bold text-slate-400 uppercase tracking-widest">Status</th>
                                            <th className="px-6 py-4 text-[11px] font-bold text-slate-400 uppercase tracking-widest">Uploaded</th>
                                            <th className="px-6 py-4 text-right"></th>
                                        </tr>
                                    </thead>
                                    <tbody className="divide-y divide-slate-50 dark:divide-slate-800/50">
                                        {filteredDocs.map((doc: any) => (
                                            <tr key={doc.id} className="group hover:bg-slate-50/80 dark:hover:bg-slate-800/30 transition-colors">
                                                <td className="px-6 py-4">
                                                    <div className="flex items-center">
                                                        <div className="w-10 h-10 rounded-lg bg-primary-100 dark:bg-primary-900/20 flex items-center justify-center mr-4">
                                                            <File className="w-5 h-5 text-primary-600 dark:text-primary-400" />
                                                        </div>
                                                        <div className="min-w-0">
                                                            <p className="text-sm font-bold text-slate-900 dark:text-white truncate max-w-[200px]">{doc.original_filename ?? doc.filename}</p>
                                                            <p className="text-[10px] text-slate-500 font-bold uppercase tracking-tight">{((doc.file_size_bytes ?? doc.size ?? 0) / 1024).toFixed(1)} KB</p>
                                                        </div>
                                                    </div>
                                                </td>
                                                <td className="px-6 py-4">
                                                    <span className="text-xs font-bold text-slate-600 dark:text-slate-400 uppercase tracking-tight bg-slate-100 dark:bg-slate-800 px-2 py-0.5 rounded">
                                                        {(doc.original_filename ?? doc.filename ?? '').split('.').pop()}
                                                    </span>
                                                </td>
                                                <td className="px-6 py-4">
                                                    <div className={cn(
                                                        "flex items-center text-xs font-bold",
                                                        doc.status === 'indexed' ? "text-emerald-600 dark:text-emerald-400" : doc.status === 'failed' ? "text-red-600 dark:text-red-400" : "text-amber-600 dark:text-amber-400"
                                                    )}>
                                                        {doc.status === 'indexed' ? <CheckCircle2 className="w-4 h-4 mr-1.5" /> : doc.status === 'failed' ? <XCircle className="w-4 h-4 mr-1.5" /> : <Clock className="w-4 h-4 mr-1.5" />}
                                                        {doc.status === 'indexed' ? 'Indexed' : doc.status === 'failed' ? 'Failed' : doc.status ?? 'Processing'}
                                                    </div>
                                                </td>
                                                <td className="px-6 py-4 text-sm text-slate-500 whitespace-nowrap">
                                                    {formatDistanceToNow(new Date(doc.created_at))} ago
                                                </td>
                                                <td className="px-6 py-4 text-right">
                                                    <div className="flex items-center justify-end space-x-1 opacity-0 group-hover:opacity-100 transition-opacity">
                                                        <button className="p-2 text-slate-400 hover:text-primary-600 dark:hover:text-primary-400">
                                                            <Download className="w-4 h-4" />
                                                        </button>
                                                        <button
                                                            onClick={() => deleteMutation.mutate(doc.id)}
                                                            className="p-2 text-slate-400 hover:text-red-600 dark:hover:text-red-400"
                                                        >
                                                            <Trash2 className="w-4 h-4" />
                                                        </button>
                                                    </div>
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}

// Inline helper
function cn(...inputs: any[]) {
    return inputs.filter(Boolean).join(' ');
}

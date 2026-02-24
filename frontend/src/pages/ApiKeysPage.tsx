import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
    Key,
    Plus,
    Copy,
    Check,
    Trash2,
    Eye,
    EyeOff,
    AlertCircle,
    ShieldCheck,
    Globe,
    Loader2,
    ExternalLink
} from 'lucide-react';
import { clientApi } from '../api';

export default function ApiKeysPage() {
    const [newKeyName, setNewKeyName] = useState('');
    const [copiedId, setCopiedId] = useState<string | null>(null);
    const [revealedKeys, setRevealedKeys] = useState<Record<string, boolean>>({});
    const queryClient = useQueryClient();

    const { data: keys, isLoading } = useQuery({
        queryKey: ['api-keys'],
        queryFn: () => clientApi.listKeys().then(res => res.data)
    });

    const createMutation = useMutation({
        mutationFn: (name: string) => clientApi.generateKey(name),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['api-keys'] });
            setNewKeyName('');
        }
    });

    const copyToClipboard = (text: string, id: string) => {
        navigator.clipboard.writeText(text);
        setCopiedId(id);
        setTimeout(() => setCopiedId(null), 2000);
    };

    const toggleReveal = (id: string) => {
        setRevealedKeys(prev => ({ ...prev, [id]: !prev[id] }));
    };

    return (
        <div className="space-y-8 animate-in fade-in duration-500">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                    <h1 className="text-2xl font-bold text-slate-900 dark:text-white">API Keys</h1>
                    <p className="text-slate-500 dark:text-slate-400">Manage tenant-scoped keys for programmatic RAG access.</p>
                </div>
                <div className="flex items-center space-x-3 text-xs font-bold text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-900/20 px-3 py-1.5 rounded-lg border border-emerald-100 dark:border-emerald-900">
                    <ShieldCheck className="w-4 h-4 mr-2" />
                    Tenant Isolation Active
                </div>
            </div>

            <div className="grid lg:grid-cols-3 gap-8">
                <div className="lg:col-span-2 space-y-6">
                    <div className="card overflow-hidden">
                        <div className="px-6 py-4 border-b border-slate-100 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/50 flex items-center justify-between">
                            <h3 className="font-bold text-sm uppercase tracking-widest text-slate-500">Active Keys</h3>
                            <span className="text-xs font-bold bg-slate-100 dark:bg-slate-800 px-2 py-0.5 rounded text-slate-500">
                                {keys?.length || 0} / 5
                            </span>
                        </div>

                        {isLoading ? (
                            <div className="p-12 text-center text-slate-500">
                                <Loader2 className="w-8 h-8 animate-spin mx-auto text-primary-600 mb-2" />
                                Loading keys...
                            </div>
                        ) : !keys || keys.length === 0 ? (
                            <div className="p-16 text-center">
                                <Key className="w-12 h-12 text-slate-200 dark:text-slate-800 mx-auto mb-4" />
                                <p className="text-sm text-slate-500 mb-6">No API keys generated yet.</p>
                                <button className="btn btn-primary" onClick={() => document.getElementById('newKeyName')?.focus()}>
                                    Generate First Key
                                </button>
                            </div>
                        ) : (
                            <div className="divide-y divide-slate-50 dark:divide-slate-800/50">
                                {keys.map((key: any) => (
                                    <div key={key.id} className="p-6 flex flex-col md:flex-row md:items-center justify-between gap-4 hover:bg-slate-50/30 dark:hover:bg-slate-800/10 transition-colors">
                                        <div className="space-y-2 flex-1">
                                            <div className="flex items-center">
                                                <span className="font-bold text-slate-900 dark:text-white mr-3">{key.name}</span>
                                                <span className="text-[10px] font-bold bg-primary-50 dark:bg-primary-900/20 text-primary-600 dark:text-primary-400 px-1.5 py-0.5 rounded">
                                                    v1
                                                </span>
                                            </div>
                                            <div className="flex items-center space-x-2">
                                                <code className="text-xs font-mono bg-slate-100 dark:bg-slate-950 px-3 py-1.5 rounded-lg border border-slate-200 dark:border-slate-800 flex-1 max-w-sm overflow-hidden text-slate-600 dark:text-slate-400 block">
                                                    {revealedKeys[key.id] ? key.key : 'sk_rag_' + '•'.repeat(24)}
                                                </code>
                                                <div className="flex items-center space-x-1">
                                                    <button
                                                        onClick={() => toggleReveal(key.id)}
                                                        className="p-2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
                                                    >
                                                        {revealedKeys[key.id] ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                                                    </button>
                                                    <button
                                                        onClick={() => copyToClipboard(key.key, key.id)}
                                                        className="p-2 text-slate-400 hover:text-primary-400"
                                                    >
                                                        {copiedId === key.id ? <Check className="w-4 h-4 text-emerald-500" /> : <Copy className="w-4 h-4" />}
                                                    </button>
                                                </div>
                                            </div>
                                        </div>

                                        <div className="flex items-center text-[10px] text-slate-500 uppercase tracking-widest font-bold md:flex-col md:items-end md:justify-center">
                                            <span className="md:mb-1">Last used</span>
                                            <span className="ml-2 md:ml-0 text-slate-400">Never</span>
                                        </div>

                                        <button className="p-2 text-slate-400 hover:text-red-500 transition-colors shrink-0">
                                            <Trash2 className="w-4 h-4" />
                                        </button>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                </div>

                <div className="space-y-6">
                    <div className="card p-6 bg-primary-600 text-white relative overflow-hidden">
                        <div className="absolute top-0 right-0 p-4 opacity-10">
                            <Key className="w-24 h-24" />
                        </div>
                        <div className="relative z-10">
                            <h3 className="text-lg font-bold mb-4">Generate New Key</h3>
                            <div className="space-y-4">
                                <div>
                                    <label className="text-xs font-bold uppercase tracking-widest text-primary-100 mb-2 block">
                                        Key Description
                                    </label>
                                    <input
                                        id="newKeyName"
                                        type="text"
                                        value={newKeyName}
                                        onChange={(e) => setNewKeyName(e.target.value)}
                                        placeholder="e.g. Production API"
                                        className="w-full bg-primary-700/50 border-primary-500 border rounded-lg px-4 py-2 text-sm placeholder:text-primary-300 focus:outline-none focus:ring-2 focus:ring-primary-400"
                                    />
                                </div>
                                <button
                                    onClick={() => createMutation.mutate(newKeyName)}
                                    disabled={!newKeyName.trim() || createMutation.isPending}
                                    className="btn bg-white text-primary-600 w-full font-bold shadow-lg shadow-primary-700/50 disabled:opacity-50"
                                >
                                    {createMutation.isPending ? <Loader2 className="w-5 h-5 animate-spin mx-auto" /> : 'Generate Key'}
                                </button>
                            </div>
                        </div>
                    </div>

                    <div className="card p-6 space-y-4">
                        <div className="flex items-start space-x-3 text-amber-600 dark:text-amber-400">
                            <AlertCircle className="w-5 h-5 shrink-0" />
                            <div className="text-sm">
                                <p className="font-bold mb-1">Security Warning</p>
                                <p className="opacity-80">Keys provide full RAG access to this tenant. Never share them in public repositories or client-side code.</p>
                            </div>
                        </div>
                        <a href="#" className="flex items-center text-sm font-bold text-primary-600 hover:text-primary-500 pt-2 border-t border-slate-100 dark:border-slate-800">
                            Read Security Best Practices
                            <ExternalLink className="w-3 h-3 ml-2" />
                        </a>
                    </div>
                </div>
            </div>
        </div>
    );
}

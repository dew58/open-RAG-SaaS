import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { User, Mail, Lock, Building2, AlertCircle, Loader2, CheckCircle2 } from 'lucide-react';
import { useAuth } from '../providers/AuthProvider';

export default function RegisterPage() {
    const [formData, setFormData] = useState({
        email: '',
        password: '',
        full_name: '',
        client_name: '',
    });
    const [error, setError] = useState<string | null>(null);
    const [isSubmitting, setIsSubmitting] = useState(false);

    const { register } = useAuth();
    const navigate = useNavigate();

    const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        setFormData({ ...formData, [e.target.id]: e.target.value });
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setIsSubmitting(true);
        setError(null);

        try {
            await register(formData);
            navigate('/dashboard');
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Registration failed. Please try again.');
        } finally {
            setIsSubmitting(false);
        }
    };

    return (
        <div className="min-h-[calc(100vh-80px)] flex items-center justify-center px-6 py-12">
            <div className="max-w-4xl w-full grid md:grid-cols-2 bg-white dark:bg-slate-900 rounded-3xl overflow-hidden shadow-2xl border border-slate-100 dark:border-slate-800">

                {/* Left Side: Branding/Value Prop */}
                <div className="hidden md:flex flex-col justify-between p-12 bg-primary-600 text-white relative overflow-hidden">
                    <div className="absolute top-0 right-0 w-64 h-64 bg-primary-500 rounded-full blur-3xl opacity-50 -translate-y-1/2 translate-x-1/2"></div>

                    <div className="relative z-10">
                        <Link to="/" className="flex items-center mb-12">
                            <div className="w-10 h-10 bg-white/20 backdrop-blur-md rounded-xl flex items-center justify-center">
                                <CheckCircle2 className="text-white w-6 h-6" />
                            </div>
                            <span className="ml-3 font-bold text-2xl tracking-tight text-white">RAG SaaS</span>
                        </Link>

                        <h2 className="text-4xl font-extrabold mb-8 leading-tight">Start your 14-day free trial.</h2>

                        <ul className="space-y-6">
                            <li className="flex items-start">
                                <CheckCircle2 className="w-6 h-6 mr-4 shrink-0 text-primary-200" />
                                <span className="text-lg">Isolated tenant storage and collections.</span>
                            </li>
                            <li className="flex items-start">
                                <CheckCircle2 className="w-6 h-6 mr-4 shrink-0 text-primary-200" />
                                <span className="text-lg">Real-time vector indexing for fast RAG.</span>
                            </li>
                            <li className="flex items-start">
                                <CheckCircle2 className="w-6 h-6 mr-4 shrink-0 text-primary-200" />
                                <span className="text-lg">Enterprise-grade audit logging & security.</span>
                            </li>
                        </ul>
                    </div>

                    <div className="relative z-10 pt-12 border-t border-white/10">
                        <p className="text-primary-100 text-sm italic italic">
                            "The most robust multi-tenant RAG architecture I've ever implemented. Scaling was seamless."
                        </p>
                        <p className="mt-4 font-bold">— Principal Architect @ AI Venture</p>
                    </div>
                </div>

                {/* Right Side: Form */}
                <div className="p-8 md:p-12">
                    <div className="mb-8 md:hidden text-center">
                        <h2 className="text-2xl font-extrabold text-slate-900 dark:text-white">Start your trial</h2>
                    </div>

                    <form className="space-y-4" onSubmit={handleSubmit}>
                        {error && (
                            <div className="p-4 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-100 dark:border-red-800 flex items-start text-red-600 dark:text-red-400 text-sm">
                                <AlertCircle className="w-5 h-5 mr-3 shrink-0" />
                                <span>{error}</span>
                            </div>
                        )}

                        <div className="space-y-1">
                            <label className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400" htmlFor="client_name">
                                Company Name
                            </label>
                            <div className="relative">
                                <Building2 className="absolute left-3 top-2.5 w-5 h-5 text-slate-400" />
                                <input
                                    id="client_name"
                                    type="text"
                                    value={formData.client_name}
                                    onChange={handleChange}
                                    className="input pl-10 h-11"
                                    placeholder="Acme Corp"
                                    required
                                />
                            </div>
                        </div>

                        <div className="space-y-1">
                            <label className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400" htmlFor="full_name">
                                Full Name
                            </label>
                            <div className="relative">
                                <User className="absolute left-3 top-2.5 w-5 h-5 text-slate-400" />
                                <input
                                    id="full_name"
                                    type="text"
                                    value={formData.full_name}
                                    onChange={handleChange}
                                    className="input pl-10 h-11"
                                    placeholder="John Doe"
                                    required
                                />
                            </div>
                        </div>

                        <div className="space-y-1">
                            <label className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400" htmlFor="email">
                                Work Email
                            </label>
                            <div className="relative">
                                <Mail className="absolute left-3 top-2.5 w-5 h-5 text-slate-400" />
                                <input
                                    id="email"
                                    type="email"
                                    value={formData.email}
                                    onChange={handleChange}
                                    className="input pl-10 h-11"
                                    placeholder="john@acme.com"
                                    required
                                />
                            </div>
                        </div>

                        <div className="space-y-1">
                            <label className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400" htmlFor="password">
                                Password
                            </label>
                            <div className="relative">
                                <Lock className="absolute left-3 top-2.5 w-5 h-5 text-slate-400" />
                                <input
                                    id="password"
                                    type="password"
                                    value={formData.password}
                                    onChange={handleChange}
                                    className="input pl-10 h-11"
                                    placeholder="••••••••"
                                    required
                                />
                            </div>
                            <p className="text-[10px] text-slate-500">Must include 8+ chars with symbols/numbers.</p>
                        </div>

                        <div className="pt-4">
                            <button
                                type="submit"
                                disabled={isSubmitting}
                                className="btn btn-primary w-full h-11 text-base shadow-lg shadow-primary-500/20"
                            >
                                {isSubmitting ? (
                                    <Loader2 className="w-5 h-5 animate-spin mr-2" />
                                ) : (
                                    'Create Trial Account'
                                )}
                            </button>
                        </div>
                    </form>

                    <div className="mt-8 pt-8 border-t border-slate-100 dark:border-slate-800 text-center">
                        <p className="text-sm text-slate-600 dark:text-slate-400">
                            Already have an account?{' '}
                            <Link to="/login" className="font-bold text-primary-600 hover:text-primary-500">
                                Log in instead
                            </Link>
                        </p>
                    </div>
                </div>
            </div>
        </div>
    );
}

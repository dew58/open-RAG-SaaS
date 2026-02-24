import React from 'react';
import { Outlet, Link } from 'react-router-dom';
import { MessageSquare, Menu, X } from 'lucide-react';

export const PublicLayout: React.FC = () => {
    const [isMenuOpen, setIsMenuOpen] = React.useState(false);

    return (
        <div className="min-h-screen flex flex-col bg-white dark:bg-slate-950 transition-colors">
            <header className="h-20 flex items-center justify-between px-6 md:px-12 border-b border-slate-100 dark:border-slate-800 sticky top-0 bg-white/80 dark:bg-slate-950/80 backdrop-blur-md z-50">
                <Link to="/" className="flex items-center group">
                    <div className="w-10 h-10 bg-primary-600 rounded-xl flex items-center justify-center group-hover:bg-primary-700 transition-colors">
                        <MessageSquare className="text-white w-6 h-6" />
                    </div>
                    <span className="ml-3 font-bold text-xl dark:text-white tracking-tight">RAG SaaS</span>
                </Link>

                {/* Desktop Nav */}
                <nav className="hidden md:flex items-center space-x-8">
                    <a href="#features" className="text-sm font-medium text-slate-600 hover:text-primary-600 dark:text-slate-400 dark:hover:text-primary-400 transition-colors">Features</a>
                    <a href="#security" className="text-sm font-medium text-slate-600 hover:text-primary-600 dark:text-slate-400 dark:hover:text-primary-400 transition-colors">Security</a>
                    <a href="#architecture" className="text-sm font-medium text-slate-600 hover:text-primary-600 dark:text-slate-400 dark:hover:text-primary-400 transition-colors">Architecture</a>
                    <div className="w-px h-4 bg-slate-200 dark:bg-slate-800"></div>
                    <Link to="/login" className="text-sm font-medium text-slate-600 hover:text-primary-600 dark:text-slate-400 dark:hover:text-primary-400 transition-colors">Login</Link>
                    <Link to="/register" className="btn btn-primary px-5 py-2.5">
                        Start Free Trial
                    </Link>
                </nav>

                {/* Mobile Toggle */}
                <button className="md:hidden p-2 text-slate-600 dark:text-slate-400" onClick={() => setIsMenuOpen(!isMenuOpen)}>
                    {isMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
                </button>
            </header>

            {/* Mobile Menu */}
            {isMenuOpen && (
                <div className="fixed inset-0 top-20 bg-white dark:bg-slate-950 z-40 md:hidden p-6 animate-in slide-in-from-top duration-300">
                    <nav className="flex flex-col space-y-6">
                        <a href="#features" onClick={() => setIsMenuOpen(false)} className="text-xl font-semibold text-slate-900 dark:text-white border-b border-slate-100 dark:border-slate-800 pb-4">Features</a>
                        <a href="#security" onClick={() => setIsMenuOpen(false)} className="text-xl font-semibold text-slate-900 dark:text-white border-b border-slate-100 dark:border-slate-800 pb-4">Security</a>
                        <a href="#architecture" onClick={() => setIsMenuOpen(false)} className="text-xl font-semibold text-slate-900 dark:text-white border-b border-slate-100 dark:border-slate-800 pb-4">Architecture</a>
                        <Link to="/login" onClick={() => setIsMenuOpen(false)} className="text-xl font-semibold text-slate-900 dark:text-white border-b border-slate-100 dark:border-slate-800 pb-4">Login</Link>
                        <Link to="/register" onClick={() => setIsMenuOpen(false)} className="btn btn-primary text-lg py-4 w-full">
                            Start Free Trial
                        </Link>
                    </nav>
                </div>
            )}

            <main className="flex-1">
                <Outlet />
            </main>

            <footer className="bg-slate-50 dark:bg-slate-900/50 border-t border-slate-100 dark:border-slate-800 py-12 px-6 md:px-12 text-center transition-colors">
                <div className="flex items-center justify-center mb-6">
                    <div className="w-8 h-8 bg-primary-600 rounded-lg flex items-center justify-center">
                        <MessageSquare className="text-white w-5 h-5" />
                    </div>
                    <span className="ml-2 font-bold text-lg dark:text-white">RAG SaaS</span>
                </div>
                <p className="text-sm text-slate-500 dark:text-slate-400 max-w-sm mx-auto mb-8">
                    Enterprise-grade Retrieval-Augmented Generation for modern multi-tenant platforms.
                </p>
                <div className="flex justify-center space-x-6 mb-8">
                    <a href="#" className="text-sm text-slate-400 hover:text-primary-500">Privacy Policy</a>
                    <a href="#" className="text-sm text-slate-400 hover:text-primary-500">Terms of Service</a>
                    <a href="#" className="text-sm text-slate-400 hover:text-primary-500">Contact</a>
                </div>
                <p className="text-xs text-slate-400 dark:text-slate-600">
                    &copy; {new Date().getFullYear()} RAG SaaS. All rights reserved.
                </p>
            </footer>
        </div>
    );
};

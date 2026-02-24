import React from 'react';
import { Link } from 'react-router-dom';
import {
    Zap,
    Shield,
    Layers,
    MessageSquare,
    Database,
    Lock,
    ArrowRight,
    CheckCircle2,
    Cpu,
    Globe
} from 'lucide-react';

export default function LandingPage() {
    return (
        <div className="flex flex-col">
            {/* Hero Section */}
            <section className="relative pt-20 pb-24 md:pt-32 md:pb-32 overflow-hidden">
                {/* Background Gradients */}
                <div className="absolute top-0 left-1/2 -translate-x-1/2 w-full h-full -z-10 opacity-30 pointer-events-none">
                    <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-primary-400 blur-[120px] rounded-full"></div>
                    <div className="absolute bottom-[-10%] right-[-10%] w-[30%] h-[30%] bg-blue-400 blur-[100px] rounded-full"></div>
                </div>

                <div className="container mx-auto px-6 text-center">
                    <div className="inline-flex items-center px-4 py-1.5 rounded-full bg-primary-50 dark:bg-primary-900/20 text-primary-600 dark:text-primary-400 text-sm font-semibold mb-8 border border-primary-100 dark:border-primary-800">
                        <Zap className="w-4 h-4 mr-2" />
                        <span>v1.0 is now live</span>
                    </div>

                    <h1 className="text-5xl md:text-7xl font-extrabold text-slate-900 dark:text-white mb-8 tracking-tight leading-tight">
                        Production-Grade <br />
                        <span className="text-transparent bg-clip-text bg-gradient-to-r from-primary-600 to-blue-500">Multi-Tenant RAG</span>
                    </h1>

                    <p className="text-lg md:text-xl text-slate-600 dark:text-slate-400 max-w-2xl mx-auto mb-12 leading-relaxed">
                        Empower your SaaS with secure, isolated, and scalable Retrieval-Augmented Generation.
                        Upload documents, index in real-time, and query with enterprise-level security.
                    </p>

                    <div className="flex flex-col sm:flex-row items-center justify-center space-y-4 sm:space-y-0 sm:space-x-4">
                        <Link to="/register" className="btn btn-primary px-8 py-4 text-lg w-full sm:w-auto shadow-xl shadow-primary-500/20 group">
                            Start Free Trial
                            <ArrowRight className="ml-2 w-5 h-5 group-hover:translate-x-1 transition-transform" />
                        </Link>
                        <a href="#features" className="btn btn-secondary px-8 py-4 text-lg w-full sm:w-auto">
                            View Features
                        </a>
                    </div>

                    {/* Social Proof / Trusted By */}
                    <div className="mt-20 pt-10 border-t border-slate-100 dark:border-slate-800">
                        <p className="text-sm font-medium text-slate-400 uppercase tracking-widest mb-8">Built on Enterprise Stack</p>
                        <div className="flex flex-wrap justify-center items-center gap-8 md:gap-16 opacity-50 grayscale hover:grayscale-0 transition-all duration-500">
                            <span className="text-xl font-bold text-slate-600 dark:text-slate-300">FastAPI</span>
                            <span className="text-xl font-bold text-slate-600 dark:text-slate-300">PostgreSQL</span>
                            <span className="text-xl font-bold text-slate-600 dark:text-slate-300">ChromaDB</span>
                            <span className="text-xl font-bold text-slate-600 dark:text-slate-300">Redis</span>
                            <span className="text-xl font-bold text-slate-600 dark:text-slate-300">Docker</span>
                            <span className="text-xl font-bold text-slate-600 dark:text-slate-300">Gemini</span>
                        </div>
                    </div>
                </div>
            </section>

            {/* Features Section */}
            <section id="features" className="py-24 bg-slate-50 dark:bg-slate-900/30">
                <div className="container mx-auto px-6">
                    <div className="text-center max-w-3xl mx-auto mb-20">
                        <h2 className="text-3xl md:text-4xl font-bold text-slate-900 dark:text-white mb-6">Designed for Modern SaaS</h2>
                        <p className="text-lg text-slate-600 dark:text-slate-400">Everything you need to build a professional AI-native platform without worrying about infrastructure.</p>
                    </div>

                    <div className="grid md:grid-cols-3 gap-8">
                        <FeatureCard
                            icon={<Shield className="w-8 h-8 text-primary-600" />}
                            title="Tenant Isolation"
                            description="Each client gets a dedicated database scope and isolated ChromaDB collections. Data leakage is mathematically impossible."
                        />
                        <FeatureCard
                            icon={<Zap className="w-8 h-8 text-amber-500" />}
                            title="Hyper-Fast RAG"
                            description="Optimized retrieval pipeline with recursive character splitting and multi-dimensional indexing."
                        />
                        <FeatureCard
                            icon={<Database className="w-8 h-8 text-blue-500" />}
                            title="Hybrid Storage"
                            description="Combine PostgreSQL's reliability for metadata with ChromaDB's speed for vector embeddings."
                        />
                        <FeatureCard
                            icon={<Lock className="w-8 h-8 text-emerald-500" />}
                            title="Audit Logging"
                            description="Every query and file upload is logged with tenant attribution for full compliance and visibility."
                        />
                        <FeatureCard
                            icon={<Globe className="w-8 h-8 text-indigo-500" />}
                            title="Multi-Cloud Ready"
                            description="Deploy anywhere with Docker. Native support for OpenAI, Gemini, and local LLMs via Ollama."
                        />
                        <FeatureCard
                            icon={<Layers className="w-8 h-8 text-purple-500" />}
                            title="Scalable Architecture"
                            description="Built to scale horizontally. Redis-backed rate limiting and async task processing (Celery/Redis ready)."
                        />
                    </div>
                </div>
            </section>

            {/* Security Architecture Section */}
            <section id="security" className="py-24">
                <div className="container mx-auto px-6">
                    <div className="flex flex-col lg:flex-row items-center gap-16">
                        <div className="lg:w-1/2">
                            <h2 className="text-3xl md:text-4xl font-bold text-slate-900 dark:text-white mb-8">Enterprise-Grade Security</h2>
                            <ul className="space-y-6">
                                <SecurityItem
                                    title="JWT Auth with Refresh Strategy"
                                    description="Short-lived access tokens combined with secure, rotation-capable refresh tokens."
                                />
                                <SecurityItem
                                    title="Strict Data Isolation"
                                    description="Row-level security patterns enforced at the API and database relationship layers."
                                />
                                <SecurityItem
                                    title="Security-Hardened Headers"
                                    description="Pre-configured HSTS, CSP, and X-Frame-Options at the Nginx layer."
                                />
                                <SecurityItem
                                    title="Rate Limiting"
                                    description="Sliding window rate limiting per tenant to prevent API abuse and cost overrun."
                                />
                            </ul>
                        </div>
                        <div className="lg:w-1/2 w-full">
                            <div className="card p-4 md:p-8 bg-slate-950 border-slate-800 text-slate-300 font-mono text-sm shadow-2xl overflow-hidden relative group">
                                <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity">
                                    <Shield className="w-32 h-32" />
                                </div>
                                <div className="space-y-2 relative">
                                    <p className="text-emerald-500"># Security Audit Log</p>
                                    <p className="text-slate-500">[{new Date().toISOString()}]</p>
                                    <p><span className="text-primary-400">ACTION:</span> REGISTER_TENANT</p>
                                    <p><span className="text-primary-400">CLIENT:</span> AcmeCorp</p>
                                    <p><span className="text-primary-400">ISOLATION:</span> Collection "client_1a2b3c" created</p>
                                    <p><span className="text-primary-400">ACL:</span> JWT signed with client_id scope</p>
                                    <p className="text-emerald-500 mt-4"># Request Protected</p>
                                    <p><span className="text-primary-400">GET</span> /api/v1/documents</p>
                                    <p><span className="text-blue-400">WHERE</span> client_id == jwt.client_id</p>
                                    <p className="text-emerald-400">✓ Security validation passed</p>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </section>

            {/* CTA Section */}
            <section className="py-20">
                <div className="container mx-auto px-6">
                    <div className="bg-primary-600 rounded-3xl p-8 md:p-16 text-center text-white shadow-2xl shadow-primary-500/30 overflow-hidden relative">
                        <div className="absolute top-0 right-0 -translate-y-1/2 translate-x-1/4 w-96 h-96 bg-primary-500 rounded-full blur-[80px] opacity-50"></div>
                        <div className="relative z-10">
                            <h2 className="text-3xl md:text-5xl font-bold mb-8 tracking-tight">Ready to build the future?</h2>
                            <p className="text-lg md:text-xl text-primary-100 max-w-2xl mx-auto mb-12">
                                Join hundreds of developers building powerful AI native applications with RAG SaaS.
                                Set up your tenant in under 60 seconds.
                            </p>
                            <div className="flex flex-col sm:flex-row items-center justify-center space-y-4 sm:space-y-0 sm:space-x-4">
                                <Link to="/register" className="btn bg-white text-primary-600 hover:bg-slate-50 px-10 py-4 text-xl font-bold shadow-lg w-full sm:w-auto">
                                    Get Started for Free
                                </Link>
                                <Link to="/login" className="btn bg-primary-700 text-white hover:bg-primary-800 px-10 py-4 text-xl font-bold w-full sm:w-auto">
                                    Sign In
                                </Link>
                            </div>
                        </div>
                    </div>
                </div>
            </section>
        </div>
    );
}

function FeatureCard({ icon, title, description }: { icon: React.ReactNode, title: string, description: string }) {
    return (
        <div className="card p-8 hover:shadow-xl hover:-translate-y-1 transition-all duration-300">
            <div className="mb-6">{icon}</div>
            <h3 className="text-xl font-bold text-slate-900 dark:text-white mb-4">{title}</h3>
            <p className="text-slate-600 dark:text-slate-400 leading-relaxed">{description}</p>
        </div>
    );
}

function SecurityItem({ title, description }: { title: string, description: string }) {
    return (
        <div className="flex items-start">
            <div className="mt-1 flex-shrink-0">
                <div className="w-6 h-6 rounded-full bg-emerald-100 dark:bg-emerald-900/30 flex items-center justify-center">
                    <CheckCircle2 className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
                </div>
            </div>
            <div className="ml-4">
                <h4 className="text-lg font-bold text-slate-900 dark:text-white mb-1">{title}</h4>
                <p className="text-slate-600 dark:text-slate-400">{description}</p>
            </div>
        </div>
    );
}

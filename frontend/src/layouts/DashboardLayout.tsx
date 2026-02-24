import React, { useState } from 'react';
import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import {
    LayoutDashboard,
    MessageSquare,
    FileText,
    History,
    Key,
    Settings,
    LogOut,
    Menu,
    X,
    Bell,
    Moon,
    Sun,
    User as UserIcon,
    Search
} from 'lucide-react';
import { useAuth } from '../providers/AuthProvider';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

function cn(...inputs: ClassValue[]) {
    return twMerge(clsx(inputs));
}

export const DashboardLayout: React.FC = () => {
    const { user, logout } = useAuth();
    const [isSidebarOpen, setIsSidebarOpen] = useState(true);
    const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
    const [darkMode, setDarkMode] = useState(false);
    const navigate = useNavigate();

    const toggleDarkMode = () => {
        setDarkMode(!darkMode);
        document.documentElement.classList.toggle('dark');
    };

    const menuItems = [
        { title: 'Overview', icon: LayoutDashboard, href: '/dashboard' },
        { title: 'RAG Chat', icon: MessageSquare, href: '/dashboard/chat' },
        { title: 'Documents', icon: FileText, href: '/dashboard/documents' },
        { title: 'Query History', icon: History, href: '/dashboard/history' },
        { title: 'API Keys', icon: Key, href: '/dashboard/api-keys' },
        { title: 'Settings', icon: Settings, href: '/dashboard/settings' },
    ];

    const handleLogout = () => {
        logout();
        navigate('/login');
    };

    return (
        <div className={cn("min-h-screen flex bg-slate-50 dark:bg-slate-950 transition-colors")}>
            {/* Desktop Sidebar */}
            <aside
                className={cn(
                    "hidden md:flex flex-col bg-white dark:bg-slate-900 border-r border-slate-200 dark:border-slate-800 transition-all duration-300 z-30",
                    isSidebarOpen ? "w-64" : "w-20"
                )}
            >
                <div className="h-16 flex items-center px-6 border-b border-slate-100 dark:border-slate-800">
                    <div className="w-8 h-8 bg-primary-600 rounded-lg flex items-center justify-center shrink-0">
                        <span className="text-white font-bold text-xl">R</span>
                    </div>
                    {isSidebarOpen && <span className="ml-3 font-bold text-lg dark:text-white truncate">RAG SaaS</span>}
                </div>

                <nav className="flex-1 py-6 px-3 space-y-1">
                    {menuItems.map((item) => (
                        <NavLink
                            key={item.href}
                            to={item.href}
                            end={item.href === '/dashboard'}
                            className={({ isActive }) => cn(
                                "flex items-center px-3 py-2.5 rounded-lg transition-all group",
                                isActive
                                    ? "bg-primary-50 text-primary-600 dark:bg-primary-900/20 dark:text-primary-400"
                                    : "text-slate-600 hover:bg-slate-50 dark:text-slate-400 dark:hover:bg-slate-800"
                            )}
                        >
                            <item.icon className={cn("w-5 h-5 shrink-0", isSidebarOpen ? "mr-3" : "mx-auto")} />
                            {isSidebarOpen && <span className="font-medium">{item.title}</span>}
                        </NavLink>
                    ))}
                </nav>

                <div className="p-4 border-t border-slate-100 dark:border-slate-800">
                    <button
                        onClick={handleLogout}
                        className={cn(
                            "w-full flex items-center px-3 py-2.5 text-slate-600 hover:bg-red-50 hover:text-red-600 rounded-lg transition-all dark:text-slate-400 dark:hover:bg-red-900/10",
                            !isSidebarOpen && "justify-center"
                        )}
                    >
                        <LogOut className="w-5 h-5 shrink-0" />
                        {isSidebarOpen && <span className="ml-3 font-medium">Logout</span>}
                    </button>
                </div>
            </aside>

            {/* Main Content Area */}
            <div className="flex-1 flex flex-col min-w-0">
                {/* Header */}
                <header className="h-16 flex items-center justify-between px-4 md:px-8 bg-white dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800 z-20 sticky top-0">
                    <div className="flex items-center">
                        <button
                            onClick={() => setIsMobileMenuOpen(true)}
                            className="md:hidden p-2 -ml-2 text-slate-600 dark:text-slate-400"
                        >
                            <Menu className="w-6 h-6" />
                        </button>
                        <button
                            onClick={() => setIsSidebarOpen(!isSidebarOpen)}
                            className="hidden md:p-2 md:-ml-2 text-slate-600 dark:text-slate-400 md:block"
                        >
                            <Menu className="w-5 h-5" />
                        </button>

                        <div className="ml-4 md:ml-0 flex items-center">
                            <span className="hidden sm:inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-slate-100 text-slate-800 dark:bg-slate-800 dark:text-slate-200 mr-3">
                                Development
                            </span>
                        </div>
                    </div>

                    <div className="flex items-center space-x-2 md:space-x-4">
                        <div className="hidden lg:flex items-center relative mr-2">
                            <Search className="w-4 h-4 absolute left-3 text-slate-400" />
                            <input
                                type="text"
                                placeholder="Search..."
                                className="pl-10 pr-4 py-1.5 bg-slate-50 border-none rounded-lg text-sm w-64 focus:ring-2 focus:ring-primary-500 dark:bg-slate-800 dark:text-slate-200"
                            />
                        </div>

                        <button
                            onClick={toggleDarkMode}
                            className="p-2 text-slate-600 hover:bg-slate-100 rounded-lg transition-colors dark:text-slate-400 dark:hover:bg-slate-800"
                        >
                            {darkMode ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
                        </button>

                        <button className="p-2 text-slate-600 hover:bg-slate-100 rounded-lg transition-colors relative dark:text-slate-400 dark:hover:bg-slate-800">
                            <Bell className="w-5 h-5" />
                            <span className="absolute top-2 right-2 w-2 h-2 bg-red-500 rounded-full"></span>
                        </button>

                        <div className="h-8 w-px bg-slate-200 dark:bg-slate-800 mx-2"></div>

                        <div className="flex items-center">
                            <div className="flex flex-col items-end mr-3 hidden sm:flex">
                                <span className="text-sm font-semibold dark:text-white">{user?.full_name}</span>
                                <span className="text-xs text-slate-500 capitalize">{user?.role}</span>
                            </div>
                            <div className="w-10 h-10 rounded-full bg-primary-100 border border-primary-200 flex items-center justify-center dark:bg-primary-900/30 dark:border-primary-800">
                                <UserIcon className="w-5 h-5 text-primary-600 dark:text-primary-400" />
                            </div>
                        </div>
                    </div>
                </header>

                {/* Dashboard Content */}
                <main className="flex-1 p-4 md:p-8 overflow-y-auto">
                    <Outlet />
                </main>
            </div>

            {/* Mobile Sidebar Overlay */}
            {isMobileMenuOpen && (
                <div
                    className="fixed inset-0 bg-slate-900/50 backdrop-blur-sm z-40 md:hidden"
                    onClick={() => setIsMobileMenuOpen(false)}
                >
                    <div
                        className="w-72 h-full bg-white dark:bg-slate-900 p-6 flex flex-col"
                        onClick={e => e.stopPropagation()}
                    >
                        <div className="flex items-center justify-between mb-8">
                            <div className="flex items-center">
                                <div className="w-8 h-8 bg-primary-600 rounded-lg flex items-center justify-center">
                                    <span className="text-white font-bold text-xl">R</span>
                                </div>
                                <span className="ml-3 font-bold text-lg dark:text-white">RAG SaaS</span>
                            </div>
                            <button onClick={() => setIsMobileMenuOpen(false)}>
                                <X className="w-6 h-6 dark:text-slate-400" />
                            </button>
                        </div>

                        <nav className="flex-1 space-y-2">
                            {menuItems.map((item) => (
                                <NavLink
                                    key={item.href}
                                    to={item.href}
                                    end={item.href === '/dashboard'}
                                    onClick={() => setIsMobileMenuOpen(false)}
                                    className={({ isActive }) => cn(
                                        "flex items-center px-4 py-3 rounded-lg transition-all",
                                        isActive
                                            ? "bg-primary-50 text-primary-600 dark:bg-primary-900/20 dark:text-primary-400"
                                            : "text-slate-600 hover:bg-slate-50 dark:text-slate-400 dark:hover:bg-slate-800"
                                    )}
                                >
                                    <item.icon className="w-6 h-6 mr-4" />
                                    <span className="font-medium text-lg">{item.title}</span>
                                </NavLink>
                            ))}
                        </nav>

                        <div className="pt-6 border-t border-slate-100 dark:border-slate-800">
                            <button
                                onClick={handleLogout}
                                className="w-full flex items-center px-4 py-3 text-slate-600 hover:bg-red-50 hover:text-red-600 rounded-lg transition-all dark:text-slate-400 dark:hover:bg-red-900/10"
                            >
                                <LogOut className="w-6 h-6 mr-4" />
                                <span className="font-medium text-lg">Logout</span>
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

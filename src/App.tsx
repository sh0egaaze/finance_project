import { useState, useEffect, useCallback } from 'react';
import Sidebar from './components/Sidebar';
import Header from './components/Header';
import { Dashboard } from './components/Dashboard';
import Transactions from './components/Transactions';
import Analytics from './components/Analytics';
import Reminders from './components/Reminders';
import CurrencyRates from './components/CurrencyRates';
import Predictions from './components/Predictions';
import SuspiciousTransactions from './components/SuspiciousTransactions';
import SavingTips from './components/SavingTips';
import Settings from './components/Settings';
import AddTransactionModal from './components/AddTransactionModal';
import AuthPage from './components/AuthPage';
import AdminPanel from './components/AdminPanel';
import { api, User, Category } from './api';

export default function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [user, setUser] = useState<User | null>(null);
  const [activeTab, setActiveTab] = useState('dashboard');
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [categories, setCategories] = useState<Category[]>([]);
  const [refreshKey, setRefreshKey] = useState(0);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  useEffect(() => {
    const theme = localStorage.getItem('theme') || 'system';
    const root = document.documentElement;
    if (theme === 'dark' || (theme === 'system' && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
      root.classList.add('dark');
    } else {
      root.classList.remove('dark');
    }
  }, []);

  // Check auth on mount
  useEffect(() => {
    const checkAuth = async () => {
      const token = localStorage.getItem('token');
      if (token) {
        try {
          const profile = await api.getMe();
          setUser(profile);
          setIsAuthenticated(true);
          
          // Load categories
          const cats = await api.getCategories();
          setCategories(cats);
        } catch {
          localStorage.removeItem('token');
          localStorage.removeItem('user');
        }
      }
      setIsLoading(false);
    };
    checkAuth();
  }, []);

  const handleLogin = async (email: string, password: string) => {
    const result = await api.login(email, password);
    localStorage.setItem('token', result.access_token);
    const profile = await api.getMe();
    localStorage.setItem('user', JSON.stringify(profile));
    setUser(profile);
    setIsAuthenticated(true);
    
    // Load categories
    const cats = await api.getCategories();
    setCategories(cats);
  };

  const handleRegister = async (email: string, password: string, fullName: string) => {
    await api.register(email, password, fullName);
    await handleLogin(email, password);
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    setIsAuthenticated(false);
    setUser(null);
    setCategories([]);
  };

  const refreshData = useCallback(() => {
      setRefreshKey(prev => prev + 1);
  }, []);

  const handleAddTransaction = async (data: {
    amount: number;
    description: string;
    category_id: number | null;
    type: 'income' | 'expense';
    source: string;
    date: string;
  }) => {
    await api.createTransaction({
      amount: Math.abs(data.amount),       
      is_income: data.type === 'income',   
      description: data.description,
      category_id: data.category_id || undefined,
      source: data.source,
      transaction_date: data.date,
    });
    setIsAddModalOpen(false);
    refreshData();
  };

  const handleTabChange = (tab: string) => {
    setActiveTab(tab);
    setIsSidebarOpen(false);
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center dark:bg-gray-900">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-500 dark:text-gray-400">Загрузка...</p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <AuthPage onLogin={handleLogin} onRegister={handleRegister} />;
  }

  const renderContent = () => {
    if (!user) return null;

    switch (activeTab) {
      case 'dashboard':
        return <Dashboard key={refreshKey} user={user} onTabChange={handleTabChange} />;
      case 'transactions':
        return <Transactions key={refreshKey} categories={categories} />;
      case 'analytics':
        return <Analytics key={refreshKey} />;
      case 'reminders':
        return (
          <div key={refreshKey}>
            <Reminders user={user} />
          </div>
        );
      case 'currency':
        return <CurrencyRates />;
      case 'predictions':
        return <Predictions key={refreshKey} />;
      case 'suspicious':
        return <SuspiciousTransactions key={refreshKey} />;
      case 'tips':
        return <SavingTips key={refreshKey} />;
      case 'admin':
        return <AdminPanel key={refreshKey} />;
      case 'settings':
        return <Settings user={user} onLogout={handleLogout} onUserUpdate={setUser} />;
      default:
        return null;
    }
  };

  return (
    <div className="h-screen bg-gray-50 dark:bg-gray-900 flex overflow-hidden">
      <Sidebar 
        activeTab={activeTab} 
        onTabChange={handleTabChange} 
        user={user}
        isOpen={isSidebarOpen}
        onClose={() => setIsSidebarOpen(false)}
      />
      
      <div className="flex-1 flex flex-col min-w-0">
        <Header 
          user={user} 
          onLogout={handleLogout}
          onAddTransaction={() => setIsAddModalOpen(true)}
          onMenuToggle={() => setIsSidebarOpen(!isSidebarOpen)}
        />
        
        <main className="flex-1 p-3 sm:p-4 lg:p-6 overflow-y-auto">
          {renderContent()}
        </main>
      </div>

      {isAddModalOpen && (
        <AddTransactionModal
          categories={categories}
          onSubmit={handleAddTransaction}
          onClose={() => setIsAddModalOpen(false)}
        />
      )}
    </div>
  );
}

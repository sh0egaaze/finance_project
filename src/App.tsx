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
import { api, User, Category } from './api';

export default function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [user, setUser] = useState<User | null>(null);
  const [activeTab, setActiveTab] = useState('dashboard');
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [categories, setCategories] = useState<Category[]>([]);

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
    // Trigger refresh in child components by changing a key
    setActiveTab(prev => prev);
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

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-500">Загрузка...</p>
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
        return <Dashboard user={user} onTabChange={setActiveTab} />;
      case 'transactions':
        return <Transactions categories={categories} />;
      case 'analytics':
        return <Analytics />;
      case 'reminders':
        return <Reminders />;
      case 'currency':
        return <CurrencyRates />;
      case 'predictions':
        return <Predictions />;
      case 'suspicious':
        return <SuspiciousTransactions />;
      case 'tips':
        return <SavingTips />;
      case 'settings':
        return <Settings user={user} onLogout={handleLogout} onUserUpdate={setUser} />;
      default:
        return null;
    }
  };

  return (
    <div className="min-h-screen bg-gray-100 flex">
      <Sidebar activeTab={activeTab} onTabChange={setActiveTab} />
      
      <div className="flex-1 flex flex-col">
        <Header 
          user={user} 
          onLogout={handleLogout}
          onAddTransaction={() => setIsAddModalOpen(true)}
        />
        
        <main className="flex-1 p-6 overflow-auto">
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

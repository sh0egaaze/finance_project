import {
  LayoutDashboard, Receipt, PieChart, Bell, TrendingUp,
  AlertTriangle, Lightbulb, Settings, DollarSign
} from 'lucide-react';

interface SidebarProps {
  activeTab: string;
  onTabChange: (tab: string) => void;
}

const menuItems = [
  { id: 'dashboard', icon: LayoutDashboard, label: 'Обзор' },
  { id: 'transactions', icon: Receipt, label: 'Транзакции' },
  { id: 'analytics', icon: PieChart, label: 'Аналитика' },
  { id: 'predictions', icon: TrendingUp, label: 'Прогнозы' },
  { id: 'reminders', icon: Bell, label: 'Напоминания' },
  { id: 'currency', icon: DollarSign, label: 'Курсы валют' },
  { id: 'suspicious', icon: AlertTriangle, label: 'Подозрительные' },
  { id: 'tips', icon: Lightbulb, label: 'Советы' },
  { id: 'settings', icon: Settings, label: 'Настройки' },
];

export default function Sidebar({ activeTab, onTabChange }: SidebarProps) {
  return (
    <aside className="w-64 bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 flex flex-col h-screen sticky top-0 shrink-0">
      {/* Логотип */}
      <div className="px-5 py-[13px] border-b border-gray-200 dark:border-gray-700">
        <div className="text-center">
          <h1 className="text-lg font-extrabold tracking-tight text-transparent bg-clip-text bg-gradient-to-r from-blue-600 to-indigo-500 dark:from-blue-400 dark:to-indigo-400">
            FinanceApp
          </h1>
          <p className="text-xs text-gray-400 dark:text-gray-500 tracking-wide uppercase">
            Управление финансами
          </p>
        </div>
      </div>
      
      {/* Навигация */}
      <nav className="flex-1 p-3 space-y-1 overflow-y-auto">
        {menuItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => onTabChange(item.id)}
              className={`w-full flex items-center gap-3 px-4 py-2.5 rounded-xl transition-all duration-200 text-sm font-medium ${
                isActive
                  ? 'bg-blue-50 text-blue-600 shadow-sm dark:bg-blue-900/30 dark:text-blue-400'
                  : 'text-gray-500 hover:bg-gray-50 hover:text-gray-700 dark:text-gray-400 dark:hover:bg-gray-700 dark:hover:text-gray-300'
              }`}
            >
              <Icon className={`w-5 h-5 ${isActive ? 'text-blue-500 dark:text-blue-400' : 'text-gray-400 dark:text-gray-500'}`} />
              {item.label}
            </button>
          );
        })}
      </nav>

      {/* Версия */}
      <div className="p-4 border-t border-gray-100 dark:border-gray-700">
        <p className="text-xs text-gray-300 text-center dark:text-gray-600">v1.0.0</p>
      </div>
    </aside>
  );
}
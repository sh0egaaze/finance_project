import { 
  LayoutDashboard, 
  Receipt, 
  PieChart, 
  Bell, 
  TrendingUp,
  AlertTriangle,
  Lightbulb,
  Settings,
  DollarSign
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
    <aside className="w-64 bg-white shadow-lg min-h-screen">
      <div className="p-6 border-b">
        <h1 className="text-2xl font-bold text-blue-600 flex items-center gap-2">
          💰 FinanceApp
        </h1>
        <p className="text-sm text-gray-500 mt-1">Управление финансами</p>
      </div>

      <nav className="p-4">
        <ul className="space-y-2">
          {menuItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            
            return (
              <li key={item.id}>
                <button
                  onClick={() => onTabChange(item.id)}
                  className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${
                    isActive
                      ? 'bg-blue-50 text-blue-600'
                      : 'text-gray-600 hover:bg-gray-50'
                  }`}
                >
                  <Icon className="w-5 h-5" />
                  <span className="font-medium">{item.label}</span>
                </button>
              </li>
            );
          })}
        </ul>
      </nav>
    </aside>
  );
}

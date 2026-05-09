import React, { useState, useEffect } from 'react';
import {
  TrendingUp, TrendingDown, Wallet, PiggyBank, RefreshCw,
  AlertTriangle, Bell, ArrowRight, Loader2
} from 'lucide-react';
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, PieChart, Pie, Cell
} from 'recharts';
import { api, DashboardData, User } from '../api';
import { SmartInput } from './SmartInput';

interface DashboardProps {
  user: User;
  onTabChange?: (tab: string) => void;
}

export const Dashboard: React.FC<DashboardProps> = ({ user, onTabChange }) => {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showIncome, setShowIncome] = useState(false);

  const loadDashboard = async () => {
    try {
      setLoading(true);
      setError(null);
      const dashboardData = await api.getDashboard();
      setData(dashboardData);
    } catch (err) {
      setError('Не удалось загрузить данные');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDashboard();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-xl p-6 text-center">
        <AlertTriangle className="w-12 h-12 text-red-500 mx-auto mb-4" />
        <p className="text-red-700 mb-4">{error || 'Ошибка загрузки'}</p>
        <button
          onClick={loadDashboard}
          className="px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600"
        >
          Попробовать снова
        </button>
      </div>
    );
  }

  const { stats, recent_transactions, spending_by_category, monthly_trend, upcoming_reminders, suspicious_transactions } = data;

  // Карточки статистики
  const statCards = [
    {
      title: 'Баланс',
      value: Number(stats.total_balance || 0),
      icon: Wallet,
      color: 'blue',
      format: 'currency',
    },
    {
      title: 'Доходы',
      value: Number(stats.total_income || 0),
      icon: TrendingUp,
      color: 'green',
      format: 'currency',
    },
    {
      title: 'Расходы',
      value: Number(stats.total_expense || 0),
      icon: TrendingDown,
      color: 'red',
      format: 'currency',
    },
    {
      title: 'Накопления',
      value: Number(stats.savings_rate || 0),
      icon: PiggyBank,
      color: 'purple',
      format: 'percent',
    },
  ];

  const formatValue = (value: number, format: string) => {
    if (format === 'currency') {
      return `${value.toLocaleString('ru-RU')} ₽`;
    }
    if (format === 'percent') {
      return `${value.toFixed(1)}%`;
    }
    return value.toString();
  };

  const colorClasses: Record<string, { bg: string; text: string; icon: string }> = {
    blue: { bg: 'bg-blue-50', text: 'text-blue-600', icon: 'text-blue-500' },
    green: { bg: 'bg-green-50', text: 'text-green-600', icon: 'text-green-500' },
    red: { bg: 'bg-red-50', text: 'text-red-600', icon: 'text-red-500' },
    purple: { bg: 'bg-purple-50', text: 'text-purple-600', icon: 'text-purple-500' },
  };

  return (
    <div className="space-y-6">
      {/* Приветствие */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">
            Привет, {user.full_name || 'Пользователь'}! 👋
          </h1>
          <p className="text-gray-500">Вот что происходит с вашими финансами</p>
        </div>
        <button
          onClick={loadDashboard}
          className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
          title="Обновить"
        >
          <RefreshCw className="w-5 h-5 text-gray-500" />
        </button>
      </div>

      {/* Умный ввод */}
      <SmartInput onTransactionAdded={loadDashboard} />

      {/* Карточки статистики */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {statCards.map((card) => {
          const Icon = card.icon;
          const colors = colorClasses[card.color];
          
          return (
            <div key={card.title} className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
              <div className="flex items-center justify-between mb-3">
                <span className="text-sm font-medium text-gray-500">{card.title}</span>
                <div className={`p-2 rounded-lg ${colors.bg}`}>
                  <Icon className={`w-5 h-5 ${colors.icon}`} />
                </div>
              </div>
              <div className={`text-2xl font-bold ${colors.text}`}>
                {formatValue(card.value, card.format)}
              </div>
            </div>
          );
        })}
      </div>

      {/* Графики */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Тренд */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Динамика</h3>
          {monthly_trend && monthly_trend.length > 0 ? (
            <ResponsiveContainer width="100%" height={250}>
              <AreaChart data={monthly_trend}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis
                  dataKey="date"
                  tick={{ fontSize: 12 }}
                  tickFormatter={(value) => {
                    const date = new Date(value);
                    return `${date.getDate()}.${date.getMonth() + 1}`;
                  }}
                />
                <YAxis tick={{ fontSize: 12 }} />
                <Tooltip
                  formatter={(value) => [`${Number(value).toLocaleString('ru-RU')} ₽`]}
                  labelFormatter={(label) => new Date(label).toLocaleDateString('ru-RU')}
                />
                <Area
                  type="monotone"
                  dataKey="income"
                  name="Доходы"
                  stroke="#22c55e"
                  fill="#22c55e"
                  fillOpacity={0.2}
                />
                <Area
                  type="monotone"
                  dataKey="expense"
                  name="Расходы"
                  stroke="#ef4444"
                  fill="#ef4444"
                  fillOpacity={0.2}
                />
              </AreaChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-[250px] flex items-center justify-center text-gray-400">
              Нет данных для отображения
            </div>
          )}
        </div>
      </div>

      {/* Категории */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-gray-900">
            {showIncome ? 'Доходы по категориям' : 'Расходы по категориям'}
          </h3>
          <button
            onClick={() => setShowIncome(!showIncome)}
            className="p-1 hover:bg-gray-100 rounded-lg transition-colors"
            title={showIncome ? 'Показать расходы' : 'Показать доходы'}
          >
            <ArrowRight className={`w-5 h-5 transition-colors ${showIncome ? 'text-green-500' : 'text-red-500'}`} />
          </button>
        </div>
        {(() => {
          const categoryData = showIncome 
            ? (data.income_by_category || []) 
            : (spending_by_category || []);
          
          return categoryData.length > 0 ? (
            <div className="flex items-center gap-4">
              <ResponsiveContainer width="50%" height={200}>
                <PieChart>
                  <Pie
                    data={categoryData}
                    dataKey="amount"
                    nameKey="name"
                    cx="50%"
                    cy="50%"
                    innerRadius={50}
                    outerRadius={80}
                  >
                    {categoryData.map((entry: any, index: number) => (
                      <Cell key={index} fill={entry.color || (showIncome ? '#22c55e' : '#6B7280')} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(value: any) => [`${Number(value).toLocaleString('ru-RU')} ₽`]} />
                </PieChart>
              </ResponsiveContainer>
              <div className="flex-1 space-y-2">
                {categoryData.slice(0, 5).map((cat: any) => (
                  <div key={cat.category || cat.name} className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <div
                        className="w-3 h-3 rounded-full"
                        style={{ backgroundColor: cat.color || (showIncome ? '#22c55e' : '#6B7280') }}
                      />
                      <span className="text-sm text-gray-600">{cat.name}</span>
                    </div>
                    <span className="text-sm font-medium">
                      {cat.amount.toLocaleString('ru-RU')} ₽
                    </span>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="h-[200px] flex items-center justify-center text-gray-400">
              {showIncome ? 'Нет доходов' : 'Нет расходов'}
            </div>
          );
        })()}
      </div>  

      {/* Нижняя секция */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Последние транзакции */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-gray-900">Последние операции</h3>
            <button
              onClick={() => onTabChange?.('transactions')}
              className="p-1 hover:bg-gray-100 rounded-lg transition-colors"
              title="Все транзакции"
            >
              <ArrowRight className="w-5 h-5 text-gray-400 hover:text-blue-500" />
            </button>
          </div>
          <div className="space-y-3">
            {recent_transactions && recent_transactions.length > 0 ? (
              recent_transactions.slice(0, 5).map((tx) => (
                <div key={tx.id} className="flex items-center justify-between py-2 border-b last:border-0">
                  <div>
                    <p className="text-sm font-medium text-gray-900">
                      {tx.description || 'Без описания'}
                    </p>
                    <p className="text-xs text-gray-500">
                      {new Date(tx.transaction_date).toLocaleDateString('ru-RU')}
                    </p>
                  </div>
                  <span className={`font-medium ${Number(tx.amount) >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                    {Number(tx.amount) >= 0 ? '+' : ''}{Number(tx.amount).toLocaleString('ru-RU')} ₽
                  </span>
                </div>
              ))
            ) : (
              <p className="text-gray-400 text-center py-4">Нет транзакций</p>
            )}
          </div>
        </div>

        {/* Подозрительные транзакции */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
          <div className="flex items-center gap-2 mb-4">
            <AlertTriangle className="w-5 h-5 text-amber-500" />
            <h3 className="text-lg font-semibold text-gray-900">Подозрительные</h3>
          </div>
          <div className="space-y-3">
            {suspicious_transactions && suspicious_transactions.length > 0 ? (
              suspicious_transactions.slice(0, 3).map((tx) => (
                <div key={tx.id} className="p-3 bg-amber-50 rounded-lg border border-amber-200">
                  <p className="text-sm font-medium text-gray-900">
                    {tx.description || 'Без описания'}
                  </p>
                  <p className="text-xs text-amber-600">{tx.suspicious_reason}</p>
                  <p className="text-sm font-bold text-red-600 mt-1">
                    {Number(tx.amount).toLocaleString('ru-RU')} ₽
                  </p>
                </div>
              ))
            ) : (
              <p className="text-gray-400 text-center py-4">Всё в порядке! 🎉</p>
            )}
          </div>
        </div>

        {/* Ближайшие платежи */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
          <div className="flex items-center gap-2 mb-4">
            <Bell className="w-5 h-5 text-blue-500" />
            <h3 className="text-lg font-semibold text-gray-900">Ближайшие платежи</h3>
          </div>
          <div className="space-y-3">
            {upcoming_reminders && upcoming_reminders.length > 0 ? (
              upcoming_reminders.slice(0, 3).map((rem) => (
                <div key={rem.id} className="p-3 bg-blue-50 rounded-lg border border-blue-200">
                  <p className="text-sm font-medium text-gray-900">{rem.title}</p>
                  <p className="text-xs text-blue-600">
                    {new Date(rem.next_reminder_date).toLocaleDateString('ru-RU')}
                  </p>
                  {rem.amount && (
                    <p className="text-sm font-bold text-gray-900 mt-1">
                      {Number(rem.amount).toLocaleString('ru-RU')} ₽
                    </p>
                  )}
                </div>
              ))
            ) : (
              <p className="text-gray-400 text-center py-4">Нет напоминаний</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

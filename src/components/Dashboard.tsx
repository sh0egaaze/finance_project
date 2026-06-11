import React, { useState, useEffect } from 'react';
import {
  TrendingUp, TrendingDown, Wallet, PiggyBank, RefreshCw,
  AlertTriangle, Bell, ArrowRight, Loader2
} from 'lucide-react';
import {
  XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, PieChart, Pie, Cell, LineChart, Line
} from 'recharts';
import { api, DashboardData, User } from '../api';
import { SmartInput } from './SmartInput';

interface DashboardProps {
  user: User;
  onTabChange?: (tab: string) => void;
}

const formatCurrency = (value: number) => {
  return new Intl.NumberFormat('ru-RU', { style: 'currency', currency: 'RUB', minimumFractionDigits: 0 }).format(value);
};

// Единые стили для графиков
const chartStyles = {
  grid: { stroke: '#374151', strokeDasharray: '3 3', opacity: 0.2 },
  tick: { fill: '#9CA3AF', fontSize: 11 },
  tooltip: { backgroundColor: '#1F2937', border: 'none', borderRadius: '8px', color: '#F9FAFB' },
  itemStyle: { color: '#F9FAFB' },
};

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

  const cardClass = "bg-white rounded-xl shadow-sm border border-gray-100 p-4 sm:p-5 dark:bg-gray-800 dark:border-gray-700";
  const titleClass = "text-base sm:text-lg font-semibold text-gray-900 dark:text-white";
  const subtitleClass = "text-gray-500 dark:text-gray-400";
  const emptyClass = "text-gray-400 text-center py-4 dark:text-gray-500";
  const iconBtnClass = "p-1 hover:bg-gray-100 rounded-lg transition-colors dark:hover:bg-gray-700";

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-xl p-6 text-center dark:bg-red-900/30 dark:border-red-700">
        <AlertTriangle className="w-12 h-12 text-red-500 mx-auto mb-4" />
        <p className="text-red-700 mb-4 dark:text-red-400">{error || 'Ошибка загрузки'}</p>
        <button onClick={loadDashboard} className="px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600">
          Попробовать снова
        </button>
      </div>
    );
  }

  const { stats, recent_transactions, spending_by_category, monthly_trend, upcoming_reminders, suspicious_transactions } = data;

  const statCards = [
    { title: 'Баланс', value: Number(stats.total_balance || 0), icon: Wallet, color: 'blue', format: 'currency' },
    { title: 'Доходы', value: Number(stats.total_income || 0), icon: TrendingUp, color: 'green', format: 'currency' },
    { title: 'Расходы', value: Number(stats.total_expense || 0), icon: TrendingDown, color: 'red', format: 'currency' },
    { title: 'Накопления', value: Number(stats.savings_rate || 0), icon: PiggyBank, color: 'purple', format: 'percent' },
  ];

  const formatValue = (value: number, format: string) => {
    if (format === 'currency') return `${value.toLocaleString('ru-RU')} ₽`;
    if (format === 'percent') return `${value.toFixed(1)}%`;
    return value.toString();
  };

  const colorClasses: Record<string, { bg: string; text: string; icon: string }> = {
    blue: { bg: 'bg-blue-50 dark:bg-blue-900/30', text: 'text-blue-600 dark:text-blue-400', icon: 'text-blue-500' },
    green: { bg: 'bg-green-50 dark:bg-green-900/30', text: 'text-green-600 dark:text-green-400', icon: 'text-green-500' },
    red: { bg: 'bg-red-50 dark:bg-red-900/30', text: 'text-red-600 dark:text-red-400', icon: 'text-red-500' },
    purple: { bg: 'bg-purple-50 dark:bg-purple-900/30', text: 'text-purple-600 dark:text-purple-400', icon: 'text-purple-500' },
  };

  return (
    <div className="space-y-4 sm:space-y-6">
      {/* Приветствие */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold text-gray-900 dark:text-white">
            Привет, {user.full_name || 'Пользователь'}! 👋
          </h1>
          <p className={`${subtitleClass} text-sm sm:text-base`}>Вот что происходит с вашими финансами</p>
        </div>
        <button onClick={loadDashboard} className="p-2 hover:bg-gray-100 rounded-lg transition-colors dark:hover:bg-gray-700" title="Обновить">
          <RefreshCw className="w-5 h-5 text-gray-500 dark:text-gray-400" />
        </button>
      </div>

      {/* Умный ввод */}
      <SmartInput onTransactionAdded={loadDashboard} />

      {/* Карточки статистики */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
        {statCards.map((card) => {
          const Icon = card.icon;
          const colors = colorClasses[card.color];
          return (
            <div key={card.title} className={cardClass}>
              <div className="flex items-center justify-between mb-2 sm:mb-3">
                <span className="text-xs sm:text-sm font-medium text-gray-500 dark:text-gray-400">{card.title}</span>
                <div className={`p-1.5 sm:p-2 rounded-lg ${colors.bg}`}>
                  <Icon className={`w-4 h-4 sm:w-5 sm:h-5 ${colors.icon}`} />
                </div>
              </div>
              <div className={`text-lg sm:text-2xl font-bold ${colors.text} truncate`}>
                {formatValue(card.value, card.format)}
              </div>
            </div>
          );
        })}
      </div>

      {/* Графики */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-6">
        {/* Тренд */}
        <div className={cardClass}>
          <h3 className={`${titleClass} mb-4`}>Динамика</h3>
          {monthly_trend && monthly_trend.length > 0 ? (
            <ResponsiveContainer width="100%" height={200}>
              <LineChart data={monthly_trend}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" opacity={0.2} />
                <XAxis
                  dataKey="date"
                  tick={chartStyles.tick}
                  tickFormatter={(value) => {
                    const date = new Date(value);
                    return `${String(date.getDate()).padStart(2, '0')}.${String(date.getMonth() + 1).padStart(2, '0')}`;
                  }}
                />
                <YAxis tick={chartStyles.tick} tickFormatter={(v) => Number(v).toLocaleString('ru-RU')} width={50} />
                <Tooltip
                  formatter={(value, name) => [formatCurrency(Number(value)), name === 'income' ? 'Доходы' : 'Расходы']}
                  labelFormatter={(label) => new Date(label).toLocaleDateString('ru-RU')}
                  contentStyle={chartStyles.tooltip}
                  itemStyle={chartStyles.itemStyle}
                  labelStyle={chartStyles.itemStyle}
                />
                <Line type="monotone" dataKey="income" name="income" stroke="#10B981" strokeWidth={2} dot={{ r: 3 }} activeDot={{ r: 5 }} />
                <Line type="monotone" dataKey="expense" name="expense" stroke="#EF4444" strokeWidth={2} dot={{ r: 3 }} activeDot={{ r: 5 }} />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-[200px] flex items-center justify-center text-gray-400 dark:text-gray-500">
              Нет данных для отображения
            </div>
          )}
        </div>

        {/* Категории */}
        <div className={cardClass}>
          <div className="flex items-center justify-between mb-4">
            <h3 className={titleClass}>{showIncome ? 'Доходы' : 'Расходы'}</h3>
            <button onClick={() => setShowIncome(!showIncome)} className={iconBtnClass} title={showIncome ? 'Показать расходы' : 'Показать доходы'}>
              <ArrowRight className="w-5 h-5 text-gray-400 hover:text-blue-500 transition-colors" />
            </button>
          </div>
          {(() => {
            const categoryData = showIncome ? (data.income_by_category || []) : (spending_by_category || []);
            return categoryData.length > 0 ? (
              <div className="flex flex-col sm:flex-row items-center gap-4">
                <ResponsiveContainer width="100%" height={160} className="sm:w-1/2">
                  <PieChart>
                    <Pie data={categoryData} dataKey="amount" nameKey="name" cx="50%" cy="50%" innerRadius={40} outerRadius={70}>
                      {categoryData.map((entry: { color?: string }, index: number) => (
                        <Cell key={index} fill={entry.color || (showIncome ? '#22c55e' : '#6B7280')} />
                      ))}
                    </Pie>
                    <Tooltip formatter={(value) => [formatCurrency(Number(value))]} contentStyle={chartStyles.tooltip} itemStyle={chartStyles.itemStyle} labelStyle={chartStyles.itemStyle} />
                  </PieChart>
                </ResponsiveContainer>
                <div className="flex-1 space-y-2 w-full sm:w-auto">
                  {categoryData.slice(0, 4).map((cat: { name: string; amount: number; color?: string; category?: string }) => (
                    <div key={cat.category || cat.name} className="flex items-center justify-between">
                      <div className="flex items-center gap-2 min-w-0">
                        <div className="w-2.5 h-2.5 rounded-full shrink-0" style={{ backgroundColor: cat.color || (showIncome ? '#22c55e' : '#6B7280') }} />
                        <span className="text-xs sm:text-sm text-gray-600 dark:text-gray-300 truncate">{cat.name}</span>
                      </div>
                      <span className="text-xs sm:text-sm font-medium dark:text-white shrink-0 ml-2">{cat.amount.toLocaleString('ru-RU')} ₽</span>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <div className="h-[160px] flex items-center justify-center text-gray-400 dark:text-gray-500">
                {showIncome ? 'Нет доходов' : 'Нет расходов'}
              </div>
            );
          })()}
        </div>
      </div>

      {/* Нижняя секция */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-6">
        {/* Последние транзакции */}
        <div className={cardClass}>
          <div className="flex items-center justify-between mb-4">
            <h3 className={titleClass}>Последние операции</h3>
            <button onClick={() => onTabChange?.('transactions')} className={iconBtnClass} title="Все транзакции">
              <ArrowRight className="w-5 h-5 text-gray-400 hover:text-blue-500" />
            </button>
          </div>
          <div className="space-y-2 sm:space-y-3">
            {recent_transactions && recent_transactions.length > 0 ? (
              recent_transactions.slice(0, 5).map((tx) => (
                <div key={tx.id} className="flex items-center justify-between py-2 border-b last:border-0 dark:border-gray-700">
                  <div className="min-w-0 flex-1">
                    <p className="text-xs sm:text-sm font-medium text-gray-900 dark:text-white truncate">{tx.description || 'Без описания'}</p>
                    <p className="text-xs text-gray-500 dark:text-gray-400">
                      {tx.transaction_date ? new Date(tx.transaction_date).toLocaleDateString('ru-RU') : ''}{' '}
                      {tx.transaction_date ? new Date(tx.transaction_date).toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' }) : ''}
                    </p>
                  </div>
                  <span className={`font-medium text-sm shrink-0 ml-2 ${Number(tx.amount) >= 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`}>
                    {Number(tx.amount) >= 0 ? '+' : ''}{Number(tx.amount).toLocaleString('ru-RU')} ₽
                  </span>
                </div>
              ))
            ) : (
              <p className={emptyClass}>Нет транзакций</p>
            )}
          </div>
        </div>

        {/* Подозрительные транзакции */}
        <div className={cardClass}>
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 sm:w-5 sm:h-5 text-amber-500" />
              <h3 className={titleClass}>Подозрительные</h3>
            </div>
            <button onClick={() => onTabChange?.('suspicious')} className={iconBtnClass} title="Все подозрительные">
              <ArrowRight className="w-5 h-5 text-gray-400 hover:text-blue-500" />
            </button>
          </div>
          <div className="space-y-2 sm:space-y-3">
            {suspicious_transactions && suspicious_transactions.length > 0 ? (
              suspicious_transactions.slice(0, 3).map((tx) => (
                <div key={tx.id} className="p-2 sm:p-3 bg-amber-50 rounded-lg border border-amber-200 dark:bg-amber-900/30 dark:border-amber-700">
                  <p className="text-xs sm:text-sm font-medium text-gray-900 dark:text-white truncate">{tx.description || 'Без описания'}</p>
                  <p className="text-xs text-amber-600 dark:text-amber-400 truncate">{tx.suspicious_reason}</p>
                  <p className="text-sm font-bold text-red-600 mt-1 dark:text-red-400">{Number(tx.amount).toLocaleString('ru-RU')} ₽</p>
                </div>
              ))
            ) : (
              <p className={emptyClass}>Всё в порядке! 🎉</p>
            )}
          </div>
        </div>

        {/* Ближайшие платежи */}
        <div className={`${cardClass} md:col-span-2 lg:col-span-1`}>
          <div className="flex items-center gap-2 mb-4">
            <Bell className="w-4 h-4 sm:w-5 sm:h-5 text-blue-500" />
            <h3 className={titleClass}>Ближайшие платежи</h3>
            <button onClick={() => onTabChange?.('reminders')} className={`${iconBtnClass} ml-auto`} title="Все напоминания">
              <ArrowRight className="w-5 h-5 text-gray-400 hover:text-blue-500" />
            </button>
          </div>
          <div className="space-y-2 sm:space-y-3">
            {upcoming_reminders && upcoming_reminders.length > 0 ? (
              upcoming_reminders.slice(0, 3).map((rem) => (
                <div key={rem.id} className="p-2 sm:p-3 bg-blue-50 rounded-lg border border-blue-200 dark:bg-blue-900/30 dark:border-blue-700">
                  <p className="text-xs sm:text-sm font-medium text-gray-900 dark:text-white truncate">{rem.title}</p>
                  <p className="text-xs text-blue-600 dark:text-blue-400">{new Date(rem.next_reminder_date).toLocaleDateString('ru-RU')}</p>
                  {rem.amount && <p className="text-sm font-bold text-gray-900 mt-1 dark:text-white">{Number(rem.amount).toLocaleString('ru-RU')} ₽</p>}
                </div>
              ))
            ) : (
              <p className={emptyClass}>Нет напоминаний</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

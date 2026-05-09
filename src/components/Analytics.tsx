import { useState, useEffect } from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  LineChart,
  Line,
} from 'recharts';
import { api, AnalyticsData } from '../api';

const CATEGORY_COLORS: Record<string, string> = {
  FOOD: '#F59E0B',
  TRANSPORT: '#3B82F6',
  ENTERTAINMENT: '#8B5CF6',
  SHOPPING: '#EC4899',
  UTILITIES: '#6366F1',
  HEALTH: '#10B981',
  EDUCATION: '#06B6D4',
  TRAVEL: '#F97316',
  SUBSCRIPTIONS: '#EF4444',
  OTHER: '#6B7280',
};

const formatCurrency = (value: number) => {
  return new Intl.NumberFormat('ru-RU', {
    style: 'currency',
    currency: 'RUB',
    minimumFractionDigits: 0,
  }).format(value);
};

export default function Analytics() {
  const [data, setData] = useState<AnalyticsData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  
  const today = new Date();
  const todayStr = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`;
  const firstDayStr = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-01`;
  const [dateFrom, setDateFrom] = useState(firstDayStr);
  const [dateTo, setDateTo] = useState(todayStr);
  const [showIncome, setShowIncome] = useState(false);

  useEffect(() => {
    const loadAnalytics = async () => {
      setIsLoading(true);
      try {
        const analytics = await api.getAnalytics(undefined, dateFrom, dateTo);
        setData(analytics);
      } catch (error) {
        console.error('Error loading analytics:', error);
      } finally {
        setIsLoading(false);
      }
    };
    loadAnalytics();
  }, [dateFrom, dateTo]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="bg-white rounded-xl shadow-sm p-12 text-center">
        <p className="text-gray-400">Не удалось загрузить аналитику</p>
      </div>
    );
  }

  const spendingByCategory = (data.spending_by_category || []).map(item => ({
    ...item,
    fill: item.color || CATEGORY_COLORS[item.category] || '#6B7280',
  }));

  const totalSpending = spendingByCategory.reduce((a, b) => a + b.amount, 0);

  if (spendingByCategory.length === 0) {
    return (
      <div className="space-y-6">
        <h2 className="text-2xl font-bold text-gray-800">Аналитика</h2>
        <div className="bg-white rounded-xl shadow-sm p-12 text-center">
          <p className="text-gray-400">Недостаточно данных для аналитики</p>
          <p className="text-sm text-gray-400 mt-2">Добавьте транзакции, чтобы увидеть статистику</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-gray-800">Аналитика</h2>
        <div className="flex items-center gap-2">
          <input
            type="date"
            value={dateFrom}
            onChange={(e) => setDateFrom(e.target.value)}
            className="px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 text-sm"
          />
          <span className="text-gray-400">—</span>
          <input
            type="date"
            value={dateTo}
            onChange={(e) => setDateTo(e.target.value)}
            className="px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 text-sm"
          />
        </div>
      </div>

      {/* Summary Cards */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <div className="bg-white rounded-xl shadow-sm p-6">
          <p className="text-gray-500 text-sm">Доходы</p>
          <p className="text-2xl font-bold text-green-600">
            {formatCurrency(data.total_income || 0)}
          </p>
        </div>
        <div className="bg-white rounded-xl shadow-sm p-6">
          <p className="text-gray-500 text-sm">Расходы</p>
          <p className="text-2xl font-bold text-red-600">
            {formatCurrency(totalSpending)}
          </p>
        </div>
        <div className="bg-white rounded-xl shadow-sm p-6">
          <p className="text-gray-500 text-sm">Баланс</p>
          <p className={`text-2xl font-bold ${(data.total_income || 0) - totalSpending >= 0 ? 'text-blue-600' : 'text-red-600'}`}>
            {formatCurrency((data.total_income || 0) - totalSpending)}
          </p>
        </div>
        <div className="bg-white rounded-xl shadow-sm p-6">
          <p className="text-gray-500 text-sm">Топ категория</p>
          <p className="text-2xl font-bold text-gray-800">
            {spendingByCategory.length > 0 
              ? spendingByCategory.sort((a, b) => b.amount - a.amount)[0].name 
              : '-'}
          </p>
        </div>
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Bar Chart */}
        <div className="bg-white rounded-xl shadow-sm p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-gray-800">
              {showIncome ? 'Доходы по категориям' : 'Расходы по категориям'}
            </h3>
            <button
              onClick={() => setShowIncome(!showIncome)}
              className="p-1 hover:bg-gray-100 rounded-lg transition-colors"
              title={showIncome ? 'Показать расходы' : 'Показать доходы'}
            >
              <svg className="w-5 h-5 text-gray-400 hover:text-blue-500" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" /></svg>
            </button>
          </div>
          {(() => {
            const chartData = showIncome ? (data.income_by_category || []) : spendingByCategory;
            return chartData.length > 0 ? (
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                  <YAxis tickFormatter={(v) => Number(v).toLocaleString('ru-RU')} width={80} />
                  <Tooltip formatter={(value) => [formatCurrency(Number(value)), 'Сумма']} />
                  <Bar dataKey="amount" radius={[4, 4, 0, 0]}>
                    {chartData.map((entry: any, index: number) => (
                      <Cell key={index} fill={entry.fill || entry.color || (showIncome ? '#22c55e' : '#6B7280')} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-[300px] flex items-center justify-center text-gray-400">
                {showIncome ? 'Нет доходов' : 'Нет расходов'}
              </div>
            );
          })()}
        </div>

        {/* Pie Chart */}
        <div className="bg-white rounded-xl shadow-sm p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-gray-800">
              {showIncome ? 'Структура доходов' : 'Структура расходов'}
            </h3>
            <button
              onClick={() => setShowIncome(!showIncome)}
              className="p-1 hover:bg-gray-100 rounded-lg transition-colors"
              title={showIncome ? 'Показать расходы' : 'Показать доходы'}
            >
              <svg className="w-5 h-5 text-gray-400 hover:text-blue-500" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" /></svg>
            </button>
          </div>
          {(() => {
            const chartData = showIncome ? (data.income_by_category || []) : spendingByCategory;
            const total = chartData.reduce((a: number, b: any) => a + b.amount, 0);
            return chartData.length > 0 ? (
              <ResponsiveContainer width="100%" height={300}>
                <PieChart>
                  <Pie
                    data={chartData}
                    dataKey="amount"
                    nameKey="name"
                    cx="50%"
                    cy="50%"
                    outerRadius={100}
                    label={({ name, percent }) => `${name}: ${((percent || 0) * 100).toFixed(1)}%`}
                  >
                    {chartData.map((entry: any, index: number) => (
                      <Cell key={index} fill={entry.fill || entry.color || (showIncome ? '#22c55e' : '#6B7280')} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(value) => [formatCurrency(Number(value))]} />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-[300px] flex items-center justify-center text-gray-400">
                {showIncome ? 'Нет доходов' : 'Нет расходов'}
              </div>
            );
          })()}
        </div>
      </div>

      {/* Spending Trend */}
      {data.spending_trend && data.spending_trend.length > 0 && (
        <div className="bg-white rounded-xl shadow-sm p-6">
          <h3 className="text-lg font-semibold text-gray-800 mb-4">Динамика доходов и расходов</h3>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={data.spending_trend}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" />
              <YAxis tickFormatter={(v) => Number(v).toLocaleString('ru-RU')} width={80} />
              <Tooltip formatter={(value, name) => {
                const label = name === 'income' ? 'Доходы' : 'Расходы';
                return [formatCurrency(Number(value)), label];
              }} />
              <Line type="monotone" dataKey="income" stroke="#10B981" name="Доходы" strokeWidth={2} />
              <Line type="monotone" dataKey="expense" stroke="#EF4444" name="Расходы" strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Category Details */}
      <div className="bg-white rounded-xl shadow-sm p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-gray-800">
            {showIncome ? 'Детали по доходам' : 'Детали по расходам'}
          </h3>
          <button
            onClick={() => setShowIncome(!showIncome)}
            className="p-1 hover:bg-gray-100 rounded-lg transition-colors"
            title={showIncome ? 'Показать расходы' : 'Показать доходы'}
          >
            <svg className="w-5 h-5 text-gray-400 hover:text-blue-500" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" /></svg>
          </button>
        </div>
        <div className="space-y-3">
          {(() => {
            const detailData = showIncome 
              ? (data.income_by_category || []).sort((a: any, b: any) => b.amount - a.amount)
              : spendingByCategory.sort((a, b) => b.amount - a.amount);
            const detailTotal = detailData.reduce((a: number, b: any) => a + b.amount, 0);
            
            return detailData.map((item: any) => {
              const percentage = detailTotal > 0 ? (item.amount / detailTotal) * 100 : 0;
            return (
                <div key={item.category_id || item.name} className="flex items-center gap-4">
                  <div 
                    className="w-4 h-4 rounded-full" 
                    style={{ backgroundColor: item.fill || item.color || (showIncome ? '#22c55e' : '#6B7280') }}
                  />
                  <span className="flex-1 text-gray-700">{item.name}</span>
                  <span className="text-gray-500">{percentage.toFixed(1)}%</span>
                  <span className="font-semibold text-gray-800 w-28 text-right">
                    {formatCurrency(item.amount)}
                  </span>
                </div>
              );
            });
          })()}
        </div>
      </div>
    </div>
  );
}

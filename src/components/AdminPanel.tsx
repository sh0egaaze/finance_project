import { useState, useEffect } from 'react';
import {
  Users, BarChart3, Shield, Search, Ban, CheckCircle, Trash2,
  AlertCircle, ChevronLeft, ChevronRight, FileText, Activity,
  UserCheck, UserX, Crown, RefreshCw, Mail
} from 'lucide-react';
import { api, AdminStats, AdminUser, AuditLogEntry } from '../api';

type AdminTab = 'stats' | 'users' | 'logs';

export default function AdminPanel() {
  const [activeTab, setActiveTab] = useState<AdminTab>('stats');

  const tabClass = (tab: AdminTab) =>
    `flex items-center gap-1.5 sm:gap-2 px-3 sm:px-4 py-2 rounded-lg text-xs sm:text-sm font-medium transition-colors ${
      activeTab === tab
        ? 'bg-blue-600 text-white'
        : 'text-gray-600 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-700'
    }`;

  return (
    <div className="space-y-4 sm:space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl sm:text-2xl font-bold text-gray-800 dark:text-white flex items-center gap-2">
          <Shield className="w-6 h-6 sm:w-7 sm:h-7 text-blue-600" />
          Админ-панель
        </h2>
      </div>

      <div className="flex gap-1 sm:gap-2 bg-white dark:bg-gray-800 p-1 sm:p-1.5 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700 w-fit overflow-x-auto">
        <button onClick={() => setActiveTab('stats')} className={tabClass('stats')}>
          <BarChart3 className="w-4 h-4" /> <span className="hidden xs:inline">Статистика</span>
        </button>
        <button onClick={() => setActiveTab('users')} className={tabClass('users')}>
          <Users className="w-4 h-4" /> <span className="hidden xs:inline">Пользователи</span>
        </button>
        <button onClick={() => setActiveTab('logs')} className={tabClass('logs')}>
          <FileText className="w-4 h-4" /> <span className="hidden xs:inline">Логи</span>
        </button>
      </div>

      {activeTab === 'stats' && <StatsTab />}
      {activeTab === 'users' && <UsersTab />}
      {activeTab === 'logs' && <LogsTab />}
    </div>
  );
}


// ====== СТАТИСТИКА ======
function StatsTab() {
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    api.getAdminStats().then(setStats).catch(console.error).finally(() => setIsLoading(false));
  }, []);

  if (isLoading) return <Loader />;
  if (!stats) return <ErrorMsg text="Ошибка загрузки статистики" />;

  const cards = [
    { label: 'Пользователей', value: stats.total_users, icon: Users, color: 'blue' },
    { label: 'Активных', value: stats.active_users, icon: UserCheck, color: 'green' },
    { label: 'Email подтв.', value: stats.verified_users, icon: Mail, color: 'emerald' },
    { label: 'Т-Банк', value: stats.tbank_connected_count, icon: Activity, color: 'yellow' },
    { label: 'Транзакций', value: stats.total_transactions, icon: BarChart3, color: 'indigo' },
    { label: 'Напомин.', value: stats.total_reminders, icon: AlertCircle, color: 'purple' },
  ];

  const colorMap: Record<string, string> = {
    blue: 'bg-blue-100 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400',
    green: 'bg-green-100 text-green-600 dark:bg-green-900/30 dark:text-green-400',
    emerald: 'bg-emerald-100 text-emerald-600 dark:bg-emerald-900/30 dark:text-emerald-400',
    yellow: 'bg-yellow-100 text-yellow-600 dark:bg-yellow-900/30 dark:text-yellow-400',
    indigo: 'bg-indigo-100 text-indigo-600 dark:bg-indigo-900/30 dark:text-indigo-400',
    purple: 'bg-purple-100 text-purple-600 dark:bg-purple-900/30 dark:text-purple-400',
  };

  return (
    <div className="space-y-4 sm:space-y-6">
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 sm:gap-4">
        {cards.map(({ label, value, icon: Icon, color }) => (
          <div key={label} className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700 p-3 sm:p-4">
            <div className={`w-8 h-8 sm:w-10 sm:h-10 rounded-lg flex items-center justify-center mb-2 sm:mb-3 ${colorMap[color]}`}>
              <Icon className="w-4 h-4 sm:w-5 sm:h-5" />
            </div>
            <p className="text-xl sm:text-2xl font-bold text-gray-800 dark:text-white">{value.toLocaleString('ru-RU')}</p>
            <p className="text-xs text-gray-400 dark:text-gray-500 mt-1 truncate">{label}</p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 sm:gap-6">
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700 p-4 sm:p-6">
          <h3 className="text-base sm:text-lg font-semibold text-gray-800 dark:text-white mb-4">Регистрации</h3>
          <div className="space-y-3">
            <StatRow label="Сегодня" value={stats.users_today} />
            <StatRow label="За неделю" value={stats.users_this_week} />
            <StatRow label="За месяц" value={stats.users_this_month} />
          </div>
        </div>
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700 p-4 sm:p-6">
          <h3 className="text-base sm:text-lg font-semibold text-gray-800 dark:text-white mb-4">Активность</h3>
          <div className="space-y-3">
            <StatRow label="Транзакций сегодня" value={stats.transactions_today} />
            <StatRow label="Транзакций за неделю" value={stats.transactions_this_week} />
            <StatRow label="Транзакций за месяц" value={stats.transactions_this_month} />
            <StatRow label="Активны сегодня" value={stats.active_today} />
            <StatRow label="Активны за неделю" value={stats.active_this_week} />
          </div>
        </div>
      </div>
    </div>
  );
}

function StatRow({ label, value }: { label: string; value: number }) {
  return (
    <div className="flex justify-between items-center">
      <span className="text-xs sm:text-sm text-gray-500 dark:text-gray-400">{label}</span>
      <span className="text-xs sm:text-sm font-semibold text-gray-800 dark:text-white">{value.toLocaleString('ru-RU')}</span>
    </div>
  );
}


// ====== ПОЛЬЗОВАТЕЛИ ======
function UsersTab() {
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [search, setSearch] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const limit = 15;

  const loadUsers = async () => {
    setIsLoading(true);
    try {
      const data = await api.getAdminUsers({ limit, offset, search: search || undefined });
      setUsers(data.items);
      setTotal(data.total);
    } catch (e) { console.error(e); }
    finally { setIsLoading(false); }
  };

  useEffect(() => { loadUsers(); }, [offset]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setOffset(0);
    loadUsers();
  };

  const handleAction = async (action: () => Promise<unknown>) => {
    try { await action(); loadUsers(); }
    catch (e: unknown) { 
      const error = e as { response?: { data?: { detail?: string } } };
      alert(error?.response?.data?.detail || 'Ошибка'); 
    }
  };

  const formatDate = (d: string | null) => d ? new Date(d).toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit', year: '2-digit', hour: '2-digit', minute: '2-digit' }) : '—';
  const totalPages = Math.ceil(total / limit);
  const currentPage = Math.floor(offset / limit) + 1;

  return (
    <div className="space-y-4">
      <form onSubmit={handleSearch} className="flex flex-col sm:flex-row gap-2 sm:gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Поиск по email или имени..."
            className="w-full pl-10 pr-4 py-2 border rounded-lg dark:bg-gray-700 dark:border-gray-600 dark:text-white text-sm"
          />
        </div>
        <div className="flex gap-2">
          <button type="submit" className="flex-1 sm:flex-none px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm">Найти</button>
          <button type="button" onClick={() => { setSearch(''); setOffset(0); setTimeout(loadUsers, 0); }} className="flex-1 sm:flex-none px-4 py-2 border rounded-lg text-gray-600 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-400 dark:hover:bg-gray-700 text-sm">Сбросить</button>
        </div>
      </form>

      {isLoading ? <Loader /> : (
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700 overflow-hidden">
          {/* Мобильный вид - карточки */}
          <div className="lg:hidden divide-y dark:divide-gray-700">
            {users.map((u) => (
              <div key={u.id} className={`p-4 ${!u.is_active ? 'opacity-50' : ''}`}>
                <div className="flex items-start justify-between mb-2">
                  <div className="flex items-center gap-2">
                    {u.is_superuser && <Crown className="w-4 h-4 text-yellow-500" />}
                    <div>
                      <p className="text-sm font-medium text-gray-800 dark:text-white">{u.full_name || '—'}</p>
                      <p className="text-xs text-gray-400">{u.email}</p>
                    </div>
                  </div>
                  <div className="flex gap-1">
                    {u.is_active ? (
                      <span className="px-2 py-0.5 rounded-full text-xs bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400">Активен</span>
                    ) : (
                      <span className="px-2 py-0.5 rounded-full text-xs bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400">Заблок.</span>
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-4 text-xs text-gray-500 dark:text-gray-400 mb-3">
                  <span>Транзакций: {u.transactions_count}</span>
                  <span>Email: {u.email_verified ? '✓' : '✗'}</span>
                </div>
                <div className="flex gap-1 flex-wrap">
                  {!u.email_verified && (
                    <button onClick={() => handleAction(() => api.adminVerifyEmail(u.id))} className="p-1.5 text-emerald-500 hover:bg-emerald-50 rounded dark:hover:bg-emerald-900/20" title="Подтвердить email">
                      <Mail className="w-4 h-4" />
                    </button>
                  )}
                  {u.is_active ? (
                    <button onClick={() => { if (confirm(`Заблокировать ${u.email}?`)) handleAction(() => api.blockUser(u.id)); }} className="p-1.5 text-amber-500 hover:bg-amber-50 rounded dark:hover:bg-amber-900/20" title="Заблокировать">
                      <Ban className="w-4 h-4" />
                    </button>
                  ) : (
                    <button onClick={() => handleAction(() => api.unblockUser(u.id))} className="p-1.5 text-green-500 hover:bg-green-50 rounded dark:hover:bg-green-900/20" title="Разблокировать">
                      <CheckCircle className="w-4 h-4" />
                    </button>
                  )}
                  <button onClick={() => handleAction(() => api.toggleSuperuser(u.id))} className="p-1.5 text-yellow-500 hover:bg-yellow-50 rounded dark:hover:bg-yellow-900/20" title={u.is_superuser ? 'Снять админа' : 'Сделать админом'}>
                    <Crown className="w-4 h-4" />
                  </button>
                  <button onClick={() => { if (confirm(`УДАЛИТЬ ${u.email}? Это необратимо!`)) handleAction(() => api.deleteUser(u.id)); }} className="p-1.5 text-red-500 hover:bg-red-50 rounded dark:hover:bg-red-900/20" title="Удалить">
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>

          {/* Десктопный вид - таблица */}
          <div className="hidden lg:block overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-100 dark:border-gray-700 bg-gray-50 dark:bg-gray-800">
                  <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Пользователь</th>
                  <th className="text-center px-4 py-3 text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Статус</th>
                  <th className="text-center px-4 py-3 text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Email</th>
                  <th className="text-center px-4 py-3 text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Транз.</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Регистрация</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Посл. вход</th>
                  <th className="text-right px-4 py-3 text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Действия</th>
                </tr>
              </thead>
              <tbody>
                {users.map((u) => (
                  <tr key={u.id} className={`border-b border-gray-50 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700/50 ${!u.is_active ? 'opacity-50' : ''}`}>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        {u.is_superuser && <Crown className="w-4 h-4 text-yellow-500" />}
                        <div>
                          <p className="text-sm font-medium text-gray-800 dark:text-white">{u.full_name || '—'}</p>
                          <p className="text-xs text-gray-400">{u.email}</p>
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-center">
                      {u.is_active ? (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400">
                          <UserCheck className="w-3 h-3" /> Активен
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400">
                          <UserX className="w-3 h-3" /> Заблок.
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-center">
                      {u.email_verified ? (
                        <CheckCircle className="w-4 h-4 text-green-500 mx-auto" />
                      ) : (
                        <AlertCircle className="w-4 h-4 text-amber-500 mx-auto" />
                      )}
                    </td>
                    <td className="px-4 py-3 text-center text-sm text-gray-600 dark:text-gray-300">{u.transactions_count}</td>
                    <td className="px-4 py-3 text-xs text-gray-500 dark:text-gray-400">{formatDate(u.created_at)}</td>
                    <td className="px-4 py-3 text-xs text-gray-500 dark:text-gray-400">{formatDate(u.last_login)}</td>
                    <td className="px-4 py-3">
                      <div className="flex justify-end gap-1">
                        {!u.email_verified && (
                          <button onClick={() => handleAction(() => api.adminVerifyEmail(u.id))} className="p-1.5 text-emerald-500 hover:bg-emerald-50 rounded dark:hover:bg-emerald-900/20" title="Подтвердить email">
                            <Mail className="w-4 h-4" />
                          </button>
                        )}
                        {u.is_active ? (
                          <button onClick={() => { if (confirm(`Заблокировать ${u.email}?`)) handleAction(() => api.blockUser(u.id)); }} className="p-1.5 text-amber-500 hover:bg-amber-50 rounded dark:hover:bg-amber-900/20" title="Заблокировать">
                            <Ban className="w-4 h-4" />
                          </button>
                        ) : (
                          <button onClick={() => handleAction(() => api.unblockUser(u.id))} className="p-1.5 text-green-500 hover:bg-green-50 rounded dark:hover:bg-green-900/20" title="Разблокировать">
                            <CheckCircle className="w-4 h-4" />
                          </button>
                        )}
                        <button onClick={() => handleAction(() => api.toggleSuperuser(u.id))} className="p-1.5 text-yellow-500 hover:bg-yellow-50 rounded dark:hover:bg-yellow-900/20" title={u.is_superuser ? 'Снять админа' : 'Сделать админом'}>
                          <Crown className="w-4 h-4" />
                        </button>
                        <button onClick={() => { if (confirm(`УДАЛИТЬ ${u.email}? Это необратимо!`)) handleAction(() => api.deleteUser(u.id)); }} className="p-1.5 text-red-500 hover:bg-red-50 rounded dark:hover:bg-red-900/20" title="Удалить">
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {totalPages > 1 && (
            <div className="flex items-center justify-between px-4 py-3 border-t border-gray-100 dark:border-gray-700">
              <p className="text-xs sm:text-sm text-gray-500 dark:text-gray-400">Всего: {total}</p>
              <div className="flex items-center gap-2">
                <button onClick={() => setOffset(Math.max(0, offset - limit))} disabled={offset === 0} className="p-1 rounded hover:bg-gray-100 disabled:opacity-30 dark:hover:bg-gray-700"><ChevronLeft className="w-5 h-5 text-gray-600 dark:text-gray-300" /></button>
                <span className="text-xs sm:text-sm text-gray-600 dark:text-gray-300">{currentPage} / {totalPages}</span>
                <button onClick={() => setOffset(offset + limit)} disabled={currentPage >= totalPages} className="p-1 rounded hover:bg-gray-100 disabled:opacity-30 dark:hover:bg-gray-700"><ChevronRight className="w-5 h-5 text-gray-600 dark:text-gray-300" /></button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}


// ====== АУДИТ-ЛОГИ ======
function LogsTab() {
  const [logs, setLogs] = useState<AuditLogEntry[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const limit = 30;

  const loadLogs = async () => {
    setIsLoading(true);
    try {
      const data = await api.getAuditLogs({ limit, offset });
      setLogs(data.items);
      setTotal(data.total);
    } catch (e) { console.error(e); }
    finally { setIsLoading(false); }
  };

  useEffect(() => { loadLogs(); }, [offset]);

  const formatDate = (d: string | null) => d ? new Date(d).toLocaleString('ru-RU') : '—';
  const totalPages = Math.ceil(total / limit);
  const currentPage = Math.floor(offset / limit) + 1;

  const actionLabels: Record<string, string> = {
    user_registered: '👤 Регистрация',
    currency_rates_updated: '💱 Курсы валют',
    reminders_check: '🔔 Проверка напоминаний',
    reminder_sent: '📧 Напоминание отправлено',
    block_user: '🔒 Блокировка',
    unblock_user: '🔓 Разблокировка',
    delete_user: '🗑️ Удаление',
    admin_verify_email: '✅ Подтверждение email',
    toggle_superuser: '👑 Права админа',
  };

  if (isLoading) return <Loader />;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-xs sm:text-sm text-gray-500 dark:text-gray-400">Всего: {total}</p>
        <button onClick={loadLogs} className="flex items-center gap-2 px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-100 rounded-lg dark:text-gray-400 dark:hover:bg-gray-700">
          <RefreshCw className="w-4 h-4" /> Обновить
        </button>
      </div>

      {logs.length === 0 ? (
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700 p-12 text-center">
          <FileText className="w-12 h-12 text-gray-300 dark:text-gray-600 mx-auto mb-4" />
          <p className="text-gray-400 dark:text-gray-500">Логов пока нет</p>
        </div>
      ) : (
        <div className="space-y-2">
          {logs.map((log) => (
            <div key={log.id} className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700 p-3 sm:p-4">
              <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-2">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1 flex-wrap">
                    <span className="text-xs sm:text-sm font-medium text-gray-800 dark:text-white">
                      {actionLabels[log.action] || log.action}
                    </span>
                    {log.status && (
                      <span className={`text-xs px-1.5 py-0.5 rounded ${log.status === 'success' ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400' : 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'}`}>
                        {log.status}
                      </span>
                    )}
                  </div>
                  <p className="text-xs sm:text-sm text-gray-500 dark:text-gray-400 break-words">{log.description}</p>
                  {log.user_email && (
                    <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">Выполнил: {log.user_email}</p>
                  )}
                </div>
                <span className="text-xs text-gray-400 dark:text-gray-500 whitespace-nowrap shrink-0">{formatDate(log.created_at)}</span>
              </div>
            </div>
          ))}
        </div>
      )}

      {totalPages > 1 && (
        <div className="flex justify-center gap-2">
          <button onClick={() => setOffset(Math.max(0, offset - limit))} disabled={offset === 0} className="p-2 rounded-lg hover:bg-gray-100 disabled:opacity-30 dark:hover:bg-gray-700"><ChevronLeft className="w-5 h-5" /></button>
          <span className="flex items-center text-sm text-gray-600 dark:text-gray-300">{currentPage} / {totalPages}</span>
          <button onClick={() => setOffset(offset + limit)} disabled={currentPage >= totalPages} className="p-2 rounded-lg hover:bg-gray-100 disabled:opacity-30 dark:hover:bg-gray-700"><ChevronRight className="w-5 h-5" /></button>
        </div>
      )}
    </div>
  );
}


// ====== Общие компоненты ======
function Loader() {
  return (
    <div className="flex items-center justify-center h-40">
      <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-600 dark:border-blue-400" />
    </div>
  );
}

function ErrorMsg({ text }: { text: string }) {
  return <div className="bg-red-50 text-red-600 p-4 rounded-lg dark:bg-red-900/30 dark:text-red-400">{text}</div>;
}

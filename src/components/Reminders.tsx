import { useState, useEffect } from 'react';
import { Plus, Bell, Trash2, Check, Clock, Calendar, Edit2, ChevronDown, Archive, Mail, AlertTriangle } from 'lucide-react';
import { api, Reminder, ReminderCreate, User as UserType } from '../api';

interface RemindersProps {
  user: UserType;
}

const formatCurrency = (value: number) => {
  return new Intl.NumberFormat('ru-RU', { style: 'currency', currency: 'RUB', minimumFractionDigits: 0 }).format(value);
};

const formatDate = (dateString: string) => {
  return new Date(dateString).toLocaleDateString('ru-RU', { day: 'numeric', month: 'long', year: 'numeric' });
};

const FREQUENCY_LABELS: Record<string, string> = {
  once: 'Один раз',
  daily: 'Ежедневно',
  weekly: 'Еженедельно',
  monthly: 'Ежемесячно',
  custom: 'Свой интервал',
};

const getDefaultDate = () => {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
};

export default function Reminders({ user }: RemindersProps) {
  const [reminders, setReminders] = useState<Reminder[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [editingReminder, setEditingReminder] = useState<Reminder | null>(null);
  const [formData, setFormData] = useState<ReminderCreate>({
    title: '',
    description: '',
    amount: undefined,
    frequency: 'once',
    next_reminder_date: getDefaultDate(),
  });
  const [reminderTime, setReminderTime] = useState('09:00');
  const [archivedReminders, setArchivedReminders] = useState<Reminder[]>([]);
  const [showArchive, setShowArchive] = useState(false);
  const [archiveLoaded, setArchiveLoaded] = useState(false);

  const isEmailVerified = user.email_verified;

  const cardClass = "bg-white rounded-xl shadow-sm p-4 sm:p-6 dark:bg-gray-800";
  const titleClass = "text-gray-800 dark:text-white";
  const labelClass = "block text-sm font-medium text-gray-700 mb-1 dark:text-gray-300";
  const inputClass = "w-full px-3 sm:px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white dark:placeholder-gray-400 text-sm sm:text-base";
  const mutedClass = "text-gray-400 dark:text-gray-500";

  const loadReminders = async () => {
    try {
      const data = await api.getReminders();
      setReminders(data);
    } catch (error) {
      console.error('Error loading reminders:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const loadArchive = async () => {
    try {
      const data = await api.getArchivedReminders();
      setArchivedReminders(data);
      setArchiveLoaded(true);
    } catch (error) {
      console.error('Error loading archive:', error);
    }
  };

  const toggleArchive = () => {
    if (!showArchive && !archiveLoaded) loadArchive();
    setShowArchive(!showArchive);
  };

  useEffect(() => {
    loadReminders();
  }, []);

  const resetForm = () => {
    setFormData({ title: '', description: '', amount: undefined, frequency: 'once', next_reminder_date: getDefaultDate() });
    setReminderTime('09:00');
    setEditingReminder(null);
  };

  const openCreateForm = () => {
    if (!isEmailVerified) return;
    resetForm();
    setShowForm(true);
  };

  const openEditForm = (reminder: Reminder) => {
    const date = new Date(reminder.next_reminder_date);
    setFormData({
      title: reminder.title,
      description: reminder.description || '',
      amount: reminder.amount ? Number(reminder.amount) : undefined,
      frequency: reminder.frequency,
      next_reminder_date: date.toISOString().split('T')[0],
    });
    setReminderTime(`${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`);
    setEditingReminder(reminder);
    setShowForm(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const dateWithTime = new Date(`${formData.next_reminder_date}T${reminderTime}:00`);
      const payload = { ...formData, next_reminder_date: dateWithTime.toISOString() };
      if (editingReminder) {
        await api.updateReminder(editingReminder.id, payload);
      } else {
        await api.createReminder(payload);
      }
      setShowForm(false);
      resetForm();
      loadReminders();
    } catch (error) {
      console.error('Error saving reminder:', error);
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm('Удалить напоминание?')) return;
    try {
      await api.deleteReminder(id);
      loadReminders();
      if (archiveLoaded) loadArchive();
    } catch (error) {
      console.error('Error deleting reminder:', error);
    }
  };

  const handleComplete = async (id: number) => {
    try {
      await api.completeReminder(id);
      loadReminders();
      if (archiveLoaded) loadArchive();
    } catch (error) {
      console.error('Error completing reminder:', error);
    }
  };

  const handleResendVerification = async () => {
    try {
      await api.resendVerification(user.email);
      alert('Письмо с подтверждением отправлено на ' + user.email);
    } catch {
      alert('Ошибка отправки. Попробуйте позже.');
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 dark:border-blue-400"></div>
      </div>
    );
  }

  return (
    <div className="space-y-4 sm:space-y-6">
      <div className="flex items-center justify-between">
        <h2 className={`text-xl sm:text-2xl font-bold ${titleClass}`}>Напоминания</h2>
        {isEmailVerified ? (
          <button onClick={openCreateForm} className="flex items-center gap-2 px-3 sm:px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm">
            <Plus className="w-4 h-4" />
            <span className="hidden xs:inline">Добавить</span>
          </button>
        ) : (
          <button disabled className="flex items-center gap-2 px-3 sm:px-4 py-2 bg-gray-300 text-gray-500 rounded-lg cursor-not-allowed dark:bg-gray-700 dark:text-gray-500 text-sm">
            <Plus className="w-4 h-4" />
            <span className="hidden xs:inline">Добавить</span>
          </button>
        )}
      </div>

      {/* Баннер: email не подтверждён */}
      {!isEmailVerified && (
        <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 sm:p-5 dark:bg-amber-900/20 dark:border-amber-800">
          <div className="flex items-start gap-3 sm:gap-4">
            <div className="w-8 h-8 sm:w-10 sm:h-10 bg-amber-100 rounded-full flex items-center justify-center shrink-0 dark:bg-amber-800">
              <AlertTriangle className="w-4 h-4 sm:w-5 sm:h-5 text-amber-600 dark:text-amber-400" />
            </div>
            <div className="flex-1 min-w-0">
              <h3 className="text-sm sm:text-base font-semibold text-amber-800 dark:text-amber-300">
                Подтвердите email
              </h3>
              <p className="text-xs sm:text-sm text-amber-700 mt-1 dark:text-amber-400">
                Для создания напоминаний необходимо подтвердить ваш email-адрес <strong className="break-all">{user.email}</strong>.
              </p>
              <button
                onClick={handleResendVerification}
                className="mt-3 flex items-center gap-2 px-3 sm:px-4 py-2 bg-amber-600 text-white rounded-lg hover:bg-amber-700 transition-colors text-xs sm:text-sm font-medium"
              >
                <Mail className="w-4 h-4" />
                Отправить письмо повторно
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Form Modal */}
      {showForm && isEmailVerified && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" onClick={() => { setShowForm(false); resetForm(); }}>
          <div className="bg-white rounded-xl shadow-xl w-full max-w-md max-h-[90vh] overflow-y-auto overflow-x-hidden dark:bg-gray-800" onClick={(e) => e.stopPropagation()}>
            <div className="sticky top-0 bg-white dark:bg-gray-800 px-4 sm:px-6 py-4 border-b dark:border-gray-700">
              <h3 className={`text-lg sm:text-xl font-semibold ${titleClass}`}>
                {editingReminder ? 'Редактировать' : 'Новое напоминание'}
              </h3>
            </div>
            <form onSubmit={handleSubmit} className="p-4 sm:p-6 space-y-4">
              <div>
                <label className={labelClass}>Название *</label>
                <input type="text" value={formData.title} onChange={(e) => setFormData({ ...formData, title: e.target.value })} placeholder="Например: Оплата ЖКХ" className={inputClass} required />
              </div>
              <div>
                <label className={labelClass}>Описание</label>
                <input type="text" value={formData.description || ''} onChange={(e) => setFormData({ ...formData, description: e.target.value })} placeholder="Дополнительная информация" className={inputClass} />
              </div>
              <div>
                <label className={labelClass}>Сумма (необязательно)</label>
                <input type="number" value={formData.amount || ''} onChange={(e) => setFormData({ ...formData, amount: e.target.value ? Number(e.target.value) : undefined })} placeholder="Если сумма фиксированная" className={inputClass} />
              </div>
              <div>
                <label className={labelClass}>Периодичность</label>
                <select value={formData.frequency} onChange={(e) => setFormData({ ...formData, frequency: e.target.value })} className={inputClass}>
                  <option value="once">Один раз</option>
                  <option value="daily">Ежедневно</option>
                  <option value="weekly">Еженедельно</option>
                  <option value="monthly">Ежемесячно</option>
                  <option value="custom">Свой интервал</option>
                </select>
              </div>
              {formData.frequency === 'custom' && (
                <div>
                  <label className={labelClass}>Интервал (дней)</label>
                  <input type="number" value={formData.interval_days || ''} onChange={(e) => setFormData({ ...formData, interval_days: Number(e.target.value) })} placeholder="Например: 30" className={inputClass} />
                </div>
              )}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className={labelClass}>Дата</label>
                  <input type="date" value={formData.next_reminder_date} onChange={(e) => setFormData({ ...formData, next_reminder_date: e.target.value })} className={inputClass} required />
                </div>
                <div>
                  <label className={labelClass}>Время</label>
                  <input type="time" value={reminderTime} onChange={(e) => setReminderTime(e.target.value)} className={inputClass} required />
                </div>
              </div>
              <div className="flex gap-3 pt-4">
                <button type="button" onClick={() => { setShowForm(false); resetForm(); }} className="flex-1 px-4 py-2.5 border rounded-lg hover:bg-gray-50 transition-colors dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-700 text-sm sm:text-base">
                  Отмена
                </button>
                <button type="submit" className="flex-1 px-4 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm sm:text-base">
                  {editingReminder ? 'Сохранить' : 'Создать'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Reminders List */}
      {reminders.length === 0 ? (
        <div className={`${cardClass} p-8 sm:p-12 text-center`}>
          <Bell className="w-10 h-10 sm:w-12 sm:h-12 text-gray-300 dark:text-gray-600 mx-auto mb-4" />
          <p className={mutedClass}>Нет активных напоминаний</p>
          <p className={`text-sm ${mutedClass} mt-2`}>
            {isEmailVerified ? 'Создайте напоминание о платеже' : 'Подтвердите email чтобы создавать напоминания'}
          </p>
        </div>
      ) : (
        <div className="space-y-3 sm:space-y-4">
          {reminders.map((reminder) => (
            <div key={reminder.id} className={`${cardClass} ${reminder.is_completed ? 'opacity-50' : ''}`}>
              <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
                <div className="flex items-start gap-3 sm:gap-4">
                  <div className={`p-2 sm:p-3 rounded-lg shrink-0 ${reminder.is_completed ? 'bg-green-100 dark:bg-green-900/30' : 'bg-blue-100 dark:bg-blue-900/30'}`}>
                    {reminder.is_completed ? <Check className="w-5 h-5 sm:w-6 sm:h-6 text-green-600 dark:text-green-400" /> : <Bell className="w-5 h-5 sm:w-6 sm:h-6 text-blue-600 dark:text-blue-400" />}
                  </div>
                  <div className="min-w-0">
                    <h3 className={`font-semibold text-sm sm:text-base ${titleClass} truncate`}>{reminder.title}</h3>
                    {reminder.description && <p className="text-gray-500 text-xs sm:text-sm mt-1 dark:text-gray-400 line-clamp-2">{reminder.description}</p>}
                    <div className={`flex flex-wrap items-center gap-2 sm:gap-4 mt-2 text-xs sm:text-sm ${mutedClass}`}>
                      <span className="flex items-center gap-1">
                        <Calendar className="w-3 h-3 sm:w-4 sm:h-4" />
                        {formatDate(reminder.next_reminder_date)}
                      </span>
                      <span className="flex items-center gap-1">
                        <Clock className="w-3 h-3 sm:w-4 sm:h-4" />
                        {FREQUENCY_LABELS[reminder.frequency] || reminder.frequency}
                      </span>
                    </div>
                  </div>
                </div>
                <div className="flex items-center justify-between sm:justify-end gap-2 sm:gap-4 mt-2 sm:mt-0">
                  {reminder.amount && <span className={`text-base sm:text-xl font-bold ${titleClass}`}>{formatCurrency(reminder.amount)}</span>}
                  <div className="flex gap-1">
                    {!reminder.is_completed && (
                      <>
                        <button onClick={() => openEditForm(reminder)} className="p-1.5 sm:p-2 text-gray-400 hover:text-blue-500 hover:bg-blue-50 rounded-lg transition-colors dark:hover:bg-blue-900/30">
                          <Edit2 className="w-4 h-4 sm:w-5 sm:h-5" />
                        </button>
                        <button onClick={() => handleComplete(reminder.id)} className="p-1.5 sm:p-2 text-gray-400 hover:text-green-500 hover:bg-green-50 rounded-lg transition-colors dark:hover:bg-green-900/30">
                          <Check className="w-4 h-4 sm:w-5 sm:h-5" />
                        </button>
                      </>
                    )}
                    <button onClick={() => handleDelete(reminder.id)} className="p-1.5 sm:p-2 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors dark:hover:bg-red-900/30">
                      <Trash2 className="w-4 h-4 sm:w-5 sm:h-5" />
                    </button>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Архив */}
      <div className="mt-6">
        <button onClick={toggleArchive} className="flex items-center gap-2 text-gray-500 hover:text-gray-700 transition-colors dark:text-gray-400 dark:hover:text-gray-300 text-sm sm:text-base">
          <Archive className="w-4 h-4 sm:w-5 sm:h-5" />
          <span className="font-medium">Архив</span>
          <ChevronDown className={`w-4 h-4 transition-transform ${showArchive ? 'rotate-180' : ''}`} />
          {archiveLoaded && <span className={`text-xs sm:text-sm ${mutedClass}`}>({archivedReminders.length})</span>}
        </button>

        {showArchive && (
          <div className="mt-4 space-y-3">
            {archivedReminders.length === 0 ? (
              <p className={`text-xs sm:text-sm ${mutedClass} pl-7`}>Нет архивных напоминаний</p>
            ) : (
              archivedReminders.map((reminder) => (
                <div key={reminder.id} className="bg-gray-50 rounded-xl border border-gray-200 p-3 sm:p-4 opacity-70 dark:bg-gray-700 dark:border-gray-600">
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-start gap-2 sm:gap-3 min-w-0">
                      <div className="p-1.5 sm:p-2 rounded-lg bg-green-100 dark:bg-green-900/30 shrink-0">
                        <Check className="w-4 h-4 sm:w-5 sm:h-5 text-green-600 dark:text-green-400" />
                      </div>
                      <div className="min-w-0">
                        <h3 className="font-medium text-sm text-gray-600 dark:text-gray-300 truncate">{reminder.title}</h3>
                        {reminder.description && <p className={`text-xs mt-1 ${mutedClass} truncate`}>{reminder.description}</p>}
                        <div className={`flex flex-wrap items-center gap-2 sm:gap-4 mt-1 text-xs ${mutedClass}`}>
                          <span className="flex items-center gap-1"><Calendar className="w-3 h-3" />{formatDate(reminder.next_reminder_date)}</span>
                          <span className="flex items-center gap-1"><Clock className="w-3 h-3" />{FREQUENCY_LABELS[reminder.frequency] || reminder.frequency}</span>
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-2 sm:gap-3 shrink-0">
                      {reminder.amount && <span className="text-sm sm:text-lg font-semibold text-gray-500 dark:text-gray-400">{formatCurrency(reminder.amount)}</span>}
                      <button onClick={() => handleDelete(reminder.id)} className="p-1.5 sm:p-2 text-red-400 hover:bg-red-50 rounded-lg transition-colors dark:hover:bg-red-900/30">
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        )}
      </div>
    </div>
  );
}

import { useState, useEffect } from 'react';
import { Plus, Bell, Trash2, Check, Clock, Calendar, Edit2, ChevronDown, Archive } from 'lucide-react';
import { api, Reminder, ReminderCreate } from '../api';

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

export default function Reminders() {
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

  const cardClass = "bg-white rounded-xl shadow-sm p-6 dark:bg-gray-800";
  const titleClass = "text-gray-800 dark:text-white";
  const labelClass = "block text-sm font-medium text-gray-700 mb-1 dark:text-gray-300";
  const inputClass = "w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white dark:placeholder-gray-400";
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

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 dark:border-blue-400"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className={`text-2xl font-bold ${titleClass}`}>Напоминания</h2>
        <button onClick={openCreateForm} className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors">
          <Plus className="w-4 h-4" />
          Добавить
        </button>
      </div>

      {/* Form Modal */}
      {showForm && (
        <div className="fixed top-0 left-0 right-0 bottom-0 bg-black/50 flex items-center justify-center" style={{ zIndex: 9999 }} onClick={() => { setShowForm(false); resetForm(); }}>
          <div className="bg-white rounded-xl shadow-xl w-full max-w-md mx-4 p-6 max-h-[90vh] overflow-y-auto dark:bg-gray-800" onClick={(e) => e.stopPropagation()}>
            <h3 className={`text-xl font-semibold ${titleClass} mb-4`}>
              {editingReminder ? 'Редактировать напоминание' : 'Новое напоминание'}
            </h3>
            <form onSubmit={handleSubmit} className="space-y-4">
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
              <div className="grid grid-cols-2 gap-3">
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
                <button type="button" onClick={() => { setShowForm(false); resetForm(); }} className="flex-1 px-4 py-2 border rounded-lg hover:bg-gray-50 transition-colors dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-700">
                  Отмена
                </button>
                <button type="submit" className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors">
                  {editingReminder ? 'Сохранить' : 'Создать'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Reminders List */}
      {reminders.length === 0 ? (
        <div className={`${cardClass} p-12 text-center`}>
          <Bell className="w-12 h-12 text-gray-300 dark:text-gray-600 mx-auto mb-4" />
          <p className={mutedClass}>Нет активных напоминаний</p>
          <p className={`text-sm ${mutedClass} mt-2`}>Создайте напоминание о платеже</p>
        </div>
      ) : (
        <div className="space-y-4">
          {reminders.map((reminder) => (
            <div key={reminder.id} className={`${cardClass} ${reminder.is_completed ? 'opacity-50' : ''}`}>
              <div className="flex items-start justify-between">
                <div className="flex items-start gap-4">
                  <div className={`p-3 rounded-lg ${reminder.is_completed ? 'bg-green-100 dark:bg-green-900/30' : 'bg-blue-100 dark:bg-blue-900/30'}`}>
                    {reminder.is_completed ? <Check className="w-6 h-6 text-green-600 dark:text-green-400" /> : <Bell className="w-6 h-6 text-blue-600 dark:text-blue-400" />}
                  </div>
                  <div>
                    <h3 className={`font-semibold ${titleClass}`}>{reminder.title}</h3>
                    {reminder.description && <p className="text-gray-500 text-sm mt-1 dark:text-gray-400">{reminder.description}</p>}
                    <div className={`flex items-center gap-4 mt-2 text-sm ${mutedClass}`}>
                      <span className="flex items-center gap-1">
                        <Calendar className="w-4 h-4" />
                        {formatDate(reminder.next_reminder_date)} {new Date(reminder.next_reminder_date).toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })}
                      </span>
                      <span className="flex items-center gap-1">
                        <Clock className="w-4 h-4" />
                        {FREQUENCY_LABELS[reminder.frequency] || reminder.frequency}
                      </span>
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-4">
                  {reminder.amount && <span className={`text-xl font-bold ${titleClass}`}>{formatCurrency(reminder.amount)}</span>}
                  <div className="flex gap-1">
                    {!reminder.is_completed && (
                      <>
                        <button onClick={() => openEditForm(reminder)} className="p-2 text-gray-400 hover:text-blue-500 hover:bg-blue-50 rounded-lg transition-colors dark:hover:bg-blue-900/30" title="Редактировать">
                          <Edit2 className="w-5 h-5" />
                        </button>
                        <button onClick={() => handleComplete(reminder.id)} className="p-2 text-gray-400 hover:text-green-500 hover:bg-green-50 rounded-lg transition-colors dark:hover:bg-green-900/30" title="Выполнено">
                          <Check className="w-5 h-5" />
                        </button>
                      </>
                    )}
                    <button onClick={() => handleDelete(reminder.id)} className="p-2 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors dark:hover:bg-red-900/30" title="Удалить">
                      <Trash2 className="w-5 h-5" />
                    </button>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Архив напоминаний */}
      <div className="mt-6">
        <button onClick={toggleArchive} className="flex items-center gap-2 text-gray-500 hover:text-gray-700 transition-colors dark:text-gray-400 dark:hover:text-gray-300">
          <Archive className="w-5 h-5" />
          <span className="font-medium">Архив напоминаний</span>
          <ChevronDown className={`w-4 h-4 transition-transform ${showArchive ? 'rotate-180' : ''}`} />
          {archiveLoaded && <span className={`text-sm ${mutedClass}`}>({archivedReminders.length})</span>}
        </button>

        {showArchive && (
          <div className="mt-4 space-y-3">
            {archivedReminders.length === 0 ? (
              <p className={`text-sm ${mutedClass} pl-7`}>Нет архивных напоминаний</p>
            ) : (
              archivedReminders.map((reminder) => (
                <div key={reminder.id} className="bg-gray-50 rounded-xl border border-gray-200 p-4 opacity-70 dark:bg-gray-700 dark:border-gray-600">
                  <div className="flex items-start justify-between">
                    <div className="flex items-start gap-3">
                      <div className="p-2 rounded-lg bg-green-100 dark:bg-green-900/30">
                        <Check className="w-5 h-5 text-green-600 dark:text-green-400" />
                      </div>
                      <div>
                        <h3 className="font-medium text-gray-600 dark:text-gray-300">{reminder.title}</h3>
                        {reminder.description && <p className={`text-sm mt-1 ${mutedClass}`}>{reminder.description}</p>}
                        <div className={`flex items-center gap-4 mt-1 text-xs ${mutedClass}`}>
                          <span className="flex items-center gap-1"><Calendar className="w-3 h-3" />{formatDate(reminder.next_reminder_date)}</span>
                          <span className="flex items-center gap-1"><Clock className="w-3 h-3" />{FREQUENCY_LABELS[reminder.frequency] || reminder.frequency}</span>
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      {reminder.amount && <span className="text-lg font-semibold text-gray-500 dark:text-gray-400">{formatCurrency(reminder.amount)}</span>}
                      <button onClick={() => handleDelete(reminder.id)} className="p-2 text-red-400 hover:bg-red-50 rounded-lg transition-colors dark:hover:bg-red-900/30" title="Удалить">
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
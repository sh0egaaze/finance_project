import { useState, useEffect } from 'react';
import { Plus, Bell, Trash2, Check, Clock, Calendar } from 'lucide-react';
import { api, Reminder, ReminderCreate } from '../api';

const formatCurrency = (value: number) => {
  return new Intl.NumberFormat('ru-RU', {
    style: 'currency',
    currency: 'RUB',
    minimumFractionDigits: 0,
  }).format(value);
};

const formatDate = (dateString: string) => {
  return new Date(dateString).toLocaleDateString('ru-RU', {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  });
};

const FREQUENCY_LABELS: Record<string, string> = {
  once: 'Один раз',
  daily: 'Ежедневно',
  weekly: 'Еженедельно',
  monthly: 'Ежемесячно',
  custom: 'Свой интервал',
};

export default function Reminders() {
  const [reminders, setReminders] = useState<Reminder[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [formData, setFormData] = useState<ReminderCreate>({
    title: '',
    description: '',
    amount: undefined,
    frequency: 'once',
    next_reminder_date: new Date().toISOString().split('T')[0],
  });

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

  useEffect(() => {
    loadReminders();
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.createReminder({
        ...formData,
        next_reminder_date: new Date(formData.next_reminder_date).toISOString(),
      });
      setShowForm(false);
      setFormData({
        title: '',
        description: '',
        amount: undefined,
        frequency: 'once',
        next_reminder_date: new Date().toISOString().split('T')[0],
      });
      loadReminders();
    } catch (error) {
      console.error('Error creating reminder:', error);
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm('Удалить напоминание?')) return;
    try {
      await api.deleteReminder(id);
      loadReminders();
    } catch (error) {
      console.error('Error deleting reminder:', error);
    }
  };

  const handleComplete = async (id: number) => {
    try {
      await api.completeReminder(id);
      loadReminders();
    } catch (error) {
      console.error('Error completing reminder:', error);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-gray-800">Напоминания</h2>
        <button
          onClick={() => setShowForm(true)}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
        >
          <Plus className="w-4 h-4" />
          Добавить
        </button>
      </div>

      {/* Add Form Modal */}
      {showForm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-md mx-4 p-6">
            <h3 className="text-xl font-semibold text-gray-800 mb-4">Новое напоминание</h3>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Название *
                </label>
                <input
                  type="text"
                  value={formData.title}
                  onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                  placeholder="Например: Оплата ЖКХ"
                  className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Описание
                </label>
                <input
                  type="text"
                  value={formData.description || ''}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  placeholder="Дополнительная информация"
                  className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Сумма (необязательно)
                </label>
                <input
                  type="number"
                  value={formData.amount || ''}
                  onChange={(e) => setFormData({ ...formData, amount: e.target.value ? Number(e.target.value) : undefined })}
                  placeholder="Если сумма фиксированная"
                  className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Периодичность
                </label>
                <select
                  value={formData.frequency}
                  onChange={(e) => setFormData({ ...formData, frequency: e.target.value })}
                  className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                >
                  <option value="once">Один раз</option>
                  <option value="daily">Ежедневно</option>
                  <option value="weekly">Еженедельно</option>
                  <option value="monthly">Ежемесячно</option>
                  <option value="custom">Свой интервал</option>
                </select>
              </div>

              {formData.frequency === 'custom' && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Интервал (дней)
                  </label>
                  <input
                    type="number"
                    value={formData.interval_days || ''}
                    onChange={(e) => setFormData({ ...formData, interval_days: Number(e.target.value) })}
                    placeholder="Например: 30"
                    className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              )}

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Дата напоминания
                </label>
                <input
                  type="date"
                  value={formData.next_reminder_date}
                  onChange={(e) => setFormData({ ...formData, next_reminder_date: e.target.value })}
                  className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                  required
                />
              </div>

              <div className="flex gap-3 pt-4">
                <button
                  type="button"
                  onClick={() => setShowForm(false)}
                  className="flex-1 px-4 py-2 border rounded-lg hover:bg-gray-50 transition-colors"
                >
                  Отмена
                </button>
                <button
                  type="submit"
                  className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                >
                  Создать
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Reminders List */}
      {reminders.length === 0 ? (
        <div className="bg-white rounded-xl shadow-sm p-12 text-center">
          <Bell className="w-12 h-12 text-gray-300 mx-auto mb-4" />
          <p className="text-gray-400">Нет активных напоминаний</p>
          <p className="text-sm text-gray-400 mt-2">Создайте напоминание о платеже</p>
        </div>
      ) : (
        <div className="space-y-4">
          {reminders.map((reminder) => (
            <div
              key={reminder.id}
              className={`bg-white rounded-xl shadow-sm p-6 ${
                reminder.is_completed ? 'opacity-50' : ''
              }`}
            >
              <div className="flex items-start justify-between">
                <div className="flex items-start gap-4">
                  <div className={`p-3 rounded-lg ${
                    reminder.is_completed ? 'bg-green-100' : 'bg-blue-100'
                  }`}>
                    {reminder.is_completed ? (
                      <Check className="w-6 h-6 text-green-600" />
                    ) : (
                      <Bell className="w-6 h-6 text-blue-600" />
                    )}
                  </div>
                  <div>
                    <h3 className="font-semibold text-gray-800">{reminder.title}</h3>
                    {reminder.description && (
                      <p className="text-gray-500 text-sm mt-1">{reminder.description}</p>
                    )}
                    <div className="flex items-center gap-4 mt-2 text-sm text-gray-400">
                      <span className="flex items-center gap-1">
                        <Calendar className="w-4 h-4" />
                        {formatDate(reminder.next_reminder_date)}
                      </span>
                      <span className="flex items-center gap-1">
                        <Clock className="w-4 h-4" />
                        {FREQUENCY_LABELS[reminder.frequency] || reminder.frequency}
                      </span>
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-4">
                  {reminder.amount && (
                    <span className="text-xl font-bold text-gray-800">
                      {formatCurrency(reminder.amount)}
                    </span>
                  )}
                  <div className="flex gap-2">
                    {!reminder.is_completed && (
                      <button
                        onClick={() => handleComplete(reminder.id)}
                        className="p-2 text-green-600 hover:bg-green-50 rounded-lg transition-colors"
                        title="Выполнено"
                      >
                        <Check className="w-5 h-5" />
                      </button>
                    )}
                    <button
                      onClick={() => handleDelete(reminder.id)}
                      className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                      title="Удалить"
                    >
                      <Trash2 className="w-5 h-5" />
                    </button>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

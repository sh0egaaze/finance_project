import { useState, useEffect } from 'react';
import { User, Bell, Shield, Download, Link, Unlink, CheckCircle, AlertCircle, LogOut } from 'lucide-react';
import { api, User as UserType, TBankStatus } from '../api';

interface SettingsProps {
  user: UserType;
  onLogout: () => void;
}

export default function Settings({ user, onLogout }: SettingsProps) {
  const [fullName, setFullName] = useState(user.full_name || '');
  const [emailNotifications, setEmailNotifications] = useState(user.email_notifications);
  const [notificationEmail, setNotificationEmail] = useState(user.notification_email || '');
  const [isSaving, setIsSaving] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  
  // T-Bank
  const [tbankStatus, setTbankStatus] = useState<TBankStatus | null>(null);
  const [tbankToken, setTbankToken] = useState('');
  const [isConnecting, setIsConnecting] = useState(false);
  
  // Password
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');

  useEffect(() => {
    loadTBankStatus();
  }, []);

  const loadTBankStatus = async () => {
    try {
      const status = await api.getTBankStatus();
      setTbankStatus(status);
    } catch (error) {
      console.error('Error loading T-Bank status:', error);
    }
  };

  const handleSaveProfile = async () => {
    setIsSaving(true);
    setMessage(null);
    try {
      await api.updateProfile({
        full_name: fullName,
        email_notifications: emailNotifications,
        notification_email: notificationEmail || undefined,
      });
      setMessage({ type: 'success', text: 'Профиль сохранён' });
    } catch (error) {
      setMessage({ type: 'error', text: 'Ошибка сохранения' });
    } finally {
      setIsSaving(false);
    }
  };

  const handleChangePassword = async () => {
    if (newPassword !== confirmPassword) {
      setMessage({ type: 'error', text: 'Пароли не совпадают' });
      return;
    }
    if (newPassword.length < 6) {
      setMessage({ type: 'error', text: 'Пароль должен быть минимум 6 символов' });
      return;
    }
    
    setIsSaving(true);
    setMessage(null);
    try {
      await api.changePassword(currentPassword, newPassword);
      setMessage({ type: 'success', text: 'Пароль изменён' });
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
    } catch {
      setMessage({ type: 'error', text: 'Неверный текущий пароль' });
    } finally {
      setIsSaving(false);
    }
  };

  const handleConnectTBank = async () => {
    if (!tbankToken.trim()) return;
    
    setIsConnecting(true);
    setMessage(null);
    try {
      const status = await api.connectTBank(tbankToken);
      setTbankStatus(status);
      setTbankToken('');
      setMessage({ type: 'success', text: 'Т-Банк подключён!' });
    } catch {
      setMessage({ type: 'error', text: 'Ошибка подключения. Проверьте токен.' });
    } finally {
      setIsConnecting(false);
    }
  };

  const handleDisconnectTBank = async () => {
    if (!confirm('Отключить Т-Банк?')) return;
    
    try {
      await api.disconnectTBank();
      setTbankStatus({ connected: false, account_id: null, balance: null, currency: 'RUB', last_sync: null, accounts_count: 0 });
      setMessage({ type: 'success', text: 'Т-Банк отключён' });
    } catch {
      setMessage({ type: 'error', text: 'Ошибка отключения' });
    }
  };

  return (
    <div className="space-y-6 max-w-2xl">
      <h2 className="text-2xl font-bold text-gray-800">Настройки</h2>

      {message && (
        <div className={`p-4 rounded-lg flex items-center gap-2 ${
          message.type === 'success' ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'
        }`}>
          {message.type === 'success' ? <CheckCircle className="w-5 h-5" /> : <AlertCircle className="w-5 h-5" />}
          {message.text}
        </div>
      )}

      {/* Profile */}
      <div className="bg-white rounded-xl shadow-sm p-6">
        <div className="flex items-center gap-3 mb-4">
          <User className="w-5 h-5 text-gray-400" />
          <h3 className="text-lg font-semibold text-gray-800">Профиль</h3>
        </div>
        
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
            <input
              type="email"
              value={user.email}
              disabled
              className="w-full px-4 py-2 border rounded-lg bg-gray-50 text-gray-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Имя</label>
            <input
              type="text"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              placeholder="Ваше имя"
              className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <button
            onClick={handleSaveProfile}
            disabled={isSaving}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
          >
            {isSaving ? 'Сохранение...' : 'Сохранить'}
          </button>
        </div>
      </div>

      {/* T-Bank */}
      <div className="bg-white rounded-xl shadow-sm p-6">
        <div className="flex items-center gap-3 mb-4">
          <Link className="w-5 h-5 text-gray-400" />
          <h3 className="text-lg font-semibold text-gray-800">Т-Банк</h3>
        </div>

        {tbankStatus?.connected ? (
          <div className="space-y-4">
            <div className="flex items-center gap-2 text-green-600">
              <CheckCircle className="w-5 h-5" />
              <span>Подключено</span>
            </div>
            {tbankStatus.balance !== null && (
              <p className="text-gray-600">
                Баланс: {new Intl.NumberFormat('ru-RU', { style: 'currency', currency: tbankStatus.currency }).format(tbankStatus.balance)}
              </p>
            )}
            {tbankStatus.last_sync && (
              <p className="text-sm text-gray-400">
                Последняя синхронизация: {new Date(tbankStatus.last_sync).toLocaleString('ru-RU')}
              </p>
            )}
            <button
              onClick={handleDisconnectTBank}
              className="flex items-center gap-2 px-4 py-2 border border-red-300 text-red-600 rounded-lg hover:bg-red-50 transition-colors"
            >
              <Unlink className="w-4 h-4" />
              Отключить
            </button>
          </div>
        ) : (
          <div className="space-y-4">
            <p className="text-gray-500 text-sm">
              Подключите Т-Банк для автоматической загрузки транзакций
            </p>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Токен API</label>
              <input
                type="password"
                value={tbankToken}
                onChange={(e) => setTbankToken(e.target.value)}
                placeholder="t.xxxxx..."
                className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
              />
              <p className="text-xs text-gray-400 mt-1">
                Получите токен на{' '}
                <a href="https://www.tinkoff.ru/invest/settings/" target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">
                  tinkoff.ru/invest/settings
                </a>
              </p>
            </div>
            <button
              onClick={handleConnectTBank}
              disabled={isConnecting || !tbankToken.trim()}
              className="flex items-center gap-2 px-4 py-2 bg-yellow-500 text-white rounded-lg hover:bg-yellow-600 disabled:opacity-50 transition-colors"
            >
              <Link className="w-4 h-4" />
              {isConnecting ? 'Подключение...' : 'Подключить'}
            </button>
          </div>
        )}
      </div>

      {/* Notifications */}
      <div className="bg-white rounded-xl shadow-sm p-6">
        <div className="flex items-center gap-3 mb-4">
          <Bell className="w-5 h-5 text-gray-400" />
          <h3 className="text-lg font-semibold text-gray-800">Уведомления</h3>
        </div>
        
        <div className="space-y-4">
          <label className="flex items-center gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={emailNotifications}
              onChange={(e) => setEmailNotifications(e.target.checked)}
              className="w-5 h-5 text-blue-600 rounded"
            />
            <span>Получать уведомления по email</span>
          </label>
          {emailNotifications && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Email для уведомлений</label>
              <input
                type="email"
                value={notificationEmail}
                onChange={(e) => setNotificationEmail(e.target.value)}
                placeholder={user.email}
                className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
              />
            </div>
          )}
          <button
            onClick={handleSaveProfile}
            disabled={isSaving}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
          >
            Сохранить
          </button>
        </div>
      </div>

      {/* Security */}
      <div className="bg-white rounded-xl shadow-sm p-6">
        <div className="flex items-center gap-3 mb-4">
          <Shield className="w-5 h-5 text-gray-400" />
          <h3 className="text-lg font-semibold text-gray-800">Безопасность</h3>
        </div>
        
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Текущий пароль</label>
            <input
              type="password"
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
              className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Новый пароль</label>
            <input
              type="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Подтверждение пароля</label>
            <input
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <button
            onClick={handleChangePassword}
            disabled={isSaving || !currentPassword || !newPassword}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
          >
            Сменить пароль
          </button>
        </div>
      </div>

      {/* Export */}
      <div className="bg-white rounded-xl shadow-sm p-6">
        <div className="flex items-center gap-3 mb-4">
          <Download className="w-5 h-5 text-gray-400" />
          <h3 className="text-lg font-semibold text-gray-800">Экспорт данных</h3>
        </div>
        
        <p className="text-gray-500 text-sm mb-4">
          Скачайте все ваши транзакции в формате CSV
        </p>
        <button className="px-4 py-2 border rounded-lg hover:bg-gray-50 transition-colors">
          Скачать CSV
        </button>
      </div>

      {/* Logout */}
      <div className="bg-white rounded-xl shadow-sm p-6">
        <button
          onClick={onLogout}
          className="flex items-center gap-2 px-4 py-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
        >
          <LogOut className="w-5 h-5" />
          Выйти из аккаунта
        </button>
      </div>
    </div>
  );
}

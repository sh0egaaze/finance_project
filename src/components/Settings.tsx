import { useState, useEffect } from 'react';
import { User as UserIcon, Bell, Shield, Link, Unlink, CheckCircle, AlertCircle, LogOut, Sun, Moon, Monitor, Mail, RefreshCw } from 'lucide-react';
import { api, User as UserType, TBankStatus } from '../api';

interface SettingsProps {
  user: UserType;
  onLogout: () => void;
  onUserUpdate?: (user: UserType) => void;
}

function Message({ message }: { message: { type: 'success' | 'error'; text: string } | null }) {
  if (!message) return null;
  return (
    <div className={`p-3 rounded-lg flex items-center gap-2 mb-4 text-sm ${
      message.type === 'success' ? 'bg-green-50 text-green-700 dark:bg-green-900/30 dark:text-green-400' : 'bg-red-50 text-red-700 dark:bg-red-900/30 dark:text-red-400'
    }`}>
      {message.type === 'success' ? <CheckCircle className="w-4 h-4 shrink-0" /> : <AlertCircle className="w-4 h-4 shrink-0" />}
      {message.text}
    </div>
  );
}

type ThemeMode = 'light' | 'dark' | 'system';

function getStoredTheme(): ThemeMode {
  return (localStorage.getItem('theme') as ThemeMode) || 'system';
}

function applyTheme(mode: ThemeMode) {
  const root = document.documentElement;
  if (mode === 'dark' || (mode === 'system' && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
    root.classList.add('dark');
  } else {
    root.classList.remove('dark');
  }
  localStorage.setItem('theme', mode);
}

export default function Settings({ user, onLogout, onUserUpdate }: SettingsProps) {
  const [fullName, setFullName] = useState(user.full_name || '');
  const [emailNotifications, setEmailNotifications] = useState(user.email_notifications);
  const [notificationEmail, setNotificationEmail] = useState(user.notification_email || '');
  const [isSaving, setIsSaving] = useState(false);
  const [themeMode, setThemeMode] = useState<ThemeMode>(getStoredTheme);

  const [profileMessage, setProfileMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  const [tbankMessage, setTbankMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  const [notifyMessage, setNotifyMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  const [passwordMessage, setPasswordMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  const [emailVerifyMessage, setEmailVerifyMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const [tbankStatus, setTbankStatus] = useState<TBankStatus | null>(null);
  const [tbankToken, setTbankToken] = useState('');
  const [isConnecting, setIsConnecting] = useState(false);
  const [isResending, setIsResending] = useState(false);
  const [isCheckingVerification, setIsCheckingVerification] = useState(false);

  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');

  useEffect(() => {
    loadTBankStatus();
  }, []);

  useEffect(() => {
    applyTheme(themeMode);
    const mq = window.matchMedia('(prefers-color-scheme: dark)');
    const handler = () => { if (themeMode === 'system') applyTheme('system'); };
    mq.addEventListener('change', handler);
    return () => mq.removeEventListener('change', handler);
  }, [themeMode]);

  const handleThemeChange = (mode: ThemeMode) => {
    setThemeMode(mode);
    applyTheme(mode);
  };

  const loadTBankStatus = async () => {
    try {
      const status = await api.getTBankStatus();
      setTbankStatus(status);
    } catch (error) {
      console.error('Error loading T-Bank status:', error);
    }
  };

  const handleResendVerification = async () => {
    setIsResending(true);
    setEmailVerifyMessage(null);
    try {
      await api.resendVerification(user.email);
      setEmailVerifyMessage({ type: 'success', text: 'Письмо отправлено! Проверьте почту.' });
    } catch (error: any) {
      const detail = error?.response?.data?.detail || 'Ошибка отправки. Попробуйте позже.';
      setEmailVerifyMessage({ type: 'error', text: detail });
    } finally {
      setIsResending(false);
    }
  };

  const handleCheckVerification = async () => {
    setIsCheckingVerification(true);
    setEmailVerifyMessage(null);
    try {
      const updatedUser = await api.checkEmailVerification();
      if (onUserUpdate) onUserUpdate(updatedUser);
      if (updatedUser.email_verified) {
        setEmailVerifyMessage({ type: 'success', text: 'Email подтверждён!' });
      } else {
        setEmailVerifyMessage({ type: 'error', text: 'Email ещё не подтверждён. Проверьте почту.' });
      }
    } catch {
      setEmailVerifyMessage({ type: 'error', text: 'Ошибка проверки статуса' });
    } finally {
      setIsCheckingVerification(false);
    }
  };

  const handleSaveProfile = async () => {
    setIsSaving(true);
    setProfileMessage(null);
    try {
      const updatedUser = await api.updateProfile({
        full_name: fullName,
        email_notifications: emailNotifications,
        notification_email: notificationEmail || undefined,
      });
      if (onUserUpdate) onUserUpdate(updatedUser);
      setProfileMessage({ type: 'success', text: 'Профиль сохранён' });
    } catch {
      setProfileMessage({ type: 'error', text: 'Ошибка сохранения' });
    } finally {
      setIsSaving(false);
    }
  };

  const handleSaveNotifications = async () => {
    setIsSaving(true);
    setNotifyMessage(null);
    try {
      const updatedUser = await api.updateProfile({
        email_notifications: emailNotifications,
        notification_email: notificationEmail || undefined,
      });
      if (onUserUpdate) onUserUpdate(updatedUser);
      setNotifyMessage({ type: 'success', text: 'Настройки сохранены' });
    } catch {
      setNotifyMessage({ type: 'error', text: 'Ошибка сохранения' });
    } finally {
      setIsSaving(false);
    }
  };

  const handleChangePassword = async () => {
    if (newPassword !== confirmPassword) {
      setPasswordMessage({ type: 'error', text: 'Пароли не совпадают' });
      return;
    }
    if (newPassword.length < 12) {
      setPasswordMessage({ type: 'error', text: 'Пароль должен быть минимум 12 символов' });
      return;
    }
    setIsSaving(true);
    setPasswordMessage(null);
    try {
      await api.changePassword(currentPassword, newPassword);
      setPasswordMessage({ type: 'success', text: 'Пароль изменён' });
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
    } catch (error: any) {
      const detail = error?.response?.data?.detail || 'Неверный текущий пароль';
      setPasswordMessage({ type: 'error', text: detail });
    } finally {
      setIsSaving(false);
    }
  };

  const handleConnectTBank = async () => {
    if (!tbankToken.trim()) return;
    setIsConnecting(true);
    setTbankMessage(null);
    try {
      const status = await api.connectTBank(tbankToken);
      setTbankStatus(status);
      setTbankToken('');
      setTbankMessage({ type: 'success', text: 'Т-Банк подключён!' });
    } catch {
      setTbankMessage({ type: 'error', text: 'Ошибка подключения. Проверьте токен.' });
    } finally {
      setIsConnecting(false);
    }
  };

  const handleDisconnectTBank = async () => {
    if (!confirm('Отключить Т-Банк?')) return;
    try {
      await api.disconnectTBank();
      setTbankStatus({ connected: false, account_id: null, balance: null, message: 'Т-Банк отключён' });
      setTbankMessage({ type: 'success', text: 'Т-Банк отключён' });
    } catch {
      setTbankMessage({ type: 'error', text: 'Ошибка отключения' });
    }
  };

  const inputClass = "w-full px-4 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white dark:placeholder-gray-400";
  const cardClass = "bg-white rounded-xl shadow-sm border border-gray-100 p-6 dark:bg-gray-800 dark:border-gray-700";
  const labelClass = "block text-sm font-medium text-gray-700 mb-1 dark:text-gray-300";
  const btnPrimary = "px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors text-sm font-medium";

  return (
    <div className="space-y-6 max-w-3xl mx-auto">
      <h2 className="text-2xl font-bold text-gray-800 dark:text-white">Настройки</h2>

      {/* Баннер верификации email */}
      {!user.email_verified && (
        <div className="bg-amber-50 border border-amber-200 rounded-xl p-5 dark:bg-amber-900/20 dark:border-amber-800">
          <div className="flex items-start gap-4">
            <div className="w-10 h-10 bg-amber-100 rounded-full flex items-center justify-center shrink-0 dark:bg-amber-800">
              <Mail className="w-5 h-5 text-amber-600 dark:text-amber-400" />
            </div>
            <div className="flex-1">
              <h3 className="text-base font-semibold text-amber-800 dark:text-amber-300">
                Подтвердите ваш email
              </h3>
              <p className="text-sm text-amber-700 mt-1 dark:text-amber-400">
                На адрес <strong>{user.email}</strong> было отправлено письмо с ссылкой для подтверждения. 
                Без подтверждения некоторые функции недоступны (например, напоминания).
              </p>
              <Message message={emailVerifyMessage} />
              <div className="flex flex-wrap gap-3 mt-3">
                <button
                  onClick={handleResendVerification}
                  disabled={isResending}
                  className="flex items-center gap-2 px-4 py-2 bg-amber-600 text-white rounded-lg hover:bg-amber-700 disabled:opacity-50 transition-colors text-sm font-medium"
                >
                  <Mail className="w-4 h-4" />
                  {isResending ? 'Отправка...' : 'Отправить повторно'}
                </button>
                <button
                  onClick={handleCheckVerification}
                  disabled={isCheckingVerification}
                  className="flex items-center gap-2 px-4 py-2 border border-amber-300 text-amber-700 rounded-lg hover:bg-amber-100 disabled:opacity-50 transition-colors text-sm font-medium dark:border-amber-700 dark:text-amber-400 dark:hover:bg-amber-900/30"
                >
                  <RefreshCw className={`w-4 h-4 ${isCheckingVerification ? 'animate-spin' : ''}`} />
                  {isCheckingVerification ? 'Проверка...' : 'Я подтвердил'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Тема */}
      <div className={cardClass}>
        <div className="flex items-center gap-3 mb-4">
          <Sun className="w-5 h-5 text-gray-400" />
          <h3 className="text-lg font-semibold text-gray-800 dark:text-white">Оформление</h3>
        </div>
        <div className="flex gap-3">
          {([
            { mode: 'light' as ThemeMode, icon: Sun, label: 'Светлая' },
            { mode: 'dark' as ThemeMode, icon: Moon, label: 'Тёмная' },
            { mode: 'system' as ThemeMode, icon: Monitor, label: 'Системная' },
          ]).map(({ mode, icon: Icon, label }) => (
            <button
              key={mode}
              onClick={() => handleThemeChange(mode)}
              className={`flex-1 flex items-center justify-center gap-2 px-4 py-3 rounded-xl border-2 transition-all text-sm font-medium ${
                themeMode === mode
                  ? 'border-blue-500 bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400'
                  : 'border-gray-200 text-gray-500 hover:border-gray-300 dark:border-gray-600 dark:text-gray-400 dark:hover:border-gray-500'
              }`}
            >
              <Icon className="w-5 h-5" />
              {label}
            </button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Профиль */}
        <div className={cardClass}>
          <div className="flex items-center gap-3 mb-4">
            <UserIcon className="w-5 h-5 text-gray-400" />
            <h3 className="text-lg font-semibold text-gray-800 dark:text-white">Профиль</h3>
          </div>
          <Message message={profileMessage} />
          <div className="space-y-4">
            <div>
              <label className={labelClass}>Email</label>
              <div className="relative">
                <input type="email" value={user.email} disabled className={`${inputClass} bg-gray-50 text-gray-500 dark:bg-gray-600 pr-10`} />
                {user.email_verified ? (
                  <CheckCircle className="absolute right-3 top-1/2 -translate-y-1/2 w-5 h-5 text-green-500" title="Email подтверждён" />
                ) : (
                  <AlertCircle className="absolute right-3 top-1/2 -translate-y-1/2 w-5 h-5 text-amber-500" title="Email не подтверждён" />
                )}
              </div>
              <p className={`text-xs mt-1 ${user.email_verified ? 'text-green-600 dark:text-green-400' : 'text-amber-600 dark:text-amber-400'}`}>
                {user.email_verified ? '✓ Email подтверждён' : '⚠ Email не подтверждён'}
              </p>
            </div>
            <div>
              <label className={labelClass}>Имя</label>
              <input type="text" value={fullName} onChange={(e) => setFullName(e.target.value)} placeholder="Ваше имя" className={inputClass} />
            </div>
            <button onClick={handleSaveProfile} disabled={isSaving} className={btnPrimary}>
              {isSaving ? 'Сохранение...' : 'Сохранить'}
            </button>
          </div>
        </div>

        {/* Уведомления */}
        <div className={cardClass}>
          <div className="flex items-center gap-3 mb-4">
            <Bell className="w-5 h-5 text-gray-400" />
            <h3 className="text-lg font-semibold text-gray-800 dark:text-white">Уведомления</h3>
          </div>
          <Message message={notifyMessage} />
          <div className="space-y-4">
            <label className="flex items-center gap-3 cursor-pointer">
              <input type="checkbox" checked={emailNotifications} onChange={(e) => setEmailNotifications(e.target.checked)} className="w-5 h-5 text-blue-600 rounded" />
              <span className="text-gray-700 dark:text-gray-300">Получать уведомления по email</span>
            </label>
            {emailNotifications && !user.email_verified && (
              <div className="p-3 bg-amber-50 rounded-lg text-sm text-amber-700 dark:bg-amber-900/20 dark:text-amber-400">
                ⚠ Для получения уведомлений необходимо подтвердить email
              </div>
            )}
            {emailNotifications && (
              <div>
                <label className={labelClass}>Email для уведомлений</label>
                <input type="email" value={notificationEmail} onChange={(e) => setNotificationEmail(e.target.value)} placeholder={user.email} className={inputClass} />
              </div>
            )}
            <button onClick={handleSaveNotifications} disabled={isSaving} className={btnPrimary}>Сохранить</button>
          </div>
        </div>

        {/* Т-Банк */}
        <div className={cardClass}>
          <div className="flex items-center gap-3 mb-4">
            <Link className="w-5 h-5 text-gray-400" />
            <h3 className="text-lg font-semibold text-gray-800 dark:text-white">Т-Банк</h3>
          </div>
          <Message message={tbankMessage} />
          {tbankStatus?.connected ? (
            <div className="space-y-4">
              <div className="flex items-center gap-2 text-green-600 dark:text-green-400">
                <CheckCircle className="w-5 h-5" />
                <span className="font-medium">Подключено</span>
              </div>
              {tbankStatus.balance !== null && (
                <p className="text-gray-600 dark:text-gray-300">
                  Баланс: {new Intl.NumberFormat('ru-RU', { style: 'currency', currency: tbankStatus.currency || 'RUB' }).format(tbankStatus.balance)}
                </p>
              )}
              <button onClick={handleDisconnectTBank} className="flex items-center gap-2 px-4 py-2 border border-red-300 text-red-600 rounded-lg hover:bg-red-50 transition-colors text-sm dark:border-red-700 dark:text-red-400 dark:hover:bg-red-900/20">
                <Unlink className="w-4 h-4" />
                Отключить
              </button>
            </div>
          ) : (
            <div className="space-y-4">
              <p className="text-gray-500 text-sm dark:text-gray-400">Подключите Т-Банк для автоматической загрузки транзакций</p>
              <div>
                <label className={labelClass}>Токен API</label>
                <input type="password" value={tbankToken} onChange={(e) => setTbankToken(e.target.value)} placeholder="t.xxxxx..." className={inputClass} />
                <p className="text-xs text-gray-400 mt-1">
                  Получите на{' '}
                  <a href="https://www.tbank.ru/invest/settings/" target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">tbank.ru/invest/settings</a>
                </p>
              </div>
              <button onClick={handleConnectTBank} disabled={isConnecting || !tbankToken.trim()} className="flex items-center gap-2 px-4 py-2 bg-yellow-500 text-white rounded-lg hover:bg-yellow-600 disabled:opacity-50 transition-colors text-sm font-medium">
                <Link className="w-4 h-4" />
                {isConnecting ? 'Подключение...' : 'Подключить'}
              </button>
            </div>
          )}
        </div>

        {/* Безопасность */}
        <div className={cardClass}>
          <div className="flex items-center gap-3 mb-4">
            <Shield className="w-5 h-5 text-gray-400" />
            <h3 className="text-lg font-semibold text-gray-800 dark:text-white">Безопасность</h3>
          </div>
          <Message message={passwordMessage} />
          <div className="space-y-4">
            <div>
              <label className={labelClass}>Текущий пароль</label>
              <input type="password" value={currentPassword} onChange={(e) => setCurrentPassword(e.target.value)} className={inputClass} />
            </div>
            <div>
              <label className={labelClass}>Новый пароль</label>
              <input type="password" value={newPassword} onChange={(e) => setNewPassword(e.target.value)} className={inputClass} />
              <p className="text-xs text-gray-400 mt-1">Минимум 12 символов</p>
            </div>
            <div>
              <label className={labelClass}>Подтверждение</label>
              <input type="password" value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} className={inputClass} />
            </div>
            <button onClick={handleChangePassword} disabled={isSaving || !currentPassword || !newPassword} className={btnPrimary}>Сменить пароль</button>
          </div>
        </div>
      </div>

      {/* Выход */}
      <div className={cardClass}>
        <button onClick={onLogout} className="flex items-center gap-2 px-4 py-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors dark:text-red-400 dark:hover:bg-red-900/20">
          <LogOut className="w-5 h-5" />
          Выйти из аккаунта
        </button>
      </div>
    </div>
  );
}
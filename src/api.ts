import axios, { AxiosInstance, AxiosError, InternalAxiosRequestConfig } from 'axios';

const API_URL = import.meta.env.VITE_API_URL ?? '/api/v1';

// Создаём axios instance
const axiosInstance: AxiosInstance = axios.create({
  baseURL: API_URL,
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Интерцептор для добавления токена
axiosInstance.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Интерцептор для обработки ошибок
axiosInstance.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response?.status === 401) {
      const url = error.config?.url || '';
      const isAuthRequest = url.includes('/auth/token') || url.includes('/auth/register');
      if (!isAuthRequest) {
        localStorage.removeItem('token');
        localStorage.removeItem('user');
        window.location.href = '/';
      }
    }
    return Promise.reject(error);
  }
);

// ============ Типы ============

export interface User {
  id: number;
  email: string;
  full_name: string | null;
  is_active: boolean;
  is_superuser: boolean;
  email_verified: boolean;
  email_notifications: boolean;
  notification_email: string | null;
  tbank_connected: boolean;
  created_at: string | null;
  last_login: string | null;
}

export interface Category {
  id: number;
  code: string;
  name: string;
  name_en: string | null;
  icon: string | null;
  color: string | null;
  is_income: boolean;
  is_expense: boolean;
  keywords: string | null;
  is_active: boolean;
  is_system: boolean;
}

export interface Transaction {
  id: number;
  description: string;
  amount: number;
  is_income: boolean;
  category_id: number | null;
  transaction_date: string | null;
  created_at: string | null;
  source?: string;
  is_suspicious?: boolean;
  suspicious_reason?: string;
}

export interface TransactionList {
  items: Transaction[];
  total: number;
  page: number;
  per_page: number;
}

export interface TransactionCreate {
  amount: number;
  description: string;
  is_income: boolean;
  category_id?: number;
  transaction_date?: string;
}

export interface TransactionUpdate {
  amount?: number;
  description?: string;
  is_income?: boolean;
  category_id?: number;
  transaction_date?: string;
}

export interface Reminder {
  id: number;
  user_id: number;
  title: string;
  description: string | null;
  amount: number | null;
  currency: string;
  frequency: string;
  interval_days: number | null;
  repeat_count: number | null;
  current_count: number;
  next_reminder_date: string;
  last_sent_date: string | null;
  is_active: boolean;
  is_completed: boolean;
  send_email: boolean;
  send_push: boolean;
  created_at: string | null;
}

export interface ReminderCreate {
  title: string;
  description?: string;
  amount?: number;
  currency?: string;
  frequency: string;
  interval_days?: number;
  repeat_count?: number;
  next_reminder_date: string;
  send_email?: boolean;
}

export interface DashboardStats {
  total_balance: number;
  total_income: number;
  total_expense: number;
  savings_rate: number;
  transaction_count: number;
}

export interface DashboardData {
  stats: DashboardStats;
  recent_transactions: Transaction[];
  spending_by_category: Array<{
    category_id: number;
    category: string;
    name: string;
    amount: number;
    color: string;
    icon: string;
  }>;
  income_by_category: Array<{
    category_id: number;
    category: string;
    name: string;
    amount: number;
    color: string;
    icon: string;
  }>;
  monthly_trend: Array<{
    date: string;
    income: number;
    expense: number;
  }>;
  upcoming_reminders: Reminder[];
  suspicious_transactions: Transaction[];
}

export interface AnalyticsData {
  spending_by_category: Array<{
    category_id: number;
    category: string;
    name: string;
    amount: number;
    color: string;
  }>;
  income_by_category: Array<{
    category_id: number;
    category: string;
    name: string;
    amount: number;
    color: string;
  }>;
  spending_by_day: Array<{
    day: string;
    amount: number;
  }>;
  spending_trend: Array<{
    date: string;
    income: number;
    expense: number;
  }>;
  income_vs_expense: Array<{
    month: string;
    income: number;
    expense: number;
  }>;
  top_merchants: Array<{
    name: string;
    amount: number;
  }>;
  average_transaction: number;
  total_transactions: number;
  total_expense: number;
  total_income: number;
}

export interface PredictionsData {
  next_month_total: number;
  next_month_expense: number;
  next_month_income: number;
  by_category: Array<{
    category_id: number;
    category: string;
    name: string;
    predicted_amount: number;
    color: string;
    trend: string;
  }>;
  trends: Array<{
    month: string;
    income: number;
    expense: number;
  }>;
  recommendations: string[];
}

export interface SavingTip {
  id: number;
  title: string;
  description: string;
  potential_savings: number | null;
  category: string | null;
  priority: string;
}

export interface SavingTipsData {
  tips: SavingTip[];
  total_potential_savings: number;
}

export interface CurrencyRate {
  currency: string;
  rate: number;
  change: number;
  name: string;
  flag: string;
}

export interface CurrencyRatesData {
  base: string;
  date: string;
  rates: CurrencyRate[];
}

export interface TBankStatus {
  connected: boolean;
  account_id: string | null;
  balance: number | null;
  message: string;
  currency?: string;
  last_sync?: string | null;
  accounts_count?: number;
}

export interface SmartInputResult {
  amount: number | null;
  description: string;
  category_id: number | null;
  category_name: string | null;
  category_confidence: number | null;
  is_income: boolean;
}

// ============ Admin Types ============

export interface AdminUser {
  id: number;
  email: string;
  full_name: string | null;
  is_active: boolean;
  is_superuser: boolean;
  email_verified: boolean;
  email_notifications: boolean;
  tbank_connected: boolean;
  transactions_count: number;
  created_at: string | null;
  last_login: string | null;
}

export interface AdminUserList {
  items: AdminUser[];
  total: number;
}

export interface AdminStats {
  total_users: number;
  active_users: number;
  verified_users: number;
  total_transactions: number;
  total_reminders: number;
  total_categories: number;
  users_today: number;
  users_this_week: number;
  users_this_month: number;
  active_today: number;
  active_this_week: number;
  transactions_today: number;
  transactions_this_week: number;
  transactions_this_month: number;
  tbank_connected_count: number;
}

export interface AuditLogEntry {
  id: number;
  user_id: number | null;
  user_email: string | null;
  action: string;
  entity_type: string | null;
  entity_id: number | null;
  description: string | null;
  status: string | null;
  error_message: string | null;
  created_at: string | null;
}

export interface AuditLogList {
  items: AuditLogEntry[];
  total: number;
}
// ============ API Клиент ============

class ApiClient {
  // Auth
  async register(email: string, password: string, fullName: string): Promise<User> {
    try {
      const response = await axiosInstance.post('/auth/register', {
        email,
        password,
        full_name: fullName,
      });
      return response.data;
    } catch (error: any) {
      const message = error.response?.data?.detail || error.message;
      throw new Error(message);
    }
  }

  async login(email: string, password: string): Promise<{ access_token: string; user: User }> {
    try {
      const formData = new URLSearchParams();
      formData.append('username', email);
      formData.append('password', password);

      const response = await axiosInstance.post('/auth/token', formData, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      });
      return response.data;
    } catch (error: any) {
      const message = error.response?.data?.detail || error.message;
      throw new Error(message);
    }
  }

  async getMe(): Promise<User> {
    const response = await axiosInstance.get('/auth/me');
    return response.data;
  }

  async updateProfile(data: { full_name?: string; email_notifications?: boolean; notification_email?: string }): Promise<User> {
    const response = await axiosInstance.put('/auth/me', data);
    return response.data;
  }

  async changePassword(currentPassword: string, newPassword: string): Promise<void> {
    await axiosInstance.post('/auth/change-password', {
      current_password: currentPassword,
      new_password: newPassword,
    });
  }

  async resendVerification(email: string): Promise<{ message: string }> {
    const response = await axiosInstance.post('/auth/resend-verification', { email });
    return response.data;
  }

  async checkEmailVerification(): Promise<User> {
    const response = await axiosInstance.get('/auth/me');
    return response.data;
  }

  // Categories
  async getCategories(): Promise<Category[]> {
    const response = await axiosInstance.get('/categories');
    return response.data;
  }

  // Transactions
  async getTransactions(params?: {
    offset?: number;
    limit?: number;
    category_id?: number;
    source?: string;
    is_suspicious?: boolean;
    search?: string;
}): Promise<TransactionList> {
    const response = await axiosInstance.get('/transactions', { params });
    const items = Array.isArray(response.data) ? response.data : (response.data.items || []);
    return {
        items,
        total: items.length,
        page: 1,
        per_page: params?.limit || 20,
    };
}

  async getTransaction(id: number): Promise<Transaction> {
    const response = await axiosInstance.get(`/transactions/${id}`);
    return response.data;
  }

  async createTransaction(data: TransactionCreate): Promise<Transaction> {
    const response = await axiosInstance.post('/transactions', data);
    return response.data;
  }

  async updateTransaction(id: number, data: TransactionUpdate): Promise<Transaction> {
    const response = await axiosInstance.put(`/transactions/${id}`, data);
    return response.data;
  }

  async deleteTransaction(id: number): Promise<void> {
    await axiosInstance.delete(`/transactions/${id}`);
  }

  async dismissSuspicious(transactionId: number): Promise<{ status: string }> {
    const response = await axiosInstance.post(`/transactions/${transactionId}/dismiss-suspicious`);
    return response.data;
  }

  async smartInput(text: string): Promise<SmartInputResult> {
    const response = await axiosInstance.post('/transactions/smart-input', { text });
    return response.data;
  }

  async smartInputConfirm(text: string): Promise<Transaction> {
    const response = await axiosInstance.post('/transactions/smart-input/confirm', { text });
    return response.data;
  }

  async loadTestData(email: string, count?: number): Promise<{ success: boolean; message: string; count: number }> {
    const response = await axiosInstance.post('/transactions/load-test-data', null, {
      params: { email, count: count || 30 },
    });
    return response.data;
  }

  // Reminders
  async getReminders(): Promise<Reminder[]> {
    const response = await axiosInstance.get('/reminders');
    return response.data;
  }

  async getArchivedReminders(): Promise<Reminder[]> {
    const response = await axiosInstance.get('/reminders/archive');
    return response.data;
  }

  async createReminder(data: ReminderCreate): Promise<Reminder> {
    const response = await axiosInstance.post('/reminders', data);
    return response.data;
  }

  async updateReminder(id: number, data: Partial<ReminderCreate>): Promise<Reminder> {
    const response = await axiosInstance.put(`/reminders/${id}`, data);
    return response.data;
  }

  async deleteReminder(id: number): Promise<void> {
    await axiosInstance.delete(`/reminders/${id}`);
  }

  async completeReminder(id: number): Promise<Reminder> {
    const response = await axiosInstance.post(`/reminders/${id}/complete`);
    return response.data;
  }

  // Dashboard
  async getDashboard(): Promise<DashboardData> {
    const response = await axiosInstance.get('/dashboard');
    return response.data;
  }

  async getAnalytics(period?: string, dateFrom?: string, dateTo?: string): Promise<AnalyticsData> {
    const params: any = {};
    if (dateFrom) params.date_from = dateFrom;
    if (dateTo) params.date_to = dateTo;
    if (!dateFrom && !dateTo && period) params.period = period;
    
    const response = await axiosInstance.get('/dashboard/analytics', { params });
    return response.data;
  }

  async getPredictions(): Promise<PredictionsData> {
    const response = await axiosInstance.get('/dashboard/predictions');
    return response.data;
  }

  async getSavingTips(): Promise<SavingTipsData> {
    const response = await axiosInstance.get('/dashboard/tips');
    return response.data;
  }

  // Currency
  async getCurrencyRates(): Promise<CurrencyRatesData> {
    const response = await axiosInstance.get('/currency/rates');
    return response.data;
  }

  async convertCurrency(amount: number, from: string, to: string): Promise<{ result: number; rate: number }> {
    const response = await axiosInstance.post('/currency/convert', {
      amount,
      from_currency: from,
      to_currency: to,
    });
    return response.data;
  }

  // T-Bank
  async getTBankStatus(): Promise<TBankStatus> {
    const response = await axiosInstance.get('/tbank/status');
    return response.data;
  }

  async connectTBank(token: string): Promise<TBankStatus> {
    const response = await axiosInstance.post('/tbank/connect', { token });
    return response.data;
  }

  async disconnectTBank(): Promise<void> {
    await axiosInstance.post('/tbank/disconnect');
  }

  async syncTBank(): Promise<{ success: boolean; message: string; transactions_added: number }> {
    const response = await axiosInstance.post('/tbank/sync');
    return response.data;
  }

  async sandboxPayIn(amount?: number): Promise<{ success: boolean; message: string }> {
    const response = await axiosInstance.post('/tbank/sandbox/pay-in', null, {
      params: { amount: amount || 100000 },
    });
    return response.data;
  }

  // Admin
  async getAdminStats(): Promise<AdminStats> {
    const response = await axiosInstance.get('/admin/stats');
    return response.data;
  }

  async getAdminUsers(params?: {
    limit?: number;
    offset?: number;
    search?: string;
    is_active?: boolean;
    is_verified?: boolean;
  }): Promise<AdminUserList> {
    const response = await axiosInstance.get('/admin/users', { params });
    return response.data;
  }

  async blockUser(userId: number, reason?: string): Promise<{ message: string }> {
    const response = await axiosInstance.post(`/admin/users/${userId}/block`, { reason });
    return response.data;
  }

  async unblockUser(userId: number): Promise<{ message: string }> {
    const response = await axiosInstance.post(`/admin/users/${userId}/unblock`);
    return response.data;
  }

  async deleteUser(userId: number): Promise<{ message: string }> {
    const response = await axiosInstance.delete(`/admin/users/${userId}`);
    return response.data;
  }

  async adminVerifyEmail(userId: number): Promise<{ message: string }> {
    const response = await axiosInstance.post(`/admin/users/${userId}/verify-email`);
    return response.data;
  }

  async toggleSuperuser(userId: number): Promise<{ message: string }> {
    const response = await axiosInstance.post(`/admin/users/${userId}/toggle-superuser`);
    return response.data;
  }

  async getAuditLogs(params?: {
    limit?: number;
    offset?: number;
    action?: string;
    user_id?: number;
  }): Promise<AuditLogList> {
    const response = await axiosInstance.get('/admin/audit-logs', { params });
    return response.data;
  }
}

export const api = new ApiClient();

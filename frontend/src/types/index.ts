// Tipos básicos
export interface User {
  id: string
  email: string
  first_name: string
  last_name: string
  full_name: string
  phone: string
  timezone: string
  currency_preference: string
  role: 'user' | 'admin'
  created_at: string
  updated_at: string
}

export interface AccountType {
  id: number
  name: string
  code: string
  description: string
  icon: string
  allows_negative_balance: boolean
  is_credit_account: boolean
}

export interface Account {
  id: string
  name: string
  account_type: number
  account_type_display: string
  currency: string
  balance: string
  available_balance: string
  credit_limit?: string
  bank_name: string
  account_number: string
  description: string
  color: string
  is_active: boolean
  include_in_total: boolean
  metadata: Record<string, any>
  created_at: string
  updated_at: string
}

export interface Category {
  id: string
  name: string
  transaction_type: 'income' | 'expense'
  transaction_type_display: string
  description: string
  color: string
  icon: string
  monthly_budget?: string
  budget_currency: string
  parent_category?: string
  parent_name?: string
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface Transaction {
  id: string
  account: string
  account_name: string
  category: string
  category_name: string
  target_account?: string
  target_account_name?: string
  date: string
  amount: string
  currency: string
  transaction_type: 'income' | 'expense' | 'transfer'
  transaction_type_display: string
  description: string
  origin: 'manual' | 'card' | 'auto_debit' | 'installment' | 'transfer' | 'import'
  origin_display: string
  reference_number: string
  location: string
  tags: string[]
  metadata: Record<string, any>
  is_confirmed: boolean
  is_recurring: boolean
  created_at: string
  updated_at: string
}

export interface Budget {
  id: string
  category: string
  category_name: string
  period: 'monthly' | 'quarterly' | 'yearly'
  period_display: string
  amount: string
  currency: string
  start_date: string
  end_date: string
  alert_percentage: number
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface CardPurchase {
  id: string
  account: string
  account_name: string
  total_amount: string
  currency: string
  total_installments: number
  installment_amount: string
  interest_rate: string
  total_with_interest: string
  first_installment_date: string
  purchase_date: string
  current_installment: number
  status: 'active' | 'completed' | 'cancelled'
  status_display: string
  description: string
  remaining_installments: number
  remaining_amount: string
  progress_percentage: number
  created_at: string
  updated_at: string
}

export interface AutoDebit {
  id: string
  account: string
  account_name: string
  category: string
  category_name: string
  name: string
  description: string
  amount: string
  currency: string
  frequency: 'daily' | 'weekly' | 'biweekly' | 'monthly' | 'quarterly' | 'yearly'
  frequency_display: string
  start_date: string
  end_date?: string
  next_execution: string
  last_execution?: string
  status: 'active' | 'paused' | 'cancelled'
  status_display: string
  execution_count: number
  failed_attempts: number
  day_of_month?: number
  created_at: string
  updated_at: string
}

// Tipos para reportes
export interface BalanceReport {
  total_balance: number
  by_account_type: Record<string, {
    balance: number
    accounts: Array<{
      id: string
      name: string
      original_balance: number
      original_currency: string
      converted_balance: number
      available_balance: number
    }>
  }>
  by_currency: Record<string, {
    balance: number
    converted_balance: number
  }>
  accounts: Array<{
    id: string
    name: string
    type: string
    currency: string
    balance: number
    converted_balance: number
    is_active: boolean
  }>
  conversion_date: string
  target_currency: string
}

export interface ExpensesByCategoryReport {
  period: {
    from: string
    to: string
  }
  target_currency: string
  total_expenses: number
  categories: Record<string, {
    total_amount: number
    transaction_count: number
    percentage: number
    transactions: Array<{
      id: string
      date: string
      description: string
      amount: number
      currency: string
      converted_amount: number
      account: string
    }>
  }>
  category_count: number
  transaction_count: number
}

export interface IncomeVsExpensesReport {
  period: {
    from: string
    to: string
  }
  target_currency: string
  totals: {
    income: number
    expense: number
    net: number
    savings_rate: number
  }
  monthly_breakdown: Array<{
    month: string
    income: number
    expense: number
    net: number
  }>
}

export interface BudgetAnalysisReport {
  period: string
  target_currency: string
  summary: {
    total_budgeted: number
    total_spent: number
    total_remaining: number
    overall_usage_percentage: number
  }
  budgets: Array<{
    category: string
    budget_amount: number
    spent_amount: number
    remaining_amount: number
    usage_percentage: number
    status: 'ok' | 'warning' | 'exceeded'
    alert_percentage: number
    period: string
  }>
  budget_count: number
}

// Tipos para conversión de divisas
export interface Currency {
  code: string
  name: string
  symbol: string
  decimal_places: number
  is_active: boolean
  is_base: boolean
}

export interface ExchangeRate {
  id: string
  from_currency: string
  from_currency_code: string
  from_currency_name: string
  to_currency: string
  to_currency_code: string
  to_currency_name: string
  rate: string
  date: string
  source: string
  provider: string
  created_at: string
}

export interface ConversionResponse {
  original_amount: string
  converted_amount: string
  from_currency: string
  to_currency: string
  exchange_rate: string
  conversion_date: string
  from_currency_symbol?: string
  to_currency_symbol?: string
}

// Tipos para formularios
export interface CreateAccountForm {
  name: string
  account_type: number
  currency: string
  credit_limit?: string
  bank_name?: string
  account_number?: string
  description?: string
  color: string
}

export interface CreateTransactionForm {
  account: string
  category: string
  target_account?: string
  date: string
  amount: string
  currency: string
  transaction_type: 'income' | 'expense' | 'transfer'
  description: string
  reference_number?: string
  location?: string
  tags: string[]
}

export interface CreateCategoryForm {
  name: string
  transaction_type: 'income' | 'expense'
  description?: string
  color: string
  icon?: string
  monthly_budget?: string
  budget_currency: string
  parent_category?: string
}

export interface CreateBudgetForm {
  category: string
  period: 'monthly' | 'quarterly' | 'yearly'
  amount: string
  currency: string
  start_date: string
  end_date: string
  alert_percentage: number
}

// Tipos de utilidad
export interface ApiResponse<T> {
  data: T
  message?: string
  errors?: Record<string, string[]>
}

export interface PaginatedResponse<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}

export interface FilterParams {
  page?: number
  page_size?: number
  search?: string
  ordering?: string
  [key: string]: any
}

// Tipos para el contexto de autenticación
export interface AuthContextType {
  user: User | null
  loading: boolean
  signIn: (email: string, password: string) => Promise<void>
  signUp: (email: string, password: string, userData: Partial<User>) => Promise<void>
  signOut: () => Promise<void>
  updateProfile: (data: Partial<User>) => Promise<void>
}

// Tipos para notificaciones
export interface Toast {
  id?: string
  type: 'success' | 'error' | 'warning' | 'info'
  title: string
  message?: string
  duration?: number
}

// Tipos para el dashboard
export interface DashboardData {
  balance: BalanceReport
  current_month_expenses: ExpensesByCategoryReport
  current_month_income_vs_expenses: IncomeVsExpensesReport
  budget_analysis: BudgetAnalysisReport
  installments_projection?: any
  period: string
  currency: string
  generated_at: string
}
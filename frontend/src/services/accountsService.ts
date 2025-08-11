import { apiRequest } from './api'
import type { 
  Account, 
  AccountType, 
  CreateAccountForm, 
  PaginatedResponse, 
  ApiResponse,
  FilterParams 
} from '../types'

export const accountsService = {
  // Obtener tipos de cuenta
  async getAccountTypes(): Promise<AccountType[]> {
    const response = await apiRequest.get<AccountType[]>('/accounts/types/')
    return response.data
  },

  // Obtener cuentas del usuario
  async getAccounts(params?: FilterParams): Promise<PaginatedResponse<Account>> {
    const response = await apiRequest.get<PaginatedResponse<Account>>('/accounts/accounts/', {
      params,
    })
    return response.data
  },

  // Obtener cuenta por ID
  async getAccount(id: string): Promise<Account> {
    const response = await apiRequest.get<Account>(`/accounts/accounts/${id}/`)
    return response.data
  },

  // Crear nueva cuenta
  async createAccount(data: CreateAccountForm): Promise<Account> {
    const response = await apiRequest.post<Account>('/accounts/accounts/', data)
    return response.data
  },

  // Actualizar cuenta
  async updateAccount(id: string, data: Partial<CreateAccountForm>): Promise<Account> {
    const response = await apiRequest.patch<Account>(`/accounts/accounts/${id}/`, data)
    return response.data
  },

  // Eliminar cuenta
  async deleteAccount(id: string): Promise<void> {
    await apiRequest.delete(`/accounts/accounts/${id}/`)
  },

  // Obtener resumen de cuentas
  async getAccountsSummary(): Promise<any> {
    const response = await apiRequest.get('/accounts/accounts/summary/')
    return response.data
  },

  // Obtener balance total por moneda
  async getBalanceByAccount(accountId: string, currency = 'ARS'): Promise<any> {
    const response = await apiRequest.get(`/accounts/accounts/${accountId}/balance/`, {
      params: { currency },
    })
    return response.data
  },
}

export default accountsService
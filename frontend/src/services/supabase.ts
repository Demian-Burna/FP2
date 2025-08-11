import { createClient } from '@supabase/supabase-js'

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY

if (!supabaseUrl || !supabaseAnonKey) {
  throw new Error(
    'Variables de entorno de Supabase no configuradas. ' +
    'Asegúrate de definir VITE_SUPABASE_URL y VITE_SUPABASE_ANON_KEY'
  )
}

export const supabase = createClient(supabaseUrl, supabaseAnonKey, {
  auth: {
    autoRefreshToken: true,
    persistSession: true,
    detectSessionInUrl: true,
  },
})

// Tipos para autenticación
export interface AuthResponse {
  user: any
  session: any
  error?: Error
}

export interface SignUpData {
  email: string
  password: string
  options?: {
    data?: {
      first_name?: string
      last_name?: string
      phone?: string
    }
  }
}

// Funciones de autenticación
export const authService = {
  async signUp({ email, password, options }: SignUpData): Promise<AuthResponse> {
    const result = await supabase.auth.signUp({
      email,
      password,
      options,
    })
    
    return {
      user: result.data.user,
      session: result.data.session,
      error: result.error,
    }
  },

  async signIn(email: string, password: string): Promise<AuthResponse> {
    const result = await supabase.auth.signInWithPassword({
      email,
      password,
    })
    
    return {
      user: result.data.user,
      session: result.data.session,
      error: result.error,
    }
  },

  async signOut(): Promise<{ error?: Error }> {
    const result = await supabase.auth.signOut()
    return { error: result.error }
  },

  async getSession() {
    const result = await supabase.auth.getSession()
    return result.data.session
  },

  async getUser() {
    const result = await supabase.auth.getUser()
    return result.data.user
  },

  onAuthStateChange(callback: (event: string, session: any) => void) {
    return supabase.auth.onAuthStateChange(callback)
  },

  async resetPassword(email: string) {
    const result = await supabase.auth.resetPasswordForEmail(email, {
      redirectTo: `${window.location.origin}/auth/reset-password`,
    })
    return result
  },

  async updatePassword(password: string) {
    const result = await supabase.auth.updateUser({ password })
    return result
  },
}
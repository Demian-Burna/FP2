import React, { createContext, useContext, useEffect, useState, ReactNode } from 'react'
import { authService } from '../services/supabase'
import { apiRequest } from '../services/api'
import type { User, AuthContextType } from '../types'
import { toast } from 'sonner'

const AuthContext = createContext<AuthContextType | undefined>(undefined)

interface AuthProviderProps {
  children: ReactNode
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // Verificar sesión inicial
    checkUser()

    // Escuchar cambios en el estado de autenticación
    const { data: { subscription } } = authService.onAuthStateChange(
      async (event, session) => {
        if (event === 'SIGNED_IN' && session) {
          await loadUserProfile()
        } else if (event === 'SIGNED_OUT') {
          setUser(null)
        }
      }
    )

    return () => {
      subscription.unsubscribe()
    }
  }, [])

  const checkUser = async () => {
    try {
      const session = await authService.getSession()
      if (session) {
        await loadUserProfile()
      }
    } catch (error) {
      console.error('Error checking user session:', error)
    } finally {
      setLoading(false)
    }
  }

  const loadUserProfile = async () => {
    try {
      const response = await apiRequest.get<User>('/accounts/profiles/me/')
      setUser(response.data)
    } catch (error: any) {
      console.error('Error loading user profile:', error)
      
      // Si hay error 401, limpiar sesión
      if (error.response?.status === 401) {
        await authService.signOut()
        setUser(null)
      }
    }
  }

  const signIn = async (email: string, password: string) => {
    try {
      setLoading(true)
      
      const { user: supabaseUser, session, error } = await authService.signIn(email, password)
      
      if (error) {
        throw error
      }

      if (session && supabaseUser) {
        await loadUserProfile()
        toast.success('¡Bienvenido!', {
          description: 'Has iniciado sesión exitosamente'
        })
      }
    } catch (error: any) {
      console.error('Error signing in:', error)
      
      let errorMessage = 'Error al iniciar sesión'
      if (error.message?.includes('Invalid login credentials')) {
        errorMessage = 'Credenciales inválidas'
      } else if (error.message?.includes('Email not confirmed')) {
        errorMessage = 'Por favor confirma tu email antes de iniciar sesión'
      }
      
      toast.error('Error de autenticación', {
        description: errorMessage
      })
      throw error
    } finally {
      setLoading(false)
    }
  }

  const signUp = async (email: string, password: string, userData: Partial<User>) => {
    try {
      setLoading(true)

      const { user: supabaseUser, error } = await authService.signUp({
        email,
        password,
        options: {
          data: {
            first_name: userData.first_name,
            last_name: userData.last_name,
            phone: userData.phone,
          }
        }
      })

      if (error) {
        throw error
      }

      toast.success('¡Cuenta creada!', {
        description: 'Revisa tu email para confirmar tu cuenta'
      })

      return supabaseUser
    } catch (error: any) {
      console.error('Error signing up:', error)
      
      let errorMessage = 'Error al crear cuenta'
      if (error.message?.includes('User already registered')) {
        errorMessage = 'Ya existe una cuenta con este email'
      } else if (error.message?.includes('Password should be at least')) {
        errorMessage = 'La contraseña debe tener al menos 6 caracteres'
      }
      
      toast.error('Error de registro', {
        description: errorMessage
      })
      throw error
    } finally {
      setLoading(false)
    }
  }

  const signOut = async () => {
    try {
      setLoading(true)
      
      await authService.signOut()
      setUser(null)
      
      toast.success('Sesión cerrada', {
        description: 'Has cerrado sesión exitosamente'
      })
    } catch (error) {
      console.error('Error signing out:', error)
      toast.error('Error al cerrar sesión')
    } finally {
      setLoading(false)
    }
  }

  const updateProfile = async (data: Partial<User>) => {
    try {
      const response = await apiRequest.patch<User>('/accounts/profiles/update_profile/', data)
      setUser(response.data)
      
      toast.success('Perfil actualizado', {
        description: 'Tus datos han sido actualizados exitosamente'
      })
      
      return response.data
    } catch (error: any) {
      console.error('Error updating profile:', error)
      
      const errorMessage = error.response?.data?.message || 'Error al actualizar perfil'
      toast.error('Error', {
        description: errorMessage
      })
      throw error
    }
  }

  const value: AuthContextType = {
    user,
    loading,
    signIn,
    signUp,
    signOut,
    updateProfile,
  }

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth(): AuthContextType {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
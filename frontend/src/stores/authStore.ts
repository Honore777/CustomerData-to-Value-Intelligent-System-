import { create } from 'zustand'
import type { AuthUser } from '../services/api'

/*
WHAT WE ARE MODELING:
- whether the user is authenticated
- whether the app is currently checking session
- current user info
- actions to update auth state
*/

/*
TypeScript interface for the user object.
For now we keep only what frontend needs immediately.
Later we can expand it.
*/
/*
This describes the entire auth store shape:
- state values
- action functions
*/
type AuthState = {
  isAuthenticated: boolean
  checkingAuth: boolean
  user: AuthUser | null

  setAuthenticated: (value: boolean) => void
  setCheckingAuth: (value: boolean) => void
  setUser: (user: AuthUser | null) => void
  clearAuth: () => void
}

/*
create(...) builds the Zustand store.

set(...) is provided by Zustand.
It updates the store state.
*/
export const useAuthStore = create<AuthState>((set) => ({
  // initial state
  isAuthenticated: false,
  checkingAuth: true,
  user: null,

  // actions
  setAuthenticated: (value) => set({ isAuthenticated: value }),

  setCheckingAuth: (value) => set({ checkingAuth: value }),

  setUser: (user) => set({ user }),

  clearAuth: () =>
    set({
      isAuthenticated: false,
      checkingAuth: false,
      user: null,
    }),
}))
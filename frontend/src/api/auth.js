import client from './client'

export const login = (email, password) =>
  client.post('/auth/login', { email, password }).then((r) => r.data)

export const refresh = (refresh_token) =>
  client.post('/auth/refresh', { refresh_token }).then((r) => r.data)

export const logout = () => client.post('/auth/logout')

export const changePassword = (current_password, new_password) =>
  client.post('/auth/change-password', { current_password, new_password }).then((r) => r.data)

export const getMe = () => client.get('/users/me').then((r) => r.data)

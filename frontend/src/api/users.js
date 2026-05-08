import client from './client'

export const listUsers = () => client.get('/users').then((r) => r.data)

export const createUser = (data) => client.post('/users', data).then((r) => r.data)

export const updateUser = (id, data) => client.patch(`/users/${id}`, data).then((r) => r.data)

export const resetPassword = (id, new_password) =>
  client.post(`/users/${id}/reset-password`, { new_password }).then((r) => r.data)

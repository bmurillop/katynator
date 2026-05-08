import client from './client'

export const listAccounts = (params) =>
  client.get('/accounts', { params }).then((r) => r.data)

export const getAccount = (id) =>
  client.get(`/accounts/${id}`).then((r) => r.data)

export const updateAccount = (id, data) =>
  client.patch(`/accounts/${id}`, data).then((r) => r.data)

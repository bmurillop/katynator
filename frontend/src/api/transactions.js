import client from './client'

export const listTransactions = (params) =>
  client.get('/transactions', { params }).then((r) => r.data)

export const getTransaction = (id) =>
  client.get(`/transactions/${id}`).then((r) => r.data)

export const updateTransaction = (id, data) =>
  client.patch(`/transactions/${id}`, data).then((r) => r.data)

export const getSummary = (params) =>
  client.get('/transactions/summary', { params }).then((r) => r.data)

export const getMonthlySummary = (params) =>
  client.get('/transactions/summary/monthly', { params }).then((r) => r.data)

export const suggestCategoriesAI = () =>
  client.post('/transactions/suggest-categories').then((r) => r.data)

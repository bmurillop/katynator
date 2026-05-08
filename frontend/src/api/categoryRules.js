import client from './client'

export const listRules = () => client.get('/category-rules').then((r) => r.data)

export const createRule = (data) =>
  client.post('/category-rules', data).then((r) => r.data)

export const updateRule = (id, data) =>
  client.patch(`/category-rules/${id}`, data).then((r) => r.data)

export const deleteRule = (id) => client.delete(`/category-rules/${id}`)

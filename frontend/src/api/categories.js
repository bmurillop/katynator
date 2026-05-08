import client from './client'

export const listCategories = () => client.get('/categories').then((r) => r.data)

export const createCategory = (data) =>
  client.post('/categories', data).then((r) => r.data)

export const updateCategory = (id, data) =>
  client.patch(`/categories/${id}`, data).then((r) => r.data)

import client from './client'

export const listEntityRules = () =>
  client.get('/entity-rules').then((r) => r.data)

export const createEntityRule = (data) =>
  client.post('/entity-rules', data).then((r) => r.data)

export const updateEntityRule = (id, data) =>
  client.patch(`/entity-rules/${id}`, data).then((r) => r.data)

export const deleteEntityRule = (id) =>
  client.delete(`/entity-rules/${id}`).then((r) => r.data)

export const previewEntityRule = (params) =>
  client.get('/entity-rules/preview', { params }).then((r) => r.data)

export const applyEntityRule = (id) =>
  client.post(`/entity-rules/${id}/apply`).then((r) => r.data)

export const reapplyEntityRules = () =>
  client.post('/entity-rules/reapply').then((r) => r.data)

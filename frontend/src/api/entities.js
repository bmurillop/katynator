import client from './client'

export const listEntities = (params) =>
  client.get('/entities', { params }).then((r) => r.data)

export const getEntity = (id) =>
  client.get(`/entities/${id}`).then((r) => r.data)

export const createEntity = (data) =>
  client.post('/entities', data).then((r) => r.data)

export const updateEntity = (id, data) =>
  client.patch(`/entities/${id}`, data).then((r) => r.data)

export const addPattern = (entityId, data) =>
  client.post(`/entities/${entityId}/patterns`, data).then((r) => r.data)

export const deletePattern = (entityId, patternId) =>
  client.delete(`/entities/${entityId}/patterns/${patternId}`)

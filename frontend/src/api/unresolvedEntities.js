import client from './client'

export const listUnresolved = (params) =>
  client.get('/unresolved-entities', { params }).then((r) => r.data)

export const resolveToExisting = (id, entity_id) =>
  client.post(`/unresolved-entities/${id}/resolve`, { entity_id }).then((r) => r.data)

export const createEntityFromUnresolved = (id, data) =>
  client.post(`/unresolved-entities/${id}/create-entity`, data).then((r) => r.data)

export const ignoreUnresolved = (id) =>
  client.post(`/unresolved-entities/${id}/ignore`).then((r) => r.data)

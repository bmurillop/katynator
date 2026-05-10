import client from './client'

export const listRules = () => client.get('/category-rules').then((r) => r.data)

export const createRule = (data) =>
  client.post('/category-rules', data).then((r) => r.data)

export const updateRule = (id, data) =>
  client.patch(`/category-rules/${id}`, data).then((r) => r.data)

export const deleteRule = (id) => client.delete(`/category-rules/${id}`)

export const previewRule = ({ memo_pattern, match_type, entity_id } = {}) => {
  const params = {}
  if (memo_pattern) params.memo_pattern = memo_pattern
  if (match_type) params.match_type = match_type
  if (entity_id) params.entity_id = entity_id
  return client.get('/category-rules/preview', { params }).then((r) => r.data)
}

export const applyRule = (id) =>
  client.post(`/category-rules/${id}/apply`).then((r) => r.data)

export const reapplyRules = () =>
  client.post('/category-rules/reapply').then((r) => r.data)

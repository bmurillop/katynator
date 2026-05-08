import client from './client'

export const listEmails = (params) =>
  client.get('/emails', { params }).then((r) => r.data)

export const getEmail = (id) =>
  client.get(`/emails/${id}`).then((r) => r.data)

export const retryEmail = (id) =>
  client.post(`/emails/${id}/retry`).then((r) => r.data)

export const triggerPoll = () =>
  client.post('/emails/poll').then((r) => r.data)

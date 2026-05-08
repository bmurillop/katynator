import client from './client'

export const listPersons = () => client.get('/persons').then((r) => r.data)

export const createPerson = (data) => client.post('/persons', data).then((r) => r.data)

export const updatePerson = (id, data) => client.patch(`/persons/${id}`, data).then((r) => r.data)

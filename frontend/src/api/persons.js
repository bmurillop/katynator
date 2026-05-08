import client from './client'

export const listPersons = () => client.get('/persons').then((r) => r.data)

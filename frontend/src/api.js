import axios from 'axios';
const client = axios.create({baseURL: import.meta.env.VITE_API_URL || '/api'});
export const uploadCsv = file => { const data = new FormData(); data.append('file', file); return client.post('/upload/csv', data); };
export const ask = (message, session_id) => client.post('/chat', {message, session_id});
export const getIngests = () => client.get('/ingests');
export const templateUrl = `${client.defaults.baseURL}/template/csv`;

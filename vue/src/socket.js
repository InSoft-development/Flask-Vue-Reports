import { io } from 'socket.io-client'

const URL = window.api.url

export const socket = io(URL)

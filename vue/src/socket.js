import { io } from 'socket.io-client'

const URL = 'http://10.23.23.31:8004'

export const socket = io(URL)

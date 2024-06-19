import { Mutex } from 'async-mutex'
import { socket } from '../socket'

const mutex = new Mutex()

/***
 * Процедура запуска обновления файла тегов kks_all.csv
 * @returns {Promise<void>}
 */
export async function runUpdate(mode, rootDirectory, exceptionDirectories, exceptionExpert) {
  await new Promise(async (resolve) => {
    await socket.emit(
      'update_kks_all',
      mode,
      rootDirectory,
      exceptionDirectories,
      exceptionExpert,
      () => {
        resolve()
      }
    )
  })
}

/***
 * Процедура применения списка исключений к уже выкаченному файлу kks_all.csv
 * @param rootDirectory
 * @param exceptionDirectories
 * @param exceptionExpert
 * @returns {Promise<void>}
 */
export async function changeUpdateFile(rootDirectory, exceptionDirectories, exceptionExpert) {
  await new Promise(async (resolve) => {
    await socket.emit(
      'change_update_kks_all',
      rootDirectory,
      exceptionDirectories,
      exceptionExpert,
      () => {
        resolve()
      }
    )
  })
}

/***
 * Процедура отмены пользователем обновления файла тегов kks_all.csv
 * @returns {Promise<void>}
 */
export async function cancelUpdate() {
  await new Promise((resolve) => {
    socket.emit('update_cancel', () => {
      resolve()
    })
  })
}

/***
 * Процедура отмены пользователем запроса среза сигналов
 * @returns {Promise<void>}
 */
export async function cancelSignals() {
  await new Promise((resolve) => {
    socket.emit('signals_data_cancel', () => {
      resolve()
    })
  })
}

/***
 * Процедура отмены пользователем запроса сетки сигналов
 * @returns {Promise<void>}
 */
export async function cancelGrid() {
  await new Promise((resolve) => {
    socket.emit('grid_data_cancel', () => {
      resolve()
    })
  })
}

/***
 * Процедура отмены пользователем запроса дребезга сигналов
 * @returns {Promise<void>}
 */
export async function cancelBounce() {
  await new Promise((resolve) => {
    socket.emit('bounce_data_cancel', () => {
      resolve()
    })
  })
}

/***
 * Процедура изменения конфигурации клиента OPC UA
 * @param ipOPC
 * @param portOPC
 * @returns {Promise<void>}
 */
export async function changeOpcServerConfig(ipOPC, portOPC) {
  await new Promise((resolve) => {
    socket.emit('change_opc_server_config', ipOPC, portOPC, () => {
      resolve()
    })
  })
}

/***
 * Процедура изменения полей по умолчанию в конфиге
 * @param defaultFields
 * @returns {Promise<void>}
 */
export async function changeDefaultFields(defaultFields) {
  await new Promise((resolve) => {
    socket.emit('change_default_fields', defaultFields, () => {
      resolve()
    })
  })
}

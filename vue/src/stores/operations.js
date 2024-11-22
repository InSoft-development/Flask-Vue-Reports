import { socket } from '../socket'

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
 * Процедура изменения выбранного клиента
 * @param modeClientRadio
 * @returns {Promise<void>}
 */
export async function changeClientMode(modeClientRadio) {
  await new Promise((resolve) => {
    socket.emit('change_client_mode', modeClientRadio, (msg) => {
      if (msg) alert(msg)
      resolve(msg)
    })
  })
}

/***
 * Процедура изменения конфигурации клиента Clickhouse
 * @param ipCH
 * @param portCH
 * @param username
 * @param password
 * @returns {Promise<void>}
 */
export async function changeCHServerConfig(ipCH, portCH, username, password) {
  await new Promise((resolve) => {
    socket.emit('change_ch_server_config', ipCH, portCH, username, password, (status, msg) => {
      if (status === false) alert('ip адрес введен не корректно')
      if (msg) alert(msg)
      resolve(status, msg)
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
    socket.emit('change_opc_server_config', ipOPC, portOPC, (status, msg) => {
      if (status === false) alert('ip адрес введен не корректно')
      if (msg) alert(msg)
      resolve(status, msg)
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
    socket.emit('change_default_fields', defaultFields, (msg) => {
      if (msg) alert(msg)
      resolve(msg)
    })
  })
}

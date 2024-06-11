import { Mutex } from 'async-mutex'
import { socket } from '../socket'

const mutex = new Mutex()

/***
 * Процедура получения конфигурации сервера OPC UA и проверки файла kks_all.csv
 * @param configServer
 * @param checkFileActive
 * @returns {Promise<void>}
 */
export async function getServerConfig(configServer, checkFileActive) {
  await new Promise((resolve) => {
    socket.emit('get_server_config', (serverConfig, checkFile) => {
      configServer.value = serverConfig
      checkFileActive.value = checkFile
      resolve([serverConfig, checkFile])
    })
  })
}

/***
 * Процедура получения ip-адреса и порта клиента OPC UA
 * @param ipOPC
 * @param portOPC
 * @returns {Promise<void>}
 */
export async function getIpAndPortConfig(ipOPC, portOPC) {
  await new Promise((resolve) => {
    socket.emit('get_ip_port_config', (ip, port) => {
      ipOPC.value = ip
      portOPC.value = port
      resolve([ip, port])
    })
  })
}

/***
 * Процедура получения даты последнего обновления файла kks_all.csv
 * @param lastUpdateFileKKS
 * @returns {Promise<void>}
 */
export async function getLastUpdateFileKKS(lastUpdateFileKKS) {
  await new Promise((resolve) => {
    socket.emit('get_last_update_file_kks', (date) => {
      lastUpdateFileKKS.value = date
      resolve(date)
    })
  })
}

/***
 * Процедура получения полей по умолчанию из конфига
 * @returns {Promise<void>}
 */
export async function getDefaultFields(defaultFields) {
  let result = null
  await new Promise((resolve) => {
    socket.emit('get_default_fields', (defaultFields) => {
      result = defaultFields
      resolve(defaultFields)
    })
  })
  if (typeof result === 'string') {
    Object.assign(defaultFields, {
      typesOfSensors: ['String', 'UInt32', 'Boolean', 'Float'],
      selectionTag: 'sequential',
      sensorsAndTemplateValue: ['Sochi2\\.GT\\.AM\\.\\S*-AM\\.Q?$'],
      quality: ['8 - (BNC) - ОТКАЗ СВЯЗИ (TIMEOUT)', '192 - (GOD) – ХОРОШ'],
      lastValueChecked: false,
      dateDeepOfSearch: new Date(),
      interval: 10,
      dimension: 'hour',
      countShowSensors: 10
    })
    alert(result)
  } else {
    Object.assign(defaultFields, result)
    if (defaultFields.dateDeepOfSearch === null) defaultFields.dateDeepOfSearch = ''
    else defaultFields.dateDeepOfSearch = new Date(defaultFields.dateDeepOfSearch)
  }
}

/***
 * Процедура получения типов данных тегов файла kks_all.csv
 * @param typesOptions
 * @returns {Promise<void>}
 */
export async function getTypesOfSensors(typesOptions) {
  await new Promise((resolve) => {
    socket.emit('get_types_of_sensors', (typesOfData) => {
      typesOptions.value[0].options = typesOfData
      resolve(typesOfData)
    })
  })
}

/***
 * Процедура фильтрации kks по маске во время их поиска и выбора шаблона
 * @param options
 * @param types
 * @param masks
 * @returns {Promise<void>}
 */
export async function getKKSFilterByMasks(options, types, masks) {
  let masksRequestArray = Array()
  let lastKKS = ''

  for (let i = 0; i < masks.length; i++) {
    if (
      !(await new Promise((resolve) => {
        socket.emit('get_kks_tag_exist', masks[i], () => {
          resolve()
        })
      }))
    ) {
      masksRequestArray.push(masks[i])
    } else {
      if (i == masks.length - 1) lastKKS = masks[i]
    }
  }

  // for (let mask of masks){
  //   if (!(await eel.get_kks_tag_exist(mask)()))
  //     masksRequestArray.push(mask)
  // }

  let result = null
  await new Promise((resolve) => {
    socket.emit('get_kks_by_masks', types, masksRequestArray, (kks) => {
      result = kks
      resolve(kks)
    })
  })
  if (lastKKS.length != 0) result.unshift(lastKKS)
  options.value[1].options = result
}

/***
 * Процедура получения тегов kks по маске шаблона
 * @param chosenSensors
 * @param types
 * @param sensorsAndTemplate
 * @param selectionTagRadio
 * @returns {Promise<void>}
 */
export async function getKKSByMasksForTable(
  chosenSensors,
  types,
  sensorsAndTemplate,
  selectionTagRadio
) {
  let kks = Array()
  let masks = Array()
  for (let element of sensorsAndTemplate) {
    if (
      await new Promise((resolve) => {
        socket.emit('get_kks_tag_exist', element, () => {
          resolve()
        })
      })
    )
      kks.push(element)
    else masks.push(element)
  }

  let result = null
  await new Promise((resolve) => {
    socket.emit('get_kks', types, masks, kks, selectionTagRadio.value, (kks) => {
      result = kks
      resolve(kks)
    })
  })
  if (result[0] === ['']) {
    alert('Неверный синтаксис регулярного выражения. Ничего не нашлось')
    return
  }
  chosenSensors.value = result
}

export async function getKKSByTextMasksFromSearch(
  templateText,
  types,
  dialogSearchedTagsTextArea,
  countOfTags
) {
  if (templateText.value.trim() === '') return
  let kks = Array()
  let masks = Array()

  if (
    await new Promise((resolve) => {
      socket.emit('get_kks_tag_exist', templateText.value, () => {
        resolve()
      })
    })
  )
    kks.push(templateText.value)
  else masks.push(templateText.value)

  let result = null
  await new Promise((resolve) => {
    socket.emit('get_kks', types, masks, kks, (kks) => {
      result = kks
      resolve(kks)
    })
  })
  if (result[0] === ['']) {
    alert('Неверный синтаксис регулярного выражения. Ничего не нашлось')
    return
  }
  countOfTags.value = result.length
  dialogSearchedTagsTextArea.value = result.join('\n')
}

/***
 * Процедура выполнения запроса среза
 * @param types
 * @param selectionTag
 * @param sensorsAndTemplate
 * @param qualities
 * @param date
 * @param dateDeepOfSearch
 * @param lastValueChecked
 * @param intervalOrDateChecked
 * @param intervalDeepOfSearch
 * @param intervalDeepOfSearchRadio
 * @param dataTable
 * @param dataTableRequested
 * @returns {Promise<void>}
 */
export async function getSignals(
  types,
  selectionTag,
  sensorsAndTemplate,
  qualities,
  date,
  lastValueChecked,
  intervalOrDateChecked,
  intervalDeepOfSearch,
  intervalDeepOfSearchRadio,
  dateDeepOfSearch,
  dataTable,
  dataTableRequested
) {
  let formatDate = new Date(date.toString().split('GMT')[0] + ' UTC').toISOString()
  let formatDateDeepOfSearch = new Date(
    dateDeepOfSearch.toString().split('GMT')[0] + ' UTC'
  ).toISOString()
  let kks = Array()
  let masks = Array()
  for (let element of sensorsAndTemplate) {
    if (
      await new Promise((resolve) => {
        socket.emit('get_kks_tag_exist', element, () => {
          resolve()
        })
      })
    )
      kks.push(element)
    else masks.push(element)
  }

  let result = null
  await new Promise((resolve) => {
    socket.emit(
      'get_signals_data',
      types,
      selectionTag,
      masks,
      kks,
      qualities,
      formatDate,
      lastValueChecked,
      intervalOrDateChecked,
      intervalDeepOfSearch,
      intervalDeepOfSearchRadio,
      formatDateDeepOfSearch,
      (res) => {
        result = res
        resolve(res)
      }
    )
  })
  if (typeof result === 'string') {
    dataTableRequested.value = false
    alert(result)
  }
  if (Array.isArray(result)) {
    dataTable.value = result
    dataTableRequested.value = true
  }
}

/***
 * Процедура выполения запроса сетки
 * @param chosenSensors
 * @param dateBegin
 * @param dateEnd
 * @param interval
 * @param dimension
 * @param dataTable
 * @param dataTableRequested
 * @param dataTableStatus
 * @returns {Promise<void>}
 */
export async function getGrid(
  chosenSensors,
  dateBegin,
  dateEnd,
  interval,
  dimension,
  dataTable,
  dataTableRequested,
  dataTableStatus
) {
  let formatDateBegin = new Date(dateBegin.toString().split('GMT')[0] + ' UTC').toISOString()
  let formatDateEnd = new Date(dateEnd.toString().split('GMT')[0] + ' UTC').toISOString()

  let result = Array()
  await new Promise((resolve) => {
    socket.emit(
      'get_grid_data',
      chosenSensors,
      formatDateBegin,
      formatDateEnd,
      interval,
      dimension,
      (data, status) => {
        result[0] = data
        result[1] = status
        resolve([data, status])
      }
    )
  })
  if (typeof result === 'string') {
    dataTableRequested.value = false
    alert(result)
  }
  if (Array.isArray(result)) {
    dataTable.value = result[0]
    dataTableStatus.value = result[1]
    dataTableRequested.value = true
  }
}

/***
 * Процедура выполнения запроса построения дребезга сигналов
 * @param templateSignal
 * @param date
 * @param interval
 * @param dimension
 * @param showSensors
 * @param dataTable
 * @param dataTableRequested
 * @returns {Promise<void>}
 */
export async function getBounceSignals(
  templateSignal,
  date,
  interval,
  dimension,
  showSensors,
  dataTable,
  dataTableRequested
) {
  let formatDate = new Date(date.toString().split('GMT')[0] + ' UTC').toISOString()

  let result = null
  await new Promise((resolve) => {
    socket.emit(
      'get_bounce_signals_data',
      templateSignal,
      formatDate,
      interval,
      dimension,
      showSensors,
      (res) => {
        result = res
        resolve(res)
      }
    )
  })
  if (typeof result === 'string') {
    dataTableRequested.value = false
    alert(result)
  }
  if (Array.isArray(result)) {
    dataTable.value = result
    dataTableRequested.value = true
  }
}
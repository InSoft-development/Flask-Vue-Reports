import { defineStore } from 'pinia'
import { ref, reactive, computed } from 'vue'
import { getDefaultFields, changeDefaultFields } from './index.js'
import { socket } from '../socket'

export const useApplicationStore = defineStore('ApplicationStore', () => {
  const qualitiesName = ref()

  const badCode = [
    'BadNoCommunication',
    'BadSensorFailure',
    'BadCommunicationFailure',
    'BadDeviceFailure',
    'UncertainLastUsableValue'
  ]

  const badNumericCode = [8, 16, 24, 28, 88]

  const getQualitiesName = async () => {
    await new Promise((resolve) => {
      socket.emit('get_qualities_name', (qualitiesNameAnswer) => {
        qualitiesName.value = [{
          label: 'Выбрать все коды качества сигнала',
          options: qualitiesNameAnswer
        }]
        resolve(qualitiesNameAnswer)
      })
    })
  }

  const deltaTimeInSeconds = {
    day: 86400,
    hour: 3600,
    minute: 60,
    second: 1
  }

  const estimatedSliceRateInHours = 4500
  const estimatedGridRateInHours = 4630000
  const estimatedBounceRateInHours = 8676604126000
  const sliceTimeLimitInHours = 0.5
  const gridTimeLimitInHours = 0.5
  const bounceTimeLimitInHours = 0.5

  let defaultFields = reactive({})
  const sensorsAndTemplateValueShow = ref('')
  const exceptionDirectoriesShow = ref('')

  const getFields = async () => {
    await getDefaultFields(defaultFields)

    if ("sensorsAndTemplateValue" in defaultFields)
      sensorsAndTemplateValueShow.value = defaultFields.sensorsAndTemplateValue.join(', ')

    if ("exceptionDirectories" in defaultFields)
      exceptionDirectoriesShow.value = defaultFields.exceptionDirectories.join(', ')
  }

  const setFields = async (fields) => {
    Object.keys(defaultFields).forEach((key) => delete defaultFields[key])
    Object.assign(defaultFields, fields)
    await changeDefaultFields(defaultFields)
  }

  const firstRaw = 0
  const lastRaw = 30
  const itemSize = 12

  return {
    badCode,
    qualitiesName,
    badNumericCode,
    getQualitiesName,
    getDefaultFields,
    deltaTimeInSeconds,
    estimatedSliceRateInHours,
    estimatedGridRateInHours,
    estimatedBounceRateInHours,
    sliceTimeLimitInHours,
    gridTimeLimitInHours,
    bounceTimeLimitInHours,
    defaultFields,
    sensorsAndTemplateValueShow,
    exceptionDirectoriesShow,
    getFields,
    setFields,
    firstRaw,
    lastRaw,
    itemSize
  }
})

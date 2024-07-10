import { defineStore } from 'pinia'
import { reactive } from 'vue'
import { getDefaultFields, changeDefaultFields } from './index.js'

export const useApplicationStore = defineStore('ApplicationStore', () => {
  const badCode = [
    'BadNoCommunication',
    'BadSensorFailure',
    'BadCommunicationFailure',
    'BadDeviceFailure',
    'UncertainLastUsableValue'
  ]

  const qualitiesName = [
    '8 - (BNC) - ОТКАЗ СВЯЗИ (TIMEOUT)',
    '16 - (BSF) - ОТКАЗ ПАРАМ',
    '24 - (BCF) - ОТКАЗ СВЯЗИ',
    '28 - (BOS) - ОТКАЗ ОБСЛУЖ',
    '88 - (BLC) - ОТКАЗ РАСЧЕТ',
    '192 - (GOD) – ХОРОШ',
    '200 - (GLC) - ХОРОШ РАСЧЕТ',
    '216 - (GFO) - ХОРОШ ИМИТИР',
    '224 - (GLT) - ХОРОШ ЛОКАЛ ВРЕМ'
  ]

  const badNumericCode = [8, 16, 24, 28, 88]

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

  const defaultFields = reactive({})

  const getFields = async () => {
    await getDefaultFields(defaultFields)
  }

  const setFields = async (fields) => {
    Object.assign(defaultFields, fields)
    await changeDefaultFields(defaultFields)
  }

  const firstRaw = 0
  const lastRaw = 100
  const itemSize = 12

  return {
    badCode,
    qualitiesName,
    badNumericCode,
    deltaTimeInSeconds,
    estimatedSliceRateInHours,
    estimatedGridRateInHours,
    estimatedBounceRateInHours,
    sliceTimeLimitInHours,
    gridTimeLimitInHours,
    bounceTimeLimitInHours,
    defaultFields,
    getFields,
    setFields,
    firstRaw,
    lastRaw,
    itemSize
  }
})

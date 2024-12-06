<script>
import { ref, onMounted, onBeforeUnmount, onUnmounted } from 'vue'
import { useConfirm } from 'primevue/useconfirm'

import { storeToRefs } from 'pinia'

import Multiselect from '@vueform/multiselect'

import {
  getClientMode,
  getServerConfig,
  getLastUpdateFileKKS,
  runUpdate,
  changeUpdateFile,
  cancelUpdate,
  getIpAndPortConfig,
  changeClientMode,
  changeOpcServerConfig,
  changeCHServerConfig,
  getTypesOfSensors
} from '../stores'

import { useApplicationStore } from '../stores/applicationStore'
import { socket } from '../socket'

export default {
  name: 'Configurator',
  components: { Multiselect },
  setup() {
    const applicationStore = useApplicationStore()
    const { getQualitiesName, getBadQualityDescr, getBadCode, getFields, setFields } = applicationStore

    const { qualitiesName, defaultFields,
      sensorsAndTemplateValueShow, exceptionDirectoriesShow } = storeToRefs(applicationStore)

    const lastUpdateFileKKS = ref('')
    const configServer = ref('')

    const modeClientRadio = ref('')
    const changeModeClient = async () => {
      await changeClientMode(modeClientRadio.value)
      await getClientMode(modeClientRadio)
      await getServerConfig(configServer, checkFileActive)
      statusUpdateTextArea.value = configServer.value
      await getLastUpdateFileKKS(lastUpdateFileKKS)
      if (!checkFileActive.value) return
      await getTypesOfSensors(defaultTypesOfSensorsDataOptions)
      await getQualitiesName()
      await getBadQualityDescr()
      await getBadCode()
      await getFields()
    }

    const ipOPC = ref('')
    const portOPC = ref(0)

    const ipCH = ref('')
    const portCH = ref(0)
    const usernameCH = ref('')
    const passwordCH = ref('')

    const statusUpdateTextArea = ref('Лог')
    const statusUpdateButtonActive = ref(false)

    const runUpdateFlag = ref(false)

    const checkFileActive = ref(false)

    const confirm = useConfirm()
    const confirmUpdate = () => {
      if (modeClientRadio.value === 'OPC') {
        confirm.require({
          message: 'Вы действительго хотите запустить обновление тегов KKS?',
          header: 'Подтверждение обновления тегов',
          icon: 'pi pi-exclamation-triangle',
          rejectClass: 'p-button-secondary p-button-outlined',
          rejectLabel: 'Отмена',
          acceptLabel: 'Подтвердить',
          accept: () => {
            onButtonDialogUpdate()
          },
          reject: () => {
            return
          }
        })
      } else onButtonDialogUpdate()
    }

    const changeUpdate = async () => {
      statusUpdateButtonActive.value = true
      await changeUpdateFile(
        defaultFields.value.rootDirectory,
        exceptionDirectoriesShow.value
          .split(',')
          .map((item) => item.trim())
          .filter((item) => item.length),
        defaultFields.value.exceptionExpertTags
      )
      await getServerConfig(configServer, checkFileActive)
      statusUpdateButtonActive.value = false
      if (!checkFileActive.value) {
        alert('Файл тегов не найден')
        return
      }
      checkFileActive.value = true
      await getLastUpdateFileKKS(lastUpdateFileKKS)
    }

    const defaultTypesOfSensorsDataOptions = ref([
      {
        label: 'Выбрать все типы данных',
        options: []
      }
    ])

    async function onDefaultTypesOfSensorsDataChange(val) {
      defaultFields.value.typesOfSensors = val
    }

    function onDefaultMultiselectQualitiesChange(val) {
      defaultFields.value.quality = val
    }

    const defaultMaxDateTime = ref(new Date())

    function onDefaultDateDeepOfSearchClick() {
      defaultMaxDateTime.value = new Date()
    }

    function onDefaultDateDeepOfSearchTodayClick() {
      defaultFields.value.dateDeepOfSearch = new Date()
    }

    let changeDefaultTimeout = null
    const changeDefaultFields = async () => {
      if (changeDefaultTimeout) {
        clearTimeout(changeDefaultTimeout)
      }

      changeDefaultTimeout = setTimeout(async function () {
        statusUpdateButtonActive.value = true
        let formatDateDeepOfSearch = new Date(
          defaultFields.value.dateDeepOfSearch.toString().split('GMT')[0] + ' UTC'
        ).toISOString()
        let defaultSaveFields = {
          typesOfSensors: defaultFields.value.typesOfSensors,
          selectionTag: defaultFields.value.selectionTag,
          sensorsAndTemplateValue: sensorsAndTemplateValueShow.value
            .split(',')
            .map((item) => item.trim())
            .filter((item) => item.length),
          quality: defaultFields.value.quality,
          lastValueChecked: defaultFields.value.lastValueChecked,
          filterTableChecked: defaultFields.value.filterTableChecked,
          intervalDeepOfSearch: defaultFields.value.intervalDeepOfSearch,
          dimensionDeepOfSearch: defaultFields.value.dimensionDeepOfSearch,
          dateDeepOfSearch: formatDateDeepOfSearch,
          interval: defaultFields.value.interval,
          dimension: defaultFields.value.dimension,
          countShowSensors: defaultFields.value.countShowSensors
        }
        if (modeClientRadio.value === 'OPC') {
          let separateTags = {
            modeOfFilter: defaultFields.value.modeOfFilter,
            rootDirectory: defaultFields.value.rootDirectory,
            exceptionDirectories: exceptionDirectoriesShow.value
              .split(',')
              .map((item) => item.trim())
              .filter((item) => item.length),
            exceptionExpertTags: defaultFields.value.exceptionExpertTags
          }
          defaultSaveFields = { ...defaultSaveFields, ...separateTags }
        }
        await setFields(defaultSaveFields)
        await getFields()
        statusUpdateTextArea.value = 'Параметры по умолчанию сохранены...\n'
        statusUpdateButtonActive.value = false
      }, 500)
    }

    onMounted(async () => {
      window.addEventListener('beforeunload', async (event) => {
        await cancelUpdate()
      })

      statusUpdateButtonActive.value = true

      await getClientMode(modeClientRadio)
      await getServerConfig(configServer, checkFileActive)
      await getLastUpdateFileKKS(lastUpdateFileKKS)
      await getIpAndPortConfig(ipOPC, portOPC, ipCH, portCH, usernameCH, passwordCH)

      statusUpdateTextArea.value = configServer.value
      if (!checkFileActive.value) {
        alert('Не найден файл kks_all.csv.\nСконфигурируйте клиент OPC UA и обновите файл тегов')
        statusUpdateButtonActive.value = false
        return
      }

      await getTypesOfSensors(defaultTypesOfSensorsDataOptions)
      await getQualitiesName()
      await getBadQualityDescr()
      await getBadCode()
      await getFields()
      statusUpdateButtonActive.value = false
    })

    onBeforeUnmount(async () => {
      window.removeEventListener('beforeunload', async (event) => {})
    })

    onUnmounted(async () => {
      await cancelUpdate()
    })

    async function onButtonDialogUpdate() {
      changeOpcServerConfig(ipOPC.value, portOPC.value)
      runUpdateFlag.value = true
      statusUpdateButtonActive.value = true
      statusUpdateTextArea.value = ''
      statusUpdateTextArea.value += 'Запуск обновления тегов...\n'
      await runUpdate(
        defaultFields.value.modeOfFilter,
        defaultFields.value.rootDirectory,
        exceptionDirectoriesShow.value
          .split(',')
          .map((item) => item.trim())
          .filter((item) => item.length),
        defaultFields.value.exceptionExpertTags
      )
      runUpdateFlag.value = false
      await getServerConfig(configServer, checkFileActive)
      statusUpdateButtonActive.value = false
      if (!checkFileActive.value) {
        alert('Файл тегов не найден')
        return
      }
      checkFileActive.value = true
      await getLastUpdateFileKKS(lastUpdateFileKKS)
    }

    socket.on('setUpdateStatus', (updateStatus) => {
      if (updateStatus.serviceFlag) statusUpdateTextArea.value += String(updateStatus.statusString)
      else {
        let textSplit = statusUpdateTextArea.value.trim('\n').split('\n')
        textSplit[textSplit.length - 1] = updateStatus.statusString
        statusUpdateTextArea.value = textSplit.join('\n')
      }
      let textarea = document.getElementById('status-text-area')
      textarea.scrollTop = textarea.scrollHeight
    })

    function onButtonCancelUpdateClick() {
      if (statusUpdateButtonActive.value) cancelUpdate()
    }

    let inputTimeout = null
    function changeConfigOPC($event) {
      // в либе PrimeVue не работает v-model при вводе через клавиатуру
      // приходится выполнять хак

      if (inputTimeout) {
        clearTimeout(inputTimeout)
      }

      inputTimeout = setTimeout(async function () {
        try {
          const numberTarget = $event.originalEvent.target
          numberTarget.blur()
          numberTarget.focus()
        } catch (e) {
          console.log(e)
        }
        if (ipOPC.value.length === 0 || !portOPC.value) {
          alert('Заполните IP адрес и порт')
          return
        }
        await changeOpcServerConfig(ipOPC.value, portOPC.value)
        await getServerConfig(configServer, checkFileActive)
        await getIpAndPortConfig(ipOPC, portOPC, ipCH, portCH, usernameCH, passwordCH)
      }, 500)
    }

    function changeConfigCH($event) {
      // в либе PrimeVue не работает v-model при вводе через клавиатуру
      // приходится выполнять хак
      if (inputTimeout) {
        clearTimeout(inputTimeout)
      }

      inputTimeout = setTimeout(async function () {
        try {
          const numberTarget = $event.originalEvent.target
          numberTarget.blur()
          numberTarget.focus()
        } catch (e) {
          console.log(e)
        }
        if (ipCH.value.length === 0 || !portCH.value) {
          alert('Заполните IP адрес и порт')
          return
        }
        await changeCHServerConfig(ipCH.value, portCH.value, usernameCH.value, passwordCH.value)
        await getServerConfig(configServer, checkFileActive)
        await getIpAndPortConfig(ipOPC, portOPC, ipCH, portCH, usernameCH, passwordCH)
      }, 500)
    }

    async function exportConfigDownloadClick() {
      const linkConfigJson = document.createElement('a')
      linkConfigJson.download = 'config.json'
      const dataConfigJson = await fetch('config.json').then((res) => res.blob())
      linkConfigJson.href = window.URL.createObjectURL(
        new Blob([dataConfigJson], { type: 'application/json' })
      )
      linkConfigJson.click()
      linkConfigJson.remove()
      window.URL.revokeObjectURL(linkConfigJson.href)
    }

    async function uploadConfig(xhr, files) {
      statusUpdateButtonActive.value = true
      await new Promise((resolve) => {
        socket.emit('upload_config', xhr.files[0], (status) => {
          alert(status)
          resolve(status)
        })
      })
      await getClientMode(modeClientRadio)
      await getServerConfig(configServer, checkFileActive)
      await getIpAndPortConfig(ipOPC, portOPC, ipCH, portCH, usernameCH, passwordCH)
      await getLastUpdateFileKKS(lastUpdateFileKKS)
      await getTypesOfSensors(defaultTypesOfSensorsDataOptions)
      await getQualitiesName()
      await getBadQualityDescr()
      await getBadCode()
      await getFields()
      statusUpdateButtonActive.value = false
    }

    async function uploadQuality(xhr, files) {
      statusUpdateButtonActive.value = true
      await new Promise((resolve) => {
        socket.emit('upload_quality', xhr.files[0], (status) => {
          alert(status)
          resolve(status)
        })
      })
      await getQualitiesName()
      await getBadQualityDescr()
      await getBadCode()
      await getFields()
      statusUpdateButtonActive.value = false
    }

    async function exportQualityDownloadClick() {
      const linkQualityCsv = document.createElement('a')
      linkQualityCsv.download = 'quality.csv'
      const dataQualityCsv = await fetch('quality.csv').then((res) => res.blob())
      linkQualityCsv.href = window.URL.createObjectURL(
        new Blob([dataQualityCsv], { type: 'text/csv' })
      )
      linkQualityCsv.click()
      linkQualityCsv.remove()
      window.URL.revokeObjectURL(linkQualityCsv.href)
    }

    return {
      lastUpdateFileKKS,
      configServer,
      modeClientRadio,
      changeModeClient,
      ipOPC,
      portOPC,
      ipCH,
      portCH,
      usernameCH,
      passwordCH,
      changeConfigOPC,
      changeConfigCH,
      statusUpdateTextArea,
      statusUpdateButtonActive,
      runUpdateFlag,
      checkFileActive,
      onButtonCancelUpdateClick,
      confirmUpdate,
      changeUpdate,
      defaultTypesOfSensorsDataOptions,
      onDefaultTypesOfSensorsDataChange,
      qualitiesName,
      onDefaultMultiselectQualitiesChange,
      defaultMaxDateTime,
      onDefaultDateDeepOfSearchClick,
      onDefaultDateDeepOfSearchTodayClick,
      changeDefaultFields,
      exportConfigDownloadClick,
      uploadConfig,
      defaultFields,
      sensorsAndTemplateValueShow,
      exceptionDirectoriesShow,
      uploadQuality,
      exportQualityDownloadClick
    }
  }
}
</script>

<template>
  <div class="container">
    <div class="row">
      <div class="col">
        <h4>Сведения о конфигурации</h4>
      </div>
    </div>
    <div class="row align-items-center">
      <div class="col-6" v-if="modeClientRadio === 'OPC'">
        Дата последнего обновления файла тегов KKS: <b>{{ lastUpdateFileKKS }}</b>
      </div>
      <div class="col-6" v-if="modeClientRadio === 'CH'">
        Дата последнего обновления таблицы тегов KKS: <b>{{ lastUpdateFileKKS }}</b>
      </div>
      <div class="col text-end">
        <FileUpload
          mode="basic"
          name="config[]"
          url="/upload_config"
          accept=".json"
          :maxFileSize="1000000"
          :auto="true"
          :customUpload="true"
          :disabled="statusUpdateButtonActive"
          chooseLabel="Импорт конфигурации"
          style="border-radius: 0px"
          @uploader="uploadConfig"
        />
        <!--        <Button :disabled="statusUpdateButtonActive">Импорт конфигурации</Button>-->
      </div>
      <div class="col text-end">
        <Button @click="exportConfigDownloadClick" :disabled="statusUpdateButtonActive"
          >Экспорт конфигурации</Button
        >
      </div>
    </div>
    <div class="row align-items-center components-margin-bottom">
      <div class="col-6"></div>
      <div class="col text-end">
        <FileUpload
          mode="basic"
          name="config[]"
          url="/upload_quality"
          accept=".csv"
          :maxFileSize="1000000"
          :auto="true"
          :customUpload="true"
          :disabled="statusUpdateButtonActive"
          chooseLabel="Импорт кодов качеств"
          style="border-radius: 0px"
          @uploader="uploadQuality"
        />
      </div>
      <div class="col text-end">
        <Button @click="exportQualityDownloadClick" :disabled="statusUpdateButtonActive"
          >Экспорт кодов качеств</Button
        >
      </div>
    </div>
    <hr />
    <div class="row">
      <div class="col-md-auto">
        <h4>Выбор клиента для получения данных:</h4>
      </div>
      <div class="col-md-auto">
        <RadioButton
          v-model="modeClientRadio"
          inputId="modeClientOPCDefault"
          name="modeClientOPCDefault"
          value="OPC"
          :disabled="statusUpdateButtonActive"
          @change="changeModeClient"
        />
        <label for="modeClientOPCDefault" class="radio-interval-margin">OPC UA</label>
      </div>
      <div class="col-md-auto">
        <RadioButton
          v-model="modeClientRadio"
          inputId="modeClientCHDefault"
          name="modeClientCHDefault"
          value="CH"
          :disabled="statusUpdateButtonActive"
          @change="changeModeClient"
        />
        <label for="modeClientCHDefault" class="radio-interval-margin">Clickhouse DB</label>
      </div>
    </div>
    <div class="row">
      <div class="col">
        <h4>Изменить параметры конфигурации клиента</h4>
      </div>
    </div>
    <div class="row components-margin-bottom">
      <div class="col" v-if="modeClientRadio === 'OPC'">
        <FloatLabel>
          <InputText
            v-model="ipOPC"
            type="text"
            id="ip-opc-server-address"
            pattern="(\b25[0-5]|\b2[0-4][0-9]|\b[01]?[0-9][0-9]?)(\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)){3}"
            required
            :disabled="statusUpdateButtonActive"
            @input="changeConfigOPC"
            style="width: 90%"
          >
          </InputText>
          <label for="ip-opc-server-address">IP адрес сервера OPC UA</label>
        </FloatLabel>
      </div>
      <div class="col-2" v-if="modeClientRadio === 'CH'">
        <FloatLabel>
          <InputText
            v-model="ipCH"
            type="text"
            id="ip-ch-server-address"
            pattern="(\b25[0-5]|\b2[0-4][0-9]|\b[01]?[0-9][0-9]?)(\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)){3}"
            required
            :disabled="statusUpdateButtonActive"
            @input="changeConfigCH"
            style="width: 100%"
          >
          </InputText>
          <label for="ip-ch-server-address">IP адрес БД Clickhouse</label>
        </FloatLabel>
      </div>
      <div class="col" v-if="modeClientRadio === 'OPC'">
        <FloatLabel>
          <InputNumber
            v-model:="portOPC"
            id="port-opc-server-address"
            input-id="port"
            :useGrouping="false"
            mode="decimal"
            show-buttons
            :min="0"
            :step="1"
            :allow-empty="true"
            :disabled="statusUpdateButtonActive"
            @input="changeConfigOPC"
            style="width: 90%"
          >
          </InputNumber>
          <label for="port-opc-server-address">Порт сервера OPC UA</label>
        </FloatLabel>
      </div>
      <div class="col-2" v-if="modeClientRadio === 'CH'">
        <FloatLabel>
          <InputNumber
            v-model:="portCH"
            id="port-ch-server-address"
            input-id="port"
            :useGrouping="false"
            mode="decimal"
            show-buttons
            :min="0"
            :step="1"
            :allow-empty="true"
            :disabled="statusUpdateButtonActive"
            @input="changeConfigCH"
            inputStyle="width: 100%"
          >
          </InputNumber>
          <label for="port-ch-server-address">Порт</label>
        </FloatLabel>
      </div>
      <div class="col-2" v-if="modeClientRadio === 'CH'">
        <FloatLabel>
          <InputText
            v-model="usernameCH"
            type="text"
            id="ch-username"
            required
            :disabled="statusUpdateButtonActive"
            @input="changeConfigCH"
            style="width: 100%"
          >
          </InputText>
          <label for="ch-username">Имя пользователя</label>
        </FloatLabel>
      </div>
      <div class="col-2" v-if="modeClientRadio === 'CH'">
        <FloatLabel>
          <!--          <InputText-->
          <!--            v-model="passwordCH"-->
          <!--            type="text"-->
          <!--            id="ch-password"-->
          <!--            required-->
          <!--            :disabled="statusUpdateButtonActive"-->
          <!--            @input="changeConfigCH"-->
          <!--            style="width: 100%"-->
          <!--          >-->
          <!--          </InputText>-->
          <Password
            v-model="passwordCH"
            :toggleMask="true"
            :feedback="false"
            id="ch-password"
            required
            :disabled="statusUpdateButtonActive"
            @input="changeConfigCH"
          >
          </Password>
          <label for="ch-password">Пароль</label>
        </FloatLabel>
      </div>
      <div class="col text-end">
        <Button
          v-if="statusUpdateButtonActive && runUpdateFlag"
          label="Отмена"
          icon="pi pi-times"
          @click="onButtonCancelUpdateClick"
          severity="danger"
          style="width: 42%; text-align: center"
        />
        <ConfirmDialog></ConfirmDialog>
        <Button
          v-if="(!statusUpdateButtonActive || !runUpdateFlag) && modeClientRadio === 'OPC'"
          label="Обновить"
          icon="pi pi-check"
          :disabled="statusUpdateButtonActive"
          @click="confirmUpdate"
          style="width: 42%; text-align: center"
        />
        <Button
          v-if="(!statusUpdateButtonActive || !runUpdateFlag) && modeClientRadio === 'CH'"
          label="Тест"
          icon="pi pi-check"
          :disabled="statusUpdateButtonActive"
          @click="confirmUpdate"
          style="width: 42%; text-align: center"
        />
      </div>
    </div>
    <div class="row components-margin-bottom" v-if="modeClientRadio === 'OPC'">
      <div class="col">
        <h4>Отбор тегов</h4>
      </div>
    </div>
    <div class="row align-items-center" v-if="modeClientRadio === 'OPC'">
      <div class="col-3">Режим фильтрации обновления тегов:</div>
      <div class="col-2">
        <RadioButton
          v-model="defaultFields.modeOfFilter"
          inputId="modeFilterHistorianDefault"
          name="modeFilterHistorianDefault"
          value="historian"
          :disabled="statusUpdateButtonActive"
          @change="changeDefaultFields"
        />
        <label for="modeFilterHistorianDefault" class="radio-interval-margin">Historian</label>
      </div>
      <div class="col-7">
        <label for="default-root-directory">Корневая папка</label><br />
        <InputText
          v-model="defaultFields.rootDirectory"
          type="text"
          id="default-root-directory"
          :disabled="statusUpdateButtonActive || defaultFields.modeOfFilter === 'historian'"
          style="width: 100%"
          @input="changeDefaultFields"
        >
        </InputText>
      </div>
    </div>
    <div class="row align-items-center" v-if="modeClientRadio === 'OPC'">
      <div class="col-3">
        <Button
          v-if="checkFileActive"
          @click="changeUpdate"
          :disabled="statusUpdateButtonActive || defaultFields.modeOfFilter === 'historian'"
          style="width: 90%"
          >Применить список исключений к файлу тегов</Button
        >
      </div>
      <div class="col-2">
        <RadioButton
          v-model="defaultFields.modeOfFilter"
          inputId="modeFilterExceptionDefault"
          name="modeFilterExceptionDefault"
          value="exception"
          :disabled="statusUpdateButtonActive"
          @change="changeDefaultFields"
        />
        <label for="modeFilterExceptionDefault" class="radio-interval-margin"
          >Список исключений</label
        >
      </div>
      <div class="col-7">
        <label for="default-exception-directories"
          >Список исключений (перечислите через запятую регулярные выражения)</label
        ><br />
        <InputText
          v-model="exceptionDirectoriesShow"
          type="text"
          id="default-exception-directories"
          :disabled="statusUpdateButtonActive || defaultFields.modeOfFilter === 'historian'"
          style="width: 100%"
          @input="changeDefaultFields"
        >
        </InputText>
        <Checkbox
          id="default-exception-expert-tags"
          v-model="defaultFields.exceptionExpertTags"
          :binary="true"
          :disabled="statusUpdateButtonActive || defaultFields.modeOfFilter === 'historian'"
          @change="changeDefaultFields"
        ></Checkbox>
        <label for="default-exception-expert-tags" class="checkbox-margin"
          >Исключить теги, помеченные экспертом</label
        >
      </div>
    </div>
    <div class="row components-margin-bottom">
      <div class="col">
        <TextArea
          id="status-text-area"
          v-model="statusUpdateTextArea"
          rows="3"
          cols="80"
          readonly
          :style="{ resize: 'none', 'overflow-y': scroll, width: '100%' }"
          >{{ statusUpdateTextArea }}</TextArea
        >
      </div>
    </div>
    <hr />
    <div class="row align-items-center" v-if="checkFileActive">
      <div class="col-8 text-start">
        <h4>Установка параметров по умолчанию</h4>
      </div>
      <div class="col-4 text-end">
        <Button @click="changeDefaultFields" :disabled="statusUpdateButtonActive"
          >Сохранить параметры</Button
        >
      </div>
    </div>
    <div class="row" v-if="checkFileActive">
      <div class="col">
        <label for="typesOfSensorsDataSignals">Выберите тип данных тегов по умолчанию</label>
        <Multiselect
          id="typesOfSensorsDataSignals"
          v-model="defaultFields.typesOfSensors"
          mode="tags"
          :close-on-select="false"
          :groups="true"
          :options="defaultTypesOfSensorsDataOptions"
          :searchable="true"
          :create-option="false"
          placeholder="Выберите тип данных тегов по умочанию"
          limit="-1"
          @change="onDefaultTypesOfSensorsDataChange"
          :disabled="statusUpdateButtonActive"
        ></Multiselect>
      </div>
    </div>
    <div class="row g-0 align-items-center" v-if="checkFileActive">
      <div class="col-3">Применять фильтр по умолчанию как:</div>
      <div class="col-3">
        <RadioButton
          v-model="defaultFields.selectionTag"
          id="sequentialDefault"
          inputId="sequentialDefault"
          name="sequential"
          value="sequential"
          :disabled="statusUpdateButtonActive"
        />
        <label for="sequentialDefault" class="radio-interval-margin"
          >Последовательные шаблоны</label
        >
      </div>
      <div class="col-3">
        <RadioButton
          v-model="defaultFields.selectionTag"
          id="unionDefault"
          inputId="unionDefault"
          name="union"
          value="union"
          :disabled="statusUpdateButtonActive"
        />
        <label for="unionDefault" class="radio-interval-margin">Объединение шаблонов</label>
      </div>
    </div>
    <div class="row" v-if="checkFileActive">
      <div class="col">
        <label for="default-template"
          >Шаблон тегов по умолчанию (перечислите шаблоны или теги через запятую)</label
        >
        <InputText
          v-model="sensorsAndTemplateValueShow"
          type="text"
          id="default-template"
          :disabled="statusUpdateButtonActive"
          style="width: 100%"
        >
        </InputText>
      </div>
    </div>
    <div class="row" v-if="checkFileActive">
      <div class="col">
        <h4>Параметры отчетов</h4>
      </div>
    </div>
    <div class="row" v-if="checkFileActive">
      <div class="col text-start">
        <label for="qualitySignals">Код качества сигнала по умолчанию</label>
        <Multiselect
          id="qualitySignals"
          v-model="defaultFields.quality"
          mode="tags"
          :close-on-select="false"
          :searchable="true"
          :create-option="false"
          :groups="true"
          :options="qualitiesName"
          placeholder="Выберите код качества сигнала по умолчанию"
          limit="-1"
          @change="onDefaultMultiselectQualitiesChange"
          :disabled="statusUpdateButtonActive"
        ></Multiselect>
      </div>
      <div class="col">
        <div class="row">
          <div class="col">
            <label for="intervalDeepOfSearch">Глубина поиска в архивах по умолчанию</label><br />
            <InputNumber
              v-model="defaultFields.intervalDeepOfSearch"
              id="intervalDeepOfSearch"
              input-id="intervalDeepOfSearch"
              :useGrouping="false"
              mode="decimal"
              show-buttons
              :min="1"
              :step="1"
              :allow-empty="false"
              :disabled="statusUpdateButtonActive"
              style="width: 100%"
            >
            </InputNumber>
          </div>
          <div class="col">
            <label for="calendarDateDeepOfSearchSignals">Дата глубины поиска в архивах</label><br />
            <Calendar
              id="calendarDateDeepOfSearchSignals"
              v-model="defaultFields.dateDeepOfSearch"
              :maxDate="defaultMaxDateTime"
              show-time
              hour-format="24"
              show-seconds="true"
              placeholder="ДД/ММ/ГГ ЧЧ:ММ:СС"
              :manualInput="true"
              date-format="dd/mm/yy"
              show-icon
              show-button-bar
              @click="onDefaultDateDeepOfSearchClick"
              :showOnFocus="false"
              @todayClick="onDefaultDateDeepOfSearchTodayClick"
              :disabled="statusUpdateButtonActive"
              style="width: 100%"
            ></Calendar>
          </div>
          <div class="col-12">
            <RadioButton
              v-model="defaultFields.dimensionDeepOfSearch"
              id="dayDefaultDeepOfSearch"
              inputId="dayDefaultDeepOfSearch"
              name="day"
              value="day"
              :disabled="statusUpdateButtonActive"
            />
            <label for="dayDefaultDeepOfSearch" class="radio-interval-margin">День</label>
            <RadioButton
              v-model="defaultFields.dimensionDeepOfSearch"
              id="hourDefaultDeepOfSearch"
              inputId="hourDefaultDeepOfSearch"
              name="hour"
              value="hour"
              :disabled="statusUpdateButtonActive"
            />
            <label for="hourDefaultDeepOfSearch" class="radio-interval-margin">Час</label>
            <RadioButton
              v-model="defaultFields.dimensionDeepOfSearch"
              id="minuteDefaultDeepOfSearch"
              inputId="minuteDefaultDeepOfSearch"
              name="minute"
              value="minute"
              :disabled="statusUpdateButtonActive"
            />
            <label for="minuteDefaultDeepOfSearch" class="radio-interval-margin">Минута</label>
            <RadioButton
              v-model="defaultFields.dimensionDeepOfSearch"
              id="secondDefaultDeepOfSearch"
              inputId="secondDefaultDeepOfSearch"
              name="second"
              value="second"
              :disabled="statusUpdateButtonActive"
            />
            <label for="secondDefaultDeepOfSearch" class="radio-interval-margin">Секунда</label>
          </div>
          <div class="col-12">
            <Checkbox
              id="lastValueChecked"
              v-model="defaultFields.lastValueChecked"
              :binary="true"
              :disabled="statusUpdateButtonActive"
            ></Checkbox>
            <label for="lastValueChecked" class="checkbox-margin"
              >Искать последние по времени значения</label
            >
          </div>
          <div class="col-12">
            <Checkbox
              id="filterTableChecked"
              v-model="defaultFields.filterTableChecked"
              :binary="true"
              :disabled="statusUpdateButtonActive"
            ></Checkbox>
            <label for="filterTableChecked" class="checkbox-margin"
              >Добавить фильтры к таблицам отчетов</label
            >
          </div>
        </div>
      </div>
    </div>
    <div class="row" v-if="checkFileActive">
      <div class="col-3">
        <label for="intervalDefaultGrid">Интервал по умолчанию: </label><br />
        <InputNumber
          v-model="defaultFields.interval"
          id="intervalDefaultGrid"
          input-id="intervalDefaultGrid"
          :useGrouping="false"
          mode="decimal"
          show-buttons
          :min="1"
          :step="1"
          :allow-empty="false"
          :disabled="statusUpdateButtonActive"
          style="width: 100%"
        >
        </InputNumber>
      </div>
      <div class="col-9">
        <label for="show-default-sensors">Показываемые датчики по умолчанию</label><br />
        <InputNumber
          v-model="defaultFields.countShowSensors"
          id="show-default-sensors"
          input-id="defaultCountShowSensors"
          :useGrouping="false"
          mode="decimal"
          show-buttons
          :min="1"
          :step="1"
          :allow-empty="false"
          :disabled="statusUpdateButtonActive"
          style="width: 32.1%"
        >
        </InputNumber>
      </div>
    </div>
    <div class="row" v-if="checkFileActive">
      <div class="col">
        <RadioButton
          v-model="defaultFields.dimension"
          id="dayDefault"
          inputId="dayDefault"
          name="day"
          value="day"
          :disabled="statusUpdateButtonActive"
        />
        <label for="dayDefault" class="radio-interval-margin">День</label>
        <RadioButton
          v-model="defaultFields.dimension"
          id="hourDefault"
          inputId="hourDefault"
          name="hour"
          value="hour"
          :disabled="statusUpdateButtonActive"
        />
        <label for="hourDefault" class="radio-interval-margin">Час</label>
        <RadioButton
          v-model="defaultFields.dimension"
          id="minuteDefault"
          inputId="minuteDefault"
          name="minute"
          value="minute"
          :disabled="statusUpdateButtonActive"
        />
        <label for="minuteDefault" class="radio-interval-margin">Минута</label>
        <RadioButton
          v-model="defaultFields.dimension"
          id="secondDefault"
          inputId="secondDefault"
          name="second"
          value="second"
          :disabled="statusUpdateButtonActive"
        />
        <label for="secondDefault" class="radio-interval-margin">Секунда</label>
      </div>
      <div class="col"></div>
    </div>
  </div>
</template>

<style>
.checkbox-margin {
  margin-left: 5px;
}
.radio-interval-margin {
  margin-left: 5px;
  margin-right: 5px;
}
.components-margin-bottom {
  margin-bottom: 10px;
  margin-top: 10px;
}
</style>

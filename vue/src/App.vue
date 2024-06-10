<script>
import { ref, onMounted } from 'vue'
import { useConfirm } from 'primevue/useconfirm'

import Multiselect from '@vueform/multiselect'

import {
  getServerConfig,
  getLastUpdateFileKKS,
  runUpdate,
  cancelUpdate,
  getIpAndPortConfig,
  changeOpcServerConfig,
  getTypesOfSensors
} from './stores'

import { useApplicationStore } from './stores/applicationStore'
import { socket } from './socket'

export default {
  components: { Multiselect },
  setup() {
    const applicationStore = useApplicationStore()

    applicationStore.getFields()

    const sidebarMenu = [
      {
        header: 'Меню отчетов',
        hiddenOnCollapse: true
      },
      {
        href: '/',
        title: 'Срезы сигналов'
      },
      {
        href: '/grid_report',
        title: 'Сетка сигналов'
      },
      {
        href: '/bounce_signals',
        title: 'Дребезг сигналов'
      }
    ]

    const collapsed = ref(false)

    const dialogConfiguratorActive = ref(false)
    const lastUpdateFileKKS = ref('')
    const configServer = ref('')
    const ipOPC = ref('')
    const portOPC = ref(0)

    const buttonDialogConfiguratorIsDisabled = ref(false)

    const statusUpdateTextArea = ref('')
    const statusUpdateButtonActive = ref(false)

    const checkFileActive = ref(false)

    const confirm = useConfirm()
    const confirmUpdate = () => {
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
    }

    const defaultTypesOfSensorsDataValue = ref([])
    const defaultTypesOfSensorsDataOptions = ref([
      {
        label: 'Выбрать все типы данных',
        options: []
      }
    ])
    let defaultChosenTypesOfSensorsData = []

    async function onDefaultTypesOfSensorsDataChange(val) {
      defaultChosenTypesOfSensorsData = val
    }

    const defaultSelectionTagRadio = ref('')

    const defaultTemplate = ref('')

    const defaultQualitiesName = ref([
      {
        label: 'Выбрать все коды качества сигнала',
        options: applicationStore.qualitiesName
      }
    ])
    const defaultQuality = ref([])
    let defaultChosenQuality = []

    function onDefaultMultiselectQualitiesChange(val) {
      defaultChosenQuality = val
    }

    const defaultDateDeepOfSearch = ref(new Date())
    const defaultMaxDateTime = ref(new Date())

    function onDefaultDateDeepOfSearchClick() {
      defaultMaxDateTime.value = new Date()
    }

    function onDefaultDateDeepOfSearchTodayClick() {
      defaultDateDeepOfSearch.value = new Date()
    }

    const defaultInterval = ref(0)
    const defaultIntervalRadio = ref('')

    const defaultCountShowSensors = ref(0)

    const changeDefaultFields = () => {
      let defaultFields = {
        typesOfSensors: defaultChosenTypesOfSensorsData,
        selectionTag: defaultSelectionTagRadio.value,
        sensorsAndTemplateValue: defaultTemplate.value
          .split(',')
          .map((item) => item.trim())
          .filter((item) => item.length),
        quality: defaultChosenQuality,
        dateDeepOfSearch: defaultDateDeepOfSearch.value,
        interval: defaultInterval.value,
        dimension: defaultIntervalRadio.value,
        countShowSensors: defaultCountShowSensors.value
      }
      applicationStore.setFields(defaultFields)
      alert('Параметры по умолчанию сохранены')
      dialogConfiguratorActive.value = false
    }

    onMounted(async () => {
      await getServerConfig(configServer, checkFileActive)
      await getLastUpdateFileKKS(lastUpdateFileKKS)
      await getIpAndPortConfig(ipOPC, portOPC)

      statusUpdateTextArea.value = configServer.value
      if (!checkFileActive.value)
        alert('Не найден файл kks_all.csv.\nСконфигурируйте клиент OPC UA и обновите файл тегов')
      window.addEventListener('beforeunload', async (event) => {
        await cancelUpdate()
      })

      defaultTypesOfSensorsDataValue.value = applicationStore.defaultFields.typesOfSensors
      await getTypesOfSensors(defaultTypesOfSensorsDataOptions)
      defaultChosenTypesOfSensorsData = applicationStore.defaultFields.typesOfSensors

      defaultSelectionTagRadio.value = applicationStore.defaultFields.selectionTag

      defaultTemplate.value = applicationStore.defaultFields.sensorsAndTemplateValue.join(', ')

      defaultQuality.value = applicationStore.defaultFields.quality
      defaultChosenQuality = applicationStore.defaultFields.quality

      defaultDateDeepOfSearch.value = applicationStore.defaultFields.dateDeepOfSearch

      defaultInterval.value = applicationStore.defaultFields.interval
      defaultIntervalRadio.value = applicationStore.defaultFields.dimension

      defaultCountShowSensors.value = applicationStore.defaultFields.countShowSensors
    })

    function onButtonDialogConfiguratorActive() {
      dialogConfiguratorActive.value = true

      defaultTypesOfSensorsDataValue.value = applicationStore.defaultFields.typesOfSensors
      getTypesOfSensors(defaultTypesOfSensorsDataOptions)
      defaultChosenTypesOfSensorsData = applicationStore.defaultFields.typesOfSensors

      defaultSelectionTagRadio.value = applicationStore.defaultFields.selectionTag

      defaultTemplate.value = applicationStore.defaultFields.sensorsAndTemplateValue.join(', ')

      defaultQuality.value = applicationStore.defaultFields.quality
      defaultChosenQuality = applicationStore.defaultFields.quality

      defaultDateDeepOfSearch.value = applicationStore.defaultFields.dateDeepOfSearch

      defaultInterval.value = applicationStore.defaultFields.interval
      defaultIntervalRadio.value = applicationStore.defaultFields.dimension

      defaultCountShowSensors.value = applicationStore.defaultFields.countShowSensors
    }

    async function onButtonDialogUpdate() {
      statusUpdateButtonActive.value = true
      statusUpdateTextArea.value = ''
      statusUpdateTextArea.value += 'Запуск обновления тегов...\n'
      await runUpdate()
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
      dialogConfiguratorActive.value = false
    }

    function toggleButton(bool) {
      buttonDialogConfiguratorIsDisabled.value = bool
    }

    function changeConfig() {
      if (ipOPC.value.length === 0 || !portOPC.value) {
        alert('Заполните IP адрес и порт')
        return
      }
      changeOpcServerConfig(ipOPC.value, portOPC.value)
      getServerConfig(configServer, checkFileActive)
      getIpAndPortConfig(ipOPC, portOPC)
    }

    return {
      sidebarMenu,
      collapsed,
      dialogConfiguratorActive,
      lastUpdateFileKKS,
      configServer,
      ipOPC,
      portOPC,
      changeConfig,
      buttonDialogConfiguratorIsDisabled,
      statusUpdateTextArea,
      statusUpdateButtonActive,
      checkFileActive,
      onButtonDialogConfiguratorActive,
      onButtonCancelUpdateClick,
      toggleButton,
      confirmUpdate,
      defaultTypesOfSensorsDataValue,
      defaultTypesOfSensorsDataOptions,
      defaultChosenTypesOfSensorsData,
      onDefaultTypesOfSensorsDataChange,
      defaultSelectionTagRadio,
      defaultTemplate,
      defaultQualitiesName,
      defaultQuality,
      defaultChosenQuality,
      onDefaultMultiselectQualitiesChange,
      defaultDateDeepOfSearch,
      defaultMaxDateTime,
      onDefaultDateDeepOfSearchClick,
      onDefaultDateDeepOfSearchTodayClick,
      defaultInterval,
      defaultIntervalRadio,
      defaultCountShowSensors,
      changeDefaultFields
    }
  }
}
</script>

<template>
  <sidebar-menu v-model:collapsed="collapsed" :menu="sidebarMenu">
    <template v-slot:footer v-if="!collapsed">
      <Button
        @click="onButtonDialogConfiguratorActive"
        :disabled="buttonDialogConfiguratorIsDisabled"
        >Обновление файла тегов KKS</Button
      >
      <Dialog
        v-model="dialogConfiguratorActive"
        :visible="dialogConfiguratorActive"
        :closable="false"
        header="Конфигуратор клиента OPC UA"
        position="left"
        :modal="true"
        :draggable="true"
        :maximizable="true"
        :style="{ width: '60rem', resize: 'both', overflow: 'auto' }"
      >
        <div class="container">
          <div class="row">
            <div class="col">
              <h4>Сведения о конфигурации</h4>
            </div>
          </div>
          <div class="row">
            <div class="col">
              Дата последнего обновления файла тегов KKS: <b>{{ lastUpdateFileKKS }}</b>
            </div>
          </div>
          <div class="row">
            <div class="col">
              Параметры конфигурации: <b>{{ configServer }}</b>
            </div>
          </div>
          <hr />
          <div class="row">
            <div class="col">
              <h4>Изменить параметры конфигурации</h4>
            </div>
          </div>
          <div class="margin-label" style="margin-bottom: 20px"></div>
          <div class="row">
            <div class="col">
              <FloatLabel>
                <InputText
                  v-model="ipOPC"
                  type="text"
                  id="ip-opc-server-address"
                  pattern="(\b25[0-5]|\b2[0-4][0-9]|\b[01]?[0-9][0-9]?)(\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)){3}"
                  required
                  :disabled="statusUpdateButtonActive"
                >
                </InputText>
                <label for="ip-opc-server-address">IP адрес сервера OPC UA</label>
              </FloatLabel>
            </div>
            <div class="col">
              <FloatLabel>
                <InputNumber
                  v-model="portOPC"
                  id="port-opc-server-address"
                  input-id="port"
                  :useGrouping="false"
                  mode="decimal"
                  show-buttons
                  :min="0"
                  :step="1"
                  :allow-empty="true"
                  :aria-label="portOPC"
                  :disabled="statusUpdateButtonActive"
                >
                </InputNumber>
                <label for="port-opc-server-address">Порт сервера OPC UA</label>
              </FloatLabel>
            </div>
            <div class="col">
              <Button @click="changeConfig" :disabled="statusUpdateButtonActive">Сохранить</Button>
            </div>
          </div>
          <hr />
          <div class="row">
            <div class="col">
              <TextArea
                id="status-text-area"
                v-model="statusUpdateTextArea"
                rows="3"
                cols="80"
                readonly
                :style="{ resize: 'none', 'overflow-y': scroll }"
                >{{ statusUpdateTextArea }}</TextArea
              >
            </div>
          </div>
          <hr />
          <div class="row align-items-center">
            <div class="col-8 text-start">
              <h4>Установка параметров по умолчанию</h4>
            </div>
            <div class="col-4 text-end">
              <Button @click="changeDefaultFields" :disabled="statusUpdateButtonActive"
                >Сохранить параметры</Button
              >
            </div>
          </div>
          <div class="row">
            <div class="col">
              <h4>Отбор тегов</h4>
            </div>
          </div>
          <div class="row">
            <div class="col">
              <label for="typesOfSensorsDataSignals">Выберите тип данных тегов по умолчанию</label>
              <Multiselect
                id="typesOfSensorsDataSignals"
                v-model="defaultTypesOfSensorsDataValue"
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
          <div class="row">
            <div class="col">Применять фильтр по умолчанию как:</div>
          </div>
          <div class="row">
            <div class="col">
              <RadioButton
                v-model="defaultSelectionTagRadio"
                id="sequentialDefault"
                inputId="sequentialDefault"
                name="sequential"
                value="sequential"
                :disabled="statusUpdateButtonActive"
              />
              <label for="sequentialDefault">&nbsp;Последовательные шаблоны&nbsp;</label>
              <RadioButton
                v-model="defaultSelectionTagRadio"
                id="unionDefault"
                inputId="unionDefault"
                name="union"
                value="union"
                :disabled="statusUpdateButtonActive"
              />
              <label for="unionDefault">&nbsp;Объединение шаблонов&nbsp;</label>
            </div>
          </div>
          <div class="row">
            <div class="col">
              <label for="default-template"
                >Шаблон тегов по умолчанию (перечислите шаблоны или теги через запятую)</label
              >
              <InputText
                v-model="defaultTemplate"
                type="text"
                id="default-template"
                :disabled="statusUpdateButtonActive"
                style="width: 100%"
              >
              </InputText>
            </div>
          </div>
          <div class="row">
            <div class="col">
              <h4>Параметры отчетов срезов</h4>
            </div>
          </div>
          <div class="row">
            <div class="col text-start">
              <label for="qualitySignals">Код качества сигнала по умолчанию</label>
              <Multiselect
                id="qualitySignals"
                v-model="defaultQuality"
                mode="tags"
                :close-on-select="false"
                :searchable="true"
                :create-option="false"
                :groups="true"
                :options="defaultQualitiesName"
                placeholder="Выберите код качества сигнала по умолчанию"
                limit="-1"
                @change="onDefaultMultiselectQualitiesChange"
                :disabled="statusUpdateButtonActive"
              ></Multiselect>
            </div>
            <div class="col text-end">
              <label for="calendarDateDeepOfSearchSignals"
                >Глубина поиска в архивах по умолчанию</label
              >
              <Calendar
                id="calendarDateDeepOfSearchSignals"
                v-model="defaultDateDeepOfSearch"
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
              ></Calendar>
            </div>
          </div>
          <div class="row">
            <div class="col">
              <h4>Параметры отчетов сетки и дребезга</h4>
            </div>
          </div>
          <div class="row">
            <div class="col">
              <label for="intervalGrid">Интервал по умолчанию</label>
              <InputNumber
                v-model="defaultInterval"
                id="intervalGrid"
                input-id="intervalGrid"
                :useGrouping="false"
                mode="decimal"
                show-buttons
                :min="1"
                :step="1"
                :allow-empty="false"
                :disabled="statusUpdateButtonActive"
              >
              </InputNumber>
            </div>
            <div class="col text-end">
              <label for="show-default-sensors">Показываемые датчики по умолчанию</label>
              <InputNumber
                v-model="defaultCountShowSensors"
                id="show-default-sensors"
                input-id="defaultCountShowSensors"
                :useGrouping="false"
                mode="decimal"
                show-buttons
                :min="1"
                :step="1"
                :allow-empty="false"
                :disabled="statusUpdateButtonActive"
              >
              </InputNumber>
            </div>
          </div>
          <div class="row">
            <div class="col">
              <RadioButton
                v-model="defaultIntervalRadio"
                id="dayDefault"
                inputId="dayDefault"
                name="day"
                value="day"
                :disabled="statusUpdateButtonActive"
              />
              <label for="dayDefault">&nbsp;День&nbsp;</label>
              <RadioButton
                v-model="defaultIntervalRadio"
                id="hourDefault"
                inputId="hourDefault"
                name="hour"
                value="hour"
                :disabled="statusUpdateButtonActive"
              />
              <label for="hourDefault">&nbsp;Час&nbsp;</label>
              <RadioButton
                v-model="defaultIntervalRadio"
                id="minuteDefault"
                inputId="minuteDefault"
                name="minute"
                value="minute"
                :disabled="statusUpdateButtonActive"
              />
              <label for="minuteDefault">&nbsp;Минута&nbsp;</label>
              <RadioButton
                v-model="defaultIntervalRadio"
                id="secondDefault"
                inputId="secondDefault"
                name="second"
                value="second"
                :disabled="statusUpdateButtonActive"
              />
              <label for="secondDefault">&nbsp;Секунда</label>
            </div>
            <div class="col"></div>
          </div>
        </div>
        <template #footer>
          <Button label="Отмена" icon="pi pi-times" @click="onButtonCancelUpdateClick" text />
          <ConfirmDialog></ConfirmDialog>
          <Button
            label="Обновить"
            icon="pi pi-check"
            :disabled="statusUpdateButtonActive"
            @click="confirmUpdate"
          />
        </template>
      </Dialog>
    </template>
  </sidebar-menu>
  <div id="content" :class="[{ collapsed: collapsed }]">
    <div class="content">
      <div class="container" v-if="!checkFileActive">
        <h1>Не найден файл kks_all.csv.</h1>
        <h1>Сконфигурируйте клиент OPC UA и обновите файл тегов.</h1>
      </div>
      <div class="container" v-if="checkFileActive">
        <RouterView :collapsed-sidebar="collapsed" @toggleButtonDialogConfigurator="toggleButton" />
      </div>
    </div>
  </div>
</template>

<style>
#content {
  padding-left: 290px;
  transition: 0.3s ease;
}
#content.collapsed {
  padding-left: 65px;
}

.sidebar-overlay {
  position: fixed;
  width: 100%;
  height: 100%;
  top: 0;
  left: 0;
  background-color: #000;
  opacity: 0.5;
  z-index: 900;
}

.content {
  padding: 50px;
}

.container {
  max-width: 900px;
}
</style>

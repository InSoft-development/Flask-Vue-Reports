<script>
import { ref, onMounted } from 'vue'
import { useConfirm } from 'primevue/useconfirm'

import Multiselect from '@vueform/multiselect'

import {
  getServerConfig,
  getLastUpdateFileKKS,
  runUpdate,
  changeUpdateFile,
  cancelUpdate,
  getIpAndPortConfig,
  changeOpcServerConfig,
  getTypesOfSensors
} from '../stores'

import { useApplicationStore } from '../stores/applicationStore'
import { socket } from '../socket'

export default {
  name: 'Configurator',
  components: { Multiselect },
  setup() {
    const applicationStore = useApplicationStore()

    // applicationStore.getFields()

    const lastUpdateFileKKS = ref('')
    const configServer = ref('')
    const ipOPC = ref('')
    const portOPC = ref(0)

    const defaultModeOfFilterRadio = ref('')
    const defaultRootDirectory = ref('')
    const defaultExceptionDirectories = ref('')
    const defaultExceptionExpertTags = ref(false)

    const statusUpdateTextArea = ref('Лог')
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

    const changeUpdate = async () => {
      statusUpdateButtonActive.value = true
      await changeUpdateFile(
        defaultRootDirectory.value,
        defaultExceptionDirectories.value
          .split(',')
          .map((item) => item.trim())
          .filter((item) => item.length),
        defaultExceptionExpertTags.value
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

    const defaultTypesOfSensorsDataValue = ref([])
    const defaultTypesOfSensorsDataOptions = ref([
      {
        label: 'Выбрать все типы данных',
        options: applicationStore.defaultFields.typesOfSensors
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

    const defaultLastValueChecked = ref(false)
    const defaultFilterTableChecked = ref(false)

    const defaultIntervalDeepOfSearch = ref(0)
    const defaultDimensionDeepOfSearch = ref('')

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
        lastValueChecked: defaultLastValueChecked.value,
        filterTableChecked: defaultFilterTableChecked.value,
        intervalDeepOfSearch: defaultIntervalDeepOfSearch.value,
        dimensionDeepOfSearch: defaultDimensionDeepOfSearch.value,
        dateDeepOfSearch: defaultDateDeepOfSearch.value,
        interval: defaultInterval.value,
        dimension: defaultIntervalRadio.value,
        countShowSensors: defaultCountShowSensors.value,
        modeOfFilter: defaultModeOfFilterRadio.value,
        rootDirectory: defaultRootDirectory.value,
        exceptionDirectories: defaultExceptionDirectories.value
          .split(',')
          .map((item) => item.trim())
          .filter((item) => item.length),
        exceptionExpertTags: defaultExceptionExpertTags.value
      }
      applicationStore.setFields(defaultFields)
      alert('Параметры по умолчанию сохранены')
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

      defaultLastValueChecked.value = applicationStore.defaultFields.lastValueChecked
      defaultFilterTableChecked.value = applicationStore.defaultFields.filterTableChecked

      defaultIntervalDeepOfSearch.value = applicationStore.defaultFields.intervalDeepOfSearch
      defaultDimensionDeepOfSearch.value = applicationStore.defaultFields.dimensionDeepOfSearch

      defaultDateDeepOfSearch.value = applicationStore.defaultFields.dateDeepOfSearch

      defaultInterval.value = applicationStore.defaultFields.interval
      defaultIntervalRadio.value = applicationStore.defaultFields.dimension

      defaultCountShowSensors.value = applicationStore.defaultFields.countShowSensors

      defaultModeOfFilterRadio.value = applicationStore.defaultFields.modeOfFilter
      defaultRootDirectory.value = applicationStore.defaultFields.rootDirectory
      defaultExceptionDirectories.value =
        applicationStore.defaultFields.exceptionDirectories.join(', ')
      defaultExceptionExpertTags.value = applicationStore.defaultFields.exceptionExpertTags
    })

    // function onButtonDialogConfiguratorActive() {
    //   defaultTypesOfSensorsDataValue.value = applicationStore.defaultFields.typesOfSensors
    //   getTypesOfSensors(defaultTypesOfSensorsDataOptions)
    //   defaultChosenTypesOfSensorsData = applicationStore.defaultFields.typesOfSensors
    //
    //   defaultSelectionTagRadio.value = applicationStore.defaultFields.selectionTag
    //
    //   defaultTemplate.value = applicationStore.defaultFields.sensorsAndTemplateValue.join(', ')
    //
    //   defaultQuality.value = applicationStore.defaultFields.quality
    //   defaultChosenQuality = applicationStore.defaultFields.quality
    //
    //   defaultLastValueChecked.value = applicationStore.defaultFields.lastValueChecked
    //   defaultFilterTableChecked.value = applicationStore.defaultFields.filterTableChecked
    //
    //   defaultIntervalDeepOfSearch.value = applicationStore.defaultFields.intervalDeepOfSearch
    //   defaultDimensionDeepOfSearch.value = applicationStore.defaultFields.dimensionDeepOfSearch
    //
    //   defaultDateDeepOfSearch.value = applicationStore.defaultFields.dateDeepOfSearch
    //
    //   defaultInterval.value = applicationStore.defaultFields.interval
    //   defaultIntervalRadio.value = applicationStore.defaultFields.dimension
    //
    //   defaultCountShowSensors.value = applicationStore.defaultFields.countShowSensors
    //
    //   defaultModeOfFilterRadio.value = applicationStore.defaultFields.modeOfFilter
    //   defaultRootDirectory.value = applicationStore.defaultFields.rootDirectory
    //   defaultExceptionDirectories.value =
    //     applicationStore.defaultFields.exceptionDirectories.join(', ')
    //   defaultExceptionExpertTags.value = applicationStore.defaultFields.exceptionExpertTags
    // }

    async function onButtonDialogUpdate() {
      statusUpdateButtonActive.value = true
      statusUpdateTextArea.value = ''
      statusUpdateTextArea.value += 'Запуск обновления тегов...\n'
      await runUpdate(
        defaultModeOfFilterRadio.value,
        defaultRootDirectory.value,
        defaultExceptionDirectories.value
          .split(',')
          .map((item) => item.trim())
          .filter((item) => item.length),
        defaultExceptionExpertTags.value
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

    function changeConfig($event) {
      console.log('ChangeConfig')
      console.log(portOPC.value)
      // в либе PrimeVue не работает v-model при вводе через клавиатуру
      // приходится выполнять хак
      try {
        const numberTarget = $event.originalEvent.target
        console.log($event.originalEvent.target)
        numberTarget.blur()
        numberTarget.focus()
      } catch (e) {
        console.log(e)
      }
      if (ipOPC.value.length === 0 || !portOPC.value) {
        alert('Заполните IP адрес и порт')
        return
      }
      changeOpcServerConfig(ipOPC.value, portOPC.value)
      getServerConfig(configServer, checkFileActive)
      getIpAndPortConfig(ipOPC, portOPC)
    }

    return {
      lastUpdateFileKKS,
      configServer,
      ipOPC,
      portOPC,
      defaultModeOfFilterRadio,
      defaultRootDirectory,
      defaultExceptionDirectories,
      defaultExceptionExpertTags,
      changeConfig,
      statusUpdateTextArea,
      statusUpdateButtonActive,
      checkFileActive,
      onButtonCancelUpdateClick,
      confirmUpdate,
      changeUpdate,
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
      defaultLastValueChecked,
      defaultFilterTableChecked,
      defaultIntervalDeepOfSearch,
      defaultDimensionDeepOfSearch,
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
    <hr />
    <div class="row">
      <div class="col">
        <h4>Изменить параметры конфигурации клиента</h4>
      </div>
    </div>
    <div style="margin-bottom: 20px"></div>
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
            @input="changeConfig"
            style="width: 100%"
          >
          </InputText>
          <label for="ip-opc-server-address">IP адрес сервера OPC UA</label>
        </FloatLabel>
      </div>
      <div class="col">
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
            @input="changeConfig"
            style="width: 100%"
          >
          </InputNumber>
          <label for="port-opc-server-address">Порт сервера OPC UA</label>
        </FloatLabel>
      </div>
      <div class="col">
        <Button
          v-if="statusUpdateButtonActive"
          label="Отмена"
          icon="pi pi-times"
          @click="onButtonCancelUpdateClick"
          severity="danger"
          style="width: 100%; text-align: center"
        />
        <ConfirmDialog></ConfirmDialog>
        <Button
          v-if="!statusUpdateButtonActive"
          label="Обновить"
          icon="pi pi-check"
          :disabled="statusUpdateButtonActive"
          @click="confirmUpdate"
          style="width: 100%; text-align: center"
        />
      </div>
    </div>
    <div style="margin-bottom: 20px"></div>
    <div class="row">
      <div class="col">
        <h4>Отбор тегов</h4>
      </div>
    </div>
    <div class="row align-items-center">
      <div class="col-4">Режим фильтрации обновления тегов:</div>
      <div class="col-3">
        <RadioButton
          v-model="defaultModeOfFilterRadio"
          inputId="modeFilterHistorianDefault"
          name="modeFilterHistorianDefault"
          value="historian"
          :disabled="statusUpdateButtonActive"
        />
        <label for="modeFilterHistorianDefault" class="radio-interval-margin">Historian</label>
      </div>
      <div class="col-5">
        <label for="default-root-directory">Корневая папка</label><br />
        <InputText
          v-model="defaultRootDirectory"
          type="text"
          id="default-root-directory"
          :disabled="statusUpdateButtonActive || defaultModeOfFilterRadio === 'historian'"
          style="width: 100%"
        >
        </InputText>
      </div>
    </div>
    <div class="row align-items-center">
      <div class="col-4">
        <Button
          @click="changeUpdate"
          :disabled="statusUpdateButtonActive || defaultModeOfFilterRadio === 'historian'"
          >Применить список исключений к уже обновленному файлу тегов</Button
        >
      </div>
      <div class="col-3">
        <RadioButton
          v-model="defaultModeOfFilterRadio"
          inputId="modeFilterExceptionDefault"
          name="modeFilterExceptionDefault"
          value="exception"
          :disabled="statusUpdateButtonActive"
        />
        <label for="modeFilterExceptionDefault" class="radio-interval-margin"
          >Список исключений</label
        >
      </div>
      <div class="col-5">
        <label for="default-exception-directories"
          >Список исключений (перечислите через запятую регулярные выражения)</label
        ><br />
        <InputText
          v-model="defaultExceptionDirectories"
          type="text"
          id="default-exception-directories"
          :disabled="statusUpdateButtonActive || defaultModeOfFilterRadio === 'historian'"
          style="width: 100%"
        >
        </InputText>
        <Checkbox
          id="default-exception-expert-tags"
          v-model="defaultExceptionExpertTags"
          :binary="true"
          :disabled="statusUpdateButtonActive || defaultModeOfFilterRadio === 'historian'"
        ></Checkbox>
        <label for="default-exception-expert-tags" class="checkbox-margin"
          >Исключить теги, помеченные экспертом</label
        >
      </div>
    </div>
    <div style="margin-bottom: 20px"></div>
    <div class="row">
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
      <div class="col-4">Применять фильтр по умолчанию как:</div>
      <div class="col-4">
        <RadioButton
          v-model="defaultSelectionTagRadio"
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
      <div class="col-4">
        <RadioButton
          v-model="defaultSelectionTagRadio"
          id="unionDefault"
          inputId="unionDefault"
          name="union"
          value="union"
          :disabled="statusUpdateButtonActive"
        />
        <label for="unionDefault" class="radio-interval-margin">Объединение шаблонов</label>
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
        <h4>Параметры отчетов</h4>
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
      <div class="col">
        <div class="row">
          <div class="col">
            <label for="intervalDeepOfSearch">Глубина поиска в архивах по умолчанию</label><br />
            <InputNumber
              v-model="defaultIntervalDeepOfSearch"
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
            <label for="calendarDateDeepOfSearchSignals"
              >Дата глубины поиска в архивах по умолчанию</label
            ><br />
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
              style="width: 100%"
            ></Calendar>
          </div>
          <div class="col-12">
            <RadioButton
              v-model="defaultDimensionDeepOfSearch"
              id="dayDefaultDeepOfSearch"
              inputId="dayDefaultDeepOfSearch"
              name="day"
              value="day"
              :disabled="statusUpdateButtonActive"
            />
            <label for="dayDefaultDeepOfSearch" class="radio-interval-margin">День</label>
            <RadioButton
              v-model="defaultDimensionDeepOfSearch"
              id="hourDefaultDeepOfSearch"
              inputId="hourDefaultDeepOfSearch"
              name="hour"
              value="hour"
              :disabled="statusUpdateButtonActive"
            />
            <label for="hourDefaultDeepOfSearch" class="radio-interval-margin">Час</label>
            <RadioButton
              v-model="defaultDimensionDeepOfSearch"
              id="minuteDefaultDeepOfSearch"
              inputId="minuteDefaultDeepOfSearch"
              name="minute"
              value="minute"
              :disabled="statusUpdateButtonActive"
            />
            <label for="minuteDefaultDeepOfSearch" class="radio-interval-margin">Минута</label>
            <RadioButton
              v-model="defaultDimensionDeepOfSearch"
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
              v-model="defaultLastValueChecked"
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
              v-model="defaultFilterTableChecked"
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
    <div class="row">
      <div class="col">
        <label for="intervalDefaultGrid">Интервал по умолчанию: </label><br />
        <InputNumber
          v-model="defaultInterval"
          id="intervalDefaultGrid"
          input-id="intervalDefaultGrid"
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
      <div class="col">
        <label for="show-default-sensors">Показываемые датчики по умолчанию</label><br />
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
        <label for="dayDefault" class="radio-interval-margin">День</label>
        <RadioButton
          v-model="defaultIntervalRadio"
          id="hourDefault"
          inputId="hourDefault"
          name="hour"
          value="hour"
          :disabled="statusUpdateButtonActive"
        />
        <label for="hourDefault" class="radio-interval-margin">Час</label>
        <RadioButton
          v-model="defaultIntervalRadio"
          id="minuteDefault"
          inputId="minuteDefault"
          name="minute"
          value="minute"
          :disabled="statusUpdateButtonActive"
        />
        <label for="minuteDefault" class="radio-interval-margin">Минута</label>
        <RadioButton
          v-model="defaultIntervalRadio"
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

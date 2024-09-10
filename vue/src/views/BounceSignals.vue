<script>
import { FilterMatchMode } from 'primevue/api'
import Multiselect from '@vueform/multiselect'

import { ref, reactive, toRefs, onMounted, onUnmounted, onBeforeUnmount, computed } from 'vue'
import {
  getKKSFilterByMasks,
  getTypesOfSensors,
  getKKSByMasksForTable,
  getBounceSignals,
  cancelBounce
} from '../stores'

import { useApplicationStore } from '../stores/applicationStore'
import { socket } from '../socket'

export default {
  name: 'BounceSignals',
  components: { Multiselect },
  props: {
    collapsedSidebar: Boolean
  },
  setup(props) {
    const applicationStore = useApplicationStore()

    const typesOfSensorsDataValue = ref(applicationStore.defaultFields.typesOfSensors)
    const typesOfSensorsDataOptions = ref([
      {
        label: 'Выбрать все типы данных',
        options: applicationStore.defaultFields.typesOfSensors
      }
    ])
    let chosenTypesOfSensorsData = applicationStore.defaultFields.typesOfSensors

    const selectionTagRadio = ref(applicationStore.defaultFields.selectionTag)

    const templates = reactive({
      templatesArray: []
    })

    for (const [
      index,
      template
    ] of applicationStore.defaultFields.sensorsAndTemplateValue.entries()) {
      templates.templatesArray.push({ id: index, templateText: template })
    }

    const changeTemplates = (position, value) => {
      templates.templatesArray[position].templateText = value
    }

    const addClicked = (position) => {
      let tempTemplate = JSON.parse(JSON.stringify(templates.templatesArray))
      tempTemplate.splice(position + 1, 0, { id: position + 1, templateText: String() })
      for (let i = position + 2; i < tempTemplate.length; i++) {
        tempTemplate[i].id += 1
      }
      templates.templatesArray = JSON.parse(JSON.stringify(tempTemplate))
    }

    const removeClicked = (position) => {
      let tempTemplate = JSON.parse(JSON.stringify(templates.templatesArray))
      tempTemplate.splice(position, 1)
      for (let i = position; i < tempTemplate.length; i++) {
        tempTemplate[i].id -= 1
      }
      templates.templatesArray = JSON.parse(JSON.stringify(tempTemplate))
    }

    const searchPressed = () => {
      disabledSensorsAndTemplate.value = !disabledSensorsAndTemplate.value
      isLoadingSensorsAndTemplate.value = !isLoadingSensorsAndTemplate.value
    }

    const sensorsAndTemplateValue = ref(applicationStore.defaultFields.sensorsAndTemplateValue)
    const sensorsAndTemplateOptions = ref([
      {
        label: 'Шаблоны',
        options: applicationStore.defaultFields.sensorsAndTemplateValue
      },
      {
        label: 'Теги KKS сигналов',
        options: []
      }
    ])
    let chosenSensorsAndTemplate = applicationStore.defaultFields.sensorsAndTemplateValue
    const disabledSensorsAndTemplate = ref(!chosenTypesOfSensorsData.length)
    const isLoadingSensorsAndTemplate = ref(false)

    const dateTime = ref(new Date())
    const disableTime = ref(false)

    const dateTimeBeginReport = ref()
    const dateTimeEndReport = ref()

    const interval = ref(applicationStore.defaultFields.interval)
    const intervalRadio = ref(applicationStore.defaultFields.dimension)

    const progressBarBounceSignals = ref('0')
    const progressBarBounceSignalsActive = ref(false)

    const statusRequestTextArea = ref('')
    const statusRequestCol = computed(() => {
      return props.collapsedSidebar ? 115 : 90
    })

    const countShowSensors = ref(applicationStore.defaultFields.countShowSensors)

    const currentDateChecked = ref(false)

    const dataTable = ref()
    const dataTableRequested = ref(false)
    const dataTableStartRequested = ref(false)

    const filters = ref(null)
    const filterTableChecked = ref(applicationStore.defaultFields.filterTableChecked)

    const estimatedTime = ref(0.0)
    const chosenSensors = ref([])

    const dialogBigRequestActive = ref(false)

    const interruptDisabledFlag = ref(false)

    onMounted(async () => {
      await getTypesOfSensors(typesOfSensorsDataOptions)

      window.addEventListener('beforeunload', async (event) => {
        await cancelBounce()
      })

      if (chosenSensorsAndTemplate.length && chosenTypesOfSensorsData.length) {
        disabledSensorsAndTemplate.value = true
        isLoadingSensorsAndTemplate.value = true
        await getKKSFilterByMasks(
          sensorsAndTemplateOptions,
          chosenTypesOfSensorsData,
          chosenSensorsAndTemplate
        )
        isLoadingSensorsAndTemplate.value = false
        disabledSensorsAndTemplate.value = false
      }
    })

    onBeforeUnmount(async () => {
      window.removeEventListener('beforeunload', async (event) => {})
    })

    onUnmounted(async () => {
      await cancelBounce()
    })

    async function onTypesOfSensorsDataChange(val) {
      chosenTypesOfSensorsData = val
      if (!chosenTypesOfSensorsData.length) {
        disabledSensorsAndTemplate.value = true
      } else {
        disabledSensorsAndTemplate.value = true
        isLoadingSensorsAndTemplate.value = true
        await getKKSFilterByMasks(
          sensorsAndTemplateOptions,
          chosenTypesOfSensorsData,
          chosenSensorsAndTemplate
        )
        isLoadingSensorsAndTemplate.value = false
        disabledSensorsAndTemplate.value = false
      }
    }

    async function onRequestButtonClick() {
      dataTableRequested.value = false

      chosenSensorsAndTemplate = templates.templatesArray.map(({ templateText }) => templateText)

      let emptyTemplateFlag = false
      for (const element of chosenSensorsAndTemplate) {
        if (element.trim() === '') emptyTemplateFlag = true
      }

      if (
        !chosenTypesOfSensorsData.length ||
        !chosenSensorsAndTemplate.length ||
        emptyTemplateFlag ||
        !dateTime.value
      ) {
        alert('Не заполнены параметры запроса!')
        return
      }

      if (progressBarBounceSignalsActive.value) return
      dateTimeBeginReport.value = new Date().toLocaleString()

      dataTableStartRequested.value = true

      progressBarBounceSignalsActive.value = true
      progressBarBounceSignals.value = '0'

      statusRequestTextArea.value = ''
      statusRequestTextArea.value +=
        'Начало выполнения запроса...\nОценка времени выполнения запроса...\n'

      interruptDisabledFlag.value = true

      chosenSensors.value = []
      await getKKSByMasksForTable(
        chosenSensors,
        chosenTypesOfSensorsData,
        chosenSensorsAndTemplate,
        selectionTagRadio
      )

      estimatedTime.value =
        (chosenSensors.value.length *
          interval.value *
          applicationStore.deltaTimeInSeconds[intervalRadio.value]) /
        applicationStore.estimatedBounceRateInHours

      dialogBigRequestActive.value = true
    }

    function onInterruptRequestButtonClick() {
      cancelBounce()
      dataTableStartRequested.value = false
      progressBarBounceSignalsActive.value = false
    }

    function onChangeCheckbox() {
      if (!disableTime.value) dateTime.value = new Date()
      disableTime.value = !disableTime.value
    }

    socket.on('setProgressBarBounceSignals', (progress) => {
      progressBarBounceSignals.value = String(progress.count)
    })

    socket.on('setUpdateBounceRequestStatus', (statusString) => {
      statusRequestTextArea.value += String(statusString.message)
      let textarea = document.getElementById('bounce-request-text-area')
      textarea.scrollTop = textarea.scrollHeight
    })

    async function onButtonDownloadCsvClick() {
      const linkBounceCsv = document.createElement('a')
      linkBounceCsv.download = 'bounce.csv'
      const dataBounceCsv = await fetch('bounce.csv').then((res) => res.blob())
      linkBounceCsv.href = window.URL.createObjectURL(
        new Blob([dataBounceCsv], { type: 'text/csv' })
      )
      linkBounceCsv.click()
      linkBounceCsv.remove()
      window.URL.revokeObjectURL(linkBounceCsv.href)
    }

    async function onButtonDownloadPdfClick() {
      const linkBouncePdf = document.createElement('a')
      linkBouncePdf.download = 'bounce.pdf'
      const dataBouncePdf = await fetch('bounce.pdf').then((res) => res.blob())
      linkBouncePdf.href = window.URL.createObjectURL(
        new Blob([dataBouncePdf], { type: 'application/octet-stream' })
      )
      linkBouncePdf.click()
      linkBouncePdf.remove()
      window.URL.revokeObjectURL(linkBouncePdf.href)
    }

    async function onButtonDownloadTagsClick() {
      const linkTagsCsv = document.createElement('a')
      linkTagsCsv.download = 'tags.csv'
      const dataTagsCsv = await fetch('tags.csv').then((res) => res.blob())
      linkTagsCsv.href = window.URL.createObjectURL(
        new Blob([dataTagsCsv], { type: 'text/csv' })
      )
      linkTagsCsv.click()
      linkTagsCsv.remove()
      window.URL.revokeObjectURL(linkTagsCsv.href)
    }

    async function onButtonCancelBigRequestClick() {
      dialogBigRequestActive.value = false
      progressBarBounceSignals.value = '100'
      progressBarBounceSignalsActive.value = false
    }

    async function onBigRequestButtonClick() {
      dialogBigRequestActive.value = false

      statusRequestTextArea.value += 'Подготовка к выполнению запроса\n'

      filters.value = {
        'Наименование датчика': {
          value: null,
          matchMode: FilterMatchMode.STARTS_WITH
        },
        Частота: {
          value: null,
          matchMode: FilterMatchMode.STARTS_WITH
        }
      }

      interruptDisabledFlag.value = false

      await getBounceSignals(
        chosenSensors.value,
        dateTime.value,
        interval.value,
        intervalRadio.value,
        countShowSensors.value,
        dataTable,
        dataTableRequested
      )

      dateTimeEndReport.value = new Date().toLocaleString()
      progressBarBounceSignals.value = '100'
      progressBarBounceSignalsActive.value = false
    }

    function onDateTodayClick() {
      dateTime.value = new Date()
    }

    return {
      typesOfSensorsDataValue,
      typesOfSensorsDataOptions,
      chosenTypesOfSensorsData,
      onTypesOfSensorsDataChange,
      selectionTagRadio,
      ...toRefs(templates),
      changeTemplates,
      addClicked,
      removeClicked,
      searchPressed,
      sensorsAndTemplateValue,
      sensorsAndTemplateOptions,
      chosenSensorsAndTemplate,
      disabledSensorsAndTemplate,
      isLoadingSensorsAndTemplate,
      dateTime,
      disableTime,
      dateTimeBeginReport,
      dateTimeEndReport,
      onDateTodayClick,
      interval,
      intervalRadio,
      progressBarBounceSignals,
      progressBarBounceSignalsActive,
      statusRequestTextArea,
      statusRequestCol,
      countShowSensors,
      currentDateChecked,
      dataTable,
      dataTableRequested,
      dataTableStartRequested,
      filters,
      filterTableChecked,
      onRequestButtonClick,
      onInterruptRequestButtonClick,
      interruptDisabledFlag,
      onChangeCheckbox,
      onButtonDownloadCsvClick,
      onButtonDownloadPdfClick,
      onButtonDownloadTagsClick,
      estimatedTime,
      chosenSensors,
      dialogBigRequestActive,
      onButtonCancelBigRequestClick,
      onBigRequestButtonClick
    }
  }
}
</script>

<template>
  <div>
    <h1 align="center">Дребезг сигналов</h1>
    <div class="container">
      <div class="row">
        <div class="col components-bounce-margin-bottom">
          <label for="typesOfSensorsDataBounceReport">Выберите тип данных тегов</label>
          <Multiselect
            id="typesOfSensorsDataBounceReport"
            v-model="typesOfSensorsDataValue"
            mode="tags"
            :close-on-select="false"
            :groups="true"
            :options="typesOfSensorsDataOptions"
            :searchable="true"
            :create-option="false"
            placeholder="Выберите тип данных тегов"
            :limit="-1"
            @change="onTypesOfSensorsDataChange"
            :disabled="progressBarBounceSignalsActive"
          ></Multiselect>
        </div>
      </div>
      <div class="row align-items-center">
        <div class="col-3 components-bounce-margin-bottom">Применять фильтр как:</div>
        <div class="col-9 components-bounce-margin-bottom">
          <RadioButton
            v-model="selectionTagRadio"
            inputId="sequential"
            name="sequential"
            value="sequential"
            :disabled="progressBarBounceSignalsActive"
          />
          <label for="sequential" class="radio-bounce-interval-margin"
            >Последовательные шаблоны</label
          >
        </div>
      </div>
      <div class="row align-items-center">
        <div class="col-3 components-bounce-margin-bottom"></div>
        <div class="col-9 components-bounce-margin-bottom">
          <RadioButton
            v-model="selectionTagRadio"
            inputId="union"
            name="union"
            value="union"
            :disabled="progressBarBounceSignalsActive"
          />
          <label for="union" class="radio-bounce-interval-margin">Объединение шаблонов</label>
        </div>
      </div>
      <hr />
      <div class="row align-items-center" v-for="template in templatesArray" :key="template">
        <UTemplate
          :position="template.id"
          :disabledFlag="disabledSensorsAndTemplate || progressBarBounceSignalsActive"
          :template="template.templateText"
          :countOfTemplates="templatesArray.length"
          :types="typesOfSensorsDataValue"
          @addUTemplate="addClicked"
          @removeUTemplate="removeClicked"
          @changeTemplate="changeTemplates"
          @searchPressed="searchPressed"
        ></UTemplate>
      </div>
      <hr />
      <div class="row">
        <div class="col-4">
          <label for="calendar-date">Введите дату</label>
        </div>
      </div>
      <div class="row align-items-center">
        <div class="col-md-auto components-bounce-margin-bottom">
          <Calendar
            id="calendar-date"
            v-model="dateTime"
            show-time
            hour-format="24"
            :show-seconds="true"
            placeholder="ДД/ММ/ГГ ЧЧ:ММ:СС"
            :manualInput="true"
            date-format="dd/mm/yy"
            show-icon
            show-button-bar
            :disabled="disableTime || progressBarBounceSignalsActive"
            :showOnFocus="false"
            @todayClick="onDateTodayClick"
          >
          </Calendar>
        </div>
        <div class="col-md-auto components-bounce-margin-bottom">
          <RadioButton
            v-model="intervalRadio"
            inputId="day"
            name="day"
            value="day"
            :disabled="progressBarBounceSignalsActive"
          />
          <label for="day" class="radio-bounce-interval-margin">День</label>
        </div>
        <div class="col-md-auto components-bounce-margin-bottom">
          <RadioButton
            v-model="intervalRadio"
            inputId="hour"
            name="hour"
            value="hour"
            :disabled="progressBarBounceSignalsActive"
          />
          <label for="hour" class="radio-bounce-interval-margin">Час</label>
        </div>
        <div class="col-md-auto components-bounce-margin-bottom">
          <RadioButton
            v-model="intervalRadio"
            inputId="minute"
            name="minute"
            value="minute"
            :disabled="progressBarBounceSignalsActive"
          />
          <label for="minute" class="radio-bounce-interval-margin">Минута</label>
        </div>
        <div class="col-md-auto components-bounce-margin-bottom">
          <RadioButton
            v-model="intervalRadio"
            inputId="second"
            name="second"
            value="second"
            :disabled="progressBarBounceSignalsActive"
          />
          <label for="second" class="radio-bounce-interval-margin">Секунда</label>
        </div>
        <div class="col-md-auto components-bounce-margin-bottom">
          <Checkbox
            id="current-date-checked"
            v-model="currentDateChecked"
            :binary="true"
            @change="onChangeCheckbox"
            :disabled="progressBarBounceSignalsActive"
          ></Checkbox>
          <label for="current-date-checked" class="checkbox-bounce-margin"
            >Использовать текущее время</label
          >
        </div>
        <div class="col-4"></div>
      </div>
      <div class="row">
        <div class="col-3">
          <label for="interval">Интервал</label>
        </div>
        <div class="col-3">
          <label for="show-sensors">Количество показываемых датчиков</label>
        </div>
      </div>
      <div class="row">
        <div class="col-3 components-bounce-margin-bottom">
          <InputNumber
            v-model="interval"
            id="interval"
            input-id="interval"
            :useGrouping="false"
            mode="decimal"
            show-buttons
            :min="1"
            :step="1"
            :allow-empty="false"
            :aria-label="interval"
            :disabled="progressBarBounceSignalsActive"
          >
          </InputNumber>
        </div>
        <div class="col-3 components-bounce-margin-bottom">
          <InputNumber
            v-model="countShowSensors"
            id="show-sensors"
            input-id="countShowSensors"
            :useGrouping="false"
            mode="decimal"
            show-buttons
            :min="1"
            :step="1"
            :allow-empty="false"
            :aria-label="countShowSensors"
            :disabled="progressBarBounceSignalsActive"
          >
          </InputNumber>
        </div>
      </div>
      <div class="row">
        <div class="col components-bounce-margin-bottom">
          <Button @click="onRequestButtonClick" :disabled="isLoadingSensorsAndTemplate"
            >Запрос</Button
          >
          <Dialog
            v-model="dialogBigRequestActive"
            :visible="dialogBigRequestActive"
            :closable="false"
            header="Подтверждение запуска длительного по времени запроса"
            position="center"
            :modal="true"
            :draggable="false"
            :style="{ width: '50rem' }"
          >
            <div class="container">
              <div class="row">
                <div class="col">
                  Примерная оценка времени выполнения запроса: <b>{{ estimatedTime }} чаc.</b>
                </div>
              </div>
              <div class="row">
                <div class="col">
                  Количество запрошенных тегов: <b>{{ chosenSensors.length }}</b>
                </div>
              </div>
            </div>
            <template #footer>
              <Button @click="onButtonDownloadTagsClick">Список тегов</Button>
              <Button
                label="Отмена"
                icon="pi pi-times"
                @click="onButtonCancelBigRequestClick"
                text
              />
              <Button
                label="Запустить запрос"
                icon="pi pi-check"
                @click="onBigRequestButtonClick"
              />
            </template>
          </Dialog>
        </div>
        <div class="col align-self-center" v-if="dataTableRequested">
          <a @click="onButtonDownloadPdfClick" href="javascript:;" type="application/octet-stream"
            >Загрузить отчет</a
          >
          <!--          <Button @click="onButtonDownloadPdfClick">Загрузить отчет</Button>-->
        </div>
        <div class="col align-self-center" v-if="dataTableRequested">
          <a @click="onButtonDownloadCsvClick" href="javascript:;" type="text/csv">Загрузить CSV</a>
          <!--          <Button @click="onButtonDownloadCsvClick">Загрузить CSV</Button>-->
        </div>
      </div>
      <div class="row" v-if="dataTableStartRequested">
        Старт построения отчета: {{ dateTimeBeginReport }}
      </div>
      <div class="row" v-if="progressBarBounceSignalsActive">
        <div class="col-10 align-self-center">
          <ProgressBar :value="progressBarBounceSignals"></ProgressBar>
        </div>
        <div class="col-2">
          <Button @click="onInterruptRequestButtonClick" :disabled="interruptDisabledFlag"
            >Прервать запрос</Button
          >
        </div>
      </div>
      <div class="row" v-if="progressBarBounceSignalsActive">
        <div class="col">
          <TextArea
            id="bounce-request-text-area"
            v-model="statusRequestTextArea"
            rows="10"
            :cols="statusRequestCol"
            readonly
            :style="{ resize: 'none', 'overflow-y': scroll, width: '83%' }"
            >{{ statusRequestTextArea }}</TextArea
          >
        </div>
      </div>
      <div class="row components-bounce-margin-bottom">
        <div class="card" v-if="dataTableRequested">
          <DataTable
            v-model:filters="filters"
            :value="dataTable"
            scrollable="true"
            scrollHeight="1000px"
            columnResizeMode="fit"
            showGridlines="true"
            tableStyle="min-width: 50rem"
            dataKey="Наименование датчика"
            filterDisplay="row"
          >
            <Column field="Наименование датчика" header="Наименование датчика" sortable>
              <template #filter="{ filterModel, filterCallback }" v-if="filterTableChecked">
                <InputText
                  v-model="filterModel.value"
                  type="text"
                  @input="filterCallback()"
                  class="p-column-filter"
                />
              </template>
            </Column>
            <Column field="Частота" header="Частота" sortable>
              <template #filter="{ filterModel, filterCallback }" v-if="filterTableChecked">
                <InputText
                  v-model="filterModel.value"
                  type="text"
                  @input="filterCallback()"
                  class="p-column-filter"
                />
              </template>
            </Column>
          </DataTable>
        </div>
      </div>
      <div class="row" v-if="dataTableRequested">Отчет: {{ dateTimeEndReport }}</div>
    </div>
  </div>
</template>

<style>
.components-bounce-margin-bottom {
  margin-bottom: 5px;
}
.checkbox-bounce-margin {
  margin-left: 5px;
}
.radio-bounce-interval-margin {
  margin-left: 5px;
}
</style>

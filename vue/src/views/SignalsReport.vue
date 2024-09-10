<script>
import { FilterMatchMode } from 'primevue/api'
import Multiselect from '@vueform/multiselect'
import { ref, reactive, toRefs, onMounted, onUnmounted, onBeforeUnmount, computed } from 'vue'
import {
  getKKSFilterByMasks,
  getTypesOfSensors,
  getSignals,
  cancelSignals,
  getKKSByMasksForTable
} from '../stores'

import { useApplicationStore } from '../stores/applicationStore'
import { socket } from '../socket'

export default {
  name: 'SignalsReport',
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

    const qualitiesName = ref([
      {
        label: 'Выбрать все коды качества сигнала',
        options: applicationStore.qualitiesName
      }
    ])
    const quality = ref(applicationStore.defaultFields.quality)
    let chosenQuality = applicationStore.defaultFields.quality

    const dateTime = ref(new Date())

    const intervalDeepOfSearch = ref(applicationStore.defaultFields.intervalDeepOfSearch)
    const intervalDeepOfSearchRadio = ref(applicationStore.defaultFields.dimensionDeepOfSearch)

    const intervalOrDateChecked = ref(false)

    const lastValueChecked = ref(applicationStore.defaultFields.lastValueChecked)
    const dateDeepOfSearch = ref(applicationStore.defaultFields.dateDeepOfSearch)
    const maxDateTime = ref(new Date())
    const dateTimeBeginReport = ref()
    const dateTimeEndReport = ref()

    const dataTable = ref()
    const dataTableRequested = ref(false)
    const dataTableStartRequested = ref(false)

    const filters = ref(null)
    const filterTableChecked = ref(applicationStore.defaultFields.filterTableChecked)

    const progressBarSignals = ref('0')
    const progressBarSignalsActive = ref(false)

    const statusRequestTextArea = ref('')
    const statusRequestCol = computed(() => {
      return props.collapsedSidebar ? 115 : 90
    })

    const estimatedTime = ref(0.0)
    const chosenSensors = ref([])

    const dialogBigRequestActive = ref(false)

    const interruptDisabledFlag = ref(false)

    onMounted(async () => {
      await getTypesOfSensors(typesOfSensorsDataOptions)
      window.addEventListener('beforeunload', async (event) => {
        await cancelSignals()
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
      await cancelSignals()
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

    function onMultiselectQualitiesChange(val) {
      chosenQuality = val
    }

    function onDateDeepOfSearchClick() {
      maxDateTime.value = new Date()
    }

    function onDateTodayClick() {
      dateTime.value = new Date()
    }

    function onDateDeepOfSearchTodayClick() {
      dateDeepOfSearch.value = new Date()
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
        !chosenQuality.length ||
        !dateTime.value ||
        !intervalDeepOfSearch.value ||
        (!dateDeepOfSearch.value && intervalOrDateChecked.value)
      ) {
        alert('Не заполнены параметры запроса!')
        return
      }

      if (dateTime.value <= dateDeepOfSearch.value && intervalOrDateChecked.value) {
        alert('Глубина поиска в архивах не должна превышать указанную дату запроса')
        return
      }

      if (progressBarSignalsActive.value) return
      dateTimeBeginReport.value = new Date().toLocaleString()

      dataTableStartRequested.value = true
      progressBarSignalsActive.value = true
      progressBarSignals.value = '0'
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
        (chosenSensors.value.length * chosenQuality.length) /
        applicationStore.estimatedSliceRateInHours

      dialogBigRequestActive.value = true
    }

    async function onInterruptRequestButtonClick() {
      await cancelSignals()
      dataTableStartRequested.value = false
      progressBarSignalsActive.value = false
    }

    function qualityClass(quality) {
      return [
        {
          'text-danger': applicationStore.badCode.includes(quality['Качество']),
          'text-warning': quality['Качество'] === '' || quality['Качество'] === 'NaN'
        }
      ]
    }

    function codeOfQualityClass(code) {
      return [
        {
          'text-danger': applicationStore.badNumericCode.includes(code['Код качества']),
          'text-warning': code['Код качества'] === '' || code['Код качества'] === 'NaN'
        }
      ]
    }

    socket.on('setProgressBarSignals', (progress) => {
      progressBarSignals.value = String(progress.count)
    })

    socket.on('setUpdateSignalsRequestStatus', (statusString) => {
      statusRequestTextArea.value += String(statusString.message)
      let textarea = document.getElementById('signals-request-text-area')
      textarea.scrollTop = textarea.scrollHeight
    })

    async function onButtonDownloadCsvClick() {
      const linkSignalsCsv = document.createElement('a')
      linkSignalsCsv.download = 'signals_slice.csv'
      const dataSignalsCsv = await fetch('signals_slice.csv').then((res) => res.blob())
      linkSignalsCsv.href = window.URL.createObjectURL(
        new Blob([dataSignalsCsv], { type: 'text/csv' })
      )
      linkSignalsCsv.click()
      linkSignalsCsv.remove()
      window.URL.revokeObjectURL(linkSignalsCsv.href)
    }

    async function onButtonDownloadPdfClick() {
      const linkSignalsPdf = document.createElement('a')
      linkSignalsPdf.download = 'signals_slice.pdf'
      const dataSignalsPdf = await fetch('signals_slice.pdf').then((res) => res.blob())
      linkSignalsPdf.href = window.URL.createObjectURL(
        new Blob([dataSignalsPdf], { type: 'application/octet-stream' })
      )
      linkSignalsPdf.click()
      linkSignalsPdf.remove()
      window.URL.revokeObjectURL(linkSignalsPdf.href)
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
      progressBarSignals.value = '100'
      progressBarSignalsActive.value = false
    }

    async function onBigRequestButtonClick() {
      dialogBigRequestActive.value = false

      statusRequestTextArea.value += 'Подготовка к выполнению запроса\n'

      filters.value = {
        'Код сигнала (KKS)': {
          value: null,
          matchMode: FilterMatchMode.STARTS_WITH
        },
        'Дата и время измерения': {
          value: null,
          matchMode: FilterMatchMode.STARTS_WITH
        },
        Значение: {
          value: null,
          matchMode: FilterMatchMode.STARTS_WITH
        },
        Качество: {
          value: null,
          matchMode: FilterMatchMode.STARTS_WITH
        },
        'Код качества': {
          value: null,
          matchMode: FilterMatchMode.STARTS_WITH
        }
      }

      interruptDisabledFlag.value = false

      await getSignals(
        chosenTypesOfSensorsData,
        selectionTagRadio.value,
        chosenSensorsAndTemplate,
        chosenQuality,
        dateTime.value,
        lastValueChecked.value,
        intervalOrDateChecked.value,
        intervalDeepOfSearch.value,
        intervalDeepOfSearchRadio.value,
        dateDeepOfSearch.value,
        dataTable,
        dataTableRequested
      )
      dateTimeEndReport.value = new Date().toLocaleString()
      progressBarSignals.value = '100'
      progressBarSignalsActive.value = false
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
      qualitiesName,
      quality,
      chosenQuality,
      onMultiselectQualitiesChange,
      lastValueChecked,
      intervalDeepOfSearch,
      intervalDeepOfSearchRadio,
      intervalOrDateChecked,
      dateTime,
      maxDateTime,
      dateDeepOfSearch,
      onDateDeepOfSearchClick,
      onDateTodayClick,
      onDateDeepOfSearchTodayClick,
      dateTimeBeginReport,
      dateTimeEndReport,
      onRequestButtonClick,
      onInterruptRequestButtonClick,
      interruptDisabledFlag,
      dataTable,
      dataTableRequested,
      dataTableStartRequested,
      filters,
      filterTableChecked,
      qualityClass,
      codeOfQualityClass,
      progressBarSignals,
      progressBarSignalsActive,
      statusRequestTextArea,
      statusRequestCol,
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
    <h1 align="center">Срезы сигналов</h1>
    <div class="container">
      <div class="row">
        <div class="col components-signals-margin-bottom">
          <label for="typesOfSensorsDataSignalsReport">Выберите тип данных тегов</label>
          <Multiselect
            id="typesOfSensorsDataSignalsReport"
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
            :disabled="progressBarSignalsActive"
          ></Multiselect>
        </div>
      </div>
      <div class="row align-items-center">
        <div class="col-3 components-signals-margin-bottom">Применять фильтр как:</div>
        <div class="col-9 components-signals-margin-bottom">
          <RadioButton
            v-model="selectionTagRadio"
            inputId="sequential"
            name="sequential"
            value="sequential"
            :disabled="progressBarSignalsActive"
          />
          <label for="sequential" class="radio-signals-interval-margin"
            >Последовательные шаблоны</label
          >
        </div>
      </div>
      <div class="row align-items-center">
        <div class="col-3 components-signals-margin-bottom"></div>
        <div class="col-9 components-signals-margin-bottom">
          <RadioButton
            v-model="selectionTagRadio"
            inputId="union"
            name="union"
            value="union"
            :disabled="progressBarSignalsActive"
          />
          <label for="union" class="radio-signals-interval-margin">Объединение шаблонов</label>
        </div>
      </div>
      <hr />
      <div
        class="row align-items-center components-signals-margin-bottom"
        v-for="template in templatesArray"
        :key="template"
      >
        <UTemplate
          :position="template.id"
          :disabledFlag="disabledSensorsAndTemplate || progressBarSignalsActive"
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
        <div class="col components-signals-margin-bottom">
          <label for="qualitySignalsReport">Код качества сигнала</label>
          <Multiselect
            id="qualitySignalsReport"
            v-model="quality"
            mode="tags"
            :close-on-select="false"
            :searchable="true"
            :create-option="false"
            :groups="true"
            :options="qualitiesName"
            placeholder="Выберите код качества сигнала"
            :limit="-1"
            noResultsText="Больше кодов качеств не найдено"
            @change="onMultiselectQualitiesChange"
            :disabled="progressBarSignalsActive"
          ></Multiselect>
        </div>
      </div>
      <div class="row">
        <div class="col">
          <label for="intervalSignalReport">Глубина поиска в архивах</label>
        </div>
      </div>
      <div class="row align-items-center">
        <div class="col-md-auto components-signals-margin-bottom">
          <InputNumber
            v-model="intervalDeepOfSearch"
            id="intervalDeepOfSearchSignalReport"
            input-id="intervalDeepOfSearch"
            :useGrouping="false"
            mode="decimal"
            show-buttons
            :min="1"
            :step="1"
            :allow-empty="false"
            :disabled="progressBarSignalsActive || intervalOrDateChecked"
          >
          </InputNumber>
        </div>
        <div class="col-md-auto components-signals-margin-bottom">
          <RadioButton
            v-model="intervalDeepOfSearchRadio"
            inputId="day"
            name="day"
            value="day"
            :disabled="progressBarSignalsActive || intervalOrDateChecked"
          />
          <label for="day" class="radio-signals-interval-margin">День</label>
        </div>
        <div class="col-md-auto components-signals-margin-bottom">
          <RadioButton
            v-model="intervalDeepOfSearchRadio"
            inputId="hour"
            name="hour"
            value="hour"
            :disabled="progressBarSignalsActive || intervalOrDateChecked"
          />
          <label for="hour" class="radio-signals-interval-margin">Час</label>
        </div>
        <div class="col-md-auto components-signals-margin-bottom">
          <RadioButton
            v-model="intervalDeepOfSearchRadio"
            inputId="minute"
            name="minute"
            value="minute"
            :disabled="progressBarSignalsActive || intervalOrDateChecked"
          />
          <label for="minute" class="radio-signals-interval-margin">Минута</label>
        </div>
        <div class="col-md-auto components-signals-margin-bottom">
          <RadioButton
            v-model="intervalDeepOfSearchRadio"
            inputId="second"
            name="second"
            value="second"
            :disabled="progressBarSignalsActive || intervalOrDateChecked"
          />
          <label for="second" class="radio-signals-interval-margin">Секунда</label>
        </div>
        <div class="col-4"></div>
      </div>
      <div class="row">
        <div class="col">
          <Checkbox
            id="intervalOrDateCheckedSignalReport"
            v-model="intervalOrDateChecked"
            :binary="true"
            :disabled="progressBarSignalsActive"
          ></Checkbox>
          <label for="intervalOrDateCheckedSignalReport" class="checkbox-signals-margin"
            >Задать глубину поиска в архивах в виде даты</label
          >
        </div>
      </div>
      <div class="row">
        <div class="col">
          <label for="calendarDateDeepOfSearchSignalsReport">Дата глубины поиска в архивах</label>
        </div>
      </div>
      <div class="row">
        <div class="col">
          <Calendar
            id="calendarDateDeepOfSearchSignalsReport"
            v-model="dateDeepOfSearch"
            :maxDate="maxDateTime"
            show-time
            hour-format="24"
            :show-seconds="true"
            placeholder="ДД/ММ/ГГ ЧЧ:ММ:СС"
            :manualInput="true"
            date-format="dd/mm/yy"
            show-icon
            show-button-bar
            @click="onDateDeepOfSearchClick"
            :disabled="progressBarSignalsActive || !intervalOrDateChecked"
            :showOnFocus="false"
            @todayClick="onDateDeepOfSearchTodayClick"
          ></Calendar>
        </div>
      </div>
      <div class="row">
        <div class="col">
          <label for="calendarDateSignalsReport">Введите дату</label>
        </div>
      </div>
      <div class="row">
        <div class="col">
          <div class="row">
            <div class="col-12">
              <Calendar
                id="calendarDateSignalsReport"
                v-model="dateTime"
                show-time
                hour-format="24"
                :show-seconds="true"
                placeholder="ДД/ММ/ГГ ЧЧ:ММ:СС"
                :manualInput="true"
                date-format="dd/mm/yy"
                show-icon
                show-button-bar
                :disabled="progressBarSignalsActive"
                :showOnFocus="false"
                @todayClick="onDateTodayClick"
              ></Calendar>
            </div>
          </div>
        </div>
      </div>
      <div class="row">
        <div class="col-12">
          <Checkbox
            id="lastValueCheckedSignalReport"
            v-model="lastValueChecked"
            :binary="true"
            :disabled="progressBarSignalsActive"
          ></Checkbox>
          <label for="lastValueCheckedSignalReport" class="checkbox-signals-margin"
            >Искать последние по времени значения</label
          >
        </div>
      </div>
      <div class="row">
        <div class="col components-signals-margin-bottom">
          <Button @click="onRequestButtonClick" :disabled="isLoadingSensorsAndTemplate"
            >Запрос</Button
          >
          <Dialog
            v-model="dialogBigRequestActive"
            :visible="dialogBigRequestActive"
            :closable="false"
            header="Подтверждение запуска запроса"
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
          <a
              @click="onButtonDownloadPdfClick"
              href="javascript:;"
              type="application/octet-stream"
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
      <div class="row" v-if="progressBarSignalsActive">
        <div class="col-10 align-self-center">
          <ProgressBar :value="progressBarSignals"></ProgressBar>
        </div>
        <div class="col-2">
          <Button @click="onInterruptRequestButtonClick" :disabled="interruptDisabledFlag"
            >Прервать запрос</Button
          >
        </div>
      </div>
      <div class="row" v-if="progressBarSignalsActive">
        <div class="col">
          <TextArea
            id="signals-request-text-area"
            v-model="statusRequestTextArea"
            rows="10"
            :cols="statusRequestCol"
            readonly
            :style="{ resize: 'none', 'overflow-y': scroll, width: '83%' }"
            >{{ statusRequestTextArea }}</TextArea
          >
        </div>
      </div>
      <div class="row">
        <div class="card" v-if="dataTableRequested">
          <DataTable
            v-model:filters="filters"
            :value="dataTable"
            paginator
            :rows="10"
            :rowsPerPageOptions="[10, 20, 50, 100]"
            scrollable="true"
            scrollHeight="flex"
            columnResizeMode="fit"
            showGridlines="true"
            tableStyle="min-width: 50rem"
            dataKey="Код сигнала (KKS)"
            filterDisplay="row"
          >
            <Column
              class="myTable"
              field="Код сигнала (KKS)"
              header="Код сигнала (KKS)"
              sortable
              style="width: 35%"
            >
              <template #filter="{ filterModel, filterCallback }" v-if="filterTableChecked">
                <InputText
                  v-model="filterModel.value"
                  type="text"
                  @input="filterCallback()"
                  class="p-column-filter"
                />
              </template>
            </Column>
            <Column
              field="Дата и время измерения"
              header="Дата и время измерения"
              sortable
              style="width: 20%"
            >
              <template #filter="{ filterModel, filterCallback }" v-if="filterTableChecked">
                <InputText
                  v-model="filterModel.value"
                  type="text"
                  @input="filterCallback()"
                  class="p-column-filter"
                />
              </template>
            </Column>
            <Column field="Значение" header="Значение" sortable style="width: 15%">
              <template #filter="{ filterModel, filterCallback }" v-if="filterTableChecked">
                <InputText
                  v-model="filterModel.value"
                  type="text"
                  @input="filterCallback()"
                  class="p-column-filter"
                />
              </template>
            </Column>
            <Column field="Качество" header="Качество" sortable style="width: 20%">
              <template #filter="{ filterModel, filterCallback }" v-if="filterTableChecked">
                <InputText
                  v-model="filterModel.value"
                  type="text"
                  @input="filterCallback()"
                  class="p-column-filter"
                />
              </template>
              <template #body="slotProps">
                <div :class="qualityClass(slotProps.data)">
                  {{ slotProps.data['Качество'] }}
                </div>
              </template>
            </Column>
            <Column field="Код качества" header="Код качества" sortable style="width: 10%">
              <template #filter="{ filterModel, filterCallback }" v-if="filterTableChecked">
                <InputText
                  v-model="filterModel.value"
                  type="text"
                  @input="filterCallback()"
                  class="p-column-filter"
                />
              </template>
              <template #body="slotProps">
                <div :class="codeOfQualityClass(slotProps.data)">
                  {{ slotProps.data['Код качества'] }}
                </div>
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
.components-signals-margin-bottom {
  margin-bottom: 5px;
}
.checkbox-signals-margin {
  margin-left: 5px;
}
.radio-signals-interval-margin {
  margin-left: 5px;
}
/*td{*/
/*  font-size: 8px;*/
/*}*/
</style>

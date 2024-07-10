<script>
import { FilterMatchMode } from 'primevue/api'
import Multiselect from '@vueform/multiselect'

import {
  ref,
  reactive,
  toRefs,
  onMounted,
  onUnmounted,
  onBeforeUnmount,
  computed,
  watch,
} from 'vue'
import {
  getKKSFilterByMasks,
  getTypesOfSensors,
  getKKSByMasksForTable,
  getGrid,
  getPartOfData,
  getFilterData,
  getSortedData,
  cancelGrid
} from '../stores'

import { useApplicationStore } from '../stores/applicationStore'
import { socket } from '../socket'

export default {
  name: 'GridReport',
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

    const dateTimeEnd = ref(new Date())
    const dateTimeBegin = ref(new Date(dateTimeEnd.value - 10 * 60000))
    // const dateTimeBegin = ref(dateTimeEnd.value.setMinutes(dateTimeEnd.value.getMinutes()-10))

    const dateTimeBeginReport = ref()
    const dateTimeEndReport = ref()

    const interval = ref(applicationStore.defaultFields.interval)
    const intervalRadio = ref(applicationStore.defaultFields.dimension)

    const progressBarGrid = ref('0')
    const progressBarGridActive = ref(false)

    const statusRequestTextArea = ref('')
    const statusRequestCol = computed(() => {
      return props.collapsedSidebar ? 115 : 90
    })

    const dataCodeTable = ref()
    const dataTable = ref()
    const dataTableStatus = ref()
    const columnsTable = ref([])
    const countOfDataTable = ref(0)
    const columnsTableArrayOfArray = ref([])
    const dataTableRequested = ref(false)
    const dataTableStartRequested = ref(false)

    const lazyLoading = ref(false)
    const loadLazyTimeout = ref()
    const loadedData = ref([])
    const loadedDataStatus = ref([])
    const tempLoadedData = ref()
    const tempLoadedStatus = ref()
    const itemSize = ref(applicationStore.itemSize)
    const loadDataLazy = (event) => {
      lazyLoading.value = true

      if (loadLazyTimeout.value) {
        clearTimeout(loadLazyTimeout.value)
      }


      loadLazyTimeout.value = setTimeout(async () => {
        let _loadedData = [...dataTable.value]
        let _loadedDataStatus = [...dataTableStatus.value]

        let { first, last } = event

        // вызов загрузки данных с Flask
        await getPartOfData(tempLoadedData, dataTableRequested, tempLoadedStatus, first, last)

        Array.prototype.splice.apply(_loadedData, [...[first, last - first], ...tempLoadedData.value])
        Array.prototype.splice.apply(_loadedDataStatus, [...[first, last - first], ...tempLoadedStatus.value])

        loadedData.value = _loadedData
        loadedDataStatus.value = _loadedDataStatus

        dataTable.value = loadedData.value
        dataTableStatus.value = loadedDataStatus.value

        lazyLoading.value = false
      }, 50)
    }

    const filters = ref(null)
    const filterTableChecked = ref(applicationStore.defaultFields.filterTableChecked)

    let loadOnFilterTimeout = null
    const onSort = (event) => {
      lazyLoading.value = true

      if (loadOnFilterTimeout) {
        clearTimeout(loadOnFilterTimeout)
      }

      loadOnFilterTimeout = setTimeout(async () => {
        let lazyParams = {
          filters: filters.value,
          sortField: String(event.sortField),
          sortOrder: event.sortOrder
        }
        await getSortedData(lazyParams, dataTable, dataTableStatus, applicationStore.firstRaw, applicationStore.lastRaw)
        lazyLoading.value = false
      }, 500)
    }

    const onFilter = () => {
      lazyLoading.value = true

      if (loadOnFilterTimeout) {
        clearTimeout(loadOnFilterTimeout)
      }

      loadOnFilterTimeout = setTimeout(async () => {
        await getFilterData(filters, dataTable, dataTableStatus, applicationStore.firstRaw, applicationStore.lastRaw)
        lazyLoading.value = false
      }, 2000)
    }

    watch(
  () => filters,
    (before, after) => {
          if (!dataTableRequested.value) return
          onFilter()
        },
 { deep: true }
      )

    const estimatedTime = ref(0.0)
    const chosenSensors = ref([])

    const dialogBigRequestActive = ref(false)

    const interruptDisabledFlag = ref(false)

    onMounted(async () => {
      await getTypesOfSensors(typesOfSensorsDataOptions)
      window.addEventListener('beforeunload', async (event) => {
        await cancelGrid()
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
      let verticalScroll = document.getElementById('data-table')
      verticalScroll = verticalScroll.querySelector('.p-virtualscroller.p-virtualscroller-inline')
      verticalScroll.removeEventListener('scroll', synchroScroll)
    })

    onUnmounted(async () => {
      await cancelGrid()
      let verticalScroll = document.getElementById('data-table')
      verticalScroll = verticalScroll.querySelector('.p-virtualscroller.p-virtualscroller-inline')
      verticalScroll.removeEventListener('scroll', synchroScroll)
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
        !dateTimeBegin.value ||
        !dateTimeEnd.value
      ) {
        alert('Не заполнены параметры запроса!')
        return
      }

      if (dateTimeEnd.value.getTime() < dateTimeBegin.value.getTime()) {
        alert('Дата конца должна быть больше даты начала')
        return
      }

      if (dateTimeEnd.value.getTime() === dateTimeBegin.value.getTime()) {
        alert('Дата конца не должна совпадать с датой начала')
        return
      }
      if (progressBarGridActive.value) return
      dateTimeBeginReport.value = new Date().toLocaleString()

      dataTableStartRequested.value = true

      progressBarGridActive.value = true
      progressBarGrid.value = '0'

      statusRequestTextArea.value = ''
      statusRequestTextArea.value +=
        'Начало выполнения запроса...\nОценка времени выполнения запроса...\n'

      interruptDisabledFlag.value = true

      chosenSensors.value = []
      let differenceInTime = dateTimeEnd.value.getTime() - dateTimeBegin.value.getTime()
      let differenceInDimension = Math.round(
        differenceInTime / (1000 * applicationStore.deltaTimeInSeconds[intervalRadio.value])
      )

      await getKKSByMasksForTable(
        chosenSensors,
        chosenTypesOfSensorsData,
        chosenSensorsAndTemplate,
        selectionTagRadio
      )

      estimatedTime.value =
        (chosenSensors.value.length * differenceInDimension) /
        (applicationStore.estimatedGridRateInHours * interval.value)

      dialogBigRequestActive.value = true
    }

    function onInterruptRequestButtonClick() {
      cancelGrid()
      dataTableStartRequested.value = false
      progressBarGridActive.value = false
    }

    socket.on('setProgressBarGrid', (progress) => {
      progressBarGrid.value = String(progress.count)
    })

    socket.on('setUpdateGridRequestStatus', (statusString) => {
      statusRequestTextArea.value += String(statusString.message)
      let textarea = document.getElementById('grid-request-text-area')
      textarea.scrollTop = textarea.scrollHeight
    })

    function onButtonDownloadCsvClick() {
      const link = document.createElement('a')
      const pathCodeCsv = 'code.csv'
      link.setAttribute('download', pathCodeCsv)
      link.setAttribute('type', 'application/octet-stream')
      link.setAttribute('href', 'code.csv')
      document.body.appendChild(link)
      link.click()
      link.remove()

      const pathGridCsv = 'grid.csv'
      link.setAttribute('download', pathGridCsv)
      link.setAttribute('type', 'application/octet-stream')
      link.setAttribute('href', 'grid.csv')
      document.body.appendChild(link)
      link.click()
      link.remove()
    }

    function onButtonDownloadPdfClick() {
      const link = document.createElement('a')
      const pathSignalsReport = 'report/grid.zip'
      link.setAttribute('download', pathSignalsReport)
      link.setAttribute('type', 'application/octet-stream')
      link.setAttribute('href', 'report/grid.zip')
      document.body.appendChild(link)
      link.click()
      link.remove()
    }

    function onButtonDownloadTagsClick() {
      const link = document.createElement('a')
      const pathTagsReport = 'tags.csv'
      link.setAttribute('download', pathTagsReport)
      link.setAttribute('type', 'application/octet-stream')
      link.setAttribute('href', 'tags.csv')
      document.body.appendChild(link)
      link.click()
      link.remove()
    }

    function statusClass(index, field) {
      return [
        {
          'text-danger': applicationStore.badCode.includes(
            dataTableStatus.value[index][String(field)]
          ),
          'text-warning':
            dataTableStatus.value[index][String(field)] === 'missed' ||
            dataTableStatus.value[index][String(field)] === 'NaN' ||
            dataTable.value[index][String(field)] === 'NaN'
          // 'text-danger': applicationStore.badCode.includes(
          //   loadedDataStatus.value[index][String(field)]
          // ),
          // 'text-warning':
          //   loadedDataStatus.value[index][String(field)] === 'missed' ||
          //   loadedDataStatus.value[index][String(field)] === 'NaN' ||
          //   loadedData.value[index][String(field)] === 'NaN'
        }
      ]
    }

    const synchroScroll = (event) => {
      let codeScroll = document.getElementById('code-table')
      codeScroll = codeScroll.querySelector('.p-virtualscroller.p-virtualscroller-inline')
      let dataScroll = document.getElementById('data-table')
      dataScroll = dataScroll.querySelector('.p-virtualscroller.p-virtualscroller-inline')
      codeScroll.scrollTop = dataScroll.scrollLeft * 0.3235
    }

    const synchroScrollByHref = (event) => {
      let codeScroll = document.getElementById('code-table')
      codeScroll = codeScroll.querySelector('.p-virtualscroller.p-virtualscroller-inline')
      let dataScroll = document.getElementById('data-table')
      dataScroll = dataScroll.querySelector('.p-virtualscroller.p-virtualscroller-inline')
      dataScroll.scrollLeft = codeScroll.scrollTop / 0.3235
    }

    async function onButtonCancelBigRequestClick() {
      dialogBigRequestActive.value = false
      progressBarGrid.value = '100'
      progressBarGridActive.value = false
    }

    async function onBigRequestButtonClick() {
      dialogBigRequestActive.value = false

      statusRequestTextArea.value += 'Подготовка к выполнению запроса\n'

      columnsTable.value = []
      columnsTableArrayOfArray.value = []

      filters.value = {
        'Метка времени': {
          value: null,
          matchMode: FilterMatchMode.STARTS_WITH
        }
      }

      let codeTableArray = Array()
      let columnsTableArray = [{ field: 'Метка времени', header: 'Метка времени' }]

      for (const [index, element] of chosenSensors.value.entries()) {
        codeTableArray.push({ '№': index, 'Обозначение сигнала': element })
        columnsTableArray.push({ field: String(index), header: String(index) })
        filters.value[index] = { value: null, matchMode: FilterMatchMode.STARTS_WITH }
      }

      dataCodeTable.value = codeTableArray
      columnsTable.value = columnsTableArray

      interruptDisabledFlag.value = false

      await getGrid(
        chosenSensors.value,
        dateTimeBegin.value,
        dateTimeEnd.value,
        interval.value,
        intervalRadio.value,
        dataTable,
        dataTableRequested,
        dataTableStatus,
        applicationStore.firstRaw,
        applicationStore.lastRaw
      )

      // countOfDataTable.value = Math.ceil(chosenSensors.value.length / 5)
      //
      // if (countOfDataTable.value === 1) columnsTableArrayOfArray.value.push(columnsTableArray)
      // else {
      //   for (let i = 0; i < countOfDataTable.value; i++) {
      //     if (i === 0) columnsTableArrayOfArray.value.push(columnsTable.value.slice(0, 6))
      //     else {
      //       columnsTableArrayOfArray.value.push(columnsTable.value.slice(i * 5 + 1, i * 5 + 6))
      //       columnsTableArrayOfArray.value[i].unshift({
      //         field: 'Метка времени',
      //         header: 'Метка времени'
      //       })
      //     }
      //   }
      // }

      dateTimeEndReport.value = new Date().toLocaleString()
      progressBarGrid.value = '100'
      progressBarGridActive.value = false

      let verticalScroll = document.getElementById('data-table')
      verticalScroll = verticalScroll.querySelector('.p-virtualscroller.p-virtualscroller-inline')
      verticalScroll.addEventListener('scroll', synchroScroll, false)
    }

    function onDateBeginTodayClick() {
      dateTimeBegin.value = new Date()
    }

    function onDateEndTodayClick() {
      dateTimeEnd.value = new Date()
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
      dateTimeBegin,
      dateTimeEnd,
      dateTimeBeginReport,
      dateTimeEndReport,
      onDateBeginTodayClick,
      onDateEndTodayClick,
      interval,
      intervalRadio,
      progressBarGrid,
      progressBarGridActive,
      statusRequestTextArea,
      statusRequestCol,
      dataCodeTable,
      dataTable,
      dataTableStatus,
      columnsTable,
      countOfDataTable,
      columnsTableArrayOfArray,
      dataTableRequested,
      dataTableStartRequested,
      lazyLoading,
      loadLazyTimeout,
      itemSize,
      loadDataLazy,
      filters,
      filterTableChecked,
      onSort,
      onFilter,
      onRequestButtonClick,
      onInterruptRequestButtonClick,
      interruptDisabledFlag,
      onButtonDownloadCsvClick,
      onButtonDownloadPdfClick,
      onButtonDownloadTagsClick,
      statusClass,
      synchroScroll,
      synchroScrollByHref,
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
    <h1 align="center">Сетка сигналов</h1>
    <div class="container">
      <div class="row">
        <div class="col components-margin-bottom">
          <label for="typesOfSensorsDataGridReport">Выберите тип данных тегов</label>
          <Multiselect
            id="typesOfSensorsDataGridReport"
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
            :disabled="progressBarGridActive"
          ></Multiselect>
        </div>
      </div>
      <div class="row align-items-center">
        <div class="col-3 components-margin-bottom">Применять фильтр как:</div>
        <div class="col-9 components-margin-bottom">
          <RadioButton
            v-model="selectionTagRadio"
            inputId="sequential"
            name="sequential"
            value="sequential"
            :disabled="progressBarGridActive"
          />
          <label for="sequential" class="radio-interval-margin">Последовательные шаблоны</label>
        </div>
      </div>
      <div class="row align-items-center">
        <div class="col-3 components-margin-bottom"></div>
        <div class="col-9 components-margin-bottom">
          <RadioButton
            v-model="selectionTagRadio"
            inputId="union"
            name="union"
            value="union"
            :disabled="progressBarGridActive"
          />
          <label for="union" class="radio-interval-margin">Объединение шаблонов</label>
        </div>
      </div>
      <hr />
      <div class="row align-items-center" v-for="template in templatesArray" :key="template">
        <UTemplate
          :position="template.id"
          :disabledFlag="disabledSensorsAndTemplate || progressBarGridActive"
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
        <div class="col">
          <label for="calendarDateBeginGridReport">Введите дату начала</label>
        </div>
        <div class="col">
          <label for="calendarDateEndGridReport">Введите дату конца</label>
        </div>
      </div>
      <div class="row">
        <div class="col components-margin-bottom">
          <Calendar
            id="calendarDateBeginGridReport"
            v-model="dateTimeBegin"
            show-time
            hour-format="24"
            :show-seconds="true"
            placeholder="ДД/ММ/ГГ ЧЧ:ММ:СС"
            :manualInput="true"
            date-format="dd/mm/yy"
            show-icon
            show-button-bar
            :disabled="progressBarGridActive"
            :showOnFocus="false"
            @todayClick="onDateBeginTodayClick"
          >
          </Calendar>
        </div>
        <div class="col components-margin-bottom">
          <Calendar
            id="calendarDateEndGridReport"
            v-model="dateTimeEnd"
            show-time
            hour-format="24"
            :show-seconds="true"
            placeholder="ДД/ММ/ГГ ЧЧ:ММ:СС"
            :manualInput="true"
            date-format="dd/mm/yy"
            show-icon
            show-button-bar
            :disabled="progressBarGridActive"
            :showOnFocus="false"
            @todayClick="onDateEndTodayClick"
          >
          </Calendar>
        </div>
      </div>
      <div class="row">
        <div class="col">
          <label for="intervalGridReport">Интервал</label>
        </div>
      </div>
      <div class="row align-items-center">
        <div class="col components-margin-bottom">
          <InputNumber
            v-model="interval"
            id="intervalGridReport"
            input-id="interval"
            :useGrouping="false"
            mode="decimal"
            show-buttons
            :min="1"
            :step="1"
            :allow-empty="false"
            :disabled="progressBarGridActive"
          >
          </InputNumber>
        </div>
        <div class="col components-margin-bottom">
          <RadioButton
            v-model="intervalRadio"
            inputId="day"
            name="day"
            value="day"
            :disabled="progressBarGridActive"
          />
          <label for="day" class="radio-interval-margin">День</label>
        </div>
        <div class="col components-margin-bottom">
          <RadioButton
            v-model="intervalRadio"
            inputId="hour"
            name="hour"
            value="hour"
            :disabled="progressBarGridActive"
          />
          <label for="hour" class="radio-interval-margin">Час</label>
        </div>
        <div class="col components-margin-bottom">
          <RadioButton
            v-model="intervalRadio"
            inputId="minute"
            name="minute"
            value="minute"
            :disabled="progressBarGridActive"
          />
          <label for="minute" class="radio-interval-margin">Минута</label>
        </div>
        <div class="col components-margin-bottom">
          <RadioButton
            v-model="intervalRadio"
            inputId="second"
            name="second"
            value="second"
            :disabled="progressBarGridActive"
          />
          <label for="second" class="radio-interval-margin">Секунда</label>
        </div>
      </div>
      <div class="row">
        <div class="col components-margin-bottom">
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
          <a href="report/grid.zip" download="report/grid.zip" type="application/octet-stream"
            >Загрузить отчет</a
          >
          <!--          <Button @click="onButtonDownloadPdfClick">Загрузить отчет</Button>-->
        </div>
        <div class="col align-self-center" v-if="dataTableRequested">
          <a href="grid.csv" download="grid.csv" type="application/octet-stream">Загрузить CSV</a>
          <!--          <Button @click="onButtonDownloadCsvClick">Загрузить CSV</Button>-->
        </div>
      </div>
      <div class="row" v-if="dataTableStartRequested">
        Старт построения отчета: {{ dateTimeBeginReport }}
      </div>
      <div class="row" v-if="progressBarGridActive">
        <div class="col-10 align-self-center">
          <ProgressBar :value="progressBarGrid"></ProgressBar>
        </div>
        <div class="col-2">
          <Button @click="onInterruptRequestButtonClick" :disabled="interruptDisabledFlag"
            >Прервать запрос</Button
          >
        </div>
      </div>
      <div class="row" v-if="progressBarGridActive">
        <div class="col">
          <TextArea
            id="grid-request-text-area"
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
        <div class="components-margin-bottom">
          <div class="card" v-if="dataTableRequested" id="code-table">
            <DataTable
              :value="dataCodeTable"
              scrollable="true"
              scrollHeight="400px"
              columnResizeMode="fit"
              showGridlines="true"
              :virtualScrollerOptions="{ itemSize: 50 }"
              tableStyle="min-width: 50rem"
            >
              <Column field="№" header="№" sortable style="width: 50%"> </Column>
              <Column
                field="Обозначение сигнала"
                header="Обозначение сигнала"
                sortable
                style="width: 50%"
              >
                <template #body="slotProps">
                  <a :href="'#' + slotProps.data['№']" @click="synchroScrollByHref">
                    <div>
                      {{ slotProps.data[slotProps.field] }}
                    </div>
                  </a>
                </template>
              </Column>
            </DataTable>
          </div>
          <div class="card" v-if="dataTableRequested" id="data-table">
            <DataTable
              v-model:filters="filters"
              :lazy="true"
              :value="dataTable"
              :scrollable="true"
              scrollHeight="1000px"
              :columnResizeMode="fit"
              :showGridlines="true"
              :virtualScrollerOptions="{ lazy: true, onLazyLoad: loadDataLazy, itemSize: itemSize, delay: 200, showLoader: true, loading: lazyLoading, numToleratedItems: 10 }"
              tableStyle="min-width: 50rem"
              dataKey="Метка времени"
              filterDisplay="row"
              class="grid-table"
              @sort="onSort($event)"
            >
<!--            <DataTable-->
<!--              v-model:filters="filters"-->
<!--              :value="dataTable"-->
<!--              :scrollable="true"-->
<!--              scrollHeight="1000px"-->
<!--              :columnResizeMode="fit"-->
<!--              :showGridlines="true"-->
<!--              :virtualScrollerOptions="{ itemSize: 50 }"-->
<!--              tableStyle="min-width: 50rem"-->
<!--              dataKey="Метка времени"-->
<!--              filterDisplay="row"-->
<!--              class="grid-table"-->
<!--            >-->
              <Column
                v-for="col of columnsTable"
                :key="col.field"
                :field="col.field"
                :header="col.header"
                sortable
                v-bind:frozen="[col.field === 'Метка времени']"
                v-bind:style="[
                  col.field === 'Метка времени'
                    ? { 'min-width': '250px' }
                    : { 'min-width': '150px' }
                ]"
              >
                <template #body="slotProps">
                  <div :class="statusClass(slotProps.index, slotProps.field)">
                    {{ slotProps.data[slotProps.field] }}
                  </div>
                </template>
                <template #filter="{ filterModel, filterCallback }" v-if="filterTableChecked">
                  <InputText
                    :id="col.header"
                    v-model="filterModel.value"
                    @input="filterCallback($event)"
                    type="text"
                    class="p-column-filter"
                    :fluid="true"
                  />
                </template>
                <template #loading>
                  <div class="flex items-center" :style="{ height: '17px', 'flex-grow': '1', overflow: 'hidden' }">
                    <Skeleton width="60%" height="1rem" />
                  </div>
                </template>
              </Column>
            </DataTable>
          </div>
        </div>
      </div>
      <div class="row" v-if="dataTableRequested">Отчет: {{ dateTimeEndReport }}</div>
    </div>
  </div>
</template>

<style>
.components-margin-bottom {
  margin-bottom: 5px;
}
.radio-interval-margin {
  margin-left: 5px;
}
.grid-table td {
  font-size: 8px;
  vertical-align: middle;
  padding-bottom: 0;
  padding-top: 0;
}
</style>

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
  watch
} from 'vue'
import {
  getKKSFilterByMasks,
  getTypesOfSensors,
  getKKSByMasksForTable,
  getGrid,
  getPartOfData,
  getSortedAndFilteredData,
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
    const { defaultFields, badQualityDescrCode, itemSize,
      firstRaw, lastRaw, deltaTimeInSeconds, estimatedGridRateInHours } = applicationStore

    const typesOfSensorsDataValue = ref(defaultFields.typesOfSensors)
    const typesOfSensorsDataOptions = ref([
      {
        label: 'Выбрать все типы данных',
        options: defaultFields.typesOfSensors
      }
    ])
    let chosenTypesOfSensorsData = defaultFields.typesOfSensors

    const selectionTagRadio = ref(defaultFields.selectionTag)

    const templates = reactive({
      templatesArray: []
    })

    for (const [
      index,
      template
    ] of defaultFields.sensorsAndTemplateValue.entries()) {
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

    const sensorsAndTemplateValue = ref(defaultFields.sensorsAndTemplateValue)
    const sensorsAndTemplateOptions = ref([
      {
        label: 'Шаблоны',
        options: defaultFields.sensorsAndTemplateValue
      },
      {
        label: 'Теги KKS сигналов',
        options: []
      }
    ])
    let chosenSensorsAndTemplate = defaultFields.sensorsAndTemplateValue
    const disabledSensorsAndTemplate = ref(!chosenTypesOfSensorsData.length)
    const isLoadingSensorsAndTemplate = ref(false)

    const dateTimeEnd = ref(new Date())
    const dateTimeBegin = ref(new Date(dateTimeEnd.value - 10 * 60000))

    const dateTimeBeginReport = ref()
    const dateTimeEndReport = ref()

    const interval = ref(defaultFields.interval)
    const intervalRadio = ref(defaultFields.dimension)

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

        Array.prototype.splice.apply(_loadedData, [
          ...[first, last - first],
          ...tempLoadedData.value
        ])
        Array.prototype.splice.apply(_loadedDataStatus, [
          ...[first, last - first],
          ...tempLoadedStatus.value
        ])

        loadedData.value = _loadedData
        loadedDataStatus.value = _loadedDataStatus

        dataTable.value = loadedData.value
        dataTableStatus.value = loadedDataStatus.value

        lazyLoading.value = false
      }, 50)
    }

    const filters = ref(null)
    const filterTableChecked = ref(defaultFields.filterTableChecked)
    const lazyParams = ref({
      filters: null,
      sortField: null,
      sortOrder: null
    })

    let loadOnFilterTimeout = null

    const onSort = async (event) => {
      lazyParams.value = {
        filters: filters.value,
        sortField: String(event.sortField),
        sortOrder: event.sortOrder
      }
      await onSortAndFilter()
    }

    const onFilter = async () => {
      lazyParams.value.filters = filters.value
      await onSortAndFilter()
    }

    const onSortAndFilter = () => {
      lazyLoading.value = true

      if (loadOnFilterTimeout) {
        clearTimeout(loadOnFilterTimeout)
      }

      loadOnFilterTimeout = setTimeout(async () => {
        await getSortedAndFilteredData(
          lazyParams.value,
          dataTable,
          dataTableStatus,
          firstRaw,
          lastRaw
        )
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
      try {
        let verticalScroll = document.getElementById('data-table')
        verticalScroll = verticalScroll.querySelector('.p-virtualscroller.p-virtualscroller-inline')
        verticalScroll.removeEventListener('scroll', synchroScroll)
      } catch (e) {
        console.log(e)
      }
    })

    onUnmounted(async () => {
      await cancelGrid()
      try {
        let verticalScroll = document.getElementById('data-table')
        verticalScroll = verticalScroll.querySelector('.p-virtualscroller.p-virtualscroller-inline')
        verticalScroll.removeEventListener('scroll', synchroScroll)
      } catch (e) {
        console.log(e)
      }
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
        differenceInTime / (1000 * deltaTimeInSeconds[intervalRadio.value])
      )

      await getKKSByMasksForTable(
        chosenSensors,
        chosenTypesOfSensorsData,
        chosenSensorsAndTemplate,
        selectionTagRadio
      )

      estimatedTime.value =
        (chosenSensors.value.length * differenceInDimension) /
        (estimatedGridRateInHours * interval.value)

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

    async function onButtonDownloadCsvClick() {
      const linkCodeCsv = document.createElement('a')
      linkCodeCsv.download = 'code.csv'
      const dataCodeCsv = await fetch('code.csv').then((res) => res.blob())
      linkCodeCsv.href = window.URL.createObjectURL(new Blob([dataCodeCsv], { type: 'text/csv' }))
      linkCodeCsv.click()
      linkCodeCsv.remove()
      window.URL.revokeObjectURL(linkCodeCsv.href)

      const linkGridCsv = document.createElement('a')
      linkGridCsv.download = 'grid.csv'
      const dataGridCsv = await fetch('grid.csv').then((res) => res.blob())
      linkGridCsv.href = window.URL.createObjectURL(new Blob([dataGridCsv], { type: 'text/csv' }))
      linkGridCsv.click()
      linkGridCsv.remove()
      window.URL.revokeObjectURL(linkGridCsv.href)
    }

    async function onButtonDownloadPdfClick() {
      const linkGridZip = document.createElement('a')
      linkGridZip.download = 'grid.zip'
      const dataGridZip = await fetch('grid.zip').then((res) => res.blob())
      linkGridZip.href = window.URL.createObjectURL(
        new Blob([dataGridZip], { type: 'application/zip' })
      )
      linkGridZip.click()
      linkGridZip.remove()
      window.URL.revokeObjectURL(linkGridZip.href)
    }

    async function onButtonDownloadTagsClick() {
      const linkTagsCsv = document.createElement('a')
      linkTagsCsv.download = 'tags.csv'
      const dataTagsCsv = await fetch('tags.csv').then((res) => res.blob())
      linkTagsCsv.href = window.URL.createObjectURL(new Blob([dataTagsCsv], { type: 'text/csv' }))
      linkTagsCsv.click()
      linkTagsCsv.remove()
      window.URL.revokeObjectURL(linkTagsCsv.href)
    }

    function statusClass(index, field) {
      return [
        {
          'text-danger': badQualityDescrCode.includes(
            dataTableStatus.value[index][String(field)]
          ),
          'text-warning':
            dataTableStatus.value[index][String(field)] === 'missed' ||
            dataTableStatus.value[index][String(field)] === 'NaN' ||
            dataTable.value[index][String(field)] === 'NaN'
        }
      ]
    }

    const synchroScroll = (event) => {
      let codeScroll = document.getElementById('code-table')
      codeScroll = codeScroll.querySelector('.p-virtualscroller.p-virtualscroller-inline')
      let dataScroll = document.getElementById('data-table')
      dataScroll = dataScroll.querySelector('.p-virtualscroller.p-virtualscroller-inline')
      codeScroll.scrollTop = dataScroll.scrollLeft * 0.395
    }

    const synchroScrollByHref = (event) => {
      let codeScroll = document.getElementById('code-table')
      codeScroll = codeScroll.querySelector('.p-virtualscroller.p-virtualscroller-inline')
      let dataScroll = document.getElementById('data-table')
      dataScroll = dataScroll.querySelector('.p-virtualscroller.p-virtualscroller-inline')
      dataScroll.scrollLeft = codeScroll.scrollTop / 0.395
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
        firstRaw,
        lastRaw
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
        <div class="col components-grid-margin-bottom">
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
        <div class="col-3 components-grid-margin-bottom">Применять фильтр как:</div>
        <div class="col-9 components-grid-margin-bottom">
          <RadioButton
            v-model="selectionTagRadio"
            inputId="sequential"
            name="sequential"
            value="sequential"
            :disabled="progressBarGridActive"
          />
          <label for="sequential" class="radio-grid-interval-margin"
            >Последовательные шаблоны</label
          >
        </div>
      </div>
      <div class="row align-items-center">
        <div class="col-3 components-grid-margin-bottom"></div>
        <div class="col-9 components-grid-margin-bottom">
          <RadioButton
            v-model="selectionTagRadio"
            inputId="union"
            name="union"
            value="union"
            :disabled="progressBarGridActive"
          />
          <label for="union" class="radio-grid-interval-margin">Объединение шаблонов</label>
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
        <div class="col-3">
          <label for="calendarDateBeginGridReport">Введите дату начала</label>
        </div>
        <div class="col-3">
          <label for="calendarDateEndGridReport">Введите дату конца</label>
        </div>
      </div>
      <div class="row">
        <div class="col-3 components-grid-margin-bottom">
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
        <div class="col-3 components-grid-margin-bottom">
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
        <div class="col-md-auto components-grid-margin-bottom">
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
        <div class="col-md-auto components-grid-margin-bottom">
          <RadioButton
            v-model="intervalRadio"
            inputId="day"
            name="day"
            value="day"
            :disabled="progressBarGridActive"
          />
          <label for="day" class="radio-grid-interval-margin">День</label>
        </div>
        <div class="col-md-auto components-grid-margin-bottom">
          <RadioButton
            v-model="intervalRadio"
            inputId="hour"
            name="hour"
            value="hour"
            :disabled="progressBarGridActive"
          />
          <label for="hour" class="radio-grid-interval-margin">Час</label>
        </div>
        <div class="col-md-auto components-grid-margin-bottom">
          <RadioButton
            v-model="intervalRadio"
            inputId="minute"
            name="minute"
            value="minute"
            :disabled="progressBarGridActive"
          />
          <label for="minute" class="radio-grid-interval-margin">Минута</label>
        </div>
        <div class="col-md-auto components-grid-margin-bottom">
          <RadioButton
            v-model="intervalRadio"
            inputId="second"
            name="second"
            value="second"
            :disabled="progressBarGridActive"
          />
          <label for="second" class="radio-grid-interval-margin">Секунда</label>
        </div>
        <div class="col-4"></div>
      </div>
      <div class="row">
        <div class="col components-grid-margin-bottom">
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
        <div class="components-grid-margin-bottom">
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
              scrollHeight="500px"
              :columnResizeMode="fit"
              :showGridlines="true"
              :virtualScrollerOptions="{
                lazy: true,
                onLazyLoad: loadDataLazy,
                itemSize: itemSize,
                delay: 200,
                showLoader: true,
                loading: lazyLoading,
                numToleratedItems: 15
              }"
              tableStyle="min-width: 50rem"
              dataKey="Метка времени"
              filterDisplay="row"
              class="grid-table"
              @sort="onSort($event)"
            >
              <Column
                v-for="col of columnsTable"
                :key="col.field"
                :field="col.field"
                :header="col.header"
                sortable
                v-bind:frozen="[col.field === 'Метка времени']"
                v-bind:style="[
                  col.field === 'Метка времени'
                    ? { 'min-width': '200px' }
                    : { 'min-width': '125px' }
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
                  <div
                    class="flex items-center"
                    :style="{ height: '17px', 'flex-grow': '1', overflow: 'hidden' }"
                  >
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
.components-grid-margin-bottom {
  margin-bottom: 5px;
}
.radio-grid-interval-margin {
  margin-left: 5px;
}
.grid-table td {
  font-size: 8px;
  vertical-align: middle;
  padding-bottom: 0;
  padding-top: 0;
}
</style>

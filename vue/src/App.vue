<script>
import { useRoute } from 'vue-router'
import { ref, onMounted, computed, watch } from 'vue'

import Multiselect from '@vueform/multiselect'

import { getFileChecked, getQualityChecked, cancelUpdate } from './stores'

import { useApplicationStore } from './stores/applicationStore'

export default {
  components: { Multiselect },
  setup() {
    const applicationStore = useApplicationStore()
    const { getFields,  getQualitiesName, getBadQualityDescr, getBadCode } = applicationStore

    getQualitiesName()
    getBadQualityDescr()
    getBadCode()
    getFields()

    const sidebarMenu = [
      {
        header: 'Меню отчетов',
        hiddenOnCollapse: true
      },
      {
        href: '/configurator',
        title: 'Конфигуратор'
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
    const checkFileActive = ref(false)
    const modeClient = ref('')
    const modeClientCHActive = ref(false)
    const checkQualityFileActive = ref(false)
    const checkQualityTableActive = ref(false)

    const route = useRoute()
    const routePath = computed(() => route.path)

    watch(route, async () => {
      if (routePath.value === '/configurator') return
      await getFileChecked(checkFileActive, modeClient, modeClientCHActive)
      if (!checkFileActive.value && modeClient.value === 'OPC')
        alert('Не найден файл kks_all.csv.\nСконфигурируйте клиент OPC UA и обновите файл тегов')
      if (!modeClientCHActive.value && modeClient.value === 'CH')
        alert('Ошибка конфигурации клиента Clickhouse.\nСконфигурируйте клиент Clickhouse')
      await getQualityChecked(checkQualityFileActive, checkQualityTableActive)
      if (!checkQualityFileActive.value && modeClient.value === 'OPC')
        alert('Не найден файл quality.csv. \nДобавьте файл с кодами качествами через конфигуратор')
      if (!checkQualityTableActive.value && modeClient.value === 'CH')
        alert('Ошибка конфигурации Clickhouse.\nТаблица с кодами качествами не найдена')
    })

    onMounted(async () => {
      // await getFileChecked(checkFileActive, modeClient, modeClientCHActive)
      // if (!checkFileActive.value && modeClient.value === 'OPC')
      //   alert('Не найден файл kks_all.csv.\nСконфигурируйте клиент OPC UA и обновите файл тегов')
      // if (!modeClientCHActive.value && modeClient.value === 'CH')
      //   alert('Ошибка конфигурации клиента Clickhouse.\nСконфигурируйте клиент Clickhouse')
      window.addEventListener('beforeunload', async (event) => {
        await cancelUpdate()
      })
    })

    return {
      sidebarMenu,
      collapsed,
      checkFileActive,
      modeClient,
      modeClientCHActive,
      checkQualityFileActive,
      checkQualityTableActive,
      routePath
    }
  }
}
</script>

<template>
  <sidebar-menu v-model:collapsed="collapsed" :menu="sidebarMenu" :width="'250px'"> </sidebar-menu>
  <div id="content" :class="[{ collapsed: collapsed }]">
    <div class="content">
      <div
        class="container"
        v-if="modeClient === 'OPC' && routePath !== '/configurator'"
      >
        <div v-if="!checkFileActive">
          <h1>Не найден файл kks_all.csv.</h1>
          <h1>Сконфигурируйте клиент OPC UA и обновите файл тегов на странице "Конфигуратор".</h1>
        </div>
        <div v-if="!checkQualityFileActive">
          <h1>Не найден файл quality.csv.</h1>
          <h1>Добавьте файл с кодами качествами через "Конфигуратор".</h1>
        </div>
      </div>
      <div
        class="container"
        v-if="!modeClientCHActive && modeClient === 'CH' && routePath !== '/configurator'"
      >
        <div v-if="!modeClientCHActive">
          <h1>Ошибка конфигурации клиента Clickhouse.</h1>
          <h1>Сконфигурируйте клиент Clickhouse</h1>
        </div>
        <div v-if="!checkQualityTableActive">
          <h1>Ошибка конфигурации Clickhouse.</h1>
          <h1>Таблица с кодами качествами не найдена</h1>
        </div>
      </div>
      <div
        class="container"
        v-if="
          (checkFileActive && checkQualityFileActive  && modeClient === 'OPC') ||
          (modeClientCHActive && checkQualityTableActive && modeClient === 'CH') ||
          routePath === '/configurator'
        "
      >
        <RouterView :collapsed-sidebar="collapsed" />
      </div>
    </div>
  </div>
</template>

<style>
#content {
  padding-left: 250px;
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
  padding: 50px 0 50px 0;
}

.container {
  max-width: 900px;
}
.p-radiobutton {
  transform: scale(0.8);
}
.p-checkbox {
  transform: scale(0.8);
}
</style>

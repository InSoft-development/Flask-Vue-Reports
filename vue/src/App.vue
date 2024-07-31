<script>
import { useRoute } from 'vue-router'
import { ref, onMounted, computed } from 'vue'

import Multiselect from '@vueform/multiselect'

import { getFileChecked, cancelUpdate } from './stores'

import { useApplicationStore } from './stores/applicationStore'

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

    const route = useRoute()
    const routePath = computed(() => route.path)

    onMounted(async () => {
      await getFileChecked(checkFileActive)
      if (!checkFileActive.value)
        alert('Не найден файл kks_all.csv.\nСконфигурируйте клиент OPC UA и обновите файл тегов')
      window.addEventListener('beforeunload', async (event) => {
        await cancelUpdate()
      })
    })

    return {
      sidebarMenu,
      collapsed,
      checkFileActive,
      routePath
    }
  }
}
</script>

<template>
  <sidebar-menu v-model:collapsed="collapsed" :menu="sidebarMenu" :width="'250px'"> </sidebar-menu>
  <div id="content" :class="[{ collapsed: collapsed }]">
    <div class="content">
      <div class="container" v-if="!checkFileActive && routePath !== '/configurator'">
        <h1>Не найден файл kks_all.csv.</h1>
        <h1>Сконфигурируйте клиент OPC UA и обновите файл тегов на странице "Конфигуратор".</h1>
      </div>
      <div class="container" v-if="checkFileActive || routePath === '/configurator'">
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

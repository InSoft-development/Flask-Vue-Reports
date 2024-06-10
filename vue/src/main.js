import { createApp } from 'vue'
import { createPinia } from 'pinia'

import App from './App.vue'
import router from './router'

import VueSidebarMenu from 'vue-sidebar-menu'
import 'vue-sidebar-menu/dist/vue-sidebar-menu.css'

import '@vueform/multiselect/themes/default.css'

import 'bootstrap/dist/css/bootstrap.min.css'
import 'bootstrap'

import PrimeVue, { defaultOptions } from 'primevue/config'
import 'primevue/resources/themes/lara-light-green/theme.css'
// import 'primevue/resources/themes/bootstrap4-light-blue/theme.css'
import 'primeicons/primeicons.css'

import globalComponents from './components/global'
import ConfirmationService from 'primevue/confirmationservice'

const app = createApp(App)

app.use(createPinia())
app.use(router)
app.use(globalComponents)
app.use(VueSidebarMenu)
app.use(PrimeVue, {
  locale: {
    ...defaultOptions.locale,
    startsWith: 'Начинается с',
    contains: 'Содержит',
    notContains: 'Не содержит',
    endsWith: 'Кончается на',
    equals: '=',
    notEquals: '!=',
    noFilter: 'Без фильтрации',
    today: 'Текущее время',
    clear: 'Сброс'
  }
})
app.use(ConfirmationService)
app.mount('#app')

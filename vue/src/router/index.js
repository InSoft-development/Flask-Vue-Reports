import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'SignalsReport',
      component: () => import('../views/SignalsReport.vue')
    },
    {
      path: '/grid_report',
      name: 'GridReport',
      component: () => import('../views/GridReport.vue')
    },
    {
      path: '/bounce_signals',
      name: 'BounceSignals',
      component: () => import('../views/BounceSignals.vue')
    },
    {
      path: '/configurator',
      name: 'Configurator',
      component: () => import('../views/Configurator.vue')
    }
  ]
})

export default router

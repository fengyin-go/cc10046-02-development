import { createRouter, createWebHistory } from 'vue-router'

import CoverageView from '@/views/CoverageView.vue'
import Overview from '@/views/Overview.vue'
import WorkbenchView from '@/views/WorkbenchView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'overview', component: Overview },
    // 固定路径要排在 /:moduleKey 之前，否则 /coverage 会被当成模块 key。
    { path: '/coverage', name: 'coverage', component: CoverageView },
    { path: '/:moduleKey', name: 'module', component: WorkbenchView, props: true },
  ],
})

export default router

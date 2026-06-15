import { createApp } from 'vue';
import { createPinia } from 'pinia';
import { createRouter, createWebHistory } from 'vue-router';
import App from './App.vue';
import Home from './views/Home.vue';
import Assessment from './views/Assessment.vue';
import Report from './views/Report.vue';
import ReportLoading from './views/ReportLoading.vue';
import ReportReady from './views/ReportUnlock.vue';
import './assets/main.css';

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', component: Home },
    { path: '/assessment', component: Assessment },
    { path: '/report/:sessionId/loading', component: ReportLoading },
    { path: '/report/:sessionId/ready', component: ReportReady },
    { path: '/report/:sessionId/unlock', component: ReportReady },
    { path: '/report/:sessionId', component: Report },
  ],
  scrollBehavior(to, from, savedPosition) {
    if (savedPosition) return savedPosition;
    return { top: 0 };
  },
});

const app = createApp(App);
const pinia = createPinia();

app.use(pinia);
app.use(router);
app.mount('#app');

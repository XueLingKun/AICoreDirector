import { createApp } from 'vue';
import ElementPlus from 'element-plus';
import 'element-plus/dist/index.css';
import App from './App.vue';
import VueECharts from 'vue-echarts';
import * as echarts from 'echarts';
import { createI18n } from 'vue-i18n';
import zhCN from './locales/zh-CN.json';
import en from './locales/en.json';

const storedLocale = localStorage.getItem('locale');
const browserIsZh = (navigator.language || '').toLowerCase().startsWith('zh');
const userPreferredLocale = storedLocale ? storedLocale : (browserIsZh ? 'zh-CN' : 'en');

const i18n = createI18n({
  legacy: false,
  globalInjection: true,
  locale: userPreferredLocale,
  fallbackLocale: 'zh-CN',
  messages: { 'zh-CN': zhCN, en }
});

const app = createApp(App);
app.use(ElementPlus);
app.use(i18n);
app.component('v-chart', VueECharts);
app.mount('#app');
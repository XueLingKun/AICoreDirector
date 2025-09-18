<template>
  <div style="height: 100%">
    <div
      v-if="showSplash"
      style="
        height: 100%;
        width: 100%;
        background: #0f172a;
        display: flex;
        align-items: center;
        justify-content: center;
      "
    >
              <img style="height: 100%" src="/logo_main.svg" alt="AICoreDirector Logo" />
    </div>
    <el-container v-else style="height: 100vh">
      <el-header height="60px" style="display: flex; align-items: center">
        <img
          class="logo-main"
          src="/logo_main.svg"
          alt="AICoreDirector Logo"
          style="height: 48px; margin-right: 24px; vertical-align: middle"
        />
        <el-menu
          mode="horizontal"
          :default-active="activeMenu"
          @select="onMenuSelect"
          style="flex: 1; font-size: 16px;"
        >
          <el-menu-item index="dashboard">{{ $t('nav.dashboard') }}</el-menu-item>
          <!-- <el-menu-item index="models">{{ $t('nav.models') }}</el-menu-item> -->
          <el-menu-item index="discovery">{{ $t('nav.discovery') }}</el-menu-item>
          <el-menu-item index="history">{{ $t('nav.history') }}</el-menu-item>
          <el-menu-item index="llmconfig">{{ $t('nav.llmconfig') }}</el-menu-item>
          <el-menu-item index="prompt">{{ $t('nav.prompt') }}</el-menu-item>
          <el-sub-menu index="help" @mouseenter="loadHelpSections">
            <template #title>{{ $t('nav.help') }}</template>
            <div style="max-height: calc(100vh - 90px); overflow-y: auto;">
              <el-menu-item
                v-for="s in helpSections"
                :key="s.title"
                :index="'help-' + s.title"
                >{{ s.title }}</el-menu-item
              >
            </div>
          </el-sub-menu>
        </el-menu>
        <div style="display:flex; align-items:center; gap:8px;">
          <el-select v-model="locale" size="small" @change="onLocaleChange" style="width: 120px;">
            <el-option :label="$t('lang.zhCN')" value="zh-CN" />
            <el-option :label="$t('lang.en')" value="en" />
          </el-select>
        </div>
      </el-header>
      <el-main>
        <component
          :is="currentView"
          :section="helpSection"
          :markdown="helpMarkdown"
        />
      </el-main>
    </el-container>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from "vue";
import { useI18n } from "vue-i18n";
import axios from "axios";
import Dashboard from "./views/Dashboard.vue";
import LLMConfig from "./views/LLMConfig.vue";
// import Models from './views/Models.vue';
import History from "./views/History.vue";
import ServiceDiscovery from "./views/ServiceDiscovery.vue";
import PromptManager from "./views/PromptManager.vue";
import Help from "./views/Help.vue";

const showSplash = ref(true);
const activeMenu = ref("dashboard");
const helpSection = ref("");
const helpMarkdown = ref("");
const helpSections = ref([]);
const { locale } = useI18n();
const views = {
  dashboard: Dashboard,
  // models: Models,
  discovery: ServiceDiscovery,
  history: History,
  llmconfig: LLMConfig,
  prompt: PromptManager,
  help: Help,
};
const currentView = computed(
  () =>
    views[activeMenu.value.startsWith("help") ? "help" : activeMenu.value] ||
    Dashboard
);

async function loadHelpSections(force = false) {
  if (!force && helpSections.value.length > 0) return;
  const res = await axios.get("/api/readme/sections", { params: { lang: locale.value } });
  helpSections.value = res.data.sections || [];
}

async function onMenuSelect(key) {
  if (key.startsWith("help-")) {
    activeMenu.value = key;
    const title = key.replace("help-", "");
    helpSection.value = title;
    // 请求markdown内容
    const res = await axios.get("/api/readme/section", { params: { title, lang: locale.value } });
    helpMarkdown.value = res.data.markdown || "";
  } else {
    activeMenu.value = key;
  }
}

async function onLocaleChange(val) {
  try {
    localStorage.setItem("locale", val);
    // 切换后重新加载帮助目录与内容
    helpSections.value = [];
    await loadHelpSections(true);
    if (activeMenu.value.startsWith("help-")) {
      // 如果切换到中文后原标题不匹配，默认切到新列表的第一个标题
      const exists = helpSections.value.some(s => s.title === helpSection.value);
      const title = exists && helpSection.value ? helpSection.value : (helpSections.value[0]?.title || "");
      if (title) {
        activeMenu.value = "help-" + title;
        helpSection.value = title;
        const res = await axios.get("/api/readme/section", { params: { title, lang: val } });
        helpMarkdown.value = res.data.markdown || "";
      } else {
        helpMarkdown.value = "";
      }
    }
  } catch {}
}

// 启动页期间预加载LLM监控数据
onMounted(() => {
  setTimeout(() => {
    showSplash.value = false;
  }, 4000);
  // 预加载Dashboard数据
  if (Dashboard && Dashboard.methods && Dashboard.methods.fetchData) {
    Dashboard.methods.fetchData();
  }

  // 也可直接请求主要接口
  axios.get("/get_model_health");
  axios.get("/get_model_qps");
  axios.get("/get_model_hit_count");
});
</script>

<style>
.logo-main {
  transition: transform 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  transform-origin: left center;
}
.logo-main:hover {
  transform: scale(3);
  z-index: 10;
}

.el-header{
  border-bottom: 1px solid var(--el-menu-border-color);
}
/* 导航菜单字体大小 */
.el-menu--horizontal .el-menu-item {
  font-size: 18px !important;
  font-weight: 500;
  /* margin: 0 20px !important; */
  /* padding: 0 20px !important; */
}

.el-menu--horizontal .el-sub-menu__title {
  font-size: 18px !important;
  font-weight: 500;
  /* margin: 0 20px !important; */
  /* padding: 0 20px !important; */
}
</style>

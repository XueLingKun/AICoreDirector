<template>
  <el-card style="margin-bottom: 20px;">
    <template #header>
      <div class="card-header">
        <span class="title">{{ $t('dashboard.title') }}</span>
        <div class="header-actions">
          <el-button size="small" type="primary" @click="fetchData">{{ $t('common.refresh') }}</el-button>
          <el-tooltip :content="$t('dashboard.autoRefreshTip')">
            <el-switch v-model="autoRefresh" style="margin-left: 12px;height: auto;" />
          </el-tooltip>
        </div>
      </div>
    </template>

    <el-row :gutter="20" style="margin-bottom:20px;">
      <el-col :span="6">
        <el-card class="stat-card healthy">
          <div class="stat-icon"><span style="color:#52c41a;font-size:28px;">✔</span></div>
          <div class="stat-title">{{ $t('dashboard.stats.healthyModels') }}</div>
          <div class="stat-value">{{ healthyModelCount }}/{{ totalModelCount }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card qps">
          <div class="stat-icon"><span style="color:#faad14;font-size:28px;">⚡</span></div>
          <div class="stat-title">{{ $t('dashboard.stats.totalQps') }}</div>
          <div class="stat-value">{{ totalQps }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card hitrate">
          <div class="stat-icon"><span style="color:#1890ff;font-size:28px;">◎</span></div>
          <div class="stat-title">{{ $t('dashboard.stats.avgHitRate') }}</div>
          <div class="stat-value">{{ avgHitRate }}<span style="font-size:14px;color:#888;">%</span></div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card hitcount">
          <div class="stat-icon"><span style="color:#722ed1;font-size:28px;">#</span></div>
          <div class="stat-title">{{ $t('dashboard.stats.totalHitCount') }}</div>
          <div class="stat-value">{{ totalHitCount }}</div>
        </el-card>
      </el-col>
    </el-row>

    <el-table
      :data="llmStatusList"
      style="width: 100%;margin-top: 30px"
      stripe
      size="large"
      @row-click="onRowClick"
      :row-class-name="tableRowClassName"
      row-key="name"
      :header-cell-style="{ background: '#F5F7FA' }"
    >
      <el-table-column prop="name" :label="$t('dashboard.table.modelName')" min-width="200" fixed="left" show-overflow-tooltip />
      <el-table-column prop="tags" :label="$t('dashboard.table.tags')" min-width="200" show-overflow-tooltip>
        <template #default="scope">
          <span v-if="Array.isArray(scope.row.tags)">{{ scope.row.tags.join(', ') }}</span>
          <span v-else>{{ scope.row.tags }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="version" :label="$t('dashboard.table.version')" min-width="90" align="center" show-overflow-tooltip />
      <el-table-column prop="status" :label="$t('dashboard.table.status')" min-width="90" align="center" show-overflow-tooltip>
        <template #default="scope">
          {{ getStatusText(scope.row.status) }}
        </template>
      </el-table-column>
      <el-table-column prop="cost" :label="$t('dashboard.table.unitCost')" min-width="90" align="center" show-overflow-tooltip />
      <el-table-column prop="qps" label="QPS" min-width="90" align="center" show-overflow-tooltip />
      <el-table-column prop="healthy" :label="$t('dashboard.table.health')" min-width="90" align="center" show-overflow-tooltip>
        <template #default="scope">
          <el-tag :type="scope.row.healthy ? 'success' : 'danger'" size="small">
            {{ scope.row.healthy ? $t('dashboard.health.ok') : $t('dashboard.health.bad') }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="current_concurrency" :label="$t('dashboard.table.currentConcurrency')" min-width="90" align="center" show-overflow-tooltip />
      <el-table-column prop="max_concurrency" :label="$t('dashboard.table.maxConcurrency')" min-width="90" align="center" show-overflow-tooltip />
      <el-table-column prop="latency" :label="$t('dashboard.table.latency')" min-width="90" align="center" show-overflow-tooltip>
        <template #default="scope">
          <span :style="{color: scope.row.latency > 10000 ? '#fa541c' : (scope.row.latency > 5000 ? '#faad14' : '#52c41a')}" >
            {{ scope.row.latency ? (scope.row.latency / 1000).toFixed(1) : '-' }}
          </span>
        </template>
      </el-table-column>
      <el-table-column prop="error_rate" :label="$t('dashboard.table.errorRate')" min-width="90" align="center" show-overflow-tooltip>
        <template #default="scope">
          <span :style="{color: scope.row.error_rate > 0.1 ? '#fa541c' : (scope.row.error_rate > 0.03 ? '#faad14' : '#52c41a')}" >
            {{ (scope.row.error_rate * 100).toFixed(2) }}%
          </span>
        </template>
      </el-table-column>
      <el-table-column prop="hit_count" :label="$t('dashboard.table.hitCount')" min-width="90" align="center" show-overflow-tooltip />
      <el-table-column prop="total_cost" :label="$t('dashboard.table.totalCost')" min-width="90" align="center" show-overflow-tooltip>
        <template #default="scope">
          {{ scope.row.total_cost ? scope.row.total_cost.toFixed(1) : '0.0' }}
        </template>
      </el-table-column>
    </el-table>

    <div style="margin-top:32px;">
      <div class="trend-header">
        <span class="title">{{ $t('dashboard.trend.title') }}</span>
        <el-button v-if="currentModel" size="small" @click="resetTrend">{{ $t('dashboard.trend.showAll') }}</el-button>
      </div>
      <v-chart :option="callsChartOption" style="height:240px;width:100%" />
      <div v-if="currentModel" style="text-align:center;margin-top:8px;font-size:16px;color:#1890ff;font-weight:500;">
        {{ currentModel }}
      </div>
    </div>
  </el-card>
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed, watch } from 'vue';
import VChart from 'vue-echarts';
import axios from 'axios';
import { useI18n } from 'vue-i18n';

const { t } = useI18n();

const llmStatusList = ref([]);
const llmBaseInfoMap = ref({});
const autoRefresh = ref(true);
let timer;
const currentModel = ref(null);

// 全局统计
const healthyModelCount = ref(0);
const totalModelCount = ref(0);
const totalQps = ref(0);
const totalHitCount = ref(0);
const avgHitRate = ref('0');

// 状态值国际化处理
function getStatusText(status) {
  if (!status) return '';
  
  // 将中文状态值转换为英文key，然后使用国际化
  const statusMap = {
    '可用': 'available',
    '下线': 'offline', 
    '未知': 'unknown',
    'available': 'available',
    'offline': 'offline',
    'unknown': 'unknown'
  };
  
  const statusKey = statusMap[status] || status;
  return t(`dashboard.status.${statusKey}`);
}

async function fetchLLMBaseInfo() {
  // 获取模型基础信息
  const res = await axios.post('/list_LLM').catch(() => ({ data: { models: [] } }));
  
  // 以模型名为key，便于后续合并
  llmBaseInfoMap.value = {};
  (res.data.models || []).forEach(m => {
    const meta = m.meta || {};
    llmBaseInfoMap.value[m.name] = {
      ...m,
      tags: meta.tags || m.tags || [],
      status: meta.status || m.status || '',
      qps: meta.qps || m.qps || 0,
      cost: meta.cost || m.cost || 0,
      version: m.version || '',
    };
  });
}

function onRowClick(row) {
  currentModel.value = row.name;
  fetchLLMStatus();
}

const callsChartOption = ref({
  tooltip: { trigger: 'axis' },
  grid: {
    left: '1%',
    right: '1%',
    bottom: '1%',
    containLabel: true
  },
  xAxis: { type: 'category', data: ['Mon','Tue','Wed','Thu','Fri','Sat','Sun'] },
  yAxis: { type: 'value', minInterval: 1 },
  series: [{ data: [0,0,0,0,0,0,0], type: 'line', smooth: true, areaStyle: {} }]
});

async function fetchData() {
  try {
    // 获取健康信息
    const h = await axios.get('/get_model_health');
    const healthData = h.data;
    
    // 获取QPS
    const q = await axios.get('/get_model_qps');
    const qpsData = q.data;
    
    // 获取命中次数
    const hit = await axios.get('/get_model_hit_count');
    const hitCounter = hit.data.hit_counter || {};
    
    // 获取总请求数
    const total = hit.data.total_request_count || 0;

    // 获取 LLM 状态（用于统计模型总数/健康数）
    let modelNames = Object.keys(healthData || {});
    totalModelCount.value = modelNames.length;
    
    const healthyModels = modelNames.filter(name => {
      const modelHealth = healthData[name];
      const statusVal = (modelHealth?.status || '').toString().toLowerCase();
      const healthVal = (modelHealth?.health || '').toString().toLowerCase();
              const isHealthy = statusVal === 'available' || healthVal === 'healthy' || modelHealth?.health === true || statusVal === $t('llmconfig.status.available');
      return isHealthy;
    });
    healthyModelCount.value = healthyModels.length;

    // 统计总QPS（所有模型QPS之和）
    totalQps.value = 0;
    if (qpsData) {
      for (const k in qpsData) {
        if (typeof qpsData[k] === 'number') totalQps.value += qpsData[k];
      }
    }

    // 统计总命中次数
    totalHitCount.value = Object.values(hitCounter).reduce((a, b) => a + b, 0);

    // 统计平均命中率
    avgHitRate.value = total ? ((totalHitCount.value / total) * 100).toFixed(2) : '0';
  } catch (error) {
    console.error('获取数据失败:', error);
  }
}

async function fetchLLMStatus() {
  let url = '/llm_status?t=' + Date.now();
  if (currentModel.value) {
    url += '&model=' + encodeURIComponent(currentModel.value);
  }
  // 并发请求命中次数和成本
  const [hit, cost] = await Promise.all([
    axios.get('/get_model_hit_count'),
    axios.get('/get_model_cost')
  ]);
  fetch(url)
    .then(resp => resp.json())
    .then(data => {
      if (data.llm_status) {
        llmStatusList.value = Object.entries(data.llm_status).map(([name, s]) => {
          // 合并基础信息
          const base = llmBaseInfoMap.value[name] || {};
          return {
            name,
            ...base, // tags, version, status等
            ...s,
            hit_count: hit.data.hit_counter?.[name] || 0,
            total_cost: cost.data?.[name] || 0
          };
        });
      }
      if (data.calls && data.dates) {
        callsChartOption.value.xAxis.data = data.dates;
        callsChartOption.value.series[0].data = data.calls;
      }
    });
}

function resetTrend() {
  currentModel.value = null;
  fetchLLMStatus();
}

function tableRowClassName({ row }) {
  const isSelected = String(row.name) === String(currentModel.value);
  return isSelected ? 'selected-row' : '';
}

watch(autoRefresh, (newVal) => {
  if (newVal) {
    timer = setInterval(() => {
      fetchData();
      fetchLLMStatus();
    }, 20000);
  } else if (timer) {
    clearInterval(timer);
  }
});

onMounted(async () => {
  await fetchLLMBaseInfo();
  fetchData();
  fetchLLMStatus();
  if (autoRefresh.value) {
    timer = setInterval(() => {
      fetchData();
      fetchLLMStatus();
    }, 20000);
  }
});

onUnmounted(() => {
  if (timer) clearInterval(timer);
});
</script>

<style>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-header .title {
  font-size: 16px;
  font-weight: 600;
}

.trend-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.trend-header .title {
  font-size: 14px;
  font-weight: 600;
}

.el-table{
  border: var(--el-table-border);
  border-bottom: none;
}
.el-table .selected-row {
  background: #e6f7ff !important;
}

.stat-card {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  padding: 16px 12px 12px 12px;
  min-height: 110px;
  border-radius: 10px;
  box-shadow: 0 2px 8px #f0f1f2;
}

.stat-icon {
  margin-bottom: 4px;
}

.stat-title {
  font-size: 14px;
  color: #888;
  margin-bottom: 2px;
}

.stat-value {
  font-size: 22px;
  font-weight: bold;
  color: #222;
}
</style> 
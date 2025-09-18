<template>
  <el-card>
    <template #header>
      <div class="card-header">
        <span class="title">{{ $t('history.title') }}</span>
      </div>
    </template>
    <el-table size="large" :data="history" :header-cell-style="{ background: '#F5F7FA' }" style="width: 100%">
      <el-table-column prop="time" :label="$t('history.time')" width="200" show-overflow-tooltip />
      <el-table-column prop="api" label="API" min-width="200" show-overflow-tooltip />
      <el-table-column :label="$t('history.params')" min-width="200" show-overflow-tooltip :tooltip-formatter="withVNode">
        <template #default="scope">
          <span>{{ JSON.stringify(scope.row.params) }}</span>
        </template>
      </el-table-column>
      <el-table-column :label="$t('history.result')" min-width="200" show-overflow-tooltip :tooltip-formatter="withVNode2">
        <template #default="scope">
          <span>{{ JSON.stringify(scope.row.params) }}</span>
          <!-- <pre style="white-space: pre-wrap;">{{ JSON.stringify(scope.row.result, null, 2) }}</pre> -->
        </template>
      </el-table-column>
    </el-table>
  </el-card>
</template>
<script setup>
import { h } from 'vue'
import { ElLink } from 'element-plus'
import { ref, onMounted } from 'vue';
const history = ref([]);
const formatTooltip = (obj) => {
  return `<pre style='max-width: 600px; white-space: pre-wrap;'>${JSON.stringify(obj, null, 2)}</pre>`;
};
const withVNode = (data) => {
  return h('pre', { style: 'white-space: pre-wrap;max-height: 500px;overflow: auto;' }, JSON.stringify(data.row.params, null, 2))
}
const withVNode2 = (data) => {
  return h('pre', { style: 'white-space: pre-wrap;max-height: 500px;overflow: auto;' }, JSON.stringify(data.row.result, null, 2))
}
onMounted(async () => {
  console.log('History mounted');
  try {
    const response = await fetch('/history?t=' + Date.now());
    const data = await response.json();
    console.log('history from backend:', data.history);
    history.value = data.history || [];
  } catch (e) {
    console.error('fetch /history error:', e);
    history.value = [];
  }
});
</script> 
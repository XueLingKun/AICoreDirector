<template>
  <el-card style="margin-bottom: 20px;">
    <template #header>
      <div class="card-header">
        <span class="title">{{ $t('discovery.registeredServices') }}</span>
      </div>
    </template>
    <el-table size="large" :data="services" style="width: 100%" :header-cell-style="{ background: '#F5F7FA' }" v-if="services.length">
      <el-table-column prop="endpoint" :label="$t('discovery.endpoint')" show-overflow-tooltip />
      <el-table-column prop="target_url" :label="$t('discovery.targetUrl')" show-overflow-tooltip />
      <el-table-column prop="status" :label="$t('discovery.health')" show-overflow-tooltip />
      <el-table-column prop="desc" :label="$t('discovery.description')" show-overflow-tooltip />
      <el-table-column prop="last_update_time" :label="$t('discovery.lastUpdated')" show-overflow-tooltip />
    </el-table>
    <div v-else style="color: #999">{{ $t('discovery.noServices') }}</div>
  </el-card>

  <el-card>
    <template #header>
      <div class="card-header">
        <span class="title">{{ $t('discovery.pluginAbilities') }}</span>
      </div>
    </template>
    <el-table size="large" :data="plugins" style="width: 100%" :header-cell-style="{ background: '#F5F7FA' }" v-if="plugins.length">
      <el-table-column prop="name" :label="$t('discovery.pluginName')" show-overflow-tooltip />
      <el-table-column prop="module" :label="$t('discovery.module')" show-overflow-tooltip />
      <el-table-column prop="params" :label="$t('discovery.params')" show-overflow-tooltip>
        <template #default="scope">{{ scope.row.params.join(', ') }}</template>
      </el-table-column>
      <el-table-column prop="doc" :label="$t('discovery.doc')" show-overflow-tooltip />
    </el-table>
    <div v-else style="color: #999">{{ $t('discovery.noPlugins') }}</div>
  </el-card>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import axios from 'axios';
const services = ref([]);
const plugins = ref([]);
async function fetchDiscovery() {
  const res = await axios.get('/service-discovery/list').catch(() => ({ data: { registered_services: [], plugin_abilities: [] } }));
  services.value = res.data.registered_services || [];
  plugins.value = res.data.plugin_abilities || [];
  console.log(services.value); 
}
onMounted(fetchDiscovery);
</script> 

<style>
  
</style>
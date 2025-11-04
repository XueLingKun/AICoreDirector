自动为你修正<template>
  <el-card>
    <template #header>
      <div class="card-header">
        <span class="title">{{ $t('llmconfig.title') }}</span>
        <div class="header-actions">
          <el-button type="primary" @click="showAddDialog = true">{{ $t('llmconfig.add') }}</el-button>
        </div>
      </div>
    </template>
    <el-table
      :data="llms"
      style="width: 100%;"
      border
      stripe
      size="large"
      :header-cell-style="{ fontWeight: 'bold', textAlign: 'center', background: '#F5F7FA' }"
    >
      <el-table-column prop="name" :label="$t('llmconfig.table.name')" min-width="200" fixed="left" show-overflow-tooltip />
      <el-table-column :label="$t('llmconfig.table.url')" min-width="200" show-overflow-tooltip>
        <template #default="scope">
          {{ scope.row.url || scope.row.base_url || '' }}
        </template>
      </el-table-column>
      <el-table-column prop="key" label="API Key" min-width="120" show-overflow-tooltip>
        <template #default="scope">
          <el-popover trigger="hover" :content="$t('llmconfig.showHide')">
            <el-button size="mini" @click="scope.row.showKey = !scope.row.showKey">
              {{ scope.row.showKey ? scope.row.key : '******' }}
            </el-button>
          </el-popover>
        </template>
      </el-table-column>
      <el-table-column prop="level" :label="$t('llmconfig.table.level')" min-width="80"/>
      <el-table-column prop="qps" label="QPS" min-width="80" align="center" show-overflow-tooltip/>
      <el-table-column prop="cost" :label="$t('llmconfig.table.unitCost')" min-width="90" align="center" show-overflow-tooltip/>
      <el-table-column prop="status" :label="$t('llmconfig.table.status')" min-width="80" align="center" show-overflow-tooltip>
        <template #default="scope">
          <el-tag :type="(['available','healthy',true].includes(scope.row.status)) ? 'success' : 'danger'">
            {{ $t('llmconfig.status.' + (scope.row.status === $t('llmconfig.status.available') ? 'available' : scope.row.status === $t('llmconfig.status.offline') ? 'offline' : scope.row.status === $t('llmconfig.status.unknown') ? 'unknown' : scope.row.status)) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="version" :label="$t('llmconfig.table.version')" min-width="80" align="center" show-overflow-tooltip/>
      <el-table-column prop="tags" :label="$t('llmconfig.table.tags')" min-width="180" show-overflow-tooltip>
        <template #default="scope">
          <el-tag
            v-for="tag in (scope.row.tags || [])"
            :key="tag"
            type="info"
            style="margin-right: 4px"
          >{{ tag }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="meta.latency" :label="$t('llmconfig.table.latency')" min-width="100" align="center" show-overflow-tooltip>
        <template #default="scope">
          {{ scope.row.meta?.latency ? (scope.row.meta.latency / 1000).toFixed(1) : '-' }}
        </template>
      </el-table-column>
      <el-table-column prop="meta.effect_score" :label="$t('llmconfig.table.effectScore')" min-width="90" align="center" show-overflow-tooltip/>
      <el-table-column prop="meta.max_input_length" :label="$t('llmconfig.table.maxInput')" min-width="90" align="center" show-overflow-tooltip/>
      <el-table-column prop="meta.supported_tasks" :label="$t('llmconfig.table.supportedTasks')" min-width="120" align="center" show-overflow-tooltip>
        <template #default="scope">
          <el-tag
            v-for="task in (scope.row.meta?.supported_tasks || [])"
            :key="task"
            type="info"
            style="margin-right: 4px"
          >{{ task }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="meta.languages" :label="$t('llmconfig.table.languages')" min-width="100" align="center" show-overflow-tooltip>
        <template #default="scope">
          <el-tag
            v-for="lang in (scope.row.meta?.languages || [])"
            :key="lang"
            type="success"
            style="margin-right: 4px"
          >{{ lang }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="meta.description" :label="$t('llmconfig.table.description')" min-width="180" align="center" show-overflow-tooltip/>
      <el-table-column :label="$t('llmconfig.table.actions')" fixed="right" width="200" align="center">
        <template #default="scope">
         <el-button-group>
           <el-button size="small" type="success" @click="testLLM(scope.row)">{{ $t('llmconfig.actions.test') }}</el-button>
           <el-button size="small" type="primary" @click="editLLM(scope.row)">{{ $t('llmconfig.actions.edit') }}</el-button>
           <el-button size="small" type="danger" @click="deleteLLM(scope.row)">{{ $t('llmconfig.actions.delete') }}</el-button>
         </el-button-group>
       </template>
      </el-table-column>
    </el-table>
    <!-- 添加/编辑对话框 -->
    <el-dialog v-model="showAddDialog" :title="$t('llmconfig.dialog.title')" width="800px">
      <el-form :model="form" label-width="auto">
        <el-form-item :label="$t('llmconfig.form.name')"><el-input v-model="form.name" /></el-form-item>
        <el-form-item :label="$t('llmconfig.form.url')"><el-input v-model="form.url" /></el-form-item>
        <el-form-item label="API Key"><el-input v-model="form.key" /></el-form-item>
        <el-form-item :label="$t('llmconfig.form.level')"><el-select v-model="form.level"><el-option label="premium" value="premium"/><el-option label="standard" value="standard"/><el-option label="economy" value="economy"/></el-select></el-form-item>
        <el-form-item label="QPS"><el-input v-model.number="form.qps" /></el-form-item>
        <el-form-item :label="$t('llmconfig.form.unitCost')"><el-input v-model.number="form.cost" /></el-form-item>
        <el-form-item :label="$t('llmconfig.form.status')"><el-input v-model="form.status" /></el-form-item>
        <el-form-item :label="$t('llmconfig.form.version')"><el-input v-model="form.version" /></el-form-item>
        <el-form-item :label="$t('llmconfig.form.tags')"><el-input v-model="form.tagsStr" placeholder="," /></el-form-item>
        <el-form-item :label="$t('llmconfig.form.maxInput')"><el-input v-model.number="form.max_input_length" /></el-form-item>
        <el-form-item :label="$t('llmconfig.form.supportedTasks')"><el-input v-model="form.supported_tasksStr" placeholder="," /></el-form-item>
        <el-form-item :label="$t('llmconfig.form.languages')"><el-input v-model="form.languagesStr" placeholder="," /></el-form-item>
        <el-form-item :label="$t('llmconfig.form.effectScore')"><el-input v-model.number="form.effect_score" /></el-form-item>
        <el-form-item :label="$t('llmconfig.form.description')"><el-input v-model="form.description" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAddDialog = false">{{ $t('common.cancel') }}</el-button>
        <el-button type="primary" @click="saveLLM">{{ $t('common.save') }}</el-button>
      </template>
    </el-dialog>
    
    <!-- LLM测试对话框 -->
    <el-dialog v-model="showTestDialog" :title="$t('llmconfig.test.title')" width="800px">
      <el-form :model="testForm" label-width="120px">
        <el-form-item :label="$t('llmconfig.test.selectModel')">
          <el-input v-model="testForm.model_name" disabled />
        </el-form-item>
        
        <el-form-item :label="$t('llmconfig.test.prompt')">
          <el-input
            v-model="testForm.prompt"
            type="textarea"
            :rows="4"
            :placeholder="$t('llmconfig.test.placeholder')"
          />
        </el-form-item>
        
        <el-form-item>
          <el-button type="primary" @click="callLLM" :loading="testLoading">{{ $t('llmconfig.test.send') }}</el-button>
          <el-button @click="testForm.prompt = $t('llmconfig.test.defaultPrompt')">{{ $t('llmconfig.test.useDefault') }}</el-button>
        </el-form-item>
      </el-form>
      
      <el-divider />
      
      <div v-if="testResult">
        <h3>{{ $t('llmconfig.test.resultTitle') }}</h3>
        <el-card>
          <div v-if="testResult.error" class="error-result">
            <el-alert
              :title="$t('llmconfig.test.callFail')"
              :description="testResult.error"
              type="error"
              show-icon
            />
          </div>
          <div v-else class="success-result">
            <el-alert
              :title="$t('llmconfig.test.callOk')"
              :description="$t('llmconfig.test.modelOk')"
              type="success"
              show-icon
            />
            <el-divider />
            <h4>{{ $t('llmconfig.test.response') }}</h4>
            <el-input
              v-model="testResult.result"
              type="textarea"
              :rows="6"
              readonly
            />
            <el-divider />
            <h4>{{ $t('llmconfig.test.details') }}</h4>
            <pre class="result-details">{{ JSON.stringify(testResult, null, 2) }}</pre>
          </div>
        </el-card>
      </div>
    </el-dialog>
  </el-card>
</template>
<script setup>
import { ref, onMounted } from 'vue';
import axios from 'axios';
import { ElMessage } from 'element-plus';
const llms = ref([]);
const showAddDialog = ref(false);
const showTestDialog = ref(false);
const form = ref({ name: '', url: '', key: '', level: 'standard', qps: 2, cost: 0, status: 'available', version: '', tagsStr: '', max_input_length: 0, supported_tasksStr: '', languagesStr: '', effect_score: 0, description: '' });
const testForm = ref({ model_name: '', prompt: '' });
const testResult = ref(null);
const testLoading = ref(false);
let editing = null;

async function fetchLLMs() {
  const res = await axios.post('/list_LLM').catch(() => ({ data: { models: [] } }));
  llms.value = (res.data.models || []).map(m => {
    const meta = m.meta || {};
    return {
      ...m,
      tags: meta.tags || m.tags || [],
      status: meta.status || m.status || '',
      qps: meta.qps || m.qps || 0,
      cost: meta.cost || m.cost || 0,
      tagsStr: (meta.tags || m.tags || []).join(','),
      showKey: false
    };
  });
}

function editLLM(row) {
  editing = row.name;
  form.value = { ...row, tagsStr: (row.tags || []).join(','), supported_tasksStr: (row.meta?.supported_tasks || []).join(','), languagesStr: (row.meta?.languages || []).join(',') };
  showAddDialog.value = true;
}

async function saveLLM() {
  try {
    const payload = {
      ...form.value,
      tags: form.value.tagsStr.split(',').map(t => t.trim()).filter(Boolean),
      supported_tasks: form.value.supported_tasksStr ? form.value.supported_tasksStr.split(',').map(t => t.trim()).filter(Boolean) : [],
      languages: form.value.languagesStr ? form.value.languagesStr.split(',').map(t => t.trim()).filter(Boolean) : [],
    };
    delete payload.tagsStr;
    delete payload.supported_tasksStr;
    delete payload.languagesStr;

    // 构建meta字段
    payload.meta = {
      tags: payload.tags,
      status: payload.status,
      qps: payload.qps,
      cost: payload.cost,
      max_input_length: payload.max_input_length,
      supported_tasks: payload.supported_tasks,
      languages: payload.languages,
      effect_score: payload.effect_score,
      description: payload.description
    };

    if (editing) {
      await axios.post('/api/llm/update', payload);
    } else {
      await axios.post('/api/llm/add', payload);
    }
    showAddDialog.value = false;
    editing = null;
    await fetchLLMs();
  } catch (error) {
    console.error($t('common.errors.saveFailed') + ':', error);
    ElMessage.error(error.response?.data?.error || $t('common.errors.saveFailedNetwork'));
  }
}

async function deleteLLM(row) {
  await axios.post('/api/llm/delete', { name: row.name });
  await fetchLLMs();
}

function testLLM(row) {
  testForm.value.model_name = row.name;
  testForm.value.prompt = $t('llmconfig.test.defaultPrompt');
  testResult.value = null;
  showTestDialog.value = true;
}

async function callLLM() {
  if (!testForm.value.model_name || !testForm.value.prompt) {
    ElMessage.warning($t('common.errors.selectModelAndPrompt'));
    return;
  }
  
  testLoading.value = true;
  testResult.value = null;
  
  try {
    const response = await axios.post('/llm_invoke', {
      prompt: testForm.value.prompt,
      model_name: testForm.value.model_name
    });
    
    testResult.value = response.data;
    ElMessage.success('LLM调用成功！');
    console.log('LLM调用成功:', response.data);
  } catch (error) {
    console.error('LLM调用失败:', error);
    testResult.value = {
      error: error.response?.data || error.message
    };
    ElMessage.error('LLM调用失败，请检查模型配置');
  } finally {
    testLoading.value = false;
  }
}

onMounted(fetchLLMs);
</script> 

<style scoped>
  .el-table{
    border: none;
  }
  
  .error-result {
    margin-bottom: 16px;
  }
  
  .success-result h4 {
    margin: 16px 0 8px 0;
    color: #409eff;
    font-weight: 600;
  }
  
  .result-details {
    background: #f5f7fa;
    padding: 12px;
    border-radius: 4px;
    font-size: 12px;
    line-height: 1.5;
    max-height: 300px;
    overflow-y: auto;
    border: 1px solid #e4e7ed;
  }
  
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  
  .card-header .title {
    font-size: 16px;
    font-weight: 600;
  }
</style>
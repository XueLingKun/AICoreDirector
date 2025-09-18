<template>
  <div class="center">
    <el-row :gutter="15" class="prompt-row">
      <!-- 左侧-文件列表 -->
      <el-col :span="8">
        <el-card>
          <template #header>
            <div class="card-header">
              <span class="title">{{ $t('promptMgr.fileList') }}</span>
              <div class="header-actions">
                <el-dropdown @command="onDropdownCommand">
                  <el-button type="primary" @click="showNewPrompt = true">{{ $t('promptMgr.newPrompt') }}</el-button>
                  <template #dropdown>
                    <el-dropdown-menu>
                      <el-dropdown-item command="list">{{ $t('promptMgr.fileList') }}</el-dropdown-item>
                      <el-dropdown-item command="new">{{ $t('promptMgr.newPrompt') }}</el-dropdown-item>
                    </el-dropdown-menu>
                  </template>
                </el-dropdown>
              </div>
            </div>
          </template>
          <!-- 普通文件区域 -->
          <div v-if="normalFiles.length > 0">
            <h4 style="margin-bottom: 10px; color: #333;">{{ $t('promptMgr.normalFiles') }}</h4>
            <el-row :gutter="15">
              <el-col :span="8" v-for="(item, index) in normalFiles" :key="`normal-${index}`" style="margin-bottom: 15px">
                <el-card 
                  class="box-card" 
                  :class="{ 'selected-file': currentFile === item }"
                  @click="onSelectFile(item)"
                >
                  <div class="text item">
                    {{ item }}
                  </div>
                </el-card>
              </el-col>
            </el-row>
          </div>
          
          <!-- 备份文件区域 -->
          <div v-if="backupFiles.length > 0" class="backup-section">
            <h4 style="margin-bottom: 10px; color: #999;">{{ $t('promptMgr.backupFiles') }}</h4>
            <el-row :gutter="15">
              <el-col :span="8" v-for="(item, index) in backupFiles" :key="`backup-${index}`" style="margin-bottom: 15px">
                <el-card 
                  class="box-card backup-file"
                  :class="{ 'selected-file': currentFile === item }"
                  @click="onSelectFile(item)"
                >
                  <div class="text item">
                    {{ item }}
                  </div>
                </el-card>
              </el-col>
            </el-row>
          </div>
        </el-card>
      </el-col>
      <!-- 右侧-文件内容 -->
      <el-col :span="16">
        <el-card class="prompt-card">
          <template #header>
            <div class="card-header">
              <span class="title">{{ currentFile || $t('promptMgr.selectFile') }}</span>
              <div class="header-actions" v-show="currentFile">
                <!-- 普通文件的按钮 -->
                <template v-if="!isBackupFile(currentFile)">
                  <el-button type="primary" @click="saveFile">{{ $t('common.save') }}</el-button>
                  <el-button type="primary" @click="saveOther">{{ $t('common.saveAs') }}</el-button>
                  <el-button type="danger" @click="deleteFile(currentFile)">{{ $t('common.delete') }}</el-button>
                  <el-button @click="cancelFile">{{ $t('common.cancel') }}</el-button>
                </template>
                <!-- 备份文件的按钮 -->
                <template v-else>
                  <el-button type="success" @click="restoreFile">{{ $t('common.restore') }}</el-button>
                  <el-button type="danger" @click="permanentlyDeleteFile">{{ $t('common.deletePermanent') }}</el-button>
                  <el-button @click="cancelFile">{{ $t('common.cancel') }}</el-button>
                </template>
              </div>
            </div>
          </template>
          <el-input
            v-if="currentFile"
            type="textarea"
            resize="none"
            v-model="fileContent"
            :readonly="isBackupFile(currentFile)"
          />
        </el-card>
      </el-col>
    </el-row>

    <el-dialog
      v-model="showNewPrompt"
      :title="$t('promptMgr.dialog.newTitle')"
      @close="handleDialogClose"
    >
      <el-input
        v-model="newFileName"
        :placeholder="$t('promptMgr.dialog.filenamePlaceholder')"
      />
      <el-input
        type="textarea"
        v-model="newFileContent"
        :rows="10"
        :placeholder="$t('promptMgr.dialog.contentPlaceholder')"
        style="margin: 10px 0"
      />
      <template #footer>
        <el-button @click="handleDialogClose">{{ $t('common.cancel') }}</el-button>
        <el-button type="primary" @click="createFile">{{ $t('common.create') }}</el-button>
      </template>
    </el-dialog>

    <!-- 删除确认对话框 -->
    <el-dialog
      v-model="showDeleteDialog"
      :title="$t('promptMgr.dialog.confirmDeleteTitle')"
      width="400px"
    >
      <div class="delete-confirm">
        <el-alert
          :title="$t('promptMgr.dialog.deleteConfirm')"
          :description="$t('promptMgr.dialog.deleteDesc', { file: fileToDelete })"
          type="warning"
          show-icon
        />
      </div>
      <template #footer>
        <el-button @click="showDeleteDialog = false">{{ $t('common.cancel') }}</el-button>
        <el-button type="danger" @click="confirmDelete">{{ $t('promptMgr.dialog.confirmDelete') }}</el-button>
      </template>
    </el-dialog>

    <!-- 保存确认对话框 -->
    <el-dialog
      v-model="showSaveDialog"
      :title="$t('promptMgr.dialog.confirmSaveTitle')"
      width="400px"
    >
      <div class="save-confirm">
        <el-alert
          :title="$t('promptMgr.dialog.saveConfirm')"
          :description="$t('promptMgr.dialog.saveDesc', { file: currentFile })"
          type="info"
          show-icon
        />
      </div>
      <template #footer>
        <el-button @click="showSaveDialog = false">{{ $t('common.cancel') }}</el-button>
        <el-button type="primary" @click="confirmSave">{{ $t('promptMgr.dialog.confirmSave') }}</el-button>
      </template>
    </el-dialog>

    <!-- 恢复确认对话框 -->
    <el-dialog
      v-model="showRestoreDialog"
      :title="$t('promptMgr.dialog.confirmRestoreTitle')"
      width="400px"
    >
      <div class="restore-confirm">
        <el-alert
          :title="$t('promptMgr.dialog.restoreConfirm')"
          :description="$t('promptMgr.dialog.restoreDesc', { file: currentFile })"
          type="warning"
          show-icon
        />
      </div>
      <template #footer>
        <el-button @click="showRestoreDialog = false">{{ $t('common.cancel') }}</el-button>
        <el-button type="success" @click="confirmRestore">{{ $t('promptMgr.dialog.confirmRestore') }}</el-button>
      </template>
    </el-dialog>

    <!-- 彻底删除确认对话框 -->
    <el-dialog
      v-model="showPermanentDeleteDialog"
      :title="$t('promptMgr.dialog.confirmPermanentDeleteTitle')"
      width="400px"
    >
      <div class="permanent-delete-confirm">
        <el-alert
          :title="$t('promptMgr.dialog.permanentDeleteConfirm')"
          :description="$t('promptMgr.dialog.permanentDeleteDesc', { file: currentFile })"
          type="error"
          show-icon
        />
      </div>
      <template #footer>
        <el-button @click="showPermanentDeleteDialog = false">{{ $t('common.cancel') }}</el-button>
        <el-button type="danger" @click="confirmPermanentDelete">{{ $t('promptMgr.dialog.confirmPermanentDelete') }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>
<script setup>
import { ref, onMounted, computed } from "vue";
import { ElMessage } from "element-plus";
import axios from "axios";

const fileList = ref([]);
const currentFile = ref("");
const fileContent = ref("");
const originalContent = ref(""); // 保存原始内容用于检测修改
const showNewPrompt = ref(false);
const newFileName = ref("");
const newFileContent = ref("");
const showList = ref(true);
const showDeleteDialog = ref(false);
const showSaveDialog = ref(false);
const showRestoreDialog = ref(false);
const showPermanentDeleteDialog = ref(false);
const fileToDelete = ref("");

// 判断是否为备份文件
function isBackupFile(fileName) {
  if (!fileName) return false;
  return fileName.includes('_备份') ||
         fileName.includes('_删除备份') ||
         fileName.includes('_副本') ||
         fileName.includes('_恢复前备份') ||
         fileName.includes('_backup') ||
         fileName.includes('_delete_backup') ||
         fileName.includes('_pre_restore_backup') ||
         fileName.includes('_copy');
}



// 从备份文件名中提取原文件名
function getOriginalFileName(backupFileName) {
  if (backupFileName.includes('_备份')) {
    return backupFileName.split('_备份')[0];
  } else if (backupFileName.includes('_删除备份')) {
    return backupFileName.split('_删除备份')[0];
  } else if (backupFileName.includes('_副本')) {
    return backupFileName.split('_副本')[0];
  } else if (backupFileName.includes('_恢复前备份')) {
    return backupFileName.split('_恢复前备份')[0];
  } else if (backupFileName.includes('_backup')) {
    return backupFileName.split('_backup')[0];
  } else if (backupFileName.includes('_delete_backup')) {
    return backupFileName.split('_delete_backup')[0];
  } else if (backupFileName.includes('_pre_restore_backup')) {
    return backupFileName.split('_pre_restore_backup')[0];
  } else if (backupFileName.includes('_copy')) {
    return backupFileName.split('_copy')[0];
  }
  return backupFileName;
}

// 计算属性：分离普通文件和备份文件
const normalFiles = computed(() => {
  return fileList.value.filter(file => !isBackupFile(file));
});

const backupFiles = computed(() => {
  return fileList.value.filter(file => isBackupFile(file));
});

async function fetchFileList() {
  const resp = await axios.get("/api/prompts/list");
  fileList.value = resp.data.files;
}

function cancelFile() {
  currentFile.value = "";
  fileContent.value = "";
}

async function onSelectFile(name) {
  currentFile.value = name;
  const resp = await axios.get("/api/prompts/file", { params: { name } });
  fileContent.value = resp.data.content;
  originalContent.value = resp.data.content; // 保存原始内容
}

function saveOther() {
  newFileName.value = currentFile.value + "_copy";
  newFileContent.value = fileContent.value;
  showNewPrompt.value = true;
}

async function saveFile() {
  // 检查是否有修改
  if (fileContent.value === originalContent.value) {
    ElMessage.info("文件未修改，无需保存");
    return;
  }
  
  // 显示确认对话框
  showSaveDialog.value = true;
}

async function confirmSave() {
  try {
    // 保存修改后的文件（后端会自动创建备份）
    await axios.post("/api/prompts/file", {
      name: currentFile.value,
      content: fileContent.value,
    });
    
    originalContent.value = fileContent.value; // 更新原始内容
    showSaveDialog.value = false;
            ElMessage.success($t('common.success.saveSuccess'));
  } catch (error) {
            ElMessage.error($t('common.errors.saveFailed') + "：" + error.message);
  }
}

async function createFile() {
  if (!newFileName.value) return ElMessage.error("请输入文件名");
  await axios.post("/api/prompts/new", {
    name: newFileName.value,
    content: newFileContent.value,
  });
  showNewPrompt.value = false;
  newFileName.value = "";
  newFileContent.value = "";
  fetchFileList();
  ElMessage.success("创建成功");
}

function onDropdownCommand(cmd) {
  if (cmd === "list") showList.value = true;
  if (cmd === "new") {
    showList.value = false;
    showNewPrompt.value = true;
  }
}

function handleDialogClose() {
  showNewPrompt.value = false;
  showList.value = true;
}

// 删除文件相关函数
function deleteFile(fileName) {
  fileToDelete.value = fileName;
  showDeleteDialog.value = true;
}

async function confirmDelete() {
  try {
    // 删除原文件（后端会自动创建备份）
    await axios.post("/api/prompts/delete", { name: fileToDelete.value });
    
    const deletedFileName = fileToDelete.value;
    showDeleteDialog.value = false;
    fileToDelete.value = "";
    
    // 如果删除的是当前打开的文件，清空当前文件
    if (currentFile.value === deletedFileName) {
      currentFile.value = "";
      fileContent.value = "";
      originalContent.value = "";
    }
    
    await fetchFileList(); // 刷新文件列表
    ElMessage.success("删除成功，文件已备份");
  } catch (error) {
    ElMessage.error("删除失败：" + error.message);
  }
}

// 恢复备份文件
function restoreFile() {
  showRestoreDialog.value = true;
}

async function confirmRestore() {
  try {
    const backupFileName = currentFile.value;
    const originalFileName = getOriginalFileName(backupFileName);
    
    // 使用新的恢复API
    await axios.post("/api/prompts/restore", {
      backup_name: backupFileName,
      original_name: originalFileName,
      content: fileContent.value,
    });
    
    showRestoreDialog.value = false;
    ElMessage.success(`恢复成功，文件已恢复为 '${originalFileName}'`);
    
    // 刷新文件列表并清空当前文件
    await fetchFileList();
    currentFile.value = "";
    fileContent.value = "";
    originalContent.value = "";
  } catch (error) {
    ElMessage.error("恢复失败：" + error.message);
  }
}

// 彻底删除备份文件
function permanentlyDeleteFile() {
  showPermanentDeleteDialog.value = true;
}

async function confirmPermanentDelete() {
  try {
    const fileName = currentFile.value;
    
    // 直接删除备份文件，不创建新的备份
    await axios.post("/api/prompts/delete", { name: fileName });
    
    showPermanentDeleteDialog.value = false;
    ElMessage.success("备份文件已彻底删除");
    
    // 刷新文件列表并清空当前文件
    await fetchFileList();
    currentFile.value = "";
    fileContent.value = "";
    originalContent.value = "";
  } catch (error) {
    ElMessage.error("彻底删除失败：" + error.message);
  }
}

onMounted(fetchFileList);
</script>

<style scoped>
.center {
  /* margin: 50px 0px; */
  width: 100%;
  height: 100%;
  /* display: flex;
  justify-content: center;
  align-items: center; */
  /* overflow: hidden; */
}
.box-card {
  width: 100%;
  cursor: pointer;
  transition: transform 0.3s ease;
}
.box-card:hover {
  transform: translateY(-5px);
}
.box-card .item {
  display: flex;
  align-items: center;
}

/* 备份文件样式 */
.backup-file {
  opacity: 0.6;
  background-color: #f5f5f5;
  border: 1px solid #e0e0e0;
}
.backup-file .item {
  color: #999;
}
.backup-file:hover {
  opacity: 0.8;
  background-color: #f0f0f0;
}

/* 备份文件区域样式 */
.backup-section {
  border-top: 1px solid #e0e0e0;
  padding-top: 15px;
}

/* 选中文件样式 */
.selected-file {
  border: 2px solid #409eff !important;
  box-shadow: 0 0 8px rgba(64, 158, 255, 0.3);
}
.selected-file .item {
  font-weight: bold;
  color: #409eff !important;
}
/* 备份文件被选中时的特殊样式 */
.backup-file.selected-file {
  opacity: 1 !important;
  background-color: #f0f8ff !important;
}
.backup-file.selected-file .item {
  color: #409eff !important;
}

.prompt-row{
  /* width: 100%; */
  height: 100%;
}
.prompt-row .el-col{
  height: 100%;
}

.el-card{
  height: 100%;
  display: flex;
  flex-direction: column;
  /* overflow: hidden; */
}
.el-card :deep(.el-card__body){
  flex: 1;
  overflow: auto;
}
.card-header{
  height: 32px;
}
.el-textarea{
  height: 100%;
  width: 100%;
}
.el-textarea :deep(.el-textarea__inner){
  height: 100% !important;
}
</style>

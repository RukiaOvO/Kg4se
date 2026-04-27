<template>
  <div class="upload-page">
    <!-- Page Header -->
    <div class="page-header">
      <div class="header-content">
        <h1 class="page-title">{{ t('upload.title') }}</h1>
        <p class="page-subtitle">支持文件上传、文本输入、网页链接，使用 GraphRAG Pipeline 构建知识图谱</p>
      </div>
    </div>

    <n-space vertical :size="24">
      <!-- Input Method Tabs -->
      <n-card class="upload-card" :bordered="false">
        <n-tabs v-model:value="activeTab" type="segment" animated>
          <!-- File Upload Tab -->
          <n-tab-pane name="file" tab="文件上传">
            <div class="tab-content">
              <div class="section-header">
                <n-icon size="20"><cloud-upload-outline /></n-icon>
                <h3>上传文档文件</h3>
              </div>
              <n-upload
                :max="1"
                :default-upload="false"
                @change="handleFileChange"
                :show-file-list="false"
                accept=".pdf,.md,.markdown,.txt,.doc,.docx"
              >
                <n-upload-dragger class="enhanced-dragger">
                  <div class="dragger-content">
                    <div class="dragger-icon-wrapper">
                      <n-icon size="64" :component="CloudUploadOutline" class="dragger-icon" />
                    </div>
                    <div class="dragger-text">
                      <h3>{{ t('upload.choose_file') }}</h3>
                      <p>{{ t('upload.drag_hint') }}</p>
                      <div class="dragger-formats">
                        <n-tag :bordered="false" size="small" type="warning">PDF</n-tag>
                        <n-tag :bordered="false" size="small" type="success">Markdown</n-tag>
                        <n-tag :bordered="false" size="small" type="info">TXT</n-tag>
                        <n-tag :bordered="false" size="small" type="error">Word</n-tag>
                      </div>
                    </div>
                  </div>
                </n-upload-dragger>
              </n-upload>

              <!-- File Info Card -->
              <div v-if="selectedFile" class="file-selected-card">
                <div class="file-preview">
                  <div class="file-icon-wrapper">
                    <n-icon size="40" :component="DocumentTextOutline" />
                  </div>
                  <div class="file-details">
                    <div class="file-name">{{ selectedFile.name }}</div>
                    <div class="file-meta">
                      <span class="file-size">{{ formatFileSize(selectedFile.size) }}</span>
                      <n-divider vertical />
                      <span class="file-type">{{ getFileType(selectedFile.name) }}</span>
                    </div>
                  </div>
                  <n-button circle quaternary @click="removeFile">
                    <template #icon>
                      <n-icon :component="CloseOutline" />
                    </template>
                  </n-button>
                </div>

                <n-button
                  type="primary"
                  :loading="uploading"
                  @click="handleUpload"
                  block
                  size="large"
                  class="upload-button"
                >
                  <template #icon>
                    <n-icon><rocket-outline /></n-icon>
                  </template>
                  {{ t('upload.upload_process') }}
                </n-button>
              </div>
            </div>
          </n-tab-pane>

          <!-- Text Input Tab -->
          <n-tab-pane name="text" tab="文本输入">
            <div class="tab-content">
              <div class="section-header">
                <n-icon size="20"><document-text-outline /></n-icon>
                <h3>直接输入文本内容</h3>
              </div>
              <n-form>
                <n-form-item label="文档标题（可选）">
                  <n-input
                    v-model:value="textTitle"
                    placeholder="为文档起个标题，留空则自动生成"
                    :maxlength="100"
                    show-count
                  />
                </n-form-item>
                <n-form-item label="文本内容">
                  <n-input
                    v-model:value="textContent"
                    type="textarea"
                    placeholder="粘贴或输入文本内容（至少10个字符）..."
                    :rows="12"
                    :maxlength="100000"
                    show-count
                  />
                </n-form-item>

                <n-button
                  type="primary"
                  :loading="uploading"
                  :disabled="!textContent || textContent.trim().length < 10"
                  @click="handleTextUpload"
                  block
                  size="large"
                  class="upload-button"
                >
                  <template #icon>
                    <n-icon><rocket-outline /></n-icon>
                  </template>
                  提交文本并处理
                </n-button>
              </n-form>
            </div>
          </n-tab-pane>

          <!-- URL Input Tab -->
          <n-tab-pane name="url" tab="网页链接">
            <div class="tab-content">
              <div class="section-header">
                <n-icon size="20"><globe-outline /></n-icon>
                <h3>从网页抓取内容</h3>
              </div>
              <n-form>
                <n-form-item label="网页链接">
                  <n-input
                    v-model:value="urlInput"
                    placeholder="输入网页 URL，例如：https://example.com/article"
                    :maxlength="2000"
                  >
                    <template #prefix>
                      <n-icon :component="LinkOutline" />
                    </template>
                  </n-input>
                </n-form-item>
                <n-form-item label="文档标题（可选）">
                  <n-input
                    v-model:value="urlTitle"
                    placeholder="为文档起个标题，留空则使用网页标题"
                    :maxlength="100"
                    show-count
                  />
                </n-form-item>
                <n-alert type="info" style="margin-bottom: 16px">
                  系统将自动抓取网页内容并使用 GraphRAG Pipeline 构建知识图谱
                </n-alert>

                <n-button
                  type="primary"
                  :loading="uploading"
                  :disabled="!urlInput || !isValidUrl(urlInput)"
                  @click="handleUrlUpload"
                  block
                  size="large"
                  class="upload-button"
                >
                  <template #icon>
                    <n-icon><rocket-outline /></n-icon>
                  </template>
                  抓取网页并处理
                </n-button>
              </n-form>
            </div>
          </n-tab-pane>
        </n-tabs>
      </n-card>

      <!-- Processing Progress Card -->
      <transition name="slide-fade">
        <n-card v-if="currentTask" class="progress-card" :bordered="false">
          <div class="section-header">
            <n-icon size="20">
              <checkmark-circle-outline v-if="processCompleted" />
              <close-outline v-else-if="processFailed" />
              <rocket-outline v-else />
            </n-icon>
            <h3>
              <span v-if="processCompleted">处理完成</span>
              <span v-else-if="processFailed">处理失败</span>
              <span v-else>GraphRAG Pipeline 处理中</span>
            </h3>
          </div>

          <!-- Document Info -->
          <n-descriptions v-if="uploadResult" bordered :column="1" class="result-descriptions" style="margin-bottom: 20px">
            <n-descriptions-item label="文档 ID">
              <n-text code strong>{{ uploadResult.documentId }}</n-text>
            </n-descriptions-item>
            <n-descriptions-item label="文件名">
              <n-text>{{ uploadResult.filename }}</n-text>
            </n-descriptions-item>
            <n-descriptions-item v-if="currentJobId" label="任务 ID">
              <n-text code>{{ currentJobId }}</n-text>
            </n-descriptions-item>
          </n-descriptions>

          <!-- Progress Bar -->
          <div v-if="processing || processCompleted" class="progress-section">
            <div class="progress-info">
              <span class="progress-label">{{ pipelineStageLabel }}</span>
              <span class="progress-percent">{{ progress }}%</span>
            </div>
            <n-progress
              type="line"
              :percentage="progress"
              :status="processFailed ? 'error' : processCompleted ? 'success' : 'default'"
              :show-indicator="false"
              :height="12"
              border-radius="6px"
            />
            <!-- Pipeline Stage Steps -->
            <div v-if="processing" class="pipeline-stages">
              <div
                v-for="(stage, index) in pipelineStages"
                :key="index"
                class="stage-item"
                :class="{
                  active: currentStageIndex === index,
                  completed: currentStageIndex > index,
                  pending: currentStageIndex < index
                }"
              >
                <div class="stage-dot">
                  <n-icon v-if="currentStageIndex > index" size="14" :component="CheckmarkCircleOutline" />
                  <span v-else>{{ index + 1 }}</span>
                </div>
                <span class="stage-name">{{ stage }}</span>
              </div>
            </div>
          </div>

          <!-- Stats (when completed) -->
          <div v-if="processCompleted && processStats" class="stats-grid">
            <div class="stat-item">
              <div class="stat-value">{{ processStats.chunks }}</div>
              <div class="stat-label">文本块</div>
            </div>
            <div class="stat-item">
              <div class="stat-value">{{ processStats.entities }}</div>
              <div class="stat-label">实体</div>
            </div>
            <div class="stat-item">
              <div class="stat-value">{{ processStats.claims }}</div>
              <div class="stat-label">论断</div>
            </div>
            <div class="stat-item">
              <div class="stat-value">{{ processStats.themes }}</div>
              <div class="stat-label">主题</div>
            </div>
            <div class="stat-item">
              <div class="stat-value">{{ processStats.relationships }}</div>
              <div class="stat-label">关系</div>
            </div>
          </div>

          <!-- Quality Metrics (when completed) -->
          <div v-if="processCompleted && currentTask?.qualityMetrics" class="quality-section">
            <n-divider style="margin: 20px 0">质量指标</n-divider>
            <div class="quality-grid">
              <div class="quality-item">
                <div class="quality-label">孤立节点比例</div>
                <div class="quality-value">{{ ((currentTask.qualityMetrics.isolated_node_ratio || 0) * 100).toFixed(1) }}%</div>
              </div>
              <div class="quality-item">
                <div class="quality-label">平均度数</div>
                <div class="quality-value">{{ (currentTask.qualityMetrics.avg_degree || 0).toFixed(2) }}</div>
              </div>
            </div>
          </div>

          <!-- Execution Time (when completed) -->
          <div v-if="processCompleted && processStats?.execution_time" class="execution-time">
            <n-tag type="info" :bordered="false" size="small">
              ⏱ 处理耗时: {{ processStats.execution_time.toFixed(1) }}s
            </n-tag>
          </div>

          <!-- Error Message -->
          <n-alert v-if="processFailed" type="error" style="margin-top: 16px">
            {{ progressMessage || '处理过程中发生错误' }}
          </n-alert>

          <!-- Actions -->
          <n-space vertical :size="12" style="margin-top: 20px">
            <n-button
              v-if="processCompleted"
              type="primary"
              @click="$router.push('/graph')"
              block
              size="large"
              class="action-button"
            >
              查看知识图谱
            </n-button>
            
            <n-button
              @click="resetUpload"
              block
              size="large"
            >
              <template #icon>
                <n-icon><add-circle-outline /></n-icon>
              </template>
              上传新文档
            </n-button>
          </n-space>
        </n-card>
      </transition>
    </n-space>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useMessage } from 'naive-ui'
import { useProcessingStore } from '@/stores/processing'
import {
  CloudUploadOutline,
  DocumentTextOutline,
  CloseOutline,
  RocketOutline,
  CheckmarkCircleOutline,
  AddCircleOutline,
  GlobeOutline,
  LinkOutline
} from '@vicons/ionicons5'
import { uploadFile, uploadText, uploadUrl } from '@/api/services'

const router = useRouter()
const { t } = useI18n()
const message = useMessage()
const processingStore = useProcessingStore()

const activeTab = ref('file')
const selectedFile = ref(null)
const textContent = ref('')
const textTitle = ref('')
const urlInput = ref('')
const urlTitle = ref('')
const uploading = ref(false)
const uploadResult = ref(null)
const currentJobId = ref(null)

const pipelineStages = [
  '语义分块',
  '指代消解',
  '实体链接',
  '论断抽取',
  '谓词治理',
  '图谱存储',
  '主题构建',
  '质量度量'
]

const pipelineStageKeywords = [
  ['分块', 'chunk', '解析'],
  ['指代', 'coref', '消解'],
  ['实体', 'entity', '链接'],
  ['论断', 'claim', '抽取'],
  ['谓词', 'predicate', '治理'],
  ['存储', 'graph', '写入', '落库'],
  ['主题', 'theme', '社区'],
  ['度量', 'metric', '质量']
]

const currentTask = computed(() => {
  if (!currentJobId.value) return null
  return processingStore.tasks.get(currentJobId.value)
})

const processing = computed(() => currentTask.value?.status === 'processing')
const processCompleted = computed(() => currentTask.value?.status === 'completed')
const processFailed = computed(() => currentTask.value?.status === 'failed')
const progress = computed(() => currentTask.value?.progress || 0)
const progressMessage = computed(() => currentTask.value?.message || '')
const processStats = computed(() => currentTask.value?.stats)

const currentStageIndex = computed(() => {
  const msg = (progressMessage.value || '').toLowerCase()
  for (let i = 0; i < pipelineStageKeywords.length; i++) {
    for (const keyword of pipelineStageKeywords[i]) {
      if (msg.includes(keyword)) return i
    }
  }
  if (progress.value >= 90) return pipelineStages.length - 1
  if (progress.value >= 10) return Math.min(Math.floor(progress.value / 12.5), pipelineStages.length - 1)
  return 0
})

const pipelineStageLabel = computed(() => {
  if (processCompleted.value) return '处理完成'
  if (processFailed.value) return '处理失败'
  const msg = progressMessage.value
  if (msg) return msg
  const idx = currentStageIndex.value
  return `阶段 ${idx + 1}/${pipelineStages.length}: ${pipelineStages[idx]}`
})

watch(currentTask, (task) => {
  if (task && task.status === 'cancelled') {
    uploading.value = false
    resetState()
  }
}, { immediate: false })

const formatFileSize = (bytes) => {
  if (bytes === 0) return '0 Bytes'
  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i]
}

const getFileType = (filename) => {
  const ext = filename.split('.').pop().toUpperCase()
  return ext
}

const ALLOWED_EXTENSIONS = ['.pdf', '.md', '.markdown', '.txt', '.doc', '.docx']
const ALLOWED_MIME_TYPES = [
  'application/pdf',
  'text/markdown',
  'text/plain',
  'application/msword',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
]

const validateFileType = (file) => {
  const fileName = file.name.toLowerCase()
  const fileExt = '.' + fileName.split('.').pop()
  
  if (!ALLOWED_EXTENSIONS.includes(fileExt)) {
    return false
  }
  
  if (file.type && !ALLOWED_MIME_TYPES.includes(file.type)) {
    if (!(fileExt === '.md' || fileExt === '.markdown')) {
      return false
    }
  }
  
  return true
}

const handleFileChange = ({ file }) => {
  if (file) {
    if (!validateFileType(file.file)) {
      message.error(t('upload.invalid_file_type'))
      return
    }
    
    selectedFile.value = file.file
    resetState()
    message.success(t('upload.file_selected', { name: file.file.name }))
  }
}

const removeFile = () => {
  selectedFile.value = null
  resetState()
}

const resetState = () => {
  uploadResult.value = null
  currentJobId.value = null
}

const handleUpload = async () => {
  if (!selectedFile.value) {
    message.warning(t('upload.choose_file'))
    return
  }

  uploading.value = true
  resetState()
  
  try {
    const result = await uploadFile(selectedFile.value)
    uploadResult.value = result
    
    if (result.status === 'duplicate') {
      message.warning(result.message || '文档已存在')
      uploading.value = false
      return
    }
    
    if (result.jobId) {
      message.success('文件上传成功，GraphRAG Pipeline 开始处理...')
      uploading.value = false
      currentJobId.value = result.jobId
      
      processingStore.addTask({
        jobId: result.jobId,
        documentId: result.documentId,
        filename: result.filename,
        status: 'processing',
        progress: 0,
        message: '开始处理...'
      })
    } else {
      message.success(t('upload.upload_success'))
      uploading.value = false
    }
  } catch (error) {
    message.error(t('upload.error') + ': ' + error.message)
    uploading.value = false
  }
}

const isValidUrl = (url) => {
  try {
    const urlObj = new URL(url)
    return urlObj.protocol === 'http:' || urlObj.protocol === 'https:'
  } catch {
    return false
  }
}

const handleTextUpload = async () => {
  if (!textContent.value || textContent.value.trim().length < 10) {
    message.error('文本内容至少需要10个字符')
    return
  }

  uploading.value = true
  resetState()
  
  try {
    const result = await uploadText(
      textContent.value,
      textTitle.value || undefined,
      true
    )
    
    uploadResult.value = result
    
    if (result.status === 'duplicate') {
      message.warning(result.message || '文档已存在')
      uploading.value = false
      return
    }
    
    if (result.jobId) {
      message.success('文本已提交，GraphRAG Pipeline 开始处理...')
      uploading.value = false
      currentJobId.value = result.jobId
      
      processingStore.addTask({
        jobId: result.jobId,
        documentId: result.documentId,
        filename: result.filename,
        status: 'processing',
        progress: 0,
        message: '开始处理...'
      })
    } else {
      message.success('文本已保存')
      uploading.value = false
    }
    
    textContent.value = ''
    textTitle.value = ''
  } catch (error) {
    console.error('Text upload failed:', error)
    message.error(error.message || '文本提交失败')
    uploading.value = false
  }
}

const handleUrlUpload = async () => {
  if (!urlInput.value || !isValidUrl(urlInput.value)) {
    message.error('请输入有效的网页链接')
    return
  }

  uploading.value = true
  resetState()
  
  try {
    const result = await uploadUrl(
      urlInput.value,
      urlTitle.value || undefined,
      true
    )
    
    uploadResult.value = result
    
    if (result.status === 'duplicate') {
      message.warning(result.message || '文档已存在')
      uploading.value = false
      return
    }
    
    if (result.jobId) {
      message.success('网页内容已抓取，GraphRAG Pipeline 开始处理...')
      uploading.value = false
      currentJobId.value = result.jobId
      
      processingStore.addTask({
        jobId: result.jobId,
        documentId: result.documentId,
        filename: result.filename,
        status: 'processing',
        progress: 0,
        message: '开始处理...'
      })
    } else {
      message.success('网页内容已保存')
      uploading.value = false
    }
    
    urlInput.value = ''
    urlTitle.value = ''
  } catch (error) {
    console.error('URL upload failed:', error)
    message.error(error.message || '网页抓取失败')
    uploading.value = false
  }
}

const resetUpload = () => {
  selectedFile.value = null
  textContent.value = ''
  textTitle.value = ''
  urlInput.value = ''
  urlTitle.value = ''
  resetState()
  activeTab.value = 'file'
}
</script>

<style lang="scss" scoped>
.upload-page {
  padding: 32px 48px;
  background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
  min-height: calc(100vh - 70px);
  position: relative;

  &::before {
    content: '';
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: 
      radial-gradient(circle at 20% 20%, rgba(194, 164, 116, 0.08) 0%, transparent 50%),
      radial-gradient(circle at 80% 80%, rgba(155, 135, 245, 0.08) 0%, transparent 50%),
      radial-gradient(circle at 50% 50%, rgba(245, 158, 11, 0.06) 0%, transparent 60%);
    pointer-events: none;
    z-index: 0;
  }

  > * {
    position: relative;
    z-index: 1;
  }

  .page-header {
    margin-bottom: 32px;
    padding: 32px;
    background: linear-gradient(135deg, rgba(255, 255, 255, 0.95) 0%, rgba(255, 255, 255, 0.85) 100%);
    border-radius: 20px;
    backdrop-filter: blur(20px);
    box-shadow: 
      0 8px 32px rgba(0, 0, 0, 0.06),
      0 2px 8px rgba(0, 0, 0, 0.04),
      inset 0 1px 0 rgba(255, 255, 255, 0.8);
    border: 1px solid rgba(194, 164, 116, 0.2);
    position: relative;
    overflow: hidden;

    &::before {
      content: '';
      position: absolute;
      top: 0;
      left: 0;
      right: 0;
      height: 3px;
      background: linear-gradient(90deg, 
        rgba(194, 164, 116, 0.5), 
        rgba(155, 135, 245, 0.5), 
        rgba(245, 158, 11, 0.5));
    }

    .page-title {
      font-size: 32px;
      font-weight: 700;
      background: linear-gradient(135deg, #c2a474 0%, #9b87f5 50%, #f59e0b 100%);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      background-clip: text;
      margin: 0 0 8px 0;
      letter-spacing: -0.5px;
    }

    .page-subtitle {
      font-size: 14px;
      color: #64748b;
      margin: 0;
      font-weight: 500;
    }
  }

  .section-header {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 20px;
    padding-bottom: 16px;
    border-bottom: 2px solid rgba(194, 164, 116, 0.1);

    .n-icon {
      color: #c2a474;
    }

    h3 {
      font-size: 18px;
      font-weight: 600;
      color: #1e293b;
      margin: 0;
      letter-spacing: -0.3px;
    }
  }

  .upload-card {
    background: linear-gradient(135deg, rgba(255, 255, 255, 0.9) 0%, rgba(255, 255, 255, 0.8) 100%);
    border-radius: 20px;
    backdrop-filter: blur(10px);
    box-shadow: 
      0 8px 32px rgba(0, 0, 0, 0.06),
      0 2px 12px rgba(0, 0, 0, 0.04);
    border: 1px solid rgba(194, 164, 116, 0.2);
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);

    &:hover {
      box-shadow: 
        0 12px 40px rgba(0, 0, 0, 0.08),
        0 4px 16px rgba(0, 0, 0, 0.06);
      transform: translateY(-2px);
    }

    .tab-content {
      padding: 20px 0;
    }
  }

  .enhanced-dragger {
    :deep(.n-upload-dragger) {
      padding: 64px 48px;
      border: 2px dashed rgba(194, 164, 116, 0.3);
      border-radius: 16px;
      background: linear-gradient(135deg, rgba(255, 255, 255, 0.5) 0%, rgba(248, 250, 252, 0.5) 100%);
      backdrop-filter: blur(10px);
      transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
      position: relative;
      overflow: hidden;

      &::before {
        content: '';
        position: absolute;
        inset: 0;
        background: 
          radial-gradient(circle at 30% 40%, rgba(194, 164, 116, 0.05) 0%, transparent 60%),
          radial-gradient(circle at 70% 60%, rgba(155, 135, 245, 0.05) 0%, transparent 60%);
        pointer-events: none;
      }

      &:hover {
        border-color: rgba(194, 164, 116, 0.5);
        background: linear-gradient(135deg, rgba(255, 255, 255, 0.8) 0%, rgba(248, 250, 252, 0.8) 100%);
        transform: translateY(-4px);
        box-shadow: 
          0 12px 32px rgba(194, 164, 116, 0.15),
          0 4px 12px rgba(0, 0, 0, 0.06);
      }
    }

    .dragger-content {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 20px;
    }

    .dragger-icon-wrapper {
      position: relative;
      display: flex;
      align-items: center;
      justify-content: center;

      .dragger-icon {
        color: #c2a474;
        position: relative;
        z-index: 2;
        animation: float 3s ease-in-out infinite;
      }
    }

    .dragger-text {
      text-align: center;
      position: relative;
      z-index: 1;

      h3 {
        font-size: 20px;
        font-weight: 600;
        color: #1e293b;
        margin: 0 0 8px 0;
        letter-spacing: -0.3px;
      }

      p {
        font-size: 14px;
        color: #64748b;
        margin: 0 0 16px 0;
        font-weight: 500;
      }

      .dragger-formats {
        display: flex;
        gap: 8px;
        justify-content: center;
        
        :deep(.n-tag) {
          font-weight: 600;
          letter-spacing: 0.3px;
          padding: 4px 12px;
          box-shadow: 0 2px 6px rgba(0, 0, 0, 0.08);
        }
      }
    }
  }

  .file-selected-card {
    margin-top: 24px;
    padding: 24px;
    border-radius: 16px;
    background: linear-gradient(135deg, rgba(194, 164, 116, 0.08) 0%, rgba(155, 135, 245, 0.08) 100%);
    border: 1px solid rgba(194, 164, 116, 0.2);
    backdrop-filter: blur(10px);
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);

    .file-preview {
      display: flex;
      align-items: center;
      gap: 16px;
      padding: 20px;
      background: linear-gradient(135deg, rgba(255, 255, 255, 0.95) 0%, rgba(255, 255, 255, 0.9) 100%);
      backdrop-filter: blur(10px);
      border-radius: 12px;
      margin-bottom: 16px;
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
      border: 1px solid rgba(194, 164, 116, 0.15);
      transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);

      &:hover {
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
        transform: translateY(-2px);
      }

      .file-icon-wrapper {
        width: 56px;
        height: 56px;
        background: linear-gradient(135deg, #c2a474 0%, #9b87f5 100%);
        border-radius: 12px;
        display: flex;
        align-items: center;
        justify-content: center;
        color: white;
        flex-shrink: 0;
        box-shadow: 0 4px 12px rgba(194, 164, 116, 0.3);
      }

      .file-details {
        flex: 1;

        .file-name {
          font-size: 16px;
          font-weight: 600;
          color: #1e293b;
          margin-bottom: 6px;
          word-break: break-all;
          letter-spacing: -0.2px;
        }

        .file-meta {
          display: flex;
          align-items: center;
          gap: 8px;
          font-size: 13px;
          color: #64748b;

          .file-size {
            font-weight: 500;
          }

          .file-type {
            font-weight: 600;
            color: #c2a474;
            letter-spacing: 0.3px;
          }
        }
      }
    }

    .upload-button {
      margin-top: 12px;
      height: 48px;
      font-size: 16px;
      font-weight: 600;
      letter-spacing: 0.3px;
      background: linear-gradient(135deg, #c2a474 0%, #9b87f5 100%);
      border: none;
      border-radius: 12px;
      box-shadow: 0 4px 12px rgba(194, 164, 116, 0.3);

      &:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 16px rgba(194, 164, 116, 0.4);
      }
    }
  }

  .progress-card {
    background: linear-gradient(135deg, rgba(255, 255, 255, 0.9) 0%, rgba(255, 255, 255, 0.8) 100%);
    border-radius: 20px;
    backdrop-filter: blur(10px);
    box-shadow: 
      0 8px 32px rgba(0, 0, 0, 0.06),
      0 2px 12px rgba(0, 0, 0, 0.04);
    border: 1px solid rgba(194, 164, 116, 0.2);
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);

    &:hover {
      box-shadow: 
        0 12px 40px rgba(0, 0, 0, 0.08),
        0 4px 16px rgba(0, 0, 0, 0.06);
    }

    .result-descriptions {
      :deep(.n-descriptions) {
        border-radius: 12px;
        overflow: hidden;
      }
    }

    .progress-section {
      padding: 20px;
      background: linear-gradient(135deg, rgba(194, 164, 116, 0.05) 0%, rgba(155, 135, 245, 0.05) 100%);
      border-radius: 12px;
      margin-bottom: 16px;

      .progress-info {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 12px;

        .progress-label {
          font-size: 14px;
          font-weight: 600;
          color: #1e293b;
        }

        .progress-percent {
          font-size: 16px;
          font-weight: 700;
          color: #c2a474;
          letter-spacing: 0.5px;
        }
      }

      :deep(.n-progress) {
        .n-progress-graph {
          .n-progress-graph-line-fill {
            background: linear-gradient(90deg, #c2a474 0%, #9b87f5 50%, #f59e0b 100%);
          }
        }
      }

      .pipeline-stages {
        display: flex;
        gap: 4px;
        margin-top: 16px;
        overflow-x: auto;
        padding-bottom: 4px;

        .stage-item {
          display: flex;
          align-items: center;
          gap: 6px;
          padding: 4px 10px;
          border-radius: 20px;
          font-size: 11px;
          font-weight: 500;
          white-space: nowrap;
          transition: all 0.3s ease;

          .stage-dot {
            width: 18px;
            height: 18px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 10px;
            font-weight: 700;
            flex-shrink: 0;
          }

          &.pending {
            color: #94a3b8;
            background: rgba(148, 163, 184, 0.08);

            .stage-dot {
              background: #e2e8f0;
              color: #94a3b8;
            }
          }

          &.active {
            color: #c2a474;
            background: rgba(194, 164, 116, 0.12);
            font-weight: 700;

            .stage-dot {
              background: linear-gradient(135deg, #c2a474, #9b87f5);
              color: white;
              animation: pulse 1.5s ease-in-out infinite;
            }
          }

          &.completed {
            color: #18a058;
            background: rgba(24, 160, 88, 0.08);

            .stage-dot {
              background: #18a058;
              color: white;
            }
          }
        }
      }
    }

    .stats-grid {
      display: grid;
      grid-template-columns: repeat(5, 1fr);
      gap: 12px;
      margin-top: 20px;

      .stat-item {
        padding: 14px 8px;
        background: linear-gradient(135deg, rgba(194, 164, 116, 0.08) 0%, rgba(155, 135, 245, 0.08) 100%);
        border-radius: 12px;
        text-align: center;
        border: 1px solid rgba(194, 164, 116, 0.15);
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);

        &:hover {
          transform: translateY(-2px);
          box-shadow: 0 4px 12px rgba(194, 164, 116, 0.2);
        }

        .stat-value {
          font-size: 24px;
          font-weight: 700;
          background: linear-gradient(135deg, #c2a474 0%, #9b87f5 100%);
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
          background-clip: text;
          margin-bottom: 4px;
        }

        .stat-label {
          font-size: 12px;
          color: #64748b;
          font-weight: 500;
        }
      }
    }

    .quality-section {
      .quality-grid {
        display: grid;
        grid-template-columns: repeat(2, 1fr);
        gap: 12px;

        .quality-item {
          padding: 12px;
          background: linear-gradient(135deg, rgba(194, 164, 116, 0.08) 0%, rgba(155, 135, 245, 0.08) 100%);
          border-radius: 10px;
          border: 1px solid rgba(194, 164, 116, 0.15);
          text-align: center;

          .quality-label {
            font-size: 12px;
            color: #64748b;
            font-weight: 500;
            margin-bottom: 4px;
          }

          .quality-value {
            font-size: 18px;
            font-weight: 700;
            background: linear-gradient(135deg, #c2a474 0%, #9b87f5 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
          }
        }
      }
    }

    .execution-time {
      margin-top: 12px;
      text-align: center;
    }

    .action-button {
      height: 48px;
      font-size: 16px;
      font-weight: 600;
      letter-spacing: 0.3px;
      border-radius: 12px;
      box-shadow: 0 4px 12px rgba(194, 164, 116, 0.3);

      &:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 16px rgba(194, 164, 116, 0.4);
      }
    }
  }
}

:deep(.n-card) {
  border-radius: 20px;
}

:deep(.n-button) {
  border-radius: 12px;
  font-weight: 600;
  letter-spacing: 0.3px;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);

  &:not(:disabled):hover {
    transform: translateY(-2px);
  }
}

@keyframes float {
  0%, 100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-8px);
  }
}

@keyframes pulse {
  0%, 100% {
    box-shadow: 0 0 0 0 rgba(194, 164, 116, 0.4);
  }
  50% {
    box-shadow: 0 0 0 6px rgba(194, 164, 116, 0);
  }
}

.slide-fade-enter-active {
  transition: all 0.5s cubic-bezier(0.4, 0, 0.2, 1);
}

.slide-fade-leave-active {
  transition: all 0.3s cubic-bezier(0.4, 0, 1, 1);
}

.slide-fade-enter-from {
  opacity: 0;
  transform: translateY(24px);
}

.slide-fade-leave-to {
  opacity: 0;
  transform: translateY(-24px);
}
</style>

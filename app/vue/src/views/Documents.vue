<template>
  <div class="documents-page">
    <!-- Page Header -->
    <div class="page-header">
      <div class="header-content">
        <h1 class="page-title">{{ t('documents.title') }}</h1>
        <p class="page-subtitle">{{ t('documents.subtitle') }}</p>
      </div>
    </div>

    <!-- Content -->
    <n-space vertical :size="24">
      <!-- Stats Cards -->
      <div class="stats-grid">
        <div class="stat-card">
          <div class="stat-icon" style="background: linear-gradient(135deg, #3b82f6, #1e40af);">
            <n-icon size="32"><document-text-outline /></n-icon>
          </div>
          <div class="stat-content">
            <div class="stat-label">{{ t('documents.total_documents') }}</div>
            <div class="stat-value">{{ totalDocuments }}</div>
          </div>
        </div>

        <div class="stat-card">
          <div class="stat-icon" style="background: linear-gradient(135deg, #10b981, #059669);">
            <n-icon size="32"><checkmark-circle-outline /></n-icon>
          </div>
          <div class="stat-content">
            <div class="stat-label">{{ t('documents.processed') }}</div>
            <div class="stat-value">{{ completedDocuments }}</div>
          </div>
        </div>

        <div class="stat-card">
          <div class="stat-icon" style="background: linear-gradient(135deg, #f59e0b, #d97706);">
            <n-icon size="32"><hourglass-outline /></n-icon>
          </div>
          <div class="stat-content">
            <div class="stat-label">{{ t('documents.to_process') }}</div>
            <div class="stat-value">{{ pendingDocuments }}</div>
          </div>
        </div>
      </div>

      <!-- Documents Table -->
      <n-card :bordered="false" class="documents-card">
        <template #header>
          <div class="card-header">
            <div class="header-left">
              <h2>{{ t('documents.all_documents') }}</h2>
              <n-space>
                <n-button
                  v-if="selectedDocs.length > 0"
                  type="error"
                  size="small"
                  @click="handleBatchDelete"
                  style="align-self: center;"
                >
                  <template #icon>
                    <n-icon size="14"><trash-outline /></n-icon>
                  </template>
                  {{ t('documents.batch_delete', { count: selectedDocs.length }) }}
                </n-button>
                <!-- 状态筛选 -->
                <n-select
                  v-model:value="filterStatus"
                  :options="[
                    { label: t('documents.all_status'), value: 'all' },
                    { label: t('documents.completed'), value: 'completed' },
                    { label: t('documents.pending'), value: 'pending' },
                    { label: t('documents.processing'), value: 'processing' }
                  ]"
                  style="width: 120px"
                  @update:value="loadDocuments"
                />

                <!-- 类型筛选 -->
                <n-select
                  v-model:value="filterType"
                  :options="[
                    { label: t('documents.all_types'), value: 'all' },
                    { label: t('documents.pdf'), value: 'pdf' },
                    { label: t('documents.markdown'), value: 'md' },
                    { label: t('documents.txt'), value: 'txt' },
                    { label: t('documents.word'), value: 'word' },
                    { label: t('documents.json'), value: 'json'},
                    { label: t('documents.csv'), value: 'csv'},
                    { label: t('documents.excel'), value: 'xlsx'}
                  ]"
                  style="width: 120px"
                  @update:value="loadDocuments"
                />
              </n-space>
            </div>

            <div class="header-right">
              <!-- 搜索框 -->
              <n-input
                v-model:value="searchKeyword"
                :placeholder="t('documents.search_filename')"
                clearable
                style="width: 200px"
                @keyup.enter="handleSearch"
                @clear="handleSearch"
              >
                <template #prefix>
                  <n-icon><search-outline /></n-icon>
                </template>
              </n-input>

              <!-- 排序 -->
              <n-select
                v-model:value="sortBy"
                :options="[
                  { label: t('documents.latest_upload'), value: 'created_at' },
                  { label: t('documents.filename'), value: 'filename' },
                  { label: t('documents.file_size'), value: 'size' }
                ]"
                style="width: 120px"
                @update:value="loadDocuments"
              />

              <!-- 刷新按钮 -->
              <n-button type="primary" @click="loadDocuments" :loading="loading">
                <template #icon>
                  <n-icon><refresh-outline /></n-icon>
                </template>
                {{ t('documents.refresh') }}
              </n-button>
            </div>
          </div>
        </template>

        <n-spin :show="loading">
          <n-data-table
            :columns="columns"
            :data="documents"
            :loading="loading"
            :scroll-x="1200"
            striped
            :row-key="(row) => row.id"
            v-model:checked-row-keys="selectedDocs"
          />
          
          <!-- 独立分页组件 -->
          <div style="display: flex; justify-content: center; margin-top: 20px;">
            <n-pagination
              v-model:page="pagination.page"
              v-model:page-size="pagination.pageSize"
              :page-count="pagination.pageCount"
              :item-count="pagination.itemCount"
              :show-size-picker="true"
              :page-sizes="[10, 20, 50, 100]"
              @update:page="handlePageChange"
              @update:page-size="handlePageSizeChange"
            />
          </div>
        </n-spin>
      </n-card>
    </n-space>

    <!-- Document Detail Modal -->
    <n-modal
      v-model:show="showDetailModal"
      :title="`${t('documents.document_detail')} - ${selectedDocument?.filename || ''}`"
      positive-text=""
      :negative-text="t('common.close')"
      :mask-closable="false"
      preset="dialog"
      style="width: 80%; max-width: 1000px"
    >
      <div v-if="selectedDocument && documentDetail" class="document-detail">
        <!-- Basic Info -->
        <n-divider>{{ t('documents.basic_info') }}</n-divider>
        <n-grid :cols="2" :x-gap="24" :y-gap="12">
          <n-gi>
            <div class="info-item">
              <span class="label">{{ t('documents.filename') }}:</span>
              <span class="value">{{ documentDetail.filename }}</span>
            </div>
          </n-gi>
          <n-gi>
            <div class="info-item">
              <span class="label">{{ t('documents.file_type') }}:</span>
              <n-tag :type="getKindColor(documentDetail.kind)">
                {{ documentDetail.kind.toUpperCase() }}
              </n-tag>
            </div>
          </n-gi>
          <n-gi>
            <div class="info-item">
              <span class="label">{{ t('documents.size') }}:</span>
              <span class="value">{{ formatFileSize(documentDetail.size) }}</span>
            </div>
          </n-gi>
          <n-gi>
            <div class="info-item">
              <span class="label">{{ t('documents.processing_status') }}:</span>
              <n-tag
                :type="documentDetail.processing_status === 'completed' ? 'success' : 'warning'"
              >
                {{ documentDetail.processing_status === 'completed' ? t('documents.completed') : t('documents.pending') }}
              </n-tag>
            </div>
          </n-gi>
          <n-gi>
            <div class="info-item">
              <span class="label">{{ t('documents.upload_time') }}:</span>
              <span class="value">{{ formatTime(documentDetail.created_at) }}</span>
            </div>
          </n-gi>
          <n-gi>
            <div class="info-item">
              <span class="label">{{ t('documents.update_time') }}:</span>
              <span class="value">{{ formatTime(documentDetail.updated_at) }}</span>
            </div>
          </n-gi>
          <n-gi>
            <div class="info-item">
              <span class="label">{{ t('documents.mime_type') }}:</span>
              <span class="value">{{ documentDetail.mime }}</span>
            </div>
          </n-gi>
          <n-gi>
            <div class="info-item">
              <span class="label">{{ t('documents.checksum') }}:</span>
              <span class="value" style="font-family: monospace; font-size: 12px;">
                {{ documentDetail.checksum.substring(0, 16) }}...
              </span>
            </div>
          </n-gi>
        </n-grid>

        <!-- Statistics -->
        <n-divider>{{ t('documents.statistics') }}</n-divider>
        <n-grid :cols="4" :x-gap="16" :y-gap="12">
          <n-gi>
            <div class="stat-box">
              <div class="stat-value">{{ documentDetail.statistics.chunk_count }}</div>
              <div class="stat-label">{{ t('documents.chunk_count') }}</div>
            </div>
          </n-gi>
          <n-gi>
            <div class="stat-box">
              <div class="stat-value">{{ documentDetail.statistics.concept_count }}</div>
              <div class="stat-label">{{ t('documents.concept_count') }}</div>
            </div>
          </n-gi>
          <n-gi>
            <div class="stat-box">
              <div class="stat-value">{{ documentDetail.statistics.claim_count }}</div>
              <div class="stat-label">{{ t('documents.claim_count') }}</div>
            </div>
          </n-gi>
          <n-gi>
            <div class="stat-box">
              <div class="stat-value">{{ documentDetail.statistics.relation_count }}</div>
              <div class="stat-label">{{ t('documents.relation_count') }}</div>
            </div>
          </n-gi>
        </n-grid>

        <!-- Themes -->
        <n-divider v-if="documentDetail.themes.length > 0">{{ t('documents.related_themes') }}</n-divider>
        <div v-if="documentDetail.themes.length > 0">
          <n-space vertical :size="12">
            <div v-for="theme in documentDetail.themes" :key="theme.id" class="theme-item">
              <n-card :bordered="false" style="background: #f5f7fa;">
                <div class="theme-header">
                  <n-tag :type="theme.level === 1 ? 'success' : 'info'">
                    Level {{ theme.level }}
                  </n-tag>
                  <h4 style="margin: 0 16px; flex: 1;">{{ theme.label }}</h4>
                  <span style="color: #999; font-size: 14px;">{{ theme.member_count }} {{ t('documents.members') }}</span>
                </div>
                <p class="theme-summary">{{ theme.summary }}</p>
              </n-card>
            </div>
          </n-space>
        </div>
        <div v-else class="empty-message">{{ t('documents.no_themes') }}</div>

        <!-- Metadata -->
        <n-divider v-if="Object.keys(documentDetail.meta).length > 0">{{ t('documents.metadata') }}</n-divider>
        <div v-if="Object.keys(documentDetail.meta).length > 0">
          <n-code
            :code="JSON.stringify(documentDetail.meta, null, 2)"
            language="json"
            word-wrap
          />
        </div>

        <n-divider>{{ t('documents.document_preview') }}</n-divider>
        <div v-if="canPreview" class="preview-container">
          <iframe :src="previewUrl" class="preview-frame" :title="t('documents.document_preview')" />
        </div>
        <div v-else class="empty-message">{{ t('documents.no_preview') }}</div>
      </div>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, h } from 'vue'
import { useRouter } from 'vue-router'
import { useMessage } from 'naive-ui'
import { useI18n } from 'vue-i18n'
import {
  NButton,
  NTag,
  NIcon
} from 'naive-ui'
import {
  RefreshOutline,
  DocumentTextOutline,
  CheckmarkCircleOutline,
  HourglassOutline,
  SearchOutline,
  TrashOutline
} from '@vicons/ionicons5'
import { listDocuments, getDocumentDetail, getDocumentFileUrl, deleteDocument, type DocumentListResponse, type DocumentDetail } from '@/api/services'

const router = useRouter()
const message = useMessage()
const { t } = useI18n()

// 响应式变量
const filterStatus = ref('all')
const filterType = ref('all')
const searchKeyword = ref('')
const selectedDocs = ref<string[]>([]) // 选中的文档ID

// State
const loading = ref(false)
const documents = ref<DocumentListResponse['documents']>([])
const totalCount = ref(0)
const completedCount = ref(0)
const pendingCount = ref(0)

const pagination = ref({
  page: 1,
  pageSize: 20,
  pageCount: 1,
  itemCount: 0,
  showSizePicker: true,
  pageSizes: [10, 20, 50, 100],
  prefix: (info: any) => `共 ${info.itemCount} 条`
})

const handlePageChange = () => {
  loadDocuments()
}

const handlePageSizeChange = () => {
  pagination.value.page = 1
  loadDocuments()
}

const sortBy = ref<'created_at' | 'filename' | 'size'>('created_at')
const showDetailModal = ref(false)
const selectedDocument = ref<DocumentListResponse['documents'][0] | null>(null)
const documentDetail = ref<DocumentDetail | null>(null)
const loadingDetail = ref(false)
const previewUrl = computed(() => selectedDocument.value ? getDocumentFileUrl(selectedDocument.value.id) : '')
const canPreview = computed(() => {
  if (!documentDetail.value) return false
  const mime = (documentDetail.value.mime || '').toLowerCase()
  const kind = (documentDetail.value.kind || '').toLowerCase()
  return mime.includes('pdf') || kind === 'pdf'
})

// Computed
const totalDocuments = computed(() => totalCount.value)
const completedDocuments = computed(() => completedCount.value)
const pendingDocuments = computed(() => pendingCount.value)

// Methods
const loadDocuments = async () => {
  loading.value = true
  try {
    const skip = (pagination.value.page - 1) * pagination.value.pageSize
    
    // 将筛选条件传递给后端
    const status = filterStatus.value === 'all' ? '' : filterStatus.value
    const kind = filterType.value === 'all' ? '' : filterType.value
    const keyword = searchKeyword.value.trim()
    
    const result = await listDocuments(skip, pagination.value.pageSize, sortBy.value, status, kind, keyword)

    // 更新文档列表，过滤无效数据
    documents.value = (result.documents || []).filter(doc => doc && doc.id)
    
    // 更新总数和分页
    totalCount.value = result.total
    pagination.value.itemCount = result.total
    pagination.value.pageCount = Math.ceil(result.total / pagination.value.pageSize)
    
    // 更新统计数据（来自后端）
    if (result.stats) {
      completedCount.value = result.stats.completed
      pendingCount.value = result.stats.pending
    } else {
      // 降级处理：从当前页数据计算（仅作为备份）
      completedCount.value = result.documents.filter(d => d.processing_status === 'completed').length
      pendingCount.value = result.documents.filter(d => 
        d.processing_status === 'uploaded' || d.processing_status === 'pending'
      ).length
    }

    // 重置选中状态
    selectedDocs.value = []

  } catch (error: any) {
    message.error(`加载文档列表失败: ${error.message}`)
  } finally {
    loading.value = false
  }
}

const formatFileSize = (bytes: number) => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i]
}

const formatTime = (time: string | null) => {
  if (!time) return '未知'
  try {
    const date = new Date(time)
    return date.toLocaleString('zh-CN')
  } catch {
    return time
  }
}

const getKindColor = (kind: string) => {
  const colors: Record<string, 'success' | 'warning' | 'info' | 'error'> = {
    pdf: 'error',
    md: 'info',
    txt: 'warning',
    word: 'success'
  }
  return colors[kind] || 'default'
}

const handleViewDocument = async (doc: DocumentListResponse['documents'][0]) => {
  selectedDocument.value = doc
  showDetailModal.value = true
  loadingDetail.value = true
  try {
    documentDetail.value = await getDocumentDetail(doc.id)
  } catch (error: any) {
    message.error(`加载文档详情失败: ${error.message}`)
  } finally {
    loadingDetail.value = false
  }
}

const handleViewGraph = (doc: DocumentListResponse['documents'][0]) => {
  router.push(`/graph?doc_id=${doc.id}`)
}

const handleDeleteDocument = async (doc: DocumentListResponse['documents'][0]) => {
  const dialog = (window as any).$dialog
  if (!dialog) {
    message.error('对话框组件不可用')
    return
  }
  
  dialog.create({
    title: '确认删除',
    content: `确定要删除文档 "${doc.filename}" 吗？此操作不可恢复。`,
    positiveText: '删除',
    negativeText: '取消',
    type: 'error',
    onPositiveClick: async () => {
      try {
        const loadingMsg = message.loading('正在删除文档...', {
          duration: 0
        })

        await deleteDocument(doc.id)

        loadingMsg.destroy()
        message.success('文档删除成功')

        if (selectedDocument.value?.id === doc.id) {
          showDetailModal.value = false
          selectedDocument.value = null
          documentDetail.value = null
        }

        await loadDocuments()

      } catch (error: any) {
        message.error(`删除文档失败: ${error.message || '未知错误'}`)
      }
      return true
    },
    onNegativeClick: () => true
  })
}

const handleBatchDelete = async () => {
  const dialog = (window as any).$dialog
  if (!dialog) {
    message.error('对话框组件不可用')
    return
  }
  
  dialog.create({
    title: '确认批量删除',
    content: `确定要删除选中的 ${selectedDocs.value.length} 个文档吗？此操作不可恢复。`,
    positiveText: '删除',
    negativeText: '取消',
    type: 'error',
    onPositiveClick: async () => {
      try {
        const loadingMsg = message.loading(`正在删除 ${selectedDocs.value.length} 个文档...`, {
          duration: 0
        })

        for (const docId of selectedDocs.value) {
          try {
            await deleteDocument(docId)
          } catch (error) {
            console.error(`删除文档 ${docId} 失败:`, error)
          }
        }

        loadingMsg.destroy()
        message.success(`已删除 ${selectedDocs.value.length} 个文档`)

        await loadDocuments()

      } catch (error: any) {
        message.error(`批量删除失败: ${error.message}`)
      }
      return true
    }
  })
}

const handleSearch = () => {
  pagination.value.page = 1 // 重置到第一页
  loadDocuments()
}

// Table columns
const columns = computed(() => [
  {
    type: 'selection' as const,
    width: 40
  },
  {
    title: t('documents.filename'),
    key: 'filename',
    width: 250,
    ellipsis: { tooltip: true },
    render: (row: any) => row.filename
  },
  {
    title: t('documents.type'),
    key: 'kind',
    width: 80,
    render: (row: any) => h(NTag, { type: getKindColor(row.kind) }, () => row.kind.toUpperCase())
  },
  {
    title: t('documents.size'),
    key: 'size',
    width: 100,
    render: (row: any) => formatFileSize(row.size)
  },
  {
    title: t('documents.chunks'),
    key: 'chunk_count',
    width: 80,
    align: 'center' as const,
    render: (row: any) => h('span', { style: 'font-weight: bold; color: #3b82f6;' }, row.chunk_count)
  },
  {
    title: t('documents.concepts'),
    key: 'concept_count',
    width: 80,
    align: 'center' as const,
    render: (row: any) => h('span', { style: 'font-weight: bold; color: #10b981;' }, row.concept_count)
  },
  {
    title: t('documents.claims'),
    key: 'claim_count',
    width: 80,
    align: 'center' as const,
    render: (row: any) => h('span', { style: 'font-weight: bold; color: #f59e0b;' }, row.claim_count)
  },
  {
    title: t('documents.status'),
    key: 'processing_status',
    width: 100,
    render: (row: any) => {
      const type = row.processing_status === 'completed' ? 'success' : 'warning'
      const label = row.processing_status === 'completed' ? t('documents.completed') : t('documents.pending')
      return h(NTag, { type }, () => label)
    }
  },
  {
    title: t('documents.upload_time'),
    key: 'created_at',
    width: 180,
    render: (row: any) => formatTime(row.created_at)
  },
  {
    title: t('documents.actions'),
    key: 'actions',
    width: 200,
    fixed: 'right' as const,
    render: (row: any) => {
      return h('div', { style: 'display: flex; gap: 8px;' }, [
        h(
          NButton,
          {
            size: 'small',
            type: 'primary',
            text: true,
            onClick: () => handleViewDocument(row)
          },
          { default: () => t('documents.view') }
        ),
        h(
          NButton,
          {
            size: 'small',
            type: 'info',
            text: true,
            onClick: () => handleViewGraph(row)
          },
          { default: () => t('documents.graph') }
        ),
        h(
          NButton,
          {
            size: 'small',
            type: 'error',
            text: true,
            onClick: () => handleDeleteDocument(row)
          },
          { default: () => t('documents.delete') }
        )
      ])
    }
  }
])

// Mount
loadDocuments()
</script>

<style scoped>
.documents-page {
  padding: 24px;
  background: #f5f7fa;
  min-height: 100vh;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 32px;
}

.header-content {
  flex: 1;
}

.page-title {
  font-size: 28px;
  font-weight: 700;
  margin: 0 0 8px 0;
  background: linear-gradient(120deg, #3b82f6, #1e40af);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.page-subtitle {
  font-size: 14px;
  color: #999;
  margin: 0;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
  margin-bottom: 24px;
}

.stat-card {
  display: flex;
  gap: 16px;
  padding: 20px;
  background: white;
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.stat-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 60px;
  height: 60px;
  border-radius: 8px;
  color: white;
  flex-shrink: 0;
}

.stat-content {
  flex: 1;
}

.stat-label {
  font-size: 12px;
  color: #999;
  margin-bottom: 8px;
}

.stat-value {
  font-size: 24px;
  font-weight: 700;
  color: #1f2937;
}

.documents-card {
  background: white;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}

.card-header h2 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
}

.empty-state {
  padding: 60px 20px;
  text-align: center;
}

.document-detail {
  padding: 20px 0;
}

.info-item {
  display: flex;
  gap: 12px;
}

.info-item .label {
  font-weight: 600;
  color: #666;
  min-width: 80px;
}

.info-item .value {
  color: #333;
}

.stat-box {
  padding: 20px;
  background: #f5f7fa;
  border-radius: 8px;
  text-align: center;
}

.stat-box .stat-value {
  font-size: 28px;
  font-weight: 700;
  color: #3b82f6;
  margin-bottom: 8px;
}

.stat-box .stat-label {
  font-size: 12px;
  color: #999;
}

.theme-item {
  margin-bottom: 12px;
}

.theme-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
}

.theme-summary {
  margin: 8px 0 0 0;
  color: #666;
  line-height: 1.5;
}

.empty-message {
  padding: 20px;
  text-align: center;
  color: #999;
}

.preview-container {
  margin-top: 12px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  overflow: hidden;
  background: #f8fafc;
}

.preview-frame {
  width: 100%;
  height: 620px;
  border: none;
  background: white;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 16px;
  width: 100%;
}

.header-left,
.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

@media (max-width: 768px) {
  .card-header {
    flex-direction: column;
    align-items: stretch;
  }

  .header-left,
  .header-right {
    width: 100%;
    justify-content: space-between;
  }
}

:deep(.n-data-table-tr--checked) {
  background-color: rgba(59, 130, 246, 0.05) !important;
}

</style>
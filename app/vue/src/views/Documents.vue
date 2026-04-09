<template>
  <div class="documents-page">
    <!-- Page Header -->
    <div class="page-header">
      <div class="header-content">
        <h1 class="page-title">文档管理</h1>
        <p class="page-subtitle">查看和管理已上传的文档</p>
      </div>
      <div class="header-actions">
        <n-button type="primary" @click="loadDocuments" :loading="loading">
          <template #icon>
            <n-icon><refresh-outline /></n-icon>
          </template>
          刷新列表
        </n-button>
        <n-button type="success" @click="$router.push('/upload')">
          <template #icon>
            <n-icon><cloud-upload-outline /></n-icon>
          </template>
          上传新文档
        </n-button>
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
            <div class="stat-label">总文档数</div>
            <div class="stat-value">{{ totalDocuments }}</div>
          </div>
        </div>

        <div class="stat-card">
          <div class="stat-icon" style="background: linear-gradient(135deg, #10b981, #059669);">
            <n-icon size="32"><checkmark-circle-outline /></n-icon>
          </div>
          <div class="stat-content">
            <div class="stat-label">已处理</div>
            <div class="stat-value">{{ completedDocuments }}</div>
          </div>
        </div>

        <div class="stat-card">
          <div class="stat-icon" style="background: linear-gradient(135deg, #f59e0b, #d97706);">
            <n-icon size="32"><hourglass-outline /></n-icon>
          </div>
          <div class="stat-content">
            <div class="stat-label">待处理</div>
            <div class="stat-value">{{ pendingDocuments }}</div>
          </div>
        </div>
      </div>

      <!-- Documents Table -->
      <n-card :bordered="false" class="documents-card">
        <template #header>
          <div class="card-header">
            <div class="header-left">
              <h2>所有文档</h2>
              <n-space>
                <!-- 状态筛选 -->
                <n-select
                  v-model:value="filterStatus"
                  :options="[
                    { label: '全部状态', value: 'all' },
                    { label: '已完成', value: 'completed' },
                    { label: '待处理', value: 'pending' },
                    { label: '处理中', value: 'processing' }
                  ]"
                  style="width: 120px"
                  @update:value="loadDocuments"
                />

                <!-- 类型筛选 -->
                <n-select
                  v-model:value="filterType"
                  :options="[
                    { label: '全部类型', value: 'all' },
                    { label: 'PDF', value: 'pdf' },
                    { label: 'Markdown', value: 'md' },
                    { label: '文本', value: 'txt' },
                    { label: 'Word', value: 'word' },
                    { label: 'Json', value: 'json'},
                    { label: 'Csv', value: 'csv'},
                    { label: 'Excel', value: 'xlsx'}
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
                placeholder="搜索文件名..."
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
                  { label: '最新上传', value: 'created_at' },
                  { label: '文件名', value: 'filename' },
                  { label: '文件大小', value: 'size' }
                ]"
                style="width: 120px"
                @update:value="loadDocuments"
              />
            </div>
          </div>
        </template>

        <n-spin :show="loading">
          <div v-if="documents.length === 0" class="empty-state">
            <n-empty description="暂无文档">
              <template #extra>
                <n-button type="primary" @click="$router.push('/upload')">
                  上传第一个文档
                </n-button>
              </template>
            </n-empty>
          </div>

          <n-data-table
            v-else
            :columns="columns"
            :data="documents"
            :pagination="pagination"
            :loading="loading"
            :scroll-x="1200"
            striped
          />
        </n-spin>
      </n-card>
    </n-space>

    <!-- Document Detail Modal -->
    <n-modal
      v-model:show="showDetailModal"
      :title="`文档详情 - ${selectedDocument?.filename || ''}`"
      positive-text=""
      negative-text="关闭"
      :mask-closable="false"
      preset="dialog"
      style="width: 80%; max-width: 1000px"
    >
      <div v-if="selectedDocument && documentDetail" class="document-detail">
        <!-- Basic Info -->
        <n-divider>基本信息</n-divider>
        <n-grid :cols="2" :x-gap="24" :y-gap="12">
          <n-gi>
            <div class="info-item">
              <span class="label">文件名:</span>
              <span class="value">{{ documentDetail.filename }}</span>
            </div>
          </n-gi>
          <n-gi>
            <div class="info-item">
              <span class="label">文件类型:</span>
              <n-tag :type="getKindColor(documentDetail.kind)">
                {{ documentDetail.kind.toUpperCase() }}
              </n-tag>
            </div>
          </n-gi>
          <n-gi>
            <div class="info-item">
              <span class="label">文件大小:</span>
              <span class="value">{{ formatFileSize(documentDetail.size) }}</span>
            </div>
          </n-gi>
          <n-gi>
            <div class="info-item">
              <span class="label">处理状态:</span>
              <n-tag
                :type="documentDetail.processing_status === 'completed' ? 'success' : 'warning'"
              >
                {{ documentDetail.processing_status === 'completed' ? '已完成' : '待处理' }}
              </n-tag>
            </div>
          </n-gi>
          <n-gi>
            <div class="info-item">
              <span class="label">上传时间:</span>
              <span class="value">{{ formatTime(documentDetail.created_at) }}</span>
            </div>
          </n-gi>
          <n-gi>
            <div class="info-item">
              <span class="label">更新时间:</span>
              <span class="value">{{ formatTime(documentDetail.updated_at) }}</span>
            </div>
          </n-gi>
          <n-gi>
            <div class="info-item">
              <span class="label">MIME 类型:</span>
              <span class="value">{{ documentDetail.mime }}</span>
            </div>
          </n-gi>
          <n-gi>
            <div class="info-item">
              <span class="label">Checksum:</span>
              <span class="value" style="font-family: monospace; font-size: 12px;">
                {{ documentDetail.checksum.substring(0, 16) }}...
              </span>
            </div>
          </n-gi>
        </n-grid>

        <!-- Statistics -->
        <n-divider>处理统计</n-divider>
        <n-grid :cols="4" :x-gap="16" :y-gap="12">
          <n-gi>
            <div class="stat-box">
              <div class="stat-value">{{ documentDetail.statistics.chunk_count }}</div>
              <div class="stat-label">文本块</div>
            </div>
          </n-gi>
          <n-gi>
            <div class="stat-box">
              <div class="stat-value">{{ documentDetail.statistics.concept_count }}</div>
              <div class="stat-label">概念节点</div>
            </div>
          </n-gi>
          <n-gi>
            <div class="stat-box">
              <div class="stat-value">{{ documentDetail.statistics.claim_count }}</div>
              <div class="stat-label">论断</div>
            </div>
          </n-gi>
          <n-gi>
            <div class="stat-box">
              <div class="stat-value">{{ documentDetail.statistics.relation_count }}</div>
              <div class="stat-label">关系</div>
            </div>
          </n-gi>
        </n-grid>

        <!-- Themes -->
        <n-divider v-if="documentDetail.themes.length > 0">关联主题</n-divider>
        <div v-if="documentDetail.themes.length > 0">
          <n-space vertical :size="12">
            <div v-for="theme in documentDetail.themes" :key="theme.id" class="theme-item">
              <n-card :bordered="false" style="background: #f5f7fa;">
                <div class="theme-header">
                  <n-tag :type="theme.level === 1 ? 'success' : 'info'">
                    Level {{ theme.level }}
                  </n-tag>
                  <h4 style="margin: 0 16px; flex: 1;">{{ theme.label }}</h4>
                  <span style="color: #999; font-size: 14px;">{{ theme.member_count }} 成员</span>
                </div>
                <p class="theme-summary">{{ theme.summary }}</p>
              </n-card>
            </div>
          </n-space>
        </div>
        <div v-else class="empty-message">暂无关联主题</div>

        <!-- Metadata -->
        <n-divider v-if="Object.keys(documentDetail.meta).length > 0">元数据</n-divider>
        <div v-if="Object.keys(documentDetail.meta).length > 0">
          <n-code
            :code="JSON.stringify(documentDetail.meta, null, 2)"
            language="json"
            word-wrap
          />
        </div>

        <n-divider>文档预览</n-divider>
        <div v-if="canPreview" class="preview-container">
          <iframe :src="previewUrl" class="preview-frame" title="文档预览" />
        </div>
        <div v-else class="empty-message">当前文件类型暂不支持在线预览，请下载后查看。</div>
      </div>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, h } from 'vue'
import { useRouter } from 'vue-router'
import { useMessage } from 'naive-ui'
import {
  NButton,
  NTag,
  NIcon
} from 'naive-ui'
import {
  RefreshOutline,
  CloudUploadOutline,
  DocumentTextOutline,
  CheckmarkCircleOutline,
  HourglassOutline,
  SearchOutline
} from '@vicons/ionicons5'
import { listDocuments, getDocumentDetail, getDocumentFileUrl, deleteDocument, type DocumentListResponse, type DocumentDetail } from '@/api/services'

const router = useRouter()
const message = useMessage()

// 响应式变量
const filterStatus = ref('all')
const filterType = ref('all')
const searchKeyword = ref('')
const selectedDocs = ref<string[]>([]) // 选中的文档ID

// State
const loading = ref(false)
const documents = ref<DocumentListResponse['documents']>([])
const pagination = ref({
  page: 1,
  pageSize: 20,
  pageCount: 1,
  prefix: (info: any) => `共 ${info.itemCount} 条`,
  onChange: (page: number) => {
    pagination.value.page = page
    loadDocuments()
  }
})

const sortBy = ref<'created_at' | 'filename'>('created_at')
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
const totalDocuments = computed(() => documents.value.length)
const completedDocuments = computed(() => documents.value.filter(d => d.processing_status === 'completed').length)
const pendingDocuments = computed(() => documents.value.filter(d => d.processing_status === 'uploaded').length)

// Methods
// const loadDocuments = async () => {
//   loading.value = true
//   try {
//     const skip = (pagination.value.page - 1) * pagination.value.pageSize
//     const result = await listDocuments(skip, pagination.value.pageSize, sortBy.value)
//     documents.value = result.documents
//     pagination.value.pageCount = Math.ceil(result.total / pagination.value.pageSize)
//   } catch (error: any) {
//     message.error(`加载文档列表失败: ${error.message}`)
//   } finally {
//     loading.value = false
//   }
// }

const loadDocuments = async () => {
  loading.value = true
  try {
    const skip = (pagination.value.page - 1) * pagination.value.pageSize
    const result = await listDocuments(skip, pagination.value.pageSize, sortBy.value)

    // 前端筛选
    let filtered = result.documents

    // 状态筛选
    if (filterStatus.value !== 'all') {
      filtered = filtered.filter(d => {
        if (filterStatus.value === 'pending') {
          return d.processing_status === 'uploaded' || d.processing_status === 'pending'
        }
        return d.processing_status === filterStatus.value
      })
    }

    // 类型筛选
    if (filterType.value !== 'all') {
      filtered = filtered.filter(d => d.kind === filterType.value)
    }

    // 搜索筛选
    if (searchKeyword.value.trim()) {
      const keyword = searchKeyword.value.toLowerCase()
      filtered = filtered.filter(d =>
        d.filename.toLowerCase().includes(keyword)
      )
    }

    documents.value = filtered
    pagination.value.pageCount = Math.ceil(filtered.length / pagination.value.pageSize)

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
  try {
    // 创建对话框
    const modal = window.$dialog?.create({
      title: '确认删除',
      content: `确定要删除文档 "${doc.filename}" 吗？此操作不可恢复。`,
      positiveText: '删除',
      negativeText: '取消',
      type: 'error',
      onPositiveClick: async () => {
        try {
          const loadingMsg = message.loading('正在删除文档...', {
            duration: 0 // 持续显示
          })

          // 调用删除 API
          await deleteDocument(doc.id)

          // 关闭加载提示
          loadingMsg.destroy()

          // 显示成功消息
          message.success('文档删除成功')

          // 如果当前正在查看的文档被删除，关闭详情弹窗
          if (selectedDocument.value?.id === doc.id) {
            showDetailModal.value = false
            selectedDocument.value = null
            documentDetail.value = null
          }

          // 重新加载文档列表
          await loadDocuments()

        } catch (error: any) {
          message.error(`删除文档失败: ${error.message || '未知错误'}`)
        }
        return true // 允许对话框关闭
      },
      onNegativeClick: () => {
        // 用户取消
        return true
      }
    })

  } catch (error: any) {
    message.error(`创建确认对话框失败: ${error.message}`)
  }
}

const handleBatchDelete = async () => {
  const modal = window.$dialog?.create({
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

        // 批量删除
        for (const docId of selectedDocs.value) {
          try {
            await deleteDocument(docId)
          } catch (error) {
            console.error(`删除文档 ${docId} 失败:`, error)
          }
        }

        loadingMsg.destroy()
        message.success(`已删除 ${selectedDocs.value.length} 个文档`)

        // 重新加载
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

const rowKey = (row: any) => row.id

const rowProps = (row: any) => {
  return {
    onClick: () => {
      const index = selectedDocs.value.indexOf(row.id)
      if (index > -1) {
        selectedDocs.value.splice(index, 1)
      } else {
        selectedDocs.value.push(row.id)
      }
    }
  }
}

// Table columns
const columns = computed(() => [
  {
    type: 'selection',
    width: 40
  },
  {
    title: '文件名',
    key: 'filename',
    width: 250,
    ellipsis: { tooltip: true },
    render: (row: any) => row.filename
  },
  {
    title: '文件名',
    key: 'filename',
    width: 250,
    ellipsis: { tooltip: true },
    render: (row: any) => row.filename
  },
  {
    title: '类型',
    key: 'kind',
    width: 80,
    render: (row: any) => h(NTag, { type: getKindColor(row.kind) }, () => row.kind.toUpperCase())
  },
  {
    title: '大小',
    key: 'size',
    width: 100,
    render: (row: any) => formatFileSize(row.size)
  },
  {
    title: '文本块',
    key: 'chunk_count',
    width: 80,
    align: 'center' as const,
    render: (row: any) => h('span', { style: 'font-weight: bold; color: #3b82f6;' }, row.chunk_count)
  },
  {
    title: '概念',
    key: 'concept_count',
    width: 80,
    align: 'center' as const,
    render: (row: any) => h('span', { style: 'font-weight: bold; color: #10b981;' }, row.concept_count)
  },
  {
    title: '论断',
    key: 'claim_count',
    width: 80,
    align: 'center' as const,
    render: (row: any) => h('span', { style: 'font-weight: bold; color: #f59e0b;' }, row.claim_count)
  },
  {
    title: '状态',
    key: 'processing_status',
    width: 100,
    render: (row: any) => {
      const type = row.processing_status === 'completed' ? 'success' : 'warning'
      const label = row.processing_status === 'completed' ? '已完成' : '待处理'
      return h(NTag, { type }, () => label)
    }
  },
  {
    title: '上传时间',
    key: 'created_at',
    width: 180,
    render: (row: any) => formatTime(row.created_at)
  },
  {
    title: '操作',
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
          { default: () => '查看' }
        ),
        h(
          NButton,
          {
            size: 'small',
            type: 'info',
            text: true,
            onClick: () => handleViewGraph(row)
          },
          { default: () => '图谱' }
        ),
        h(
          NButton,
          {
            size: 'small',
            type: 'error',
            text: true,
            onClick: () => handleDeleteDocument(row)
          },
          { default: () => '删除' }
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

.header-actions {
  display: flex;
  gap: 12px;
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

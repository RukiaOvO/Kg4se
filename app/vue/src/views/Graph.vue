<template>
  <div class="graph-page">
    <!-- Enhanced Header -->
    <div class="graph-header">
      <div>
        <h1 class="graph-title">
          <n-gradient-text type="success">
            {{ t('graph.title') }}
          </n-gradient-text>
        </h1>
        <p class="graph-subtitle">交互式知识图谱可视化</p>
      </div>
    </div>

    <n-card class="graph-card" :bordered="false">
      <!-- Control Panel -->
      <div class="control-panel">
        <n-space :size="16" align="center">
          <!-- Search -->
          <div class="control-item">
            <n-input
              v-model:value="searchKeyword"
              placeholder="搜索节点..."
              clearable
              style="width: 180px"
              @keyup.enter="searchNode"
              @clear="clearSearch"
            >
              <template #prefix>
                <n-icon size="16" :component="SearchOutline" />
              </template>
            </n-input>
          </div>

          <!-- Node Limit -->
          <div class="control-item">
            <n-input-number
              v-model:value="nodeLimit"
              :min="10"
              :max="10000"
              :step="10"
              style="width: 200px"
              size="small"
            >
              <template #prefix>
                {{ t('graph.node_limit') }}
              </template>
            </n-input-number>
          </div>

          <!-- Layout Type -->
          <div class="control-item">
            <n-select
              v-model:value="layoutType"
              :options="layoutOptions"
              style="width: 120px"
              size="small"
              @update:value="handleLayoutChange"
            />
          </div>

          <!-- Load Button -->
          <n-button type="primary" :loading="loading" @click="loadGraph" size="small">
            <template #icon>
              <n-icon><refresh-outline /></n-icon>
            </template>
            {{ t('graph.load_graph') }}
          </n-button>

          <!-- Document Scope -->
          <div class="control-item" style="min-width: 240px">
            <n-select
              v-model:value="currentDocumentId"
              :options="documentOptions"
              placeholder="选择文档"
              clearable
              filterable
              style="width: 200px"
              size="small"
              @update:value="handleDocumentChange"
            />
          </div>

          <!-- Quick Actions -->
          <n-button type="success" @click="handleCreateNode" :disabled="!cy" size="small">
            <template #icon>
              <n-icon><add-outline /></n-icon>
            </template>
            创建节点
          </n-button>

          <n-button @click="handleCreateEdge" :disabled="!cy" size="small">
            <template #icon>
              <n-icon><link-outline /></n-icon>
            </template>
            创建关系
          </n-button>

          <!-- Graph Controls -->
          <n-button-group size="small">
            <n-button @click="zoomIn" :disabled="!cy" tooltip="放大">
              <template #icon>
                <n-icon><add-outline /></n-icon>
              </template>
            </n-button>
            <n-button @click="zoomOut" :disabled="!cy" tooltip="缩小">
              <template #icon>
                <n-icon><remove-outline /></n-icon>
              </template>
            </n-button>
            <n-button @click="fitView" :disabled="!cy" tooltip="适应视图">
              <template #icon>
                <n-icon><expand-outline /></n-icon>
              </template>
            </n-button>
            <n-button @click="resetView" :disabled="!cy" tooltip="重置视图">
              <template #icon>
                <n-icon><contract-outline /></n-icon>
              </template>
            </n-button>
          </n-button-group>

          <!-- Export -->
          <n-button @click="exportGraph" :disabled="!cy" size="small">
            <template #icon>
              <n-icon><download-outline /></n-icon>
            </template>
            导出
          </n-button>
        </n-space>
      </div>

      <!-- Stats Bar -->
      <div v-if="graphData" class="stats-bar">
        <div class="stat-item stat-blue">
          <n-icon size="20" :component="CubeOutline" />
          <span class="stat-label">{{ t('graph.nodes') }}</span>
          <n-number-animation :from="0" :to="graphData.nodes.length" :duration="1000" class="stat-value" />
        </div>
        <div class="stat-item stat-green">
          <n-icon size="20" :component="GitNetworkOutline" />
          <span class="stat-label">{{ t('graph.edges') }}</span>
          <n-number-animation :from="0" :to="graphData.edges.length" :duration="1000" class="stat-value" />
        </div>
        <div class="stat-item stat-yellow" v-if="currentDocumentId">
          <n-icon size="20" :component="InformationCircleOutline" />
          <span class="stat-label">文本块</span>
          <n-number-animation :from="0" :to="chunkCount" :duration="1000" class="stat-value" />
        </div>
        <div class="stat-item" v-if="docInfo">
          <n-icon size="20" :component="InformationCircleOutline" />
          <span class="stat-label">上传时间</span>
          <span class="stat-value">{{ docInfo.created_at || '未知' }}</span>
        </div>
        <div class="stat-item stat-yellow" v-if="selectedNode">
          <n-icon size="20" :component="InformationCircleOutline" />
          <span class="stat-label">已选择</span>
          <span class="stat-value">{{ selectedNode.label }}</span>
        </div>
      </div>

      <!-- Graph Container -->
      <div class="graph-wrapper">
        <div ref="graphContainer" class="graph-container"></div>
        
        <!-- Legend -->
        <div class="graph-legend">
          <div class="legend-title">节点类型</div>
          <div class="legend-items">
            <div class="legend-item">
              <div class="legend-color" style="background: #2080f0"></div>
              <span>概念 (Concept)</span>
            </div>
            <div class="legend-item">
              <div class="legend-color" style="background: #2d3748"></div>
              <span>文档 (Document)</span>
            </div>
            <div class="legend-item">
              <div class="legend-color" style="background: #f0a020"></div>
              <span>实体 (Entity)</span>
            </div>
            <div class="legend-item">
              <div class="legend-color" style="background: #18a058"></div>
              <span>其他 (Other)</span>
            </div>
          </div>
        </div>

        <!-- Loading Overlay -->
        <div v-if="loading" class="loading-overlay">
          <n-spin size="large">
            <template #description>
              <div class="loading-text">正在加载图谱数据...</div>
            </template>
          </n-spin>
        </div>

        <!-- Empty State -->
        <div v-if="!loading && !graphData" class="empty-state">
          <n-empty :description="t('graph.no_data')" size="huge">
            <template #icon>
              <n-icon size="80" :component="GitNetworkOutline" style="opacity: 0.3" />
            </template>
            <template #extra>
              <n-button type="primary" @click="$router.push('/knowledge')">
                去构建知识
              </n-button>
            </template>
          </n-empty>
        </div>
      </div>

      <!-- Node Detail Panel -->
      <n-drawer v-model:show="showNodeDetail" :width="400" placement="right">
        <n-drawer-content title="节点详情">
          <div v-if="selectedNode" class="node-detail">
            <n-descriptions :column="1" bordered>
              <n-descriptions-item label="ID">
                <n-text code>{{ selectedNode.id }}</n-text>
              </n-descriptions-item>
              <n-descriptions-item label="标签">
                <n-tag type="info" size="small">{{ selectedNode.label }}</n-tag>
              </n-descriptions-item>
              <n-descriptions-item v-for="(value, key) in selectedNode.properties" :key="key" :label="key">
                {{ value }}
              </n-descriptions-item>
            </n-descriptions>
          </div>
        </n-drawer-content>
      </n-drawer>

      <!-- Context Menu -->
      <div
        v-if="contextMenuVisible"
        class="context-menu"
        :style="{
          left: contextMenuPosition.x + 'px',
          top: contextMenuPosition.y + 'px'
        }"
      >
        <div v-if="contextMenuType === 'node'" class="context-menu-items">
          <div class="context-menu-item" @click="handleEditNode">
            <n-icon :component="CreateOutline" />
            <span>编辑节点</span>
          </div>
          <div class="context-menu-item" @click="handleCreateEdge">
            <n-icon :component="LinkOutline" />
            <span>创建关系</span>
          </div>
          <n-divider style="margin: 4px 0" />
          <div class="context-menu-item danger" @click="handleDeleteNode">
            <n-icon :component="TrashOutline" />
            <span>删除节点</span>
          </div>
        </div>

        <div v-if="contextMenuType === 'edge'" class="context-menu-items">
          <div class="context-menu-item danger" @click="handleDeleteEdge">
            <n-icon :component="TrashOutline" />
            <span>删除关系</span>
          </div>
        </div>

        <div v-if="contextMenuType === 'canvas'" class="context-menu-items">
          <div class="context-menu-item" @click="handleCreateNode">
            <n-icon :component="AddOutline" />
            <span>创建节点</span>
          </div>
          <div class="context-menu-item" @click="handleCreateEdge">
            <n-icon :component="LinkOutline" />
            <span>创建关系</span>
          </div>
        </div>
      </div>

      <!-- Node Edit Modal -->
      <n-modal v-model:show="showNodeEditModal" preset="dialog" title="编辑节点" style="width: 600px">
        <n-form :model="nodeEditForm" label-placement="left" label-width="100px">
          <n-form-item label="节点 ID">
            <n-input :value="nodeEditForm.id" disabled />
          </n-form-item>
          <n-form-item label="标签">
            <n-dynamic-tags v-model:value="nodeEditForm.labels" />
          </n-form-item>
          <n-form-item label="属性">
            <div style="width: 100%">
              <div v-for="(key) in Object.keys(nodeEditForm.properties)" :key="key" style="display: flex; gap: 8px; margin-bottom: 8px">
                <n-input :value="String(key)" disabled style="width: 150px" />
                <n-input v-model:value="nodeEditForm.properties[key]" style="flex: 1" />
              </div>
            </div>
          </n-form-item>
        </n-form>
        <template #action>
          <n-space>
            <n-button @click="showNodeEditModal = false">取消</n-button>
            <n-button type="primary" @click="submitNodeEdit">保存</n-button>
          </n-space>
        </template>
      </n-modal>

      <!-- Node Create Modal -->
      <n-modal v-model:show="showNodeCreateModal" preset="dialog" title="创建节点" style="width: 600px">
        <n-form :model="nodeCreateForm" label-placement="left" label-width="100px">
          <n-form-item label="标签">
            <n-dynamic-tags v-model:value="nodeCreateForm.labels" />
          </n-form-item>
          <n-form-item label="节点名称" required>
            <n-input v-model:value="nodeCreateForm.properties.name" placeholder="输入节点名称" />
          </n-form-item>
          <n-form-item label="描述">
            <n-input
              v-model:value="nodeCreateForm.properties.description"
              type="textarea"
              placeholder="输入节点描述（可选）"
              :autosize="{ minRows: 3, maxRows: 6 }"
            />
          </n-form-item>
        </n-form>
        <template #action>
          <n-space>
            <n-button @click="showNodeCreateModal = false">取消</n-button>
            <n-button type="primary" @click="submitNodeCreate">创建</n-button>
          </n-space>
        </template>
      </n-modal>

      <!-- Edge Create Modal -->
      <n-modal v-model:show="showEdgeCreateModal" preset="dialog" title="创建关系" style="width: 600px">
        <n-form :model="edgeCreateForm" label-placement="left" label-width="100px">
          <n-form-item label="源节点" required>
            <n-select
              v-model:value="edgeCreateForm.source"
              :options="availableNodes"
              filterable
              placeholder="选择源节点"
            />
          </n-form-item>
          <n-form-item label="目标节点" required>
            <n-select
              v-model:value="edgeCreateForm.target"
              :options="availableNodes"
              filterable
              placeholder="选择目标节点"
            />
          </n-form-item>
          <n-form-item label="关系类型" required>
            <n-input v-model:value="edgeCreateForm.type" placeholder="如：RELATES_TO, DEPENDS_ON" />
          </n-form-item>
          <n-form-item label="描述">
            <n-input
              v-model:value="edgeCreateForm.properties.description"
              type="textarea"
              placeholder="输入关系描述（可选）"
              :autosize="{ minRows: 2, maxRows: 4 }"
            />
          </n-form-item>
        </n-form>
        <template #action>
          <n-space>
            <n-button @click="showEdgeCreateModal = false">取消</n-button>
            <n-button type="primary" @click="submitEdgeCreate">创建</n-button>
          </n-space>
        </template>
      </n-modal>
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick, onMounted, onUnmounted, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useMessage, useDialog } from 'naive-ui'
import {
  RefreshOutline,
  LayersOutline,
  GridOutline,
  AddOutline,
  RemoveOutline,
  ExpandOutline,
  ContractOutline,
  DownloadOutline,
  CubeOutline,
  GitNetworkOutline,
  InformationCircleOutline,
  CreateOutline,
  TrashOutline,
  LinkOutline,
  SearchOutline
} from '@vicons/ionicons5'
import cytoscape from 'cytoscape'
import type { Core, ElementDefinition } from 'cytoscape'
import dagre from 'cytoscape-dagre'
import { 
  getGraphData, 
  getDocumentGraph,
  listDocuments,
  createNode, 
  updateNode, 
  deleteNode, 
  createEdge,
  deleteEdge
} from '@/api/services'

import { useDebounceFn } from '@vueuse/core'


cytoscape.use(dagre)

const { t } = useI18n()
const message = useMessage()
const dialog = useDialog()
const route = useRoute()
const router = useRouter()
const nodeLimit = ref(500)
const documentDepth = ref(2)
const currentDocumentId = ref<string | null>(null)
const documentOptions = ref<Array<{ label: string; value: string; meta?: any }>>([])
const debouncedLoadGraph = useDebounceFn(async () => {
  await loadGraph()
}, 300)
const search = useDebounceFn(async (keyword: string) => {
  const results = await api.search(keyword)
  // 处理结果
}, 300)
const docInfo = ref<{ id: string; filename?: string; created_at?: string } | null>(null)
const loading = ref(false)
const graphContainer = ref<HTMLElement | null>(null)
const graphData = ref<{ nodes: ElementDefinition[]; edges: ElementDefinition[] } | null>(null)
const layoutType = ref('dagre')
const selectedNode = ref<{ id: string; label: string; properties: Record<string, any> } | null>(null)
const searchKeyword = ref('')
const showNodeDetail = ref(false)
const showNodeEditModal = ref(false)
const showNodeCreateModal = ref(false)
const showEdgeCreateModal = ref(false)
const contextMenuVisible = ref(false)
const contextMenuPosition = ref({ x: 0, y: 0 })
const contextMenuTarget = ref<any | null>(null)
const contextMenuType = ref<'node' | 'edge' | 'canvas'>('canvas')
let cy: Core | null = null

// Form data
const nodeEditForm = ref<{ id: string; labels: string[]; properties: Record<string, any> }>({
  id: '',
  labels: [],
  properties: {}
})

const nodeCreateForm = ref<{ labels: string[]; properties: Record<string, any> }>({
  labels: ['Concept'],
  properties: {
    name: ''
  }
})

const edgeCreateForm = ref<{ source: string; target: string; type: string; properties: Record<string, any> }>({
  source: '',
  target: '',
  type: 'RELATES_TO',
  properties: {}
})

// Layout options
const layoutOptions = [
  { label: '层级布局', value: 'dagre' },
  { label: '圆形布局', value: 'circle' },
  { label: '网格布局', value: 'grid' },
  { label: '同心圆', value: 'concentric' },
  { label: '力导向', value: 'cose' }
]

const loadDocuments = async () => {
  try {
    const result = await listDocuments(0, 100)
    const docs = result?.documents || []
    documentOptions.value = docs.map((doc: any) => ({
      label: `${doc.filename} (${doc.id})`,
      value: doc.id,
      meta: doc
    }))
  } catch (err) {
    console.warn('加载文档列表失败', err)
  }
}

const handleDocumentChange = async (value: string | null) => {
  currentDocumentId.value = value
  if (value) {
    await router.replace({ path: '/graph', query: { doc_id: value } })
  } else {
    await router.replace({ path: '/graph' })
  }
  await loadGraph()
}

const loadGraph = async () => {
  loading.value = true
  try {
    // 优先使用路由中的 doc_id 过滤，默认加载全量图谱
    const routeDocId = (route.query.doc_id as string) || null
    currentDocumentId.value = currentDocumentId.value || routeDocId
    const docId = currentDocumentId.value

    const result = docId
      ? await getDocumentGraph(docId, documentDepth.value, nodeLimit.value)
      : await getGraphData(nodeLimit.value)
    
    if (!result) {
      message.warning(t('graph.no_data'))
      return
    }

    let nodes: ElementDefinition[] = []
    let edges: ElementDefinition[] = []

    // Backend returns format: { nodes: [], edges: [], stats: {} }
    if (result.nodes && result.edges) {
      // Transform backend Node format to Cytoscape format
      // New format includes: id, labels, type, label, properties, degree
      nodes = result.nodes
        .filter((node: any) => {
          // Filter out system nodes like system_config
          const nodeId = node.id || ''
          const nodeLabel = node.label || node.properties?.name || ''
          const isSystemNode = 
            nodeId.toLowerCase().includes('system') || 
            nodeId.toLowerCase().includes('config') ||
            nodeLabel.toLowerCase().includes('system') ||
            nodeLabel.toLowerCase().includes('config')
          return !isSystemNode
        })
        .map((node: any) => {
          // Extract labels and determine primary type
          // Handle different label formats: array, string, or undefined
          let nodeLabels = node.labels || []
          if (typeof nodeLabels === 'string') {
            nodeLabels = [nodeLabels]
          }
          const nodeType = node.type || (nodeLabels.length > 0 ? nodeLabels[0] : 'Unknown')
          
          // Also check properties for document type hints
          const hasFilename = !!node.properties?.filename
          const hasDocType = node.properties?.kind === 'pdf' || 
                           node.properties?.kind === 'docx' ||
                           node.properties?.kind === 'md'
          
          // Determine node class for styling
          // Prioritize known types: Concept, Document, Entity
          let nodeClass = 'Unknown'
          
          // 增强类型识别：收集所有可能的类型提示
          const typeLower = (nodeType || '').toLowerCase()
          const allHints = [
            nodeType, 
            ...nodeLabels, 
            node.label, 
            node.properties?.name,
            node.properties?.type
          ].filter(Boolean).map(h => String(h).toLowerCase())
          
          const hasConceptHint = allHints.some(h => h.includes('concept'))
          const hasEntityHint = allHints.some(h => h.includes('entity'))
          const hasDocumentHint = allHints.some(h => h.includes('document'))
          
          // 优先级：Concept > Document > Entity > Unknown
          if (hasConceptHint || typeLower === 'concept') {
            nodeClass = 'Concept'
          } else if (hasDocumentHint || typeLower === 'document' || hasFilename || hasDocType) {
            nodeClass = 'Document'
          } else if (hasEntityHint || typeLower === 'entity') {
            nodeClass = 'Entity'
          } else {
            // 如果都不匹配，尝试从 properties.type 获取类型
            const propType = (node.properties?.type || '').toLowerCase()
            if (propType.includes('concept')) {
              nodeClass = 'Concept'
            } else if (propType.includes('entity')) {
              nodeClass = 'Entity'
            } else if (propType.includes('document')) {
              nodeClass = 'Document'
            }
          }
          
          return {
            data: {
              id: node.id,
              label: node.label || node.properties?.name || node.properties?.filename || node.id,
              type: nodeClass,
              degree: node.degree || 0,
              ...node.properties
            },
            classes: nodeClass
          }
        })
      
      // Transform backend Edge format to Cytoscape format
      // First get valid node IDs after filtering
      const validNodeIds = new Set(nodes.map((n: any) => n.data.id))
      
      edges = result.edges
        .filter((edge: any) => {
          // Filter out edges connected to filtered nodes
          const sourceValid = validNodeIds.has(edge.source)
          const targetValid = validNodeIds.has(edge.target)
          return sourceValid && targetValid
        })
        .map((edge: any) => ({
          data: {
            id: edge.id || `${edge.source}-${edge.target}-${edge.type}`,
            source: edge.source,
            target: edge.target,
            label: edge.label || edge.type,
            type: edge.type,
            ...edge.properties
          }
        }))

      // Keep all filtered nodes, edges already filtered to only connect valid nodes
      
      // Re-process edges to ensure they only connect valid nodes
      const finalNodeIds = new Set(nodes.map((n: any) => n.data.id))
      edges = edges.filter((edge: any) => {
        const sourceValid = finalNodeIds.has(edge.data.source)
        const targetValid = finalNodeIds.has(edge.data.target)
        return sourceValid && targetValid
      })
    } else {
      edges = result.edges
        .map((edge: any) => ({
          data: {
            id: edge.id || `${edge.source}-${edge.target}-${edge.type}`,
            source: edge.source,
            target: edge.target,
            label: edge.label || edge.type,
            type: edge.type,
            ...edge.properties
          }
        }))
    }

    graphData.value = { nodes, edges }

    // 提取当前文档元信息（上传时间等）
    if (docId) {
      const docNode = nodes.find((n: any) => {
        const cls = (n.classes || '').toLowerCase()
        return n.data.id === docId || cls.includes('document')
      })
      if (docNode) {
        docInfo.value = {
          id: docId,
          filename: docNode.data.filename,
          created_at: docNode.data.created_at || docNode.data.createdAt
        }
      } else {
        docInfo.value = { id: docId }
      }
    } else {
      docInfo.value = null
    }

    if (nodes.length === 0) {
      message.warning(t('graph.no_nodes'))
      return
    }

    await nextTick()
    renderGraph()
    message.success(t('graph.loaded', { nodes: nodes.length, edges: edges.length }))
  } catch (error: any) {
    message.error(t('common.error'))
    console.error('Failed to load graph:', error)
  } finally {
    loading.value = false
  }
}

const renderGraph = () => {
  if (!graphContainer.value || !graphData.value) return

  if (cy) {
    cy.destroy()
  }

  const nodeCount = graphData.value.nodes.length
  const edgeCount = graphData.value.edges.length
  
  // Performance optimizations based on node count
  const shouldAnimate = nodeCount < 200
  const shouldShowLabels = nodeCount < 500
  const shouldSimplify = nodeCount >= 1000
  
  if (nodeCount >= 500) {
    message.warning(`图谱包含 ${nodeCount} 个节点和 ${edgeCount} 条边，可能会影响渲染性能。建议使用文档过滤功能或减小节点数量限制。`)
  }

  const layoutOptions: any = {
    name: layoutType.value,
    rankDir: 'TB',
    spacingFactor: shouldSimplify ? 1.2 : 1.5,
    animate: shouldAnimate,
    animationDuration: 300,
    randomize: false
  }

  // Build dynamic styles based on node count
  const nodeWidth = shouldSimplify ? 20 : 40
  const nodeHeight = shouldSimplify ? 20 : 40
  const fontSize = shouldSimplify ? 8 : 12
  
  const nodeStyle: any = {
    'background-color': '#18a058',
    'width': nodeWidth,
    'height': nodeHeight,
    'border-width': shouldSimplify ? 1 : 3,
    'border-color': '#fff',
    'box-shadow': shouldSimplify ? 'none' : '0 4px 8px rgba(0,0,0,0.15)'
  }
  
  if (shouldShowLabels) {
    nodeStyle['label'] = 'data(label)'
    nodeStyle['text-valign'] = 'bottom'
    nodeStyle['text-halign'] = 'center'
    nodeStyle['text-margin-y'] = '8px'
    nodeStyle['font-size'] = `${fontSize}px`
    nodeStyle['font-weight'] = 500
    nodeStyle['font-family'] = 'Noto Serif SC, sans-serif'
    nodeStyle['color'] = '#333'
    nodeStyle['text-background-color'] = '#fff'
    nodeStyle['text-background-opacity'] = 0.8
    nodeStyle['text-background-padding'] = '4px'
  }
  
  const edgeStyle: any = {
    'width': shouldSimplify ? 1 : 2,
    'line-color': '#cbd5e1',
    'target-arrow-color': '#cbd5e1',
    'target-arrow-shape': 'triangle',
    'curve-style': shouldSimplify ? 'straight' : 'bezier'
  }
  
  if (shouldShowLabels && !shouldSimplify) {
    edgeStyle['label'] = 'data(label)'
    edgeStyle['font-size'] = '10px'
    edgeStyle['text-background-color'] = '#fff'
    edgeStyle['text-background-opacity'] = 0.8
    edgeStyle['text-background-padding'] = '2px'
  }

  cy = cytoscape({
    container: graphContainer.value,
    elements: [...graphData.value.nodes, ...graphData.value.edges],
    style: ([
      {
        selector: 'node',
        style: nodeStyle
      },
      {
        selector: 'node.Concept',
        style: {
          'background-color': '#2080f0'
        }
      },
      {
        selector: 'node.Document',
        style: {
          'background-color': '#2d3748'
        }
      },
      {
        selector: 'node.Entity',
        style: {
          'background-color': '#f0a020'
        }
      },
      {
        selector: 'node:selected',
        style: {
          'border-width': 4,
          'border-color': '#6366f1',
          'width': shouldSimplify ? 26 : 50,
          'height': shouldSimplify ? 26 : 50
        }
      },
      {
        selector: 'edge',
        style: edgeStyle
      },
      {
        selector: 'edge:selected',
        style: {
          'width': 3,
          'line-color': '#6366f1',
          'target-arrow-color': '#6366f1'
        }
      },
      {
        selector: '.highlighted',
        style: {
          'background-color': '#FFD700 !important',
          'border-width': '3px !important',
          'border-color': '#FF6B6B !important',
          'line-color': '#FF6B6B !important',
          'target-arrow-color': '#FF6B6B !important'
        }
      }
    ] as any),
    layout: layoutOptions as any
  })

  // Node click handler
  cy.on('tap', 'node', (evt: any) => {
    const node = evt.target
    selectedNode.value = {
      id: node.id(),
      label: node.data('label'),
      properties: node.data()
    }
    showNodeDetail.value = true
  })

  // Right-click context menu
  cy.on('cxttap', 'node', (evt: any) => {
    evt.preventDefault()
    const node = evt.target
    const position = evt.renderedPosition || evt.position
    contextMenuType.value = 'node'
    contextMenuTarget.value = {
      id: node.id(),
      labels: node.classes(),
      properties: node.data()
    }
    contextMenuPosition.value = {
      x: position.x,
      y: position.y
    }
    contextMenuVisible.value = true
  })

  cy.on('cxttap', 'edge', (evt: any) => {
    evt.preventDefault()
    const edge = evt.target
    const position = evt.renderedPosition || evt.position
    contextMenuType.value = 'edge'
    contextMenuTarget.value = {
      id: edge.id(),
      source: edge.data('source'),
      target: edge.data('target'),
      type: edge.data('label'),
      properties: edge.data()
    }
    contextMenuPosition.value = {
      x: position.x,
      y: position.y
    }
    contextMenuVisible.value = true
  })

  cy.on('cxttap', (evt: any) => {
    if (evt.target === cy) {
      evt.preventDefault()
      const position = evt.renderedPosition || evt.position
      contextMenuType.value = 'canvas'
      contextMenuTarget.value = null
      contextMenuPosition.value = {
        x: position.x,
        y: position.y
      }
      contextMenuVisible.value = true
    }
  })

  // Close context menu on left click
  cy.on('tap', () => {
    contextMenuVisible.value = false
  })
}

const searchNode = () => {
  if (!cy || !searchKeyword.value.trim()) return

  // 清除之前的高亮
  cy.nodes().removeClass('highlighted')
  cy.edges().removeClass('highlighted')

  // 搜索节点
  const nodes = cy.nodes().filter(node => {
    const label = node.data('label') || ''
    const id = node.data('id') || ''
    const type = node.data('type') || ''

    return label.toLowerCase().includes(searchKeyword.value.toLowerCase()) ||
           id.toLowerCase().includes(searchKeyword.value.toLowerCase()) ||
           type.toLowerCase().includes(searchKeyword.value.toLowerCase())
  })

  if (nodes.length > 0) {
    // 高亮显示
    nodes.addClass('highlighted')

    // 获取关联的边
    const connectedEdges = nodes.connectedEdges()
    connectedEdges.addClass('highlighted')

    // 聚焦到搜索结果
    cy.animate({
      fit: { eles: nodes, padding: 100 },
      duration: 500
    })

    message.success(`找到 ${nodes.length} 个节点`)
  } else {
    message.warning('未找到匹配的节点')
  }
}

const clearSearch = () => {
  if (cy) {
    cy.nodes().removeClass('highlighted')
    cy.edges().removeClass('highlighted')
  }
}


// Graph control functions
const zoomIn = () => {
  if (cy) cy.zoom(cy.zoom() * 1.2)
}

const zoomOut = () => {
  if (cy) cy.zoom(cy.zoom() * 0.8)
}

const fitView = () => {
  if (cy) cy.fit(undefined, 50)
}

const resetView = () => {
  if (cy) {
    cy.zoom(1)
    cy.center()
  }
}

const handleLayoutChange = () => {
  if (cy && graphData.value) {
    const layout = cy.layout(({ 
      name: layoutType.value,
      animate: true,
      animationDuration: 500,
      spacingFactor: 1.5
    } as any))
    layout.run()
  }
}

const exportGraph = () => {
  if (!cy) return
  
  const png = cy.png({
    full: true,
    scale: 2,
    bg: '#ffffff'
  })
  
  const link = document.createElement('a')
  link.download = `knowledge-graph-${Date.now()}.png`
  link.href = png
  link.click()
  
  message.success('图谱已导出')
}

const resetDocumentFilter = async () => {
  // 清除 doc_id 查询参数，回到全局图谱
  currentDocumentId.value = null
  await router.replace({ path: '/graph' })
  await loadGraph()
}

// ========== Node CRUD Operations ==========

const handleEditNode = () => {
  if (!contextMenuTarget.value) return
  const target = contextMenuTarget.value
  
  nodeEditForm.value = {
    id: target.id,
    labels: target.labels || [],
    properties: { ...target.properties }
  }
  
  showNodeEditModal.value = true
  contextMenuVisible.value = false
}

const handleCreateNode = () => {
  nodeCreateForm.value = {
    labels: ['Concept'],
    properties: {
      name: ''
    }
  }
  
  showNodeCreateModal.value = true
  contextMenuVisible.value = false
}

const handleDeleteNode = () => {
  if (!contextMenuTarget.value) return
  const target = contextMenuTarget.value
  dialog.warning({
    title: '确认删除节点',
    content: `确定要删除节点 "${contextMenuTarget.value.properties.name || contextMenuTarget.value.id}" 吗？`,
    positiveText: '删除',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        await deleteNode(target.id, true)
        message.success('节点已删除')
        await loadGraph()
      } catch (error: any) {
        message.error('删除节点失败：' + (error.response?.data?.detail || error.message))
      }
    }
  })
  
  contextMenuVisible.value = false
}

const submitNodeEdit = async () => {
  try {
    const updateData = {
      labels: nodeEditForm.value.labels.length > 0 ? nodeEditForm.value.labels : undefined,
      properties: nodeEditForm.value.properties
    }
    
    await updateNode(nodeEditForm.value.id, updateData)
    message.success('节点已更新')
    showNodeEditModal.value = false
    await loadGraph()
  } catch (error: any) {
    message.error('更新节点失败：' + (error.response?.data?.detail || error.message))
  }
}

const submitNodeCreate = async () => {
  try {
    if (!nodeCreateForm.value.properties.name) {
      message.error('请输入节点名称')
      return
    }
    
    const createData = {
      labels: nodeCreateForm.value.labels,
      properties: nodeCreateForm.value.properties
    }
    
    await createNode(createData)
    message.success('节点已创建')
    showNodeCreateModal.value = false
    await loadGraph()
  } catch (error: any) {
    message.error('创建节点失败：' + (error.response?.data?.detail || error.message))
  }
}

// ========== Edge CRUD Operations ==========

const handleCreateEdge = () => {
  if (contextMenuType.value === 'node' && contextMenuTarget.value) {
    const t = contextMenuTarget.value
    edgeCreateForm.value.source = t.id
    edgeCreateForm.value.target = ''
  } else {
    edgeCreateForm.value.source = ''
    edgeCreateForm.value.target = ''
  }
  
  edgeCreateForm.value.type = 'RELATES_TO'
  edgeCreateForm.value.properties = {}
  
  showEdgeCreateModal.value = true
  contextMenuVisible.value = false
}

const handleDeleteEdge = () => {
  if (!contextMenuTarget.value) return
  const etarget = contextMenuTarget.value
  
  dialog.warning({
    title: '确认删除关系',
    content: `确定要删除 "${etarget.source}" 到 "${etarget.target}" 的 "${etarget.type}" 关系吗？`,
    positiveText: '删除',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        await deleteEdge(
          etarget.source,
          etarget.target,
          etarget.type
        )
        message.success('关系已删除')
        await loadGraph()
      } catch (error: any) {
        message.error('删除关系失败：' + (error.response?.data?.detail || error.message))
      }
    }
  })
  
  contextMenuVisible.value = false
}

const submitEdgeCreate = async () => {
  try {
    if (!edgeCreateForm.value.source || !edgeCreateForm.value.target) {
      message.error('请选择源节点和目标节点')
      return
    }
    
    if (!edgeCreateForm.value.type) {
      message.error('请输入关系类型')
      return
    }
    
    const createData = {
      source: edgeCreateForm.value.source,
      target: edgeCreateForm.value.target,
      type: edgeCreateForm.value.type,
      properties: edgeCreateForm.value.properties
    }
    
    await createEdge(createData)
    message.success('关系已创建')
    showEdgeCreateModal.value = false
    await loadGraph()
  } catch (error: any) {
    message.error('创建关系失败：' + (error.response?.data?.detail || error.message))
  }
}

// Available nodes for edge creation
const availableNodes = computed(() => {
  if (!graphData.value) return []
  return graphData.value.nodes.map((node: any) => ({
    label: node.data.label || node.data.id,
    value: node.data.id
  }))
})

const chunkCount = computed(() => {
  if (!graphData.value) return 0
  return graphData.value.nodes.filter((node: any) => {
    const type = (node.data.type || '').toLowerCase()
    const classes = (node.classes || '').toLowerCase()
    return type === 'chunk' || classes.includes('chunk')
  }).length
})

// 路由参数变化时自动切换图谱视图
watch(
  () => route.query.doc_id,
  async () => {
    await debouncedLoadGraph() // TODO 添加防抖或者节流控制
  }
)

onMounted(() => {
  loadDocuments()
  loadGraph()
})

onUnmounted(() => {
  if (cy) {
    cy.destroy()
  }
})
</script>

<style lang="scss" scoped>
.graph-page {
  padding: 32px 48px;
  background: #f5f7fa;
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
      radial-gradient(circle at 20% 20%, rgba(16, 185, 129, 0.05) 0%, transparent 50%),
      radial-gradient(circle at 80% 80%, rgba(52, 211, 153, 0.05) 0%, transparent 50%),
      radial-gradient(circle at 50% 50%, rgba(5, 150, 105, 0.03) 0%, transparent 60%);
    pointer-events: none;
    z-index: 0;
  }

  > * {
    position: relative;
    z-index: 1;
  }

  // Header Section - 轻奢现代化设计
  .graph-header {
    margin-bottom: 32px;
    padding: 32px 36px;
    background: linear-gradient(135deg, 
      rgba(240, 253, 244, 0.95) 0%, 
      rgba(236, 254, 255, 0.95) 50%, 
      rgba(245, 243, 255, 0.95) 100%);
    border-radius: 24px;
    backdrop-filter: blur(20px);
    box-shadow: 
      0 8px 32px rgba(0, 0, 0, 0.06),
      0 2px 8px rgba(0, 0, 0, 0.04),
      inset 0 1px 0 rgba(255, 255, 255, 0.8);
    border: 1px solid rgba(255, 255, 255, 0.6);
    position: relative;
    overflow: hidden;

    &::before {
      content: '';
      position: absolute;
      top: 0;
      left: 0;
      right: 0;
      height: 2px;
      background: linear-gradient(90deg, 
        transparent, 
        rgba(16, 185, 129, 0.4), 
        transparent);
    }

    .graph-title {
      font-size: 36px;
      font-weight: 700;
      margin: 0 0 10px 0;
      letter-spacing: -0.5px;
    }

    .graph-subtitle {
      font-size: 15px;
      color: #64748b;
      margin: 0;
      font-weight: 500;
    }
  }

  .graph-card {
    border-radius: 24px;
    box-shadow: 
      0 8px 32px rgba(0, 0, 0, 0.06),
      0 2px 12px rgba(0, 0, 0, 0.04);
    border: 1px solid rgba(255, 255, 255, 0.6);
    backdrop-filter: blur(10px);
    transition: all 0.3s;

    &:hover {
      box-shadow: 
        0 12px 40px rgba(0, 0, 0, 0.08),
        0 4px 16px rgba(0, 0, 0, 0.06);
    }

    :deep(.n-card__content) {
      padding: 28px;
    }
  }

  // Control Panel - 轻奢控制面板
  .control-panel {
    padding: 24px 28px;
    background: linear-gradient(135deg, 
      rgba(240, 253, 244, 0.6) 0%, 
      rgba(236, 254, 255, 0.6) 50%, 
      rgba(255, 255, 255, 0.6) 100%);
    backdrop-filter: blur(10px);
    border-radius: 20px;
    margin-bottom: 24px;
    border: 1px solid rgba(16, 185, 129, 0.15);
    box-shadow: 
      0 4px 16px rgba(0, 0, 0, 0.04),
      inset 0 1px 0 rgba(255, 255, 255, 0.8);

    .control-item {
      display: flex;
      align-items: center;
      gap: 10px;

      .control-icon {
        color: #10b981;
        filter: drop-shadow(0 2px 4px rgba(16, 185, 129, 0.2));
      }
    }

    :deep(.n-input-number),
    :deep(.n-select) {
      border-radius: 16px;
      
      .n-input__border,
      .n-input__state-border {
        border-radius: 16px;
      }
    }

    :deep(.n-button) {
      border-radius: 16px;
      font-weight: 600;
      letter-spacing: 0.3px;
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
      transition: all 0.3s;

      &:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.12);
      }
    }
  }

  // Stats Bar - 轻奢统计条
  .stats-bar {
    display: flex;
    gap: 20px;
    padding: 20px;
    background: linear-gradient(135deg, 
      rgba(255, 255, 255, 0.9) 0%, 
      rgba(248, 250, 252, 0.9) 100%);
    backdrop-filter: blur(10px);
    border-radius: 20px;
    margin-bottom: 24px;
    border: 1px solid rgba(226, 232, 240, 0.6);
    box-shadow: 
      0 4px 16px rgba(0, 0, 0, 0.04),
      inset 0 1px 0 rgba(255, 255, 255, 0.8);

    .stat-item {
      display: flex;
      align-items: center;
      gap: 14px;
      padding: 16px 24px;
      border-radius: 16px;
      background: linear-gradient(135deg, 
        rgba(255, 255, 255, 0.95) 0%, 
        rgba(248, 250, 252, 0.95) 100%);
      flex: 1;
      transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
      position: relative;
      overflow: hidden;
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);

      &::before {
        content: '';
        position: absolute;
        left: 0;
        top: 0;
        bottom: 0;
        width: 4px;
        transition: width 0.3s;
      }

      &:hover {
        transform: translateY(-4px);
        box-shadow: 
          0 8px 16px rgba(0, 0, 0, 0.1),
          0 2px 8px rgba(0, 0, 0, 0.06);

        &::before {
          width: 100%;
          opacity: 0.05;
        }
      }

      &.stat-blue {
        &::before {
          background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
        }
        
        .n-icon {
          color: #3b82f6;
        }
      }

      &.stat-green {
        &::before {
          background: linear-gradient(135deg, #10b981 0%, #059669 100%);
        }
        
        .n-icon {
          color: #10b981;
        }
      }

      &.stat-yellow {
        &::before {
          background: linear-gradient(135deg, #f59e0b 0%, #c2a474 100%);
        }
        
        .n-icon {
          color: #f59e0b;
        }
      }

      .stat-label {
        font-size: 14px;
        color: #64748b;
        font-weight: 600;
      }

      .stat-value {
        font-size: 24px;
        font-weight: 800;
        color: #0f172a;
        letter-spacing: -0.5px;
      }
    }
  }

  // Graph Wrapper - 企业级图谱容器
  .graph-wrapper {
    position: relative;
    height: 720px;
    border-radius: 20px;
    overflow: hidden;
    background: linear-gradient(135deg, 
      #f8fafc 0%, 
      #f1f5f9 50%, 
      #e2e8f0 100%);
    border: 1px solid rgba(226, 232, 240, 0.8);
    box-shadow: 
      inset 0 2px 8px rgba(0, 0, 0, 0.04),
      0 4px 16px rgba(0, 0, 0, 0.06);
  }

  .graph-container {
    width: 100%;
    height: 100%;
    background: #ffffff;
    position: relative;

    &::before {
      content: '';
      position: absolute;
      inset: 0;
      background: 
        radial-gradient(circle at 20% 30%, rgba(99, 102, 241, 0.03) 0%, transparent 50%),
        radial-gradient(circle at 80% 70%, rgba(16, 185, 129, 0.03) 0%, transparent 50%);
      pointer-events: none;
    }
  }

  // Graph Legend - 轻奢图例
  .graph-legend {
    position: absolute;
    bottom: 24px;
    left: 24px;
    background: linear-gradient(135deg, 
      rgba(255, 255, 255, 0.98) 0%, 
      rgba(248, 250, 252, 0.98) 100%);
    backdrop-filter: blur(20px);
    padding: 20px 24px;
    border-radius: 20px;
    box-shadow: 
      0 8px 24px rgba(0, 0, 0, 0.12),
      0 2px 8px rgba(0, 0, 0, 0.08),
      inset 0 1px 0 rgba(255, 255, 255, 0.8);
    border: 1px solid rgba(255, 255, 255, 0.6);
    z-index: 10;

    .legend-title {
      font-weight: 700;
      font-size: 15px;
      color: #0f172a;
      margin-bottom: 16px;
      letter-spacing: -0.2px;
    }

    .legend-items {
      display: flex;
      flex-direction: column;
      gap: 12px;
    }

    .legend-item {
      display: flex;
      align-items: center;
      gap: 12px;
      font-size: 14px;
      color: #475569;
      font-weight: 500;
      transition: all 0.2s;
      padding: 4px;
      border-radius: 8px;

      &:hover {
        background: rgba(0, 0, 0, 0.02);
        color: #1e293b;
      }

      .legend-color {
        width: 24px;
        height: 24px;
        border-radius: 50%;
        border: 3px solid #fff;
        box-shadow: 
          0 4px 8px rgba(0, 0, 0, 0.15),
          0 1px 4px rgba(0, 0, 0, 0.1);
        transition: transform 0.2s;
      }

      &:hover .legend-color {
        transform: scale(1.1);
      }
    }
  }

  // Loading Overlay - 轻奢加载层
  .loading-overlay {
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: linear-gradient(135deg, 
      rgba(255, 255, 255, 0.98) 0%, 
      rgba(248, 250, 252, 0.98) 100%);
    backdrop-filter: blur(16px);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 100;
    border-radius: 20px;

    .loading-text {
      margin-top: 20px;
      font-size: 17px;
      color: #475569;
      font-weight: 600;
      letter-spacing: 0.3px;
    }
  }

  // Empty State
  .empty-state {
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    z-index: 10;

    :deep(.n-empty) {
      .n-empty__icon {
        margin-bottom: 20px;
      }

      .n-empty__description {
        font-size: 16px;
        font-weight: 500;
        color: #64748b;
      }
    }
  }

  // Node Detail - 轻奢节点详情
  .node-detail {
    :deep(.n-descriptions) {
      .n-descriptions-table-content {
        padding: 12px;
      }

      .n-descriptions-table-wrapper {
        border-radius: 16px;
        overflow: hidden;
      }

      .n-descriptions-table-row {
        transition: background 0.2s;

        &:hover {
          background: rgba(0, 0, 0, 0.02);
        }
      }
    }
  }

  // Drawer 样式增强
  :deep(.n-drawer) {
    .n-drawer-header {
      padding: 24px 28px;
      font-weight: 700;
      font-size: 18px;
      letter-spacing: -0.3px;
      border-bottom: 1px solid rgba(226, 232, 240, 0.6);
    }

    .n-drawer-body-content-wrapper {
      padding: 24px 28px;
    }
  }
}

// Animations - 流畅动画
@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateY(30px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes shimmer {
  0% {
    background-position: -1000px 0;
  }
  100% {
    background-position: 1000px 0;
  }
}

.graph-page > * {
  animation: slideIn 0.5s ease-out;
}

// 全局按钮样式增强
:deep(.n-button) {
  border-radius: 16px;
  font-weight: 600;
  letter-spacing: 0.3px;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);

  &:not(:disabled):hover {
    transform: translateY(-2px);
  }

  &.n-button--primary-type {
    box-shadow: 0 4px 12px rgba(16, 185, 129, 0.25);

    &:hover {
      box-shadow: 0 6px 16px rgba(16, 185, 129, 0.35);
    }
  }
}

  // Button Group 样式增强
:deep(.n-button-group) {
  border-radius: 16px;
  overflow: hidden;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);

  .n-button {
    border-radius: 0;

    &:first-child {
      border-top-left-radius: 16px;
      border-bottom-left-radius: 16px;
    }

    &:last-child {
      border-top-right-radius: 16px;
      border-bottom-right-radius: 16px;
    }
  }
}

// 高亮样式增强
.highlighted {
  z-index: 999 !important;
  box-shadow: 0 0 20px rgba(255, 107, 107, 0.5) !important;
  animation: pulse 1.5s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.8; }
}

// Context Menu 样式
.context-menu {
  position: fixed;
  background: linear-gradient(135deg, 
    rgba(255, 255, 255, 0.98) 0%, 
    rgba(248, 250, 252, 0.98) 100%);
  backdrop-filter: blur(20px);
  border-radius: 16px;
  box-shadow: 
    0 8px 32px rgba(0, 0, 0, 0.15),
    0 2px 12px rgba(0, 0, 0, 0.1),
    inset 0 1px 0 rgba(255, 255, 255, 0.8);
  border: 1px solid rgba(255, 255, 255, 0.6);
  padding: 8px;
  z-index: 1000;
  min-width: 180px;

  .context-menu-items {
    .context-menu-item {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 10px 14px;
      border-radius: 12px;
      cursor: pointer;
      transition: all 0.2s;
      font-size: 14px;
      font-weight: 500;
      color: #334155;

      .n-icon {
        font-size: 18px;
        color: #64748b;
      }

      &:hover {
        background: rgba(16, 185, 129, 0.08);
        color: #10b981;

        .n-icon {
          color: #10b981;
        }
      }

      &.danger {
        &:hover {
          background: rgba(239, 68, 68, 0.08);
          color: #ef4444;

          .n-icon {
            color: #ef4444;
          }
        }
      }
    }
  }
}

// Modal 样式增强
:deep(.n-modal) {
  .n-dialog {
    border-radius: 24px;
    overflow: hidden;

    .n-dialog__title {
      font-size: 20px;
      font-weight: 700;
      color: #0f172a;
    }
  }

  .n-form-item {
    margin-bottom: 20px;

    .n-form-item-label {
      font-weight: 600;
      color: #475569;
    }
  }

  .n-input,
  .n-select,
  .n-input-number {
    border-radius: 12px;
  }

  .n-button {
    border-radius: 12px;
    font-weight: 600;
  }
}
</style>
# Vue 前端开发指南

## 📋 快速开始

### 环境要求

- Node.js >= 18
- npm >= 9 或 pnpm >= 8

### 安装依赖

```bash
cd app/vue
npm install
```

### 开发模式

```bash
npm run dev
# 访问 http://localhost:5173
```

### 生产构建

```bash
npm run build
# 输出到 dist/ 目录
```

---

## 🎯 核心功能模块

### 1. 文档管理模块

**位置**: `src/views/Documents.vue` + `src/views/Upload.vue`

**功能**:
- ✅ 文档上传（拖拽/选择）
- ✅ 批量上传
- ✅ 文档列表展示
- ✅ 状态筛选
- ✅ 搜索功能
- ✅ 删除操作

**API调用**:
```typescript
import { documentApi } from '@/api/services'

// 上传文档
const result = await documentApi.upload(file, {
  enableAISegmentation: true,
  userPrompt: '关注架构设计'
})

// 获取文档列表
const documents = await documentApi.list({
  page: 1,
  pageSize: 20,
  status: 'completed'
})

// 删除文档
await documentApi.delete(docId)
```

---

### 2. 知识图谱可视化

**位置**: `src/views/Graph.vue` (1571行核心代码)

**技术栈**:
- Cytoscape.js: 图可视化引擎
- cytoscape-dagre: 层次布局算法
- Naive UI: UI组件

**布局算法**:

| 算法 | 特点 | 适用场景 |
|------|------|----------|
| `cose` | 力导向 | 通用，自然分布 |
| `dagre` | 层次树 | 有向无环图 |
| `circle` | 环形 | 强调关系对称性 |
| `grid` | 网格 | 规整排列 |
| `concentric` | 同心圆 | 中心化展示 |

**核心功能实现**:

```typescript
// 1. 初始化Cytoscape实例
const initCytoscape = () => {
  cy = cytoscape({
    container: document.getElementById('cy'),
    style: [
      {
        selector: 'node',
        style: {
          'label': 'data(label)',
          'background-color': '#4CAF50',
          'text-valign': 'center',
          'text-halign': 'center',
          'font-size': '12px',
          'width': 'label',
          'height': 'label',
          'padding': '10px'
        }
      },
      {
        selector: 'edge',
        style: {
          'label': 'data(label)',
          'curve-style': 'bezier',
          'target-arrow-shape': 'triangle',
          'line-color': '#9E9E9E',
          'target-arrow-color': '#9E9E9E',
          'font-size': '10px'
        }
      }
    ]
  })
  
  // 绑定事件
  cy.on('tap', 'node', (evt) => {
    const node = evt.target
    showNodeDetail(node.data())
  })
  
  cy.on('cxttap', 'node', (evt) => {
    // 右键菜单
    showContextMenu(evt)
  })
}

// 2. 加载图谱数据
const loadGraph = async () => {
  loading.value = true
  try {
    let data: GraphData
    
    if (currentDocumentId.value) {
      // 加载文档范围图谱
      data = await graphApi.getDocumentGraph(
        currentDocumentId.value,
        documentDepth.value
      )
    } else {
      // 加载全局图谱
      data = await graphApi.visualize({
        limit: nodeLimit.value
      })
    }
    
    renderGraph(data)
  } finally {
    loading.value = false
  }
}

// 3. 渲染图谱
const renderGraph = (data: GraphData) => {
  cy.elements().remove()
  
  // 添加节点
  const nodes = data.nodes.map(node => ({
    data: {
      id: node.id,
      label: node.properties.name || node.id,
      ...node.properties
    }
  }))
  
  // 添加边
  const edges = data.edges.map(edge => ({
    data: {
      id: edge.id,
      source: edge.source,
      target: edge.target,
      label: edge.properties.predicate || edge.type,
      ...edge.properties
    }
  }))
  
  cy.add([...nodes, ...edges])
  
  // 应用布局
  cy.layout({
    name: layoutType.value,
    animate: true,
    animationDuration: 500
  }).run()
}

// 4. 搜索定位
const searchNode = (keyword: string) => {
  const nodes = cy.nodes().filter(node => 
    node.data('label').includes(keyword)
  )
  
  if (nodes.length > 0) {
    cy.animate({
      fit: { eles: nodes, padding: 50 },
      duration: 500
    })
    nodes.addClass('highlighted')
  }
}
```

**样式配置**:
```scss
.cytoscape-container {
  width: 100%;
  height: 600px;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  background: #fafafa;
}

// 高亮样式
.highlighted {
  background-color: #FFD700 !important;
  border-width: 3px !important;
  border-color: #FF6B6B !important;
}
```

---

### 3. 智能问答系统

**位置**: `src/views/Query.vue`

**界面特性**:
- 类ChatGPT对话界面
- Markdown渲染
- 代码高亮
- 历史记录

**实现示例**:
```vue
<template>
  <div class="qa-container">
    <!-- 对话历史 -->
    <div class="messages">
      <div
        v-for="msg in messages"
        :key="msg.id"
        :class="['message', msg.role]"
      >
        <div class="message-content">
          <Markdown :source="msg.content" />
        </div>
        <div class="message-meta">
          {{ formatTime(msg.timestamp) }}
        </div>
      </div>
    </div>
    
    <!-- 输入框 -->
    <div class="input-area">
      <n-input
        v-model:value="question"
        type="textarea"
        placeholder="输入您的问题..."
        @keydown.enter.prevent="handleSend"
      />
      <n-button
        type="primary"
        :loading="loading"
        @click="handleSend"
      >
        发送
      </n-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { qaApi } from '@/api/services'
import Markdown from '@/components/Markdown.vue'

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: number
}

const messages = ref<Message[]>([])
const question = ref('')
const loading = ref(false)

const handleSend = async () => {
  if (!question.value.trim()) return
  
  // 添加用户消息
  messages.value.push({
    id: `msg_${Date.now()}`,
    role: 'user',
    content: question.value,
    timestamp: Date.now()
  })
  
  const userQuestion = question.value
  question.value = ''
  loading.value = true
  
  try {
    // 调用API
    const response = await qaApi.ask(userQuestion)
    
    // 添加AI回复
    messages.value.push({
      id: `msg_${Date.now()}`,
      role: 'assistant',
      content: response.answer,
      timestamp: Date.now()
    })
  } catch (error) {
    message.error('问答失败')
  } finally {
    loading.value = false
  }
}

const formatTime = (timestamp: number) => {
  return new Date(timestamp).toLocaleTimeString()
}
</script>

<style scoped>
.qa-container {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 200px);
}

.messages {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
}

.message {
  margin-bottom: 20px;
  padding: 12px 16px;
  border-radius: 8px;
  max-width: 80%;
}

.message.user {
  margin-left: auto;
  background: #e3f2fd;
}

.message.assistant {
  background: #f5f5f5;
}

.input-area {
  display: flex;
  gap: 12px;
  padding: 20px;
  border-top: 1px solid #e0e0e0;
}
</style>
```

---

### 4. 知识卡片系统

**位置**: `src/views/KnowledgeCard.vue`

**功能**:
- 概念列表浏览
- 全文搜索
- 概念详情
- 关系网络

**卡片组件**:
```vue
<template>
  <n-card class="concept-card" hoverable>
    <template #header>
      <div class="card-header">
        <n-tag type="success">{{ concept.canonical_name }}</n-tag>
        <n-space>
          <n-tag
            v-for="alias in concept.aliases"
            :key="alias"
            size="small"
          >
            {{ alias }}
          </n-tag>
        </n-space>
      </div>
    </template>
    
    <div class="card-content">
      <div class="properties">
        <div
          v-for="(value, key) in concept.properties"
          :key="key"
          class="property-item"
        >
          <span class="key">{{ key }}:</span>
          <span class="value">{{ value }}</span>
        </div>
      </div>
      
      <div class="relations">
        <h4>关联关系</h4>
        <n-space>
          <n-tag
            v-for="rel in concept.relations"
            :key="rel.id"
            type="info"
            size="small"
          >
            {{ rel.predicate }} → {{ rel.target }}
          </n-tag>
        </n-space>
      </div>
    </div>
    
    <template #footer>
      <n-space justify="end">
        <n-button size="small" @click="viewDetail">
          详情
        </n-button>
        <n-button size="small" @click="visualize">
          可视化
        </n-button>
      </n-space>
    </template>
  </n-card>
</template>
```

---

## 🎨 组件开发规范

### 1. 组件命名

```typescript
// ✅ 推荐：PascalCase
const MyComponent = defineComponent({})

// ❌ 避免：kebab-case
const my-component = defineComponent({})
```

### 2. Props定义

```typescript
interface Props {
  title: string
  count?: number
  data: Array<any>
}

const props = withDefaults(defineProps<Props>(), {
  count: 0
})
```

### 3. Emits定义

```typescript
const emit = defineEmits<{
  (e: 'update:modelValue', value: string): void
  (e: 'submit', data: FormData): void
}>()
```

### 4. 组件结构

```vue
<script setup lang="ts">
// 1. 导入
import { ref, computed, onMounted } from 'vue'

// 2. Props/Emits
const props = defineProps<Props>()
const emit = defineEmits<Emits>()

// 3. 响应式状态
const count = ref(0)

// 4. 计算属性
const doubleCount = computed(() => count.value * 2)

// 5. 方法
const increment = () => {
  count.value++
}

// 6. 生命周期
onMounted(() => {
  // 初始化
})
</script>

<template>
  <!-- 模板 -->
</template>

<style scoped>
/* 样式 */
</style>
```

---

## 🔌 API集成最佳实践

### 1. 错误处理

```typescript
import { message } from 'naive-ui'

const loadData = async () => {
  try {
    const data = await api.getData()
    return data
  } catch (error: any) {
    if (error.response) {
      // 服务器返回错误
      message.error(error.response.data.message || '请求失败')
    } else if (error.request) {
      // 网络错误
      message.error('网络连接失败')
    } else {
      // 其他错误
      message.error('操作失败')
    }
    throw error
  }
}
```

### 2. 加载状态

```typescript
const loading = ref(false)

const fetchData = async () => {
  loading.value = true
  try {
    const data = await api.getData()
    // 处理数据
  } finally {
    loading.value = false
  }
}
```

### 3. 防抖/节流

```typescript
import { useDebounceFn } from '@vueuse/core'

const search = useDebounceFn(async (keyword: string) => {
  const results = await api.search(keyword)
  // 处理结果
}, 300)
```

---

## 📦 状态管理模式

### Store定义

```typescript
// stores/document.ts
export const useDocumentStore = defineStore('document', () => {
  // State
  const documents = ref<Document[]>([])
  const currentDocument = ref<Document | null>(null)
  
  // Getters
  const documentCount = computed(() => documents.value.length)
  const completedDocuments = computed(() => 
    documents.value.filter(d => d.status === 'completed')
  )
  
  // Actions
  const loadDocuments = async () => {
    const data = await documentApi.list()
    documents.value = data
  }
  
  const selectDocument = (docId: string) => {
    currentDocument.value = documents.value.find(d => d.id === docId) || null
  }
  
  return {
    documents,
    currentDocument,
    documentCount,
    completedDocuments,
    loadDocuments,
    selectDocument
  }
})
```

### 在组件中使用

```vue
<script setup lang="ts">
import { useDocumentStore } from '@/stores/document'

const docStore = useDocumentStore()

onMounted(() => {
  docStore.loadDocuments()
})
</script>

<template>
  <div>
    <p>文档总数: {{ docStore.documentCount }}</p>
    <div v-for="doc in docStore.documents" :key="doc.id">
      {{ doc.filename }}
    </div>
  </div>
</template>
```

---

## 🎭 样式开发指南

### 1. 使用CSS变量

```scss
// styles/variables.scss
:root {
  --primary-color: #18a058;
  --text-color: #333;
  --border-color: #e0e0e0;
  --border-radius: 8px;
}

// 使用
.button {
  background-color: var(--primary-color);
  border-radius: var(--border-radius);
}
```

### 2. 响应式设计

```scss
.container {
  width: 100%;
  
  @media (min-width: 768px) {
    width: 750px;
  }
  
  @media (min-width: 992px) {
    width: 970px;
  }
  
  @media (min-width: 1200px) {
    width: 1170px;
  }
}
```

### 3. Scoped样式

```vue
<style scoped>
/* 只影响当前组件 */
.title {
  color: red;
}

/* 深度选择器：影响子组件 */
:deep(.child-class) {
  color: blue;
}

/* 全局选择器 */
:global(.global-class) {
  color: green;
}
</style>
```

---

## 🧪 测试

### 组件测试

```typescript
import { mount } from '@vue/test-utils'
import { describe, it, expect } from 'vitest'
import DocumentCard from '@/components/DocumentCard.vue'

describe('DocumentCard', () => {
  it('renders document info correctly', () => {
    const wrapper = mount(DocumentCard, {
      props: {
        document: {
          id: 'doc_001',
          filename: 'test.pdf',
          status: 'completed'
        }
      }
    })
    
    expect(wrapper.text()).toContain('test.pdf')
    expect(wrapper.find('.status').text()).toBe('completed')
  })
  
  it('emits delete event when button clicked', async () => {
    const wrapper = mount(DocumentCard, {
      props: { document: mockDoc }
    })
    
    await wrapper.find('.delete-btn').trigger('click')
    expect(wrapper.emitted('delete')).toBeTruthy()
  })
})
```

---

## 🚀 性能优化技巧

### 1. 虚拟滚动

```vue
<template>
  <n-virtual-list
    :items="largeList"
    :item-size="50"
    style="height: 600px"
  >
    <template #default="{ item }">
      <div class="list-item">{{ item.name }}</div>
    </template>
  </n-virtual-list>
</template>
```

### 2. 懒加载

```typescript
// 路由懒加载
const routes = [
  {
    path: '/graph',
    component: () => import('@/views/Graph.vue')
  }
]

// 组件懒加载
const AsyncComponent = defineAsyncComponent(() =>
  import('@/components/HeavyComponent.vue')
)
```

### 3. Keep-alive

```vue
<router-view v-slot="{ Component }">
  <keep-alive :include="['Graph', 'Documents']">
    <component :is="Component" />
  </keep-alive>
</router-view>
```

---

## 🔧 开发工具配置

### VS Code 推荐插件

```json
{
  "recommendations": [
    "vue.volar",
    "vue.vscode-typescript-vue-plugin",
    "dbaeumer.vscode-eslint",
    "esbenp.prettier-vscode"
  ]
}
```

### ESLint 配置

```javascript
module.exports = {
  extends: [
    'plugin:vue/vue3-recommended',
    '@vue/typescript/recommended',
    'prettier'
  ],
  rules: {
    'vue/multi-word-component-names': 'off',
    '@typescript-eslint/no-explicit-any': 'warn'
  }
}
```

---

## 📚 相关资源

- [Vue 3 官方文档](https://vuejs.org/)
- [Naive UI 组件库](https://www.naiveui.com/)
- [Cytoscape.js](https://js.cytoscape.org/)
- [Pinia 状态管理](https://pinia.vuejs.org/)
- [VueUse 工具库](https://vueuse.org/)

---

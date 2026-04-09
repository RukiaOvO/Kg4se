# 前端架构文档

POW_SE 前端基于 Vue 3 + TypeScript + Vite 构建,采用组合式 API 和模块化设计。

## 📁 目录结构

```
src/
├── main.ts                  # 应用入口
├── App.vue                  # 根组件
├── api/                     # API 服务层
│   ├── index.ts            # API 配置
│   └── services.ts         # API 方法定义
├── components/              # 公共组件
│   ├── AppContent.vue      # 内容容器
│   ├── ProcessingFloater.vue  # 处理状态浮窗
│   └── QADialog.vue        # 问答对话框
├── views/                   # 页面组件
│   ├── Dashboard.vue       # 仪表盘
│   ├── Upload.vue          # 文档上传
│   ├── Documents.vue       # 文档管理
│   ├── Graph.vue           # 图谱可视化
│   ├── Query.vue           # 知识查询
│   ├── KnowledgeCard.vue   # 知识卡片
│   ├── Status.vue          # 处理状态
│   └── Settings.vue        # 系统设置
├── layouts/                 # 布局组件
│   └── MainLayout.vue      # 主布局
├── router/                  # 路由配置
│   └── index.ts            # 路由定义
├── stores/                  # 状态管理
│   ├── app.ts              # 应用状态
│   └── processing.ts       # 处理状态
├── i18n/                    # 国际化
│   ├── index.ts            # i18n 配置
│   └── locales/            # 语言文件
│       ├── zh.json         # 中文
│       └── en.json         # 英文
├── styles/                  # 全局样式
│   └── main.scss           # 主样式文件
└── types/                   # TypeScript 类型定义
    └── cytoscape-dagre.d.ts
```

## 🎨 核心页面

### 1. Dashboard (仪表盘)

**路由**: `/`

**功能**:
- 显示系统概览
- 图谱统计数据
- 最近文档列表
- 快捷操作入口

**组件代码示例**:
```vue
<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { getGraphStats } from '@/api/services'

const stats = ref({
  documents: 0,
  concepts: 0,
  nodes: 0,
  edges: 0
})

onMounted(async () => {
  const data = await getGraphStats()
  stats.value = data
})
</script>

<template>
  <div class="dashboard">
    <n-card title="知识图谱统计">
      <n-statistic label="文档数" :value="stats.documents" />
      <n-statistic label="概念数" :value="stats.concepts" />
    </n-card>
  </div>
</template>
```

---

### 2. Upload (文档上传)

**路由**: `/upload`

**功能**:
- 拖拽上传文件
- 批量上传
- 上传进度显示
- 文件格式验证

**关键代码**:
```vue
<script setup lang="ts">
import { ref } from 'vue'
import { uploadDocument } from '@/api/services'
import { useMessage } from 'naive-ui'

const message = useMessage()
const fileList = ref([])

const handleUpload = async ({ file }) => {
  const formData = new FormData()
  formData.append('file', file.file)
  
  try {
    const result = await uploadDocument(formData)
    message.success(`上传成功: ${result.filename}`)
  } catch (error) {
    message.error(`上传失败: ${error.message}`)
  }
}
</script>
```

---

### 3. Graph (图谱可视化)

**路由**: `/graph`

**功能**:
- 交互式图谱展示(Cytoscape.js)
- 节点筛选和搜索
- 图谱布局切换
- 节点详情查看
- 文档子图查看

**核心技术**:
```typescript
import cytoscape from 'cytoscape'
import dagre from 'cytoscape-dagre'

cytoscape.use(dagre)

const cy = cytoscape({
  container: containerRef.value,
  elements: {
    nodes: graphData.value.nodes.map(n => ({
      data: { id: n.id, label: n.properties.name }
    })),
    edges: graphData.value.edges.map(e => ({
      data: { source: e.source, target: e.target }
    }))
  },
  style: [
    {
      selector: 'node',
      style: {
        'label': 'data(label)',
        'background-color': '#3b82f6'
      }
    }
  ],
  layout: { name: 'dagre' }
})
```

---

### 4. Documents (文档管理)

**路由**: `/documents`

**功能**:
- 文档列表展示
- 搜索和筛选
- 文档详情查看
- 删除文档
- 查看处理状态

---

### 5. Query (知识查询)

**路由**: `/query`

**功能**:
- 智能问答
- 历史记录
- 相关概念推荐
- 答案来源追溯

---

### 6. KnowledgeCard (知识卡片)

**路由**: `/knowledge-card`

**功能**:
- 概念列表浏览
- 概念详情查看
- 关系图谱展示
- 证据链查看

---

## 🔧 核心服务

### API 服务 (`api/services.ts`)

统一的 API 调用封装:

```typescript
import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
  timeout: 30000
})

// 请求拦截器
api.interceptors.request.use(config => {
  // 添加 token
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// 响应拦截器
api.interceptors.response.use(
  response => response.data,
  error => {
    console.error('API Error:', error)
    return Promise.reject(error)
  }
)

// API 方法
export const getGraphData = (limit: number) => 
  api.get(`/graph/visualize?limit=${limit}`)

export const uploadDocument = (formData: FormData) =>
  api.post('/uploads', formData)

export const askQuestion = (question: string) =>
  api.post('/qa/ask', { question })
```

---

### 状态管理 (Pinia)

**应用状态** (`stores/app.ts`):
```typescript
import { defineStore } from 'pinia'

export const useAppStore = defineStore('app', {
  state: () => ({
    theme: 'light',
    language: 'zh',
    sidebarCollapsed: false
  }),
  
  actions: {
    toggleTheme() {
      this.theme = this.theme === 'light' ? 'dark' : 'light'
    },
    
    setLanguage(lang: string) {
      this.language = lang
    }
  }
})
```

**处理状态** (`stores/processing.ts`):
```typescript
import { defineStore } from 'pinia'

export const useProcessingStore = defineStore('processing', {
  state: () => ({
    tasks: [],
    activeTask: null
  }),
  
  getters: {
    pendingTasks: (state) => 
      state.tasks.filter(t => t.status === 'pending')
  },
  
  actions: {
    addTask(task) {
      this.tasks.push(task)
    },
    
    updateTask(taskId, updates) {
      const task = this.tasks.find(t => t.id === taskId)
      if (task) Object.assign(task, updates)
    }
  }
})
```

---

### 路由守卫

```typescript
// router/index.ts
import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'Dashboard',
      component: () => import('@/views/Dashboard.vue')
    },
    {
      path: '/graph',
      name: 'Graph',
      component: () => import('@/views/Graph.vue')
    }
    // ... 其他路由
  ]
})

// 全局前置守卫
router.beforeEach((to, from, next) => {
  // 路由拦截逻辑
  next()
})

export default router
```

---

## 🌐 国际化

使用 vue-i18n 实现多语言支持:

```typescript
// i18n/index.ts
import { createI18n } from 'vue-i18n'
import zh from './locales/zh.json'
import en from './locales/en.json'

export default createI18n({
  legacy: false,
  locale: 'zh',
  fallbackLocale: 'en',
  messages: { zh, en }
})
```

**使用示例**:
```vue
<template>
  <h1>{{ $t('dashboard.title') }}</h1>
  <p>{{ $t('dashboard.description') }}</p>
</template>

<script setup>
import { useI18n } from 'vue-i18n'

const { t, locale } = useI18n()

const switchLanguage = () => {
  locale.value = locale.value === 'zh' ? 'en' : 'zh'
}
</script>
```

---

## 🎨 样式管理

### 主题系统

使用 CSS 变量实现主题切换:

```scss
// styles/main.scss
:root {
  --primary-color: #3b82f6;
  --bg-color: #ffffff;
  --text-color: #1f2937;
}

[data-theme="dark"] {
  --bg-color: #1f2937;
  --text-color: #f9fafb;
}
```

### Naive UI 主题定制

```typescript
import { darkTheme, lightTheme } from 'naive-ui'

const theme = computed(() => 
  isDark.value ? darkTheme : lightTheme
)

const themeOverrides = {
  common: {
    primaryColor: '#3b82f6'
  }
}
```

---

## 📱 响应式设计

使用 Tailwind CSS 和媒体查询:

```vue
<template>
  <div class="container mx-auto px-4 md:px-6 lg:px-8">
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      <!-- 响应式网格 -->
    </div>
  </div>
</template>
```

---

## 🚀 性能优化

1. **路由懒加载**:
```typescript
{
  path: '/graph',
  component: () => import('@/views/Graph.vue')
}
```

2. **组件懒加载**:
```vue
<script setup>
import { defineAsyncComponent } from 'vue'

const HeavyComponent = defineAsyncComponent(() =>
  import('./HeavyComponent.vue')
)
</script>
```

3. **虚拟滚动**(大列表):
```vue
<n-virtual-list
  :items="largeList"
  :item-size="50"
  :item-resizable="false"
>
  <template #default="{ item }">
    <div>{{ item.name }}</div>
  </template>
</n-virtual-list>
```

---

## 🧪 前端测试

```bash
# 单元测试
npm run test:unit

# E2E 测试
npm run test:e2e

# 类型检查
npm run type-check
```

---

## 📦 构建部署

```bash
# 开发环境
npm run dev

# 生产构建
npm run build

# 预览构建结果
npm run preview
```

**环境变量** (`.env`):
```env
VITE_API_URL=http://localhost:8000
VITE_APP_TITLE=POW_SE
VITE_ENABLE_MOCK=false
```

---

## 📚 相关文档

- [Vue 3 文档](https://vuejs.org/)
- [Naive UI 组件库](https://www.naiveui.com/)
- [Cytoscape.js 图谱库](https://js.cytoscape.org/)
- [Pinia 状态管理](https://pinia.vuejs.org/)
- [Vue Router 路由](https://router.vuejs.org/)

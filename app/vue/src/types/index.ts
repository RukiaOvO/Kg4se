// API 响应类型
export interface ApiResponse<T = any> {
  success: boolean
  data: T
  message?: string
  error?: string
}

// 分页参数
export interface PaginationParams {
  page?: number
  pageSize?: number
  sortBy?: string
  sortOrder?: 'asc' | 'desc'
}

// 分页响应
export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  pageSize: number
  hasMore: boolean
}

// 图谱数据相关类型
export interface GraphNodeData {
  id: string
  label: string
  type: string
  properties: Record<string, any>
  degree?: number
}

export interface GraphEdgeData {
  id: string
  source: string
  target: string
  label: string
  type: string
  properties: Record<string, any>
}

export interface GraphData {
  nodes: GraphNodeData[]
  edges: GraphEdgeData[]
  stats?: {
    nodeCount: number
    edgeCount: number
    nodeTypes: Record<string, number>
    edgeTypes: Record<string, number>
  }
}

// 文档相关类型
export interface Document {
  id: string
  filename: string
  size: number
  mimeType: string
  status: 'pending' | 'processing' | 'completed' | 'failed'
  createdAt: string
  updatedAt: string
  chunkCount?: number
  conceptCount?: number
  claimCount?: number
  themes?: Theme[]
}

export interface Theme {
  id: string
  label: string
  level: number
  memberCount: number
  summary: string
}

// 问答相关类型
export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: number
}

export interface Conversation {
  id: string
  title: string
  messages: Message[]
  createdAt: string
  updatedAt: string
}

// 知识卡片类型
export interface KnowledgeCard {
  id: string
  name: string
  description?: string
  domain?: string
  category?: string
  importance: 'low' | 'medium' | 'high'
  tags: string[]
  aliases: string[]
  relatedConcepts: string[]
  connectionCount: number
  createdAt: string
  updatedAt: string
  attributes?: Record<string, any>
}

// 设置类型
export interface AISettings {
  provider: 'openai' | 'azure' | 'ollama' | 'claude'
  apiKey?: string
  model: string
  baseUrl?: string
  temperature?: number
  maxTokens?: number
}

export interface GraphSettings {
  layout: 'dagre' | 'circle' | 'grid' | 'concentric' | 'cose'
  nodeLimit: number
  showLabels: boolean
  edgeCurvature: number
}

export interface SystemSettings {
  ai: AISettings
  graph: GraphSettings
  autoRefresh: boolean
  language: 'zh' | 'en'
  theme: 'light' | 'dark'
}

// 处理状态类型
export interface ProcessingJob {
  id: string
  documentId: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  progress: number
  message?: string
  error?: string
  startedAt: string
  completedAt?: string
  stats?: {
    chunks: number
    triplets: number
    concepts: number
    relations: number
  }
}

// 路由元信息类型
export interface RouteMeta {
  title: string
  requiresAuth?: boolean
  roles?: string[]
  icon?: string
  breadcrumb?: boolean
  keepAlive?: boolean
}
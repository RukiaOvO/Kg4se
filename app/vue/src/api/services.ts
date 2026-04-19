import api from './index'

// Expose API base for constructing absolute URLs (e.g., file preview)
export const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

// Types
export interface DashboardStats {
  total_nodes: number
  total_edges: number
  node_labels: Record<string, number>
  edge_types: Record<string, number>
}

export interface UploadResponse {
  documentId: string
  filename: string
  checksum: string
  status: string
  jobId?: string
  message?: string
  path?: string
  sourceUrl?: string
}

export interface IngestionResponse {
  job_id: string
  status: string
}

export interface GraphNode {
  id: string
  labels: string[]
  properties: Record<string, any>
}

export interface GraphEdge {
  id: string
  type: string
  source: string
  target: string
  properties: Record<string, any>
}

export interface GraphData {
  nodes: GraphNode[]
  edges: GraphEdge[]
}

export interface JobStatus {
  jobId?: string
  documentId?: string
  status: string
  progress?: number
  message?: string
  error?: string
  stats?: {
    chunks: number
    triplets: number
    concepts: number
    textLength?: number
  }
  ai_mode?: boolean
  ai_stats?: {
    total_tokens?: number
    prompt_tokens?: number
    completion_tokens?: number
    model?: string
  }
  insights?: string[]
}

export interface AIProvider {
  id: string
  name: string
  default_model: string
  requires_api_key: boolean
}

export interface AISettings {
  ai_provider: string
  ai_api_key?: string
  ai_model?: string
  ai_base_url?: string
  // 旧配置（向后兼容）
  openai_api_key?: string
  openai_model?: string
  openai_base_url?: string
  ollama_base_url?: string
  ollama_model?: string
}

export interface Settings extends AISettings {
  neo4j_uri: string
  neo4j_user: string
  redis_url: string
  [key: string]: any
}

// Dashboard
export const getDashboardStats = (): Promise<DashboardStats> => 
  api.get('/graph/stats')

// Upload - 统一使用 /uploads/process 接口，自动处理
export const uploadFile = (
  file: File, 
  options?: {
    enable_ai_segmentation?: boolean
    userPrompt?: string
    optimizePrompt?: boolean
    rootTopic?: string
  }
): Promise<UploadResponse> => {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('auto_process', 'true')
  
  // 始终发送 enable_ai_segmentation 字段，避免后端使用默认值
  formData.append('enable_ai_segmentation', String(options?.enable_ai_segmentation === true))
  
  if (options?.enable_ai_segmentation) {
    if (options.userPrompt) {
      formData.append('user_prompt', options.userPrompt)
    }
    if (options.optimizePrompt !== undefined) {
      formData.append('optimize_prompt', String(options.optimizePrompt))
    }
  } else {
    // AI 模式关闭时也发送 optimize_prompt 默认值
    formData.append('optimize_prompt', 'true')
  }
  
  if (options?.rootTopic) {
    formData.append('root_topic', options.rootTopic)
  }
  
  return api.post('/uploads/process', formData)
}

export const uploadText = (
  content: string, 
  title?: string, 
  autoProcess: boolean = true,
  options?: {
    enable_ai_segmentation?: boolean
    userPrompt?: string
    optimizePrompt?: boolean
    rootTopic?: string
  }
): Promise<UploadResponse> => {
  const payload: any = { 
    content, 
    title, 
    auto_process: autoProcess,
    // 始终发送 enable_ai_segmentation 字段
    enable_ai_segmentation: options?.enable_ai_segmentation === true,
    optimize_prompt: options?.optimizePrompt !== undefined ? options.optimizePrompt : true
  }
  
  if (options?.enable_ai_segmentation && options.userPrompt) {
    payload.user_prompt = options.userPrompt
  }
  
  if (options?.rootTopic) {
    payload.root_topic = options.rootTopic
  }
  
  return api.post('/uploads/text', payload)
}

export const uploadUrl = (
  url: string, 
  title?: string, 
  autoProcess: boolean = true,
  options?: {
    enable_ai_segmentation?: boolean
    userPrompt?: string
    optimizePrompt?: boolean
    rootTopic?: string
  }
): Promise<UploadResponse> => {
  const payload: any = { 
    url, 
    title, 
    auto_process: autoProcess,
    // 始终发送 enable_ai_segmentation 字段
    enable_ai_segmentation: options?.enable_ai_segmentation === true,
    optimize_prompt: options?.optimizePrompt !== undefined ? options.optimizePrompt : true
  }
  
  if (options?.enable_ai_segmentation && options.userPrompt) {
    payload.user_prompt = options.userPrompt
  }
  
  if (options?.rootTopic) {
    payload.root_topic = options.rootTopic
  }
  
  return api.post('/uploads/url', payload)
}

export const startIngestion = (documentId: string): Promise<IngestionResponse> => 
  api.post(`/ingest/${documentId}`)

// Documents Management
export interface DocumentListResponse {
  total: number
  documents: Array<{
    id: string
    filename: string
    kind: string
    size: number
    created_at: string
    updated_at: string
    checksum: string
    chunk_count: number
    concept_count: number
    claim_count: number
    processing_status: string
  }>
}

export interface DocumentDetail {
  id: string
  filename: string
  kind: string
  size: number
  created_at: string
  updated_at: string
  checksum: string
  mime: string
  meta: Record<string, any>
  statistics: {
    chunk_count: number
    concept_count: number
    claim_count: number
    relation_count: number
  }
  themes: Array<{
    id: string
    label: string
    level: number
    member_count: number
    summary: string
  }>
  processing_status: string
}

export const listDocuments = (skip: number = 0, limit: number = 50, sortBy: string = 'created_at'): Promise<DocumentListResponse> =>
  api.get('/uploads', {
    params: {
      skip,
      limit,
      sort_by: sortBy,
      _: Date.now()  // 添加时间戳参数防止浏览器缓存
    }
  })

export const getDocumentDetail = (documentId: string): Promise<DocumentDetail> =>
  api.get(`/uploads/${documentId}`)

// Get file download/preview URL for embedding in viewer
export const getDocumentFileUrl = (documentId: string): string => `${API_BASE}/uploads/${documentId}/file`

export const deleteDocument = (documentId: string): Promise<void> =>
  api.delete(`/uploads/${documentId}`)

// Graph
export const getGraphData = (limit: number = 500): Promise<any> =>
  api.get('/graph/visualize', {
    params: {
      limit: Math.min(limit, 10000)
    }
  })

export const getGraphDataByType = (nodeType: string, limit: number = 500): Promise<any> =>
  api.get('/graph/visualize', {
    params: {
      limit: Math.min(limit, 5000),
      node_type: nodeType
    }
  })

// Graph by document
export const getDocumentGraph = (documentId: string, depth: number = 2, limit: number = 500, edgeLimit: number = 1000): Promise<any> =>
  api.get(`/graph/documents/${documentId}/graph`, {
    params: {
      depth: Math.max(1, Math.min(depth, 5)),
      limit: Math.min(limit, 10000),
      edge_limit: Math.min(edgeLimit, 50000)
    }
  })

// Query
export const executeCypherQuery = (cypher: string): Promise<any> => 
  api.get('/graph/query', { params: { cypher } })

export const getNodes = (label: string | null = null, limit: number = 100): Promise<GraphNode[]> => {
  const params: Record<string, any> = { limit }
  if (label) {
    params.label = label
  }
  return api.get('/graph/nodes', { params })
}

export const getEdges = (relType: string | null = null, limit: number = 100): Promise<GraphEdge[]> => {
  const params: Record<string, any> = { limit }
  if (relType) {
    params.rel_type = relType
  }
  return api.get('/graph/edges', { params })
}

// Status - 统一使用 /uploads/status 接口
export const getJobStatus = (jobId: string): Promise<JobStatus> => 
  api.get(`/uploads/status/${jobId}`)

// Settings
export const getAIProviders = (): Promise<{ providers: AIProvider[] }> => 
  api.get('/settings/ai-providers')

export const getSettings = (): Promise<Settings> => 
  api.get('/settings/')

export const updateAISettings = (settings: AISettings): Promise<any> => 
  api.post('/settings/ai', settings)

export const testAIConnection = (settings: AISettings): Promise<any> => 
  api.post('/settings/test-connection', settings)

export const getOllamaModels = (): Promise<{ success: boolean; models: string[]; message?: string }> => 
  api.get('/settings/ollama/models')

// ========== Graph CRUD Operations ==========

// Node CRUD
export interface NodeCreate {
  labels: string[]
  properties: Record<string, any>
}

export interface NodeUpdate {
  labels?: string[]
  properties: Record<string, any>
  remove_properties?: string[]
}

export const createNode = (data: NodeCreate): Promise<GraphNode> => 
  api.post('/graph/nodes', data)

export const getNode = (nodeId: string): Promise<GraphNode> => 
  api.get(`/graph/nodes/${nodeId}`)

export const updateNode = (nodeId: string, data: NodeUpdate): Promise<GraphNode> => 
  api.put(`/graph/nodes/${nodeId}`, data)

export const deleteNode = (nodeId: string, force: boolean = false): Promise<void> => 
  api.delete(`/graph/nodes/${nodeId}`, { params: { force } })

// Edge CRUD
export interface EdgeCreate {
  source: string
  target: string
  type: string
  properties?: Record<string, any>
}

export interface EdgeUpdate {
  type?: string
  properties?: Record<string, any>
  remove_properties?: string[]
}

export const createEdge = (data: EdgeCreate): Promise<GraphEdge> => 
  api.post('/graph/edges', data)

export const updateEdge = (sourceId: string, targetId: string, relType: string, data: EdgeUpdate): Promise<GraphEdge> => 
  api.put(`/graph/edges/${sourceId}/${targetId}/${relType}`, data)

export const deleteEdge = (sourceId: string, targetId: string, relType: string): Promise<void> => 
  api.delete(`/graph/edges/${sourceId}/${targetId}/${relType}`)

// ========== Q&A Service ==========

export interface Message {
  role: 'user' | 'assistant'
  content: string
}

export type QAMode = 'graphrag' | 'rag' | 'llm'

export interface AskRequest {
  question: string
  conversation_history?: Message[]
  mode?: QAMode
}

export interface AskResponse {
  success: boolean
  answer: string
  used_context: boolean
  context_snippet?: string
  error?: string
}

export const askQuestion = (request: AskRequest): Promise<AskResponse> =>
  api.post('/qa/ask', request)

export const checkQAHealth = (): Promise<{ status: string; provider: string; has_ai_client: boolean }> =>
  api.get('/qa/health')

// ========== Evaluation Service ==========

export interface GraphQualityResult {
  structural_quality: {
    node_count: number
    edge_count: number
    avg_degree: number
    modularity: number
    density: number
    connected_components: number
  }
  content_quality: {
    sample_size: number
    valid_ratio: number
    avg_confidence: number
    predicate_diversity: number
    predicate_normalized_ratio: number
  }
  construction_efficiency: {
    documents_processed: number
    total_build_time: number
    tokens_consumed: number
    throughput: number
  }
  overall_score: number
  recommendations: string[]
}

export interface AnswerEvaluationResult {
  success: boolean
  question: string
  graphrag_answer: string
  rag_answer: string
  llm_answer: string
  evaluation: {
    graphrag: {
      automatic: {
        semantic_similarity: number
        word_overlap: number
      }
      overall_score: number
    }
    rag: {
      automatic: {
        semantic_similarity: number
        word_overlap: number
      }
      overall_score: number
    }
    llm: {
      automatic: {
        semantic_similarity: number
        word_overlap: number
      }
      overall_score: number
    }
    statistics: {
      graphrag_score: number
      rag_score: number
      llm_score: number
    }
  }
  improvement: {
    graphrag_over_rag_percent: number
    graphrag_over_llm_percent: number
    rag_over_llm_percent: number
  }
}

export const evaluateGraphQuality = (): Promise<GraphQualityResult> =>
  api.get('/evaluation/graph')

export const evaluateAnswerQuality = (question: string, expectedAnswer?: string): Promise<AnswerEvaluationResult> =>
  api.post('/evaluation/answer', {
    question,
    expected_answer: expectedAnswer
  })


import api from './index'

// Expose API base for constructing absolute URLs (e.g., file preview)
export const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

// Types
export interface DashboardStats {
  totalDocuments: number
  totalConcepts: number
  totalChunks: number
  totalEntities: number
  totalClaims: number
  totalRelations: number
  skeletonNodeCount: number
  communityCount: number
  node_labels: Record<string, number>
  edge_types: Record<string, number>
  recentDocuments: Array<{
    id: string
    filename: string
    createdAt: string
    kind: string
  }>
  topConcepts: Array<{
    name: string
    domain: string
    connections: number
  }>
  relationTypes: Array<{
    type: string
    count: number
  }>
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
    entities: number
    claims: number
    themes: number
    relationships: number
    execution_time?: number
    textLength?: number
  }
  quality_metrics?: {
    isolated_node_ratio?: number
    avg_degree?: number
  }
  stage_metrics?: Record<string, any>
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
  api.get('/graph/stats', { params: { _: Date.now() } })

// Upload - 统一使用 /uploads/process 接口，自动处理
export const uploadFile = (
  file: File
): Promise<UploadResponse> => {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('auto_process', 'true')
  
  return api.post('/uploads/process', formData)
}

export const uploadText = (
  content: string, 
  title?: string, 
  autoProcess: boolean = true
): Promise<UploadResponse> => {
  const payload: any = { 
    content, 
    title, 
    auto_process: autoProcess
  }
  
  return api.post('/uploads/text', payload)
}

export const uploadUrl = (
  url: string, 
  title?: string, 
  autoProcess: boolean = true
): Promise<UploadResponse> => {
  const payload: any = { 
    url, 
    title, 
    auto_process: autoProcess
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
    theme_count: number
    processing_status: string
  }>
  stats?: {
    total: number
    completed: number
    pending: number
  }
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
    theme_count: number
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

export const listDocuments = (
  skip: number = 0, 
  limit: number = 50, 
  sortBy: string = 'created_at',
  status: string = '',
  kind: string = '',
  keyword: string = ''
): Promise<DocumentListResponse> =>
  api.get('/uploads', {
    params: {
      skip,
      limit,
      sort_by: sortBy,
      status,
      kind,
      keyword,
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
export const getGraphData = (limit: number = 500, signal?: AbortSignal): Promise<any> =>
  api.get('/graph/visualize', {
    params: {
      limit,
      edge_limit: Math.min(limit * 10, 100000)
    },
    timeout: 120000,
    signal
  })

export const getGraphDataByType = (nodeType: string, limit: number = 500, signal?: AbortSignal): Promise<any> =>
  api.get('/graph/visualize', {
    params: {
      limit,
      edge_limit: Math.min(limit * 10, 100000),
      node_type: nodeType
    },
    timeout: 120000,
    signal
  })

// Graph by document
export const getDocumentGraph = (documentId: string, depth: number = 2, limit: number = 500, signal?: AbortSignal): Promise<any> =>
  api.get(`/graph/documents/${documentId}/graph`, {
    params: {
      depth: Math.max(1, Math.min(depth, 5)),
      limit,
      edge_limit: Math.min(limit * 10, 100000)
    },
    timeout: 120000,
    signal
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

export const askQuestionStream = (
  request: AskRequest,
  onToken: (token: string) => void,
  onStatus: (status: string) => void,
  onDone: (result: { answer: string; used_context: boolean; context_snippet?: string }) => void,
  onError: (error: string) => void
): AbortController => {
  const controller = new AbortController()

  fetch(`${API_BASE}/qa/ask/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
    signal: controller.signal
  }).then(async (response) => {
    if (!response.ok) {
      onError(`请求失败: ${response.status}`)
      return
    }
    const reader = response.body?.getReader()
    if (!reader) {
      onError('响应流不可用')
      return
    }
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        const trimmed = line.trim()
        if (!trimmed || !trimmed.startsWith('data: ')) continue
        try {
          const event = JSON.parse(trimmed.slice(6))
          if (event.type === 'token') {
            onToken(event.data)
          } else if (event.type === 'status') {
            onStatus(event.data)
          } else if (event.type === 'done') {
            onDone(event.data)
          } else if (event.type === 'error') {
            onError(event.data)
          }
        } catch { /* skip malformed lines */ }
      }
    }
  }).catch((err) => {
    if (err.name !== 'AbortError') {
      onError(err.message || '网络错误')
    }
  })

  return controller
}

export const checkQAHealth = (): Promise<{ status: string; provider: string; has_ai_client: boolean }> =>
  api.get('/qa/health')

// ========== Evaluation Service ==========

export interface LLMJudgeResult {
  accuracy: number
  completeness: number
  relevance: number
  expertise: number
  explainability: number
  overall: number
  comment: string
  sample_std?: {
    accuracy: number
    completeness: number
    relevance: number
    expertise: number
    explainability: number
  }
}

export interface AutomaticEvaluation {
  semantic_similarity: number
  length_adequacy: number
  word_overlap: number
  keyword_f1: number
  rouge_l: number
  score: number
}

export interface MethodEvaluation {
  predicted: string
  expected: string
  context: string
  automatic: AutomaticEvaluation
  info_credibility: number
  llm_judge: LLMJudgeResult | null
  overall_score: number
  samples: any[] | null
}

export interface AnswerEvaluationResult {
  success: boolean
  question: string
  graphrag_answer: string
  rag_answer: string
  llm_answer: string
  evaluation: {
    graphrag: MethodEvaluation
    rag: MethodEvaluation
    llm: MethodEvaluation
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
  trace?: {
    graphrag: {
      context_snippet: string | null
      used_context: boolean
      entities: Array<{ name: string }>
    }
    rag: {
      context_snippet: string | null
      used_context: boolean
      vector_results: Array<{
        source: string
        similarity: number
        text: string
      }>
    }
    llm: {
      context_snippet: string | null
      used_context: boolean
      note?: string
    }
  }
}

export const evaluateAnswerQuality = (question: string, expectedAnswer?: string): Promise<AnswerEvaluationResult> =>
  api.post('/evaluation/answer', {
    question,
    expected_answer: expectedAnswer
  }, { timeout: 180000 })


// ========== Benchmark Dataset APIs ==========

export interface BenchmarkDataset {
  id: string
  filename: string
  name: string
  version: string
  description: string
  question_count: number
  categories: string[]
  difficulty_levels: string[]
}

export interface BenchmarkQuestion {
  id: string
  question: string
  expected_answer: string
  category: string
  difficulty: string
  keywords: string[]
}

export interface BenchmarkDatasetDetail {
  name: string
  version: string
  description: string
  categories: string[]
  difficulty_levels: string[]
  questions: BenchmarkQuestion[]
}

export interface DatasetEvaluationResult {
  success: boolean
  dataset_id: string
  dataset_name: string
  filters: {
    category: string | null
    difficulty: string | null
  }
  questions_evaluated: number
  results: any
}

export const listBenchmarkDatasets = (): Promise<{ datasets: BenchmarkDataset[] }> =>
  api.get('/evaluation/datasets')

export const getBenchmarkDataset = (datasetId: string): Promise<{ success: boolean; dataset: BenchmarkDatasetDetail }> =>
  api.get(`/evaluation/datasets/${datasetId}`)

export const evaluateBenchmarkDataset = (
  datasetId: string,
  options?: {
    category?: string
    difficulty?: string
    limit?: number
    num_samples?: number
    enable_pairwise?: boolean
  }
): Promise<DatasetEvaluationResult> => {
  const params = new URLSearchParams()
  if (options?.category) params.append('category', options.category)
  if (options?.difficulty) params.append('difficulty', options.difficulty)
  if (options?.limit) params.append('limit', String(options.limit))
  if (options?.num_samples) params.append('num_samples', String(options.num_samples))
  if (options?.enable_pairwise !== undefined) params.append('enable_pairwise', String(options.enable_pairwise))
  
  return api.post(`/evaluation/datasets/${datasetId}/evaluate?${params.toString()}`, {}, { timeout: 600000 })
}


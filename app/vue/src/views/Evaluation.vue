<template>
  <div class="evaluation-page">
    <div class="page-header">
      <div class="header-content">
        <h1 class="page-title">质量分析</h1>
        <p class="page-subtitle">LLM Answer Quality Analysis</p>
      </div>
    </div>

    <n-tabs v-model:value="activeTab" type="line" class="tab-container" :default-value="'answer'">
      <n-tab-pane name="answer" tab="LLM回答质量分析">
        <div class="tab-content">
          <div class="analysis-card">
            <div class="card-header">
              <n-icon size="20"><document-text-outline /></n-icon>
              <h3>回答质量对比评估</h3>
            </div>

            <div class="question-input">
              <n-input
                v-model:value="question"
                type="textarea"
                :rows="3"
                placeholder="请输入要评估的问题..."
                @keyup.enter="evaluateAnswer"
              />
              <div class="expected-answer-input">
                <n-input
                  v-model:value="expectedAnswer"
                  type="textarea"
                  :rows="2"
                  placeholder="可选：输入期望答案/标准答案（用于自动评估，留空则仅使用LLM评分）"
                />
              </div>
              <n-button type="primary" @click="evaluateAnswer" :loading="loadingAnswer">
                <template #icon>
                  <n-icon><send-outline /></n-icon>
                </template>
                开始评估
              </n-button>
            </div>

            <div v-if="answerEvaluation" class="answer-results">
              <n-alert v-if="answerEvaluation.evaluation?.graphrag?.evaluation_mode === 'llm_only'" type="warning" :bordered="false" style="margin-bottom: 16px;">
                ⚠️ {{ answerEvaluation.evaluation.graphrag.warning }}
              </n-alert>
              <div class="radar-section">
                <div class="section-title">
                  <n-icon size="20"><analytics-outline /></n-icon>
                  <h4>LLM-as-a-Judge 五维评分对比</h4>
                </div>
                <div class="radar-layout">
                  <div class="radar-left">
                    <div class="formula-subtitle">
                      <span class="sub-label">综合评分公式</span>
                      <code>S = 0.4 × A<sub>自动评估</sub> + 0.6 × L<sub>LLM评分</sub></code>
                    </div>
                    <div class="radar-chart-card">
                      <div class="radar-chart-inner">
                        <v-chart :option="getCombinedRadarOption" autoresize class="combined-radar-chart" />
                        <div class="radar-legend-vertical">
                          <div class="rv-item graphrag-legend">
                            <span class="rv-dot"></span>
                            <span class="rv-label">GraphRAG</span>
                          </div>
                          <div class="rv-item rag-legend">
                            <span class="rv-dot"></span>
                            <span class="rv-label">RAG</span>
                          </div>
                          <div class="rv-item llm-legend">
                            <span class="rv-dot"></span>
                            <span class="rv-label">LLM</span>
                          </div>
                        </div>
                      </div>
                    </div>
                    <div class="total-score-row">
                      <div class="total-item graphrag-total">
                        <span class="total-label">GraphRAG</span>
                        <span class="total-calc">0.4&times;{{ getAutoScore('graphrag') }} + 0.6&times;{{ getLlmScore('graphrag') }}</span>
                        <span class="total-value">{{ (answerEvaluation.evaluation.statistics.graphrag_score * 100).toFixed(2) }}</span>
                      </div>
                      <div class="total-item rag-total">
                        <span class="total-label">RAG</span>
                        <span class="total-calc">0.4&times;{{ getAutoScore('rag') }} + 0.6&times;{{ getLlmScore('rag') }}</span>
                        <span class="total-value">{{ (answerEvaluation.evaluation.statistics.rag_score * 100).toFixed(2) }}</span>
                      </div>
                      <div class="total-item llm-total">
                        <span class="total-label">LLM</span>
                        <span class="total-calc">0.4&times;{{ getAutoScore('llm') }} + 0.6&times;{{ getLlmScore('llm') }}</span>
                        <span class="total-value">{{ (answerEvaluation.evaluation.statistics.llm_score * 100).toFixed(2) }}</span>
                      </div>
                    </div>
                    <div class="comparison-table">
                      <table>
                        <thead>
                          <tr>
                            <th>对比项</th>
                            <th>提升幅度</th>
                          </tr>
                        </thead>
                        <tbody>
                          <tr>
                            <td><span class="method-dot graphrag"></span>GraphRAG vs RAG</td>
                            <td :class="answerEvaluation.improvement.graphrag_over_rag_percent > 0 ? 'positive' : 'negative'">{{ answerEvaluation.improvement.graphrag_over_rag_percent > 0 ? '+' : '' }}{{ answerEvaluation.improvement.graphrag_over_rag_percent.toFixed(1) }}%</td>
                          </tr>
                          <tr>
                            <td><span class="method-dot rag"></span>GraphRAG vs LLM</td>
                            <td :class="answerEvaluation.improvement.graphrag_over_llm_percent > 0 ? 'positive' : 'negative'">{{ answerEvaluation.improvement.graphrag_over_llm_percent > 0 ? '+' : '' }}{{ answerEvaluation.improvement.graphrag_over_llm_percent.toFixed(1) }}%</td>
                          </tr>
                          <tr>
                            <td><span class="method-dot llm"></span>RAG vs LLM</td>
                            <td :class="answerEvaluation.improvement.rag_over_llm_percent > 0 ? 'positive' : 'negative'">{{ answerEvaluation.improvement.rag_over_llm_percent > 0 ? '+' : '' }}{{ answerEvaluation.improvement.rag_over_llm_percent.toFixed(1) }}%</td>
                          </tr>
                        </tbody>
                      </table>
                    </div>
                  </div>

                  <div class="radar-right">
                    <n-tabs type="line" animated size="small" class="eval-tabs">
                      <n-tab-pane name="auto" tab="自动评估标准">
                        <div class="tab-content">
                          <div class="tab-subtitle">基于文本相似度的自动化指标</div>
                          <div class="formula-list">
                            <div class="formula-list-item">
                              <span class="fl-label">语义相似度</span>
                              <div class="fl-value"><code>Cosine(v<sub>1</sub>, v<sub>2</sub>)</code></div>
                              <span class="fl-desc">向量余弦相似度</span>
                            </div>
                            <div class="formula-list-item">
                              <span class="fl-label">词重叠率</span>
                              <div class="fl-value"><code>|A &cap; B| / |A &cup; B|</code></div>
                              <span class="fl-desc">Jaccard系数</span>
                            </div>
                            <div class="formula-list-item">
                              <span class="fl-label">关键词覆盖率</span>
                              <div class="fl-value"><code>|K<sub>pred</sub> &cap; K<sub>exp</sub>| / |K<sub>exp</sub>|</code></div>
                              <span class="fl-desc">信息完整性</span>
                            </div>
                            <div class="formula-list-item">
                              <span class="fl-label">ROUGE-L</span>
                              <div class="fl-value"><code>LCS F-measure</code></div>
                              <span class="fl-desc">语序匹配度</span>
                            </div>
                          </div>
                          <div class="formula-total">
                            <span class="ft-label">自动评估总分 A</span>
                            <div class="ft-value"><code>A = 0.3&times;Sim + 0.15&times;WOR + 0.3&times;KC + 0.25&times;RL</code></div>
                          </div>
                          <div class="tab-score-section">
                            <div class="tss-header">各方法自动评估分数 A</div>
                            <div class="tss-body">
                              <div class="tss-row">
                                <span class="tss-dot" style="background:#52c41a"></span>
                                <span class="tss-name">GraphRAG</span>
                                <span class="tss-score" style="color:#52c41a">{{ getAutoScore('graphrag') }}</span>
                              </div>
                              <div class="tss-row">
                                <span class="tss-dot" style="background:#faad14"></span>
                                <span class="tss-name">RAG</span>
                                <span class="tss-score" style="color:#faad14">{{ getAutoScore('rag') }}</span>
                              </div>
                              <div class="tss-row">
                                <span class="tss-dot" style="background:#1890ff"></span>
                                <span class="tss-name">LLM</span>
                                <span class="tss-score" style="color:#1890ff">{{ getAutoScore('llm') }}</span>
                              </div>
                            </div>
                          </div>
                        </div>
                      </n-tab-pane>
                      <n-tab-pane name="llm" tab="LLM 评分标准">
                        <div class="tab-content">
                          <div class="tab-subtitle">LLM-as-a-Judge 五维度评估</div>
                          <div class="dimension-grid">
                            <div class="dg-item" v-for="dim in llmJudgeDimensions" :key="dim">
                              <span class="dg-name">{{ getDimLabel(dim) }}</span>
                              <span class="dg-desc">{{ getDimDesc(dim) }}</span>
                            </div>
                          </div>
                          <div class="score-scale">
                            <div class="ss-header">评分等级（1-5分）</div>
                            <div class="ss-body">
                              <div class="ss-row" v-for="(item, idx) in scoreScaleList" :key="idx">
                                <span class="ss-score" :style="{ color: item.color }">{{ item.score }}</span>
                                <span class="ss-level">{{ item.level }}</span>
                                <span class="ss-desc">{{ item.desc }}</span>
                              </div>
                            </div>
                          </div>
                          <div class="formula-total formula-total-blue">
                            <span class="ft-label">LLM评分 L</span>
                            <div class="ft-value"><code>L = &Sigma;(dim<sub>i</sub>) / 5, dim &isin; [1,5]</code></div>
                          </div>
                          <div class="tab-score-section">
                            <div class="tss-header">各方法LLM评分 L</div>
                            <div class="tss-body">
                              <div class="tss-row">
                                <span class="tss-dot" style="background:#52c41a"></span>
                                <span class="tss-name">GraphRAG</span>
                                <span class="tss-score" style="color:#52c41a">{{ getLlmScore('graphrag') }}</span>
                              </div>
                              <div class="tss-row">
                                <span class="tss-dot" style="background:#faad14"></span>
                                <span class="tss-name">RAG</span>
                                <span class="tss-score" style="color:#faad14">{{ getLlmScore('rag') }}</span>
                              </div>
                              <div class="tss-row">
                                <span class="tss-dot" style="background:#1890ff"></span>
                                <span class="tss-name">LLM</span>
                                <span class="tss-score" style="color:#1890ff">{{ getLlmScore('llm') }}</span>
                              </div>
                            </div>
                          </div>
                        </div>
                      </n-tab-pane>
                    </n-tabs>
                  </div>
                </div>
              </div>

              <n-divider />

              <div class="answers-section">
                <div class="section-title">
                  <n-icon size="20"><document-text-outline /></n-icon>
                  <h4>回答对比</h4>
                </div>
                <div class="answers-grid">
                  <div class="answer-card graphrag">
                    <div class="answer-header">
                      <n-tag type="success" bordered>GraphRAG</n-tag>
                      <span class="score-badge">{{ (answerEvaluation.evaluation.statistics.graphrag_score * 100).toFixed(1) }}</span>
                    </div>
                    <div class="answer-content">{{ answerEvaluation.graphrag_answer }}</div>
                  </div>

                  <div class="answer-card rag">
                    <div class="answer-header">
                      <n-tag type="warning" bordered>RAG</n-tag>
                      <span class="score-badge">{{ (answerEvaluation.evaluation.statistics.rag_score * 100).toFixed(1) }}</span>
                    </div>
                    <div class="answer-content">{{ answerEvaluation.rag_answer }}</div>
                  </div>

                  <div class="answer-card llm">
                    <div class="answer-header">
                      <n-tag type="info" bordered>LLM</n-tag>
                      <span class="score-badge">{{ (answerEvaluation.evaluation.statistics.llm_score * 100).toFixed(1) }}</span>
                    </div>
                    <div class="answer-content">{{ answerEvaluation.llm_answer }}</div>
                  </div>
                </div>
              </div>

              <n-divider />

              <div class="trace-section">
                <div class="section-title">
                  <n-icon size="20"><git-network-outline /></n-icon>
                  <h4>信息溯源</h4>
                </div>
                <div class="trace-grid">
                  <div class="trace-card graphrag-trace">
                    <div class="trace-header">
                      <n-tag type="success" bordered>GraphRAG</n-tag>
                      <span class="trace-badge" v-if="answerEvaluation.trace?.graphrag?.used_context">已使用知识图谱</span>
                      <span class="trace-badge disabled" v-else>未使用知识图谱</span>
                    </div>
                    <n-scrollbar style="max-height: 160px;">
                      <div class="trace-content">
                        <div class="trace-entity-list" v-if="answerEvaluation.trace?.graphrag?.entities?.length > 0">
                          <div class="trace-subtitle">检索实体 ({{ answerEvaluation.trace.graphrag.entities.length }})</div>
                          <div class="entity-tags">
                            <n-tag 
                              v-for="(entity, idx) in answerEvaluation.trace.graphrag.entities" 
                              :key="idx" 
                              type="success" 
                              size="small" 
                              :bordered="false"
                            >
                              {{ entity.name }}
                            </n-tag>
                          </div>
                        </div>
                        <div class="trace-context" v-if="answerEvaluation.trace?.graphrag?.context_snippet">
                          <div class="trace-subtitle">知识图谱上下文</div>
                          <pre class="context-text">{{ answerEvaluation.trace.graphrag.context_snippet }}</pre>
                        </div>
                        <n-empty v-if="!answerEvaluation.trace?.graphrag?.entities?.length && !answerEvaluation.trace?.graphrag?.context_snippet" description="无知识图谱信息" size="small" />
                      </div>
                    </n-scrollbar>
                  </div>

                  <div class="trace-card rag-trace">
                    <div class="trace-header">
                      <n-tag type="warning" bordered>RAG</n-tag>
                      <span class="trace-badge" v-if="answerEvaluation.trace?.rag?.used_context">已检索文档</span>
                      <span class="trace-badge disabled" v-else>未检索到文档</span>
                    </div>
                    <n-scrollbar style="max-height: 160px;">
                      <div class="trace-content">
                        <div class="trace-vector-list" v-if="answerEvaluation.trace?.rag?.vector_results?.length > 0">
                          <div class="trace-subtitle">检索文档片段 ({{ answerEvaluation.trace.rag.vector_results.length }})</div>
                          <div class="vector-results">
                            <div 
                              v-for="(item, idx) in answerEvaluation.trace.rag.vector_results" 
                              :key="idx" 
                              class="vector-item"
                            >
                              <div class="vector-item-header">
                                <span class="vector-source">{{ item.source }}</span>
                                <n-tag size="small" type="warning">相似度: {{ (item.similarity * 100).toFixed(1) }}%</n-tag>
                              </div>
                              <div class="vector-item-text">{{ item.text.substring(0, 150) }}...</div>
                            </div>
                          </div>
                        </div>
                        <div class="trace-context" v-if="answerEvaluation.trace?.rag?.context_snippet">
                          <div class="trace-subtitle">文档上下文</div>
                          <pre class="context-text">{{ answerEvaluation.trace.rag.context_snippet }}</pre>
                        </div>
                        <n-empty v-if="!answerEvaluation.trace?.rag?.vector_results?.length && !answerEvaluation.trace?.rag?.context_snippet" description="无检索信息" size="small" />
                      </div>
                    </n-scrollbar>
                  </div>

                  <div class="trace-card llm-trace">
                    <div class="trace-header">
                      <n-tag type="info" bordered>LLM</n-tag>
                      <span class="trace-badge disabled">无外部信息来源</span>
                    </div>
                    <div class="trace-content llm-placeholder">
                      <n-empty description="纯LLM回答，无外部信息来源" size="small" />
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <n-empty v-else-if="!loadingAnswer" description="输入问题后点击开始评估，系统将对比三种回答方式的质量" />
            <n-spin v-else size="large" />
          </div>
        </div>
      </n-tab-pane>
    </n-tabs>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { NButton, NIcon, NInput, NTabs, NTabPane, NSpin, NEmpty, NTag, NScrollbar, NDivider, NAlert } from 'naive-ui'
import { DocumentTextOutline, SendOutline, GitNetworkOutline, AnalyticsOutline } from '@vicons/ionicons5'
import { evaluateAnswerQuality } from '@/api/services'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { RadarChart } from 'echarts/charts'
import { TooltipComponent, LegendComponent } from 'echarts/components'

use([CanvasRenderer, RadarChart, TooltipComponent, LegendComponent])

const activeTab = ref('answer')
const loadingAnswer = ref(false)
const answerEvaluation = ref(null)
const question = ref('')
const expectedAnswer = ref('')

const llmJudgeDimensions = ['accuracy', 'completeness', 'relevance', 'expertise', 'explainability']

const dimLabels = {
  accuracy: '准确性',
  completeness: '完整性',
  relevance: '相关性',
  expertise: '专业性',
  explainability: '可解释性'
}

const getCombinedRadarOption = computed(() => {
  if (!answerEvaluation.value?.evaluation) return { series: [] }
  
  const evalData = answerEvaluation.value.evaluation
  
  const getScores = (method) => {
    if (!evalData[method]?.llm_judge) return llmJudgeDimensions.map(() => 0)
    return llmJudgeDimensions.map(dim => evalData[method].llm_judge[dim] ?? 0)
  }
  
  return {
    tooltip: {
      trigger: 'item',
      confine: true
    },
    legend: {
      show: false
    },
    radar: {
      indicator: llmJudgeDimensions.map(dim => ({ name: dimLabels[dim], max: 5 })),
      shape: 'polygon',
      splitNumber: 5,
      center: ['45%', '50%'],
      radius: '65%',
      axisName: {
        color: '#444',
        fontSize: 12,
        fontWeight: 500
      },
      splitLine: {
        lineStyle: { color: 'rgba(0,0,0,0.08)' }
      },
      splitArea: {
        areaStyle: {
          color: ['rgba(82,196,26,0.02)', 'rgba(250,173,20,0.02)', 'rgba(24,144,255,0.02)']
        }
      },
      axisLine: {
        lineStyle: { color: 'rgba(0,0,0,0.08)' }
      }
    },
    series: [{
      type: 'radar',
      data: [
        {
          value: getScores('graphrag'),
          name: 'GraphRAG',
          areaStyle: { color: 'rgba(82,196,26,0.25)' },
          lineStyle: { color: '#52c41a', width: 2 },
          itemStyle: { color: '#52c41a' }
        },
        {
          value: getScores('rag'),
          name: 'RAG',
          areaStyle: { color: 'rgba(250,173,20,0.25)' },
          lineStyle: { color: '#faad14', width: 2 },
          itemStyle: { color: '#faad14' }
        },
        {
          value: getScores('llm'),
          name: 'LLM',
          areaStyle: { color: 'rgba(24,144,255,0.25)' },
          lineStyle: { color: '#1890ff', width: 2 },
          itemStyle: { color: '#1890ff' }
        }
      ]
    }]
  }
})

const evaluateAnswer = async () => {
  if (!question.value.trim()) return
  
  answerEvaluation.value = null
  loadingAnswer.value = true
  try {
    const data = await evaluateAnswerQuality(question.value, expectedAnswer.value.trim() || undefined)
    console.log('评估结果:', data)
    answerEvaluation.value = data
  } catch (error) {
    console.error('回答质量评估失败:', error)
    if (error.response?.data?.detail) {
      alert('评估失败: ' + error.response.data.detail)
    }
  } finally {
    loadingAnswer.value = false
  }
}

const getDimLabel = (dim) => {
  return dimLabels[dim] || dim
}

const getJudgeScore = (method, dim) => {
  if (!answerEvaluation.value?.evaluation?.[method]?.llm_judge) return '-'
  const judge = answerEvaluation.value.evaluation[method].llm_judge
  return judge[dim] ?? '-'
}

const getJudgeScorePercent = (method, dim) => {
  const score = getJudgeScore(method, dim)
  if (score === '-') return 0
  return (score / 5 * 100).toFixed(0)
}

const getLlmScorePercent = (method) => {
  if (!answerEvaluation.value?.evaluation?.[method]?.llm_judge) return '-'
  const overall = answerEvaluation.value.evaluation[method].llm_judge.overall
  return ((overall / 5) * 100).toFixed(1) + '%'
}

const getAutoScore = (method) => {
  if (!answerEvaluation.value?.evaluation?.[method]?.automatic) return '-'
  const score = answerEvaluation.value.evaluation[method].automatic.score
  return (score * 100).toFixed(1)
}

const getLlmScore = (method) => {
  if (!answerEvaluation.value?.evaluation?.[method]?.llm_judge) return '-'
  const overall = answerEvaluation.value.evaluation[method].llm_judge.overall
  return ((overall / 5) * 100).toFixed(1)
}

const dimDescriptions = {
  accuracy: '回答的事实是否正确',
  completeness: '是否覆盖所有关键要点',
  relevance: '是否与问题直接相关',
  expertise: '是否正确使用专业术语',
  explainability: '是否清晰说明推理过程'
}

const getDimDesc = (dim) => {
  return dimDescriptions[dim] || ''
}

const scoreScaleList = [
  { score: '5', level: '优秀', desc: '完全符合要求', color: '#52c41a' },
  { score: '4', level: '良好', desc: '大部分符合要求', color: '#73d13d' },
  { score: '3', level: '一般', desc: '基本符合要求', color: '#faad14' },
  { score: '2', level: '较差', desc: '部分符合要求', color: '#ff7a45' },
  { score: '1', level: '差', desc: '不符合要求', color: '#ff4d4f' }
]
</script>

<style lang="scss" scoped>
.evaluation-page {
  padding: 32px 48px;
  background: #f5f7fa;
  min-height: calc(100vh - 70px);
}

.page-header {
  margin-bottom: 24px;
  
  .header-content {
    .page-title {
      font-size: 32px;
      font-weight: 700;
      margin: 0 0 8px 0;
      background: linear-gradient(135deg, #d4af37 0%, #b8860b 100%);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      background-clip: text;
    }
    
    .page-subtitle {
      font-size: 14px;
      color: #666;
      margin: 0;
    }
  }
}

.tab-container {
  :deep(.n-tabs-nav) {
    background: white;
    border-radius: 16px;
    padding: 8px;
    box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
  }
  
  :deep(.n-tabs-tab) {
    font-weight: 600;
    padding: 12px 24px;
    border-radius: 12px;
    
    &.n-tabs-tab--active {
      background: linear-gradient(135deg, #d4af37 0%, #b8860b 100%);
      color: white;
    }
  }
}

.tab-content {
  margin-top: 24px;
}

.analysis-card {
  background: white;
  border-radius: 16px;
  padding: 24px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
  
  .card-header {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 24px;
    padding-bottom: 16px;
    border-bottom: 2px solid #f0f0f0;
    
    h3 {
      margin: 0;
      font-size: 18px;
      font-weight: 600;
      color: #333;
    }
    
    :deep(.n-icon) {
      color: #d4af37;
    }
    
    :deep(.n-button) {
      margin-left: auto;
    }
  }
}

.question-input {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 24px;

  .expected-answer-input {
    :deep(.n-input) {
      textarea {
        border-radius: 12px;
        font-size: 13px;
        background: #fafbfc;
      }
    }
  }
  
  :deep(.n-input) {
    flex: 1;
    
    textarea {
      border-radius: 12px;
      font-size: 14px;
    }
  }
  
  :deep(.n-button) {
    align-self: flex-end;
    padding: 0 32px;
  }
}

.answer-results {
  animation: fadeInUp 0.5s ease;
}

.radar-section {
  background: #fafafa;
  border-radius: 16px;
  padding: 24px;
  margin-bottom: 24px;

  code {
    font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
    font-style: normal;
  }

  .radar-layout {
    display: flex;
    gap: 20px;
  }

  .radar-left {
    flex: 6;
    min-width: 0;
  }

  .radar-right {
    flex: 4;
    min-width: 280px;
  }

  .formula-subtitle {
    text-align: center;
    margin-bottom: 12px;
    padding: 8px 16px;
    background: white;
    border-radius: 8px;
    border-left: 3px solid #d4af37;

    .sub-label {
      display: block;
      font-size: 11px;
      color: #999;
      margin-bottom: 2px;
    }

    code {
      font-family: 'Consolas', 'Monaco', monospace;
      font-size: 14px;
      color: #b8860b;
      font-weight: 600;

      sub {
        font-size: 10px;
        color: #999;
        font-weight: 400;
      }
    }
  }

  .radar-chart-card {
    background: white;
    border-radius: 12px;
    padding: 16px;
    box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
  }

  .radar-chart-inner {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
  }

  .combined-radar-chart {
    width: 100%;
    height: 300px;
    flex: 1;
    min-width: 0;
  }

  .radar-legend-vertical {
    display: flex;
    flex-direction: column;
    gap: 10px;
    padding-left: 8px;
    margin-left: 4px;
    border-left: 2px solid #f0f0f0;
    flex-shrink: 0;

    .rv-item {
      display: flex;
      align-items: center;
      gap: 6px;
      font-size: 12px;
      font-weight: 600;

      .rv-dot {
        width: 10px;
        height: 10px;
        border-radius: 3px;
        flex-shrink: 0;
      }

      .rv-label {
        white-space: nowrap;
      }

      &.graphrag-legend { color: #52c41a; }
      &.graphrag-legend .rv-dot { background: #52c41a; }

      &.rag-legend { color: #faad14; }
      &.rag-legend .rv-dot { background: #faad14; }

      &.llm-legend { color: #1890ff; }
      &.llm-legend .rv-dot { background: #1890ff; }
    }
  }

  .total-score-row {
    display: flex;
    justify-content: space-around;
    gap: 12px;
    margin-top: 10px;
    padding: 12px 16px;
    background: white;
    border-radius: 8px;

    .total-item {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 2px;

      .total-label {
        font-size: 11px;
        color: #888;
        font-weight: 500;
      }

      .total-calc {
        font-family: 'Consolas', 'Monaco', monospace;
        font-size: 11px;
        color: #999;
        font-weight: 400;
      }

      .total-value {
        font-size: 20px;
        font-weight: 800;
        font-family: 'Consolas', 'Monaco', monospace;
      }

      &.graphrag-total .total-value { color: #52c41a; }
      &.rag-total .total-value { color: #faad14; }
      &.llm-total .total-value { color: #1890ff; }
    }
  }

  .comparison-table {
    margin-top: 12px;
    background: white;
    border-radius: 10px;
    overflow: hidden;
    box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);

    table {
      width: 100%;
      border-collapse: collapse;

      thead {
        background: #f5f7fa;

        th {
          padding: 8px 14px;
          font-size: 12px;
          font-weight: 600;
          color: #666;
          text-align: left;
          border-bottom: 1px solid #eee;
        }
      }

      tbody tr {
        &:hover { background: #fafbfc; }

        td {
          padding: 8px 14px;
          font-size: 13px;
          color: #444;
          border-bottom: 1px solid #f0f0f0;

          &:first-child {
            display: flex;
            align-items: center;
            gap: 6px;
          }

          &.positive { color: #52c41a; font-weight: 700; }
          &.negative { color: #ff4d4f; font-weight: 700; }
        }
      }
    }

    .method-dot {
      display: inline-block;
      width: 8px;
      height: 8px;
      border-radius: 50%;

      &.graphrag { background: #52c41a; }
      &.rag { background: #faad14; }
      &.llm { background: #1890ff; }
    }
  }

  .eval-tabs {
    background: white;
    border-radius: 12px;
    padding: 16px;
    box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
    height: 100%;

    :deep(.n-tabs-tab) {
      font-weight: 600;
      font-size: 13px;
    }
  }

  .tab-content {
    padding-top: 12px;
  }

  .tab-subtitle {
    font-size: 13px;
    color: #888;
    margin-bottom: 12px;
    padding-bottom: 8px;
    border-bottom: 1px solid #f0f0f0;
  }

  .formula-list {
    display: flex;
    flex-direction: column;
    gap: 10px;
    margin-bottom: 14px;

    .formula-list-item {
      display: grid;
      grid-template-columns: 80px 1fr auto;
      gap: 8px;
      align-items: center;
      padding: 8px 10px;
      background: #fafafa;
      border-radius: 6px;

      .fl-label {
        font-size: 12px;
        font-weight: 600;
        color: #555;
      }

      .fl-value {
        text-align: center;

        code {
          font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, 'Helvetica Neue', Arial, sans-serif;
          font-size: 13px;
          color: #b8860b;
          font-weight: 600;

          sub, sup {
            font-size: 10px;
            color: #b8860b;
          }
        }
      }

      .fl-desc {
        font-size: 11px;
        color: #999;
        white-space: nowrap;
      }
    }
  }

  .formula-total {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 10px 14px;
    background: linear-gradient(135deg, #fffbf0, #fff9e6);
    border-radius: 8px;
    border-left: 3px solid #d4af37;

    &.formula-total-blue {
      background: linear-gradient(135deg, #f0f7ff, #f5faff);
      border-left-color: #1890ff;

      .ft-value code { color: #096dd9; }
    }

    .ft-label {
      font-size: 12px;
      font-weight: 600;
      color: #666;
      white-space: nowrap;
    }

    .ft-value {
      flex: 1;
      text-align: center;

      code {
        font-family: 'Consolas', 'Monaco', monospace;
        font-size: 14px;
        color: #b8860b;
        font-weight: 700;
      }
    }
  }

  .dimension-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 8px;
    margin-bottom: 14px;

    .dg-item {
      display: flex;
      align-items: baseline;
      gap: 6px;
      padding: 6px 10px;
      background: #fafafa;
      border-radius: 6px;

      .dg-name {
        font-size: 13px;
        font-weight: 600;
        color: #333;
        white-space: nowrap;
      }

      .dg-desc {
        font-size: 11px;
        color: #777;
      }
    }
  }

  .tab-score-section {
    margin-top: 12px;
    padding: 10px 12px;
    background: #fafafa;
    border-radius: 8px;

    .tss-header {
      font-size: 12px;
      font-weight: 600;
      color: #555;
      margin-bottom: 8px;
    }

    .tss-body {
      display: flex;
      flex-direction: column;
      gap: 6px;
    }

    .tss-row {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 4px 8px;
      border-radius: 4px;

      &:hover { background: white; }

      .tss-dot {
        width: 8px;
        height: 8px;
        border-radius: 3px;
        flex-shrink: 0;
      }

      .tss-name {
        font-size: 12px;
        font-weight: 600;
        color: #444;
        flex: 1;
      }

      .tss-score {
        font-family: 'Consolas', 'Monaco', monospace;
        font-size: 14px;
        font-weight: 700;
      }
    }
  }

  .score-scale {
    margin-bottom: 14px;

    .ss-header {
      font-size: 12px;
      font-weight: 600;
      color: #555;
      margin-bottom: 8px;
    }

    .ss-body {
      display: flex;
      flex-direction: column;
      gap: 4px;

      .ss-row {
        display: flex;
        align-items: center;
        gap: 8px;
        padding: 4px 8px;
        border-radius: 4px;

        &:hover { background: #fafafa; }

        .ss-score {
          font-size: 15px;
          font-weight: 800;
          width: 22px;
          text-align: center;
        }

        .ss-level {
          font-size: 12px;
          font-weight: 600;
          color: #333;
          width: 40px;
        }

        .ss-desc {
          font-size: 11px;
          color: #888;
        }
      }
    }
  }
}

.answers-section {
  margin-bottom: 24px;
  
  .answers-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 16px;
  }
}

.section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
  
  h4 {
    margin: 0;
    font-size: 16px;
    font-weight: 600;
    color: #333;
  }
  
  :deep(.n-icon) {
    color: #d4af37;
  }
}

.trace-section {
  margin-bottom: 24px;
}

.trace-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}

.trace-card {
  background: #fafafa;
  border-radius: 12px;
  padding: 20px;
  border-left: 4px solid;
  
  &.graphrag-trace {
    border-color: #52c41a;
  }
  
  &.rag-trace {
    border-color: #faad14;
  }
  
  &.llm-trace {
    border-color: #1890ff;
  }
  
  .trace-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 12px;
  }
  
  .trace-badge {
    font-size: 12px;
    font-weight: 600;
    padding: 2px 8px;
    border-radius: 4px;
    
    &.disabled {
      color: #999;
    }
  }
  
  .trace-content {
    .trace-subtitle {
      font-size: 13px;
      font-weight: 600;
      color: #666;
      margin-bottom: 8px;
    }
    
    .entity-tags {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      margin-bottom: 12px;
    }
    
    .vector-results {
      display: flex;
      flex-direction: column;
      gap: 8px;
      margin-bottom: 12px;
    }
    
    .vector-item {
      background: white;
      border-radius: 8px;
      padding: 10px;
      border: 1px solid #e8e8e8;
      
      .vector-item-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 4px;
        
        .vector-source {
          font-size: 12px;
          font-weight: 600;
          color: #555;
        }
      }
      
      .vector-item-text {
        font-size: 12px;
        color: #888;
        line-height: 1.4;
      }
    }
    
    .context-text {
      font-size: 12px;
      line-height: 1.5;
      color: #666;
      white-space: pre-wrap;
      word-wrap: break-word;
      background: white;
      padding: 12px;
      border-radius: 8px;
      border: 1px solid #e8e8e8;
      margin: 0;
    }
  }

  .llm-placeholder {
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 60px;
  }
}

.answer-card {
  background: #fafafa;
  border-radius: 12px;
  padding: 20px;
  border-left: 4px solid;
  
  &.graphrag {
    border-color: #52c41a;
    background: linear-gradient(135deg, rgba(82, 196, 26, 0.05), rgba(62, 184, 20, 0.02));
  }
  
  &.rag {
    border-color: #faad14;
    background: linear-gradient(135deg, rgba(250, 173, 20, 0.05), rgba(247, 148, 30, 0.02));
  }
  
  &.llm {
    border-color: #1890ff;
    background: linear-gradient(135deg, rgba(24, 144, 255, 0.05), rgba(13, 110, 253, 0.02));
  }
  
  .answer-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 12px;
    
    .score-badge {
      font-weight: 700;
      font-size: 14px;
      color: #333;
    }
  }
  
  .answer-content {
    font-size: 14px;
    line-height: 1.6;
    color: #444;
    min-height: 60px;
  }
}

@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

:deep(.n-button--primary-type) {
  background: linear-gradient(135deg, #d4af37 0%, #b8860b 100%) !important;
  border: none;
  
  &:hover {
    background: linear-gradient(135deg, #c9a668 0%, #9a7509 100%) !important;
  }
}

@media (max-width: 1200px) {
  .trace-grid,
  .answers-section .answers-grid {
    grid-template-columns: 1fr;
  }
  
  .radar-section .radar-layout {
    flex-direction: column;
    
    .radar-left, .radar-right {
      width: 100%;
      min-width: 0;
    }
  }
  
  .combined-radar-chart {
    height: 280px;
  }
}
</style>

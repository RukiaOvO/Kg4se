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
                      <code>S = 0.4&times;A + 0.4&times;L + 0.2&times;C</code>
                    </div>
                    <div class="radar-charts-row">
                      <div class="radar-chart-item graphrag-chart">
                        <div class="radar-chart-label">GraphRAG</div>
                        <v-chart :option="getGraphragRadarOption" autoresize class="single-radar-chart" />
                      </div>
                      <div class="radar-chart-item rag-chart">
                        <div class="radar-chart-label">RAG</div>
                        <v-chart :option="getRagRadarOption" autoresize class="single-radar-chart" />
                      </div>
                      <div class="radar-chart-item llm-chart">
                        <div class="radar-chart-label">LLM</div>
                        <v-chart :option="getLlmRadarOption" autoresize class="single-radar-chart" />
                      </div>
                    </div>
                    <div class="total-score-row">
                      <div class="total-item graphrag-total">
                        <span class="total-label">GraphRAG</span>
                        <span class="total-calc">0.4&times;{{ getAutoScore('graphrag') }} + 0.4&times;{{ getLlmScore('graphrag') }} + 0.2&times;{{ getCredibilityScore('graphrag') }}</span>
                        <span class="total-value">{{ (answerEvaluation.evaluation.statistics.graphrag_score * 100).toFixed(2) }}</span>
                      </div>
                      <div class="total-item rag-total">
                        <span class="total-label">RAG</span>
                        <span class="total-calc">0.4&times;{{ getAutoScore('rag') }} + 0.4&times;{{ getLlmScore('rag') }} + 0.2&times;{{ getCredibilityScore('rag') }}</span>
                        <span class="total-value">{{ (answerEvaluation.evaluation.statistics.rag_score * 100).toFixed(2) }}</span>
                      </div>
                      <div class="total-item llm-total">
                        <span class="total-label">LLM</span>
                        <span class="total-calc">0.4&times;{{ getAutoScore('llm') }} + 0.4&times;{{ getLlmScore('llm') }} + 0.2&times;{{ getCredibilityScore('llm') }}</span>
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
                          <div class="tab-subtitle">五维度自动化指标（均归一化至[0,1]）</div>
                          <div class="formula-list">
                            <div class="formula-list-item">
                              <span class="fl-label">语义相似度</span>
                              <div class="fl-value"><code>cos(emb<sub>pred</sub>, emb<sub>ref</sub>)</code></div>
                              <span class="fl-desc">语义匹配</span>
                            </div>
                            <div class="formula-list-item">
                              <span class="fl-label">长度充分度</span>
                              <div class="fl-value"><code>min(1, |pred|/|ref|)</code></div>
                              <span class="fl-desc">有界比率</span>
                            </div>
                            <div class="formula-list-item">
                              <span class="fl-label">词重叠率</span>
                              <div class="fl-value"><code>|A &cap; B| / |A &cup; B|</code></div>
                              <span class="fl-desc">Jaccard系数</span>
                            </div>
                            <div class="formula-list-item">
                              <span class="fl-label">关键词F1</span>
                              <div class="fl-value"><code>2PR / (P + R)</code></div>
                              <span class="fl-desc">精确率+召回率</span>
                            </div>
                            <div class="formula-list-item">
                              <span class="fl-label">ROUGE-L</span>
                              <div class="fl-value"><code>LCS F-measure</code></div>
                              <span class="fl-desc">语序匹配度</span>
                            </div>
                          </div>
                          <div class="formula-total">
                            <span class="ft-label">自动评估总分 A</span>
                            <div class="ft-value"><code>A = 0.30&times;Sem + 0.30&times;Len + 0.10&times;WOR + 0.15&times;KF1 + 0.15&times;RL</code></div>
                          </div>
                          <div class="tab-score-section">
                            <div class="tss-header">各方法分数 A</div>
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
                            <div class="tss-header">各方法分数 L</div>
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
                      <n-tab-pane name="credibility" tab="可信度 C">
                        <div class="tab-content">
                          <div class="tab-subtitle">信息可信度：评估回答是否有外部知识支撑</div>
                          <div class="credibility-concept">
                            <div class="cc-item">
                              <span class="cc-icon">&#128218;</span>
                              <div class="cc-text">
                                <span class="cc-title">有外部知识</span>
                                <span class="cc-desc">回答基于知识图谱或文档检索结果，具有事实依据</span>
                              </div>
                            </div>
                            <div class="cc-item">
                              <span class="cc-icon">&#128172;</span>
                              <div class="cc-text">
                                <span class="cc-title">无外部知识</span>
                                <span class="cc-desc">回答完全依靠模型参数化记忆，可能包含幻觉</span>
                              </div>
                            </div>
                          </div>
                          <div class="formula-list">
                            <div class="formula-list-item">
                              <span class="fl-label">有上下文</span>
                              <div class="fl-value"><code>C = 0.4 + 0.6 &times; overlap</code></div>
                              <span class="fl-desc">上下文引用率</span>
                            </div>
                            <div class="formula-list-item">
                              <span class="fl-label">无上下文</span>
                              <div class="fl-value"><code>C = 0.15</code></div>
                              <span class="fl-desc">无事实依据</span>
                            </div>
                          </div>
                          <div class="credibility-note">
                            <span class="cn-label">公平性说明</span>
                            <span class="cn-text">所有方法使用同一公式，差异仅来自是否拥有外部知识上下文及引用程度，与方法类型无关</span>
                          </div>
                          <div class="tab-score-section">
                            <div class="tss-header">各方法分数 C</div>
                            <div class="tss-body">
                              <div class="tss-row">
                                <span class="tss-dot" style="background:#52c41a"></span>
                                <span class="tss-name">GraphRAG</span>
                                <span class="tss-score" style="color:#52c41a">{{ getCredibilityScore('graphrag') }}</span>
                              </div>
                              <div class="tss-row">
                                <span class="tss-dot" style="background:#faad14"></span>
                                <span class="tss-name">RAG</span>
                                <span class="tss-score" style="color:#faad14">{{ getCredibilityScore('rag') }}</span>
                              </div>
                              <div class="tss-row">
                                <span class="tss-dot" style="background:#1890ff"></span>
                                <span class="tss-name">LLM</span>
                                <span class="tss-score" style="color:#1890ff">{{ getCredibilityScore('llm') }}</span>
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

              <div v-if="answerEvaluation.pairwise" class="pairwise-section">
                <div class="section-title">
                  <n-icon size="20"><trophy-outline /></n-icon>
                  <h4>Pairwise 成对比较（位置交换策略）</h4>
                  <div class="pairwise-subtitle">四维度评估：准确性、全面性、逻辑连贯性、有用性</div>
                </div>
                <div class="pairwise-grid">
                  <div
                    v-for="pair in pairwiseComparisons"
                    :key="pair.key"
                    class="pairwise-card"
                    :class="getPairwiseWinnerClass(pair.result)"
                  >
                    <div class="pairwise-card-header">
                      <span class="pairwise-vs">{{ pair.labelA }}</span>
                      <span class="pairwise-vs-divider">VS</span>
                      <span class="pairwise-vs">{{ pair.labelB }}</span>
                    </div>
                    <div class="pairwise-winner">
                      <n-tag :type="getPairwiseTagType(pair.result.winner, pair.keyA, pair.keyB)" size="large" round>
                        {{ getPairwiseWinnerLabel(pair.result.winner, pair.keyA, pair.keyB, pair.labelA, pair.labelB) }}
                      </n-tag>
                    </div>
                    <div class="pairwise-scores-row" v-if="pair.result.scores">
                      <div class="pairwise-model-scores" v-for="modelName in [pair.keyA, pair.keyB]" :key="modelName">
                        <div class="pairwise-model-name">{{ modelName }}</div>
                        <div class="pairwise-dim-bars">
                          <div class="pairwise-dim-bar" v-for="dim in pairwiseDimensions" :key="dim.key">
                            <span class="pairwise-dim-label">{{ dim.label }}</span>
                            <div class="pairwise-bar-track">
                              <div
                                class="pairwise-bar-fill"
                                :style="{
                                  width: ((pair.result.scores[modelName]?.[dim.key] || 0) / 5 * 100) + '%',
                                  backgroundColor: dim.color
                                }"
                              ></div>
                            </div>
                            <span class="pairwise-dim-value">{{ pair.result.scores[modelName]?.[dim.key] || '-' }}</span>
                          </div>
                        </div>
                      </div>
                    </div>
                    <div class="pairwise-reasoning" v-if="pair.result.reasoning">
                      <span class="pairwise-reasoning-label">评判理由：</span>
                      <n-scrollbar style="max-height: 120px;">
                        <div class="pairwise-reasoning-text">{{ pair.result.reasoning }}</div>
                      </n-scrollbar>
                    </div>
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
                      <div class="header-metrics">
                        <span class="time-badge" v-if="answerEvaluation.timing">
                          <n-icon size="14"><time-outline /></n-icon>
                          {{ answerEvaluation.timing.graphrag_gen_time }}s
                        </span>
                        <span class="score-badge">{{ (answerEvaluation.evaluation.statistics.graphrag_score * 100).toFixed(1) }}</span>
                      </div>
                    </div>
                    <div class="answer-content markdown-content">
                      <Markdown :source="answerEvaluation.graphrag_answer" />
                    </div>
                  </div>

                  <div class="answer-card rag">
                    <div class="answer-header">
                      <n-tag type="warning" bordered>RAG</n-tag>
                      <div class="header-metrics">
                        <span class="time-badge" v-if="answerEvaluation.timing">
                          <n-icon size="14"><time-outline /></n-icon>
                          {{ answerEvaluation.timing.rag_gen_time }}s
                        </span>
                        <span class="score-badge">{{ (answerEvaluation.evaluation.statistics.rag_score * 100).toFixed(1) }}</span>
                      </div>
                    </div>
                    <div class="answer-content markdown-content">
                      <Markdown :source="answerEvaluation.rag_answer" />
                    </div>
                  </div>

                  <div class="answer-card llm">
                    <div class="answer-header">
                      <n-tag type="info" bordered>LLM</n-tag>
                      <div class="header-metrics">
                        <span class="time-badge" v-if="answerEvaluation.timing">
                          <n-icon size="14"><time-outline /></n-icon>
                          {{ answerEvaluation.timing.llm_gen_time }}s
                        </span>
                        <span class="score-badge">{{ (answerEvaluation.evaluation.statistics.llm_score * 100).toFixed(1) }}</span>
                      </div>
                    </div>
                    <div class="answer-content markdown-content">
                      <Markdown :source="answerEvaluation.llm_answer" />
                    </div>
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
import { DocumentTextOutline, SendOutline, GitNetworkOutline, AnalyticsOutline, TimeOutline, TrophyOutline } from '@vicons/ionicons5'
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

const getSingleRadarOption = (method, color, bgColor) => {
  if (!answerEvaluation.value?.evaluation?.[method]?.llm_judge) return { series: [] }
  
  const llmJudge = answerEvaluation.value.evaluation[method].llm_judge
  const scores = llmJudgeDimensions.map(dim => llmJudge[dim] ?? 0)
  const methodNames = { graphrag: 'GraphRAG', rag: 'RAG', llm: 'LLM' }
  
  return {
    tooltip: {
      trigger: 'item',
      confine: true,
      formatter: (params) => {
        let html = `<b>${methodNames[method]}</b><br/>`
        params.value.forEach((v, i) => {
          html += `${dimLabels[llmJudgeDimensions[i]]}: ${v}<br/>`
        })
        return html
      }
    },
    legend: { show: false },
    radar: {
      indicator: llmJudgeDimensions.map(dim => ({ name: dimLabels[dim], max: 5 })),
      shape: 'polygon',
      splitNumber: 5,
      center: ['50%', '50%'],
      radius: '70%',
      axisName: {
        color: '#444',
        fontSize: 11,
        fontWeight: 500
      },
      splitLine: {
        lineStyle: { color: 'rgba(0,0,0,0.08)' }
      },
      splitArea: {
        areaStyle: {
          color: ['rgba(0,0,0,0.01)', 'rgba(0,0,0,0.02)']
        }
      },
      axisLine: {
        lineStyle: { color: 'rgba(0,0,0,0.08)' }
      }
    },
    series: [{
      type: 'radar',
      data: [{
        value: scores,
        name: methodNames[method],
        areaStyle: { color: bgColor },
        lineStyle: { color: color, width: 2 },
        itemStyle: { color: color },
        symbol: 'circle',
        symbolSize: 5
      }]
    }]
  }
}

const getGraphragRadarOption = computed(() => getSingleRadarOption('graphrag', '#52c41a', 'rgba(82,196,26,0.25)'))
const getRagRadarOption = computed(() => getSingleRadarOption('rag', '#faad14', 'rgba(250,173,20,0.25)'))
const getLlmRadarOption = computed(() => getSingleRadarOption('llm', '#1890ff', 'rgba(24,144,255,0.25)'))

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

const getCredibilityScore = (method) => {
  if (!answerEvaluation.value?.evaluation?.[method]) return '-'
  const credibility = answerEvaluation.value.evaluation[method].info_credibility
  return (credibility * 100).toFixed(1)
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

const pairwiseDimensions = [
  { key: 'accuracy', label: '准确性', color: '#52c41a' },
  { key: 'comprehensiveness', label: '全面性', color: '#1890ff' },
  { key: 'coherence', label: '逻辑连贯', color: '#722ed1' },
  { key: 'helpfulness', label: '有用性', color: '#fa8c16' }
]

const pairwiseComparisons = computed(() => {
  if (!answerEvaluation.value?.pairwise) return []
  const pw = answerEvaluation.value.pairwise
  return [
    { key: 'graphrag_vs_rag', keyA: 'GraphRAG', keyB: 'RAG', labelA: 'GraphRAG', labelB: 'RAG', result: pw.graphrag_vs_rag },
    { key: 'graphrag_vs_llm', keyA: 'GraphRAG', keyB: 'LLM', labelA: 'GraphRAG', labelB: 'LLM', result: pw.graphrag_vs_llm },
    { key: 'rag_vs_llm', keyA: 'RAG', keyB: 'LLM', labelA: 'RAG', labelB: 'LLM', result: pw.rag_vs_llm }
  ]
})

const getPairwiseWinnerClass = (result) => {
  if (!result?.winner) return ''
  if (result.winner === 'tie') return 'pairwise-tie'
  return 'pairwise-has-winner'
}

const getPairwiseTagType = (winner, keyA, keyB) => {
  if (!winner || winner === 'tie') return 'warning'
  if (winner === keyA) return 'success'
  if (winner === keyB) return 'info'
  return 'default'
}

const getPairwiseWinnerLabel = (winner, keyA, keyB, labelA, labelB) => {
  if (winner === 'tie') return '平局'
  if (winner === keyA) return `${labelA} 胜出`
  if (winner === keyB) return `${labelB} 胜出`
  return '未知'
}
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

  .radar-charts-row {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 12px;
    margin-bottom: 12px;
  }

  .radar-chart-item {
    background: white;
    border-radius: 12px;
    padding: 12px 8px 8px;
    box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
    text-align: center;

    .radar-chart-label {
      font-size: 13px;
      font-weight: 700;
      margin-bottom: 4px;
    }

    &.graphrag-chart .radar-chart-label { color: #52c41a; }
    &.rag-chart .radar-chart-label { color: #faad14; }
    &.llm-chart .radar-chart-label { color: #1890ff; }
  }

  .single-radar-chart {
    width: 100%;
    height: 240px;
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
    min-height: 480px;
    display: flex;
    flex-direction: column;

    :deep(.n-tabs-nav) {
      flex-shrink: 0;
    }

    :deep(.n-tabs-pane-wrapper) {
      flex: 1;
      overflow-y: auto;
    }

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

  .credibility-concept {
    display: flex;
    flex-direction: column;
    gap: 10px;
    margin-bottom: 14px;

    .cc-item {
      display: flex;
      align-items: flex-start;
      gap: 10px;
      padding: 10px 12px;
      background: #fafafa;
      border-radius: 8px;

      .cc-icon {
        font-size: 20px;
        line-height: 1;
        flex-shrink: 0;
        margin-top: 2px;
      }

      .cc-text {
        display: flex;
        flex-direction: column;
        gap: 2px;

        .cc-title {
          font-size: 13px;
          font-weight: 600;
          color: #333;
        }

        .cc-desc {
          font-size: 11px;
          color: #888;
          line-height: 1.4;
        }
      }
    }
  }

  .credibility-note {
    display: flex;
    flex-direction: column;
    gap: 4px;
    padding: 10px 14px;
    margin-top: 4px;
    background: linear-gradient(135deg, #f0fff0, #f5fff5);
    border-radius: 8px;
    border-left: 3px solid #52c41a;

    .cn-label {
      font-size: 12px;
      font-weight: 600;
      color: #666;
    }

    .cn-text {
      font-size: 11px;
      color: #777;
      line-height: 1.5;
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
      flex-direction: row;
      gap: 8px;
      justify-content: space-between;

      .ss-row {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 2px;
        padding: 8px 10px;
        border-radius: 6px;
        background: #fafafa;
        flex: 1;
        min-width: 50px;

        &:hover { background: white; }

        .ss-score {
          font-size: 16px;
          font-weight: 800;
          width: auto;
          text-align: center;
        }

        .ss-level {
          font-size: 11px;
          font-weight: 600;
          color: #333;
          width: auto;
        }

        .ss-desc {
          font-size: 10px;
          color: #888;
          text-align: center;
          white-space: nowrap;
        }
      }
    }
  }
}

.pairwise-section {
  background: #fafafa;
  border-radius: 16px;
  padding: 24px;
  margin-bottom: 24px;

  .section-title {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 6px;

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

  .pairwise-subtitle {
    font-size: 12px;
    color: #999;
    margin-bottom: 16px;
    margin-left: 28px;
  }

  .pairwise-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 16px;
  }

  .pairwise-card {
    background: white;
    border-radius: 12px;
    padding: 20px;
    box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
    border-left: 4px solid #e0e0e0;
    transition: transform 0.2s ease, box-shadow 0.2s ease;

    &:hover {
      transform: translateY(-2px);
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
    }

    &.pairwise-has-winner {
      border-left-color: #52c41a;
    }

    &.pairwise-tie {
      border-left-color: #faad14;
    }
  }

  .pairwise-card-header {
    display: flex;
    justify-content: center;
    align-items: center;
    gap: 10px;
    margin-bottom: 12px;

    .pairwise-vs {
      font-size: 14px;
      font-weight: 700;
      color: #333;
    }

    .pairwise-vs-divider {
      font-size: 12px;
      color: #bbb;
      font-weight: 600;
      padding: 2px 8px;
      background: #f5f5f5;
      border-radius: 4px;
    }
  }

  .pairwise-winner {
    text-align: center;
    margin-bottom: 14px;

    :deep(.n-tag) {
      font-weight: 600;
      padding: 4px 16px;
    }
  }

  .pairwise-scores-row {
    display: flex;
    flex-direction: column;
    gap: 10px;
    margin-bottom: 12px;
  }

  .pairwise-model-scores {
    .pairwise-model-name {
      font-size: 12px;
      font-weight: 600;
      color: #555;
      margin-bottom: 6px;
      padding-left: 2px;
    }

    .pairwise-dim-bars {
      display: flex;
      flex-direction: column;
      gap: 5px;
    }

    .pairwise-dim-bar {
      display: flex;
      align-items: center;
      gap: 6px;

      .pairwise-dim-label {
        font-size: 11px;
        color: #888;
        width: 52px;
        text-align: right;
        flex-shrink: 0;
      }

      .pairwise-bar-track {
        flex: 1;
        height: 8px;
        background: #f0f0f0;
        border-radius: 4px;
        overflow: hidden;

        .pairwise-bar-fill {
          height: 100%;
          border-radius: 4px;
          transition: width 0.5s ease;
        }
      }

      .pairwise-dim-value {
        font-size: 11px;
        font-weight: 700;
        color: #555;
        width: 20px;
        text-align: left;
        flex-shrink: 0;
      }
    }
  }

  .pairwise-reasoning {
    padding: 6px 8px;
    border-radius: 6px;
    background: #fafafa;

    .pairwise-reasoning-label {
      font-size: 11px;
      color: #888;
      font-weight: 500;
    }

    .pairwise-reasoning-text {
      font-size: 12px;
      color: #666;
      line-height: 1.5;
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
    
    .header-metrics {
      display: flex;
      align-items: center;
      gap: 10px;
    }
    
    .time-badge {
      display: flex;
      align-items: center;
      gap: 3px;
      font-size: 12px;
      color: #888;
      font-weight: 500;
      padding: 2px 8px;
      background: rgba(0, 0, 0, 0.04);
      border-radius: 6px;
      
      :deep(.n-icon) {
        color: #999;
      }
    }
    
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

  .markdown-content {
    h1, h2, h3, h4 {
      margin: 12px 0 8px;
      font-weight: 600;
      color: #333;
    }
    h1 { font-size: 18px; }
    h2 { font-size: 16px; }
    h3 { font-size: 15px; }
    h4 { font-size: 14px; }

    p {
      margin: 0 0 8px;
      line-height: 1.7;
    }

    ul, ol {
      margin: 4px 0 8px;
      padding-left: 20px;
    }

    li {
      margin: 2px 0;
      line-height: 1.6;
    }

    code {
      font-size: 13px;
      padding: 1px 5px;
      border-radius: 3px;
      background: rgba(0,0,0,0.06);
      color: #d63384;
      font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
    }

    pre {
      margin: 8px 0;
      padding: 12px;
      border-radius: 8px;
      background: #1e1e1e;
      overflow-x: auto;
      font-size: 13px;
      line-height: 1.5;

      code {
        background: none;
        color: #d4d4d4;
        padding: 0;
      }
    }

    table {
      width: 100%;
      border-collapse: collapse;
      margin: 8px 0;
      font-size: 13px;
    }

    th, td {
      padding: 6px 10px;
      border: 1px solid #e0e0e0;
      text-align: left;
    }

    th {
      background: #f5f5f5;
      font-weight: 600;
    }

    blockquote {
      margin: 8px 0;
      padding: 6px 12px;
      border-left: 3px solid #d4af37;
      background: #fafafa;
      color: #666;
    }

    strong {
      font-weight: 700;
      color: #333;
    }

    a {
      color: #1890ff;
      text-decoration: none;
      &:hover { text-decoration: underline; }
    }
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
  .answers-section .answers-grid,
  .pairwise-section .pairwise-grid {
    grid-template-columns: 1fr;
  }
  
  .radar-section .radar-layout {
    flex-direction: column;
    
    .radar-left, .radar-right {
      width: 100%;
      min-width: 0;
    }
  }
  
  .radar-section .radar-charts-row {
    grid-template-columns: 1fr;
  }
  
  .single-radar-chart {
    height: 280px;
  }
}
</style>

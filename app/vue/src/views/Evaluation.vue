<template>
  <div class="evaluation-page">
    <!-- Header -->
    <div class="page-header">
      <div class="header-content">
        <h1 class="page-title">质量分析</h1>
        <p class="page-subtitle">LLM Answer Quality Analysis</p>
      </div>
    </div>

    <!-- Tab Switch -->
    <n-tabs v-model:value="activeTab" type="line" class="tab-container" :default-value="'answer'">
      <n-tab-pane name="answer" tab="LLM回答质量分析">
        <div class="tab-content">
          <div class="analysis-card">
            <div class="card-header">
              <n-icon size="20"><document-text-outline /></n-icon>
              <h3>回答质量对比评估</h3>
            </div>

            <!-- Question Input -->
            <div class="question-input">
              <n-input
                v-model:value="question"
                type="textarea"
                :rows="3"
                placeholder="请输入要评估的问题..."
                @keyup.enter="evaluateAnswer"
              />
              <n-button type="primary" @click="evaluateAnswer" :loading="loadingAnswer">
                <template #icon>
                  <n-icon><send-outline /></n-icon>
                </template>
                开始评估
              </n-button>
            </div>

            <!-- Results -->
            <div v-if="answerEvaluation" class="answer-results">
              <!-- Answers Comparison -->
              <div class="answers-grid">
                <div class="answer-card graphrag">
                  <div class="answer-header">
                    <n-tag type="success" bordered>GraphRAG</n-tag>
                    <span class="score-badge">{{ (answerEvaluation.evaluation.statistics.graphrag_score * 100).toFixed(1) }}%</span>
                  </div>
                  <div class="answer-content">{{ answerEvaluation.graphrag_answer }}</div>
                  <div class="answer-metrics">
                    <span>语义相似度: {{ (answerEvaluation.evaluation.graphrag.automatic.semantic_similarity * 100).toFixed(1) }}%</span>
                    <span>词重叠: {{ (answerEvaluation.evaluation.graphrag.automatic.word_overlap * 100).toFixed(1) }}%</span>
                  </div>
                </div>

                <div class="answer-card rag">
                  <div class="answer-header">
                    <n-tag type="warning" bordered>RAG</n-tag>
                    <span class="score-badge">{{ (answerEvaluation.evaluation.statistics.rag_score * 100).toFixed(1) }}%</span>
                  </div>
                  <div class="answer-content">{{ answerEvaluation.rag_answer }}</div>
                  <div class="answer-metrics">
                    <span>语义相似度: {{ (answerEvaluation.evaluation.rag.automatic.semantic_similarity * 100).toFixed(1) }}%</span>
                    <span>词重叠: {{ (answerEvaluation.evaluation.rag.automatic.word_overlap * 100).toFixed(1) }}%</span>
                  </div>
                </div>

                <div class="answer-card llm">
                  <div class="answer-header">
                    <n-tag type="info" bordered>LLM</n-tag>
                    <span class="score-badge">{{ (answerEvaluation.evaluation.statistics.llm_score * 100).toFixed(1) }}%</span>
                  </div>
                  <div class="answer-content">{{ answerEvaluation.llm_answer }}</div>
                  <div class="answer-metrics">
                    <span>语义相似度: {{ (answerEvaluation.evaluation.llm.automatic.semantic_similarity * 100).toFixed(1) }}%</span>
                    <span>词重叠: {{ (answerEvaluation.evaluation.llm.automatic.word_overlap * 100).toFixed(1) }}%</span>
                  </div>
                </div>
              </div>

              <!-- Improvement Chart -->
              <div class="improvement-section">
                <h4>性能提升对比</h4>
                <div class="improvement-bars">
                  <div class="bar-item">
                    <span class="bar-label">GraphRAG vs RAG</span>
                    <div class="bar-container">
                      <div 
                        class="bar graphrag-bar" 
                        :style="{ width: Math.abs(answerEvaluation.improvement.graphrag_over_rag_percent) + '%' }"
                      ></div>
                    </div>
                    <span class="bar-value" :class="answerEvaluation.improvement.graphrag_over_rag_percent > 0 ? 'positive' : 'negative'">
                      {{ answerEvaluation.improvement.graphrag_over_rag_percent > 0 ? '+' : '' }}{{ answerEvaluation.improvement.graphrag_over_rag_percent.toFixed(1) }}%
                    </span>
                  </div>
                  <div class="bar-item">
                    <span class="bar-label">GraphRAG vs LLM</span>
                    <div class="bar-container">
                      <div 
                        class="bar llm-bar" 
                        :style="{ width: Math.abs(answerEvaluation.improvement.graphrag_over_llm_percent) + '%' }"
                      ></div>
                    </div>
                    <span class="bar-value" :class="answerEvaluation.improvement.graphrag_over_llm_percent > 0 ? 'positive' : 'negative'">
                      {{ answerEvaluation.improvement.graphrag_over_llm_percent > 0 ? '+' : '' }}{{ answerEvaluation.improvement.graphrag_over_llm_percent.toFixed(1) }}%
                    </span>
                  </div>
                  <div class="bar-item">
                    <span class="bar-label">RAG vs LLM</span>
                    <div class="bar-container">
                      <div 
                        class="bar rag-bar" 
                        :style="{ width: Math.abs(answerEvaluation.improvement.rag_over_llm_percent) + '%' }"
                      ></div>
                    </div>
                    <span class="bar-value" :class="answerEvaluation.improvement.rag_over_llm_percent > 0 ? 'positive' : 'negative'">
                      {{ answerEvaluation.improvement.rag_over_llm_percent > 0 ? '+' : '' }}{{ answerEvaluation.improvement.rag_over_llm_percent.toFixed(1) }}%
                    </span>
                  </div>
                </div>
              </div>

              <!-- Conclusion -->
              <div class="conclusion-section">
                <h4>评估结论</h4>
                <div class="conclusion-content">
                  <p v-if="answerEvaluation.evaluation.statistics.graphrag_score > answerEvaluation.evaluation.statistics.rag_score && 
                           answerEvaluation.evaluation.statistics.graphrag_score > answerEvaluation.evaluation.statistics.llm_score">
                    <span class="highlight">✅ GraphRAG 在本次评估中表现最优</span>，证明了基于知识图谱的检索增强生成在专业领域问答中的有效性。
                  </p>
                  <p v-else>
                    根据评估结果，当前测试问题的最佳回答方式为 
                    <span class="highlight">{{ getBestMethod() }}</span>。
                  </p>
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
import { ref } from 'vue'
import { NButton, NIcon, NInput, NTabs, NTabPane, NSpin, NEmpty, NTag } from 'naive-ui'
import { DocumentTextOutline, SendOutline } from '@vicons/ionicons5'
import { evaluateAnswerQuality } from '@/api/services'

const activeTab = ref('answer')
const loadingAnswer = ref(false)
const answerEvaluation = ref(null)
const question = ref('')

const evaluateAnswer = async () => {
  if (!question.value.trim()) return
  
  loadingAnswer.value = true
  try {
    const data = await evaluateAnswerQuality(question.value)
    answerEvaluation.value = data
  } catch (error) {
    console.error('回答质量评估失败:', error)
  } finally {
    loadingAnswer.value = false
  }
}

const getBestMethod = () => {
  if (!answerEvaluation.value) return '未知'
  const stats = answerEvaluation.value.evaluation.statistics
  if (stats.graphrag_score >= stats.rag_score && stats.graphrag_score >= stats.llm_score) {
    return 'GraphRAG'
  } else if (stats.rag_score >= stats.llm_score) {
    return 'RAG'
  } else {
    return 'LLM'
  }
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

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 24px;
}

.metric-section {
  background: #fafafa;
  border-radius: 12px;
  padding: 20px;
  
  h4 {
    margin: 0 0 16px 0;
    font-size: 14px;
    font-weight: 600;
    color: #666;
    padding-bottom: 12px;
    border-bottom: 1px solid #e0e0e0;
  }
  
  .metric-items {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }
  
  .metric-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 8px 0;
    
    .metric-label {
      font-size: 13px;
      color: #888;
    }
    
    .metric-value {
      font-size: 16px;
      font-weight: 700;
      color: #333;
    }
  }
}

.overall-score {
  margin-top: 24px;
  display: flex;
  gap: 24px;
  align-items: flex-start;
  
  .score-circle {
    width: 160px;
    height: 160px;
    border-radius: 50%;
    background: linear-gradient(135deg, #d4af37 0%, #b8860b 100%);
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    color: white;
    box-shadow: 0 8px 24px rgba(212, 175, 55, 0.4);
    
    .score-value {
      font-size: 48px;
      font-weight: 700;
      line-height: 1;
    }
    
    .score-label {
      font-size: 12px;
      opacity: 0.9;
      margin-top: 8px;
    }
  }
  
  .recommendations {
    flex: 1;
    background: #fafafa;
    border-radius: 12px;
    padding: 16px 20px;
    
    h4 {
      margin: 0 0 12px 0;
      font-size: 14px;
      font-weight: 600;
      color: #666;
    }
    
    ul {
      margin: 0;
      padding-left: 20px;
      
      li {
        font-size: 13px;
        color: #555;
        margin-bottom: 8px;
        
        &:last-child {
          margin-bottom: 0;
        }
      }
    }
  }
}

.question-input {
  display: flex;
  gap: 12px;
  margin-bottom: 24px;
  
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

.answers-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  margin-bottom: 24px;
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
    margin-bottom: 12px;
    min-height: 80px;
  }
  
  .answer-metrics {
    display: flex;
    gap: 16px;
    font-size: 12px;
    color: #888;
  }
}

.improvement-section {
  background: #fafafa;
  border-radius: 12px;
  padding: 20px;
  margin-bottom: 24px;
  
  h4 {
    margin: 0 0 16px 0;
    font-size: 14px;
    font-weight: 600;
    color: #666;
  }
  
  .improvement-bars {
    display: flex;
    flex-direction: column;
    gap: 16px;
  }
  
  .bar-item {
    display: flex;
    align-items: center;
    gap: 12px;
    
    .bar-label {
      width: 140px;
      font-size: 13px;
      color: #555;
      font-weight: 500;
    }
    
    .bar-container {
      flex: 1;
      height: 24px;
      background: #e0e0e0;
      border-radius: 12px;
      overflow: hidden;
    }
    
    .bar {
      height: 100%;
      border-radius: 12px;
      transition: width 0.8s ease;
    }
    
    .graphrag-bar {
      background: linear-gradient(90deg, #52c41a, #389e0d);
    }
    
    .rag-bar {
      background: linear-gradient(90deg, #faad14, #d48806);
    }
    
    .llm-bar {
      background: linear-gradient(90deg, #1890ff, #096dd9);
    }
    
    .bar-value {
      width: 80px;
      font-size: 14px;
      font-weight: 600;
      text-align: right;
      
      &.positive {
        color: #52c41a;
      }
      
      &.negative {
        color: #ff4d4f;
      }
    }
  }
}

.conclusion-section {
  background: linear-gradient(135deg, rgba(212, 175, 55, 0.1), rgba(184, 134, 11, 0.05));
  border-radius: 12px;
  padding: 20px;
  
  h4 {
    margin: 0 0 12px 0;
    font-size: 14px;
    font-weight: 600;
    color: #d4af37;
  }
  
  .conclusion-content {
    p {
      margin: 0;
      font-size: 14px;
      line-height: 1.6;
      color: #444;
      
      .highlight {
        font-weight: 700;
        color: #d4af37;
      }
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
</style>
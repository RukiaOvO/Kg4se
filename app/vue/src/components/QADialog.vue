<template>
  <n-modal
    v-model:show="show"
    class="qa-modal"
    preset="card"
    :title="`智能问答 - ${providerName}`"
    size="large"
    @after-leave="resetModal"
  >
    <div class="qa-container">
      <!-- Conversation History -->
      <div class="conversation-area">
        <n-empty
          v-if="messages.length === 0"
          description="开始提问以获得回答"
          size="small"
          style="margin-top: 20px;"
        >
          <template #icon>
            <n-icon><chatbubble-outline /></n-icon>
          </template>
        </n-empty>

        <div v-else class="messages-list">
          <div
            v-for="(msg, index) in messages"
            :key="index"
            :class="['message', `message-${msg.role}`]"
          >
            <div v-if="msg.role === 'user'" class="message-avatar user">
              <n-icon size="20"><person-circle-outline /></n-icon>
            </div>
            <div v-else class="message-avatar assistant">
              <n-icon size="20"><sparkles-outline /></n-icon>
            </div>

            <div class="message-content">
              <div v-if="msg.role === 'user'" class="user-content">
                {{ msg.content }}
              </div>
              <div v-else class="assistant-content">
                <!-- Markdown render for assistant messages -->
                <Markdown :source="msg.content" class="markdown-content" />
                
                <!-- Show context if available -->
                <div v-if="msg.context" class="context-info">
                  <n-collapse>
                    <n-collapse-item title="📚 参考信息" name="context">
                      <div class="context-text">{{ msg.context }}</div>
                    </n-collapse-item>
                  </n-collapse>
                </div>
              </div>
            </div>
          </div>

          <!-- Loading indicator -->
          <div v-if="loading" class="message message-loading">
            <div class="message-avatar assistant">
              <n-icon size="20"><sparkles-outline /></n-icon>
            </div>
            <div class="message-content">
              <n-spin size="small" />
              <span style="margin-left: 8px;">{{ streamingStatus || '思考中...' }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Input Area -->
      <div class="input-area">
        <div class="input-controls">
          <n-space>
            <n-radio-group v-model:value="qaMode" size="small">
              <n-radio value="graphrag">GraphRAG</n-radio>
              <n-radio value="rag">RAG</n-radio>
              <n-radio value="llm">LLM</n-radio>
            </n-radio-group>
            <n-button
              v-if="messages.length > 0"
              type="error"
              text
              @click="clearMessages"
              size="small"
            >
              清空历史
            </n-button>
          </n-space>
        </div>

        <div class="input-box">
          <n-input
            v-model:value="inputQuestion"
            type="textarea"
            placeholder="输入您的问题... (按 Ctrl+Enter 提交)"
            :rows="3"
            :disabled="loading"
            @keydown.ctrl.enter="handleAsk"
            @keydown.meta.enter="handleAsk"
          />
        </div>

        <div class="input-footer">
          <n-space justify="end">
            <n-button @click="show = false">关闭</n-button>
            <n-button
              type="primary"
              :loading="loading"
              :disabled="!inputQuestion.trim() || loading"
              @click="handleAsk"
            >
              提交
            </n-button>
          </n-space>
        </div>
      </div>
    </div>
  </n-modal>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick } from 'vue'
import {
  NModal,
  NEmpty,
  NIcon,
  NSpin,
  NInput,
  NButton,
  NSpace,
  NRadioGroup,
  NRadio,
  NCollapse,
  NCollapseItem,
  useMessage
} from 'naive-ui'
import {
  ChatbubbleOutline,
  PersonCircleOutline
} from '@vicons/ionicons5'
import { checkQAHealth, QAMode, Message } from '@/api/services'
import { askQuestionStream } from '@/api/services'

interface ConversationMessage extends Message {
  context?: string
}

const props = withDefaults(
  defineProps<{
    modelValue?: boolean
  }>(),
  {
    modelValue: false
  }
)

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
}>()

const message = useMessage()

// State
const show = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value)
})

const messages = ref<ConversationMessage[]>([])
const inputQuestion = ref('')
const loading = ref(false)
const qaMode = ref<QAMode>('graphrag')
const providerName = ref('AI')
const streamingStatus = ref('')
const abortController = ref<AbortController | null>(null)

// Initialize
watch(
  () => show.value,
  async (newVal) => {
    if (newVal) {
      await initializeQA()
    }
  }
)

async function initializeQA() {
  try {
    const health = await checkQAHealth()
    const providerMap: Record<string, string> = {
      openai: 'OpenAI',
      qwen: 'Qwen',
      glm: '智谱GLM',
      deepseek: 'DeepSeek',
      anthropic: 'Claude',
      ollama: 'Ollama',
      mock: '模拟'
    }
    providerName.value = providerMap[health.provider] || health.provider

    if (health.status !== 'healthy') {
      message.warning(`AI服务不可用 (${health.provider})`)
    }
  } catch (error) {
    console.error('Failed to initialize QA:', error)
    message.error('QA服务初始化失败')
  }
}

async function handleAsk() {
  const question = inputQuestion.value.trim()
  if (!question) {
    message.warning('请输入问题')
    return
  }

  try {
    loading.value = true
    streamingStatus.value = '准备中...'

    messages.value.push({
      role: 'user',
      content: question
    })

    const conversationHistory: Message[] = messages.value
      .filter((m) => m.role !== undefined)
      .map((m) => ({
        role: m.role as 'user' | 'assistant',
        content: m.content
      }))

    const assistantIndex = messages.value.length
    messages.value.push({
      role: 'assistant',
      content: ''
    })

    abortController.value = askQuestionStream(
      {
        question,
        conversation_history: conversationHistory.slice(0, -1),
        mode: qaMode.value
      },
      (token) => {
        const msg = messages.value[assistantIndex]
        if (msg) msg.content += token
      },
      (status) => {
        streamingStatus.value = status
      },
      (result) => {
        const msg = messages.value[assistantIndex]
        if (msg) {
          msg.content = result.answer
          msg.context = result.context_snippet
        }
        streamingStatus.value = ''
        loading.value = false
        abortController.value = null
      },
      (error) => {
        const msg = messages.value[assistantIndex]
        if (msg && !msg.content) {
          msg.content = `回答生成失败: ${error}`
        }
        streamingStatus.value = ''
        loading.value = false
        abortController.value = null
      }
    )

    inputQuestion.value = ''

    await nextTick()
    scrollToBottom()
  } catch (error) {
    console.error('Error asking question:', error)
    message.error('请求失败，请检查网络连接')
    messages.value.pop()
    loading.value = false
  }
}

function clearMessages() {
  if (abortController.value) {
    abortController.value.abort()
    abortController.value = null
  }
  messages.value = []
  inputQuestion.value = ''
  streamingStatus.value = ''
  loading.value = false
}

function resetModal() {
  if (abortController.value) {
    abortController.value.abort()
    abortController.value = null
  }
  messages.value = []
  inputQuestion.value = ''
  loading.value = false
  streamingStatus.value = ''
}

function scrollToBottom() {
  const container = document.querySelector('.messages-list')
  if (container) {
    container.scrollTop = container.scrollHeight
  }
}
</script>

<style scoped>
.qa-container {
  display: flex;
  flex-direction: column;
  height: 600px;
  background: linear-gradient(135deg, rgba(212, 175, 55, 0.05), rgba(185, 134, 11, 0.05));
}

.conversation-area {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  margin-bottom: 16px;
  border: 1px solid rgba(212, 175, 55, 0.2);
  border-radius: 8px;
  background-color: rgba(255, 255, 255, 0.5);
}

.messages-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.message {
  display: flex;
  gap: 12px;
  animation: slideIn 0.3s ease;
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.message-user {
  justify-content: flex-end;
}

.message-loading {
  justify-content: flex-start;
}

.message-avatar {
  flex-shrink: 0;
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
}

.message-avatar.user {
  background: linear-gradient(135deg, #d4af37, #b8860b);
  color: white;
}

.message-avatar.assistant {
  background: linear-gradient(135deg, #c9a668, #9a7509);
  color: white;
}

.message-content {
  flex: 1;
  max-width: 70%;
}

.message-user .message-content {
  max-width: 70%;
}

.user-content {
  background: linear-gradient(135deg, rgba(212, 175, 55, 0.2), rgba(185, 134, 11, 0.2));
  padding: 12px 16px;
  border-radius: 12px;
  border-left: 3px solid #d4af37;
  color: #333;
  word-break: break-word;
}

.assistant-content {
  background: rgba(255, 255, 255, 0.8);
  padding: 12px 16px;
  border-radius: 12px;
  border-left: 3px solid #c9a668;
  color: #333;
}

.markdown-content {
  line-height: 1.7;
  word-break: break-word;
}

.markdown-content :deep(h1),
.markdown-content :deep(h2),
.markdown-content :deep(h3),
.markdown-content :deep(h4) {
  margin: 12px 0 8px;
  font-weight: 600;
  color: #333;
}

.markdown-content :deep(h1) { font-size: 18px; }
.markdown-content :deep(h2) { font-size: 16px; }
.markdown-content :deep(h3) { font-size: 15px; }
.markdown-content :deep(h4) { font-size: 14px; }

.markdown-content :deep(p) {
  margin: 0 0 8px;
  line-height: 1.7;
}

.markdown-content :deep(ul),
.markdown-content :deep(ol) {
  margin: 4px 0 8px;
  padding-left: 20px;
}

.markdown-content :deep(li) {
  margin: 2px 0;
  line-height: 1.6;
}

.markdown-content :deep(code) {
  font-size: 13px;
  padding: 1px 5px;
  border-radius: 3px;
  background: rgba(0, 0, 0, 0.06);
  color: #d63384;
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
}

.markdown-content :deep(pre) {
  margin: 8px 0;
  padding: 12px;
  border-radius: 8px;
  background: #1e1e1e;
  overflow-x: auto;
  font-size: 13px;
  line-height: 1.5;
}

.markdown-content :deep(pre code) {
  background: none;
  color: #d4d4d4;
  padding: 0;
}

.markdown-content :deep(table) {
  width: 100%;
  border-collapse: collapse;
  margin: 8px 0;
  font-size: 13px;
}

.markdown-content :deep(th),
.markdown-content :deep(td) {
  padding: 6px 10px;
  border: 1px solid #e0e0e0;
  text-align: left;
}

.markdown-content :deep(th) {
  background: #f5f5f5;
  font-weight: 600;
}

.markdown-content :deep(blockquote) {
  margin: 8px 0;
  padding: 6px 12px;
  border-left: 3px solid #d4af37;
  background: #fafafa;
  color: #666;
}

.markdown-content :deep(strong) {
  font-weight: 700;
  color: #333;
}

.markdown-content :deep(a) {
  color: #1890ff;
  text-decoration: none;
}

.markdown-content :deep(a:hover) {
  text-decoration: underline;
}

.context-info {
  margin-top: 12px;
  font-size: 12px;
}

.context-text {
  max-height: 150px;
  overflow-y: auto;
  padding: 8px;
  background: rgba(212, 175, 55, 0.05);
  border-radius: 4px;
  font-family: 'Courier New', monospace;
  white-space: pre-wrap;
  word-break: break-word;
  color: #666;
}

.input-area {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 12px;
  background: rgba(255, 255, 255, 0.8);
  border-radius: 8px;
  border: 1px solid rgba(212, 175, 55, 0.2);
}

.input-controls {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.mode-icon {
  margin-right: 4px;
  font-size: 14px;
}

.input-box {
  flex: 1;
}

.input-footer {
  display: flex;
  justify-content: flex-end;
}

/* Responsive */
@media (max-width: 768px) {
  .qa-container {
    height: 500px;
  }

  .message-content {
    max-width: 85% !important;
  }
}
</style>

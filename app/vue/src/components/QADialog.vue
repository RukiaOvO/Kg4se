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
                <!-- Markdown support for assistant messages -->
                <div class="answer-text" v-html="formatAnswer(msg.content)"></div>
                
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
              <span style="margin-left: 8px;">思考中...</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Input Area -->
      <div class="input-area">
        <div class="input-controls">
          <n-space>
            <n-checkbox v-model:checked="useKG" size="small">
              使用知识图谱
            </n-checkbox>
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
  NCheckbox,
  NCollapse,
  NCollapseItem,
  useMessage
} from 'naive-ui'
import {
  ChatbubbleOutline,
  PersonCircleOutline,
  SparkliesOutline
} from '@vicons/ionicons5'
import { askQuestion, Message, checkQAHealth } from '@/api/services'

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
const useKG = ref(true)
const providerName = ref('AI')
const messagesContainer = ref<HTMLElement>()

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

    // Add user message
    messages.value.push({
      role: 'user',
      content: question
    })

    // Prepare conversation history
    const conversationHistory: Message[] = messages.value
      .filter((m) => m.role !== undefined)
      .map((m) => ({
        role: m.role as 'user' | 'assistant',
        content: m.content
      }))

    // Get answer
    const response = await askQuestion({
      question,
      conversation_history: conversationHistory.slice(0, -1), // Exclude current user message
      use_kg: useKG.value
    })

    if (response.success) {
      messages.value.push({
        role: 'assistant',
        content: response.answer,
        context: response.context_snippet
      })
    } else {
      message.error(response.error || '获取答案失败')
      messages.value.pop() // Remove user message if failed
    }

    inputQuestion.value = ''

    // Scroll to bottom
    await nextTick()
    scrollToBottom()
  } catch (error) {
    console.error('Error asking question:', error)
    message.error('请求失败，请检查网络连接')
    messages.value.pop() // Remove user message on error
  } finally {
    loading.value = false
  }
}

function clearMessages() {
  messages.value = []
  inputQuestion.value = ''
}

function resetModal() {
  messages.value = []
  inputQuestion.value = ''
  loading.value = false
}

function scrollToBottom() {
  const container = document.querySelector('.messages-list')
  if (container) {
    container.scrollTop = container.scrollHeight
  }
}

// Format answer with basic markdown support
function formatAnswer(text: string): string {
  let formatted = text
    // Bold
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    // Italic
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    // Code
    .replace(/`(.*?)`/g, '<code>$1</code>')
    // Line breaks
    .replace(/\n/g, '<br>')
    // Lists
    .replace(/^- (.*?)$/gm, '<li>$1</li>')

  // Wrap consecutive list items in ul
  formatted = formatted.replace(/(<li>.*?<\/li>[\n]?)+/gs, (match) => `<ul>${match}</ul>`)

  return formatted
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

.answer-text {
  line-height: 1.6;
  word-break: break-word;
}

.answer-text strong {
  color: #d4af37;
  font-weight: 600;
}

.answer-text code {
  background: rgba(212, 175, 55, 0.1);
  padding: 2px 6px;
  border-radius: 4px;
  font-family: 'Courier New', monospace;
  color: #b8860b;
}

.answer-text ul {
  margin: 8px 0;
  padding-left: 24px;
}

.answer-text li {
  margin: 4px 0;
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

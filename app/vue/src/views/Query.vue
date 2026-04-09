<template>
  <div class="query-page">
    <div class="query-header">
      <h1 class="query-title">
        <n-gradient-text type="info">
          {{ t('query.title') }}
        </n-gradient-text>
      </h1>
      <p class="query-subtitle">使用 Cypher 查询语言探索知识图谱</p>
    </div>

    <n-card>
      <n-tabs v-model:value="activeTab" type="line">
        <n-tab-pane :name="'cypher'" :tab="t('query.cypher_query')">
          <n-space vertical :size="16">
            <n-input
              v-model:value="cypherQuery"
              type="textarea"
              :rows="8"
              :placeholder="t('query.cypher_help')"
            />

            <n-button type="primary" :loading="executing" @click="executeCypher">
              <template #icon>
                <n-icon><play-outline /></n-icon>
              </template>
              {{ t('query.execute') }}
            </n-button>
          </n-space>
        </n-tab-pane>

        <n-tab-pane :name="'nodes'" :tab="t('query.get_nodes')">
          <n-space :size="16" style="margin-bottom: 16px">
            <n-input
              v-model:value="nodeLabel"
              :placeholder="t('query.label_help')"
              clearable
              style="width: 200px"
            >
              <template #prefix>
                {{ t('query.label_optional') }}:
              </template>
            </n-input>

            <n-input-number
              v-model:value="nodeLimit"
              :min="1"
              :max="1000"
              style="width: 150px"
            >
              <template #prefix>
                {{ t('query.limit') }}:
              </template>
            </n-input-number>

            <n-button type="primary" :loading="fetchingNodes" @click="fetchNodes">
              <template #icon>
                <n-icon><search-outline /></n-icon>
              </template>
              {{ t('query.get_nodes_btn') }}
            </n-button>
          </n-space>
        </n-tab-pane>

        <n-tab-pane :name="'edges'" :tab="t('query.get_edges')">
          <n-space :size="16" style="margin-bottom: 16px">
            <n-input
              v-model:value="relType"
              :placeholder="t('query.rel_type_help')"
              clearable
              style="width: 200px"
            >
              <template #prefix>
                {{ t('query.rel_type_optional') }}:
              </template>
            </n-input>

            <n-input-number
              v-model:value="edgeLimit"
              :min="1"
              :max="1000"
              style="width: 150px"
            >
              <template #prefix>
                {{ t('query.limit') }}:
              </template>
            </n-input-number>

            <n-button type="primary" :loading="fetchingEdges" @click="fetchEdges">
              <template #icon>
                <n-icon><search-outline /></n-icon>
              </template>
              {{ t('query.get_edges_btn') }}
            </n-button>
          </n-space>
        </n-tab-pane>
      </n-tabs>

      <n-divider v-if="queryResult" />

      <div v-if="queryResult" class="query-result">
        <n-alert type="success" :show-icon="true" style="margin-bottom: 16px">
          {{ t('query.success') }}
        </n-alert>

        <n-tabs v-model:value="resultView" type="card">
          <n-tab-pane :name="'table'" :tab="t('query.view_result')">
            <n-data-table
              :columns="resultColumns"
              :data="queryResult"
              :pagination="{ pageSize: 10 }"
              :scroll-x="1200"
            />
          </n-tab-pane>

          <n-tab-pane :name="'json'" :tab="t('query.view_raw_json')">
            <n-code :code="JSON.stringify(queryResult, null, 2)" language="json" />
          </n-tab-pane>
        </n-tabs>
      </div>
    </n-card>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useMessage } from 'naive-ui'
import { PlayOutline, SearchOutline } from '@vicons/ionicons5'
import { executeCypherQuery, getNodes, getEdges } from '@/api/services'

const { t } = useI18n()
const message = useMessage()

const activeTab = ref('cypher')
const cypherQuery = ref('')
const nodeLabel = ref('')
const nodeLimit = ref(100)
const relType = ref('')
const edgeLimit = ref(100)
const executing = ref(false)
const fetchingNodes = ref(false)
const fetchingEdges = ref(false)
const queryResult = ref(null)
const resultView = ref('table')

const resultColumns = computed(() => {
  if (!queryResult.value || queryResult.value.length === 0) return []

  const firstRow = queryResult.value[0]
  return Object.keys(firstRow).map(key => ({
    title: key,
    key: key,
    ellipsis: {
      tooltip: true
    },
    render: (row) => {
      const value = row[key]
      if (typeof value === 'object') {
        return JSON.stringify(value)
      }
      return String(value || '')
    }
  }))
})

const executeCypher = async () => {
  if (!cypherQuery.value.trim()) {
    message.warning(t('query.enter_cypher'))
    return
  }

  executing.value = true
  try {
    const result = await executeCypherQuery(cypherQuery.value)
    if (Array.isArray(result) && result.length > 0) {
      queryResult.value = result
      message.success(t('query.success'))
    } else {
      message.warning(t('query.no_results'))
      queryResult.value = null
    }
  } catch (error) {
    message.error(t('common.error') + ': ' + error.message)
    queryResult.value = null
  } finally {
    executing.value = false
  }
}

const fetchNodes = async () => {
  fetchingNodes.value = true
  try {
    const result = await getNodes(nodeLabel.value || null, nodeLimit.value)
    if (Array.isArray(result) && result.length > 0) {
      queryResult.value = result
      message.success(t('query.found_nodes', { count: result.length }))
    } else {
      message.warning(t('query.no_nodes_found'))
      queryResult.value = null
    }
  } catch (error) {
    message.error(t('common.error') + ': ' + error.message)
    queryResult.value = null
  } finally {
    fetchingNodes.value = false
  }
}

const fetchEdges = async () => {
  fetchingEdges.value = true
  try {
    const result = await getEdges(relType.value || null, edgeLimit.value)
    if (Array.isArray(result) && result.length > 0) {
      queryResult.value = result
      message.success(t('query.found_edges', { count: result.length }))
    } else {
      message.warning(t('query.no_edges_found'))
      queryResult.value = null
    }
  } catch (error) {
    message.error(t('common.error') + ': ' + error.message)
    queryResult.value = null
  } finally {
    fetchingEdges.value = false
  }
}


</script>

<style lang="scss" scoped>
.query-page {
  padding: 32px 48px;
  background: #f5f7fa;
  min-height: calc(100vh - 70px);
  position: relative;

  &::before {
    content: '';
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background:
      radial-gradient(circle at 20% 20%, rgba(59, 130, 246, 0.05) 0%, transparent 50%),
      radial-gradient(circle at 80% 80%, rgba(96, 165, 250, 0.05) 0%, transparent 50%),
      radial-gradient(circle at 50% 50%, rgba(37, 99, 235, 0.03) 0%, transparent 60%);
    pointer-events: none;
    z-index: 0;
  }

  > * {
    position: relative;
    z-index: 1;
  }

  .query-header {
    margin-bottom: 32px;
    padding: 32px 36px;
    background: linear-gradient(135deg,
      rgba(236, 254, 255, 0.95) 0%,
      rgba(224, 242, 254, 0.95) 50%,
      rgba(219, 234, 254, 0.95) 100%);
    border-radius: 24px;
    backdrop-filter: blur(20px);
    box-shadow:
      0 8px 32px rgba(0, 0, 0, 0.06),
      0 2px 8px rgba(0, 0, 0, 0.04),
      inset 0 1px 0 rgba(255, 255, 255, 0.8);
    border: 1px solid rgba(255, 255, 255, 0.6);
    position: relative;
    overflow: hidden;

    &::before {
      content: '';
      position: absolute;
      top: 0;
      left: 0;
      right: 0;
      height: 2px;
      background: linear-gradient(90deg,
        transparent,
        rgba(59, 130, 246, 0.4),
        transparent);
    }

    .query-title {
      font-size: 36px;
      font-weight: 700;
      margin: 0 0 10px 0;
      letter-spacing: -0.5px;
    }

    .query-subtitle {
      font-size: 15px;
      color: #64748b;
      margin: 0;
      font-weight: 500;
    }
  }

  :deep(.n-card) {
    border-radius: 24px;
    box-shadow:
      0 8px 32px rgba(0, 0, 0, 0.06),
      0 2px 12px rgba(0, 0, 0, 0.04);
    border: 1px solid rgba(255, 255, 255, 0.6);
    backdrop-filter: blur(10px);
    transition: all 0.3s;

    &:hover {
      box-shadow:
        0 12px 40px rgba(0, 0, 0, 0.08),
        0 4px 16px rgba(0, 0, 0, 0.06);
    }
  }

  :deep(.n-tabs) {
    .n-tabs-nav {
      background: linear-gradient(135deg,
        rgba(248, 250, 252, 0.8) 0%,
        rgba(241, 245, 249, 0.8) 100%);
      backdrop-filter: blur(10px);
      border-radius: 20px;
      padding: 8px;
      margin-bottom: 24px;
    }

    .n-tabs-tab {
      font-weight: 700;
      padding: 14px 24px;
      border-radius: 16px;
      transition: all 0.3s;
      letter-spacing: 0.2px;

      &:hover {
        background: rgba(255, 255, 255, 0.8);
      }

      &.n-tabs-tab--active {
        background: linear-gradient(135deg,
          rgba(255, 255, 255, 1) 0%,
          rgba(248, 250, 252, 1) 100%);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
      }
    }
  }

  :deep(.n-input),
  :deep(.n-input-number) {
    .n-input__border,
    .n-input__state-border {
      border-radius: 16px;
    }

    textarea {
      border-radius: 16px;
      font-family: 'Cascadia Code', 'Fira Code', monospace;
      font-size: 14px;
      line-height: 1.6;
    }
  }

  :deep(.n-button) {
    border-radius: 16px;
    font-weight: 700;
    letter-spacing: 0.3px;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    height: 44px;
    padding: 0 28px;

    &:not(:disabled):hover {
      transform: translateY(-2px);
    }

    &.n-button--primary-type {
      box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);

      &:hover {
        box-shadow: 0 6px 16px rgba(59, 130, 246, 0.4);
      }
    }
  }

  .query-result {
    margin-top: 24px;
    animation: fadeInUp 0.6s ease-out;

    :deep(.n-alert) {
      border-radius: 16px;
      padding: 16px 20px;
      font-weight: 600;
    }

    :deep(.n-data-table) {
      .n-data-table-th {
        background: linear-gradient(135deg,
          rgba(248, 250, 252, 0.9) 0%,
          rgba(241, 245, 249, 0.9) 100%);
        font-weight: 700;
        font-size: 14px;
        letter-spacing: 0.2px;
      }

      .n-data-table-td {
        font-size: 14px;
      }
    }

    :deep(.n-code) {
      border-radius: 16px;
      background: linear-gradient(135deg,
        rgba(15, 23, 42, 0.98) 0%,
        rgba(30, 41, 59, 0.98) 100%);
    }
  }
}

@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(30px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.query-card {
  height: calc(100vh - 240px);
  display: flex;
  flex-direction: column;
  border-radius: 24px;
  overflow: hidden;
}

.messages-container {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
  background: linear-gradient(135deg,
    rgba(248, 250, 252, 0.8) 0%,
    rgba(241, 245, 249, 0.8) 100%);
}

.welcome-message {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;

  .welcome-hint {
    color: #64748b;
    font-size: 14px;
    margin-top: 8px;
  }
}

.messages {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.message {
  display: flex;
  gap: 16px;
  animation: fadeInUp 0.3s ease-out;

  &.user {
    flex-direction: row-reverse;

    .message-content {
      align-items: flex-end;
    }

    .message-body {
      background: linear-gradient(135deg, #3b82f6, #1e40af);
      color: white;
      border-radius: 18px 18px 4px 18px;
    }
  }

  &.assistant {
    .message-body {
      background: white;
      border: 1px solid rgba(226, 232, 240, 0.8);
      border-radius: 18px 18px 18px 4px;
    }
  }
}

.message-avatar {
  flex-shrink: 0;
}

.message-content {
  flex: 1;
  max-width: 80%;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.message-header {
  display: flex;
  align-items: center;
  gap: 8px;

  strong {
    font-weight: 600;
    color: #1e293b;
  }

  .message-time {
    font-size: 12px;
    color: #94a3b8;
  }
}

.message-body {
  padding: 16px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);

  :deep(.markdown-content) {
    line-height: 1.6;

    h1, h2, h3, h4 {
      margin-top: 1em;
      margin-bottom: 0.5em;
      font-weight: 600;
    }

    code {
      background: rgba(0, 0, 0, 0.05);
      padding: 2px 6px;
      border-radius: 4px;
      font-family: 'Fira Code', monospace;
    }

    pre {
      background: #1e293b;
      color: #e2e8f0;
      padding: 16px;
      border-radius: 8px;
      overflow-x: auto;
      margin: 16px 0;
    }
  }
}

.context-info {
  margin-top: 8px;
}

.input-area {
  padding: 20px;
  border-top: 1px solid rgba(226, 232, 240, 0.8);
  background: white;

  :deep(.n-input) {
    .n-input__border {
      border-radius: 16px;
    }

    textarea {
      font-size: 16px;
      line-height: 1.5;
    }
  }
}

.input-actions {
  margin-top: 12px;
  display: flex;
  justify-content: flex-end;
}

.quick-questions {
  margin-top: 24px;
  padding: 20px;
  background: white;
  border-radius: 20px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.06);

  h3 {
    margin: 0 0 16px 0;
    font-size: 16px;
    font-weight: 600;
    color: #475569;
  }

  .quick-buttons {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
  }
}

@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

</style>


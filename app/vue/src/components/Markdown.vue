<template>
  <div class="markdown-renderer" v-html="renderedContent"></div>
</template>

<script setup lang="ts">
import { computed, ref, watch, onMounted } from 'vue'
import { marked } from 'marked'
import hljs from 'highlight.js'
import 'highlight.js/styles/github-dark.css'

interface Props {
  source: string
  options?: {
    sanitize?: boolean
    breaks?: boolean
    gfm?: boolean
  }
}

const props = withDefaults(defineProps<Props>(), {
  source: '',
  options: () => ({
    sanitize: true,
    breaks: true,
    gfm: true
  })
})

// 配置 marked
marked.setOptions({
  highlight: (code, language) => {
    const validLanguage = hljs.getLanguage(language) ? language : 'plaintext'
    return hljs.highlight(code, { language: validLanguage }).value
  },
  langPrefix: 'hljs language-',
  breaks: props.options.breaks,
  gfm: props.options.gfm,
  sanitize: props.options.sanitize
})

const renderedContent = computed(() => {
  try {
    return marked(props.source)
  } catch (error) {
    console.error('Markdown渲染失败:', error)
    return `<pre>${props.source}</pre>`
  }
})

// 复制代码功能
const handleCopyCode = (event: Event) => {
  const target = event.target as HTMLElement
  if (target.classList.contains('copy-code-btn')) {
    const codeBlock = target.parentElement?.querySelector('code')
    if (codeBlock) {
      navigator.clipboard.writeText(codeBlock.textContent || '')
        .then(() => {
          target.textContent = '已复制'
          setTimeout(() => {
            target.textContent = '复制'
          }, 2000)
        })
        .catch(err => console.error('复制失败:', err))
    }
  }
}

// 点击链接在新窗口打开
const handleLinkClick = (event: Event) => {
  const target = event.target as HTMLElement
  if (target.tagName === 'A') {
    event.preventDefault()
    window.open(target.getAttribute('href') || '', '_blank')
  }
}

onMounted(() => {
  // 添加复制按钮到代码块
  const preElements = document.querySelectorAll('.markdown-renderer pre')
  preElements.forEach(pre => {
    const copyButton = document.createElement('button')
    copyButton.className = 'copy-code-btn'
    copyButton.textContent = '复制'
    pre.appendChild(copyButton)
  })
})

// 监听内容变化
watch(() => props.source, () => {
  // 重新渲染后重新绑定事件
  setTimeout(() => {
    const container = document.querySelector('.markdown-renderer')
    if (container) {
      container.addEventListener('click', handleCopyCode)
      container.addEventListener('click', handleLinkClick)
    }
  }, 100)
})
</script>

<style scoped>
.markdown-renderer {
  line-height: 1.6;
  word-wrap: break-word;
}

.markdown-renderer :deep(h1),
.markdown-renderer :deep(h2),
.markdown-renderer :deep(h3),
.markdown-renderer :deep(h4) {
  margin-top: 1.5em;
  margin-bottom: 0.8em;
  font-weight: 600;
}

.markdown-renderer :deep(p) {
  margin: 1em 0;
}

.markdown-renderer :deep(a) {
  color: #0366d6;
  text-decoration: none;
}

.markdown-renderer :deep(a:hover) {
  text-decoration: underline;
}

.markdown-renderer :deep(ul),
.markdown-renderer :deep(ol) {
  padding-left: 2em;
  margin: 1em 0;
}

.markdown-renderer :deep(blockquote) {
  border-left: 4px solid #dfe2e5;
  padding-left: 1em;
  margin: 1em 0;
  color: #6a737d;
}

.markdown-renderer :deep(pre) {
  position: relative;
  background: #1a1a1a;
  border-radius: 6px;
  padding: 1em;
  margin: 1em 0;
  overflow-x: auto;
}

.markdown-renderer :deep(code) {
  font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
  font-size: 0.9em;
}

.markdown-renderer :deep(pre code) {
  background: transparent;
  padding: 0;
  color: inherit;
}

.markdown-renderer :deep(.copy-code-btn) {
  position: absolute;
  top: 8px;
  right: 8px;
  padding: 4px 8px;
  background: #2d3748;
  color: white;
  border: none;
  border-radius: 4px;
  font-size: 12px;
  cursor: pointer;
  opacity: 0;
  transition: opacity 0.2s;
}

.markdown-renderer :deep(pre:hover .copy-code-btn) {
  opacity: 1;
}

.markdown-renderer :deep(table) {
  border-collapse: collapse;
  width: 100%;
  margin: 1em 0;
}

.markdown-renderer :deep(th),
.markdown-renderer :deep(td) {
  border: 1px solid #dfe2e5;
  padding: 8px 12px;
  text-align: left;
}

.markdown-renderer :deep(th) {
  background-color: #f6f8fa;
  font-weight: 600;
}

.markdown-renderer :deep(img) {
  max-width: 100%;
  height: auto;
}

.markdown-renderer :deep(.math) {
  overflow-x: auto;
  overflow-y: hidden;
}
</style>
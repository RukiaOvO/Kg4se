import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { listDocuments, getDocumentDetail, deleteDocument } from '@/api/services'
import type { DocumentListResponse, DocumentDetail } from '@/api/services'

export interface Document {
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
}

export const useDocumentStore = defineStore('document', () => {
  // State
  const documents = ref<Document[]>([])
  const currentDocument = ref<DocumentDetail | null>(null)
  const total = ref(0)
  const loading = ref(false)

  // Getters
  const documentCount = computed(() => documents.value.length)
  const completedDocuments = computed(() => 
    documents.value.filter(d => d.processing_status === 'completed')
  )
  const processingDocuments = computed(() =>
    documents.value.filter(d => 
      ['pending', 'processing', 'chunking', 'extracting'].includes(d.processing_status)
    )
  )

  // Actions
  const loadDocuments = async (skip: number = 0, limit: number = 50, sortBy: string = 'created_at') => {
    loading.value = true
    try {
      const result: DocumentListResponse = await listDocuments(skip, limit, sortBy)
      documents.value = result.documents
      total.value = result.total
    } finally {
      loading.value = false
    }
  }

  const loadDocumentDetail = async (documentId: string) => {
    loading.value = true
    try {
      currentDocument.value = await getDocumentDetail(documentId)
    } finally {
      loading.value = false
    }
  }

  const removeDocument = async (documentId: string) => {
    await deleteDocument(documentId)
    documents.value = documents.value.filter(doc => doc.id !== documentId)
    if (currentDocument.value?.id === documentId) {
      currentDocument.value = null
    }
  }

  const refreshDocumentStatus = async (documentId: string) => {
    try {
      const updatedDoc = await getDocumentDetail(documentId)
      const index = documents.value.findIndex(d => d.id === documentId)
      if (index !== -1) {
        documents.value[index] = {
          ...documents.value[index],
          ...updatedDoc
        }
      }
      if (currentDocument.value?.id === documentId) {
        currentDocument.value = updatedDoc
      }
    } catch (error) {
      console.error('刷新文档状态失败:', error)
    }
  }

  return {
    // State
    documents,
    currentDocument,
    total,
    loading,
    
    // Getters
    documentCount,
    completedDocuments,
    processingDocuments,
    
    // Actions
    loadDocuments,
    loadDocumentDetail,
    removeDocument,
    refreshDocumentStatus
  }
})
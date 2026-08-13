import { defineStore } from 'pinia'
import { uploadFile, retrieveKnowledge } from '../api'

export const useKnowledgeStore = defineStore('knowledge', {
  state: () => ({
    uploading: false,
    uploadResult: null,
    retrieving: false,
    searchResults: []
  }),
  actions: {
    async upload(file) {
      this.uploading = true
      try {
        const result = await uploadFile(file)
        this.uploadResult = result
        return result
      } finally {
        this.uploading = false
      }
    },
    async search(query, topK = 4) {
      this.retrieving = true
      try {
        const result = await retrieveKnowledge(query, topK)
        this.searchResults = result.docs || []
        return result
      } finally {
        this.retrieving = false
      }
    }
  }
})

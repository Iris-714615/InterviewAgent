import { defineStore } from 'pinia'
import { uploadFile, retrieveKnowledge, listFiles, deleteDocument, generateProfile, getProfiles, getPrivacyStatus, updatePrivacy, clearPrivacyData } from '../api'

export const useKnowledgeStore = defineStore('knowledge', {
  state: () => ({
    uploading: false,
    uploadResult: null,
    retrieving: false,
    searchResults: [],
    files: [],
    profile: null,
    profiles: [],
    privacy: null
  }),
  actions: {
    async upload(file, options = {}) {
      this.uploading = true
      try {
        const result = await uploadFile(file, options)
        this.uploadResult = result
        return result
      } finally {
        this.uploading = false
      }
    },
    async loadFiles(sessionId = null) {
      this.files = await listFiles(sessionId)
      return this.files
    },
    async remove(documentId) {
      const result = await deleteDocument(documentId)
      this.files = this.files.filter((file) => file.document_id !== documentId)
      return result
    },
    async search(query, topK = 4, sessionId = null) {
      this.retrieving = true
      try {
        const result = await retrieveKnowledge(query, topK, sessionId)
        this.searchResults = result.docs || []
        return result
      } finally {
        this.retrieving = false
      }
    },
    async generate(sessionId) {
      this.profile = await generateProfile(sessionId)
      return this.profile
    },
    async loadProfiles(sessionId) {
      const result = await getProfiles(sessionId)
      this.profiles = result.profiles || []
      this.profile = this.profiles[0] || this.profile
      return this.profiles
    },
    async loadPrivacy(sessionId) {
      this.privacy = await getPrivacyStatus(sessionId)
      return this.privacy
    },
    async setRetention(sessionId, days) {
      this.privacy = await updatePrivacy(sessionId, days)
      return this.privacy
    },
    async clearAll() {
      const result = await clearPrivacyData()
      this.files = []
      this.profile = null
      this.profiles = []
      this.privacy = null
      return result
    }
  }
})

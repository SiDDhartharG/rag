import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from './api'

const ACTIVE = new Set(['pending', 'indexing'])

export function useHealth() {
  return useQuery({ queryKey: ['health'], queryFn: api.health, refetchInterval: 5000, retry: false })
}

export function useRagConfig() {
  return useQuery({ queryKey: ['rag'], queryFn: api.getRag })
}

export function useSaveRag() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: api.putRag,
    onSuccess: (data) => qc.setQueryData(['rag'], data),
  })
}

export function useLlmConfig() {
  return useQuery({ queryKey: ['llm'], queryFn: api.getLlm })
}

export function useSaveLlm() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: api.putLlm,
    onSuccess: (data) => qc.setQueryData(['llm'], data),
  })
}

export function useDocuments() {
  return useQuery({
    queryKey: ['documents'],
    queryFn: api.listDocs,
    // Indexing runs in the background on the server, so poll while anything is still in progress.
    refetchInterval: (query) => (query.state.data?.some((d) => ACTIVE.has(d.status)) ? 1500 : false),
  })
}

export function useUpload() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: api.upload,
    onSettled: () => qc.invalidateQueries({ queryKey: ['documents'] }),
  })
}

export function useDeleteDoc() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: api.deleteDoc,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['documents'] }),
  })
}

export function useReindex() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: api.reindex,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['documents'] })
      qc.invalidateQueries({ queryKey: ['rag'] })
    },
  })
}

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import {
  addExperience,
  deleteExperience,
  getProfile,
  improveProfile,
  saveProfile,
  updateExperience,
  updatePersonalProfile,
  updateProfileSummary,
} from "@/features/profile/api"
import type { ProfileDraft } from "@/features/profile/types"
import { queryKeys } from "@/shared/lib/queryKeys"

export const profileQueryKey = queryKeys.profile

export function useProfile() {
  return useQuery({ queryKey: profileQueryKey, queryFn: ({ signal }) => getProfile(signal) })
}

export function useSaveProfile() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ profile, signal }: { profile: ProfileDraft; signal: AbortSignal }) =>
      saveProfile(profile, signal),
    onSuccess: (profile) => {
      queryClient.setQueryData(profileQueryKey, profile)
      void queryClient.invalidateQueries({ queryKey: queryKeys.cvAts })
    },
  })
}

export function useImproveProfile() {
  return useMutation({
    mutationFn: ({ profile, signal }: { profile: ProfileDraft; signal: AbortSignal }) =>
      improveProfile(profile, signal),
  })
}

export function useUpdateProfileSummary() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: updateProfileSummary,
    onSuccess: (profile) => queryClient.setQueryData(profileQueryKey, profile),
  })
}

export function useUpdatePersonalProfile() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: updatePersonalProfile,
    onSuccess: (profile) => queryClient.setQueryData(profileQueryKey, profile),
  })
}

export function useExperienceMutations() {
  const queryClient = useQueryClient()
  const invalidate = () => queryClient.invalidateQueries({ queryKey: profileQueryKey })
  return {
    add: useMutation({ mutationFn: addExperience, onSuccess: invalidate }),
    update: useMutation({ mutationFn: ({ id, ...payload }: { id: string } & Parameters<typeof updateExperience>[1]) => updateExperience(id, payload), onSuccess: invalidate }),
    remove: useMutation({ mutationFn: deleteExperience, onSuccess: invalidate }),
  }
}


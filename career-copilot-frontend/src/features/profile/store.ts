import { create } from "zustand"
import { createJSONStorage, persist } from "zustand/middleware"
import type { ProfileDraft } from "@/features/profile/types"

interface ProfileDraftState {
  draft: ProfileDraft | null
  setDraft: (draft: ProfileDraft) => void
  updateDraft: (updater: (current: ProfileDraft) => ProfileDraft) => void
  clearDraft: () => void
}

export const useProfileDraftStore = create<ProfileDraftState>()(
  persist(
    (set) => ({
      draft: null,
      setDraft: (draft) => set({ draft }),
      updateDraft: (updater) =>
        set((state) => (state.draft ? { draft: updater(state.draft) } : state)),
      clearDraft: () => set({ draft: null }),
    }),
    {
      name: "career-copilot-onboarding-draft",
      storage: createJSONStorage(() => sessionStorage),
      partialize: ({ draft }) => ({ draft }),
    },
  ),
)

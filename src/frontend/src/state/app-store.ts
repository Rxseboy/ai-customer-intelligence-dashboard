import { create } from "zustand";
import { persist } from "zustand/middleware";
import i18n from "../i18n/config";

interface AppState {
  language: "en" | "id";
  setLanguage: (lang: "en" | "id") => void;
  isChatOpen: boolean;
  setChatOpen: (open: boolean) => void;
}

export const useAppStore = create<AppState>()(
  persist(
    (set) => ({
      language: "en",
      setLanguage: (lang) => {
        i18n.changeLanguage(lang);
        set({ language: lang });
      },
      isChatOpen: false,
      setChatOpen: (open) => set({ isChatOpen: open }),
    }),
    {
      name: "app-storage",
      partialize: (state) => ({ language: state.language }), // only persist language
    }
  )
);

// frontend/src/store/projectStore.ts
import { create } from 'zustand';
import { listProjectFiles } from '../lib/apiClient'; // Adjust path
import type { ApiError } from '../types/projectManagement'; // Adjust path

interface ProjectState {
  availableProjectFiles: string[];
  isLoadingProjectFiles: boolean;
  projectFileError: ApiError | null;
  lastComponentsUpdateTimestamp: number | null; // For triggering UI refresh
  fetchAvailableProjectFiles: () => Promise<void>;
  notifyComponentsUpdated: () => void; // Action to update timestamp
}

const useProjectStore = create<ProjectState>((set) => ({
  availableProjectFiles: [],
  isLoadingProjectFiles: false,
  projectFileError: null,
  lastComponentsUpdateTimestamp: null,
  fetchAvailableProjectFiles: async () => {
    set({ isLoadingProjectFiles: true, projectFileError: null });
    try {
      const files = await listProjectFiles();
      set({ availableProjectFiles: files, isLoadingProjectFiles: false });
    } catch (error) {
      set({ projectFileError: error as ApiError, isLoadingProjectFiles: false });
      console.error("Failed to fetch project files:", error);
    }
  },
  notifyComponentsUpdated: () => {
    set({ lastComponentsUpdateTimestamp: Date.now() });
  }
}));

export default useProjectStore;

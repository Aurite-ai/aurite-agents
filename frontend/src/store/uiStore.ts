import { create } from 'zustand';
import type { ActionType } from '../components/layout/ActionTabs'; // Adjust path as needed
import type { ComponentType } from '../components/layout/ComponentSidebar'; // Adjust path as needed

interface UIState {
  selectedAction: ActionType;
  selectedComponent: ComponentType;
  setSelectedAction: (action: ActionType) => void;
  setSelectedComponent: (component: ComponentType) => void;
}

const useUIStore = create<UIState>((set) => ({
  selectedAction: 'configure', // Default action
  selectedComponent: 'agents', // Default component
  setSelectedAction: (action) => set({ selectedAction: action }),
  setSelectedComponent: (component) => set({ selectedComponent: component }),
}));

export default useUIStore;

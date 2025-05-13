import { create } from 'zustand';
import type { ActionType } from '../components/layout/Header'; // Adjust path as needed
import type { ConfigurableComponentType } from '../components/layout/ComponentSidebar'; // Adjust path as needed

interface UIState {
  selectedAction: ActionType;
  selectedComponent: ConfigurableComponentType;
  setSelectedAction: (action: ActionType) => void;
  setSelectedComponent: (component: ConfigurableComponentType) => void;
}

const useUIStore = create<UIState>((set) => ({
  selectedAction: 'configure', // Default action
  selectedComponent: 'agents', // Default component
  setSelectedAction: (action) => set({ selectedAction: action }),
  setSelectedComponent: (component) => set({ selectedComponent: component }),
}));

export default useUIStore;

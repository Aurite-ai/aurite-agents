import React from 'react';
import useUIStore from '../../../store/uiStore';
import AgentBuildView from './AgentBuildView';
import SimpleWorkflowBuildView from './SimpleWorkflowBuildView';
import ClientBuildView from './ClientBuildView';
import LLMBuildView from './LLMBuildView'; // Added
// Placeholder for other build views
// import CustomWorkflowBuildView from './CustomWorkflowBuildView';

const BuildView: React.FC = () => {
  const { selectedComponent } = useUIStore();

  const renderSelectedBuilder = () => {
    switch (selectedComponent) {
      case 'agents':
        return <AgentBuildView />;
      case 'llms':
        return <LLMBuildView />; // Render actual component
      case 'clients':
        return <ClientBuildView />;
      case 'simple_workflows':
        return <SimpleWorkflowBuildView />;
      case 'custom_workflows':
        // return <CustomWorkflowBuildView />;
        return <div className="p-4"><h3 className="text-lg font-semibold text-dracula-purple">Custom Workflow Builder</h3><p className="text-dracula-comment">Custom workflow builder UI will be here.</p></div>; // Placeholder
      case 'projects':
        return <div className="p-4"><p className="text-dracula-comment">Project configuration is managed via the 'Configure' tab or by loading/creating project files directly.</p></div>;
      default:
        return <div className="p-4"><p className="text-dracula-comment">Select a component type from the sidebar to start building.</p></div>;
    }
  };

  return (
    <div className="flex-grow p-1"> {/* Changed from p-4 to p-1 to match ExecuteView style */}
      {/* Header for the build section - might be dynamic based on selectedComponent */}
      {/* <h2 className="text-2xl font-semibold text-dracula-foreground mb-4">Build Components</h2> */}
      {renderSelectedBuilder()}
    </div>
  );
};

export default BuildView;

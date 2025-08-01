import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Layout from '@/components/layout/Layout';
import HomePage from '@/components/pages/HomePage';
import AgentsPage from '@/components/pages/AgentsPage';
import WorkflowsPage from '@/components/pages/WorkflowsPage';
import MCPClientsPage from '@/components/pages/MCPClientsPage';
import LLMConfigsPage from '@/components/pages/LLMConfigsPage';
import AgentForm from '@/components/forms/AgentForm';
import WorkflowForm from '@/components/forms/WorkflowForm';
import LLMConfigForm from '@/components/forms/LLMConfigForm';
import MCPClientForm from '@/components/forms/MCPClientForm';
import CustomWorkflowForm from '@/components/forms/CustomWorkflowForm';
import WorkflowRunnerDemo from '@/components/pages/WorkflowRunnerDemo';
import { useResizeObserverErrorHandler } from '@/hooks/useResizeObserverErrorHandler';

function App() {
  // Apply ResizeObserver error handling globally
  useResizeObserverErrorHandler();

  return (
    <BrowserRouter>
      <Routes>
        {/* Pages with Layout */}
        <Route path="/" element={<Layout><HomePage /></Layout>} />
        <Route path="/agents" element={<Layout><AgentsPage /></Layout>} />
        <Route path="/workflows" element={<Layout><WorkflowsPage /></Layout>} />
        <Route path="/mcp-clients" element={<Layout><MCPClientsPage /></Layout>} />
        <Route path="/llm-configs" element={<Layout><LLMConfigsPage /></Layout>} />
        
        {/* Forms with Layout */}
        <Route path="/agents/new" element={<Layout><AgentForm editMode={false} /></Layout>} />
        <Route path="/agents/:name/edit" element={<Layout><AgentForm editMode={true} /></Layout>} />
        <Route path="/workflows/new" element={<Layout><WorkflowForm editMode={false} /></Layout>} />
        <Route path="/workflows/:name/edit" element={<Layout><WorkflowForm editMode={true} /></Layout>} />
        <Route path="/workflows/custom/:name/edit" element={<Layout><CustomWorkflowForm editMode={true} /></Layout>} />
        <Route path="/workflows/run-demo" element={<Layout><WorkflowRunnerDemo /></Layout>} />
        <Route path="/mcp-clients/new" element={<Layout><MCPClientForm editMode={false} /></Layout>} />
        <Route path="/mcp-clients/:name/edit" element={<Layout><MCPClientForm editMode={true} /></Layout>} />
        <Route path="/llm-configs/new" element={<Layout><LLMConfigForm editMode={false} /></Layout>} />
        <Route path="/llm-configs/:name/edit" element={<Layout><LLMConfigForm editMode={true} /></Layout>} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;

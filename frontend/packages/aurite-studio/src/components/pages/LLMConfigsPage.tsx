import React from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Cloud, Plus, Edit, Play, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useLLMsWithConfigs } from '@/hooks/useLLMs';

export default function LLMConfigsPage() {
  const navigate = useNavigate();

  // API Hooks
  const { data: llms = [], isLoading: llmsLoading } = useLLMsWithConfigs();

  const handleNewLLMConfig = () => {
    // Navigate to new LLM config form
    navigate('/llm-configs/new');
  };

  const handleEditLLMConfig = (llm: any) => {
    const llmId = typeof llm.id === 'string' ? llm.id : (llm.id as any)?.name || 'unknown_llm';

    // Navigate to edit form
    navigate(`/llm-configs/${encodeURIComponent(llmId)}/edit`);
  };

  return (
    <motion.div
      initial={{ y: 20, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.5 }}
      className="w-full max-w-6xl mx-auto space-y-6"
    >
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-foreground">LLM Configs</h1>
          <p className="text-muted-foreground mt-1">
            Manage and configure your language model settings
          </p>
        </div>
        <Button className="gap-2" onClick={handleNewLLMConfig}>
          <Plus className="h-4 w-4" />
          New LLM Config
        </Button>
      </div>

      {/* Loading State */}
      {llmsLoading && (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      )}

      {/* Empty State */}
      {!llmsLoading && llms.length === 0 && (
        <motion.div
          initial={{ y: 20, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ delay: 0.1 }}
          className="bg-card border border-border rounded-lg p-12 text-center space-y-4"
        >
          <div className="w-16 h-16 bg-muted rounded-full flex items-center justify-center mx-auto">
            <Cloud className="h-8 w-8 text-muted-foreground" />
          </div>
          <div className="space-y-2">
            <h3 className="text-lg font-medium text-foreground">No LLM configurations yet</h3>
            <p className="text-sm text-muted-foreground max-w-md mx-auto">
              Configure your first language model to enable AI capabilities
            </p>
          </div>
          <Button className="gap-2" onClick={handleNewLLMConfig}>
            <Plus className="h-4 w-4" />
            Configure Your First LLM
          </Button>
        </motion.div>
      )}

      {/* LLM Configs Grid */}
      {!llmsLoading && llms.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {llms.map((llm, index) => {
            const llmId =
              typeof llm.id === 'string' ? llm.id : (llm.id as any)?.name || 'unknown_llm';
            return (
              <motion.div
                key={llmId}
                initial={{ y: 20, opacity: 0 }}
                animate={{ y: 0, opacity: 1 }}
                transition={{ delay: index * 0.1 }}
                className="gradient-card rounded-lg p-4 space-y-3 hover:shadow-md transition-all duration-200 gradient-glow"
              >
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <h3 className="font-semibold text-foreground">{llmId}</h3>
                    <div
                      className={`w-2 h-2 rounded-full ${llm.status === 'active' ? 'bg-green-500' : 'bg-gray-500'}`}
                    />
                  </div>
                  <p className="text-sm text-muted-foreground">
                    {llm.configFile ? 'Configured' : 'Configuration pending'}
                  </p>
                  <div className="flex items-center justify-between text-xs text-muted-foreground">
                    <span className="capitalize">Status: {llm.status}</span>
                  </div>
                </div>

                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    className="gap-1.5"
                    onClick={() => handleEditLLMConfig(llm)}
                  >
                    <Edit className="h-3.5 w-3.5" />
                    Configure
                  </Button>
                  <Button size="sm" className="gap-1.5">
                    <Play className="h-3.5 w-3.5" />
                    {llm.status === 'active' ? 'Deactivate' : 'Activate'}
                  </Button>
                </div>
              </motion.div>
            );
          })}
        </div>
      )}
    </motion.div>
  );
}

import React from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Cloud, Plus, Edit, TestTube, Loader2, CheckCircle, AlertTriangle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useLLMsWithConfigs, useTestLLM } from '@/hooks/useLLMs';
import { ProviderIcon } from '@/components/ui/ProviderIcon';
import { formatModelName, formatRelativeTime } from '@/utils/formatters';

export default function LLMConfigsPage() {
  const navigate = useNavigate();

  // State to track which LLM is currently being tested
  const [currentlyTestingId, setCurrentlyTestingId] = React.useState<string | null>(null);

  // State to track which LLMs have recently failed tests
  const [failedTests, setFailedTests] = React.useState<Set<string>>(new Set());

  // Callback functions for test results
  const handleMarkAsFailed = React.useCallback((llmConfigId: string) => {
    setFailedTests(prev => new Set(prev).add(llmConfigId));
  }, []);

  const handleMarkAsSuccess = React.useCallback((llmConfigId: string) => {
    setFailedTests(prev => {
      const newSet = new Set(prev);
      newSet.delete(llmConfigId);
      return newSet;
    });
  }, []);

  // API Hooks
  const { data: llms = [], isLoading: llmsLoading } = useLLMsWithConfigs();
  const testLLM = useTestLLM(handleMarkAsFailed, handleMarkAsSuccess);

  const handleNewLLMConfig = () => {
    // Navigate to new LLM config form
    navigate('/llm-configs/new');
  };

  const handleEditLLMConfig = (llm: any) => {
    const llmId = typeof llm.id === 'string' ? llm.id : (llm.id as any)?.name || 'unknown_llm';
    
    // Navigate to edit form
    navigate(`/llm-configs/${encodeURIComponent(llmId)}/edit`);
  };

  const handleTestLLM = (llmId: string) => {
    setCurrentlyTestingId(llmId);
    testLLM.mutate(llmId);
  };

  // Reset the currently testing ID when the test completes
  React.useEffect(() => {
    if (!testLLM.isPending) {
      setCurrentlyTestingId(null);
    }
  }, [testLLM.isPending]);

  const getEnhancedStatus = (llm: any, llmId: string) => {
    // Check if this LLM recently failed a test
    if (failedTests.has(llmId)) {
      return {
        icon: AlertTriangle,
        text: 'Not tested yet',
        className: 'text-red-600',
        buttonText: 'Run Test',
        circleColor: 'bg-red-500',
      };
    }

    // Check if LLM has been successfully tested
    if (llm.validated_at) {
      return {
        icon: CheckCircle,
        text: `Tested ${formatRelativeTime(llm.validated_at)}`,
        className: 'text-green-600',
        buttonText: 'Re-Run Test',
        circleColor: 'bg-green-500',
      };
    }

    // Default: Not tested yet
    return {
      icon: AlertTriangle,
      text: 'Not tested yet',
      className: 'text-yellow-600',
      buttonText: 'Run Test',
      circleColor: 'bg-yellow-500',
    };
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
          <p className="text-muted-foreground mt-1">Manage and configure your language model settings</p>
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
            if (!llm) {
              return null;
            } // Handle null entries
            
            // Safely extract LLM config ID
            const llmId = llm && typeof llm.id === 'string' 
              ? llm.id 
              : (llm?.id && typeof llm.id === 'object' && 'name' in llm.id)
                ? String((llm.id as any).name)
                : 'unknown_llm';
            const isThisButtonLoading = testLLM.isPending && currentlyTestingId === llmId;
            return (
              <motion.div
                key={llmId}
                initial={{ y: 20, opacity: 0 }}
                animate={{ y: 0, opacity: 1 }}
                transition={{ delay: index * 0.1 }}
                className="gradient-card rounded-lg p-4 space-y-3 hover:shadow-md transition-all duration-200 gradient-glow"
              >
                <div className="space-y-2">
                  {/* Header with Provider Icon and LLM Name */}
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <ProviderIcon
                        provider={llm.fullConfig?.provider || 'unknown'}
                        className="h-4 w-4"
                      />
                      <h3 className="font-semibold text-foreground">{llmId}</h3>
                    </div>
                    <div
                      className={`w-2 h-2 rounded-full ${getEnhancedStatus(llm, llmId).circleColor}`}
                    />
                  </div>

                  {/* Model Name */}
                  <p className="text-sm text-muted-foreground">
                    {formatModelName(llm.fullConfig?.model || '')}
                  </p>

                  {/* Status with Timestamp */}
                  <div className="flex items-center gap-1.5 text-xs">
                    {(() => {
                      const status = getEnhancedStatus(llm, llmId);
                      const StatusIcon = status.icon;
                      return (
                        <>
                          <StatusIcon className={`h-3.5 w-3.5 ${status.className}`} />
                          <span className={status.className}>{status.text}</span>
                        </>
                      );
                    })()}
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
                  <Button
                    size="sm"
                    className="gap-1.5"
                    onClick={() => handleTestLLM(llmId)}
                    disabled={false}
                  >
                    {isThisButtonLoading ? (
                      <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    ) : (
                      <TestTube className="h-3.5 w-3.5" />
                    )}
                    {isThisButtonLoading ? 'Testing...' : getEnhancedStatus(llm, llmId).buttonText}
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

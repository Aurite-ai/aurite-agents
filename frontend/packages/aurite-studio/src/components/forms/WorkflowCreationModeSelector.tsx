import React from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { ArrowLeft, FileText, Workflow } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface WorkflowCreationModeSelectorProps {
  // No props needed for now
}

export default function WorkflowCreationModeSelector(): React.ReactElement {
  const navigate = useNavigate();

  const handleTextMode = () => {
    navigate('/workflows/new/text');
  };

  const handleVisualMode = () => {
    navigate('/workflows/new/visual');
  };

  return (
    <div className="flex h-screen bg-background text-foreground">
      {/* Main Content */}
      <div className="flex-1 flex flex-col relative">
        {/* Main Content Area */}
        <main className="flex-1 flex flex-col px-6 pt-12 pb-8">
          <motion.div
            initial={{ y: 20, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ duration: 0.5 }}
            className="w-full max-w-4xl mx-auto space-y-8"
          >
            {/* Header */}
            <div className="flex items-center gap-4">
              <Button
                variant="ghost"
                size="icon"
                onClick={() => navigate('/workflows')}
                className="w-9 h-9"
              >
                <ArrowLeft className="h-4 w-4" />
              </Button>
              <h1 className="text-3xl font-bold text-primary">
                Create New Workflow
              </h1>
            </div>

            {/* Mode Selection Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Text-Based Mode */}
              <motion.div
                initial={{ y: 20, opacity: 0 }}
                animate={{ y: 0, opacity: 1 }}
                transition={{ delay: 0.1 }}
                className="bg-card border border-border rounded-lg p-8 space-y-6 hover:border-primary/50 transition-colors cursor-pointer group"
                onClick={handleTextMode}
              >
                <div className="flex items-center gap-4">
                  <div className="w-12 h-12 bg-primary/10 rounded-lg flex items-center justify-center group-hover:bg-primary/20 transition-colors">
                    <FileText className="h-6 w-6 text-primary" />
                  </div>
                  <div>
                    <h2 className="text-xl font-semibold text-primary">Text-Based Workflow</h2>
                    <p className="text-sm text-muted-foreground">Traditional list-based approach</p>
                  </div>
                </div>
                
                <div className="space-y-3">
                  <p className="text-sm text-foreground">
                    Create workflows by selecting agents from a dropdown and arranging them in a sequential list.
                  </p>
                  
                  <ul className="text-sm text-muted-foreground space-y-1">
                    <li>• Simple and familiar interface</li>
                    <li>• Quick sequential workflow creation</li>
                    <li>• Perfect for linear processes</li>
                  </ul>
                </div>

                <Button 
                  className="w-full"
                  onClick={(e) => {
                    e.stopPropagation();
                    handleTextMode();
                  }}
                >
                  Create Text-Based Workflow
                </Button>
              </motion.div>

              {/* Visual Mode */}
              <motion.div
                initial={{ y: 20, opacity: 0 }}
                animate={{ y: 0, opacity: 1 }}
                transition={{ delay: 0.2 }}
                className="bg-card border border-border rounded-lg p-8 space-y-6 hover:border-primary/50 transition-colors cursor-pointer group"
                onClick={handleVisualMode}
              >
                <div className="flex items-center gap-4">
                  <div className="w-12 h-12 bg-primary/10 rounded-lg flex items-center justify-center group-hover:bg-primary/20 transition-colors">
                    <Workflow className="h-6 w-6 text-primary" />
                  </div>
                  <div>
                    <h2 className="text-xl font-semibold text-primary">Visual Workflow Builder</h2>
                    <p className="text-sm text-muted-foreground">Drag-and-drop canvas interface</p>
                  </div>
                </div>
                
                <div className="space-y-3">
                  <p className="text-sm text-foreground">
                    Build workflows visually by dragging agents onto a canvas and connecting them with flow lines.
                  </p>
                  
                  <ul className="text-sm text-muted-foreground space-y-1">
                    <li>• Intuitive drag-and-drop interface</li>
                    <li>• Visual flow representation</li>
                    <li>• Perfect for complex workflows</li>
                  </ul>
                </div>

                <Button 
                  className="w-full"
                  onClick={(e) => {
                    e.stopPropagation();
                    handleVisualMode();
                  }}
                >
                  Create Visual Workflow
                </Button>
              </motion.div>
            </div>

            {/* Help Text */}
            <motion.div
              initial={{ y: 20, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              transition={{ delay: 0.3 }}
              className="bg-muted/20 border border-border rounded-lg p-4"
            >
              <p className="text-sm text-muted-foreground text-center">
                Both workflow types are fully compatible and can be executed in the same way. 
                Choose the creation method that best fits your workflow complexity and personal preference.
              </p>
            </motion.div>
          </motion.div>
        </main>
      </div>
    </div>
  );
}
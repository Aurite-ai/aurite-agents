import React from 'react';
import { Brain, Cpu, Chrome, Zap, HardDrive, Cloud } from 'lucide-react';

interface ProviderIconProps {
  provider: string;
  className?: string;
}

/**
 * Provider icon component that displays appropriate icons for different LLM providers
 */
export const ProviderIcon: React.FC<ProviderIconProps> = ({ provider, className = 'h-4 w-4' }) => {
  const getProviderIcon = (providerName: string) => {
    switch (providerName?.toLowerCase()) {
      case 'openai':
        return <Zap className={`${className} text-green-500`} />;
      case 'anthropic':
        return <Brain className={`${className} text-orange-500`} />;
      case 'google':
        return <Chrome className={`${className} text-blue-500`} />;
      case 'cohere':
        return <Cloud className={`${className} text-purple-500`} />;
      case 'huggingface':
        return <HardDrive className={`${className} text-yellow-500`} />;
      case 'ollama':
        return <Cpu className={`${className} text-gray-500`} />;
      case 'azure':
        return <Cloud className={`${className} text-blue-600`} />;
      default:
        return <Brain className={`${className} text-gray-400`} />;
    }
  };

  return getProviderIcon(provider);
};

export default ProviderIcon;

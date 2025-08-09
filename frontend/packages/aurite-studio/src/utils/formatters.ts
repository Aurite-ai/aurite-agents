/**
 * Utility functions for formatting data in the UI
 */

/**
 * Format model names to be more user-friendly
 */
export const formatModelName = (model: string): string => {
  if (!model) {
    return 'Unknown Model';
  }

  const modelMap: Record<string, string> = {
    // OpenAI models
    'gpt-4-turbo-preview': 'GPT-4 Turbo',
    'gpt-4-turbo': 'GPT-4 Turbo',
    'gpt-4': 'GPT-4',
    'gpt-3.5-turbo': 'GPT-3.5 Turbo',
    'gpt-3.5-turbo-16k': 'GPT-3.5 Turbo 16K',

    // Anthropic models
    'claude-3-opus-20240229': 'Claude 3 Opus',
    'claude-3-sonnet-20240229': 'Claude 3 Sonnet',
    'claude-3-haiku-20240307': 'Claude 3 Haiku',
    'claude-2.1': 'Claude 2.1',
    'claude-2': 'Claude 2',
    'claude-instant-1.2': 'Claude Instant',

    // Google models
    'gemini-pro': 'Gemini Pro',
    'gemini-pro-vision': 'Gemini Pro Vision',
    'palm-2': 'PaLM 2',

    // Other models
    'llama-2-70b': 'Llama 2 70B',
    'llama-2-13b': 'Llama 2 13B',
    'llama-2-7b': 'Llama 2 7B',
  };

  return modelMap[model] || model;
};

/**
 * Format timestamp to relative time (e.g., "2 mins ago")
 */
export const formatRelativeTime = (timestamp: string | null): string => {
  if (!timestamp) {
    return '';
  }

  try {
    const date = new Date(timestamp);
    const now = new Date();
    const diffInSeconds = Math.floor((now.getTime() - date.getTime()) / 1000);

    if (diffInSeconds < 60) {
      return 'Just now';
    } else if (diffInSeconds < 3600) {
      const minutes = Math.floor(diffInSeconds / 60);
      return `${minutes} min${minutes > 1 ? 's' : ''} ago`;
    } else if (diffInSeconds < 86400) {
      const hours = Math.floor(diffInSeconds / 3600);
      return `${hours} hour${hours > 1 ? 's' : ''} ago`;
    } else if (diffInSeconds < 2592000) {
      const days = Math.floor(diffInSeconds / 86400);
      return `${days} day${days > 1 ? 's' : ''} ago`;
    }
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: date.getFullYear() !== now.getFullYear() ? 'numeric' : undefined,
    });
  } catch {
    return 'Invalid date';
  }
};

/**
 * Get provider display name
 */
export const getProviderDisplayName = (provider: string): string => {
  const providerMap: Record<string, string> = {
    openai: 'OpenAI',
    anthropic: 'Anthropic',
    google: 'Google',
    cohere: 'Cohere',
    huggingface: 'Hugging Face',
    ollama: 'Ollama',
    azure: 'Azure OpenAI',
  };

  return providerMap[provider?.toLowerCase()] || provider || 'Unknown';
};

/**
 * Format LLM test error messages to be user-friendly and actionable
 */
export const formatLLMTestError = (llmConfigId: string, error: any): string => {
  // Extract error information
  let errorType = 'Unknown error';
  let actionableAdvice = 'Please try again';

  // First, check for structured API response (from LLM test endpoint)
  const structuredError = error?.response?.data?.error;
  if (structuredError?.message) {
    const errorMessage = structuredError.message.toLowerCase();
    const errorTypeFromAPI = structuredError.error_type;

    // Parse specific LiteLLM errors
    if (
      errorMessage.includes('llm provider not provided') ||
      errorMessage.includes('provider not provided')
    ) {
      errorType = 'Model format error';
      actionableAdvice = 'Use correct format like "anthropic/claude-3-haiku-20240307"';
    } else if (
      errorMessage.includes('authenticationerror') ||
      errorMessage.includes('invalid api key')
    ) {
      errorType = 'API key error';
      actionableAdvice = 'Check your API key configuration';
    } else if (errorMessage.includes('ratelimiterror') || errorMessage.includes('rate limit')) {
      errorType = 'Rate limit exceeded';
      actionableAdvice = 'Wait a moment and try again';
    } else if (errorMessage.includes('notfounderror') || errorMessage.includes('model not found')) {
      errorType = 'Model not available';
      actionableAdvice = 'Verify the model name exists for your provider';
    } else if (errorMessage.includes('badrequesterror')) {
      if (errorMessage.includes('model=')) {
        // Extract model name from error for better guidance
        const modelMatch = errorMessage.match(/model=([^\s\n]+)/);
        const modelName = modelMatch ? modelMatch[1] : 'your model';
        errorType = 'Model format error';
        actionableAdvice = `Fix model format: "${modelName}" should include provider prefix`;
      } else {
        errorType = 'Configuration error';
        actionableAdvice = 'Review your model and provider settings';
      }
    } else if (errorMessage.includes('timeout')) {
      errorType = 'Request timeout';
      actionableAdvice = 'Check your connection and try again';
    } else if (errorMessage.includes('connection')) {
      errorType = 'Connection error';
      actionableAdvice = 'Check your internet connection';
    } else if (errorTypeFromAPI) {
      // Use the error type from API if available
      errorType = errorTypeFromAPI.replace('Error', ' error');
      actionableAdvice = 'Check your configuration settings';
    } else if (structuredError.message.length < 100) {
      errorType = 'Configuration error';
      actionableAdvice = structuredError.message.split('\n')[0]; // First line only
    } else {
      errorType = 'Configuration error';
      actionableAdvice = 'Check your LLM configuration settings';
    }
  } else {
    // Fallback to HTTP status codes and generic error messages
    const status = error?.response?.status || error?.status;
    const message = error?.response?.data?.detail || error?.message || '';

    if (status === 401 || message.toLowerCase().includes('auth')) {
      errorType = 'Authentication error';
      actionableAdvice = 'Check your API key configuration';
    } else if (status === 404) {
      errorType = 'Configuration not found';
      actionableAdvice = 'Verify the LLM configuration exists';
    } else if (status === 500) {
      errorType = 'Server error';
      actionableAdvice = 'Check your configuration and try again';
    } else if (status === 429) {
      errorType = 'Rate limit exceeded';
      actionableAdvice = 'Wait a moment and try again';
    } else if (status === 400) {
      errorType = 'Configuration error';
      actionableAdvice = 'Review your LLM settings';
    } else if (message.toLowerCase().includes('timeout')) {
      errorType = 'Network timeout';
      actionableAdvice = 'Check your connection and retry';
    } else if (message.toLowerCase().includes('network')) {
      errorType = 'Network error';
      actionableAdvice = 'Check your internet connection';
    } else if (message.toLowerCase().includes('api key')) {
      errorType = 'API key error';
      actionableAdvice = 'Verify your API key is correct';
    } else if (status >= 500) {
      errorType = 'Server error';
      actionableAdvice = 'Try again in a moment';
    } else if (status >= 400) {
      errorType = 'Request error';
      actionableAdvice = 'Check your configuration settings';
    }
  }

  // Format the final message with config name in quotes
  return `"${llmConfigId}" test failed: ${errorType} - ${actionableAdvice}`;
};

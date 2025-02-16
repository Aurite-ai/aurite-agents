import { tool } from 'ai';
import { z } from 'zod';
import axios from 'axios';

interface TavilySearchToolOptions {
  onFindResults?: (
    references: {
      title: string;
      url: string;
      content: string;
      score: number;
    }[]
  ) => void;
}

export const createTavilySearchTool = (options?: TavilySearchToolOptions) =>
  tool({
    description: 'Search for data using the Tavily Web Search API.',
    parameters: z.object({
      query: z.string().describe('The search query to execute on Tavily.'),
    }),
    execute: async ({
      query,
    }: // include_domains,
    {
      query: string;
      // include_domains: string[];
    }) => {
      try {
        const { data } = await axios.post('https://api.tavily.com/search', {
          api_key: process.env.TAVILY_API_KEY,
          query,
          search_depth: 'basic',
          topic: 'general',
          max_results: 10,
          include_images: false,
          include_answer: true,
          use_cache: false,
        });

        console.log(`Search results: ${JSON.stringify(data)}`);

        options?.onFindResults?.(data.results);

        return JSON.stringify(data);
      } catch (error) {
        console.error('Error in TavilySearchTool:', error);
        return `Error: ${error}`;
      }
    },
  });

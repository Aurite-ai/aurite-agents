import { tool } from "ai";
import { z } from "zod";
import axios from "axios";

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
    description: "Search for data using the Tavily Web Search API.",
    parameters: z.object({
      query: z.string().describe("The search query to execute on Tavily."),
      // include_domains: z
      //   .array(z.string())
      //   .optional()
      //   .describe("The domains to include in the search."),
    }),
    execute: async ({
      query,
    }: // include_domains,
    {
      query: string;
      // include_domains: string[];
    }) => {
      try {
        const { data } = await axios.post("https://api.tavily.com/search", {
          api_key: process.env.TAVILY_API_KEY,
          query,
          search_depth: "basic",
          topic: "general",
          max_results: 5,
          include_images: true,
          include_answer: true,
          // include_domains,
          use_cache: false,
        });

        console.log(`Search results: ${JSON.stringify(data)}`);

        options?.onFindResults?.(data.results);

        return JSON.stringify(data);
      } catch (error) {
        console.error("Error in TavilySearchTool:", error);
        return `Error: ${error}`;
      }
    },
  });

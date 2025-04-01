import logging
from mcp.server.fastmcp import FastMCP
from openai import OpenAI
from typing import Dict, Any, List, Optional
import json
import os
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

LIMIT = 64

RED = '\033[91m'
GREEN = '\033[92m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'  # Reset to default color

current_dir = Path(__file__).parent.resolve()

logging.basicConfig(
    level=logging.DEBUG, format="%(levelname)s - %(name)s - %(message)s"
)
logger = logging.getLogger(__name__)

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY", default="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"),
)


mcp = FastMCP("march-madness-server")


@mcp.tool("get_first_round")
def get_matchups():
    logger.info(f"{YELLOW}Getting round of 4 matchups{RESET}")
    try:
        # Fetch from the inputs directory
        with open(os.path.join(current_dir, 'inputs/ro_8.json'), 'r') as file:
            data = json.load(file)
            # Log successful data loading
            logger.debug(f"{GREEN}Successfully loaded data from {os.path.join(current_dir, 'inputs/ro_8.json')}{RESET}")
            logger.debug(f"{GREEN}Found {len(data)} matchups{RESET}")
            if not data:
                logger.debug(f"{RED}No data found{RESET}")
                return [{"type": "text", "text": "No data found. Do not proceed."}]
            # trimmed = data[:LIMIT]
            return [{"type": "text", "text": json.dumps(data)}]
    except Exception as e:
        logger.debug(f"{RED}Error: {e}{RESET}")
        return [{"type": "text", "text": f"Error: {e}"}]

@mcp.tool()
def compare_matchup(
    team1: str = "Gonzaga",
    team2: str = "Norfolk State/Appalachian State",
) -> Dict[str, Any]:
    logger.info(f"{YELLOW}Comparing matchup between {team1} and {team2}{RESET}")

    try:

        completion = client.chat.completions.create(
        model="gpt-4o-search-preview",
        web_search_options={},
        messages=[
            {
                "role": "user",
                "content": f"Compare the hypothetical Match Madess matchup between {team1} and {team2}. Analyze strengths and weaknesses of each team and predict the winner. Use statistics and historical data to enhance your prediction. remember that upsets are common in March Madness.",
            }
        ],
        max_completion_tokens=400
        )

        result = completion.choices[0].message.content
        logger.debug(f"{BLUE}{result}{RESET}")

        simple_result = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": f"Take the following information and output the winner of the matchup {result}.",
            }
        ],
        max_completion_tokens=100
        )

        return [{"type": "text", "text": simple_result.choices[0].message.content}]
    except Exception as e:
        logger.debug(f"{RED}Error: {e}{RESET}")
        return [{"type": "text", "text": f"Error: {e}"}]

@mcp.tool()
def store_round_results(
    round_results: List[Dict[str, Any]],
    round_number: int,
) -> Dict[str, Any]:
    logger.info(f"{YELLOW}Storing results for round {round_number}{RESET}")

    try:
        # Save to current directory
        # Create outputs directory in current script directory
        outputs_dir = os.path.join(current_dir, "outputs")
        os.makedirs(outputs_dir, exist_ok=True)
        
        # Save to current script directory
        with open(os.path.join(current_dir, f"agent_round_{round_number}.json"), "w") as file:
            json.dump(round_results, file)
        
        # Also save to /outputs directory
        with open(os.path.join(outputs_dir, f"agent_round_{round_number}.json"), "w") as file:
            json.dump(round_results, file)
            
        return {"success": True}
    except Exception as e:
        logger.debug(f"{RED}Error: {e}{RESET}")
        return {"success": False, "error": str(e)}
    

@mcp.prompt()
def march_madness_prompt() -> str:
    return f'''
    Using the march madess tools at your disposal, return a complete prediction for a march madness bracket. Start with the first round and go all the way to the championship game.

    Your process should be as follows:
    1. Get the first round matchups
    2. Compare each matchup and predict the winner
    2.1 Remember that upsets are common in March Madness
    3. Compare to the winners of the next round and predict the winner
    4. Continue until you have a complete bracket
    5. Return the bracket as a JSON object with the team names and predicted winners

    Always execute the compare tool in parallel -> ie compare 4 matchups at a time.
    
    !Important: You MUST search every matchup you encounter, along every round, about 64 + 32 + 16 + 8 + 4 + 2 + 1 in total. Do this all in one response.

    !Important: This is a single shot response, you must return the entire bracket in one response. There will be no follow up questions.

    !Important: If you are unable to fetch the first round matchups, return an error message and do not proceed.
    
    Example:
    Returns
    First Round (64):
    1. Auburn (1) defeats Alabama State (16)
    2. Creighton (9) defeats Louisville (8)
    ...

    Second Round (32):
1   . Auburn (1) defeats Creighton (9)
    ...

    Sweet 16 (16):
    ...
    
    '''


if __name__ == "__main__":
    mcp.run(transport="stdio")



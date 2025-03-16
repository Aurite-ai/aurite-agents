"""
Example demonstrating the integration of workflows with the MCP Host.

This example shows:
1. Creating an MCPHost instance
2. Registering a DataAnalysisWorkflow with the host
3. Running the workflow on a sample dataset
4. Processing and displaying the results
"""

import asyncio
import os
import logging
from pathlib import Path

from src.host.host import MCPHost, HostConfig, ClientConfig
from src.host.foundation import RootConfig
from src.agents.examples.data_analysis_workflow import DataAnalysisWorkflow


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

# Sample weather data server for tools
WEATHER_SERVER_PATH = Path(__file__).parent / "weather_server.py"


async def main():
    """Run the example workflow"""
    # Create host configuration with the weather tools server
    config = HostConfig(
        clients=[
            ClientConfig(
                client_id="weather_tools",
                server_path=WEATHER_SERVER_PATH,
                roots=[
                    RootConfig(
                        uri="aurite:/tools/weather/*",
                        description="Weather tools",
                    )
                ],
                capabilities=["tools", "resources"],
            )
        ]
    )
    
    # Create and initialize host
    host = MCPHost(config)
    await host.initialize()
    
    try:
        # Display available tools
        print("Available tools:")
        for tool in host.tools.list_tools():
            print(f"  - {tool['name']}: {tool['description']}")
        
        # Register the DataAnalysisWorkflow with the host
        workflow_name = await host.register_workflow(DataAnalysisWorkflow)
        print(f"\nRegistered workflow: {workflow_name}")
        
        # Create sample input data
        input_data = {
            "dataset_id": "weather_data_2025",
            "analysis_type": "comprehensive",
            "include_visualization": True,
            "max_rows": 1000,
        }
        
        # Execute the workflow
        print(f"\nExecuting workflow with data: {input_data}")
        result = await host.execute_workflow(workflow_name, input_data)
        
        # Process the results
        summary = result.summarize_results()
        print("\nWorkflow execution summary:")
        print(f"  Success: {summary['success']}")
        print(f"  Execution time: {summary['execution_time']:.2f} seconds")
        print(f"  Steps completed: {summary['steps_completed']}")
        
        # Display output data
        data = summary["data"]
        print("\nWorkflow results:")
        print(f"  Dataset: {data.get('dataset_info', {}).get('id')}")
        print(f"  Quality score: {data.get('data_quality_report', {}).get('overall_quality_score')}")
        
        # Show the first few lines of the final report
        if "final_report" in data:
            report_lines = data["final_report"].split("\n")
            print("\nFinal report preview:")
            for line in report_lines[:5]:
                print(f"  {line}")
            print("  ...")
            
    finally:
        # Shutdown the host
        await host.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
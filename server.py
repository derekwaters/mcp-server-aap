#!/usr/bin/env python3
"""
MCP Server for Ansible Automation Platform
Provides functions to extract templates and launch jobs
"""

import asyncio
import json
import logging
import re
import random
from typing import Any, Dict, List, Optional
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    Tool,
    TextContent,
    CallToolResult,
    CallToolRequestParams,
)
from aap_client import AAPClient, JobTemplate, JobLaunch

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize MCP server
server = Server("ansible-aap-server")

# NOTE: This function is needed because Qwen seems to think that
# having a parameter marked as integer means it should send it as
# 12.0 not 12. Sigh.
#
def safe_get_int_arg(arguments: object, arg_name: str) -> int | None:
    val = arguments.get(arg_name)
    if val is not None and isinstance(val, float):
        val = int(val)
    return val

@server.list_tools()
async def list_tools() -> List[Tool]:
    """List available tools"""
    return [
        Tool(
            name="get_job_templates",
            description="Get available job templates from the configured AAP project with detailed descriptions and metadata",
            inputSchema={
                "type": "object",
                "properties": {
                    # NOTE: Some MCP clients (eg llama-stack MCP) send session_id, ignore it
                    "session_id": {
                        "type": "string",
                        "description": "OPTIONAL"
                    }
                },
                "additionalProperties": False
            }
        ),
        Tool(
            name="get_host_inventories",
            description="Get available host inventories from AAP including details of the list of hostnames",
            inputSchema={
                "type": "object",
                "properties": {
                    # NOTE: Some MCP clients send session_id, ignore it
                    "session_id": {
                        "type": "string",
                        "description": "OPTIONAL"
                    }
                },
                "additionalProperties": False
            }
        ),
        Tool(
            name="launch_job_template",
            description="Launch an Ansible job template with optional parameters",
            inputSchema={
                "type": "object",
                "properties": {
                    # NOTE: Some MCP clients send session_id, ignore it
                    "session_id": {
                        "type": "string",
                        "description": "OPTIONAL"
                    },
                    "template_id": {
                        "type": "integer",
                        "description": "ID of the job template to launch"
                    },
                    "extra_vars": {
                        "type": "string",
                        # NOTE: llama-stack and qwen really could not get around the idea of
                        # embedding a subobject here, hence the need to make this a JSON-encoded
                        # string of extra_vars
                        "description": "A JSON-encoded string containing any Extra variables to pass to the job template"
                    },
                    "inventory_id": {
                        "type": "integer",
                        "description": "Optional inventory ID to use"
                    }
                },
                "required": ["template_id"],
                "additionalProperties": False
            }
        ),
        Tool(
            name="get_job_status",
            description="Get the status and details of a running or completed job",
            inputSchema={
                "type": "object",
                "properties": {
                    # NOTE: Some MCP clients send session_id, ignore it
                    "session_id": {
                        "type": "string",
                        "description": "OPTIONAL"
                    },
                    "job_id": {
                        "type": "integer",
                        "description": "ID of the job to check"
                    }
                },
                "required": ["job_id"],
                "additionalProperties": False
            }
        ),
        Tool(
            name="get_job_output",
            description="Get the output/logs of a job",
            inputSchema={
                "type": "object",
                "properties": {
                    # NOTE: Some MCP clients send session_id, ignore it
                    "session_id": {
                        "type": "string",
                        "description": "OPTIONAL"
                    },
                    "job_id": {
                        "type": "integer",
                        "description": "ID of the job to get output from"
                    }
                },
                "required": ["job_id"],
                "additionalProperties": False
            }
        ),
        Tool(
            name="test_aap_connection",
            description="Test the connection to Ansible Automation Platform",
            inputSchema={
                "type": "object",
                "properties": {},
                "additionalProperties": False
            }
        ),
        Tool(
            name="create_incident",
            description="Generate an incident record and return an incident number",
            inputSchema={
                "type": "object",
                "properties": {
                    # NOTE: Some MCP clients send session_id, ignore it
                    "session_id": {
                        "type": "string",
                        "description": "OPTIONAL"
                    },
                    "affected_host": {
                        "type": "string",
                        "description": "The hostname affected by the incident"
                    },
                    "error_description": {
                        "type": "string",
                        "description": "Any additional error details"
                    }
                },
                "required": ["affected_host"],
                "additionalProperties": False
            }
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]):
    """Handle tool calls"""
    try:
        async with AAPClient() as client:
            if name == "get_job_templates":
                project_id = arguments.get("project_id")
                templates = await client.get_job_templates(project_id)

                # Format templates for display with enhanced descriptions
                if not templates:
                    return [
                        TextContent(
                            type="text",
                            text="No job templates found in the specified project."
                        )
                    ]

                # Create detailed template information
                template_details = []
                template_list = []

                for i, template in enumerate(templates, 1):
                    # Detailed description for readable format
                    template_detail = f"**{i}. {template.name}** (ID: {template.id})\n"
                    template_detail += f"   📋 Description: {template.description or 'No description provided'}\n"
                    template_detail += f"   📘 Playbook: {template.playbook}\n"
                    template_detail += f"   📁 Project: {template.project}\n"

                    if template.inventory:
                        template_detail += f"   🗂️  Inventory: {template.inventory}\n"
                    if template.credential:
                        template_detail += f"   🔑 Credential: {template.credential}\n"

                    template_detail += f"   📝 Survey Enabled: {'Yes' if template.survey_enabled else 'No'}\n"
                    template_details.append(template_detail)

                    # Also maintain JSON structure for programmatic use
                    template_info = {
                        "id": template.id,
                        "name": template.name,
                        "description": template.description,
                        "playbook": template.playbook,
                        "project": template.project,
                        "survey_enabled": template.survey_enabled
                    }
                    if template.inventory:
                        template_info["inventory"] = template.inventory
                    if template.credential:
                        template_info["credential"] = template.credential
                    template_list.append(template_info)

                # Create comprehensive response
                response_text = f"Found {len(templates)} job template{'s' if len(templates) != 1 else ''}:\n\n"
                response_text += "\n".join(template_details)
                response_text += "\n\n---\n\nJSON Data:\n```json\n"
                response_text += json.dumps(template_list, indent=2)
                response_text += "\n```"

                return [
                    TextContent(
                        type="text",
                        text=response_text
                    )
                ]

            elif name == "get_host_inventories":

                organization_id = arguments.get("organization_id")
                inventories = await client.get_inventories(organization_id)

                # Format inventories for display with enhanced descriptions
                if not inventories:
                    return [
                        TextContent(
                            type="text",
                            text="No inventories found in the specific organization."
                        )
                    ]

                # Create detailed inventory information
                inventory_details = []
                inventory_list = []

                for i, inventory in enumerate(inventories, 1):
                    # Detailed description for readable format
                    inventory_detail = f"**{i}. {inventory.name}** (ID: {inventory.id})\n"
                    inventory_detail += f"   📋 Description: {inventory.description or 'No description provided'}\n"

                    # Also maintain JSON structure for programmatic use
                    inventory_info = {
                        "id": inventory.id,
                        "name": inventory.name,
                        "description": inventory.description,
                        "hosts": []
                    }

                    for j, host in enumerate(inventory.hosts, 1):
                        inventory_detail += f"   - Host {j}: {host.name}\n"
                        inventory_detail += f"              Description : {host.description}\n"
                        inventory_detail += f"              Enabled     : {'Yes' if host.enabled else 'No'}\n"

                        host_detail = {
                            "name": host.name,
                            "description": host.description,
                            "enabled": host.enabled
                        }
                        inventory_info["hosts"].append(host_detail)

                    inventory_details.append(inventory_detail)
                    inventory_list.append(inventory_info)

                # Create comprehensive response
                response_text = f"Found {len(inventories)} inventor{'ies' if len(inventories) != 1 else 'y'}:\n\n"
                response_text += "\n".join(inventory_details)
                response_text += "\n\n---\n\nJSON Data:\n```json\n"
                response_text += json.dumps(inventory_list, indent=2)
                response_text += "\n```"

                return [
                    TextContent(
                        type="text",
                        text=response_text
                    )
                ]

            elif name == "launch_job_template":
                template_id = safe_get_int_arg(arguments, "template_id")
                extra_vars = arguments.get("extra_vars")
                inventory = safe_get_int_arg(arguments, "inventory_id")
                
                if extra_vars and isinstance(extra_vars, str):
                    extra_vars = json.loads(extra_vars)
                else:
                    extra_vars = None

                launch_result = await client.launch_job_template(
                    template_id=template_id,
                    extra_vars=extra_vars,
                    inventory=inventory,
                )

                return [
                    TextContent(
                        type="text",
                        text=f"Job launched successfully!\n\n" +
                             f"Job ID: {launch_result.job}\n" +
                             f"Launch ID: {launch_result.id}\n" +
                             f"URL: {launch_result.url}\n" +
                             f"Type: {launch_result.type}\n\n" +
                             "Use get_job_status to check the job progress."
                    )
                ]

            elif name == "get_job_status":
                job_id = safe_get_int_arg(arguments, "job_id")
                job_status = await client.get_job_status(job_id)

                # Extract key status information
                status_info = {
                    "id": job_status.get("id"),
                    "name": job_status.get("name"),
                    "status": job_status.get("status"),
                    "failed": job_status.get("failed"),
                    "started": job_status.get("started"),
                    "finished": job_status.get("finished"),
                    "elapsed": job_status.get("elapsed"),
                    "job_template": job_status.get("job_template"),
                    "playbook": job_status.get("playbook")
                }

                check_explanation = job_status.get("job_explanation")
                if check_explanation:
                    print(f"GOT A POSSIBLE JOB VIOLATION: {check_explanation}")
                    find_violation = re.search("^This job cannot be executed due to a policy violation.*Violations': {'([A-Za-z]+)': ['(.+)'", check_explanation)
                    if find_violation:
                        status_info["explanation"] = f"Policy was violated on {find_violation.group(1)} : {find_violation.group(2)}. Please correct the issue and launch the job again" 

                return [
                    TextContent(
                        type="text",
                        text=f"Job Status:\n\n" +
                             json.dumps(status_info, indent=2)
                    )
                ]

            elif name == "get_job_output":
                job_id = safe_get_int_arg(arguments, "job_id")
                job_output = await client.get_job_stdout(job_id)

                return [
                    TextContent(
                        type="text",
                        text=f"Job Output (Job ID: {job_id}):\n\n" +
                             "```\n" + job_output + "\n```"
                    )
                ]

            elif name == "test_aap_connection":
                connection_ok = await client.test_connection()

                # Create simple result
                result_text = f"AAP Connection Test: {'✅ SUCCESS' if connection_ok else '❌ FAILED'}\n\n" + \
                             f"URL: {client.config.url}\n" + \
                             f"Project ID: {client.config.project_id}\n" + \
                             f"SSL Verification: {client.config.verify_ssl}"

                return [TextContent(type="text", text=result_text)]

            elif name == "create_incident":
                # NOTE: This is a dummy function for demo purposes only
                # TODO: Investigate MCP servers for ServiceNow to do this

                result_text = f"Created new Incident with Incident Number: INC-{random.randint(1000, 9999)}"
                return [TextContent(type="text", text=result_text)]

            else:
                return [
                    TextContent(
                        type="text",
                        text=f"Unknown tool: {name}"
                    )
                ]

    except Exception as e:
        logger.error(f"Error in tool call {name}: {str(e)}")
        return [
            TextContent(
                type="text",
                text=f"Error: {str(e)}"
            )
        ]


async def main():
    """Main server function"""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())
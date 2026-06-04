"""
Cloud Governance AI Agent - Streamlit Application
Provides natural language interface to query OpenSearch data via MCP server
"""

import asyncio
import os
import sys
import threading
from contextlib import AsyncExitStack
from typing import List

import streamlit as st
from google import genai
from google.genai import types
from dotenv import load_dotenv
from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp.client.session import ClientSession

CONVERSATION_DIR = os.path.join(os.path.dirname(__file__), 'conversations')
CONVERSATION_FILE = os.path.join(CONVERSATION_DIR, 'chat_history.json')


def _reload_config():
    """Re-read .env so changes are picked up without restarting Streamlit."""
    load_dotenv(override=True)
    return {
        "MODEL_NAME": os.getenv('MODEL_NAME', 'gemini-2.0-flash-exp'),
        "GEMINI_API_KEY": os.getenv('GEMINI_API_KEY'),
        "ES_INDEX": os.getenv('ES_INDEX', 'cloud-governance-policy-es-index'),
        "OPENSEARCH_HOSTS": os.getenv('OPENSEARCH_HOSTS', 'http://localhost:9200'),
    }


_cfg = _reload_config()
MODEL_NAME = _cfg["MODEL_NAME"]
GEMINI_API_KEY = _cfg["GEMINI_API_KEY"]
ES_INDEX = _cfg["ES_INDEX"]
OPENSEARCH_HOSTS = _cfg["OPENSEARCH_HOSTS"]


@st.cache_data(ttl=300)
def _fetch_available_indices() -> list[str]:
    """Fetch index names from OpenSearch for the sidebar dropdown."""
    try:
        from opensearchpy import OpenSearch
        client = OpenSearch(
            hosts=[OPENSEARCH_HOSTS],
            use_ssl=OPENSEARCH_HOSTS.startswith("https"),
            verify_certs=False,
            ssl_show_warn=False,
            timeout=10,
        )
        indices = client.cat.indices(format="json")
        names = sorted(
            idx.get("index", "") for idx in indices
            if idx.get("index", "").startswith("cloud-governance")
        )
        return names
    except Exception:
        return []


def _build_mcp_server_params() -> StdioServerParameters:
    env = {
        "OPENSEARCH_HOSTS": OPENSEARCH_HOSTS,
        "PATH": os.environ.get("PATH", ""),
        "HOME": os.environ.get("HOME", ""),
    }
    username = os.getenv("OPENSEARCH_USERNAME", "")
    password = os.getenv("OPENSEARCH_PASSWORD", "")
    if username:
        env["OPENSEARCH_USERNAME"] = username
    if password:
        env["OPENSEARCH_PASSWORD"] = password

    return StdioServerParameters(
        command=sys.executable,
        args=[os.path.join(os.path.dirname(__file__), "mcp_server.py")],
        env=env,
    )

# System instruction for AI agent (will be formatted with ES_INDEX)
SYSTEM_INSTRUCTION_TEMPLATE = """
You query OpenSearch index "{es_index}". You MUST call tools for every question.

WORKFLOW:
1. If unsure about available fields, call get_fields(index="{es_index}")
2. Use search_documents for filtered lookups
3. Use count_by_field for grouping and counting
4. Use aggregate for sums, averages, max, min on numeric fields
5. Use date_range_search for time-based queries
6. Use raw_search only for complex queries that don't fit the above tools
7. Present results in clear markdown tables

TIPS:
- You do NOT need to add .keyword suffix - tools handle this automatically
- Use filters as a list: [{{"field": "<field_name>", "value": "<value>"}}]
- Filters work on ANY field type including numeric fields
- Use date_range_search ONLY for actual date/timestamp fields, NOT for integer fields
- To filter aggregations by a field value, pass the filters parameter to aggregate or count_by_field
- Always call get_fields first to discover field names and types before querying
- Always pass index="{es_index}" to every tool call
"""

def _get_system_instruction():
    return SYSTEM_INSTRUCTION_TEMPLATE.format(es_index=ES_INDEX)


# Conversation persistence functions
def load_conversation_history() -> list:
    """Load chat history from file"""
    import json

    # Create directory if it doesn't exist
    os.makedirs(CONVERSATION_DIR, exist_ok=True)

    if os.path.exists(CONVERSATION_FILE):
        try:
            with open(CONVERSATION_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            st.warning(f"Could not load chat history: {e}")
            return []
    return []


def save_conversation_history(messages: list):
    """Save chat history to file"""
    import json

    try:
        # Create directory if it doesn't exist
        os.makedirs(CONVERSATION_DIR, exist_ok=True)

        with open(CONVERSATION_FILE, 'w') as f:
            json.dump(messages, f, indent=2)
    except Exception as e:
        st.warning(f"Could not save chat history: {e}")


def clear_conversation_history():
    """Delete saved chat history"""
    if os.path.exists(CONVERSATION_FILE):
        try:
            os.remove(CONVERSATION_FILE)
        except Exception as e:
            st.warning(f"Could not delete chat history: {e}")


def fix_gemini_schema(schema) -> dict:
    """Normalize MCP schemas for Gemini compatibility

    MCP schemas may use array notation for types: {"type": ["string", "null"]}
    Gemini expects single type: {"type": "string"}
    """
    if not isinstance(schema, dict):
        return {"type": str(schema)}

    cleaned = {}

    # Handle type as list or string
    raw_type = schema.get("type")
    if isinstance(raw_type, list):
        # Take first non-null type
        cleaned["type"] = next((t for t in raw_type if t != "null"), raw_type[0])
    else:
        cleaned["type"] = raw_type or "object"

    # Preserve description
    if "description" in schema:
        cleaned["description"] = schema["description"]

    # Handle array items recursively
    if cleaned["type"] == "array":
        if "items" in schema:
            cleaned["items"] = fix_gemini_schema(schema["items"])
        else:
            cleaned["items"] = {"type": "string"}

    # Recursively clean nested properties
    if "properties" in schema and isinstance(schema["properties"], dict):
        cleaned["properties"] = {
            k: fix_gemini_schema(v)
            for k, v in schema["properties"].items()
        }

    # Preserve required fields
    if "required" in schema:
        cleaned["required"] = schema["required"]

    return cleaned


async def fetch_mcp_tools_async() -> List[types.FunctionDeclaration]:
    """Dynamically fetch available tools from MCP server (stdio subprocess)"""
    st.info("Connecting to MCP server (stdio)...")

    server_params = _build_mcp_server_params()

    async with AsyncExitStack() as stack:
        read, write = await stack.enter_async_context(
            stdio_client(server_params)
        )
        st.info("stdio connection established")

        session = await stack.enter_async_context(
            ClientSession(read, write)
        )
        st.info("Session created")

        await session.initialize()
        st.info("Session initialized")

        mcp_data = await session.list_tools()
        st.info(f"Found {len(mcp_data.tools)} tools")

        tools = [
            types.FunctionDeclaration(
                name=tool.name,
                description=tool.description or "No description",
                parameters=fix_gemini_schema(tool.inputSchema)
            )
            for tool in mcp_data.tools
        ]

        st.success(f"Successfully loaded {len(tools)} tools!")
        return tools


def fetch_mcp_tools() -> List[types.FunctionDeclaration]:
    """Synchronous wrapper that runs async tool fetching in a separate thread"""
    result = []
    error = None

    def run_in_thread():
        nonlocal result, error
        try:
            # Create a new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(fetch_mcp_tools_async())
            finally:
                loop.close()
        except Exception as e:
            error = e

    thread = threading.Thread(target=run_in_thread)
    thread.start()
    thread.join()

    if error:
        st.error(f"❌ Failed to connect to MCP server")
        st.error(f"Error type: {type(error).__name__}")
        st.error(f"Error message: {str(error)}")
        st.info(f"OpenSearch: {OPENSEARCH_HOSTS}")
        st.info("Check that opensearch-py is installed and OPENSEARCH_HOSTS is correct in .env")

        import traceback
        st.code(traceback.format_exception(type(error), error, error.__traceback__))

        return []

    return result


async def execute_mcp_tool_async(name: str, arguments: dict) -> str:
    """Execute a tool via MCP server (stdio subprocess)"""
    try:
        server_params = _build_mcp_server_params()

        async with AsyncExitStack() as stack:
            read, write = await stack.enter_async_context(
                stdio_client(server_params)
            )
            session = await stack.enter_async_context(
                ClientSession(read, write)
            )
            await session.initialize()

            result = await session.call_tool(name, arguments)

            return "\n".join([
                content.text for content in result.content
                if hasattr(content, 'text')
            ])
    except Exception as e:
        import json
        error_msg = f"ERROR calling {name}:\n"
        error_msg += f"Type: {type(e).__name__}\n"
        error_msg += f"Message: {str(e)}\n"
        error_msg += f"Arguments: {json.dumps(arguments, indent=2)}\n"

        if hasattr(e, '__cause__') and e.__cause__:
            error_msg += f"Cause: {str(e.__cause__)}\n"

        return error_msg


def execute_mcp_tool(name: str, arguments: dict) -> str:
    """Synchronous wrapper for executing MCP tool"""
    import json

    result = None
    error = None

    # Debug logging - show what tool is being called
    debug_mode = st.session_state.get("debug_mode", True)
    if debug_mode:
        with st.expander(f"🔧 Tool Call: {name}", expanded=False):
            st.code(json.dumps(arguments, indent=2), language="json")

    def run_in_thread():
        nonlocal result, error
        try:
            # Create a new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(execute_mcp_tool_async(name, arguments))
            finally:
                loop.close()
        except Exception as e:
            error = e

    thread = threading.Thread(target=run_in_thread)
    thread.start()
    thread.join()

    if error:
        error_msg = f"Error executing {name}: {str(error)}"
        st.error(error_msg)
        return error_msg

    # Debug logging - show tool response
    if debug_mode:
        with st.expander(f"✅ Tool Response: {name}", expanded=False):
            try:
                # Try to pretty-print JSON
                parsed = json.loads(result)
                st.code(json.dumps(parsed, indent=2), language="json")
            except (json.JSONDecodeError, TypeError):
                # If not JSON, show as text (truncate if too long)
                if len(result) > 2000:
                    st.text(result[:2000] + f"\n\n... (truncated, total {len(result)} chars)")
                else:
                    st.text(result)

    return result


def run_agent_loop_gemini(user_message: str, tools: List[types.FunctionDeclaration], previous_messages: list | None = None) -> str:
    """Run agentic loop with Gemini"""

    if not GEMINI_API_KEY:
        return "❌ GEMINI_API_KEY not set. Please configure .env file."

    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
    except Exception as e:
        return f"❌ Failed to initialize Gemini client: {e}"

    # Create tool wrapper
    gemini_tool = types.Tool(function_declarations=tools) if tools else None

    # Debug: Verify tools are available
    if hasattr(st, 'session_state') and st.session_state.get("debug_mode", False):
        if tools:
            st.info(f"🔍 Debug: {len(tools)} tools available to AI: {[t.name for t in tools]}")
        else:
            st.error("❌ Debug: NO TOOLS AVAILABLE - this will cause issues!")

    # Few-shot example: discover fields then search
    history = []

    history.append(types.Content(
        role="user",
        parts=[types.Part(text="Show me the data in this index")]
    ))
    history.append(types.Content(
        role="model",
        parts=[
            types.Part(function_call=types.FunctionCall(
                name="get_fields",
                args={"index": ES_INDEX}
            ))
        ]
    ))
    history.append(types.Content(
        role="user",
        parts=[
            types.Part(function_response=types.FunctionResponse(
                name="get_fields",
                response={"result": "| Field | Type | Aggregatable |\n| --- | --- | --- |\n| name | text | |\n| category | keyword | Yes (keyword) |\n| status | text | |\n| count | long | Yes (numeric) |\n| timestamp | date | |\n\nNumeric fields for aggregation (sum/avg/max/min): count"}
            ))
        ]
    ))
    history.append(types.Content(
        role="model",
        parts=[
            types.Part(function_call=types.FunctionCall(
                name="search_documents",
                args={"index": ES_INDEX, "size": 5}
            ))
        ]
    ))
    history.append(types.Content(
        role="user",
        parts=[
            types.Part(function_response=types.FunctionResponse(
                name="search_documents",
                response={"result": "Total matching documents: 100\nShowing 5 results:\n\n| name | category | status | count |\n| --- | --- | --- | --- |\n| item-1 | typeA | active | 10 |"}
            ))
        ]
    ))
    history.append(types.Content(
        role="model",
        parts=[types.Part(text=f"Here are 5 sample documents from `{ES_INDEX}`. The index contains fields like name, category, status, count, and timestamp.")]
    ))

    # Second few-shot: count by field with filter
    history.append(types.Content(
        role="user",
        parts=[types.Part(text="Count active items by category")]
    ))
    history.append(types.Content(
        role="model",
        parts=[
            types.Part(function_call=types.FunctionCall(
                name="count_by_field",
                args={
                    "index": ES_INDEX,
                    "group_by": "category",
                    "filters": [{"field": "status", "value": "active"}]
                }
            ))
        ]
    ))
    history.append(types.Content(
        role="user",
        parts=[
            types.Part(function_response=types.FunctionResponse(
                name="count_by_field",
                response={"result": "| category | Count |\n| --- | --- |\n| typeA | 45 |\n| typeB | 23 |\n| typeC | 12 |\nTotal matching documents: 80"}
            ))
        ]
    ))
    history.append(types.Content(
        role="model",
        parts=[types.Part(text="Here are active items grouped by category:\n\n| Category | Count |\n|---------|-------|\n| typeA | 45 |\n| typeB | 23 |\n| typeC | 12 |\n\nTotal: 80 active items found.")]
    ))

    # Third few-shot: aggregate with filters (teaches filtering pattern)
    history.append(types.Content(
        role="user",
        parts=[types.Part(text="Show me the sum of count grouped by category, but only for active items")]
    ))
    history.append(types.Content(
        role="model",
        parts=[
            types.Part(function_call=types.FunctionCall(
                name="aggregate",
                args={
                    "index": ES_INDEX,
                    "group_by": "category",
                    "metric_field": "count",
                    "metric_type": "sum",
                    "filters": [{"field": "status", "value": "active"}]
                }
            ))
        ]
    ))
    history.append(types.Content(
        role="user",
        parts=[
            types.Part(function_response=types.FunctionResponse(
                name="aggregate",
                response={"result": "| category | sum(count) | Count |\n| --- | --- | --- |\n| typeA | 1,250 | 45 |\n| typeB | 830 | 23 |\n| typeC | 410 | 12 |\nTotal matching documents: 80"}
            ))
        ]
    ))
    history.append(types.Content(
        role="model",
        parts=[types.Part(text="Here is the sum of count for active items by category:\n\n| Category | Total Count | Documents |\n|---------|------------|----------|\n| typeA | 1,250 | 45 |\n| typeB | 830 | 23 |\n| typeC | 410 | 12 |")]
    ))

    # Add previous conversation messages if any
    if previous_messages:
        for msg in previous_messages:
            role = "model" if msg["role"] == "assistant" else msg["role"]
            history.append(types.Content(
                role=role,
                parts=[types.Part(text=msg["content"])]
            ))

    # Add current user message
    history.append(types.Content(role="user", parts=[types.Part(text=user_message)]))

    MAX_TURNS = 10
    final_answer = ""
    tool_calls_made = []

    for turn in range(MAX_TURNS):
        try:
            # Force tool calling on first turn, allow text on subsequent turns
            if turn == 0 and gemini_tool:
                tool_config = types.ToolConfig(
                    function_calling_config=types.FunctionCallingConfig(
                        mode="ANY"
                    )
                )
            else:
                tool_config = types.ToolConfig(
                    function_calling_config=types.FunctionCallingConfig(
                        mode="AUTO"
                    )
                )

            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=history,
                config=types.GenerateContentConfig(
                    tools=[gemini_tool] if gemini_tool else None,
                    tool_config=tool_config if gemini_tool else None,
                    system_instruction=_get_system_instruction()
                )
            )

            # Add assistant response to history
            history.append(response.candidates[0].content)

            # Extract function calls
            fcalls = [
                p.function_call for p in response.candidates[0].content.parts
                if hasattr(p, 'function_call') and p.function_call
            ]

            # If no function calls, we have final answer
            if not fcalls:
                final_answer = response.text

                if hasattr(st, 'session_state') and st.session_state.get("debug_mode", False):
                    st.info(f"🔍 Debug: Final answer on turn {turn + 1}. Tools called: {len(tool_calls_made)}")

                break

            # Execute all function calls
            tool_responses = []
            for fc in fcalls:
                tool_calls_made.append(fc.name)
                result = execute_mcp_tool(fc.name, dict(fc.args))

                tool_responses.append(
                    types.Part(
                        function_response=types.FunctionResponse(
                            name=fc.name,
                            response={"result": result}
                        )
                    )
                )

            # Add tool results to history
            history.append(types.Content(role="user", parts=tool_responses))

        except Exception as e:
            return f"❌ Error during agent loop: {str(e)}"

    if final_answer and tool_calls_made:
        citation = f"\n\n✅ *Data from OpenSearch via: {', '.join(set(tool_calls_made))}*"
        return final_answer + citation
    elif final_answer and not tool_calls_made:
        return "❌ I was unable to query the database for this request. Please try rephrasing your question, for example:\n- *Show me 5 sample documents*\n- *What fields are in this index?*\n- *Count documents grouped by [field]*"

    return final_answer or "⚠️ Max reasoning turns reached. Please refine your question."


def main():
    """Main Streamlit application"""

    # Re-read .env on every Streamlit rerun so config changes are picked up
    global MODEL_NAME, GEMINI_API_KEY, ES_INDEX, OPENSEARCH_HOSTS
    cfg = _reload_config()
    MODEL_NAME = cfg["MODEL_NAME"]
    GEMINI_API_KEY = cfg["GEMINI_API_KEY"]
    ES_INDEX = cfg["ES_INDEX"]
    OPENSEARCH_HOSTS = cfg["OPENSEARCH_HOSTS"]

    st.set_page_config(
        page_title="Cloud Governance AI Agent",
        page_icon="☁️",
        layout="wide"
    )

    st.title("☁️ Cloud Governance AI Agent")
    st.caption("Ask questions about cloud costs, usage, and policy compliance in natural language")

    # Index will be set from sidebar selectbox; initialize from .env default
    if "es_index" not in st.session_state:
        st.session_state.es_index = ES_INDEX

    # Initialize session state - load from file if exists (do this before sidebar)
    if "messages" not in st.session_state:
        st.session_state.messages = load_conversation_history()
        if st.session_state.messages:
            st.info(f"📂 Loaded {len(st.session_state.messages)} previous messages from history")

    # Initialize MCP tools (only once)
    if "mcp_tools" not in st.session_state:
        with st.spinner("🔄 Connecting to MCP server and discovering tools..."):
            # Run async function in separate thread with clean event loop
            tools = fetch_mcp_tools()
            st.session_state.mcp_tools = tools
            if tools:
                st.success(f"✅ Loaded {len(tools)} tools from MCP server")
            else:
                st.error("❌ No tools available. Check if MCP server is running.")

    # Sidebar
    with st.sidebar:
        st.header("⚙️ Configuration")

        # Index selector dropdown
        available_indices = _fetch_available_indices()
        if available_indices:
            default_idx = available_indices.index(ES_INDEX) if ES_INDEX in available_indices else 0
            selected_index = st.selectbox(
                "OpenSearch Index",
                available_indices,
                index=default_idx,
                help="Select the index to query. Changing this resets the conversation.",
            )
            if selected_index != st.session_state.es_index:
                st.session_state.es_index = selected_index
                ES_INDEX = selected_index
                clear_conversation_history()
                st.session_state.pop("messages", None)
                st.session_state.pop("mcp_tools", None)
                st.rerun()
            ES_INDEX = st.session_state.es_index
        else:
            st.text_input("OpenSearch Index", value=ES_INDEX, disabled=True)

        st.caption(f"**Model:** {MODEL_NAME} | **OpenSearch:** {OPENSEARCH_HOSTS}")

        # Connection status
        if "mcp_tools" in st.session_state and st.session_state.mcp_tools:
            st.success(f"✅ Connected ({len(st.session_state.mcp_tools)} tools)")
        else:
            st.warning("⚠️ Not connected")

        st.divider()

        # Conversation info
        if "messages" in st.session_state and st.session_state.messages:
            st.info(f"💬 **Messages:** {len(st.session_state.messages)}")
            st.caption("✅ Context preserved across queries")
            if os.path.exists(CONVERSATION_FILE):
                import datetime
                mod_time = os.path.getmtime(CONVERSATION_FILE)
                last_saved = datetime.datetime.fromtimestamp(mod_time).strftime("%Y-%m-%d %H:%M:%S")
                st.caption(f"Last saved: {last_saved}")

        st.divider()

        # Debug mode toggle
        if "debug_mode" not in st.session_state:
            st.session_state.debug_mode = True  # Default to True to see what's happening

        st.session_state.debug_mode = st.checkbox(
            "🐛 Debug Mode (Show Tool Calls)",
            value=st.session_state.debug_mode,
            help="Show detailed tool calls and responses for debugging"
        )

        st.divider()

        # Reset button
        if st.button("🧹 Reset Conversation", use_container_width=True):
            clear_conversation_history()
            st.session_state.clear()
            st.rerun()

        # Export button
        if "messages" in st.session_state and st.session_state.messages:
            import json
            import datetime

            # Create JSON export
            export_data = {
                "exported_at": datetime.datetime.now().isoformat(),
                "model": MODEL_NAME,
                "message_count": len(st.session_state.messages),
                "messages": st.session_state.messages
            }

            st.download_button(
                label="📥 Export Chat History",
                data=json.dumps(export_data, indent=2),
                file_name=f"chat_history_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json",
                use_container_width=True
            )

        st.divider()

        # Example queries
        st.subheader("📝 Example Queries")
        st.caption(f"Queries will search: `{ES_INDEX}`")

        st.markdown("""
        **Discovery Queries:**
        - *What fields are available in this index?*
        - *Show me 5 sample documents*
        - *List all unique values for [field_name]*

        **Data Queries:**
        - *Count documents by [field_name]*
        - *Show documents from the last 7 days*
        - *Filter by [field_name] = [value]*

        **Aggregation Queries:**
        - *Total/average/max of [numeric_field]*
        - *Group by [field] and sum [numeric_field]*
        - *Top 10 [field] by [metric]*
        """)

        st.divider()

        # Data integrity reminder
        st.warning("⚠️ **Data Integrity**: Always check debug tool calls to verify data is from OpenSearch, not generated")

    # Display chat history
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Chat input
    if prompt := st.chat_input("Ask about cloud costs, usage, or policies..."):
        # Add user message
        st.session_state.messages.append({
            "role": "user",
            "content": prompt
        })

        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)

        # Get AI response
        with st.chat_message("assistant"):
            with st.spinner("🤖 Investigating..."):
                # Pass previous messages for context (exclude the just-added user message)
                previous = st.session_state.messages[:-1] if len(st.session_state.messages) > 1 else []
                response = run_agent_loop_gemini(
                    prompt,
                    st.session_state.mcp_tools,
                    previous_messages=previous
                )
            st.markdown(response)

        # Add assistant message to history
        st.session_state.messages.append({
            "role": "assistant",
            "content": response
        })

        # Save conversation to file
        save_conversation_history(st.session_state.messages)


if __name__ == "__main__":
    main()

# Cloud Governance AI Agent

AI-powered natural language interface for querying cloud-governance OpenSearch data using MCP (Model Context Protocol).

## Overview

This application allows you to ask questions about cloud costs, usage, and policy compliance in plain English, without needing to know OpenSearch query syntax or Kibana dashboard building.

**Architecture:**
- **Streamlit Web UI**: Chat interface (port 8501)
- **Custom MCP Server**: Python subprocess with high-level query tools (stdio transport, no container)
- **Google Gemini AI**: Natural language understanding and tool calling
- **OpenSearch/Elasticsearch**: Your existing cloud-governance data

## Prerequisites

### System Requirements
- **OS**: Linux (RHEL, Fedora, CentOS) or macOS
- **Python**: 3.10+

### Access Requirements
1. **OpenSearch/Elasticsearch Cluster**
   - Host URL (e.g., `http://your-host:9200`)
   - Username and password (if authentication enabled)
   - Cloud-governance indices with data

2. **Google Gemini API Key**
   - Get from: https://ai.google.dev/
   - Free tier available for development

## Quick Start

### 1. Configure Environment

```bash
cd cloud-governance-mcp
cp .env.example .env
vi .env
```

Fill in your credentials:

```bash
GEMINI_API_KEY=your-actual-gemini-api-key
OPENSEARCH_HOSTS=http://your-opensearch-host:9200
# OPENSEARCH_USERNAME=your-username   (only if auth required)
# OPENSEARCH_PASSWORD=your-password   (only if auth required)
```

### 2. Start the Application

```bash
./run_agent.sh
```

The MCP server starts automatically as a subprocess -- no separate container or process needed.

**Expected output:**
```
Streamlit started successfully
Access the UI at: http://localhost:8501
```

### 3. Open in Browser

Navigate to: http://localhost:8501

## Available Tools

The AI agent has 7 query tools available:

| Tool | Description |
|------|-------------|
| `list_indices` | List all cloud-governance indices with document counts |
| `get_fields` | Discover field names and types for an index |
| `search_documents` | Filtered search with simple field/value pairs (auto-handles `.keyword`) |
| `count_by_field` | Group documents by a field and count (terms aggregation) |
| `aggregate` | Compute sum/avg/max/min on numeric fields, grouped by another field |
| `date_range_search` | Search within a date range with optional filters |
| `raw_search` | Escape hatch for complex raw OpenSearch Query DSL |

## Usage Examples

### Example Questions

**Discovery:**
```
What fields are available in this index?
Show me 5 sample documents
What indices are available?
```

**Filtered Searches:**
```
Show me all zombie_cluster_resource resources from PERF-DEPT
Find all unattached volumes in us-east-1
List resources with skip_policy tag
```

**Aggregations:**
```
Count documents by policy type
Top 10 accounts by resource count
Total yearly savings by account
Average cost per region
```

**Date Ranges:**
```
Show resources created in the last 7 days
Find all policies that ran between 2026-01-01 and 2026-03-31
```

### How It Works

1. **You ask a question** in natural language
2. **AI selects the right tool** (search, count, aggregate, etc.)
3. **MCP server builds the query** automatically (handles `.keyword` suffixes, Query DSL construction)
4. **AI formats the results** as markdown tables
5. **You get the answer** with data summary

## Troubleshooting

### Streamlit Won't Start

```bash
# Kill existing process
kill $(lsof -ti tcp:8501)

# Try again
./run_agent.sh
```

### AI Not Calling Tools

- Check GEMINI_API_KEY is valid
- Verify tools loaded (check sidebar: "Connected (X tools)")
- Try more specific questions
- Check streamlit.log for errors

### OpenSearch Connection Failed

```bash
# Test connection manually
curl http://your-opensearch-host:9200/_cat/indices

# Check non-secret OpenSearch settings
grep -E '^(OPENSEARCH_HOSTS|OPENSEARCH_USERNAME)=' .env
```

## Management Commands

```bash
# View logs
tail -f streamlit.log

# Stop Streamlit
kill $(lsof -ti tcp:8501)

# Restart
./run_agent.sh

# Update dependencies
source .venv/bin/activate
pip install -r requirements.txt --upgrade
```

## Available OpenSearch Indices

The cloud-governance repository populates these indices:

| Index | Description |
|-------|-------------|
| `cloud-governance-policy-es-index` | Policy execution results |
| `cloud-governance-global-cost-billing-index` | Cost billing data |
| `cloud-governance-cost-explorer-perf` | Performance account costs |
| `cloud-governance-cost-explorer-psap` | PSAP account costs |
| `cloud-governance-cost-explorer-global` | Global cost explorer |
| `cloud-governance-resource-orchestration` | CRO tracking |
| `cloud-governance-yearly-saving` | Yearly savings analysis |

## Security Notes

- `.env` file is gitignored (never commit credentials)
- Uses read-only OpenSearch credentials (recommended)
- Streamlit has no built-in authentication (deploy behind VPN)
- GEMINI_API_KEY gives full access to your AI usage quota

## Advanced Configuration

### Use Different Gemini Model

Edit `.env`:
```bash
MODEL_NAME=gemini-1.5-pro    # More capable, slower
MODEL_NAME=gemini-2.5-flash  # Experimental, fastest
```

### Change Streamlit Port

Edit `run_agent.sh`:
```bash
streamlit run app.py --server.port 9001
```

### Connect to Different OpenSearch Cluster

Update `.env`:
```bash
OPENSEARCH_HOSTS=http://my-other-cluster.example.com:9200
OPENSEARCH_USERNAME=different-user
OPENSEARCH_PASSWORD=different-password
```

Then restart: `./run_agent.sh`

## Project Structure

```
cloud-governance-mcp/
├── .env                  # Configuration (DO NOT COMMIT)
├── .env.example         # Template for .env
├── .gitignore           # Ignore sensitive files
├── app.py               # Streamlit chat application
├── mcp_server.py        # Custom MCP server with high-level query tools
├── requirements.txt     # Python dependencies
├── run_agent.sh         # Start Streamlit (MCP server auto-starts)
├── README.md            # This file
├── .venv/               # Virtual environment (auto-created)
└── streamlit.log        # Application logs
```

## Support

- **Cloud Governance**: https://github.com/redhat-performance/cloud-governance
- **MCP Documentation**: https://modelcontextprotocol.io/
- **Streamlit Docs**: https://docs.streamlit.io/
- **Gemini API**: https://ai.google.dev/

## License

Same as cloud-governance repository (Apache License 2.0)

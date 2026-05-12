"""
Cloud Governance MCP Server
Exposes high-level OpenSearch query tools via Model Context Protocol (stdio transport).
"""

import json
import os
import sys
from typing import Any

from dotenv import load_dotenv
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool
from opensearchpy import OpenSearch

load_dotenv()

OPENSEARCH_HOSTS = os.getenv("OPENSEARCH_HOSTS", "http://localhost:9200")
OPENSEARCH_USERNAME = os.getenv("OPENSEARCH_USERNAME", "")
OPENSEARCH_PASSWORD = os.getenv("OPENSEARCH_PASSWORD", "")

server = Server("cloud-governance-mcp")

_client: OpenSearch | None = None
_mapping_cache: dict[str, dict[str, str]] = {}


def _get_client() -> OpenSearch:
    global _client
    if _client is not None:
        return _client

    parsed = OPENSEARCH_HOSTS
    use_ssl = parsed.startswith("https")

    kwargs: dict[str, Any] = {
        "hosts": [OPENSEARCH_HOSTS],
        "use_ssl": use_ssl,
        "verify_certs": False,
        "ssl_show_warn": False,
        "timeout": 30,
    }
    if OPENSEARCH_USERNAME and OPENSEARCH_PASSWORD:
        kwargs["http_auth"] = (OPENSEARCH_USERNAME, OPENSEARCH_PASSWORD)

    _client = OpenSearch(**kwargs)
    return _client


def _get_field_types(index: str) -> dict[str, str]:
    """Return {field_name: es_type} for an index, with caching."""
    if index in _mapping_cache:
        return _mapping_cache[index]

    client = _get_client()
    mappings = client.indices.get_mapping(index=index)

    field_types: dict[str, str] = {}
    index_key = list(mappings.keys())[0]
    properties = mappings[index_key].get("mappings", {}).get("properties", {})

    def _extract(props: dict, prefix: str = ""):
        for name, meta in props.items():
            full = f"{prefix}{name}" if not prefix else f"{prefix}.{name}"
            ftype = meta.get("type", "object")
            field_types[full] = ftype
            if "properties" in meta:
                _extract(meta["properties"], full)
            if "fields" in meta:
                for sub_name, sub_meta in meta["fields"].items():
                    sub_full = f"{full}.{sub_name}"
                    field_types[sub_full] = sub_meta.get("type", "keyword")

    _extract(properties)
    _mapping_cache[index] = field_types
    return field_types


def _find_field(index: str, field: str) -> str:
    """Find the actual field name, handling case-insensitive matching."""
    field_types = _get_field_types(index)
    if field in field_types:
        return field
    field_lower = field.lower()
    candidates = [f for f in field_types if f.lower() == field_lower and ".keyword" not in f]
    if not candidates:
        return field
    # Prefer the candidate that has a .keyword sub-field (more useful for queries)
    for c in candidates:
        if f"{c}.keyword" in field_types:
            return c
    return candidates[0]


def _resolve_field(index: str, field: str) -> str:
    """Resolve field name (case-insensitive) and append .keyword for text fields."""
    field_types = _get_field_types(index)
    actual = _find_field(index, field)
    if actual in field_types and field_types[actual] == "text":
        if f"{actual}.keyword" in field_types:
            return f"{actual}.keyword"
    return actual


def _coerce_value(index: str, field: str, value: Any) -> Any:
    """Cast value to the correct type based on field mapping."""
    field_types = _get_field_types(index)
    actual = _find_field(index, field)
    ftype = field_types.get(actual, "")
    if ftype in ("integer", "long", "short", "byte"):
        try:
            return int(value)
        except (ValueError, TypeError):
            return value
    if ftype in ("float", "double", "half_float", "scaled_float"):
        try:
            return float(value)
        except (ValueError, TypeError):
            return value
    if ftype == "boolean":
        if isinstance(value, bool):
            return value
        return str(value).lower() in ("true", "1", "yes")
    # For text/keyword fields, ensure string
    if isinstance(value, (int, float)):
        return str(value)
    return value


def _build_bool_query(index: str, filters: list[dict] | None) -> dict:
    """Build a bool/must query from a simple filter list."""
    if not filters:
        return {"match_all": {}}

    must_clauses = []
    for f in filters:
        field = f.get("field", "")
        value = f.get("value", "")
        resolved = _resolve_field(index, field)
        coerced = _coerce_value(index, field, value)
        must_clauses.append({"term": {resolved: coerced}})

    return {"bool": {"must": must_clauses}}


def _format_hits(hits: list[dict], fields: list[str] | None = None) -> str:
    """Format ES hits as a readable table."""
    if not hits:
        return "No documents found."

    sources = [h.get("_source", {}) for h in hits]

    if fields:
        display_fields = fields
    else:
        all_keys: list[str] = []
        for src in sources:
            for k in src:
                if k not in all_keys:
                    all_keys.append(k)
        display_fields = all_keys[:15]

    header = " | ".join(display_fields)
    separator = " | ".join(["---"] * len(display_fields))
    rows = []
    for src in sources:
        row = " | ".join(str(src.get(f, "")) for f in display_fields)
        rows.append(row)

    table = f"| {header} |\n| {separator} |\n"
    table += "\n".join(f"| {r} |" for r in rows)
    return table


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="list_indices",
            description="List all OpenSearch indices with document counts",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="get_fields",
            description="Get field names and types for an index. Call this first to discover available fields.",
            inputSchema={
                "type": "object",
                "properties": {
                    "index": {"type": "string", "description": "Index name to inspect"},
                },
                "required": ["index"],
            },
        ),
        Tool(
            name="search_documents",
            description=(
                "Search documents with simple filters. Filters are AND-ed. "
                "No need to use .keyword suffix — it is handled automatically."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "index": {"type": "string", "description": "Index name"},
                    "filters": {
                        "type": "array",
                        "description": 'List of filters, e.g. [{"field": "status", "value": "active"}]',
                        "items": {
                            "type": "object",
                            "properties": {
                                "field": {"type": "string"},
                                "value": {"type": "string"},
                            },
                            "required": ["field", "value"],
                        },
                    },
                    "fields": {
                        "type": "array",
                        "description": "Fields to include in results (optional, defaults to all)",
                        "items": {"type": "string"},
                    },
                    "size": {
                        "type": "integer",
                        "description": "Number of results to return (default 10)",
                    },
                    "sort_by": {
                        "type": "object",
                        "description": 'Sort results, e.g. {"field": "timestamp", "order": "desc"}',
                        "properties": {
                            "field": {"type": "string"},
                            "order": {"type": "string", "enum": ["asc", "desc"]},
                        },
                    },
                },
                "required": ["index"],
            },
        ),
        Tool(
            name="count_by_field",
            description=(
                "Count documents grouped by a field (terms aggregation). "
                "No need to use .keyword suffix — it is handled automatically."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "index": {"type": "string", "description": "Index name"},
                    "group_by": {"type": "string", "description": "Field to group by"},
                    "filters": {
                        "type": "array",
                        "description": "Optional filters to narrow results",
                        "items": {
                            "type": "object",
                            "properties": {
                                "field": {"type": "string"},
                                "value": {"type": "string"},
                            },
                            "required": ["field", "value"],
                        },
                    },
                    "top_n": {
                        "type": "integer",
                        "description": "Number of top groups to return (default 20)",
                    },
                },
                "required": ["index", "group_by"],
            },
        ),
        Tool(
            name="aggregate",
            description=(
                "Compute a metric (sum, avg, max, min) on a numeric field, grouped by another field. "
                "No need to use .keyword suffix — it is handled automatically."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "index": {"type": "string", "description": "Index name"},
                    "group_by": {"type": "string", "description": "Field to group by"},
                    "metric_field": {"type": "string", "description": "Numeric field to aggregate"},
                    "metric_type": {
                        "type": "string",
                        "enum": ["sum", "avg", "max", "min"],
                        "description": "Aggregation type",
                    },
                    "filters": {
                        "type": "array",
                        "description": "Optional filters",
                        "items": {
                            "type": "object",
                            "properties": {
                                "field": {"type": "string"},
                                "value": {"type": "string"},
                            },
                            "required": ["field", "value"],
                        },
                    },
                    "top_n": {
                        "type": "integer",
                        "description": "Number of top groups to return (default 20)",
                    },
                },
                "required": ["index", "group_by", "metric_field", "metric_type"],
            },
        ),
        Tool(
            name="date_range_search",
            description="Search documents within a date range, with optional filters.",
            inputSchema={
                "type": "object",
                "properties": {
                    "index": {"type": "string", "description": "Index name"},
                    "date_field": {"type": "string", "description": "Date field name (e.g. timestamp, SnapshotDate)"},
                    "gte": {"type": "string", "description": "Start date (yyyy-MM-dd)"},
                    "lte": {"type": "string", "description": "End date (yyyy-MM-dd)"},
                    "filters": {
                        "type": "array",
                        "description": "Optional additional filters",
                        "items": {
                            "type": "object",
                            "properties": {
                                "field": {"type": "string"},
                                "value": {"type": "string"},
                            },
                            "required": ["field", "value"],
                        },
                    },
                    "size": {
                        "type": "integer",
                        "description": "Number of results (default 10)",
                    },
                },
                "required": ["index", "date_field", "gte", "lte"],
            },
        ),
        Tool(
            name="raw_search",
            description="Execute a raw OpenSearch Query DSL query. Use only for complex queries that don't fit the other tools.",
            inputSchema={
                "type": "object",
                "properties": {
                    "index": {"type": "string", "description": "Index name"},
                    "query_body": {
                        "type": "object",
                        "description": "Full OpenSearch Query DSL body",
                    },
                },
                "required": ["index", "query_body"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    try:
        result = _dispatch(name, arguments)
        return [TextContent(type="text", text=result)]
    except Exception as e:
        return [TextContent(type="text", text=f"Error in {name}: {type(e).__name__}: {e}")]


def _dispatch(name: str, args: dict) -> str:
    if name == "list_indices":
        return _tool_list_indices()
    elif name == "get_fields":
        return _tool_get_fields(args["index"])
    elif name == "search_documents":
        return _tool_search_documents(
            index=args["index"],
            filters=args.get("filters"),
            fields=args.get("fields"),
            size=args.get("size", 10),
            sort_by=args.get("sort_by"),
        )
    elif name == "count_by_field":
        return _tool_count_by_field(
            index=args["index"],
            group_by=args["group_by"],
            filters=args.get("filters"),
            top_n=args.get("top_n", 20),
        )
    elif name == "aggregate":
        return _tool_aggregate(
            index=args["index"],
            group_by=args["group_by"],
            metric_field=args["metric_field"],
            metric_type=args["metric_type"],
            filters=args.get("filters"),
            top_n=args.get("top_n", 20),
        )
    elif name == "date_range_search":
        return _tool_date_range_search(
            index=args["index"],
            date_field=args["date_field"],
            gte=args["gte"],
            lte=args["lte"],
            filters=args.get("filters"),
            size=args.get("size", 10),
        )
    elif name == "raw_search":
        return _tool_raw_search(args["index"], args["query_body"])
    else:
        return f"Unknown tool: {name}"


def _tool_list_indices() -> str:
    client = _get_client()
    indices = client.cat.indices(format="json")
    if not indices:
        return "No indices found."

    lines = ["| Index | Docs | Size |", "| --- | --- | --- |"]
    for idx in sorted(indices, key=lambda x: x.get("index", "")):
        lines.append(f"| {idx.get('index', '')} | {idx.get('docs.count', '0')} | {idx.get('store.size', 'N/A')} |")
    return "\n".join(lines)


def _tool_get_fields(index: str) -> str:
    _mapping_cache.pop(index, None)
    field_types = _get_field_types(index)
    if not field_types:
        return f"No fields found in index '{index}'."

    numeric_types = {"integer", "long", "short", "byte", "float", "double", "half_float", "scaled_float"}
    # Skip .keyword sub-fields for cleaner output
    top_level = {f: t for f, t in field_types.items() if ".keyword" not in f}

    lines = ["| Field | Type | Aggregatable |", "| --- | --- | --- |"]
    for field, ftype in sorted(top_level.items()):
        agg = "Yes (numeric)" if ftype in numeric_types else "Yes (keyword)" if ftype == "keyword" else ""
        lines.append(f"| {field} | {ftype} | {agg} |")

    numeric_fields = [f for f, t in top_level.items() if t in numeric_types]
    if numeric_fields:
        lines.append(f"\nNumeric fields for aggregation (sum/avg/max/min): {', '.join(numeric_fields)}")
    return "\n".join(lines)


def _tool_search_documents(
    index: str,
    filters: list[dict] | None = None,
    fields: list[str] | None = None,
    size: int = 10,
    sort_by: dict | None = None,
) -> str:
    client = _get_client()
    query = _build_bool_query(index, filters)

    body: dict[str, Any] = {"query": query, "size": size}
    if sort_by:
        sort_field = _resolve_field(index, sort_by.get("field", ""))
        body["sort"] = [{sort_field: {"order": sort_by.get("order", "desc")}}]
    if fields:
        body["_source"] = fields

    response = client.search(index=index, body=body)
    total = response["hits"]["total"]["value"]
    hits = response["hits"]["hits"]

    table = _format_hits(hits, fields)
    result = f"Total matching documents: {total}\nShowing {len(hits)} results:\n\n{table}"
    if total == 0 and filters:
        result += f"\n\nDebug - query sent: {json.dumps(body, default=str)}"
    return result


def _tool_count_by_field(
    index: str,
    group_by: str,
    filters: list[dict] | None = None,
    top_n: int = 20,
) -> str:
    client = _get_client()
    query = _build_bool_query(index, filters)
    resolved_group = _resolve_field(index, group_by)

    body: dict[str, Any] = {
        "size": 0,
        "query": query,
        "aggs": {
            "group_count": {
                "terms": {"field": resolved_group, "size": top_n}
            }
        },
    }

    response = client.search(index=index, body=body)
    total = response["hits"]["total"]["value"]
    buckets = response.get("aggregations", {}).get("group_count", {}).get("buckets", [])

    if not buckets:
        field_types = _get_field_types(index)
        actual_group = _find_field(index, group_by)
        msg = f"No results found. Total documents matching filters: {total}"
        if total > 0 and field_types.get(actual_group) == "text" and f"{actual_group}.keyword" not in field_types:
            msg += f"\nWARNING: '{actual_group}' is a text field without a .keyword sub-field. Aggregations on analyzed text fields return empty results. Try a different field."
        msg += f"\nDebug - query sent: {json.dumps(body, default=str)}"
        return msg

    lines = [f"| {group_by} | Count |", "| --- | --- |"]
    for b in buckets:
        lines.append(f"| {b['key']} | {b['doc_count']} |")

    other = response.get("aggregations", {}).get("group_count", {}).get("sum_other_doc_count", 0)
    footer = f"\nTotal matching documents: {total}"
    if other > 0:
        footer += f"\n(+{other} documents in other groups not shown)"
    return "\n".join(lines) + footer


def _tool_aggregate(
    index: str,
    group_by: str,
    metric_field: str,
    metric_type: str,
    filters: list[dict] | None = None,
    top_n: int = 20,
) -> str:
    client = _get_client()
    query = _build_bool_query(index, filters)
    resolved_group = _resolve_field(index, group_by)
    resolved_metric = _find_field(index, metric_field)

    body: dict[str, Any] = {
        "size": 0,
        "query": query,
        "aggs": {
            "group_agg": {
                "terms": {"field": resolved_group, "size": top_n},
                "aggs": {
                    "metric_value": {metric_type: {"field": resolved_metric}}
                },
            }
        },
    }

    response = client.search(index=index, body=body)
    total = response["hits"]["total"]["value"]
    buckets = response.get("aggregations", {}).get("group_agg", {}).get("buckets", [])

    if not buckets:
        msg = f"No results found. Total documents matching filters: {total}"
        msg += f"\nDebug - query sent: {json.dumps(body, default=str)}"
        return msg

    lines = [f"| {group_by} | {metric_type}({metric_field}) | Count |", "| --- | --- | --- |"]
    all_zero = True
    for b in buckets:
        val = b.get("metric_value", {}).get("value", 0)
        if val and val != 0:
            all_zero = False
        formatted = f"{val:,.2f}" if isinstance(val, float) else str(val)
        lines.append(f"| {b['key']} | {formatted} | {b['doc_count']} |")

    result = "\n".join(lines) + f"\nTotal matching documents: {total}"

    if all_zero and total > 0:
        field_types = _get_field_types(index)
        numeric_types = {"integer", "long", "short", "byte", "float", "double", "half_float", "scaled_float"}
        numeric_fields = [f for f, t in field_types.items() if t in numeric_types and ".keyword" not in f]
        result += (
            f"\n\nWARNING: All {metric_type} values are 0. "
            f"The field '{metric_field}' may not exist or may not be numeric. "
            f"Available numeric fields: {', '.join(numeric_fields)}"
            f"\nDebug - query sent: {json.dumps(body, default=str)}"
        )

    return result


def _tool_date_range_search(
    index: str,
    date_field: str,
    gte: str,
    lte: str,
    filters: list[dict] | None = None,
    size: int = 10,
) -> str:
    client = _get_client()

    must_clauses = []
    if filters:
        for f in filters:
            field = f.get("field", "")
            resolved = _resolve_field(index, field)
            coerced = _coerce_value(index, field, f.get("value", ""))
            must_clauses.append({"term": {resolved: coerced}})

    field_types = _get_field_types(index)
    resolved_date = _find_field(index, date_field)
    ftype = field_types.get(resolved_date, "")

    if ftype == "text":
        kw = f"{resolved_date}.keyword"
        range_field = kw if kw in field_types else resolved_date
        range_clause = {"gte": gte, "lte": lte}
    else:
        range_field = resolved_date
        range_clause = {"gte": gte, "lte": lte, "format": "yyyy-MM-dd"}

    must_clauses.append({"range": {range_field: range_clause}})

    sort_field = range_field
    body: dict[str, Any] = {
        "query": {"bool": {"must": must_clauses}},
        "size": size,
        "sort": [{sort_field: {"order": "desc"}}],
    }

    response = client.search(index=index, body=body)
    total = response["hits"]["total"]["value"]
    hits = response["hits"]["hits"]

    table = _format_hits(hits)
    return f"Total matching documents: {total}\nShowing {len(hits)} results:\n\n{table}"


def _tool_raw_search(index: str, query_body: dict) -> str:
    client = _get_client()
    response = client.search(index=index, body=query_body)
    return json.dumps(response, indent=2, default=str)


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())

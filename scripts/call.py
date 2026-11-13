"""Call one of the server's tools and print what comes back, as an MCP host (and so the model) sees it.

The server is launched over stdio, the same way Claude Code or Claude Desktop runs it.

Usage:
    uv run python scripts/call.py                        # interactive: pick a tool, then paste JSON arguments
                                                         #   or get prompted for each one
    uv run python scripts/call.py --list                 # list the tools
    uv run python scripts/call.py get_position --help-tool   # a tool's description and parameters
    uv run python scripts/call.py get_position target=Jupiter "place=Moab, Utah"
    uv run python scripts/call.py get_position '{"target": "Jupiter", "place": "Moab, Utah"}'

Arguments are key=value pairs (values are converted to the type the tool's schema asks for) or one JSON
object. Output is each content block the model receives; --raw prints the whole JSON-RPC result instead.
Image blocks are saved to a temp folder and their path printed.
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import json
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

from mcp import Client
from mcp.client.stdio import StdioServerParameters

IMAGE_DIR = Path(tempfile.gettempdir()) / "astronomy-mcp-call"


# ---- schema helpers -------------------------------------------------------------------------------

def _types(prop: dict[str, Any]) -> list[str]:
    """JSON-schema types a property accepts, looking through anyOf (used for `X | None`)."""
    if "type" in prop:
        return [prop["type"]] if isinstance(prop["type"], str) else list(prop["type"])
    found: list[str] = []
    for option in prop.get("anyOf", []):
        found += _types(option)
    return found


def _enum(prop: dict[str, Any]) -> list[Any] | None:
    if "enum" in prop:
        return prop["enum"]
    for option in prop.get("anyOf", []):
        if "enum" in option:
            return option["enum"]
    return None


def _type_label(prop: dict[str, Any]) -> str:
    choices = _enum(prop)
    if choices:
        return " | ".join(map(str, choices))
    types = [t for t in _types(prop) if t != "null"]
    return " | ".join(types) or "any"


def coerce(raw: str, prop: dict[str, Any]) -> Any:
    """Turn typed-in text into the value the schema expects."""
    types = _types(prop)
    if raw.lower() in ("null", "none") and "null" in types:
        return None
    if types == ["string"] or set(types) == {"string", "null"}:
        return raw
    if "boolean" in types and raw.lower() in ("true", "false", "yes", "no", "y", "n", "1", "0"):
        return raw.lower() in ("true", "yes", "y", "1")
    try:
        return json.loads(raw)  # numbers, arrays, objects
    except json.JSONDecodeError:
        return raw  # let the server's validation report it


def parse_args(pairs: list[str], schema: dict[str, Any]) -> dict[str, Any]:
    if len(pairs) == 1 and pairs[0].lstrip().startswith("{"):
        return json.loads(pairs[0])
    props = schema.get("properties", {})
    args: dict[str, Any] = {}
    for pair in pairs:
        key, sep, value = pair.partition("=")
        if not sep:
            raise SystemExit(f"Expected key=value, got {pair!r}")
        if key not in props:
            raise SystemExit(f"Unknown parameter {key!r}. Parameters: {', '.join(props) or '(none)'}")
        args[key] = coerce(value, props[key])
    return args


# ---- printing -------------------------------------------------------------------------------------

def describe(tool: Any) -> None:
    print(f"\n{tool.name}")
    if tool.description:
        print("\n" + tool.description.strip())
    props = tool.input_schema.get("properties", {})
    required = set(tool.input_schema.get("required", []))
    if not props:
        print("\nParameters: none")
        return
    print("\nParameters:")
    for name, prop in props.items():
        flag = "required" if name in required else f"default {json.dumps(prop.get('default'))}"
        print(f"  {name} ({_type_label(prop)}; {flag})")
        if prop.get("description"):
            print(f"      {prop['description']}")


def show_result(name: str, result: Any, elapsed: float, raw: bool) -> None:
    if raw:
        print(json.dumps(result.model_dump(mode="json", by_alias=True, exclude_none=True), indent=2, ensure_ascii=False))
        return
    status = "ERROR (isError: true)" if result.is_error else "ok"
    print(f"\n== {name} -> {status} in {elapsed:.1f}s, {len(result.content)} content block(s)")
    for i, block in enumerate(result.content, 1):
        print(f"\n--- [{i}] {block.type} ---")
        if block.type == "text":
            print(block.text)
        elif block.type == "image":
            IMAGE_DIR.mkdir(exist_ok=True)
            ext = block.mime_type.split("/")[-1]
            path = IMAGE_DIR / f"{name}-{int(time.time())}-{i}.{ext}"
            path.write_bytes(base64.b64decode(block.data))
            print(f"{block.mime_type}, {path.stat().st_size:,} bytes, saved to {path}")
        else:
            print(json.dumps(block.model_dump(mode="json", by_alias=True, exclude_none=True), indent=2))


# ---- interactive ----------------------------------------------------------------------------------

def read_json_object(first_line: str) -> dict[str, Any] | None:
    """Parse a pasted JSON object, reading more lines if it spans several. None if it isn't valid."""
    text = first_line
    while True:
        try:
            value = json.loads(text)
        except json.JSONDecodeError as exc:
            if exc.pos < len(text.rstrip()):  # broken in the middle, not just unfinished
                print(f"    Invalid JSON: {exc}")
                return None
            more = input("... ")
            if not more.strip():
                print(f"    Invalid JSON: {exc}")
                return None
            text += "\n" + more
            continue
        if not isinstance(value, dict):
            print("    Expected a JSON object, e.g. {\"target\": \"M31\"}")
            return None
        return value


def prompt_json(tool: Any) -> dict[str, Any] | None:
    """Offer to take all arguments as one JSON object. None means fill them in one at a time."""
    props = tool.input_schema.get("properties", {})
    required = set(tool.input_schema.get("required", []))
    while True:
        line = input("\nPaste arguments as a JSON object, or press Enter to fill them in one at a time:\n> ").strip()
        if not line:
            return None
        args = read_json_object(line)
        if args is None:
            continue
        unknown = [k for k in args if k not in props]
        if unknown:
            print(f"    Note: {', '.join(unknown)} not in this tool's parameters; sending anyway.")
        missing = [k for k in required if k not in args]
        if missing:
            print(f"    Note: missing required {', '.join(missing)}; sending anyway.")
        return args


def prompt_args(tool: Any) -> dict[str, Any]:
    props = tool.input_schema.get("properties", {})
    required = set(tool.input_schema.get("required", []))
    args: dict[str, Any] = {}
    if props:
        pasted = prompt_json(tool)
        if pasted is not None:
            return pasted
        print("\nEnter values (blank = leave out / use default):")
    for name, prop in props.items():
        hint = "required" if name in required else f"default {json.dumps(prop.get('default'))}"
        while True:
            raw = input(f"  {name} [{_type_label(prop)}; {hint}]: ").strip()
            if raw or name not in required:
                break
            print("    (required)")
        if raw:
            args[name] = coerce(raw, prop)
    return args


def pick_tool(tools: dict[str, Any]) -> Any | None:
    names = sorted(tools)
    while True:
        query = input("\nTool (number, name, part of a name to filter, ? to list, q to quit): ").strip()
        if query.lower() in ("q", "quit", "exit"):
            return None
        if query in ("", "?"):
            for i, n in enumerate(names, 1):
                print(f"  {i:3}. {n}")
            continue
        if query.isdigit() and 1 <= int(query) <= len(names):
            return tools[names[int(query) - 1]]
        if query in tools:
            return tools[query]
        matches = [n for n in names if query.lower() in n.lower()]
        if len(matches) == 1:
            return tools[matches[0]]
        if matches:
            for n in matches:
                print(f"  {names.index(n) + 1:3}. {n}")
        else:
            print("  No tool matches.")


async def interactive(client: Client, tools: dict[str, Any], raw: bool) -> None:
    print(f"Connected to {client.server_info.name} {client.server_info.version}: {len(tools)} tools.")
    while True:
        tool = pick_tool(tools)
        if tool is None:
            return
        describe(tool)
        try:
            args = prompt_args(tool)
        except (KeyboardInterrupt, EOFError):
            print("\n(cancelled)")
            continue
        print(f"\ntools/call {tool.name} {json.dumps(args, ensure_ascii=False)}")
        start = time.perf_counter()
        result = await client.call_tool(tool.name, args)
        show_result(tool.name, result, time.perf_counter() - start, raw)


# ---- main -----------------------------------------------------------------------------------------

async def run(opts: argparse.Namespace) -> int:
    params = StdioServerParameters(command=sys.executable, args=["-m", "astronomy_mcp"])
    async with Client(params) as client:
        tools = {t.name: t for t in (await client.list_tools()).tools}

        if opts.list:
            for name in sorted(tools):
                first_line = (tools[name].description or "").strip().splitlines()[0]
                print(f"{name:32} {first_line}")
            return 0
        if opts.instructions:
            print(client.instructions or "(no instructions)")
            return 0
        if not opts.tool:
            await interactive(client, tools, opts.raw)
            return 0

        tool = tools.get(opts.tool)
        if tool is None:
            close = [n for n in tools if opts.tool.lower() in n.lower()]
            print(f"No tool named {opts.tool!r}." + (f" Did you mean: {', '.join(close)}?" if close else ""))
            return 2
        if opts.help_tool:
            describe(tool)
            return 0

        args = parse_args(opts.args, tool.input_schema)
        start = time.perf_counter()
        result = await client.call_tool(tool.name, args)
        show_result(tool.name, result, time.perf_counter() - start, opts.raw)
        return 1 if result.is_error else 0


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8")  # degree signs etc. on a Windows console
    parser = argparse.ArgumentParser(description="Call an astronomy MCP tool over stdio and print the result.")
    parser.add_argument("tool", nargs="?", help="Tool name; omit for interactive mode")
    parser.add_argument("args", nargs="*", help="key=value pairs, or one JSON object")
    parser.add_argument("--list", action="store_true", help="List tools and exit")
    parser.add_argument("--help-tool", action="store_true", help="Show the tool's description and parameters")
    parser.add_argument("--instructions", action="store_true", help="Print the server's instructions to the model")
    parser.add_argument("--raw", action="store_true", help="Print the full CallToolResult as JSON")
    try:
        return asyncio.run(run(parser.parse_args()))
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    sys.exit(main())

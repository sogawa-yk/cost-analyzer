"""CLI interface using Typer."""

from __future__ import annotations

from typing import Annotated

import typer
from rich.console import Console

from cost_analyzer.config import get_settings, setup_logging
from cost_analyzer.models import ErrorResponse, ErrorType, QueryType

app = typer.Typer(help="自然言語 OCI コストクエリツール")
console = Console()
err_console = Console(stderr=True)

EXIT_CODES = {
    ErrorType.PARSE_ERROR: 1,
    ErrorType.AUTH_ERROR: 2,
    ErrorType.API_ERROR: 3,
    ErrorType.NO_DATA: 4,
}


@app.command()
def query(
    query_text: Annotated[str, typer.Argument(help="自然言語コストクエリ")],
    format: Annotated[str, typer.Option("--format", "-f", help="出力フォーマット: table, json, csv")] = "table",
    lang: Annotated[str, typer.Option("--lang", "-l", help="応答言語: ja, en, auto")] = "auto",
) -> None:
    """自然言語でOCIコストを照会します。"""
    settings = get_settings()
    setup_logging(settings.log_level)

    from cost_analyzer.formatter import format_breakdown, format_error
    from cost_analyzer.oci_client import OCIClient
    from cost_analyzer.parser import parse_query

    # Initialize OCI client
    try:
        with console.status("OCI に接続中...", spinner="dots"):
            oci_client = OCIClient()
    except Exception as e:
        from cost_analyzer.config import map_oci_error

        error_type, message, guidance = map_oci_error(e)
        error = ErrorResponse(
            error_type=ErrorType(error_type),
            message=message,
            guidance=guidance,
        )
        err_console.print(format_error(error))
        raise typer.Exit(code=EXIT_CODES.get(error.error_type, 3)) from None

    # Parse query
    with console.status("クエリを解析中...", spinner="dots"):
        result = parse_query(query_text, oci_client)

    if isinstance(result, ErrorResponse):
        err_console.print(format_error(result))
        raise typer.Exit(code=EXIT_CODES.get(result.error_type, 1))

    # Handle clarification
    if result.needs_clarification:
        console.print(f"[yellow]{result.clarification_message}[/yellow]")
        raise typer.Exit(code=0)

    # Fetch data
    from cost_analyzer.engine import fetch_breakdown

    with console.status("コストデータを取得中...", spinner="dots"):
        if result.query_type == QueryType.BREAKDOWN:
            data = fetch_breakdown(result, oci_client)
        else:
            # Comparison will be added in US2
            from cost_analyzer.engine import fetch_comparison

            data = fetch_comparison(result, oci_client)

    if isinstance(data, ErrorResponse):
        err_console.print(format_error(data))
        raise typer.Exit(code=EXIT_CODES.get(data.error_type, 4))

    # Format and output
    if result.query_type == QueryType.BREAKDOWN:
        output = format_breakdown(data, output_format=format)
    else:
        from cost_analyzer.formatter import format_comparison

        output = format_comparison(data, output_format=format)

    console.print(output, highlight=False)


@app.command()
def serve(
    host: Annotated[str, typer.Option(help="バインドアドレス")] = "0.0.0.0",
    port: Annotated[int, typer.Option(help="バインドポート")] = 8080,
) -> None:
    """FastAPI サーバーを起動します。"""
    import uvicorn

    from cost_analyzer.config import get_settings, setup_logging

    settings = get_settings()
    setup_logging(settings.log_level)
    console.print(f"サーバーを起動中: {host}:{port}")
    uvicorn.run("cost_analyzer.api:app", host=host, port=port, log_level="info")

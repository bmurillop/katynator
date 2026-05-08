"""
CLI tool for iterating the AI extraction prompt against a PDF without the full pipeline.

Usage:
    python -m app.tools.parse_pdf path/to/statement.pdf
    python -m app.tools.parse_pdf path/to/statement.pdf --provider claude
    python -m app.tools.parse_pdf path/to/statement.pdf --provider gemini --raw
    python -m app.tools.parse_pdf path/to/statement.pdf --text-only

Options:
    --provider  gemini | claude | lmstudio  (default: AI_PROVIDER env var or gemini)
    --raw       Also print the raw LLM response before the parsed result
    --text-only Only extract and print the PDF text; do not call the AI
"""
import argparse
import asyncio
import json
import sys
from pathlib import Path


def _extract_text(pdf_path: Path) -> str:
    import pdfplumber
    pages = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                pages.append(page_text)
    return "\n\n".join(pages)


async def _run(args: argparse.Namespace) -> None:
    pdf_path = Path(args.pdf_path)
    if not pdf_path.exists():
        print(f"Error: file not found: {pdf_path}", file=sys.stderr)
        sys.exit(1)

    print(f"Extracting text from: {pdf_path.name}", file=sys.stderr)
    text = _extract_text(pdf_path)

    if not text.strip():
        print("Warning: no text extracted — the PDF may be image-based (OCR not yet supported).", file=sys.stderr)
        sys.exit(1)

    if args.text_only:
        print(text)
        return

    print(f"Extracted {len(text)} characters across {text.count(chr(12)) + 1} page(s).", file=sys.stderr)

    # Import here so the CLI fails fast on missing API keys only when actually calling
    from app.ai.factory import get_provider_by_name
    from app.config import settings

    provider_name = args.provider or settings.ai_provider or "gemini"
    print(f"Calling provider: {provider_name}", file=sys.stderr)

    provider = get_provider_by_name(provider_name)
    result = await provider.parse_financial_document(text)

    if args.raw:
        print("\n─── RAW LLM RESPONSE ───────────────────────────────────────────────────────",
              file=sys.stderr)
        print(result.raw_response or "(not available)", file=sys.stderr)
        print("────────────────────────────────────────────────────────────────────────────\n",
              file=sys.stderr)

    print(json.dumps(result.model_dump(mode="json"), indent=2, ensure_ascii=False))

    # Summary line
    n = len(result.transactions)
    currency = result.currency.value if result.currency else "?"
    bank = result.bank_hint or "unknown bank"
    print(f"\n✓ {n} transaction(s) extracted  |  {currency}  |  {bank}", file=sys.stderr)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract transactions from a PDF bank statement using the configured AI provider."
    )
    parser.add_argument("pdf_path", help="Path to the PDF file")
    parser.add_argument(
        "--provider",
        choices=["gemini", "claude", "lmstudio"],
        default=None,
        help="AI provider to use (default: AI_PROVIDER env var or gemini)",
    )
    parser.add_argument(
        "--raw",
        action="store_true",
        help="Print the raw LLM response (to stderr) before the parsed JSON",
    )
    parser.add_argument(
        "--text-only",
        action="store_true",
        help="Only extract and print the PDF text; skip the AI call",
    )
    args = parser.parse_args()
    asyncio.run(_run(args))


if __name__ == "__main__":
    main()

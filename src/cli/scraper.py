"""Main CLI for VF-Data scraper."""

import asyncio
import argparse
from src.scraper.auth import get_authenticated_browser
from src.scraper.chat_list_scraper import scrape_chat_list
from src.scraper.chat_message_scraper import scrape_chat_messages
from src.training import optimize_prompt, OptimizationConfig


async def scrape_chats(dry_run: bool = False, limit: int = 50, date_filter: str = "all"):
    """Scrape chat list."""
    browser, context = await get_authenticated_browser()

    try:
        run_dir = await scrape_chat_list(
            context,
            dry_run=dry_run,
            dry_run_limit=limit,
            date_filter=date_filter
        )
        print(f"\nChat list scraping completed! Results: {run_dir}")

    finally:
        await context.close()
        await browser.close()


async def scrape_messages(
    date_filter: str = "all",
    limit: int = None,
    dry_run: bool = False,
    dry_run_limit: int = 3,
    workers: int = 1,
    skip_existing: bool = False
):
    """Scrape chat messages."""
    browser, context = await get_authenticated_browser()

    try:
        run_dir = await scrape_chat_messages(
            context,
            date_filter=date_filter,
            chat_limit=limit,
            dry_run=dry_run,
            dry_run_limit=dry_run_limit,
            workers=workers,
            skip_existing=skip_existing
        )
        print(f"\nMessage scraping completed! Results: {run_dir}")

    finally:
        await context.close()
        await browser.close()


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="VF-Data: Soomgo Chat Scraper")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Chat list scraper
    chat_parser = subparsers.add_parser("chats", help="Scrape chat list")
    chat_parser.add_argument("--dry-run", action="store_true", help="Dry run mode")
    chat_parser.add_argument("--limit", type=int, default=50, help="Limit for dry run")
    chat_parser.add_argument("--filter", choices=["all", "30days"], default="all", help="Date filter (all or 30days)")

    # Message scraper
    msg_parser = subparsers.add_parser("messages", help="Scrape chat messages")
    msg_parser.add_argument("--filter", choices=["all", "30days"], default="all", help="Date filter")
    msg_parser.add_argument("--limit", type=int, help="Limit number of chats to process")
    msg_parser.add_argument("--dry-run", action="store_true", help="Dry run mode (3 chats)")
    msg_parser.add_argument("--dry-run-limit", type=int, default=3, help="Number of chats in dry run")
    msg_parser.add_argument("--workers", type=int, default=1, help="Number of concurrent workers (1-3)")
    msg_parser.add_argument("--skip-existing", action="store_true", help="Skip chats that already have message files")

    # DSPy prompt optimizer
    opt_parser = subparsers.add_parser("optimize-prompt", help="Optimize prompt using DSPy")
    opt_parser.add_argument("--model", default="gpt-4o", help="OpenAI model to use (default: gpt-4o)")
    opt_parser.add_argument("--approach", choices=["few-shot", "instruction-only"], default="few-shot", help="Optimization approach")
    opt_parser.add_argument("--max-examples", type=int, default=8, help="Maximum examples in final prompt")
    opt_parser.add_argument("--optimizer", choices=["BootstrapFewShot", "SignatureOptimizer", "MIPRO"], default="BootstrapFewShot", help="DSPy optimizer")
    opt_parser.add_argument("--train-split", type=float, default=0.8, help="Training set ratio (0.1-0.9)")
    opt_parser.add_argument("--dry-run", action="store_true", help="Preview data only, don't optimize")
    # Filtering options
    opt_parser.add_argument("--min-response-length", type=int, default=50, help="Minimum response length (default: 50)")
    opt_parser.add_argument("--max-turn-number", type=int, default=20, help="Max turn number (default: 20)")
    opt_parser.add_argument("--sample-chats", type=int, help="Number of chats to sample (default: all)")

    args = parser.parse_args()

    if args.command == "chats":
        asyncio.run(scrape_chats(dry_run=args.dry_run, limit=args.limit, date_filter=args.filter))
    elif args.command == "messages":
        asyncio.run(scrape_messages(
            date_filter=args.filter,
            limit=args.limit,
            dry_run=args.dry_run,
            dry_run_limit=args.dry_run_limit,
            workers=args.workers,
            skip_existing=args.skip_existing
        ))
    elif args.command == "optimize-prompt":
        config = OptimizationConfig(
            model=args.model,
            approach=args.approach,
            max_examples=args.max_examples,
            optimizer=args.optimizer,
            train_split=args.train_split,
            dry_run=args.dry_run,
            min_response_length=args.min_response_length,
            max_turn_number=args.max_turn_number,
            sample_chats=args.sample_chats,
        )
        result = optimize_prompt(config)

        if result.status == "completed":
            print(f"\n✓ Optimization completed successfully!")
            print(f"Results saved to: {result.output_dir}")
            print(f"\nValidation score: {result.results.get('validation_score', 'N/A')}")
        else:
            print(f"\n✗ Optimization failed: {result.error}")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

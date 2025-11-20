"""Test script for chat list scraping."""

import asyncio
import sys
from loguru import logger
from src.scraper.auth import get_authenticated_browser, close_browser
from src.scraper.chat_list_scraper import scrape_chat_list


async def main():
    """Test the chat list scraper."""
    # Check for --dry-run flag
    dry_run = "--dry-run" in sys.argv
    dry_run_limit = 50  # Default limit

    # Check for custom limit
    if "--limit" in sys.argv:
        try:
            limit_index = sys.argv.index("--limit")
            dry_run_limit = int(sys.argv[limit_index + 1])
        except (IndexError, ValueError):
            logger.warning("Invalid --limit value, using default (50)")

    # Check for date filter
    date_filter = "all"  # Default
    if "--filter" in sys.argv:
        try:
            filter_index = sys.argv.index("--filter")
            date_filter = sys.argv[filter_index + 1]
            if date_filter not in ["all", "30days"]:
                logger.warning(f"Invalid --filter value '{date_filter}', using 'all'")
                date_filter = "all"
        except (IndexError, ValueError):
            logger.warning("Invalid --filter value, using 'all'")

    logger.info("=" * 60)
    if dry_run:
        logger.info(f"Testing Soomgo Chat List Scraper [DRY RUN - Limit: {dry_run_limit}]")
    else:
        logger.info(f"Testing Soomgo Chat List Scraper [FULL RUN - Filter: {date_filter}]")
    logger.info("=" * 60)

    browser = None
    context = None

    try:
        # Get authenticated browser
        logger.info("Authenticating...")
        browser, context = await get_authenticated_browser()
        logger.success("Authentication successful!")

        # Scrape chat list
        logger.info("\nStarting chat list scraping...")
        run_dir = await scrape_chat_list(context, dry_run=dry_run, dry_run_limit=dry_run_limit, date_filter=date_filter)

        logger.success("\n" + "=" * 60)
        logger.success("Chat list scraping completed!")
        logger.success(f"Results saved to: {run_dir}")
        logger.success("=" * 60)

        # Print summary
        import json
        summary_file = run_dir / "run_summary.json"
        with open(summary_file, 'r') as f:
            summary = json.load(f)

        # Load quality report
        quality_file = run_dir / "data_quality_report.json"
        quality_report = None
        if quality_file.exists():
            with open(quality_file, 'r') as f:
                quality_report = json.load(f)

        print("\n📊 Scraping Summary:")
        print(f"  • Total chats: {summary['total_items_processed']}")
        print(f"  • API calls: {summary['api_calls_intercepted']}")
        print(f"  • Scroll iterations: {summary['scroll_iterations']}")
        print(f"  • Duration: {summary['duration_seconds']:.1f}s")
        print(f"  • Duplicates filtered: {summary['total_duplicates_filtered']}")

        # Efficiency metrics
        if 'efficiency_metrics' in summary:
            em = summary['efficiency_metrics']
            print(f"\n⚡ Efficiency Metrics:")
            if em.get('chats_per_api_call'):
                print(f"  • Chats per API call: {em['chats_per_api_call']:.2f}")
            if em.get('chats_per_scroll'):
                print(f"  • Chats per scroll: {em['chats_per_scroll']:.2f}")
            if em.get('api_calls_per_minute'):
                print(f"  • API calls per minute: {em['api_calls_per_minute']:.2f}")
            if em.get('scrolls_per_minute'):
                print(f"  • Scrolls per minute: {em['scrolls_per_minute']:.2f}")

        # Humanization stats
        if 'humanization_stats' in summary:
            hs = summary['humanization_stats']
            print(f"\n🤖 Humanization Stats:")
            print(f"  • Reading pauses: {hs['reading_pauses']}")
            print(f"  • Scroll-ups: {hs['scroll_ups']}")
            print(f"  • Mouse movements: {hs['mouse_movements']}")
            print(f"  • Session breaks: {hs['session_breaks']}")
            print(f"  • Total wait time: {hs['total_wait_time_seconds']:.1f}s")

        # Safety metrics
        print(f"\n🛡️  Safety Metrics:")
        print(f"  • Viewport changes: {summary.get('viewport_changes', 0)}")
        print(f"  • Rate limit hits: {summary.get('rate_limit_hits', 0)}")
        print(f"  • Backoff events: {summary.get('backoff_events', 0)}")

        if summary.get('unique_services'):
            print(f"\n📋 Services found ({len(summary['unique_services'])}):")
            for service in summary['unique_services'][:10]:  # Show first 10
                print(f"  • {service}")
            if len(summary['unique_services']) > 10:
                print(f"  ... and {len(summary['unique_services']) - 10} more")

        print(f"\n📁 Output files:")
        for output_file in summary['output_files']:
            print(f"  • {output_file}")

        # Display data quality report
        if quality_report:
            print(f"\n🔍 Data Quality Report:")
            print(f"  • Overall Score: {quality_report['quality_score']}/100")
            print(f"  • Grade: {quality_report['quality_grade']}")
            print(f"  • Completeness: {quality_report['overall_completeness_percent']:.1f}%")
            print(f"  • Valid Records: {quality_report['valid_records_count']}/{quality_report['total_records']}")

            if quality_report['validation_issues']:
                print(f"  • Validation Issues: {len(quality_report['validation_issues'])}")
                error_issues = [i for i in quality_report['validation_issues'] if i['severity'] == 'error']
                if error_issues:
                    print(f"    - Errors: {len(error_issues)}")

            if quality_report['duplicate_ids']:
                print(f"  • Duplicate IDs: {len(quality_report['duplicate_ids'])}")

            if quality_report['anomalies']:
                print(f"  • Anomalies Detected: {len(quality_report['anomalies'])}")
                for anomaly in quality_report['anomalies'][:3]:  # Show first 3
                    print(f"    - {anomaly['details']}")

            if quality_report['statistics']:
                stats = quality_report['statistics']
                if 'hiring' in stats:
                    print(f"  • Hiring Rate: {stats['hiring']['hiring_rate_percent']:.1f}%")
                if 'price' in stats and stats['price']:
                    print(f"  • Price Range: ₩{stats['price']['min']:,} - ₩{stats['price']['max']:,}")
                    print(f"  • Average Price: ₩{int(stats['price']['mean']):,}")

            print(f"\n  📄 Full quality report: data_quality_report.json")

    except Exception as e:
        logger.error(f"Test failed: {e}")
        raise

    finally:
        # Clean up
        if browser and context:
            await close_browser(browser, context)


if __name__ == "__main__":
    asyncio.run(main())

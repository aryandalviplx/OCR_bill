#!/usr/bin/env python3
"""Script to run claim processing pipeline."""

import argparse
import logging
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from pipelines.claim_pipeline import ClaimPipeline
from config.settings import settings

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL, logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def main() -> None:
    """Main entry point for claim processing script."""
    parser = argparse.ArgumentParser(
        description="Process a claim through OCR Bill Itemization pipeline"
    )
    parser.add_argument(
        "claim_id",
        type=str,
        help="Claim ID to process",
    )
    parser.add_argument(
        "gcs_links",
        nargs="+",
        help="One or more GCS links (gs://bucket/path or https://storage.googleapis.com/bucket/path) to claim documents",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    try:
        pipeline = ClaimPipeline()
        result = pipeline.process_claim(args.claim_id, args.gcs_links)

        if result["status"] == "SUCCESS":
            logger.info("=" * 60)
            logger.info("CLAIM PROCESSING SUCCESSFUL")
            logger.info("=" * 60)
            logger.info(f"Claim ID: {result['claim_id']}")
            logger.info(f"Final Bill ID: {result.get('final_bill_id', 'N/A')}")
            logger.info("\nOutputs Generated:")
            for key in result.get("outputs", {}).keys():
                logger.info(f"  {key}")
            logger.info("=" * 60)
            sys.exit(0)
        else:
            logger.error("=" * 60)
            logger.error("CLAIM PROCESSING FAILED")
            logger.error("=" * 60)
            logger.error(f"Claim ID: {result['claim_id']}")
            logger.error(f"Error: {result.get('error', 'Unknown error')}")
            logger.error("=" * 60)
            sys.exit(1)

    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()


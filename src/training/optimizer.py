"""Main DSPy optimization logic."""

import hashlib
import json
import os
import random
from datetime import datetime
from pathlib import Path

import dspy
from loguru import logger

from .data_loader import load_all_hired_conversations
from .formatter import create_training_examples, get_example_stats
from .models import OptimizationConfig, OptimizationResult, TrainingExample
from .signature import SoomgoProviderResponse


def setup_dspy_lm(config: OptimizationConfig) -> None:
    """Configure DSPy language model."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError(
            "OPENAI_API_KEY not found in environment. "
            "Please add it to your .env file."
        )

    lm = dspy.LM(model=f"openai/{config.model}", api_key=api_key)
    dspy.configure(lm=lm)

    logger.info(f"Configured DSPy with model: {config.model}")


def simple_metric(example: dspy.Example, prediction, trace=None) -> float:
    """
    Simple quality metric for provider responses.

    Checks:
    - Response is not empty
    - Response length is reasonable (50-500 characters)
    - Response is in Korean (contains Hangul)

    Returns:
        Score between 0.0 and 1.0
    """
    response = prediction.provider_response.strip()

    if not response:
        return 0.0

    score = 0.0

    # Check length (50-500 chars is good)
    if 50 <= len(response) <= 500:
        score += 0.4
    elif 30 <= len(response) <= 700:
        score += 0.2

    # Check contains Korean
    if any("\uac00" <= c <= "\ud7a3" for c in response):
        score += 0.3

    # Check has question (engagement)
    if "?" in response or "?" in response:
        score += 0.15

    # Check reasonable punctuation
    if any(p in response for p in [".", "!", ",", "ㅎㅎ", "ㅋㅋ"]):
        score += 0.15

    return min(score, 1.0)


def split_train_val(
    examples: list[TrainingExample],
    train_ratio: float = 0.8,
    seed: int = 42,
) -> tuple[list[dspy.Example], list[dspy.Example]]:
    """
    Split examples into training and validation sets by chat_id.

    This ensures examples from the same conversation stay together.

    Args:
        examples: List of TrainingExample objects
        train_ratio: Fraction for training set
        seed: Random seed for reproducibility

    Returns:
        Tuple of (train_examples, val_examples) as dspy.Example objects
    """
    # Group by chat_id
    chat_groups = {}
    for ex in examples:
        if ex.chat_id not in chat_groups:
            chat_groups[ex.chat_id] = []
        chat_groups[ex.chat_id].append(ex)

    # Split chat IDs
    chat_ids = list(chat_groups.keys())
    random.seed(seed)
    random.shuffle(chat_ids)

    split_idx = int(len(chat_ids) * train_ratio)
    train_chat_ids = set(chat_ids[:split_idx])
    val_chat_ids = set(chat_ids[split_idx:])

    # Convert to dspy.Example format
    train_examples = []
    val_examples = []

    for chat_id, chat_examples in chat_groups.items():
        target = train_examples if chat_id in train_chat_ids else val_examples

        for ex in chat_examples:
            dspy_ex = dspy.Example(
                conversation_history=ex.conversation_history,
                provider_response=ex.provider_response,
            ).with_inputs("conversation_history")

            target.append(dspy_ex)

    logger.info(
        f"Split data: {len(train_examples)} train examples "
        f"({len(train_chat_ids)} chats), "
        f"{len(val_examples)} val examples "
        f"({len(val_chat_ids)} chats)"
    )

    return train_examples, val_examples


def create_run_directory() -> tuple[str, Path]:
    """Create a timestamped run directory."""
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    run_hash = hashlib.md5(timestamp.encode()).hexdigest()[:8]
    run_id = f"{timestamp}_prompt_optimize_{run_hash}"

    output_dir = Path("data/runs") / run_id
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"Created run directory: {output_dir}")
    return run_id, output_dir


def save_training_examples(
    examples: list[TrainingExample],
    output_dir: Path,
) -> None:
    """Save training examples to JSONL file."""
    output_file = output_dir / "training_examples.jsonl"

    with open(output_file, "w", encoding="utf-8") as f:
        for ex in examples:
            f.write(ex.model_dump_json() + "\n")

    logger.info(f"Saved {len(examples)} training examples to {output_file}")


def save_optimized_prompt(
    optimized_program: dspy.Module,
    output_dir: Path,
    config: OptimizationConfig,
) -> None:
    """Save the optimized prompt in multiple formats."""
    # Save as text
    prompt_txt = output_dir / "optimized_prompt.txt"
    with open(prompt_txt, "w", encoding="utf-8") as f:
        f.write("# Optimized Soomgo Provider Response Prompt\n\n")
        f.write(f"Model: {config.model}\n")
        f.write(f"Approach: {config.approach}\n")
        f.write(f"Optimizer: {config.optimizer}\n\n")
        f.write("=" * 80 + "\n\n")

        # Get the prompt from the program
        try:
            # Try to extract demos from DSPy compiled program
            demos = []

            # DSPy stores demos in the predictor attribute
            if hasattr(optimized_program, 'predictor') and hasattr(optimized_program.predictor, 'demos'):
                demos = optimized_program.predictor.demos
            elif hasattr(optimized_program, 'demos'):
                demos = optimized_program.demos

            if demos:
                f.write(f"Number of examples: {len(demos)}\n\n")

                for i, demo in enumerate(demos, 1):
                    f.write(f"Example {i}:\n")
                    f.write("-" * 40 + "\n")

                    # Demo can be a dspy.Example or dict
                    if hasattr(demo, 'conversation_history'):
                        history = demo.conversation_history
                        response = demo.provider_response
                    else:
                        history = demo.get('conversation_history', 'N/A')
                        response = demo.get('provider_response', 'N/A')

                    f.write(f"History:\n{history[:500]}...\n\n" if len(str(history)) > 500 else f"History:\n{history}\n\n")
                    f.write(f"Response:\n{response}\n\n")
            else:
                f.write("Instruction-only optimization (no examples found)\n\n")

            # Write the signature
            f.write("Signature Instructions:\n")
            f.write("-" * 40 + "\n")
            f.write(SoomgoProviderResponse.__doc__ or "")

        except Exception as e:
            logger.warning(f"Could not extract full prompt details: {e}")
            f.write("Program state:\n")
            f.write(str(optimized_program))

    logger.info(f"Saved optimized prompt to {prompt_txt}")

    # Save as JSON
    prompt_json = output_dir / "optimized_prompt.json"
    prompt_data = {
        "config": config.model_dump(),
        "signature": {
            "name": "SoomgoProviderResponse",
            "docstring": SoomgoProviderResponse.__doc__,
        },
        "demos": [],
    }

    try:
        demos = []
        if hasattr(optimized_program, 'predictor') and hasattr(optimized_program.predictor, 'demos'):
            demos = optimized_program.predictor.demos
        elif hasattr(optimized_program, 'demos'):
            demos = optimized_program.demos

        if demos:
            prompt_data["demos"] = [
                {
                    "conversation_history": demo.conversation_history if hasattr(demo, 'conversation_history') else demo.get("conversation_history", ""),
                    "provider_response": demo.provider_response if hasattr(demo, 'provider_response') else demo.get("provider_response", ""),
                }
                for demo in demos
            ]
    except Exception as e:
        logger.warning(f"Could not extract demos for JSON: {e}")

    with open(prompt_json, "w", encoding="utf-8") as f:
        json.dump(prompt_data, f, ensure_ascii=False, indent=2)

    logger.info(f"Saved prompt JSON to {prompt_json}")


def optimize_prompt(config: OptimizationConfig) -> OptimizationResult:
    """
    Run DSPy prompt optimization.

    Args:
        config: Optimization configuration

    Returns:
        OptimizationResult with metrics and output paths
    """
    started_at = datetime.now()
    run_id, output_dir = create_run_directory()

    result = OptimizationResult(
        run_id=run_id,
        started_at=started_at,
        config=config,
        output_dir=output_dir,
    )

    try:
        # Setup logging
        log_file = output_dir / "run.log"
        logger.add(log_file)

        logger.info("=" * 80)
        logger.info(f"Starting DSPy prompt optimization: {run_id}")
        logger.info("=" * 80)
        logger.info(f"Config: {config.model_dump_json(indent=2)}")

        # Load data
        logger.info("Loading hired conversations...")
        conversations = load_all_hired_conversations()

        if not conversations:
            raise ValueError("No hired conversations found!")

        logger.info(f"Loaded {len(conversations)} conversations")

        # Sample conversations if requested
        if config.sample_chats and config.sample_chats < len(conversations):
            logger.info(f"Sampling {config.sample_chats} chats from {len(conversations)}...")
            random.seed(42)
            conversations = random.sample(conversations, config.sample_chats)
            logger.info(f"Using {len(conversations)} sampled conversations")

        # Create training examples with filters
        logger.info("Creating training examples...")
        logger.info(
            f"Filters: min_response_length={config.min_response_length}, "
            f"max_turn_number={config.max_turn_number}"
        )
        all_examples = create_training_examples(
            conversations,
            min_response_length=config.min_response_length,
            max_turn_number=config.max_turn_number,
        )

        if not all_examples:
            raise ValueError("No training examples created!")

        example_stats = get_example_stats(all_examples)
        logger.info(f"Example stats: {json.dumps(example_stats, indent=2)}")

        result.data_stats = {
            "total_hired_chats": len(conversations),
            "total_training_examples": len(all_examples),
            **example_stats,
        }

        # Save training examples
        save_training_examples(all_examples, output_dir)

        if config.dry_run:
            logger.info("Dry run mode - skipping optimization")
            result.status = "completed"
            result.completed_at = datetime.now()
            result.results = {"dry_run": True}
            return result

        # Configure DSPy (only needed for actual optimization)
        setup_dspy_lm(config)

        # Split train/val
        train_examples, val_examples = split_train_val(
            all_examples,
            train_ratio=config.train_split,
        )

        result.data_stats["training_split"] = len(train_examples)
        result.data_stats["validation_split"] = len(val_examples)

        # Run optimization
        logger.info(f"Running {config.optimizer} optimization...")

        if config.optimizer == "BootstrapFewShot":
            optimizer = dspy.BootstrapFewShot(
                metric=simple_metric,
                max_bootstrapped_demos=config.max_examples,
                max_labeled_demos=config.max_examples,
            )
        else:
            raise ValueError(f"Optimizer {config.optimizer} not yet implemented")

        # Create base program
        program = dspy.ChainOfThought(SoomgoProviderResponse)

        # Compile
        logger.info("Compiling optimized program...")
        optimized_program = optimizer.compile(
            program,
            trainset=train_examples,
        )

        # Evaluate on validation set
        logger.info("Evaluating on validation set...")
        val_scores = []
        for ex in val_examples[:10]:  # Sample 10 for speed
            try:
                pred = optimized_program(conversation_history=ex.conversation_history)
                score = simple_metric(ex, pred)
                val_scores.append(score)
            except Exception as e:
                logger.warning(f"Evaluation error: {e}")

        avg_val_score = sum(val_scores) / len(val_scores) if val_scores else 0.0

        logger.info(f"Validation score: {avg_val_score:.3f}")

        # Save results
        result.results = {
            "validation_score": avg_val_score,
            "validation_samples": len(val_scores),
            "examples_selected": config.max_examples,
        }

        # Save optimized prompt
        save_optimized_prompt(optimized_program, output_dir, config)

        # Save validation results
        val_results_file = output_dir / "validation_results.json"
        with open(val_results_file, "w", encoding="utf-8") as f:
            json.dump(
                {"scores": val_scores, "average": avg_val_score},
                f,
                indent=2,
            )

        result.status = "completed"
        result.completed_at = datetime.now()

        logger.info("=" * 80)
        logger.info("Optimization completed successfully!")
        logger.info(f"Results saved to: {output_dir}")
        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"Optimization failed: {e}", exc_info=True)
        result.status = "failed"
        result.error = str(e)
        result.completed_at = datetime.now()

    finally:
        # Save run summary
        summary_file = output_dir / "run_summary.json"
        with open(summary_file, "w", encoding="utf-8") as f:
            json.dump(result.model_dump(mode="json"), f, indent=2, default=str)

        # Save optimization report
        report_file = output_dir / "optimization_report.json"
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "run_id": result.run_id,
                    "status": result.status,
                    "data_stats": result.data_stats,
                    "results": result.results,
                    "error": result.error,
                },
                f,
                indent=2,
            )

    return result

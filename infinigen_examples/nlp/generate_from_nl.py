# Copyright (C) 2024, Princeton University.
# This source code is licensed under the BSD 3-Clause license found in the LICENSE file in the root directory
# of this source tree.

"""Main interface module for generating scenes from natural language."""

import hashlib
import logging
from pathlib import Path
from typing import Optional

from infinigen_examples.nlp import (
    generate_config,
    parse_natural_language,
    post_process,
    validate_constraints,
)

logger = logging.getLogger(__name__)


def generate_scene_from_nl(
    natural_language: str,
    output_folder: Path,
    scene_seed: Optional[int] = None,
    use_openai: bool = False,
    api_key: Optional[str] = None,
    use_local_llm: bool = True,
    ollama_model: str = "gemma3",
    ollama_base_url: str = "http://localhost:11434",
    base_config: str = "infinigen_examples/configs_indoor/base_indoors.gin",
    **kwargs,
) -> Path:
    """Generate indoor scene from natural language description.

    This function:
    1. Parses natural language input using LLM
    2. Validates and post-processes parsed constraints
    3. Generates gin config file
    4. Returns path to generated config file

    Args:
        natural_language: Natural language description of desired scene
        output_folder: Output folder for generated files
        scene_seed: Random seed for scene generation (optional)
        use_openai: Whether to use OpenAI API (default: False)
        api_key: OpenAI API key (if None, uses OPENAI_API_KEY env var)
        use_local_llm: Whether to use local LLM (default: True)
        ollama_model: Ollama model name (default: "gemma3")
        ollama_base_url: Ollama server base URL (default: "http://localhost:11434")
        base_config: Base gin config file to include
        **kwargs: Additional arguments passed to scene generation

    Returns:
        Path to generated gin config file

    Raises:
        ValueError: If parsing or validation fails
    """
    logger.info(f"Parsing natural language input: {natural_language}")

    # Step 1: Parse natural language
    try:
        parsed_data = parse_natural_language.parse_natural_language(
            natural_language,
            use_openai=use_openai,
            api_key=api_key,
            use_local_llm=use_local_llm,
            ollama_model=ollama_model,
            ollama_base_url=ollama_base_url,
        )
        logger.info(f"LLM parsed data: {parsed_data}")
    except Exception as e:
        logger.error(f"Failed to parse natural language: {e}")
        logger.info("Using default parsed data")
        parsed_data = parse_natural_language.get_default_parsed_data()

    # Step 2: Post-process parsed data (pass original text for fallback extraction)
    parsed_data = post_process.post_process_parsed_data(
        parsed_data, input_text=natural_language
    )
    logger.info(f"Post-processed data: {parsed_data}")

    # Step 3: Validate constraints
    is_valid, warnings = validate_constraints.validate_constraints(parsed_data)

    if warnings:
        for warning in warnings:
            logger.warning(warning)

    if not is_valid:
        logger.warning(
            "Some constraints are invalid, but continuing with corrected values"
        )

    # Step 4: Generate gin config
    config_content = generate_config.generate_gin_config(
        parsed_data,
        base_config=base_config,
    )

    # Step 5: Save config file
    # Save to configs_indoor folder so generate_indoors.py can find it
    from infinigen import repo_root

    configs_indoor_dir = repo_root() / "infinigen_examples" / "configs_indoor"
    configs_indoor_dir.mkdir(parents=True, exist_ok=True)

    # Generate unique filename based on input hash
    input_hash = hashlib.md5(natural_language.encode()).hexdigest()[:8]
    config_filename = f"nl_generated_{input_hash}.gin"
    config_path = configs_indoor_dir / config_filename

    generate_config.save_gin_config(config_content, config_path)

    logger.info(f"Generated gin config: {config_path}")
    logger.info(f"Config content:\n{config_content}")

    return config_path

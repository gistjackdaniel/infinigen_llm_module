# Copyright (C) 2024, Princeton University.
# This source code is licensed under the BSD 3-Clause license found in the LICENSE file in the root directory
# of this source tree.

"""Natural language parsing module using LLM."""

import json
import logging
import os
from typing import Any, Dict, Optional

from infinigen_examples.nlp import prompts

logger = logging.getLogger(__name__)


def parse_with_openai(input_text: str, api_key: Optional[str] = None) -> Dict[str, Any]:
    """Parse natural language using OpenAI API.

    Args:
        input_text: Natural language input text
        api_key: OpenAI API key (if None, uses OPENAI_API_KEY env var)

    Returns:
        Parsed structured data as dictionary
    """
    try:
        import openai
    except ImportError:
        raise ImportError(
            "openai package is required. Install with: pip install openai"
        )

    if api_key is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key is None:
            raise ValueError(
                "OpenAI API key not provided. Set OPENAI_API_KEY environment variable or pass api_key parameter."
            )

    client = openai.OpenAI(api_key=api_key)

    prompt = prompts.get_prompt(input_text)
    examples = prompts.get_examples()

    # Build messages with examples
    messages = [
        {
            "role": "system",
            "content": "You are a natural language parser for indoor scene generation. Extract structured information and return valid JSON only.",
        }
    ]

    # Add examples for few-shot learning
    for example in examples:
        messages.append({"role": "user", "content": example["input"]})
        messages.append(
            {
                "role": "assistant",
                "content": json.dumps(example["output"], ensure_ascii=False),
            }
        )

    # Add actual input
    messages.append({"role": "user", "content": prompt})

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # Use cost-effective model
            messages=messages,
            temperature=0.1,  # Low temperature for consistent parsing
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content
        parsed = json.loads(content)
        logger.info("Successfully parsed natural language input")
        logger.debug(f"Parsed JSON: {parsed}")
        return parsed

    except Exception as e:
        logger.error(f"Error parsing with OpenAI: {e}")
        raise


def parse_with_local_llm(
    input_text: str,
    model_name: str = "gemma3",
    base_url: str = "http://localhost:11434",
    temperature: float = 0.1,
    timeout: int = 60,
) -> Dict[str, Any]:
    """Parse natural language using local LLM via Ollama.

    Args:
        input_text: Natural language input text
        model_name: Ollama model name (default: "gemma3")
        base_url: Ollama server base URL (default: "http://localhost:11434")
        temperature: Sampling temperature (default: 0.1 for consistent parsing)
        timeout: Request timeout in seconds (default: 60)

    Returns:
        Parsed structured data as dictionary

    Raises:
        ImportError: If ollama package is not installed
        ConnectionError: If Ollama server is not reachable
        ValueError: If parsing fails
    """
    try:
        import ollama
    except ImportError:
        raise ImportError(
            "ollama package is required. Install with: pip install ollama"
        )

    # Check if Ollama server is reachable
    try:
        import requests

        response = requests.get(f"{base_url}/api/tags", timeout=5)
        response.raise_for_status()
    except (requests.exceptions.RequestException, ImportError) as e:
        logger.error(f"Failed to connect to Ollama server at {base_url}: {e}")
        raise ConnectionError(
            f"Ollama server is not reachable at {base_url}. "
            "Make sure Ollama is running. You can start it with: ollama serve"
        ) from e

    # Create Ollama client with base_url
    try:
        # Try new API: Client object
        from ollama import Client

        client = Client(host=base_url)
        use_client_api = True
    except (ImportError, AttributeError, TypeError) as e:
        # Fallback to old API if Client doesn't exist or doesn't support host parameter
        logger.warning(f"Using legacy ollama API: {e}")
        use_client_api = False
        client = None

    # Check if model exists
    try:
        if use_client_api:
            models_response = client.list()
            if isinstance(models_response, dict):
                model_list = models_response.get("models", [])
            else:
                model_list = (
                    models_response.models if hasattr(models_response, "models") else []
                )
            model_names = [
                model["name"] if isinstance(model, dict) else model.name
                for model in model_list
            ]
        else:
            models = ollama.list()
            if isinstance(models, dict):
                model_list = models.get("models", [])
            else:
                model_list = models.models if hasattr(models, "models") else []
            model_names = [
                model["name"] if isinstance(model, dict) else model.name
                for model in model_list
            ]

        if model_name not in model_names:
            logger.warning(
                f"Model '{model_name}' not found in local Ollama models. "
                f"Available models: {', '.join(model_names) if model_names else 'none'}. "
                f"Install with: ollama pull {model_name}"
            )
            # Try to continue anyway - Ollama might auto-download
    except Exception as e:
        logger.warning(f"Could not verify model existence: {e}. Continuing anyway...")

    prompt = prompts.get_prompt(input_text)
    examples = prompts.get_examples()

    # Build system message with examples for few-shot learning
    system_content = "You are a natural language parser for indoor scene generation. Extract structured information and return valid JSON only.\n\n"

    # Add examples
    for example in examples:
        system_content += f"Example input: {example['input']}\n"
        system_content += (
            f"Example output: {json.dumps(example['output'], ensure_ascii=False)}\n\n"
        )

    # Build the full prompt with JSON format requirement
    full_prompt = f"{system_content}{prompt}\n\nReturn only valid JSON, no other text."

    try:
        # Use Ollama chat API
        if use_client_api:
            # New API: Use Client object
            response = client.chat(
                model=model_name,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a natural language parser for indoor scene generation. Extract structured information and return valid JSON only.",
                    },
                    {
                        "role": "user",
                        "content": full_prompt,
                    },
                ],
                options={
                    "temperature": temperature,
                },
            )
        else:
            # Old API: Direct function call (may not support base_url)
            response = ollama.chat(
                model=model_name,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a natural language parser for indoor scene generation. Extract structured information and return valid JSON only.",
                    },
                    {
                        "role": "user",
                        "content": full_prompt,
                    },
                ],
                options={
                    "temperature": temperature,
                },
            )

        # Extract content from response
        # Handle both dict and object response formats
        if isinstance(response, dict):
            content = response["message"]["content"]
        else:
            content = (
                response.message.content
                if hasattr(response.message, "content")
                else str(response.message)
            )

        # Try to extract JSON from response (may contain markdown code blocks)
        import re

        json_match = re.search(r"\{.*\}", content, re.DOTALL)
        if json_match:
            content = json_match.group(0)
        else:
            logger.warning("No JSON found in response, trying to parse entire content")

        # Parse JSON
        parsed = json.loads(content)
        logger.info(
            f"Successfully parsed natural language input using local LLM ({model_name})"
        )
        logger.debug(f"Parsed JSON: {parsed}")
        return parsed

    except ConnectionError as e:
        logger.error(f"Failed to connect to Ollama server at {base_url}: {e}")
        raise ConnectionError(
            f"Ollama server is not reachable at {base_url}. "
            "Make sure Ollama is running: ollama serve"
        ) from e
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON from Ollama response: {e}")
        logger.error(
            f"Response content: {content[:500] if 'content' in locals() else 'N/A'}"
        )
        raise ValueError(
            f"Failed to parse JSON response from Ollama. "
            f"Response may not be valid JSON. Error: {e}"
        ) from e
    except Exception as e:
        logger.error(f"Error parsing with local LLM: {e}")
        # Check if it's a model not found error
        error_str = str(e).lower()
        if "model" in error_str and (
            "not found" in error_str or "does not exist" in error_str
        ):
            raise ValueError(
                f"Model '{model_name}' not found. Install it with: ollama pull {model_name}"
            ) from e
        raise


def parse_natural_language(
    input_text: str,
    use_openai: bool = False,
    api_key: Optional[str] = None,
    use_local_llm: bool = True,
    ollama_model: str = "gemma3",
    ollama_base_url: str = "http://localhost:11434",
) -> Dict[str, Any]:
    """Parse natural language input to structured constraints.

    This function extracts only information that can be controlled via gin config.

    Args:
        input_text: Natural language description of desired scene
        use_openai: Whether to use OpenAI API (default: False)
        api_key: OpenAI API key (if None, uses OPENAI_API_KEY env var)
        use_local_llm: Whether to use local LLM (default: True)
        ollama_model: Ollama model name (default: "gemma3")
        ollama_base_url: Ollama server base URL (default: "http://localhost:11434")

    Returns:
        Dictionary with parsed constraints:
        {
            "restrict_parent_rooms": [...],
            "restrict_child_primary": [...],
            "solve_max_rooms": int,
            "solve_large_enabled": bool,
            ...
        }
    """
    if use_local_llm:
        return parse_with_local_llm(
            input_text,
            model_name=ollama_model,
            base_url=ollama_base_url,
        )
    elif use_openai:
        return parse_with_openai(input_text, api_key)
    else:
        raise ValueError("Either use_openai or use_local_llm must be True")


def get_default_parsed_data() -> Dict[str, Any]:
    """Get default parsed data structure with all fields set to None/defaults.

    Returns:
        Dictionary with default values
    """
    return {
        "restrict_parent_rooms": None,
        "restrict_parent_objs": None,
        "restrict_child_primary": None,
        "restrict_child_secondary": None,
        "solve_max_rooms": 1,
        "solve_max_parent_obj": None,
        "consgraph_filters": None,
        "solve_steps": None,
        "solve_large_enabled": True,
        "solve_medium_enabled": True,
        "solve_small_enabled": True,
        "terrain_enabled": False,
        "topview": False,
        "animate_cameras_enabled": False,
        "floating_objs_enabled": False,
        "restrict_single_supported_roomtype": False,
    }

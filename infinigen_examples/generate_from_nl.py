# Copyright (C) 2024, Princeton University.
# This source code is licensed under the BSD 3-Clause license found in the LICENSE file in the root directory
# of this source tree.

"""CLI interface for generating indoor scenes from natural language."""

import argparse
import logging
import os
import subprocess
import sys
from pathlib import Path

# ruff: noqa: E402
# NOTE: logging config has to be before imports that use logging
logging.basicConfig(
    format="[%(asctime)s.%(msecs)03d] [%(module)s] [%(levelname)s] | %(message)s",
    datefmt="%H:%M:%S",
    level=logging.INFO,
)

from infinigen import repo_root

# Import only the functions we need, not the whole module to avoid bpy import
from infinigen.core.init import apply_scene_seed, parse_args_blender
from infinigen_examples.nlp.generate_from_nl import generate_scene_from_nl

logger = logging.getLogger(__name__)


def main(args):
    """Main function for CLI interface."""
    # apply_scene_seed expects string or None; convert int seed to hex string
    seed_arg = hex(args.seed)[2:] if args.seed is not None else None
    scene_seed = apply_scene_seed(seed_arg)

    # Generate gin config from natural language
    logger.info(f"Generating config from natural language: {args.nl}")

    try:
        config_path = generate_scene_from_nl(
            natural_language=args.nl,
            output_folder=args.output_folder,
            scene_seed=scene_seed,
            use_openai=args.use_openai,
            api_key=args.api_key,
            use_local_llm=args.use_local_llm,
            ollama_model=args.ollama_model,
            ollama_base_url=args.ollama_base_url,
            base_config=args.base_config,
        )

        logger.info(f"Generated config file: {config_path}")

        # If --generate-scene is set, also generate the scene
        if args.generate_scene:
            logger.info("Generating scene using generated config...")

            # Extract config filename without extension
            config_name = config_path.stem

            # Build command to call generate_indoors.py
            cmd = [
                sys.executable,
                "-m",
                "infinigen_examples.generate_indoors",
                "--output_folder",
                str(args.output_folder),
                "--seed",
                str(scene_seed) if scene_seed else "0",
                "--task",
                *args.task,
                "--configs",
                "base_indoors",  # Include base config
                config_name,  # Our generated config
            ]

            # Add overrides if provided
            if args.overrides:
                cmd.extend(["--overrides", *args.overrides])

            env = os.environ.copy()
            # Ensure correct libstdc++ is used for bpy compatibility
            conda_prefix = os.environ.get("CONDA_PREFIX", "")
            if conda_prefix:
                libstdcpp = os.path.join(conda_prefix, "lib", "libstdc++.so.6")
                if os.path.exists(libstdcpp):
                    env["LD_PRELOAD"] = libstdcpp
            logger.info(f"Running command: {' '.join(cmd)}")
            result = subprocess.run(cmd, cwd=repo_root(), env=env, check=False)

            if result.returncode != 0:
                logger.error(
                    f"Scene generation failed with return code {result.returncode}"
                )
                sys.exit(result.returncode)
            else:
                logger.info("Scene generation completed successfully")
        else:
            logger.info(
                "Config file generated. Use --generate-scene to generate the scene."
            )
            logger.info(
                f"Or manually run: python -m infinigen_examples.generate_indoors --configs base_indoors {config_path.stem} --output_folder {args.output_folder}"
            )

    except Exception as e:
        logger.error(
            f"Error generating scene from natural language: {e}", exc_info=True
        )
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate indoor scenes from natural language descriptions"
    )
    parser.add_argument(
        "--nl",
        type=str,
        required=True,
        help="Natural language description of the desired scene (Korean or English)",
    )
    parser.add_argument(
        "--output_folder",
        type=Path,
        required=True,
        help="Output folder for generated files",
    )
    parser.add_argument(
        "-s",
        "--seed",
        type=int,
        default=None,
        help="Random seed for scene generation",
    )
    parser.add_argument(
        "--generate-scene",
        action="store_true",
        help="Also generate the scene after creating config (default: False, only creates config)",
    )
    parser.add_argument(
        "--use-openai",
        action="store_true",
        default=False,
        help="Use OpenAI API for parsing (default: False, uses local LLM by default)",
    )
    parser.add_argument(
        "--use-local-llm",
        action="store_true",
        default=True,
        help="Use local LLM via Ollama (default: True)",
    )
    parser.add_argument(
        "--ollama-model",
        type=str,
        default="gemma3",
        help="Ollama model name (default: gemma3)",
    )
    parser.add_argument(
        "--ollama-base-url",
        type=str,
        default="http://localhost:11434",
        help="Ollama server base URL (default: http://localhost:11434)",
    )
    parser.add_argument(
        "--api-key",
        type=str,
        default=None,
        help="OpenAI API key (if not provided, uses OPENAI_API_KEY env var)",
    )
    parser.add_argument(
        "--base-config",
        type=str,
        default="infinigen_examples/configs_indoor/base_indoors.gin",
        help="Base gin config file to include (default: base_indoors.gin)",
    )
    parser.add_argument(
        "-t",
        "--task",
        nargs="+",
        default=["coarse"],
        choices=[
            "coarse",
            "populate",
            "fine_terrain",
            "ground_truth",
            "render",
            "mesh_save",
            "export",
        ],
        help="Tasks to run (default: coarse)",
    )
    parser.add_argument(
        "-p",
        "--overrides",
        nargs="+",
        default=[],
        help="Additional gin parameter overrides",
    )
    parser.add_argument(
        "-d",
        "--debug",
        type=str,
        nargs="*",
        default=None,
        help="Debug logging for specific modules",
    )

    args = parse_args_blender(parser)

    logging.getLogger("infinigen").setLevel(logging.INFO)
    logging.getLogger("infinigen.core.nodes.node_wrangler").setLevel(logging.CRITICAL)

    if args.debug is not None:
        for name in logging.root.manager.loggerDict:
            if not name.startswith("infinigen"):
                continue
            if len(args.debug) == 0 or any(name.endswith(x) for x in args.debug):
                logging.getLogger(name).setLevel(logging.DEBUG)

    main(args)

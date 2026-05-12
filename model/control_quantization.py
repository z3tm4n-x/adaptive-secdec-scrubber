#!/usr/bin/env python3

from __future__ import annotations

import argparse
import bisect
import csv
import math
from dataclasses import dataclass
from pathlib import Path


SUPPORTED_QUANTIZATION_MODES = (
    "linear_max",
    "percentile_tail",
)

DEFAULT_PERCENTILE_BOUNDARIES = (
    0.50,
    0.70,
    0.85,
    0.93,
    0.97,
    0.99,
    0.997,
)


@dataclass(frozen=True)
class QuantizationConfig:
    mode: str
    boundaries: tuple[float, ...]
    percentile_boundaries: tuple[float, ...] = ()


def percentile_linear(sorted_values: list[float], percentile: float) -> float:
    if not sorted_values:
        raise ValueError("Cannot compute percentile of empty list")

    if percentile < 0.0 or percentile > 1.0:
        raise ValueError("percentile must be in [0, 1]")

    if len(sorted_values) == 1:
        return sorted_values[0]

    position = (len(sorted_values) - 1) * percentile
    lower_index = int(math.floor(position))
    upper_index = int(math.ceil(position))

    if lower_index == upper_index:
        return sorted_values[lower_index]

    lower_value = sorted_values[lower_index]
    upper_value = sorted_values[upper_index]
    alpha = position - lower_index

    return lower_value * (1.0 - alpha) + upper_value * alpha


def linear_max_boundaries(values: list[float]) -> tuple[float, ...]:
    max_value = max(values) if values else 0.0

    if max_value <= 0.0:
        return tuple(0.0 for _ in range(7))

    return tuple(((level + 0.5) / 7.0) * max_value for level in range(7))


def percentile_tail_boundaries(
    values: list[float],
    percentile_boundaries: tuple[float, ...] = DEFAULT_PERCENTILE_BOUNDARIES,
) -> tuple[float, ...]:
    if not values:
        raise ValueError("Cannot build percentile boundaries for empty series")

    if len(percentile_boundaries) != 7:
        raise ValueError("Exactly 7 percentile boundaries are required")

    previous = -1.0

    for percentile in percentile_boundaries:
        if percentile <= previous:
            raise ValueError("Percentile boundaries must be strictly increasing")

        if percentile <= 0.0 or percentile >= 1.0:
            raise ValueError("Percentile boundaries must be inside (0, 1)")

        previous = percentile

    sorted_values = sorted(values)

    return tuple(
        percentile_linear(sorted_values, percentile)
        for percentile in percentile_boundaries
    )


def build_quantization_config(
    values: list[float],
    mode: str,
    percentile_boundaries: tuple[float, ...] = DEFAULT_PERCENTILE_BOUNDARIES,
) -> QuantizationConfig:
    if mode not in SUPPORTED_QUANTIZATION_MODES:
        raise ValueError(
            f"Unsupported quantization mode: {mode}. "
            f"Supported: {', '.join(SUPPORTED_QUANTIZATION_MODES)}"
        )

    if mode == "linear_max":
        return QuantizationConfig(
            mode=mode,
            boundaries=linear_max_boundaries(values),
            percentile_boundaries=(),
        )

    if mode == "percentile_tail":
        return QuantizationConfig(
            mode=mode,
            boundaries=percentile_tail_boundaries(
                values=values,
                percentile_boundaries=percentile_boundaries,
            ),
            percentile_boundaries=percentile_boundaries,
        )

    raise AssertionError(f"Unhandled quantization mode: {mode}")


def quantize_value(value: float, config: QuantizationConfig) -> int:
    if config.mode == "linear_max":
        max_boundary = config.boundaries[-1] if config.boundaries else 0.0
        max_value = (7.0 / 6.5) * max_boundary if max_boundary > 0.0 else 0.0

        if max_value <= 0.0:
            return 0

        normalized = value / max_value

        if normalized < 0.0:
            normalized = 0.0

        if normalized > 1.0:
            normalized = 1.0

        level = int(round(7.0 * normalized))

        if level < 0:
            return 0

        if level > 7:
            return 7

        return level

    if config.mode == "percentile_tail":
        level = bisect.bisect_right(config.boundaries, value)

        if level < 0:
            return 0

        if level > 7:
            return 7

        return level

    raise ValueError(f"Unsupported quantization mode: {config.mode}")


def quantize_values(
    values: list[float],
    mode: str,
    percentile_boundaries: tuple[float, ...] = DEFAULT_PERCENTILE_BOUNDARIES,
) -> tuple[list[int], QuantizationConfig]:
    config = build_quantization_config(
        values=values,
        mode=mode,
        percentile_boundaries=percentile_boundaries,
    )

    return [quantize_value(value, config) for value in values], config


def level_counts(levels: list[int]) -> list[int]:
    counts = [0 for _ in range(8)]

    for level in levels:
        if level < 0 or level > 7:
            raise ValueError(f"Control level out of range: {level}")

        counts[level] += 1

    return counts


def count_level_changes(levels: list[int]) -> int:
    changes = 0
    previous_level: int | None = None

    for level in levels:
        if previous_level is None or level != previous_level:
            changes += 1
            previous_level = level

    return changes


def parse_percentile_boundaries(text: str) -> tuple[float, ...]:
    values: list[float] = []

    for raw_part in text.replace(";", ",").split(","):
        part = raw_part.strip()

        if not part:
            continue

        value = float(part)

        if value > 1.0:
            value = value / 100.0

        values.append(value)

    if len(values) != 7:
        raise ValueError("Exactly 7 percentile boundaries are required")

    return tuple(values)


def format_percentile_boundaries(values: tuple[float, ...]) -> str:
    if not values:
        return ""

    return ",".join(f"{value:.6g}" for value in values)


def write_thresholds_csv(
    output_path: Path,
    config: QuantizationConfig,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(
            [
                "mode",
                "boundary",
                "lower_level",
                "upper_level",
                "percentile",
                "upsets_value",
            ]
        )

        for lower_level, boundary_value in enumerate(config.boundaries):
            percentile_text = ""

            if config.percentile_boundaries:
                percentile_text = f"{config.percentile_boundaries[lower_level]:.9f}"

            writer.writerow(
                [
                    config.mode,
                    f"level_{lower_level}_to_{lower_level + 1}",
                    lower_level,
                    lower_level + 1,
                    percentile_text,
                    f"{boundary_value:.12g}",
                ]
            )


def add_quantization_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--control-quantization",
        choices=SUPPORTED_QUANTIZATION_MODES,
        default="linear_max",
        help=(
            "Control-level quantization mode. "
            "linear_max preserves the legacy max-normalized rule; "
            "percentile_tail uses fixed percentile thresholds."
        ),
    )

    parser.add_argument(
        "--control-percentiles",
        default=format_percentile_boundaries(DEFAULT_PERCENTILE_BOUNDARIES),
        help=(
            "Comma-separated percentile boundaries for percentile_tail. "
            "Values can be fractions or percentages. Default: "
            + format_percentile_boundaries(DEFAULT_PERCENTILE_BOUNDARIES)
        ),
    )
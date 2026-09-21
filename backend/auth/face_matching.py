"""
face_matching.py - Biometric facial recognition utilities and vector matching algorithms.

This module provides Euclidean distance calculation and nearest-neighbor
face matching for 128-dimensional facial embedding vectors extracted
by face-api.js.
"""

import os
import math
from typing import List, Tuple, Optional

# Calibrated Euclidean distance matching threshold for face-api.js (defaults to 0.58)
DEFAULT_FACE_MATCH_THRESHOLD: float = float(os.getenv("FACE_MATCH_THRESHOLD", "0.58"))


def calculate_euclidean_distance(vector_a: List[float], vector_b: List[float]) -> float:
    """
    Calculates the Euclidean (L2) distance between two 128-dimensional face vectors.
    """
    if len(vector_a) != len(vector_b):
        raise ValueError(
            f"Vector dimensions do not match: expected {len(vector_a)} elements, got {len(vector_b)}"
        )

    squared_diff_sum = sum((a - b) ** 2 for a, b in zip(vector_a, vector_b))
    return math.sqrt(squared_diff_sum)


def find_best_face_match(
    incoming_descriptor: List[float],
    candidate_users: List[Tuple[str, List[float]]],
    threshold: float = DEFAULT_FACE_MATCH_THRESHOLD,
) -> Optional[Tuple[str, float]]:
    """
    Compares an incoming face descriptor against all registered users' stored descriptors
    to identify the closest matching identity.

    Parameters:
    - incoming_descriptor: The 128-float array captured from the user's camera.
    - candidate_users: List of tuples containing (user_identifier, stored_128_float_descriptor).
    - threshold: Maximum Euclidean distance allowed for a match (default: 0.5).

    Returns:
    - Tuple of (matched_user_identifier, match_distance) if a valid match within threshold is found.
    - None if candidate list is empty or the closest match exceeds the threshold.
    """
    if not candidate_users:
        return None

    best_user_id: Optional[str] = None
    min_distance: float = float("inf")

    for user_id, stored_descriptor in candidate_users:
        try:
            distance = calculate_euclidean_distance(incoming_descriptor, stored_descriptor)
            if distance < min_distance:
                min_distance = distance
                best_user_id = user_id
        except ValueError:
            continue

    if best_user_id is not None and min_distance < threshold:
        return best_user_id, min_distance

    return None

"""
face_utils.py - Biometric facial recognition utilities and vector matching algorithms.

This module provides Euclidean distance calculation and nearest-neighbor
face matching for 128-dimensional facial embedding vectors extracted
by face-api.js.
"""

import math
from typing import List, Tuple, Optional


# ==============================================================================
# MATCHING THRESHOLD CONFIGURATION
# ==============================================================================
# Threshold for Euclidean distance matching.
# Lower values mean stricter matching (fewer false positives, but more rejections).
# Higher values mean looser matching (easier recognition, but higher risk of false acceptance).
#
# NOTE: 0.5 is a reasonable starting threshold and may need tuning based on
# real-world testing (e.g. lighting conditions, camera angles, webcams).
# In face-api.js benchmarks, 0.6 is a standard threshold; using 0.5 provides
# higher security for an authentication system.
DEFAULT_FACE_MATCH_THRESHOLD: float = 0.5


def calculate_euclidean_distance(vector_a: List[float], vector_b: List[float]) -> float:
    """
    Calculates the Euclidean (L2) distance between two 128-dimensional face vectors.

    NON-TECHNICAL EXPLANATION:
    --------------------------
    When your camera captures your face, face-api.js measures 128 distinct facial
    characteristics (such as eye spacing, jawline curve, nose width).
    These 128 numbers form a unique 'face descriptor' vector.

    This function calculates the direct, straight-line distance between two sets
    of measurements in 128-dimensional space:
    - If the two faces are identical, the distance is 0.0.
    - If the two faces are from the same person under normal conditions, the distance
      is typically below 0.5.
    - If the two faces belong to different people, the distance is typically above 0.6.
    """
    if len(vector_a) != len(vector_b):
        raise ValueError(
            f"Vector dimensions do not match: expected {len(vector_a)} elements, got {len(vector_b)}"
        )

    # Sum of squared differences across all 128 dimensions, then take the square root
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

    NON-TECHNICAL EXPLANATION:
    --------------------------
    This function acts as the biometric guard. It compares the face scanned at the camera
    against every registered user in our database. It finds the user whose stored face
    measurements are closest to the scanned face.

    If that closest distance is smaller than our safety threshold (0.5), we confirm
    the user's identity and let them in. If no user's face is close enough, we reject
    the login attempt.

    Parameters:
    - incoming_descriptor: The 128-float array captured from the user's camera.
    - candidate_users: List of tuples containing (username, stored_128_float_descriptor).
    - threshold: Maximum Euclidean distance allowed for a match (default: 0.5).

    Returns:
    - Tuple of (matched_username, match_distance) if a valid match within threshold is found.
    - None if candidate list is empty or the closest match exceeds the threshold.
    """
    if not candidate_users:
        return None

    best_username: Optional[str] = None
    min_distance: float = float("inf")

    for username, stored_descriptor in candidate_users:
        try:
            distance = calculate_euclidean_distance(incoming_descriptor, stored_descriptor)
            if distance < min_distance:
                min_distance = distance
                best_username = username
        except ValueError:
            # Skip candidates with mismatched descriptor dimensions
            continue

    # Verify if the closest candidate is within the acceptable similarity threshold
    if best_username is not None and min_distance < threshold:
        return best_username, min_distance

    return None

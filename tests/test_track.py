"""Tests puros de la pista."""

from __future__ import annotations

import math

from horror_karting.track import Track


def test_track_is_closed_and_has_expected_length() -> None:
    track = Track()
    assert abs(track.length - 1600.0) < 1e-6
    assert track.sample_count > 100
    start = track.point(0.0)
    wrapped = track.point(track.length)
    assert math.dist(start, wrapped) < 1e-6


def test_negative_distance_wraps_to_incoming_straight() -> None:
    track = Track()
    behind = track.point(-8.0)
    wrapped = track.point(track.length - 8.0)
    assert math.dist(behind, wrapped) < 1e-6
    # La grilla queda detrás de la línea de largada, no encima.
    grid = track.point(-10.0)
    start = track.point(0.0)
    assert math.dist(grid, start) > 5.0


def test_heading_points_west_at_start() -> None:
    track = Track()
    heading = math.degrees(track.heading(0.0))
    assert abs(heading - 90.0) < 3.0


def test_nearest_s_returns_close_distance() -> None:
    track = Track()
    point = track.point(640.0, 2.0)
    found = track.nearest_s(point[0], point[1])
    assert abs(found - 640.0) < 3.0


def test_height_profile_has_bridge() -> None:
    track = Track()
    heights = [track.height(index * 8.0) for index in range(int(track.length / 8.0))]
    assert max(heights) > 2.0
    assert min(heights) >= -0.5

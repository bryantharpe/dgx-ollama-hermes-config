#!/usr/bin/env python3
"""Route optimization utilities for AI World Fair prototype."""


def build_grid(booths: list, obstacles: list = None) -> dict:
    """Build 2D grid from booth positions and obstacle cells.

    Args:
        booths: List of booth dicts with grid_x, grid_y
        obstacles: List of (x, y) tuples for non-traversable cells

    Returns:
        Grid dict with dimensions, booths, and obstacles
    """
    if obstacles is None:
        obstacles = []

    max_x = max((b.get("grid_x", 0) for b in booths), default=0)
    max_y = max((b.get("grid_y", 0) for b in booths), default=0)

    grid = {
        "width": max_x + 3,
        "height": max_y + 3,
        "booths": {b.get("booth_id", b.get("id")): (b.get("grid_x", 0), b.get("grid_y", 0)) for b in booths},
        "booth_coords": {(b.get("grid_x", 0), b.get("grid_y", 0)): b.get("booth_id", b.get("id")) for b in booths},
        "obstacles": set(obstacles),
    }
    return grid


def manhattan_distance(p1: tuple, p2: tuple) -> int:
    """Calculate Manhattan distance between two points."""
    return abs(p1[0] - p2[0]) + abs(p1[1] - p2[1])


def optimize_route(booths: list, start: tuple = (0, 0)) -> list:
    """Calculate optimized route through booths using greedy nearest-neighbor.

    Args:
        booths: List of booth dicts with booth_id, grid_x, grid_y
        start: Starting position (x, y), defaults to entrance at (0, 0)

    Returns:
        Ordered list of booth IDs representing optimized path
    """
    if not booths:
        return []

    grid = build_grid(booths)
    unvisited = list(grid["booths"].items())
    route = []
    current = start

    while unvisited:
        if not unvisited:
            break

        nearest = min(unvisited, key=lambda x: manhattan_distance(current, x[1]))
        booth_id, coords = nearest
        route.append(booth_id)
        current = coords
        unvisited.remove(nearest)

    return route


def get_route_path(booths: list, route_order: list) -> list:
    """Get sequence of coordinates for route visualization.

    Args:
        booths: List of booth dicts
        route_order: Ordered list of booth IDs

    Returns:
        List of (x, y) tuples representing the full path
    """
    grid = build_grid(booths)
    path = [(0, 0)]

    for booth_id in route_order:
        if booth_id in grid["booths"]:
            path.append(grid["booths"][booth_id])

    return path


if __name__ == "__main__":
    test_booths = [
        {"booth_id": "b1", "grid_x": 2, "grid_y": 3},
        {"booth_id": "b2", "grid_x": 5, "grid_y": 7},
        {"booth_id": "b3", "grid_x": 8, "grid_y": 4},
    ]

    route = optimize_route(test_booths)
    print("Optimized route:", route)

    path = get_route_path(test_booths, route)
    print("Route path:", path)

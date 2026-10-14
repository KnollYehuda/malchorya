"""Lays the world's locations out on a grid from their exits, and tracks what's been seen."""
from collections import deque
from typing import Dict, Set, Tuple

from core.enums import WindDirection

OFFSETS: Dict[WindDirection, Tuple[int, int]] = {
    WindDirection.NORTH: (0, -1),
    WindDirection.SOUTH: (0, 1),
    WindDirection.EAST: (1, 0),
    WindDirection.WEST: (-1, 0),
}


def layout(world, origin: str = "crossroads") -> Dict[str, Tuple[int, int]]:
    """Grid coordinates (column, row) for every location reachable from `origin`; north is up."""
    positions: Dict[str, Tuple[int, int]] = {origin: (0, 0)}
    queue = deque([origin])
    while queue:
        current = queue.popleft()
        column, row = positions[current]
        for direction, neighbour in world.get_location(current).exits.items():
            if neighbour in positions or neighbour not in world.locations:
                continue
            offset_column, offset_row = OFFSETS[direction]
            positions[neighbour] = (column + offset_column, row + offset_row)
            queue.append(neighbour)
    return positions


def frontier(world, visited) -> Set[str]:
    """Places you know exist (adjacent to somewhere visited) but haven't been to."""
    known: Set[str] = set()
    for location_id in visited:
        for neighbour in world.get_location(location_id).exits.values():
            if neighbour not in visited:
                known.add(neighbour)
    return known


def ascii_map(state) -> str:
    world = state.world
    positions = layout(world)
    visited = set(state.visited)
    unknown = frontier(world, visited)
    shown = {location_id: positions[location_id] for location_id in visited | unknown if location_id in positions}
    if not shown:
        return "You have no map yet."
    min_column = min(column for column, _ in shown.values())
    max_column = max(column for column, _ in shown.values())
    min_row = min(row for _, row in shown.values())
    max_row = max(row for _, row in shown.values())
    by_position = {position: location_id for location_id, position in shown.items()}

    def symbol(location_id: str) -> str:
        if location_id == state.player.location_id:
            return "@"
        return "#" if location_id in visited else "?"

    def connected(first: str, second: str) -> bool:
        return second in world.get_location(first).exits.values() and (first in visited or second in visited)

    lines = []
    for row in range(min_row, max_row + 1):
        cells, below = "", ""
        for column in range(min_column, max_column + 1):
            here = by_position.get((column, row))
            cells += f"[{symbol(here)}]" if here else "   "
            east = by_position.get((column + 1, row))
            cells += "-" if here and east and connected(here, east) else " "
            south = by_position.get((column, row + 1))
            below += " | " if here and south and connected(here, south) else "   "
            below += " "
        lines.append(cells.rstrip())
        lines.append(below.rstrip())
    legend = ["", "@ you   # visited   ? unexplored   (north is up)", "Explored: " + ", ".join(
        world.get_location(location_id).name for location_id in sorted(visited, key=lambda value: positions.get(value, (9, 9)))
    )]
    return "\n".join([line for line in lines if line.strip()] + legend)

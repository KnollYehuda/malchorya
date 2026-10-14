"""Low-poly, flat-shaded mesh primitives built straight into Panda3D geometry."""
import math
import random
from typing import List, Optional, Sequence, Tuple

from panda3d.core import (
    Geom,
    GeomNode,
    GeomTriangles,
    GeomVertexData,
    GeomVertexFormat,
    GeomVertexWriter,
    NodePath,
    Vec3,
)

Point = Tuple[float, float, float]
Color = Tuple[float, float, float, float]


def rgb(red: int, green: int, blue: int, alpha: float = 1.0) -> Color:
    return (red / 255.0, green / 255.0, blue / 255.0, alpha)


def _scaled(color: Color, factor: float) -> Color:
    return (min(1.0, color[0] * factor), min(1.0, color[1] * factor), min(1.0, color[2] * factor), color[3])


def _subtract(first: Point, second: Point) -> Point:
    return (first[0] - second[0], first[1] - second[1], first[2] - second[2])


def _cross(first: Point, second: Point) -> Point:
    return (
        first[1] * second[2] - first[2] * second[1],
        first[2] * second[0] - first[0] * second[2],
        first[0] * second[1] - first[1] * second[0],
    )


def _dot(first: Point, second: Point) -> float:
    return first[0] * second[0] + first[1] * second[1] + first[2] * second[2]


def _normalize(vector: Point) -> Point:
    length = math.sqrt(_dot(vector, vector)) or 1.0
    return (vector[0] / length, vector[1] / length, vector[2] / length)


def _rotated(point: Point, center: Point, heading_degrees: float) -> Point:
    if not heading_degrees:
        return point
    angle = math.radians(heading_degrees)
    cosine, sine = math.cos(angle), math.sin(angle)
    offset_x, offset_y = point[0] - center[0], point[1] - center[1]
    return (
        center[0] + offset_x * cosine - offset_y * sine,
        center[1] + offset_x * sine + offset_y * cosine,
        point[2],
    )


class MeshBuilder:
    """Collects triangles (flat shaded, wound to face away from a reference point)."""

    def __init__(self, name: str = "mesh", seed: int = 0, variation: float = 0.07) -> None:
        self.name = name
        self.rng = random.Random(seed)
        self.variation = variation
        self.triangles: List[Tuple[Point, Point, Point, Color]] = []

    # -------------------------------------------------------------- basics

    def triangle(self, first: Point, second: Point, third: Point, color: Color, inside: Optional[Point]) -> None:
        normal = _cross(_subtract(second, first), _subtract(third, first))
        if inside is not None:
            centroid = (
                (first[0] + second[0] + third[0]) / 3,
                (first[1] + second[1] + third[1]) / 3,
                (first[2] + second[2] + third[2]) / 3,
            )
            if _dot(normal, _subtract(centroid, inside)) < 0:
                second, third = third, second
        factor = 1.0 + self.rng.uniform(-self.variation, self.variation)
        self.triangles.append((first, second, third, _scaled(color, factor)))

    def quad(self, first: Point, second: Point, third: Point, fourth: Point, color: Color, inside: Optional[Point]) -> None:
        self.triangle(first, second, third, color, inside)
        self.triangle(first, third, fourth, color, inside)

    # ---------------------------------------------------------- primitives

    def box(
        self, center: Point, size: Point, color: Color, heading: float = 0.0, top_color: Optional[Color] = None
    ) -> None:
        half_x, half_y, half_z = size[0] / 2, size[1] / 2, size[2] / 2
        corners = {}
        for sign_x in (-1, 1):
            for sign_y in (-1, 1):
                for sign_z in (-1, 1):
                    corner = (center[0] + sign_x * half_x, center[1] + sign_y * half_y, center[2] + sign_z * half_z)
                    corners[(sign_x, sign_y, sign_z)] = _rotated(corner, center, heading)
        faces = [
            ((-1, -1, -1), (1, -1, -1), (1, -1, 1), (-1, -1, 1), color),
            ((-1, 1, -1), (1, 1, -1), (1, 1, 1), (-1, 1, 1), color),
            ((-1, -1, -1), (-1, 1, -1), (-1, 1, 1), (-1, -1, 1), color),
            ((1, -1, -1), (1, 1, -1), (1, 1, 1), (1, -1, 1), color),
            ((-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1), top_color or _scaled(color, 1.12)),
            ((-1, -1, -1), (1, -1, -1), (1, 1, -1), (-1, 1, -1), _scaled(color, 0.7)),
        ]
        for first, second, third, fourth, face_color in faces:
            self.quad(corners[first], corners[second], corners[third], corners[fourth], face_color, center)

    def tube(
        self,
        start: Point,
        end: Point,
        start_radius: float,
        end_radius: float,
        color: Color,
        segments: int = 8,
        cap_color: Optional[Color] = None,
    ) -> None:
        axis = _normalize(_subtract(end, start))
        helper = (1.0, 0.0, 0.0) if abs(axis[0]) < 0.9 else (0.0, 1.0, 0.0)
        side = _normalize(_cross(axis, helper))
        up = _cross(axis, side)
        middle = ((start[0] + end[0]) / 2, (start[1] + end[1]) / 2, (start[2] + end[2]) / 2)

        def ring_point(base: Point, radius: float, index: int) -> Point:
            angle = 2 * math.pi * index / segments
            return (
                base[0] + radius * (side[0] * math.cos(angle) + up[0] * math.sin(angle)),
                base[1] + radius * (side[1] * math.cos(angle) + up[1] * math.sin(angle)),
                base[2] + radius * (side[2] * math.cos(angle) + up[2] * math.sin(angle)),
            )

        for index in range(segments):
            bottom_a, bottom_b = ring_point(start, start_radius, index), ring_point(start, start_radius, index + 1)
            top_a, top_b = ring_point(end, end_radius, index), ring_point(end, end_radius, index + 1)
            self.quad(bottom_a, bottom_b, top_b, top_a, color, middle)
            if end_radius > 0:
                self.triangle(end, top_a, top_b, cap_color or _scaled(color, 1.15), middle)
            if start_radius > 0:
                self.triangle(start, bottom_a, bottom_b, _scaled(color, 0.7), middle)

    def cylinder(self, base: Point, radius: float, height: float, color: Color, segments: int = 8, **kwargs) -> None:
        self.tube(base, (base[0], base[1], base[2] + height), radius, radius, color, segments, **kwargs)

    def cone(self, base: Point, radius: float, height: float, color: Color, segments: int = 8) -> None:
        self.tube(base, (base[0], base[1], base[2] + height), radius, 0.0, color, segments)

    def sphere(
        self,
        center: Point,
        radii: Point,
        color: Color,
        rings: int = 3,
        segments: int = 7,
        jitter: float = 0.0,
    ) -> None:
        def surface_point(ring: int, segment: int) -> Point:
            polar = math.pi * ring / (rings + 1)
            azimuth = 2 * math.pi * segment / segments
            scale = 1.0 + (self.rng.uniform(-jitter, jitter) if jitter and 0 < ring <= rings else 0.0)
            return (
                center[0] + radii[0] * scale * math.sin(polar) * math.cos(azimuth),
                center[1] + radii[1] * scale * math.sin(polar) * math.sin(azimuth),
                center[2] + radii[2] * scale * math.cos(polar),
            )

        grid = [[surface_point(ring, segment % segments) for segment in range(segments + 1)] for ring in range(rings + 2)]
        for ring in range(rings + 1):
            for segment in range(segments):
                first, second = grid[ring][segment], grid[ring][segment + 1]
                third, fourth = grid[ring + 1][segment + 1], grid[ring + 1][segment]
                shade = 0.85 + 0.3 * (1 - ring / (rings + 1))
                if ring == 0:
                    self.triangle(first, fourth, third, _scaled(color, shade), center)
                elif ring == rings:
                    self.triangle(first, second, fourth, _scaled(color, shade), center)
                else:
                    self.quad(first, second, third, fourth, _scaled(color, shade), center)

    def gable_roof(
        self,
        base_center: Point,
        width: float,
        depth: float,
        height: float,
        roof_color: Color,
        wall_color: Color,
        overhang: float = 0.4,
    ) -> None:
        """Roof with the ridge along Y; gables face +/-Y (front faces -Y)."""
        center_x, center_y, base_z = base_center
        half_w, half_d = width / 2 + overhang, depth / 2 + overhang * 0.5
        front_left = (center_x - half_w, center_y - half_d, base_z)
        front_right = (center_x + half_w, center_y - half_d, base_z)
        back_left = (center_x - half_w, center_y + half_d, base_z)
        back_right = (center_x + half_w, center_y + half_d, base_z)
        ridge_front = (center_x, center_y - half_d, base_z + height)
        ridge_back = (center_x, center_y + half_d, base_z + height)
        inside = (center_x, center_y, base_z + height * 0.3)
        self.quad(front_left, back_left, ridge_back, ridge_front, roof_color, inside)
        self.quad(front_right, back_right, ridge_back, ridge_front, _scaled(roof_color, 0.85), inside)
        self.triangle(front_left, front_right, ridge_front, wall_color, inside)
        self.triangle(back_left, back_right, ridge_back, _scaled(wall_color, 0.8), inside)
        self.quad(front_left, front_right, back_right, back_left, _scaled(roof_color, 0.5), inside)

    # --------------------------------------------------------------- output

    def build(self) -> NodePath:
        vertex_data = GeomVertexData(self.name, GeomVertexFormat.getV3n3cp(), Geom.UHStatic)
        vertex_data.setNumRows(len(self.triangles) * 3)
        vertex_writer = GeomVertexWriter(vertex_data, "vertex")
        normal_writer = GeomVertexWriter(vertex_data, "normal")
        color_writer = GeomVertexWriter(vertex_data, "color")
        primitive = GeomTriangles(Geom.UHStatic)
        for index, (first, second, third, color) in enumerate(self.triangles):
            normal = _normalize(_cross(_subtract(second, first), _subtract(third, first)))
            for point in (first, second, third):
                vertex_writer.addData3(*point)
                normal_writer.addData3(*normal)
                color_writer.addData4(*color)
            primitive.addVertices(index * 3, index * 3 + 1, index * 3 + 2)
        geom = Geom(vertex_data)
        geom.addPrimitive(primitive)
        node = GeomNode(self.name)
        node.addGeom(geom)
        return NodePath(node)


def flat_quad(
    x_min: float, y_min: float, x_max: float, y_max: float, height: float, uv_per_unit: float = 1.0 / 16, name: str = "flat"
) -> NodePath:
    """Upward-facing textured quad lying on the ground."""
    vertex_data = GeomVertexData(name, GeomVertexFormat.getV3n3t2(), Geom.UHStatic)
    vertex_writer = GeomVertexWriter(vertex_data, "vertex")
    normal_writer = GeomVertexWriter(vertex_data, "normal")
    uv_writer = GeomVertexWriter(vertex_data, "texcoord")
    for corner_x, corner_y in ((x_min, y_min), (x_max, y_min), (x_max, y_max), (x_min, y_max)):
        vertex_writer.addData3(corner_x, corner_y, height)
        normal_writer.addData3(0, 0, 1)
        uv_writer.addData2(corner_x * uv_per_unit, corner_y * uv_per_unit)
    primitive = GeomTriangles(Geom.UHStatic)
    primitive.addVertices(0, 1, 2)
    primitive.addVertices(0, 2, 3)
    geom = Geom(vertex_data)
    geom.addPrimitive(primitive)
    node = GeomNode(name)
    node.addGeom(geom)
    return NodePath(node)


def flat_ellipse(
    radius_x: float, radius_y: float, height: float, uv_per_unit: float = 1.0 / 16, segments: int = 28, name: str = "disc"
) -> NodePath:
    vertex_data = GeomVertexData(name, GeomVertexFormat.getV3n3t2(), Geom.UHStatic)
    vertex_writer = GeomVertexWriter(vertex_data, "vertex")
    normal_writer = GeomVertexWriter(vertex_data, "normal")
    uv_writer = GeomVertexWriter(vertex_data, "texcoord")
    points = [(0.0, 0.0)] + [
        (radius_x * math.cos(2 * math.pi * index / segments), radius_y * math.sin(2 * math.pi * index / segments))
        for index in range(segments)
    ]
    for point_x, point_y in points:
        vertex_writer.addData3(point_x, point_y, height)
        normal_writer.addData3(0, 0, 1)
        uv_writer.addData2(point_x * uv_per_unit, point_y * uv_per_unit)
    primitive = GeomTriangles(Geom.UHStatic)
    for index in range(segments):
        primitive.addVertices(0, 1 + index, 1 + (index + 1) % segments)
    geom = Geom(vertex_data)
    geom.addPrimitive(primitive)
    node = GeomNode(name)
    node.addGeom(geom)
    return NodePath(node)


def vertical_quad(
    start: Tuple[float, float],
    end: Tuple[float, float],
    bottom: float,
    top: float,
    facing: Tuple[float, float],
    uv_per_unit: float = 1.0 / 16,
    name: str = "wall",
) -> NodePath:
    """Textured wall segment between two ground points, front face looking toward `facing`."""
    corners = [(start[0], start[1], bottom), (end[0], end[1], bottom), (end[0], end[1], top), (start[0], start[1], top)]
    edge = _subtract(corners[1], corners[0])
    normal = _cross(edge, _subtract(corners[3], corners[0]))
    if normal[0] * facing[0] + normal[1] * facing[1] < 0:
        corners = [corners[1], corners[0], corners[3], corners[2]]
        edge = _subtract(corners[1], corners[0])
        normal = _cross(edge, _subtract(corners[3], corners[0]))
    normal = _normalize(normal)
    length = math.hypot(end[0] - start[0], end[1] - start[1])
    vertex_data = GeomVertexData(name, GeomVertexFormat.getV3n3t2(), Geom.UHStatic)
    vertex_writer = GeomVertexWriter(vertex_data, "vertex")
    normal_writer = GeomVertexWriter(vertex_data, "normal")
    uv_writer = GeomVertexWriter(vertex_data, "texcoord")
    uvs = [(0, bottom), (length, bottom), (length, top), (0, top)]
    for corner, (uv_u, uv_v) in zip(corners, uvs):
        vertex_writer.addData3(*corner)
        normal_writer.addData3(*normal)
        uv_writer.addData2(uv_u * uv_per_unit, uv_v * uv_per_unit)
    primitive = GeomTriangles(Geom.UHStatic)
    primitive.addVertices(0, 1, 2)
    primitive.addVertices(0, 2, 3)
    geom = Geom(vertex_data)
    geom.addPrimitive(primitive)
    node = GeomNode(name)
    node.addGeom(geom)
    return NodePath(node)

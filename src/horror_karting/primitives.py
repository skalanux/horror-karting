"""Ayudas de geometría procedural: cajas, esferas, tarjetas y textos."""

from __future__ import annotations

from typing import Any

from panda3d.core import CardMaker, NodePath, TextNode, Vec3, Vec4

Color = Vec4


class Build:
    def __init__(self, base: Any) -> None:
        self.base = base
        self._box = base.loader.loadModel("models/box")
        self._sphere = base.loader.loadModel("models/misc/sphere")

    # -- cajas --------------------------------------------------------------

    def box(
        self,
        parent: NodePath,
        center: tuple[float, float, float],
        size: tuple[float, float, float],
        color: Color,
        *,
        hpr: tuple[float, float, float] | None = None,
        lit: bool = False,
    ) -> NodePath:
        if hpr is not None:
            pivot = parent.attachNewNode("box-pivot")
            pivot.setPos(*center)
            pivot.setHpr(*hpr)
            holder: NodePath = pivot
            offset = (-size[0] / 2.0, -size[1] / 2.0, -size[2] / 2.0)
        else:
            holder = parent
            offset = (
                center[0] - size[0] / 2.0,
                center[1] - size[1] / 2.0,
                center[2] - size[2] / 2.0,
            )
        model = self._box.copyTo(holder)
        model.set_texture_off(1)
        model.set_scale(*size)
        model.set_pos(*offset)
        model.set_color(color)
        if not lit:
            model.set_light_off(1)
        return model

    def ball(
        self,
        parent: NodePath,
        center: tuple[float, float, float],
        radius: float | tuple[float, float, float],
        color: Color,
        *,
        hpr: tuple[float, float, float] | None = None,
        lit: bool = False,
        alpha: bool = False,
    ) -> NodePath:
        if isinstance(radius, (int, float)):
            scale = (float(radius), float(radius), float(radius))
        else:
            scale = radius
        if hpr is not None:
            pivot = parent.attachNewNode("ball-pivot")
            pivot.setPos(*center)
            pivot.setHpr(*hpr)
            holder = pivot
        else:
            holder = parent
            pivot = None
        model = self._sphere.copyTo(holder)
        model.set_texture_off(1)
        model.set_scale(*scale)
        if pivot is None:
            model.set_pos(*center)
        model.set_color(color)
        if alpha:
            model.set_transparency(1)
        if not lit:
            model.set_light_off(1)
        return model

    # -- tarjetas -----------------------------------------------------------

    def card(
        self,
        parent: NodePath,
        center: tuple[float, float, float],
        width: float,
        height: float,
        color: Color,
        *,
        hpr: tuple[float, float, float] | None = None,
        billboard: bool = False,
        two_sided: bool = True,
        depth_write: bool = True,
        alpha: bool = False,
    ) -> NodePath:
        maker = CardMaker("card")
        maker.set_frame(-width / 2.0, width / 2.0, -height / 2.0, height / 2.0)
        card = parent.attachNewNode(maker.generate())
        card.set_pos(*center)
        if hpr is not None:
            card.setHpr(*hpr)
        if billboard:
            card.set_billboard_point_eye()
        if two_sided:
            card.set_two_sided(True)
        card.set_color(color)
        if alpha or color[3] < 1.0:
            card.set_transparency(1)
        if not depth_write:
            card.set_depth_write(False)
        card.set_light_off(1)
        return card

    def text(
        self,
        parent: NodePath,
        value: str,
        pos: tuple[float, float, float],
        scale: float,
        color: Color,
        *,
        billboard: bool = False,
        align: int = TextNode.ACenter,
        shadow: bool = True,
    ) -> NodePath:
        node = TextNode("text")
        node.set_text(value)
        node.set_align(align)
        node.set_text_color(color)
        if shadow:
            node.set_shadow(0.06, 0.06)
            node.set_shadow_color(Vec4(0.0, 0.0, 0.0, 0.75))
        holder = parent.attachNewNode(node)
        holder.set_pos(*pos)
        holder.set_scale(scale)
        if billboard:
            holder.set_billboard_point_eye()
        holder.set_light_off(1)
        return holder

    # -- ayudas -------------------------------------------------------------

    def glow(
        self,
        parent: NodePath,
        center: tuple[float, float, float],
        radius: float,
        color: Color,
        *,
        layers: int = 2,
        sort: int = 5,
    ) -> NodePath:
        root = parent.attachNewNode("glow")
        root.set_pos(*center)
        for index in range(layers):
            factor = 1.0 + index * 0.55
            alpha = color[3] * (0.75 / (index + 1.0))
            orb = self.ball(
                root,
                (0.0, 0.0, 0.0),
                radius * factor,
                Vec4(color[0], color[1], color[2], alpha),
                alpha=True,
            )
            orb.set_depth_write(False)
            orb.set_bin("fixed", sort)
        return root

    def line_points(self, parent: NodePath, points: list[Vec3], color: Color, thickness: float = 2.0) -> NodePath:
        from panda3d.core import LineSegs

        segs = LineSegs("line")
        segs.set_color(color)
        segs.set_thickness(thickness)
        if points:
            segs.move_to(points[0])
            for point in points[1:]:
                segs.draw_to(point)
        node = segs.create()
        holder = parent.attachNewNode(node)
        holder.set_light_off(1)
        return holder

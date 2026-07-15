from __future__ import annotations
import json

import pymod
from ..components.ui.ui_rect import UIRect, UIAnchor
from ..components.ui.widgets import UIImage, UIText, UIButton, UISlider, UIToggle
from ..components.ui.layouts import VerticalLayout, HorizontalLayout, GridLayout

UI_LAYER = "ui"

_ANCHORS = {
    "top_left": UIAnchor.TOP_LEFT, "top_center": UIAnchor.TOP_CENTER,
    "top_right": UIAnchor.TOP_RIGHT, "center_left": UIAnchor.CENTER_LEFT,
    "center": UIAnchor.CENTER, "center_right": UIAnchor.CENTER_RIGHT,
    "bottom_left": UIAnchor.BOTTOM_LEFT, "bottom_center": UIAnchor.BOTTOM_CENTER,
    "bottom_right": UIAnchor.BOTTOM_RIGHT, "stretch": UIAnchor.STRETCH,
    "stretch_horizontal": UIAnchor.STRETCH_HORIZONTAL,
    "stretch_vertical": UIAnchor.STRETCH_VERTICAL,
}


def build_layout(path: str, scene, actions: dict) -> None:
    """Load a JSON UI layout file and instantiate it into a scene.

    Args:
        path: Path to the JSON layout.
        scene: Scene to add created UI GameObjects to.
        actions: Maps action name strings to callables for button clicks and value-change callbacks.
    """
    with open(path, "r") as f:
        data = json.load(f)

    styles = data.get("styles", {})

    for element in data.get("elements", []):
        _build_element(element, parent=None, scene=scene, actions=actions, styles=styles)


def _resolve_style(element: dict, styles: dict) -> dict:
    """Merge a named style under the element's own properties.

    Element-level keys override the style's keys.
    """
    style_name = element.get("style")
    if style_name and style_name in styles:
        merged = dict(styles[style_name])
        merged.update(element)
        return merged
    return element


def _build_element(element, parent, scene, actions, styles):
    element = _resolve_style(element, styles)

    obj = pymod.GameObject(layer=UI_LAYER)
    obj.name = element.get("name", "ui_element")

    # UIRect — every element has one
    rect = UIRect(
        anchor=_ANCHORS.get(element.get("anchor", "top_left"), UIAnchor.TOP_LEFT),
        size=tuple(element.get("size", (100, 100))),
        offset=tuple(element.get("offset", (0, 0))),
        margin=tuple(element.get("margin", (0, 0, 0, 0))),
        pivot=tuple(element.get("pivot", (0.5, 0.5))),
    )
    obj.add_component(rect)

    # the widget itself
    etype = element.get("type", "panel")
    _attach_widget(obj, etype, element, actions)

    # a layout group on this element, arranging its children
    layout = element.get("layout")
    if layout:
        _attach_layout(obj, layout)

    scene.add_object(obj)

    if parent is not None:
        parent.add_child(obj)

    for child in element.get("children", []):
        _build_element(child, parent=obj, scene=scene, actions=actions, styles=styles)

    return obj


def _attach_widget(obj, etype, element, actions):
    if etype in ("image", "panel", "background"):
        obj.add_component(UIImage(
            color=tuple(element.get("color", (255, 255, 255))),
            image_path=element.get("image"),
            corner_radius=element.get("corner_radius", 0),
        ))
    elif etype == "text":
        obj.add_component(UIText(
            text=element.get("text", ""),
            font_size=element.get("font_size", 24),
            color=tuple(element.get("color", (255, 255, 255))),
            align=element.get("align", "center"),
            valign=element.get("valign", "middle"),
            wrap=element.get("wrap", False),
        ))
    elif etype == "button":
        obj.add_component(UIButton(
            text=element.get("text", "Button"),
            font_size=element.get("font_size", 24),
            normal_color=tuple(element.get("color", (60, 60, 70))),
            corner_radius=element.get("corner_radius", 6),
            on_click_callback=actions.get(element.get("action")),
        ))
    elif etype == "slider":
        obj.add_component(UISlider(
            min_value=element.get("min", 0.0),
            max_value=element.get("max", 1.0),
            value=element.get("value", 0.5),
            on_change_callback=actions.get(element.get("action")),
        ))
    elif etype == "toggle":
        obj.add_component(UIToggle(
            value=element.get("value", False),
            on_change_callback=actions.get(element.get("action")),
        ))


def _attach_layout(obj, layout):
    ltype = layout.get("type", "vertical")
    spacing = layout.get("spacing", 8)
    padding = layout.get("padding", 8)
    if ltype == "vertical":
        obj.add_component(VerticalLayout(spacing, padding))
    elif ltype == "horizontal":
        obj.add_component(HorizontalLayout(spacing, padding))
    elif ltype == "grid":
        obj.add_component(GridLayout(layout.get("columns", 2), spacing, padding))
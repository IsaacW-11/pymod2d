"""UI loader v3 — styles library, per-state, rotation, and all new components."""
from __future__ import annotations
import json
import pymod
from ..components.ui.ui_rect import UIRect, UIAnchor
from ..components.ui.ui_style import build_style_set
from ..components.ui.widgets import (UIImage, UIText, UIButton, UISlider, UIToggle,
                      UIProgressBar, UIDivider, UIIcon, UITextInput,
                      UIRadioGroup, UIDropdown, UITooltip, UIScrollView)
from ..components.ui.layouts import VerticalLayout, HorizontalLayout, GridLayout

UI_LAYER="ui"
_ANCHORS={"top_left":UIAnchor.TOP_LEFT,"top_center":UIAnchor.TOP_CENTER,"top_right":UIAnchor.TOP_RIGHT,
  "center_left":UIAnchor.CENTER_LEFT,"center":UIAnchor.CENTER,"center_right":UIAnchor.CENTER_RIGHT,
  "bottom_left":UIAnchor.BOTTOM_LEFT,"bottom_center":UIAnchor.BOTTOM_CENTER,"bottom_right":UIAnchor.BOTTOM_RIGHT,
  "stretch":UIAnchor.STRETCH,"stretch_horizontal":UIAnchor.STRETCH_HORIZONTAL,"stretch_vertical":UIAnchor.STRETCH_VERTICAL}


def build_layout(path, scene, actions):
    with open(path) as f: data=json.load(f)
    styles=_resolve_library(data.get("styles",{}))
    for el in data.get("elements",[]): _build(el,None,scene,actions,styles)

def _resolve_library(raw):
    out={}
    def res(name,seen):
        if name in out: return out[name]
        if name in seen or name not in raw: return {}
        seen.add(name); s=dict(raw[name]); parent=s.pop("extends",None)
        if parent: s=_merge(dict(res(parent,seen)),s)
        out[name]=s; return s
    for n in raw: res(n,set())
    return out

def _merge(base,over):
    for k,v in over.items():
        if isinstance(v,dict) and isinstance(base.get(k),dict): base[k]=_merge(dict(base[k]),v)
        else: base[k]=v
    return base

def _apply(el,styles):
    name=el.get("style")
    if name and name in styles:
        return _merge(dict(styles[name]),{k:v for k,v in el.items() if k!="style"})
    return el

def _build(el,parent,scene,actions,styles):
    el=_apply(el,styles)
    obj=pymod.GameObject(layer=UI_LAYER); obj.name=el.get("name","ui_element")
    obj.add_component(UIRect(
        anchor=_ANCHORS.get(el.get("anchor","top_left"),UIAnchor.TOP_LEFT),
        size=tuple(el.get("size",(100,100))), offset=tuple(el.get("offset",(0,0))),
        margin=tuple(el.get("margin",(0,0,0,0))), pivot=tuple(el.get("pivot",(0.5,0.5))),
        rotation=el.get("rotation",0.0)))
    _widget(obj, el.get("type","panel"), el, actions)
    layout=el.get("layout")
    if layout: _layout(obj,layout)
    scene.add_object(obj)
    if parent is not None: parent.add_child(obj)
    for c in el.get("children",[]): _build(c,obj,scene,actions,styles)
    if layout:
        for c in obj.children:
            crc=c.get_component(UIRect)
            if crc: crc.layout_controlled=True
    return obj

def _style_dict(el):
    """Strip the element's POSITION offset before building a Style.

    "offset" means two different things depending on where it appears:
    top-level = the element's PLACEMENT (owned by UIRect). Inside a
    "states" block = a per-state visual NUDGE (owned by Style, e.g. a
    button moving down 2px on press). They share a JSON key by convenience
    but must never be merged — build_style_set would otherwise pick up the
    placement value as the style's baseline offset, and a state without its
    own nudge would inherit and re-apply that placement on top of the
    already-positioned rect, doubling it.
    """
    d = dict(el)
    d.pop("offset", None)
    return d


def _widget(obj,t,el,actions):
    if t in ("image","panel","background"):
        obj.add_component(UIImage(build_style_set(_style_dict(el)), el.get("image")))
    elif t=="text":
        obj.add_component(UIText(el.get("text",""),el.get("font_size",24),el.get("color",(255,255,255)),
            align=el.get("align","center"),valign=el.get("valign","middle"),wrap=el.get("wrap",False)))
    elif t=="button":
        obj.add_component(UIButton(build_style_set(_style_dict(el)),el.get("text","Button"),el.get("font_size",24),
            on_click_callback=actions.get(el.get("action"))))
    elif t=="slider":
        obj.add_component(UISlider(el.get("min",0.0),el.get("max",1.0),el.get("value",0.5),
            on_change_callback=actions.get(el.get("action"))))
    elif t=="toggle":
        obj.add_component(UIToggle(el.get("value",False),on_change_callback=actions.get(el.get("action"))))
    elif t=="progress":
        fs=build_style_set(_style_dict(el.get("fill_style",{}))) if el.get("fill_style") else None
        obj.add_component(UIProgressBar(el.get("value",0.5),
            tuple(el.get("track_color",(40,44,56))),tuple(el.get("fill_color",(90,180,140))),
            el.get("corner_radius",6),fs))
    elif t=="divider":
        obj.add_component(UIDivider(tuple(el.get("color",(70,78,94))),el.get("thickness",2),
            el.get("orientation","horizontal")))
    elif t=="icon":
        obj.add_component(UIIcon(el.get("shape","circle"),tuple(el.get("color",(220,225,235))),el.get("image")))
    elif t=="textinput":
        obj.add_component(UITextInput(build_style_set(_style_dict(el)),el.get("text",""),el.get("placeholder",""),
            el.get("font_size",20),max_length=el.get("max_length",64),
            on_change_callback=actions.get(el.get("action"))))
    elif t=="radio":
        obj.add_component(UIRadioGroup(el.get("options",["Option A","Option B"]),el.get("selected",0),
            font_size=el.get("font_size",20),on_change_callback=actions.get(el.get("action"))))
    elif t=="dropdown":
        obj.add_component(UIDropdown(build_style_set(_style_dict(el)),el.get("options",["One","Two","Three"]),
            el.get("selected",0),el.get("font_size",20),on_change_callback=actions.get(el.get("action"))))
    elif t=="scroll":
        obj.add_component(UIScrollView(el.get("content_height",0),tuple(el.get("color",(22,26,36))),
            el.get("corner_radius",8)))
    # tooltip is an attachable extra, not a standalone type
    if el.get("tooltip"):
        obj.add_component(UITooltip(el["tooltip"], el.get("tooltip_delay",0.5)))

def _layout(obj,layout):
    t=layout.get("type","vertical"); sp=layout.get("spacing",8)
    pad=layout.get("padding",(8,8,8,8))
    if isinstance(pad,(int,float)): pad=(pad,pad,pad,pad)
    align=layout.get("align","center")
    if t=="vertical": obj.add_component(VerticalLayout(sp,pad,align))
    elif t=="horizontal": obj.add_component(HorizontalLayout(sp,pad,align))
    elif t=="grid": obj.add_component(GridLayout(layout.get("columns",2),sp,pad,layout.get("cell_size")))

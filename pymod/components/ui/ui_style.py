from __future__ import annotations
from dataclasses import dataclass, field, replace
import math

import pygame


def lerp(a, b, t):
    return a + (b - a) * t

def clamp(v, lo, hi):
    return max(lo, min(hi, v))

def lerp_colour(a, b, t):
    return (int(lerp(a[0], b[0], t)), int(lerp(a[1], b[1], t)),
            int(lerp(a[2], b[2], t)),
            int(lerp(a[3] if len(a) > 3 else 255, b[3] if len(b) > 3 else 255, t)))


@dataclass
class Shadow:
    color: tuple = (0, 0, 0, 120)
    offset: tuple = (0, 4)
    blur: int = 12
    spread: int = 0
    enabled: bool = False


@dataclass
class Border:
    color: tuple = (255, 255, 255, 255)
    width: int = 0
    enabled: bool = False


@dataclass
class GradientStop:
    color: tuple = (255, 255, 255, 255)
    pos: float = 0.0            # 0..1 along the gradient


@dataclass
class Gradient:
    """Multi-stop gradient. type 'linear' uses angle (degrees, 0 = left→right,
    90 = top→bottom). type 'radial' ignores angle and runs centre→edge."""
    stops: list = field(default_factory=lambda: [GradientStop((255,255,255,255), 0.0),
                                                 GradientStop((200,200,200,255), 1.0)])
    type: str = "linear"
    angle: float = 90.0
    enabled: bool = False

    def colour_at(self, t: float):
        """Sample the gradient at t in [0,1] by interpolating between stops."""
        stops = sorted(self.stops, key=lambda s: s.pos)
        if t <= stops[0].pos:
            return stops[0].color
        if t >= stops[-1].pos:
            return stops[-1].color
        for i in range(len(stops) - 1):
            a, b = stops[i], stops[i + 1]
            if a.pos <= t <= b.pos:
                span = b.pos - a.pos
                lt = 0.0 if span == 0 else (t - a.pos) / span
                return lerp_colour(a.color, b.color, lt)
        return stops[-1].color


@dataclass
class Style:
    color: tuple = (60, 60, 70, 255)
    corner_radius: int = 6
    opacity: int = 255
    scale: float = 1.0
    offset: tuple = (0, 0)
    border: Border = field(default_factory=Border)
    shadow: Shadow = field(default_factory=Shadow)
    gradient: Gradient = field(default_factory=Gradient)
    text_color: tuple = (255, 255, 255, 255)

    def blend(self, other: Style, t: float) -> Style:
        if t <= 0: return self
        if t >= 1: return other
        return Style(
            color=lerp_colour(self.color, other.color, t),
            corner_radius=int(lerp(self.corner_radius, other.corner_radius, t)),
            opacity=int(lerp(self.opacity, other.opacity, t)),
            scale=lerp(self.scale, other.scale, t),
            offset=(lerp(self.offset[0], other.offset[0], t),
                    lerp(self.offset[1], other.offset[1], t)),
            text_color=lerp_colour(self.text_color, other.text_color, t),
            border=Border(lerp_colour(self.border.color, other.border.color, t),
                          int(lerp(self.border.width, other.border.width, t)),
                          self.border.enabled or other.border.enabled),
            shadow=Shadow(lerp_colour(self.shadow.color, other.shadow.color, t),
                          (lerp(self.shadow.offset[0], other.shadow.offset[0], t),
                           lerp(self.shadow.offset[1], other.shadow.offset[1], t)),
                          int(lerp(self.shadow.blur, other.shadow.blur, t)),
                          int(lerp(self.shadow.spread, other.shadow.spread, t)),
                          self.shadow.enabled or other.shadow.enabled),
            # gradient: blend stop colours when stop counts match, else switch at t>0.5
            gradient=self._blend_gradient(other.gradient, t),
        )

    def _blend_gradient(self, other_grad, t):
        a, b = self.gradient, other_grad
        if len(a.stops) == len(b.stops):
            stops = [GradientStop(lerp_colour(sa.color, sb.color, t),
                                  lerp(sa.pos, sb.pos, t))
                     for sa, sb in zip(a.stops, b.stops)]
            return Gradient(stops, b.type, lerp(a.angle, b.angle, t),
                            a.enabled or b.enabled)
        return b if t > 0.5 else a

    def transformed_rect(self, base):
        if self.scale == 1.0 and self.offset == (0, 0):
            return base.copy()
        w, h = base.width * self.scale, base.height * self.scale
        cx, cy = base.centerx + self.offset[0], base.centery + self.offset[1]
        return pygame.Rect(cx - w/2, cy - h/2, w, h)

    def paint(self, surface, base_rect):
        rect = self.transformed_rect(base_rect)
        r = max(0, int(self.corner_radius))
        if self.shadow.enabled:
            self._paint_shadow(surface, rect, r)
        body = self._render_body(rect.size, r)
        if self.opacity < 255:
            body.set_alpha(self.opacity)
        surface.blit(body, rect.topleft)
        if self.border.enabled and self.border.width > 0:
            pygame.draw.rect(surface, self.border.color[:3], rect,
                             int(self.border.width), border_radius=r)
        return rect

    def render_body_surface(self, size, radius):
        """Public: get the fill as a surface (used by rotation path)."""
        return self._render_body(size, radius)

    def _paint_shadow(self, surface, rect, radius):
        sh = self.shadow
        layers = max(1, sh.blur)
        for i in range(layers, 0, -1):
            grow = int(sh.spread + i)
            a = int(sh.color[3] * (1 - i/layers) / max(1, layers) * 3)
            if a <= 0: continue
            lr = pygame.Rect(0, 0, rect.width + grow*2, rect.height + grow*2)
            layer = pygame.Surface(lr.size, pygame.SRCALPHA)
            pygame.draw.rect(layer, (*sh.color[:3], a), layer.get_rect(),
                             border_radius=radius + grow)
            surface.blit(layer, (rect.x + sh.offset[0] - grow, rect.y + sh.offset[1] - grow))

    def _render_body(self, size, radius):
        w, h = max(1, int(size[0])), max(1, int(size[1]))
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        if self.gradient.enabled:
            grad = (self._render_radial((w, h)) if self.gradient.type == "radial"
                    else self._render_linear((w, h)))
            mask = pygame.Surface((w, h), pygame.SRCALPHA)
            pygame.draw.rect(mask, (255, 255, 255, 255), mask.get_rect(), border_radius=radius)
            grad.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
            surf.blit(grad, (0, 0))
        else:
            pygame.draw.rect(surf, self.color, surf.get_rect(), border_radius=radius)
        return surf

    def _render_linear(self, size):
        w, h = size
        g = self.gradient
        ang = math.radians(g.angle)
        dx, dy = math.cos(ang), math.sin(ang)

        corners = [(0,0),(w,0),(0,h),(w,h)]
        projs = [cx*dx + cy*dy for cx,cy in corners]
        pmin, pmax = min(projs), max(projs)
        span = (pmax - pmin) or 1

        strip_res = max(2, int(min(256, max(w, h))))
        strip = [g.colour_at(i/(strip_res-1)) for i in range(strip_res)]
        arr = pygame.Surface((w, h), pygame.SRCALPHA)

        if abs(dy) >= abs(dx):
            for y in range(h):
                p = (0*dx + y*dy - pmin)/span
                arr_col = strip[int(clamp(p,0,1)*(strip_res-1))]
                pygame.draw.line(arr, arr_col, (0,y),(w,y))
        else:
            for x in range(w):
                p = (x*dx + 0*dy - pmin)/span
                arr_col = strip[int(clamp(p,0,1)*(strip_res-1))]
                pygame.draw.line(arr, arr_col, (x,0),(x,h))
        return arr

    def _render_radial(self, size):
        w, h = size
        g = self.gradient
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        cx, cy = w/2, h/2
        maxd = math.hypot(cx, cy) or 1
        # draw concentric rings outward-in for smoothness
        steps = max(8, int(maxd))
        for i in range(steps, 0, -1):
            t = i/steps
            col = g.colour_at(t)
            pygame.draw.circle(surf, col, (int(cx), int(cy)), int(maxd*t)+1)
        return surf


class StyleSet:
    def __init__(self, normal, hover=None, pressed=None, disabled=None, transition=0.12):
        self.normal = normal
        self.hover = hover or normal
        self.pressed = pressed or hover or normal
        self.disabled = disabled or normal
        self.transition = max(0.0, transition)
        self._blend = 0.0

    def resolve(self, state, dt):
        if state == "disabled":
            return self.disabled
        target = 1.0 if state in ("hover", "pressed") else 0.0
        if self.transition <= 0:
            self._blend = target
        else:
            step = dt / self.transition
            self._blend = min(target, self._blend + step) if self._blend < target \
                else max(target, self._blend - step)
        if state == "pressed":
            return self.normal.blend(self.pressed, self._blend)
        return self.normal.blend(self.hover, self._blend)


def _col(v, d=(0,0,0,255)):
    if v is None: return d
    return (v[0],v[1],v[2],255) if len(v)==3 else tuple(v)

def _gradient(d, base):
    if d is None: return base
    stops = d.get("stops")
    if stops:
        gs = [GradientStop(_col(s.get("color")), s.get("pos", i/(max(1,len(stops)-1))))
              for i, s in enumerate(stops)]
    else:
        # back-compat with v2 two-colour form
        gs = [GradientStop(_col(d.get("color_a"), (255,255,255,255)), 0.0),
              GradientStop(_col(d.get("color_b"), (200,200,200,255)), 1.0)]
    ang = d.get("angle", 90.0)
    if isinstance(ang, str):
        ang = 90.0 if ang == "vertical" else 0.0
    return Gradient(gs, d.get("type", "linear"), ang, d.get("enabled", True))

def build_style(d, base=None):
    s = replace(base) if base else Style()
    if "color" in d:
        s.color = _col(d["color"])
    if "corner_radius" in d:
        s.corner_radius = d["corner_radius"]
    if "opacity" in d:
        s.opacity = d["opacity"]
    if "scale" in d:
        s.scale = d["scale"]
    if "offset" in d:
        s.offset = tuple(d["offset"])
    if "text_color" in d:
        s.text_color = _col(d["text_color"])
    if "border" in d:
        b = d["border"]
        s.border = Border(_col(b.get("color"), s.border.color),
                          b.get("width", s.border.width), b.get("enabled", True))
    if "shadow" in d:
        sh = d["shadow"]
        s.shadow = Shadow(_col(sh.get("color"), s.shadow.color),
                         tuple(sh.get("offset", s.shadow.offset)),
                         sh.get("blur", s.shadow.blur), sh.get("spread", s.shadow.spread),
                         sh.get("enabled", True))
    if "gradient" in d:
        s.gradient = _gradient(d["gradient"], s.gradient)
    return s

def build_style_set(d):
    normal = build_style(d)
    st = d.get("states", {})
    hover = build_style(st["hover"], normal) if "hover" in st else None
    pressed = build_style(st["pressed"], hover or normal) if "pressed" in st else None
    disabled = build_style(st["disabled"], normal) if "disabled" in st else None
    return StyleSet(normal, hover, pressed, disabled, d.get("transition", 0.12))

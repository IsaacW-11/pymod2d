from __future__ import annotations

import pygame

import pymod
from .ui_rect import UIRect
from .ui_style import StyleSet, Style


def _rotate_blit(surface, body, center, rotation):
    """Blit `body` rotated `rotation` degrees about `center`."""
    if rotation % 360 == 0:
        surface.blit(body, (center[0] - body.get_width()/2,
                            center[1] - body.get_height()/2))
        return
    rot = pygame.transform.rotate(body, -rotation)
    rect = rot.get_rect(center=center)
    surface.blit(rot, rect.topleft)


class UIInteractive(pymod.Component):
    """Base for UI components that respond to mouse hover and clicks.

    The UIManager drives the state transitions. It calls the _on_* hooks when the mouse enters, leaves, presses, releases, or clicks this element.
    Widgets override the hooks they care about. `interactable` can be toggled to disable interaction without removing the component.

    Attributes:
        interactable: Whether this element responds to input at all.
        hovered: Whether the mouse is currently over this element.
        pressed: Whether the mouse button is currently held on this element.
    """

    def __init__(self):
        super().__init__()
        self.interactable: bool = True
        self.hovered: bool = False
        self.pressed: bool = False

    def _state(self):
        if not self.interactable:
            return "disabled"
        if self.pressed:
            return "pressed"
        if self.hovered:
            return "hover"
        return "normal"

    def _on_hover_enter(self) -> None:
        self.hovered = True
        self.on_hover_enter()

    def _on_hover_exit(self) -> None:
        self.hovered = False
        self.pressed = False
        self.on_hover_exit()

    def _on_press(self) -> None:
        self.pressed = True
        self.on_press()

    def _on_release(self) -> None:
        self.pressed = False
        self.on_release()

    def _on_click(self) -> None:
        self.on_click()

    # override these in widgets
    def on_hover_enter(self) -> None: ...
    def on_hover_exit(self) -> None: ...
    def on_press(self) -> None: ...
    def on_release(self) -> None: ...
    def on_click(self) -> None: ...

    def _rc(self):
        return self.owner.get_component(UIRect)
    def _rect(self) -> pygame.Rect:
        rc = self.owner.get_component(UIRect)
        return rc.rect if rc else pygame.Rect(0, 0, 0, 0)


"""
UI WIDGETS BELOW
"""


class UIImage(pymod.Component):
    """Draws a solid colour rectangle or an image filling its UIRect.

    Used for backgrounds, panels, and icons. If image_path is given it draws that image scaled to the rect; otherwise it fills with color.

    Attributes:
        color: RGBA or RGB fill colour, used when no image is set.
        image_path: Optional asset name/path to draw instead of a fill.
        corner_radius: Rounded corner radius in pixels, 0 for square.
    """

    def __init__(self, style_set=None, image_path=None):
        super().__init__()

        self.style_set=style_set or StyleSet(Style())
        self.image_path=image_path
        self._image=None

    def on_start(self):
        if self.image_path:
            self._image = pymod.assets.load_image(self.image_path)

    def draw_ui(self, surface):
        rc = self.owner.get_component(UIRect)
        if rc is None:
            return
        style = self.style_set.resolve("normal", pymod.time.unscaled_delta)
        rect = rc.rect
        body = style.render_body_surface(rect.size, max(0, int(style.corner_radius)))
        if self._image is not None:
            img=pygame.transform.smoothscale(self._image, rect.size)
            body.blit(img,(0,0))
        if style.opacity < 255:
            body.set_alpha(style.opacity)
        if style.shadow.enabled:
            style._paint_shadow(surface, rect, int(style.corner_radius))

        _rotate_blit(surface, body, rect.center, rc.rotation)

        if style.border.enabled and style.border.width>0 and rc.rotation%360==0:
            pygame.draw.rect(surface, style.border.color[:3], rect, int(style.border.width), border_radius=int(style.corner_radius))


class UIText(pymod.Component):
    """Draws text within its UIRect, with alignment.

    Attributes:
        text: The string to display.
        font_size: Font size in points.
        color: Text colour.
        font_path: Optional font asset; None uses the default font.
        align: Horizontal alignment: "left", "center", or "right".
        valign: Vertical alignment: "top", "middle", or "bottom".
        wrap: Whether to wrap text to the rect width.
    """

    def __init__(self, text="", font_size=24, color=(255, 255, 255),
                 font_path=None, align="center", valign="middle", wrap=False):
        super().__init__()
        self.text = text
        self.font_size = font_size
        self.color = color
        self.font_path = font_path
        self.align = align
        self.valign = valign
        self.wrap = wrap
        self._font = None

    def on_start(self):
        self._font = pymod.assets.load_font(self.font_path, self.font_size)

    def set_text(self, text: str):
        """Change the displayed text."""
        self.text = str(text)

    def draw_ui(self, surface):
        rc = self.owner.get_component(UIRect)
        if rc is None or self._font is None:
            return
        rect = rc.rect

        lines = self._wrap(rect.width) if self.wrap else [self.text]
        line_h = self._font.get_height()
        total_h = line_h * len(lines)

        # render to a surface so we can rotate
        buf=pygame.Surface(rect.size, pygame.SRCALPHA)
        y=(0 if self.valign=="top" else rect.height-total_h if self.valign=="bottom" else rect.height//2-total_h//2)

        for line in lines:
            rendered = self._font.render(line, True, self.color[:3])
            x = (0 if self.align == "left" else rect.width - rendered.get_width() if self.align == "right" else rect.width // 2 - rendered.get_width() // 2)
            surface.blit(rendered, (x, y))
            buf.blit(rendered,(x,y)); y+=line_h

    def _wrap(self, max_width):
        words = self.text.split(" ")
        lines, current = [], ""
        for word in words:
            test = f"{current} {word}".strip()
            if self._font.size(test)[0] <= max_width:
                current = test
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)
        return lines


class UIButton(UIInteractive):
    """A clickable button with a label and hover/press colour states.

    Calls its on_click_callback when clicked (press then release inside the button).
    The JSON loader wires this to an action function.

    Attributes:
        text: Button label.
        normal_color / hover_color / pressed_color: Background per state.
        text_color: Label colour.
        font_size: Label size.
        corner_radius: Rounded corners.
        on_click_callback: Called with no args when the button is clicked.
    """

    def __init__(self, style_set, text="Button", font_size=24, font_path=None, on_click_callback=None):
        super().__init__()
        self.style_set=style_set
        self.text=text
        self.font_size=font_size
        self.font_path=font_path
        self.on_click_callback=on_click_callback
        self._font=None

    def on_start(self):
        self._font = pymod.assets.load_font(self.font_path, self.font_size)

    def on_click(self):
        if self.on_click_callback:
            self.on_click_callback()

    def draw_ui(self, surface):
        rc = self._rc()
        if not rc:
            return

        style=self.style_set.resolve(self._state(), pymod.time.unscaled_delta)
        base=rc.rect
        trect=style.transformed_rect(base)
        body=style.render_body_surface(trect.size, max(0,int(style.corner_radius)))

        if self._font and self.text:
            label=self._font.render(self.text, True, style.text_color[:3])
            body.blit(label,(trect.width//2-label.get_width()//2, trect.height//2-label.get_height()//2))

        if style.opacity<255:
            body.set_alpha(style.opacity)

        if style.shadow.enabled:
            style._paint_shadow(surface, trect, int(style.corner_radius))

        _rotate_blit(surface, body, trect.center, rc.rotation)

        if style.border.enabled and style.border.width>0 and rc.rotation%360==0:
            pygame.draw.rect(surface, style.border.color[:3], trect, int(style.border.width), border_radius=int(style.corner_radius))


class UISlider(UIInteractive):
    """A horizontal slider for choosing a value in a range.

    Calls on_change_callback with the new value whenever it moves.

    Attributes:
        min_value / max_value: The value range.
        value: Current value, clamped to the range.
        track_color / fill_color / handle_color: Colours.
        on_change_callback: Called with the new float value on change.
    """

    def __init__(self, min_value=0.0, max_value=1.0, value=0.5,
                 track_color=(50, 50, 60), fill_color=(90, 140, 220),
                 handle_color=(230, 230, 235), on_change_callback=None):
        super().__init__()
        self.min_value = min_value
        self.max_value = max_value
        self.value = max(min_value, min(max_value, value))
        self.track_color = track_color
        self.fill_color = fill_color
        self.handle_color = handle_color
        self.on_change_callback = on_change_callback

    def _fraction(self):
        span = self.max_value - self.min_value
        return 0.0 if span == 0 else (self.value - self.min_value) / span

    def on_press(self):
        self._set()

    def update(self):
        # dragging: while held, keep updating from the mouse
        if self.pressed and pymod.input.mouse_held("left"):
            self._set()

    def _set(self):
        rect = self._rect()
        if rect.width == 0:
            return
        mx = pymod.Game.get().screen.window_to_render_coordinates(pymod.input.mouse_position)[0]
        frac = max(0.0, min(1.0, (mx - rect.left) / rect.width))
        new_value = self.min_value + frac * (self.max_value - self.min_value)
        if new_value != self.value:
            self.value = new_value
            if self.on_change_callback:
                self.on_change_callback(self.value)

    def draw_ui(self, surface):
        rect = self._rect()
        cy = rect.centery
        pygame.draw.rect(surface,self.track_color,(rect.left,cy-3,rect.width,6),border_radius=3)

        fill_w = int(rect.width * self._fraction())
        if fill_w:
            pygame.draw.rect(surface,self.fill_color,(rect.left,cy-3,fill_w,6),border_radius=3)

        r=12 if self.hovered else 10
        pygame.draw.circle(surface,self.handle_color,(rect.left+fill_w,cy),r)


class UIToggle(UIInteractive):
    """A checkbox / on-off toggle.

    Calls on_change_callback with the new bool state when toggled.

    Attributes:
        value: Current on/off state.
        box_color / check_color: Colours.
        on_change_callback: Called with the new bool on toggle.
    """

    def __init__(self, value=False, box_color=(50, 50, 60),
                 check_color=(90, 200, 120), on_change_callback=None):
        super().__init__()
        self.value = value
        self.box_color = box_color
        self.check_color = check_color
        self.on_change_callback = on_change_callback

    def on_click(self):
        self.value = not self.value
        if self.on_change_callback:
            self.on_change_callback(self.value)

    def draw_ui(self, surface):
        rect = self._rect()
        col=tuple(min(255,c+15) for c in self.box_color[:3]) if self.hovered else self.box_color
        pygame.draw.rect(surface,col,rect,border_radius=4)
        if self.value:
            pygame.draw.rect(surface,self.check_color,rect.inflate(-rect.width//3,-rect.height//3),border_radius=3)
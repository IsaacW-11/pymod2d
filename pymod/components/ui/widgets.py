from __future__ import annotations

import pygame

import pymod
from .ui_rect import UIRect


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

    def __init__(self, color=(255, 255, 255), image_path=None, corner_radius=0):
        super().__init__()
        self.color = color
        self.image_path = image_path
        self.corner_radius = corner_radius
        self._image = None

    def on_start(self):
        if self.image_path:
            self._image = pymod.assets.load_image(self.image_path)

    def draw_ui(self, surface):
        rc = self.owner.get_component(UIRect)
        if rc is None:
            return
        rect = rc.rect
        if self._image is not None:
            scaled = pygame.transform.smoothscale(self._image, rect.size)
            surface.blit(scaled, rect.topleft)
        else:
            if self.corner_radius > 0:
                pygame.draw.rect(surface, self.color, rect, border_radius=self.corner_radius)
            else:
                pygame.draw.rect(surface, self.color, rect)


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

        lines = self._wrap_lines(rect.width) if self.wrap else [self.text]
        line_h = self._font.get_height()
        total_h = line_h * len(lines)

        if self.valign == "top":
            y = rect.top
        elif self.valign == "bottom":
            y = rect.bottom - total_h
        else:
            y = rect.centery - total_h // 2

        for line in lines:
            rendered = self._font.render(line, True, self.color)
            if self.align == "left":
                x = rect.left
            elif self.align == "right":
                x = rect.right - rendered.get_width()
            else:
                x = rect.centerx - rendered.get_width() // 2
            surface.blit(rendered, (x, y))
            y += line_h

    def _wrap_lines(self, max_width):
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

    def __init__(self, text="Button", font_size=24,
                 normal_color=(60, 60, 70), hover_color=(80, 80, 95),
                 pressed_color=(45, 45, 55), text_color=(255, 255, 255),
                 corner_radius=6, on_click_callback=None):
        super().__init__()
        self.text = text
        self.font_size = font_size
        self.normal_color = normal_color
        self.hover_color = hover_color
        self.pressed_color = pressed_color
        self.text_color = text_color
        self.corner_radius = corner_radius
        self.on_click_callback = on_click_callback
        self._font = None

    def on_start(self):
        self._font = pymod.assets.load_font(None, self.font_size)

    def on_click(self):
        if self.on_click_callback:
            self.on_click_callback()

    def draw_ui(self, surface):
        rect = self._rect()
        if self.pressed:
            color = self.pressed_color
        elif self.hovered:
            color = self.hover_color
        else:
            color = self.normal_color

        pygame.draw.rect(surface, color, rect, border_radius=self.corner_radius)

        if self._font and self.text:
            label = self._font.render(self.text, True, self.text_color)
            surface.blit(label, (rect.centerx - label.get_width() // 2,
                                 rect.centery - label.get_height() // 2))


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
        self._set_from_mouse()

    def update(self):
        # dragging: while held, keep updating from the mouse
        if self.pressed and pymod.input.mouse_held("left"):
            self._set_from_mouse()

    def _set_from_mouse(self):
        rect = self._rect()
        if rect.width == 0:
            return
        mx = pymod.Game.get().screen.window_to_render_coordinates(
            pymod.input.mouse_position
        )[0]
        frac = max(0.0, min(1.0, (mx - rect.left) / rect.width))
        new_value = self.min_value + frac * (self.max_value - self.min_value)
        if new_value != self.value:
            self.value = new_value
            if self.on_change_callback:
                self.on_change_callback(self.value)

    def draw_ui(self, surface):
        rect = self._rect()
        cy = rect.centery
        track = pygame.Rect(rect.left, cy - 3, rect.width, 6)
        pygame.draw.rect(surface, self.track_color, track, border_radius=3)

        fill_w = int(rect.width * self._fraction())
        if fill_w > 0:
            fill = pygame.Rect(rect.left, cy - 3, fill_w, 6)
            pygame.draw.rect(surface, self.fill_color, fill, border_radius=3)

        hx = rect.left + fill_w
        pygame.draw.circle(surface, self.handle_color, (hx, cy), 10)


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
        pygame.draw.rect(surface, self.box_color, rect, border_radius=4)
        if self.value:
            inset = rect.inflate(-rect.width // 3, -rect.height // 3)
            pygame.draw.rect(surface, self.check_color, inset, border_radius=3)
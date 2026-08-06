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
        body = style.render_body_surface(rect.size, max(0, int(style.corner_radius))).copy()
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
        if not rc or not self._font:
            return
        rect = rc.rect
        lines = self._wrap(rect.width) if self.wrap else [self.text]
        lh = self._font.get_height()
        total = lh * len(lines)
        # draw upright into a buffer at LOCAL coords, then place by rect
        buf = pygame.Surface(rect.size, pygame.SRCALPHA)
        y = (0 if self.valign == "top"
             else rect.height - total if self.valign == "bottom"
             else rect.height // 2 - total // 2)
        for line in lines:
            r = self._font.render(line, True, self.color[:3])
            x = (0 if self.align == "left"
                 else rect.width - r.get_width() if self.align == "right"
                 else rect.width // 2 - r.get_width() // 2)
            buf.blit(r, (x, y))
            y += lh
        _rotate_blit(surface, buf, rect.center, rc.rotation)

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
        body = style.render_body_surface(trect.size, max(0, int(style.corner_radius))).copy()

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

class UIProgressBar(pymod.Component):
    """A progress meter. Set value from 0-1. Fill can be a solid colour or gradient (via a StyleSet on the fill)."""
    def __init__(self, value=0.5, track_color=(40,44,56), fill_color=(90,180,140), corner_radius=6, fill_style=None):
        super().__init__()
        self.value=value; self.track_color=track_color; self.fill_color=fill_color
        self.corner_radius=corner_radius; self.fill_style=fill_style

    def draw_ui(self, surface):
        rc = self.owner.get_component(UIRect)
        if not rc:
            return
        rect = rc.rect
        r = int(self.corner_radius)
        buf = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(buf, self.track_color, buf.get_rect(), border_radius=r)
        fw = int(rect.width * max(0.0, min(1.0, self.value)))
        if fw > 0:
            frect = pygame.Rect(0, 0, fw, rect.height)
            if self.fill_style:
                st = self.fill_style.resolve("normal", pymod.time.unscaled_delta)
                buf.blit(st.render_body_surface(frect.size, r), (0, 0))
            else:
                pygame.draw.rect(buf, self.fill_color, frect, border_radius=r)
        _rotate_blit(surface, buf, rect.center, rc.rotation)

class UIDivider(pymod.Component):
    """A separator line, horizontal or vertical, centred in its rect."""
    def __init__(self, color=(70,78,94), thickness=2, orientation="horizontal"):
        super().__init__()
        self.color=color
        self.thickness=thickness
        self.orientation=orientation

    def draw_ui(self, surface):
        rc=self.owner.get_component(UIRect)
        if not rc:
            return
        rect = rc.rect
        buf = pygame.Surface(rect.size, pygame.SRCALPHA)
        t = max(1, int(self.thickness))
        if self.orientation == "horizontal":
            y = rect.height // 2
            pygame.draw.line(buf, self.color, (0, y), (rect.width, y), t)
        else:
            x = rect.width // 2
            pygame.draw.line(buf, self.color, (x, 0), (x, rect.height), t)
        _rotate_blit(surface, buf, rect.center, rc.rotation)

class UIIcon(pymod.Component):
    """A shape icon (circle/square/triangle/diamond) or an image icon."""
    def __init__(self, shape="circle", color=(220,225,235), image_path=None):
        super().__init__()
        self.shape=shape; self.color=color; self.image_path=image_path; self._image=None

    def on_start(self):
        if self.image_path: self._image=pymod.assets.load_image(self.image_path)

    def draw_ui(self, surface):
        rc=self.owner.get_component(UIRect)
        if not rc:
            return
        rect = rc.rect
        buf = pygame.Surface(rect.size, pygame.SRCALPHA)
        if self._image is not None:
            buf.blit(pygame.transform.smoothscale(self._image, rect.size), (0, 0))
        else:
            c = self.color
            w, h = rect.width, rect.height
            cx, cy = w // 2, h // 2
            r = min(w, h) // 2
            if self.shape == "circle":
                pygame.draw.circle(buf, c, (cx, cy), r)
            elif self.shape == "square":
                pygame.draw.rect(buf, c, buf.get_rect().inflate(-4, -4), border_radius=4)
            elif self.shape == "triangle":
                pygame.draw.polygon(buf, c, [(cx, cy - r), (cx - r, cy + r), (cx + r, cy + r)])
            elif self.shape == "diamond":
                pygame.draw.polygon(buf, c, [(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)])
        _rotate_blit(surface, buf, rect.center, rc.rotation)

class UITextInput(UIInteractive):
    """Typed text entry. Focus on click; types via pymod.input text events."""
    def __init__(self, style_set, text="", placeholder="", font_size=20, font_path=None,
                 max_length=64, on_change_callback=None):
        super().__init__()
        self.style_set=style_set
        self.text=text
        self.placeholder=placeholder
        self.font_size=font_size
        self.font_path=font_path
        self.max_length=max_length
        self.on_change_callback=on_change_callback
        self.focused=False
        self._font=None
        self._caret_t=0.0

    def on_start(self):
        self._font=pymod.assets.load_font(self.font_path, self.font_size)

    def on_click(self):
        self.focused=True

    def _defocus(self):
        self.focused=False

    def type_char(self, ch):
        if len(self.text)<self.max_length:
            self.text+=ch
            if self.on_change_callback: self.on_change_callback(self.text)

    def backspace(self):
        self.text=self.text[:-1]
        if self.on_change_callback: self.on_change_callback(self.text)

    def draw_ui(self, surface):
        self._caret_t += pymod.time.unscaled_delta
        rc=self.owner.get_component(UIRect)
        if not rc or not self._font: return
        state="hover" if self.focused else self._state()
        style=self.style_set.resolve(state, pymod.time.unscaled_delta)
        rect=style.paint(surface, rc.rect)
        show=self.text if self.text else self.placeholder
        col=style.text_color[:3] if self.text else (140,146,158)
        r=self._font.render(show, True, col)
        surface.blit(r,(rect.left+10, rect.centery-r.get_height()//2))
        if self.focused and int(self._caret_t*2)%2==0:
            cx=rect.left+12+(self._font.size(self.text)[0] if self.text else 0)
            pygame.draw.line(surface,(220,225,235),(cx,rect.centery-self.font_size//2),(cx,rect.centery+self.font_size//2),2)

class UIRadioGroup(pymod.Component):
    """A vertical set of options; one selected at a time. Options are strings. Emits the selected index via callback."""
    def __init__(self, options=None, selected=0, dot_color=(90,170,240), text_color=(220,226,236), font_size=20, font_path=None, on_change_callback=None):
        super().__init__()
        self.options=options or ["Option A","Option B"]
        self.selected=selected
        self.dot_color=dot_color
        self.text_color=text_color
        self.font_size=font_size
        self.font_path=font_path
        self.on_change_callback=on_change_callback
        self._font=None

    def on_start(self):
        self._font=pymod.assets.load_font(self.font_path, self.font_size)

    def update(self):
        if not pymod.input.mouse_pressed("left"):
            return
        rc=self.owner.get_component(UIRect)
        if not rc:
            return
        mp=pymod.screen.window_to_render_coordinates(pymod.input.mouse_position)
        rect=rc.rect; row_h=rect.height/max(1,len(self.options))
        for i in range(len(self.options)):
            rr=pygame.Rect(rect.left,rect.top+i*row_h,rect.width,row_h)
            if rr.collidepoint(mp):
                if i!=self.selected:
                    self.selected=i
                    if self.on_change_callback: self.on_change_callback(i)

    def draw_ui(self, surface):
        rc=self.owner.get_component(UIRect)
        if not rc or not self._font:
            return
        rect=rc.rect; row_h=rect.height/max(1,len(self.options))
        for i,opt in enumerate(self.options):
            cy=int(rect.top+i*row_h+row_h/2); cx=rect.left+12
            pygame.draw.circle(surface,(90,96,110),(cx,cy),8,2)
            if i==self.selected: pygame.draw.circle(surface,self.dot_color,(cx,cy),4)
            r=self._font.render(opt,True,self.text_color[:3])
            surface.blit(r,(cx+18,cy-r.get_height()//2))

class UIDropdown(UIInteractive):
    """A select box. Click toggles a list of options drawn below it."""
    def __init__(self, style_set, options=None, selected=0, font_size=20, font_path=None, on_change_callback=None):
        super().__init__()
        self.style_set=style_set
        self.options=options or ["One","Two","Three"]
        self.selected=selected
        self.font_size=font_size; self.font_path=font_path
        self.on_change_callback=on_change_callback
        self.open=False
        self._font=None

    def on_start(self):
        self._font=pymod.assets.load_font(self.font_path, self.font_size)

    def on_click(self):
        self.open=not self.open

    def update(self):
        if self.open and pymod.input.mouse_pressed("left"):
            rc=self.owner.get_component(UIRect)
            mp=pymod.screen.window_to_render_coordinates(pymod.input.mouse_position)
            rect=rc.rect
            row_h=rect.height
            for i in range(len(self.options)):
                rr=pygame.Rect(rect.left,rect.bottom+i*row_h,rect.width,row_h)
                if rr.collidepoint(mp):
                    self.selected=i; self.open=False
                    if self.on_change_callback:
                        self.on_change_callback(i)
                    return
            if not self.hovered: self.open=False
    def draw_ui(self, surface):
        rc=self.owner.get_component(UIRect)
        if not rc or not self._font:
            return
        style=self.style_set.resolve(self._state(), pymod.time.unscaled_delta)
        rect=style.paint(surface, rc.rect)
        label=self._font.render(self.options[self.selected], True, style.text_color[:3])
        surface.blit(label,(rect.left+10, rect.centery-label.get_height()//2))
        # arrow
        ax=rect.right-18; ay=rect.centery
        pygame.draw.polygon(surface,style.text_color[:3],[(ax-5,ay-3),(ax+5,ay-3),(ax,ay+4)])

    def draw_ui_overlay(self, surface):
        if not self.open or not self._font: return
        rc=self.owner.get_component(UIRect)
        if not rc: return
        rect=rc.rect; row_h=rect.height
        for i,opt in enumerate(self.options):
            rr=pygame.Rect(rect.left,rect.bottom+i*row_h,rect.width,row_h)
            pygame.draw.rect(surface,(28,32,44),rr)
            pygame.draw.rect(surface,(50,56,70),rr,1)
            r=self._font.render(opt,True,(220,226,236))
            surface.blit(r,(rr.left+10,rr.centery-r.get_height()//2))

class UITooltip(pymod.Component):
    """Shows a text bubble after the mouse hovers the owner for `delay` sec.

    Attach alongside an interactive element (or any element with a UIRect).
    """
    def __init__(self, text="", delay=0.5, font_size=16, font_path=None, bg=(20,24,32), fg=(230,235,244)):
        super().__init__()
        self.text=text
        self.delay=delay
        self.font_size=font_size
        self.font_path=font_path
        self.bg=bg
        self.fg=fg
        self._hover_t=0.0
        self._font=None

    def on_start(self):
        self._font=pymod.assets.load_font(self.font_path, self.font_size)

    def update(self):
        rc=self.owner.get_component(UIRect)
        if not rc:
            return
        mp=pymod.screen.window_to_render_coordinates(pymod.input.mouse_position)
        if rc.contains_point(*mp):
            self._hover_t+=pymod.time.unscaled_delta
        else:
            self._hover_t=0.0

    def draw_ui_overlay(self, surface):
        if self._hover_t<self.delay or not self._font or not self.text:
            return
        rc=self.owner.get_component(UIRect)
        rect=rc.rect
        r=self._font.render(self.text, True, self.fg[:3])
        pad=8; bw,bh=r.get_width()+pad*2, r.get_height()+pad*2
        bx,by=rect.centerx-bw//2, rect.top-bh-8
        pygame.draw.rect(surface,self.bg,(bx,by,bw,bh),border_radius=6)
        surface.blit(r,(bx+pad,by+pad))

class UIScrollView(pymod.Component):
    """A clipping container with a vertical scroll offset. Children are laid out normally but drawn through a clip + offset.

    Scroll with the wheel while hovered. (The UIManager draws children; this shifts + clips them.)
    """
    def __init__(self, content_height=0, bg_color=(22,26,36), corner_radius=8):
        super().__init__()
        self.content_height=content_height
        self.bg_color=bg_color
        self.corner_radius=corner_radius
        self.scroll_offset=0.0

    def update(self):
        rc=self.owner.get_component(UIRect)
        if not rc: return
        mp=pymod.screen.window_to_render_coordinates(pymod.input.mouse_position)
        if rc.contains_point(*mp):
            w=pymod.input.mouse_wheel
            if w:
                self.scroll_offset=max(0.0, min(max(0,self.content_height-rc.rect.height),
                                                self.scroll_offset - w*30))
    def draw_ui(self, surface):
        rc=self.owner.get_component(UIRect)
        if not rc:
            return
        pygame.draw.rect(surface,self.bg_color,rc.rect,border_radius=self.corner_radius)
        # scrollbar
        if self.content_height>rc.rect.height:
            track=rc.rect
            ratio=track.height/self.content_height
            bar_h=max(24,int(track.height*ratio))
            max_off=self.content_height-track.height
            t=self.scroll_offset/max_off if max_off else 0
            by=track.top+int((track.height-bar_h)*t)
            pygame.draw.rect(surface,(70,78,94),(track.right-6,by,4,bar_h),border_radius=2)

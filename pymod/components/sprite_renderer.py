from __future__ import annotations
from enum import Enum, auto

import pygame

import pymod


class Anchor(Enum):
    """Pivot point used when positioning and rotating a sprite.

    The anchor determines which point of the image aligns with the GameObject's x, y world position, and is also the pivot point
    used for rotation.

    TOP_LEFT matches pygame's natural blit behaviour. CENTER is usually what you want for characters and anything that rotates.
    """
    TOP_LEFT = auto()
    TOP_CENTER = auto()
    TOP_RIGHT = auto()
    CENTER_LEFT = auto()
    CENTER = auto()
    CENTER_RIGHT = auto()
    BOTTOM_LEFT = auto()
    BOTTOM_CENTER = auto()
    BOTTOM_RIGHT = auto()


class SpriteRenderer(pymod.Component):
    """Draws a static image at the owner GameObject's world position.

    Supports flipping, rotation, scaling, tinting, opacity, an anchor point, a visual-only draw offset, and off-screen culling.

    The owner's x and y are treated as the world position. The anchor determines which point of the sprite aligns to that position.
    The offset is an additional purely-visual shift that does not affect the owner's real position.

    Attributes:
        image_path: Registered asset name or file path for the source image.
        anchor: Which point of the sprite aligns to the owner's position.
        offset: Purely visual (x, y) shift in world units, added before drawing.
        flip_x: Whether to flip the sprite horizontally.
        flip_y: Whether to flip the sprite vertically.
        rotation: Rotation in degrees, clockwise, around the anchor point.
        scale: Uniform scale multiplier, or an (sx, sy) tuple for non-uniform.
        opacity: Alpha from 0 (transparent) to 255 (opaque).
        tint: RGB tuple multiplied over the image, or None for no tint.
        visible: Whether the sprite is drawn at all.
        cull: Whether to skip drawing when fully outside the camera view.
        ignore_camera: If True, draws at raw screen coordinates ignoring the camera transform.
        smooth: If true, bilinear smooth, otherwise crisp pixel scale
    """

    def __init__(
        self,
        image_path: str | pygame.surface | None = None,
        anchor: Anchor = Anchor.TOP_LEFT,
        offset: tuple[float, float] = (0.0, 0.0),
        flip_x: bool = False,
        flip_y: bool = False,
        rotation: float = 0.0,
        scale: float | tuple[float, float] = 1.0,
        opacity: int = 255,
        tint: tuple[int, int, int] | None = None,
        visible: bool = True,
        cull: bool = True,
        ignore_camera: bool = False,
        smooth: bool = False,
    ):
        """Initialise the sprite renderer.

        Args:
            image_path: Registered asset name or direct file path. Should be None if you intend to call set_surface manually.
            anchor: Pivot point for positioning and rotation. Defaults to TOP_LEFT.
            offset: Visual-only (x, y) shift in world units. Defaults to (0, 0).
            flip_x: Whether to flip horizontally. Defaults to False.
            flip_y: Whether to flip vertically. Defaults to False.
            rotation: Initial rotation in degrees. Defaults to 0.
            scale: Uniform scale, or (sx, sy) for non-uniform. Defaults to 1.0.
            opacity: Initial opacity, 0-255. Defaults to 255.
            tint: Initial RGB tint, or None. Defaults to None.
            visible: Whether the sprite starts visible. Defaults to True.
            cull: Whether to skip drawing when off-screen. Defaults to True.
            ignore_camera: Whether to draw in raw screen space. Defaults to False.
            smooth: Whether to use bilinear smoothing. Defaults to False.
        """
        super().__init__()

        if isinstance(image_path, pygame.Surface):
            self.image_path = None
            self._original_image = image_path
        else:
            self.image_path = image_path
            self._original_image = None

        self.image_path: str | None = image_path
        self.anchor: Anchor = anchor
        self.offset: tuple[float, float] = offset
        self.flip_x: bool = flip_x
        self.flip_y: bool = flip_y
        self.rotation: float = rotation
        self._scale: tuple[float, float] = self._normalize_scale(scale)
        self.opacity: int = opacity
        self.tint: tuple[int, int, int] | None = tint
        self.visible: bool = visible
        self.cull: bool = cull
        self.ignore_camera: bool = ignore_camera
        self.smooth: bool = smooth

        self._cached_image: pygame.Surface | None = None
        self._cache_key: tuple | None = None

    # IMAGE SOURCE
    def set_image(self, image_path: str) -> None:
        """Change the source image by registered name or path.

        Args:
            image_path: Registered asset name or direct file path.
        """
        self.image_path = image_path
        self._original_image = pymod.assets.load_image(image_path)
        self._invalidate_cache()

    def set_surface(self, surface: pygame.Surface) -> None:
        """Set the source image directly from a surface, bypassing AssetManager.

        Use for procedurally generated images or pre-sliced spritesheet frames that already exist as surfaces.

        Args:
            surface: The pygame.Surface to render.
        """
        self.image_path = None
        self._original_image = surface
        self._invalidate_cache()

    @property
    def source_surface(self) -> pygame.Surface | None:
        """The untransformed source surface, or None if not yet loaded.

        This is the shared cached surface from AssetManager. Do NOT modify it in place.
        Use it for read-only access.
        """
        return self._original_image

    # TRANSFORM PROPERTIES
    @property
    def scale(self) -> tuple[float, float]:
        """Current scale as an (sx, sy) tuple."""
        return self._scale

    @scale.setter
    def scale(self, value: float | tuple[float, float]) -> None:
        self._scale = self._normalize_scale(value)

    @property
    def width(self) -> int:
        """Current rendered width in pixels, after scaling."""
        if self._original_image is None:
            return 0
        return int(self._original_image.get_width() * self._scale[0])

    @property
    def height(self) -> int:
        """Current rendered height in pixels, after scaling."""
        if self._original_image is None:
            return 0
        return int(self._original_image.get_height() * self._scale[1])

    def get_world_rect(self) -> pygame.Rect:
        """Get the sprite's bounding rect in world space, as currently configured.

        Accounts for scale, anchor, and offset, but not rotation.

        Returns:
            A pygame.Rect positioned and sized in world coordinates.
        """
        w = self.width
        h = self.height
        ax, ay = self._anchor_offset(w, h)
        world_x = self.owner.x + self.offset[0] - ax
        world_y = self.owner.y + self.offset[1] - ay
        return pygame.Rect(world_x, world_y, w, h)

    # LIFECYCLE
    def on_start(self) -> None:
        if self.image_path is not None and self._original_image is None:
            self._original_image = pymod.assets.load_image(self.image_path)

    def draw(self) -> None:
        if not self.visible or self._original_image is None:
            return

        image = self._get_processed_image()
        w, h = image.get_size()
        ax, ay = self._anchor_offset(w, h)

        world_x = self.owner.x + self.offset[0] - ax
        world_y = self.owner.y + self.offset[1] - ay

        camera = None if self.ignore_camera else pymod.Game.get().camera.active

        if camera is not None:
            if self.cull and not self._is_on_screen(camera, w, h):
                return
            screen_pos = camera.world_to_screen(world_x, world_y)
        else:
            screen_pos = (world_x, world_y)

        pymod.Game.get().screen.render_surface.blit(image, screen_pos)

    # INTERNAL
    def _normalize_scale(self, value: float | tuple[float, float]) -> tuple[float, float]:
        if isinstance(value, (int, float)):
            return (float(value), float(value))
        return (float(value[0]), float(value[1]))

    def _invalidate_cache(self) -> None:
        self._cached_image = None
        self._cache_key = None

    def _get_processed_image(self) -> pygame.Surface:
        """Build and cache the final image after all transforms.

        Rebuilds only when a transform property changes since the last draw, rather than every frame, so static sprites cost almost
        nothing per frame.
        """
        cache_key = (
            self.flip_x, self.flip_y, self.rotation,
            self._scale, self.opacity, self.tint,
        )

        if self._cached_image is not None and cache_key == self._cache_key:
            return self._cached_image

        image = self._original_image

        if self.flip_x or self.flip_y:
            image = pygame.transform.flip(image, self.flip_x, self.flip_y)

        if self._scale != (1.0, 1.0):
            w = max(1, int(image.get_width() * self._scale[0]))
            h = max(1, int(image.get_height() * self._scale[1]))
            if self.smooth:
                image = pygame.transform.smoothscale(image, (w, h))
            else:
                image = pygame.transform.scale(image, (w, h))

        if self.rotation != 0.0:
            image = pygame.transform.rotate(image, -self.rotation)

        if self.tint is not None:
            image = image.copy()
            image.fill(self.tint, special_flags=pygame.BLEND_RGB_MULT)

        if self.opacity != 255:
            if self.tint is None:
                image = image.copy()
            image.set_alpha(self.opacity)

        self._cached_image = image
        self._cache_key = cache_key
        return image

    def _anchor_offset(self, width: int, height: int) -> tuple[float, float]:
        """Compute the pixel offset from the owner position for the current anchor."""
        offsets = {
            Anchor.TOP_LEFT:      (0,          0),
            Anchor.TOP_CENTER:    (width / 2,  0),
            Anchor.TOP_RIGHT:     (width,      0),
            Anchor.CENTER_LEFT:   (0,          height / 2),
            Anchor.CENTER:        (width / 2,  height / 2),
            Anchor.CENTER_RIGHT:  (width,      height / 2),
            Anchor.BOTTOM_LEFT:   (0,          height),
            Anchor.BOTTOM_CENTER: (width / 2,  height),
            Anchor.BOTTOM_RIGHT:  (width,      height),
        }
        return offsets[self.anchor]

    def _is_on_screen(self, camera, width: int, height: int) -> bool:
        """Check whether the sprite's screen rect intersects the camera viewport.

        Uses the already-computed transformed image size so culling accounts for scale and rotation.
        """
        surface_size = pymod.Game.get().screen.render_size
        viewport_rect = camera.get_viewport_rect(surface_size)

        world_x = self.owner.x + self.offset[0]
        world_y = self.owner.y + self.offset[1]
        center_screen = camera.world_to_screen(world_x, world_y)

        # generous bounds using the full transformed size as a radius,
        # avoids popping when a rotated sprite's corners extend past center
        half_diag = max(width, height)
        sprite_rect = pygame.Rect(
            center_screen[0] - half_diag,
            center_screen[1] - half_diag,
            half_diag * 2,
            half_diag * 2,
        )
        return sprite_rect.colliderect(viewport_rect)
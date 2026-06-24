from __future__ import annotations
import os
import warnings

import pygame

from ..utils.exceptions import AssetNotFound

class AssetManager:
    """Manages loading and caching of all game assets.

        Automatically registers all assets in a root folder, and puts each one under a name you
        can load by later. You can also bypass the registry entirely and load
        any file by its direct path.

        Every load method caches its result, so loading the same asset from
        multiple components only reads the file from disk once.

        Supported categories:
            Images       — .png, .jpg, .jpeg, .bmp, .gif, .tga, .webp
            Audio        — .wav, .ogg, .mp3, .flac
            Fonts        — .ttf, .otf

        Attributes:
            IMAGE_EXTENSIONS: Set of recognised image file extensions.
            AUDIO_EXTENSIONS: Set of recognised audio file extensions.
            FONT_EXTENSIONS: Set of recognised font file extensions.
            _asset_root: Root directory that gets scanned for assets.
            _image_paths: Maps registered names to image file paths.
            _audio_paths: Maps registered names to audio file paths.
            _font_paths: Maps registered names to font file paths.
            _image_cache: Cache of loaded pygame.Surface objects, keyed by path.
            _sound_cache: Cache of loaded pygame.mixer.Sound objects, keyed by path.
            _font_cache: Cache of loaded pygame.font.Font objects, keyed by (path, size).
            _spritesheet_cache: Cache of sliced spritesheet frames, keyed by (path, frame_width, frame_height, margin, spacing).
        """
    IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".tga", ".webp"}
    AUDIO_EXTENSIONS = {".wav", ".ogg", ".mp3", ".flac"}
    FONT_EXTENSIONS = {".ttf", ".otf"}

    def __init__(self, asset_root: str = "assets", auto_scan: bool = True, preload = False):
        """Initialise the asset manager.

        Args:
            asset_root: Root directory to scan for assets. Defaults to 'assets'.
            auto_scan: Whether to scan asset_root immediately on creation.
            preload: Whether to load every discovered image and sound immediately after scanning, rather than lazily on first access.
        """

        self._asset_root = asset_root

        self._image_paths: dict[str, str] = {}
        self._audio_paths: dict[str, str] = {}
        self._font_paths: dict[str, str] = {}

        self._image_cache: dict[str, pygame.Surface] = {}
        self._sound_cache: dict[str, pygame.mixer.Sound] = {}
        self._font_cache: dict[tuple[str, int], pygame.font.Font] = {}
        self._spritesheet_cache: dict[tuple, list[pygame.Surface]] = {}

        if auto_scan:
            self.scan_directory(asset_root)

        if preload:
            self.preload_all()

    # SCANNING
    def scan_directory(self, root: str = None):
        """Scan a directory and register every recognised asset inside it.

        Walks every subfolder under root. Each file is registered under
        two keys where possible:
            - its path relative to root, without extension (always unique)
            - its filename alone, without extension (only if unique; the first file found claims the short name, others must
            be referenced by their full relative path)

        Args:
            root: Directory to scan. Defaults to the asset_root set at creation.
        """
        root = root or self._asset_root
        if not os.path.isdir(root):
            warnings.warn(f"Asset directory '{root}' does not exist. Skipping scan.")
            return

        for dirpath, _, filenames in os.walk(root):
            for filename in filenames:
                full_path = os.path.join(dirpath, filename)
                name, ext = os.path.splitext(filename) # gets the file extension (.png, etc), aswell as the file name
                ext = ext.lower()

                rel_path = os.path.relpath(full_path, root) # gets the relative path to the asset folder
                rel_key = os.path.splitext(rel_path)[0].replace(os.sep, "/") # formats relative path

                if ext in self.IMAGE_EXTENSIONS:
                    self._register(self._image_paths, rel_key, name, full_path)
                elif ext in self.AUDIO_EXTENSIONS:
                    self._register(self._audio_paths, rel_key, name, full_path)
                elif ext in self.FONT_EXTENSIONS:
                    self._register(self._font_paths, rel_key, name, full_path)

    def rescan(self):
        """Re-scan the asset root, picking up any newly added files.

        Does not clear existing caches. Already loaded assets keep their cached versions
        """
        self.scan_directory(self._asset_root)

    def _register(self, registry: dict[str, str], full_key: str, short_key: str, path: str):
        """Internal helper to register an asset under its full and short keys.

        Args:
            registry: The dict to register into (image/audio/font paths).
            full_key: Relative path key, always registered.
            short_key: Filename-only key, registered only if not already taken.
            path: Full file path on disk.
        """
        registry[full_key] = path
        if short_key not in registry:
            registry[short_key] = path
        # if short_key is already taken by a different file, the full path key above is still valid

    # IMAGES
    def load_image(self, name_or_path: str, convert_alpha: bool = True, colorkey: tuple[int, int, int] = None) -> pygame.Surface:
        """Load an image by registered name or direct file path.

        Cached after first load. Calling this again with the same
        resolved path returns the cached surface instantly.

        Warning:
            The returned surface is shared across every caller. Do not modify it in place (e.g. blitting onto it directly).
            Use surface.copy() first if you need a mutable version.

        Args:
            name_or_path: A registered asset name, or a direct file path.
            convert_alpha: Whether to call convert_alpha() for per-pixel transparency and faster blitting. Defaults to True.
            colorkey: RGB tuple to use as a transparent colorkey instead of per-pixel alpha. Ignored if convert_alpha is True
                      and the image already has an alpha channel.

        Returns:
            The loaded pygame.Surface.

        Raises:
            AssetNotFoundError: If the name or path cannot be resolved.
        """
        path = self._resolve_path(name_or_path, self._image_paths, "image")

        if path in self._image_cache:
            return self.image_cache[path]

        surface = pygame.image.load(path)

        if colorkey is not None:
            surface = surface.convert()
            surface.set_colorkey(colorkey)
        elif convert_alpha:
            surface = surface.convert_alpha()
        else:
            surface = surface.convert()

        self._image_cache[path] = surface
        return surface

    def load_spritesheet(self,
                         name_or_path: str,
                         frame_width: int,
                         frame_height: int,
                         margin: int = 0,
                         spacing: int = 0,) -> list[pygame.Surface]:
        """Load and slice a spritesheet into individual frames.

        Slices left to right, top to bottom, in a uniform grid.

        Args:
            name_or_path: A registered asset name, or a direct file path.
            frame_width: Width of each frame in pixels.
            frame_height: Height of each frame in pixels.
            margin: Pixels to skip from the edge of the sheet before slicing.
            spacing: Pixels of gap between frames.

        Returns:
            List of pygame.Surface frames, in reading order.

        Raises:
            AssetNotFoundError: If the name or path cannot be resolved.
        """
        path = self._resolve_path(name_or_path, self._image_paths, "image")
        cache_key = (path, frame_width, frame_height, margin, spacing)

        if cache_key in self._spritesheet_cache:
            return self._spritesheet_cache[cache_key]

        sheet = self.load_image(path)
        sheet_w, sheet_h = sheet.get_size()

        frames = []
        y = margin
        while y + frame_height <= sheet_h:
            x = margin
            while x + frame_width <= sheet_w:
                frame = sheet.subsurface(pygame.Rect(x, y, frame_width, frame_height)).copy()
                frames.append(frame)
                x += frame_width + spacing
            y += frame_height + spacing

        self._spritesheet_cache[cache_key] = frames
        return frames

    def unload_image(self, name_or_path: str):
        """Remove a specific image from the cache.

        Args:
            name_or_path: A registered asset name, or a direct file path.
        """
        path = self._resolve_path(name_or_path, self._image_paths, "image", strict=False)
        if path:
            self._image_cache.pop(path, None)

    def list_images(self) -> list[str]:
        """Get all registered image asset names.

        Returns:
            List of registered names, including both full-path and short keys.
        """
        return list(self._image_paths.keys())

    def has_image(self, name: str) -> bool:
        """Check if an image is registered under a given name.

        Args:
            name: The registered asset name to check.

        Returns:
            True if the name is registered.
        """
        return name in self._image_paths

    # AUDIO
    def load_sound(self, name_or_path: str) -> pygame.mixer.Sound:
        """Load a sound effect by registered name or direct file path.

        Use this for short sound effects. For background music,
        use AudioManager's play_music, which streams rather than
        loading the entire file into memory.

        Args:
            name_or_path: A registered asset name, or a direct file path.

        Returns:
            The loaded pygame.mixer.Sound.

        Raises:
            AssetNotFoundError: If the name or path cannot be resolved.
        """
        path = self._resolve_path(name_or_path, self._audio_paths, "audio")

        if path in self._sound_cache:
            return self._sound_cache[path]

        sound = pygame.mixer.Sound(path)

        self._sound_cache[path] = sound
        return sound

    def unload_sound(self, name_or_path: str) -> None:
        """Remove a specific sound from the cache.

        Args:
            name_or_path: A registered asset name, or a direct file path.
        """
        path = self._resolve_path(name_or_path, self._audio_paths, "audio", strict=False)
        if path:
            self._sound_cache.pop(path, None)

    def list_sounds(self) -> list[str]:
        """Get all registered audio asset names.

        Returns:
            List of registered names, including both full-path and short keys.
        """
        return list(self._audio_paths.keys())

    def has_sound(self, name: str) -> bool:
        """Check if a sound is registered under a given name.

        Args:
            name: The registered asset name to check.

        Returns:
            True if the name is registered.
        """
        return name in self._audio_paths

    def get_audio_path(self, name_or_path: str) -> str:
        """Resolve a registered audio name to its full file path.

        Useful for AudioManager.play_music, which needs a raw path
        rather than a loaded Sound object.

        Args:
            name_or_path: A registered asset name, or a direct file path.

        Returns:
            The resolved file path.

        Raises:
            AssetNotFoundError: If the name or path cannot be resolved.
        """
        return self._resolve_path(name_or_path, self._audio_paths, "audio")

    # FONTS
    def load_font(self, name_or_path: str | None, size: int = 24) -> pygame.font.Font:
        """Load a font by registered name or direct file path, at a given size.

        Pass None as the name to get pygame's built-in default font.

        Args:
            name_or_path: A registered asset name, a direct file path, or None for the default system font.
            size: Font size in points. Defaults to 24.

        Returns:
            The loaded pygame.font.Font.

        Raises:
            AssetNotFoundError: If the name or path cannot be resolved.
        """
        if name_or_path is None:
            cache_key = ("__default__", size)
            if cache_key not in self._font_cache:
                self._font_cache[cache_key] = pygame.font.Font(None, size)
            return self._font_cache[cache_key]

        path = self._resolve_path(name_or_path, self._font_paths, "font")
        cache_key = (path, size)

        if cache_key in self._font_cache:
            return self._font_cache[cache_key]

        font = pygame.font.Font(path, size)
        self._font_cache[cache_key] = font
        return font

    def unload_font(self, name_or_path: str, size: int = None) -> None:
        """Remove a specific font from the cache.

        Args:
            name_or_path: A registered asset name, or a direct file path.
            size: Specific size to unload. If None, unloads all sizes cached for this font.
        """
        path = self._resolve_path(name_or_path, self._font_paths, "font", strict=False)
        if not path:
            return
        if size is not None:
            self._font_cache.pop((path, size), None)
        else:
            keys_to_remove = [k for k in self._font_cache if k[0] == path]
            for key in keys_to_remove:
                del self._font_cache[key]

    def list_fonts(self) -> list[str]:
        """Get all registered font asset names.

        Returns:
            List of registered names, including both full-path and short keys.
        """
        return list(self._font_paths.keys())

    def has_font(self, name: str) -> bool:
        """Check if a font is registered under a given name.

        Args:
            name: The registered asset name to check.

        Returns:
            True if the name is registered.
        """
        return name in self._font_paths

    def preload_all(self):
        """Load every registered image and sound immediately.

        Fonts are not preloaded since they require a size to load.
        Load fonts explicitly with the sizes your game needs.

        Use this at startup or during a loading screen to avoid
        load delays during gameplay.
        """
        self.preload_images()
        self.preload_sounds()

    def preload_images(self):
        """Load every registered image immediately."""
        seen_paths = set()
        for path in self._image_paths.values():
            if path not in seen_paths:
                seen_paths.add(path)
                self.load_image(path)

    def preload_sounds(self):
        """Load every registered sound immediately."""
        seen_paths = set()
        for path in self._audio_paths.values():
            if path not in seen_paths:
                seen_paths.add(path)
                self.load_sound(path)

    def clear(self) -> None:
        """Clear every cache. Registered names remain available.

        The next time an asset is loaded, it will be read from disk again.
        """
        self._image_cache.clear()
        self._sound_cache.clear()
        self._font_cache.clear()
        self._spritesheet_cache.clear()

    def clear_registry(self) -> None:
        """Clear all registered asset names. Does not affect caches.

        Use rescan() or scan_directory() afterwards to rebuild the registry.
        """
        self._image_paths.clear()
        self._audio_paths.clear()
        self._font_paths.clear()

    # INTERNAL
    def _resolve_path(
        self,
        name_or_path: str,
        registry: dict[str, str],
        category: str,
        strict: bool = True,
    ) -> str | None:
        """Resolve a registered name or direct path to an actual file path.

        Tries, in order:
            1. name_or_path as a direct file path on disk
            2. name_or_path as a key in the given registry

        Args:
            name_or_path: A registered asset name, or a direct file path.
            registry: The registry dict to check (image/audio/font paths).
            category: Human readable category name, used in error messages.
            strict: Whether to raise an error if not found. If False,
                    returns None instead.

        Returns:
            The resolved file path, or None if not found and strict is False.

        Raises:
            AssetNotFoundError: If not found and strict is True.
        """
        if os.path.isfile(name_or_path):
            return name_or_path

        if name_or_path in registry:
            return registry[name_or_path]

        if strict:
            raise AssetNotFound(
                f"Could not resolve {category} '{name_or_path}'. "
                f"It is not a valid file path and is not registered. "
                f"Check your spelling or call scan_directory() to re-scan for new assets."
            )
        return None
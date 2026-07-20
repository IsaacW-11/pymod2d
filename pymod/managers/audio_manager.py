from __future__ import annotations
import math

import pygame

import pymod


class AudioManager:
    """Manages all sound effect and music playback.

    Sounds are played through the manager from anywhere. There is no audio component.
    If you want a sound tied to a GameObject, write a component that calls this manager, optionally passing the object's position for spatial audio.

    Volume is organised into buses. A sound's final volume is:
        sound_volume × bus_volume × master_volume

    So lowering the SFX bus quiets all sound effects at once, and the master bus quiets everything.

    Spatial audio is opt-in per call.
    Pass a `position` to play() and the sound is attenuated by distance from the listener and panned left or  right based on which side of the listener it's on.
    Omit position and it plays at full volume, centered.

    Attributes:
        master_volume: Global multiplier on everything, 0.0 to 1.0.
        sfx_volume: Multiplier on all sound effects, 0.0 to 1.0.
        music_volume: Multiplier on music, 0.0 to 1.0.
        listener_position: World position sounds are heard from. Set this to the player or camera position each frame for spatial audio. Defaults to (0, 0).
        min_distance: Within this distance of the listener, spatial sounds play at full volume.
        max_distance: Beyond this distance, spatial sounds are silent. Between min and max they fade linearly.
    """

    def __init__(
        self,
        channels: int = 32,
        master_volume: float = 1.0,
        sfx_volume: float = 1.0,
        music_volume: float = 1.0,
        min_distance: float = 200.0,
        max_distance: float = 1200.0,
    ):
        pygame.mixer.init()
        pygame.mixer.set_num_channels(channels)

        self._master_volume = self._clamp(master_volume)
        self._sfx_volume = self._clamp(sfx_volume)
        self._music_volume = self._clamp(music_volume)

        self.listener_position: tuple[float, float] = (0.0, 0.0)
        self.min_distance = min_distance
        self.max_distance = max_distance

        self._current_music: str | None = None
        self._music_paused: bool = False

        # tracks active playbacks so we can update/stop them by handle
        self._active: dict[int, SoundHandle] = {}
        self._next_handle_id: int = 0

    # VOLUME BUSES
    @property
    def master_volume(self) -> float:
        """Global volume multiplier applied to everything, 0.0 to 1.0."""
        return self._master_volume

    @master_volume.setter
    def master_volume(self, value: float):
        self._master_volume = self._clamp(value)
        self._refresh_all_volumes()

    @property
    def sfx_volume(self) -> float:
        """Volume multiplier for all sound effects, 0.0 to 1.0."""
        return self._sfx_volume

    @sfx_volume.setter
    def sfx_volume(self, value: float):
        self._sfx_volume = self._clamp(value)
        self._refresh_all_volumes()

    @property
    def music_volume(self) -> float:
        """Volume multiplier for music, 0.0 to 1.0."""
        return self._music_volume

    @music_volume.setter
    def music_volume(self, value: float):
        self._music_volume = self._clamp(value)
        pygame.mixer.music.set_volume(self._music_volume * self._master_volume)


    # SOUND EFFECTS
    def play(
        self,
        name: str,
        volume: float = 1.0,
        loops: int = 0,
        position: tuple[float, float] | None = None,
        fade_in: float = 0.0,
    ) -> SoundHandle | None:
        """Play a sound effect.

        Args:
            name: Registered asset name or file path, loaded via AssetManager.
            volume: Volume for this specific sound, 0.0 to 1.0. Multiplied by the sfx and master buses.
            loops: How many extra times to repeat. 0 plays once, -1 loops forever.
            position: World position of the sound. If given, the sound is attenuated by distance from listener_position and panned left/right.
                      If None, plays at full volume, centered.
            fade_in: Seconds to fade in from silence. 0 starts at full volume.

        Returns:
            A SoundHandle for controlling this playback (stop, fade out, update position), or None if no free channel was available.
        """
        sound = pymod.assets.load_sound(name)
        channel = pygame.mixer.find_channel()
        if channel is None:
            return None

        handle = SoundHandle(
            manager=self,
            handle_id=self._next_handle_id,
            channel=channel,
            sound=sound,
            base_volume=self._clamp(volume),
            position=position,
        )
        self._next_handle_id += 1
        self._active[handle.id] = handle

        fade_ms = int(fade_in * 1000)
        channel.play(sound, loops=loops, fade_ms=fade_ms)
        handle._apply_volume()

        return handle

    def stop_all(self, fade_out: float = 0.0):
        """Stop every playing sound effect. Does not affect music.

        Args:
            fade_out: Seconds to fade out over. 0 stops immediately.
        """
        if fade_out > 0:
            pygame.mixer.fadeout(int(fade_out * 1000))
        else:
            pygame.mixer.stop()
        self._active.clear()

    def pause_all(self):
        """Pause every playing sound effect."""
        pygame.mixer.pause()

    def resume_all(self):
        """Resume every paused sound effect."""
        pygame.mixer.unpause()

    # MUSIC
    def play_music(
        self,
        name: str,
        loops: int = -1,
        fade_in: float = 0.0,
        start_at: float = 0.0,
    ):
        """Play background music. Replaces any currently playing music.

        Music streams from disk rather than loading fully into memory, so it's suited to long tracks.
        Only one music track plays at a time.
        Use crossfade_music to transition smoothly between tracks.

        Args:
            name: Registered asset name or file path.
            loops: How many extra times to repeat. -1 loops forever (default).
            fade_in: Seconds to fade in from silence.
            start_at: Seconds into the track to begin playback.
        """
        path = pymod.assets.get_audio_path(name)
        pygame.mixer.music.load(path)
        pygame.mixer.music.set_volume(self._music_volume * self._master_volume)
        pygame.mixer.music.play(loops=loops, start=start_at, fade_ms=int(fade_in * 1000))
        self._current_music = name
        self._music_paused = False

    def stop_music(self, fade_out: float = 0.0):
        """Stop the current music.

        Args:
            fade_out: Seconds to fade out over. 0 stops immediately.
        """
        if fade_out > 0:
            pygame.mixer.music.fadeout(int(fade_out * 1000))
        else:
            pygame.mixer.music.stop()
        self._current_music = None

    def crossfade_music(self, name: str, duration: float = 1.0):
        """Fade out the current music while fading in a new track.

        Because pygame only supports one music stream, this fades the old track out and starts the new one fading in.
        They overlap only briefly rather than truly crossfading. For a true crossfade you ould need to play one of them as a looping sound effect instead.

        Args:
            name: The new track to fade in.
            duration: Seconds for the transition.
        """
        pygame.mixer.music.fadeout(int(duration * 1000))
        self.play_music(name, fade_in=duration)

    def pause_music(self):
        """Pause the current music, keeping its position."""
        pygame.mixer.music.pause()
        self._music_paused = True

    def resume_music(self):
        """Resume paused music from where it left off."""
        pygame.mixer.music.unpause()
        self._music_paused = False

    @property
    def music_playing(self) -> bool:
        """Whether music is currently playing (and not paused)."""
        return pygame.mixer.music.get_busy() and not self._music_paused

    @property
    def current_music(self) -> str | None:
        """Name of the currently loaded music track, or None."""
        return self._current_music

    # SPATIAL AUDIO
    def set_listener(self, x: float, y: float):
        """Set the world position that spatial sounds are heard from.

        Typically called each frame with the player's or camera's position.
        Sounds played with a `position` are attenuated and panned relative to this point.

        Args:
            x: Listener world x.
            y: Listener world y.
        """
        self.listener_position = (x, y)

    def _spatial_factors(self, position: tuple[float, float]) -> tuple[float, float, float]:
        """Compute (attenuation, left_gain, right_gain) for a world position.

        Attenuation fades linearly from 1.0 at min_distance to 0.0 at max_distance.
        Panning is based on horizontal offset from the listener.
        """
        lx, ly = self.listener_position
        dx = position[0] - lx
        dy = position[1] - ly
        distance = math.hypot(dx, dy)

        # distance attenuation
        if distance <= self.min_distance:
            attenuation = 1.0
        elif distance >= self.max_distance:
            attenuation = 0.0
        else:
            span = self.max_distance - self.min_distance
            attenuation = 1.0 - ((distance - self.min_distance) / span)

        # stereo panning — how far left/right of the listener
        pan = 0.0
        if self.max_distance > 0:
            pan = max(-1.0, min(1.0, dx / self.max_distance))

        # convert pan (-1 left, 0 center, 1 right) into channel gains
        left = (1.0 - pan) / 2 + 0.5 * (1.0 - abs(pan))
        right = (1.0 + pan) / 2 + 0.5 * (1.0 - abs(pan))
        left = min(1.0, left)
        right = min(1.0, right)

        return (attenuation, left, right)

    # INTERNAL
    def _clamp(self, value: float) -> float:
        return max(0.0, min(1.0, value))

    def _refresh_all_volumes(self):
        """Reapply volume to every active sound after a bus change."""
        for handle in list(self._active.values()):
            if handle.playing:
                handle._apply_volume()
            else:
                self._active.pop(handle.id, None)
        pygame.mixer.music.set_volume(self._music_volume * self._master_volume)

    def _update(self):
        """Internal method called each frame by Game. Cleans up finished sounds
        and refreshes spatial audio for any sound with a live position."""
        finished = []
        for handle in self._active.values():
            if not handle.playing:
                finished.append(handle.id)
            elif handle.position is not None:
                handle._apply_volume()

        for hid in finished:
            self._active.pop(hid, None)

    def _shutdown(self):
        """Internal — called by Game on quit."""
        pygame.mixer.music.stop()
        pygame.mixer.stop()
        pygame.mixer.quit()


class SoundHandle:
    """A handle to one playing sound, returned by AudioManager.play().

    Lets you control a specific playback after starting it.
    You can stop it, fade it out, or move its spatial position as the emitting object moves.

    Attributes:
        id: Unique identifier for this playback.
        position: World position for spatial audio, or None for non-spatial.
                  Update this each frame to make the sound follow a moving object.
    """

    def __init__(self, manager, handle_id, channel, sound, base_volume, position):
        self._manager = manager
        self.id = handle_id
        self._channel = channel
        self._sound = sound
        self._base_volume = base_volume
        self.position = position

    @property
    def playing(self) -> bool:
        """Whether this sound is still playing."""
        return self._channel.get_busy() and self._channel.get_sound() is self._sound

    def stop(self, fade_out: float = 0.0):
        """Stop this sound.

        Args:
            fade_out: Seconds to fade out over. 0 stops immediately.
        """
        if fade_out > 0:
            self._channel.fadeout(int(fade_out * 1000))
        else:
            self._channel.stop()

    def set_volume(self, volume: float):
        """Change this sound's own volume, before bus multipliers.

        Args:
            volume: 0.0 to 1.0.
        """
        self._base_volume = max(0.0, min(1.0, volume))
        self._apply_volume()

    def set_position(self, x: float, y: float):
        """Move this sound's world position, for spatial audio.

        Call this each frame to have the sound follow a moving object.

        Args:
            x: World x.
            y: World y.
        """
        self.position = (x, y)
        self._apply_volume()

    def _apply_volume(self):
        """Recompute and apply the final channel volume from all factors."""
        bus = self._manager.sfx_volume * self._manager.master_volume
        vol = self._base_volume * bus

        if self.position is not None:
            attenuation, left, right = self._manager._spatial_factors(self.position)
            vol *= attenuation
            self._channel.set_volume(vol * left, vol * right)
        else:
            self._channel.set_volume(vol)
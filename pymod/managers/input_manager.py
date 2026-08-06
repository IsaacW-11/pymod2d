from __future__ import annotations
from typing import Any

from ..utils.exceptions import MissingAction

import pygame

class InputManager:
    """Manages all input from keyboard, mouse, and gamepads.

    Provides action-based input with rebinding support, raw input access,
    and multi-device handling for future gamepad support.

    Actions are defined by name and can be bound to multiple inputs.
    This allows easy rebinding in settings menus and multi-device support.
    """
    def __init__(self, default_bindings: dict[str, list] = None):
        # keyboard state
        self._keys_current: set[int] = set()
        self._keys_previous: set[int] = set()

        self._text_typed: str = ""

        # mouse state
        self._mouse_buttons_current: set[int] = set()
        self._mouse_buttons_previous: set[int] = set()
        self._mouse_pos: tuple[int, int] = (0, 0)
        self._mouse_pos_previous: tuple[int, int] = (0, 0)
        self._mouse_delta: tuple[int, int] = (0, 0)
        self._mouse_wheel: int = 0

        # gamepad state
        self._gamepads: dict[int, pygame.joystick.Joystick] = {}
        self._gamepad_buttons_current: dict[int, set[int]] = {}
        self._gamepad_buttons_previous: dict[int, set[int]] = {}
        self._gamepad_axes: dict[int, dict[int, float]] = {}
        self._gamepad_hats: dict[int, dict[int, tuple[int, int]]] = {}

        # action mapping
        self._action_map: dict[str, list[Any]] = {} # key = action name, value = binding list

        # key name mapping
        self._key_names: dict[str, int] = {
            # letters
            "a": pygame.K_a, "b": pygame.K_b, "c": pygame.K_c, "d": pygame.K_d,
            "e": pygame.K_e, "f": pygame.K_f, "g": pygame.K_g, "h": pygame.K_h,
            "i": pygame.K_i, "j": pygame.K_j, "k": pygame.K_k, "l": pygame.K_l,
            "m": pygame.K_m, "n": pygame.K_n, "o": pygame.K_o, "p": pygame.K_p,
            "q": pygame.K_q, "r": pygame.K_r, "s": pygame.K_s, "t": pygame.K_t,
            "u": pygame.K_u, "v": pygame.K_v, "w": pygame.K_w, "x": pygame.K_x,
            "y": pygame.K_y, "z": pygame.K_z,
            # numbers
            "0": pygame.K_0, "1": pygame.K_1, "2": pygame.K_2, "3": pygame.K_3,
            "4": pygame.K_4, "5": pygame.K_5, "6": pygame.K_6, "7": pygame.K_7,
            "8": pygame.K_8, "9": pygame.K_9,
            # special
            "space": pygame.K_SPACE, "return": pygame.K_RETURN, "enter": pygame.K_RETURN,
            "backspace": pygame.K_BACKSPACE, "tab": pygame.K_TAB, "escape": pygame.K_ESCAPE,
            "esc": pygame.K_ESCAPE,
            # arrows
            "left": pygame.K_LEFT, "right": pygame.K_RIGHT,
            "up": pygame.K_UP, "down": pygame.K_DOWN,
            # modifiers
            "shift": pygame.K_LSHIFT, "lshift": pygame.K_LSHIFT, "rshift": pygame.K_RSHIFT,
            "ctrl": pygame.K_LCTRL, "lctrl": pygame.K_LCTRL, "rctrl": pygame.K_RCTRL,
            "alt": pygame.K_LALT, "lalt": pygame.K_LALT, "ralt": pygame.K_RALT,
            # function keys
            "f1": pygame.K_F1, "f2": pygame.K_F2, "f3": pygame.K_F3, "f4": pygame.K_F4,
            "f5": pygame.K_F5, "f6": pygame.K_F6, "f7": pygame.K_F7, "f8": pygame.K_F8,
            "f9": pygame.K_F9, "f10": pygame.K_F10, "f11": pygame.K_F11, "f12": pygame.K_F12,
        }

        # reverse lookup for keycode -> name
        self._keycode_to_name: dict[int, str] = {value: key for key, value in self._key_names.items()}

        # initialize gamepads
        pygame.joystick.init()
        self._refresh_gamepads()

        # input listening for rebinding
        self._listening: bool = False
        self._listening_callback = None

        # load default binds
        if default_bindings:
            for action, bindings in default_bindings.items():
                self.create_action(action, bindings)

    # ACTION BASED INPUT
    def action_pressed(self, action: str) -> bool:
        """Checks if an action was pressed this frame.

        Args:
            action: The name of the action to check.

        Returns:
            True if any input bound to this action was pressed this frame, otherwise False.

        Raises:
            MissingAction: If the action does not exist.
        """
        if action not in self._action_map:
            raise MissingAction(f"{action} is not a valid action. Check your spelling or create a new action.")

        for input_binding in self._action_map[action]:
            if self._is_pressed(input_binding):
                return True
        return False

    def action_held(self, action: str) -> bool:
        """Checks if an action is being held this frame.

            Args:
                action: The name of the action to check.

            Returns:
                True if any input bound to this action is being held this frame, otherwise False.

            Raises:
                MissingAction: If the action does not exist.
        """
        if action not in self._action_map:
            raise MissingAction(f"{action} is not a valid action. Check your spelling or create a new action.")

        for input_binding in self._action_map[action]:
            if self._is_held(input_binding):
                return True
        return False

    def action_released(self, action: str) -> bool:
        """Checks if an action was released this frame.

            Args:
                action: The name of the action to check.

            Returns:
                True if any input bound to this action was released this frame, otherwise False.

            Raises:
                MissingAction: If the action does not exist.
        """
        if action not in self._action_map:
            raise MissingAction(f"{action} is not a valid action. Check your spelling or create a new action.")

        for input_binding in self._action_map[action]:
            if self._is_released(input_binding):
                return True
        return False

    # ACTION MANAGEMENT
    def rebind_action(self, action: str, new_bindings: list[Any]):
        """Completely replaces the current binds for an action with a new list of bindings.

        Args:
            action: The name of the action to rebind
            new_bindings: List of new binds (can be strings, keycodes, or empty)
        Raises:
            MissingAction: If the action does not exist.
        """
        if action not in self._action_map:
            raise MissingAction(f"{action} is not a valid action. Check your spelling or create a new action.")

        self._action_map[action] = new_bindings

    def add_binding(self, action: str, binding: Any):
        """Adds a new binding to an action.

        Args:
            action: The name of the action to add a binding to.
            binding: New binding (can be a string, or keycode)
        Raises:
            MissingAction: If the action does not exist.
        """
        if action not in self._action_map:
            raise MissingAction(f"{action} is not a valid action. Check your spelling or create a new action.")

        if binding not in self._action_map[action]:
            self._action_map[action].append(binding)

    def remove_binding(self, action: str, binding: Any):
        """Removes a specific binding from an action.

        Args:
            action: The name of the action to remove a binding from.
            binding: Binding to remove (can be a string, or keycode)
        Raises:
            MissingAction: If the action does not exist.
        """
        if action not in self._action_map:
            raise MissingAction(f"{action} is not a valid action. Check your spelling or create a new action.")

        if binding in self._action_map[action]:
            self._action_map[action].remove(binding)

    def get_bindings(self, action: str) -> list[Any]:
        """Get all bindings for a specific action.

        Args:
            action: The name of the action to query.

        Returns:
            List of inputs bound to this action.

        Raises:
            MissingAction: If the action does not exist.
        """
        if action not in self._action_map:
            raise MissingAction(f"{action} is not a valid action. Check your spelling or create a new action.")

        return self._action_map[action].copy()

    def create_action(self, action: str, bindings: list[Any] = None):
        """Creates a new action with the option to add initial bindings.

        Args:
            action: The name of the action to create.
            bindings: Initial bindings for the action.
        """
        self._action_map[action] = bindings if bindings else []

    def delete_action(self, action: str):
        """Removes an action entirely.

        Args:
            action: The name of the action to remove.

        Raises:
            MissingAction: If the action does not exist.
        """
        if action not in self._action_map:
            raise MissingAction(f"{action} is not a valid action. Check your spelling or create a new action.")
        del self._action_map[action]

    def get_all_actions(self) -> list[str]:
        """Gets a list of all defined actions.

        Returns:
            List of action names.
        """
        return list(self._action_map.keys())

    # RAW KEYBOARD INPUT
    def key_pressed(self, key: int | str) -> bool:
        """Checks if a specific key was pressed this frame.

        Args:
            key: Pygame keycode or string name for specific key.

        Returns:
            True if the key was pressed this frame, otherwise False.
        """
        keycode = self._resolve_key(key)
        return keycode in self._keys_current and keycode not in self._keys_previous

    def key_held(self, key: int | str) -> bool:
        """Checks if a specific key is currently held down.

        Args:
            key: Pygame keycode or string name for specific key.

        Returns:
            True if the key is currently held down, otherwise False.
        """
        keycode = self._resolve_key(key)
        return keycode in self._keys_current

    def key_released(self, key: int | str) -> bool:
        """Checks if a specific key was released this frame.

        Args:
            key: Pygame keycode or string name for specific key.

        Returns:
            True if the key was released this frame, otherwise False.
        """
        keycode = self._resolve_key(key)
        return key not in self._keys_current and keycode in self._keys_previous

    def any_key_pressed(self) -> bool:
        """Checks if any key was pressed this frame.

        Returns:
            True if a key was pressed this frame, otherwise False.
        """
        return bool(self._keys_current - self._keys_previous)

    def get_pressed_keys(self) -> list[int]:
        """Get all keys currently held down.

        Returns:
            List of pygame keycodes,
        """
        return list(self._keys_current)

    # RAW MOUSE INPUT
    def mouse_pressed(self, button: int | str = 0) -> bool:
        """Checks if a specific mouse button was pressed this frame.

        Args:
            button: Button index (0=left, 1=middle, 2=right) or string name. Defaults to left.

        Returns:
            True if the button was pressed this frame, otherwise False.
        """
        button_id = self._resolve_mouse_button(button)
        return button_id in self._mouse_buttons_current and button_id not in self._mouse_buttons_previous

    def mouse_held(self, button: int | str = 0) -> bool:
        """Checks if a specific mouse button is being held down.

        Args:
            button: Button index (0=left, 1=middle, 2=right) or string name. Defaults to left.

        Returns:
            True if the button is being held down, otherwise False.
        """
        button_id = self._resolve_mouse_button(button)
        return button_id in self._mouse_buttons_current

    def mouse_released(self, button: int | str = 0) -> bool:
        """Checks if a specific mouse button was released this frame.

        Args:
            button: Button index (0=left, 1=middle, 2=right) or string name. Defaults to left.

        Returns:
            True if the button was released this frame, otherwise False.
        """
        button_id = self._resolve_mouse_button(button)
        return button_id not in self._mouse_buttons_current and button_id in self._mouse_buttons_previous

    @property
    def mouse_position(self) -> tuple[int, int]:
        """Get the current mouse position in screen coordinates.

        Returns:
            (X,Y) coordinates.
        """
        return self._mouse_pos

    @property
    def mouse_x(self) -> int:
        """Get the current mouse X coordinate.

        Returns:
            X coordinate.
        """
        return self._mouse_pos[0]

    @property
    def mouse_y(self) -> int:
        """Get the current mouse Y coordinate.

        Returns:
            Y coordinate.
        """
        return self._mouse_pos[1]

    @property
    def mouse_delta(self) -> tuple[int, int]:
        """Get how much the mouse has moved this frame.

        Returns:
            (dX,dY)
        """
        return self._mouse_delta

    @property
    def mouse_wheel(self) -> int:
        """Get mouse wheel scroll this frame.

        Returns:
            Positive for scroll up, negative for scroll down, 0 for no scroll.
        """
        return self._mouse_wheel

    @property
    def text_typed(self) -> str:
        """Characters typed this frame, for text fields. Empty most frames."""
        return self._text_typed

    # GAMEPAD INPUT
    def gamepad_button_pressed(self, button: int, gamepad_id: int = 0) -> bool:
        """Check if a gamepad button was pressed this frame.

        Args:
            button: Button index.
            gamepad_id: Gamepad device ID (0 for first gamepad). Defaults to 0.

        Returns:
            True if the button was pressed this frame, otherwise False
        """
        if gamepad_id not in self._gamepad_buttons_current:
            return False
        current = self._gamepad_buttons_current[gamepad_id]
        previous = self._gamepad_buttons_previous.get(gamepad_id, set())
        return button in current and button not in previous

    def gamepad_button_held(self, button: int, gamepad_id: int = 0) -> bool:
        """Check if a gamepad button is currently held down.

        Args:
            button: Button index.
            gamepad_id: Gamepad device ID (0 for first gamepad). Defaults to 0.

        Returns:
            True if the button is currently held down, otherwise False
        """
        if gamepad_id not in self._gamepad_buttons_current:
            return False
        current = self._gamepad_buttons_current[gamepad_id]
        return button in current

    def gamepad_button_released(self, button: int, gamepad_id: int = 0) -> bool:
        """Check if a gamepad button was released this frame.

        Args:
            button: Button index.
            gamepad_id: Gamepad device ID (0 for first gamepad). Defaults to 0.

        Returns:
            True if the button was released this frame, otherwise False
        """
        if gamepad_id not in self._gamepad_buttons_current:
            return False
        current = self._gamepad_buttons_current[gamepad_id]
        previous = self._gamepad_buttons_previous.get(gamepad_id, set())
        return button not in current and button in previous

    def gamepad_axis(self, axis: int, gamepad_id: int = 0) -> float:
        """Get the current value of a gamepad axis.

        Args:
            axis: Axis index (typically 0-1 for left stick, 2-3 for right stick).
            gamepad_id: Gamepad device ID.

        Returns:
            Float value between -1.0 and 1.0, or 0.0 if gamepad not found.
        """
        if gamepad_id not in self._gamepad_axes:
            return 0.0
        return self._gamepad_axes[gamepad_id].get(axis, 0.0)

    def gamepad_hat(self, hat: int, gamepad_id: int = 0) -> tuple[int, int]:
        """Get the current value of a gamepad hat (d-pad).

        Args:
            hat: Hat index (usually 0).
            gamepad_id: Gamepad device ID.

        Returns:
            Tuple of (x, y) where each is -1, 0, or 1.
        """
        if gamepad_id not in self._gamepad_hats:
            return (0, 0)
        return self._gamepad_hats[gamepad_id].get(hat, (0, 0))

    def gamepad_count(self) -> int:
        """Get the number of connected gamepads.

        Returns:
            Number of gamepads.
        """
        return len(self._gamepads)

    def gamepad_connected(self, gamepad_id: int = 0) -> bool:
        """Check if a specific gamepad is connected.

        Args:
            gamepad_id: Gamepad device ID.

        Returns:
            True if the gamepad is connected, otherwise False
        """
        return gamepad_id in self._gamepads

    # HELPER METHODS
    def get_key_name(self, keycode: int) -> str:
        """Get the string name of a keycode.

        Args:
            keycode: Pygame keycode.

        Returns:
            String name if found, otherwise pygame's name
        """
        return self._keycode_to_name.get(keycode, pygame.key.name(keycode))

    def start_listening_for_input(self, callback):
        """Start listening for any input. Calls callback when input detected.

        Args:
            callback: Function to call when input is detected. Must receive the input as argument.
        """
        self._listening_callback = callback
        self._listening = True

    def stop_listening_for_input(self):
        """Stop listening for input."""
        self._listening = False
        self._listening_callback = None

    # INTERNAL METHODS
    def _update(self) -> None:
        """Internal method called every frame by Game to update input state."""
        # save previous state
        self._keys_previous = self._keys_current.copy()
        self._mouse_buttons_previous = self._mouse_buttons_current.copy()
        self._mouse_pos_previous = self._mouse_pos
        self._text_typed = ""

        for gamepad_id in self._gamepad_buttons_current:
            self._gamepad_buttons_previous[gamepad_id] = self._gamepad_buttons_current[gamepad_id].copy()

        # read fresh state from pygame
        pressed_keys = pygame.key.get_pressed()
        self._keys_current = {i for i in range(len(pressed_keys)) if pressed_keys[i]}

        mouse_buttons = pygame.mouse.get_pressed()
        self._mouse_buttons_current = {i for i in range(len(mouse_buttons)) if mouse_buttons[i]}

        self._mouse_pos = pygame.mouse.get_pos()
        self._mouse_delta = (
            self._mouse_pos[0] - self._mouse_pos_previous[0],
            self._mouse_pos[1] - self._mouse_pos_previous[1]
        )

        # mouse wheel is reset each frame (handled in handle_event)
        self._mouse_wheel = 0

        # update gamepad state
        for gamepad_id, gamepad in self._gamepads.items():
            buttons = {i for i in range(gamepad.get_numbuttons()) if gamepad.get_button(i)}
            self._gamepad_buttons_current[gamepad_id] = buttons

            axes = {i: gamepad.get_axis(i) for i in range(gamepad.get_numaxes())}
            self._gamepad_axes[gamepad_id] = axes

            hats = {i: gamepad.get_hat(i) for i in range(gamepad.get_numhats())}
            self._gamepad_hats[gamepad_id] = hats

    def _handle_event(self, event: pygame.event.Event) -> None:
        """Internal method called by Game to handle special input events.

        Args:
            event: The pygame event to process.
        """
        # if listening for rebind, intercept first input and stop listening
        if self._listening:
            detected_input = None
            if event.type == pygame.KEYDOWN:
                detected_input = event.key
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    detected_input = "mouse_left"
                elif event.button == 2:
                    detected_input = "mouse_middle"
                elif event.button == 3:
                    detected_input = "mouse_right"
            elif event.type == pygame.JOYBUTTONDOWN:
                detected_input = f"gamepad_{event.joy}_button_{event.button}"

            elif event.type == pygame.TEXTINPUT:
                self._text_typed += event.text

            if detected_input:
                self._listening = False
                if self._listening_callback:
                    self._listening_callback(detected_input)
                return  # consume the event, don't process normally

        # handle mouse wheel
        if event.type == pygame.MOUSEWHEEL:
            self._mouse_wheel = event.y

        # handle gamepad connection/disconnection
        elif event.type == pygame.JOYDEVICEADDED:
            self._refresh_gamepads()
        elif event.type == pygame.JOYDEVICEREMOVED:
            self._refresh_gamepads()

    def _refresh_gamepads(self) -> None:
        """Refresh the list of connected gamepads."""
        self._gamepads.clear()
        for i in range(pygame.joystick.get_count()):
            gamepad = pygame.joystick.Joystick(i)
            gamepad.init()
            self._gamepads[i] = gamepad
            self._gamepad_buttons_current[i] = set()
            self._gamepad_buttons_previous[i] = set()
            self._gamepad_axes[i] = {}
            self._gamepad_hats[i] = {}

    def _resolve_key(self, key: int | str) -> int:
        """Convert a key string to keycode, or pass through if already int.

        Args:
            key: Keycode or string name.

        Returns:
            Pygame keycode.

        Raises:
            ValueError: If string key name is not recognized.
        """
        if isinstance(key, int):
            return key
        key_lower = key.lower()
        if key_lower in self._key_names:
            return self._key_names[key_lower]
        raise ValueError(f"Unknown key name: '{key}'")

    def _resolve_mouse_button(self, button: int | str) -> int:
        """Convert mouse button string to index.

        Args:
            button: Button index or string name.

        Returns:
            Button index.
        """
        if isinstance(button, int):
            return button
        button_map = {
            "left": 0, "mouse_left": 0,
            "middle": 1, "mouse_middle": 1,
            "right": 2, "mouse_right": 2,
        }
        if button.lower() in button_map:
            return button_map[button.lower()]
        return 0

    def _is_pressed(self, input_binding: Any) -> bool:
        """Check if a raw input binding was pressed this frame.

        Args:
            input_binding: Keycode, mouse button string, or gamepad identifier.

        Returns:
            True if the input was pressed this frame.
        """
        if isinstance(input_binding, int):
            return self.key_pressed(input_binding)
        elif isinstance(input_binding, str):
            if input_binding.startswith("mouse_"):
                return self.mouse_pressed(input_binding)
            elif input_binding.startswith("gamepad_"):
                # format: "gamepad_0_button_5"
                parts = input_binding.split("_")
                gamepad_id = int(parts[1])
                button = int(parts[3])
                return self.gamepad_button_pressed(button, gamepad_id)
            else:
                return self.key_pressed(input_binding)
        return False

    def _is_held(self, input_binding: Any) -> bool:
        """Check if a raw input binding is currently held.

        Args:
            input_binding: Keycode, mouse button string, or gamepad identifier.

        Returns:
            True if the input is currently held.
        """
        if isinstance(input_binding, int):
            return self.key_held(input_binding)
        elif isinstance(input_binding, str):
            if input_binding.startswith("mouse_"):
                return self.mouse_held(input_binding)
            elif input_binding.startswith("gamepad_"):
                parts = input_binding.split("_")
                gamepad_id = int(parts[1])
                button = int(parts[3])
                return self.gamepad_button_held(button, gamepad_id)
            else:
                return self.key_held(input_binding)
        return False

    def _is_released(self, input_binding: Any) -> bool:
        """Check if a raw input binding was released this frame.

        Args:
            input_binding: Keycode, mouse button string, or gamepad identifier.

        Returns:
            True if the input was released this frame.
        """
        if isinstance(input_binding, int):
            return self.key_released(input_binding)
        elif isinstance(input_binding, str):
            if input_binding.startswith("mouse_"):
                return self.mouse_released(input_binding)
            elif input_binding.startswith("gamepad_"):
                parts = input_binding.split("_")
                gamepad_id = int(parts[1])
                button = int(parts[3])
                return self.gamepad_button_released(button, gamepad_id)
            else:
                return self.key_released(input_binding)
        return False
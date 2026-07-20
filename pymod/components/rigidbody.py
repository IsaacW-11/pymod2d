from __future__ import annotations
import math

import pymod


class Rigidbody(pymod.Component):
    """Gives a GameObject velocity-based physics: gravity, forces, and collision response.

    Integrates on the fixed timestep using TimeManager.fixed_delta, so behaviour is stable and framerate-independent.
    Reads the collision normals produced by the CollisionManager to bounce or stop velocity when hitting other colliders.

    A collider with NO Rigidbody is treated as an immovable wall (infinite mass).
    Dynamic bodies collide against it correctly without it needing any physics of its own.
    This means static ground, walls, and platforms only need a Collider, not a Rigidbody.

    NOTE: Currently, there is a very minor bug where resting RigidBodies aren't actually resting, and bob up and down by about 0.3 pixels.

    Attributes:
        velocity: Current linear velocity in world units per second, as [x, y].
        angular_velocity: Current rotation speed in degrees per second.
        mass: Mass in arbitrary units. Heavier bodies are pushed less in collisions. Must be > 0.
        gravity_scale: Multiplier on the global gravity. 0 disables gravity for this body. 1 is normal, 2 is twice as heavy-feeling.
        linear_drag: Fraction of linear velocity shed per second (0 = none, higher = more air resistance / friction-like slowdown).
        angular_drag: Same as linear_drag but for rotation.
        bounciness: Restitution, 0 to 1. 0 = no bounce (stops dead), 1 = perfectly elastic (bounces with no energy loss).
        friction: Tangential velocity damping on contact, 0 to 1. 0 = frictionless (slides freely along surfaces), 1 = grips fully.
        kinematic: If True, this body moves only via script (setting velocity or position directly) and is never affected by gravity,
                   forces, or collision push-back. Use for moving platforms.
        freeze_x: Lock horizontal position — velocity.x is forced to 0.
        freeze_y: Lock vertical position — velocity.y is forced to 0.
        freeze_rotation: Lock rotation — angular_velocity is forced to 0.
    """

    def __init__(
        self,
        mass: float = 1.0,
        gravity_scale: float = 1.0,
        linear_drag: float = 0.0,
        angular_drag: float = 0.0,
        bounciness: float = 0.0,
        friction: float = 0.0,
        kinematic: bool = False,
        freeze_x: bool = False,
        freeze_y: bool = False,
        freeze_rotation: bool = True,
    ):
        super().__init__()
        self.velocity: list[float] = [0.0, 0.0]
        self.angular_velocity: float = 0.0

        self.mass: float = max(0.0001, mass)
        self.gravity_scale: float = gravity_scale
        self.linear_drag: float = linear_drag
        self.angular_drag: float = angular_drag
        self.bounciness: float = bounciness
        self.friction: float = friction
        self.kinematic: bool = kinematic
        self.freeze_x: bool = freeze_x
        self.freeze_y: bool = freeze_y
        self.freeze_rotation: bool = freeze_rotation

        self._force_accum: list[float] = [0.0, 0.0]
        self._torque_accum: float = 0.0

    # APPLYING FORCES
    def add_force(self, fx: float, fy: float):
        """Accumulate a force to apply on the next physics step.

        Force is divided by mass to produce acceleration (F = ma), so heavier bodies accelerate less from the same force.
        Accumulated forces are cleared each step.

        Args:
            fx: Force along x.
            fy: Force along y.
        """
        self._force_accum[0] += fx
        self._force_accum[1] += fy

    def add_impulse(self, ix: float, iy: float):
        """Apply an instantaneous change in velocity, scaled by mass.

        Unlike a force, an impulse changes velocity immediately rather than over time.

        Args:
            ix: Impulse along x.
            iy: Impulse along y.
        """
        self.velocity[0] += ix / self.mass
        self.velocity[1] += iy / self.mass

    def add_torque(self, torque: float):
        """Accumulate rotational force for the next step.

        Args:
            torque: Torque in degrees/second^2 units.
        """
        self._torque_accum += torque

    def set_velocity(self, vx: float, vy: float):
        """Directly set the linear velocity.

        Args:
            vx: Velocity along x.
            vy: Velocity along y.
        """
        self.velocity[0] = vx
        self.velocity[1] = vy

    @property
    def speed(self) -> float:
        """Current linear speed (magnitude of velocity)."""
        return math.hypot(self.velocity[0], self.velocity[1])

    # COLLISION RESPONSE — called by CollisionManager
    def _apply_collision_response(
            self,
            normal: tuple[float, float],
            other: "Rigidbody | None",
    ):
        """Adjust velocity in response to a collision along `normal`.

        normal points in the direction THIS body was pushed to separate.
        If `other` is None (or kinematic), the collision is against an immovable wall of infinite mass.
        Otherwise the impulse is shared between both bodies based on mass.
        """
        if self.kinematic:
            return

        REST_THRESHOLD = 100.0  # into-surface speed below which we stop bouncing

        nx, ny = normal

        if other is None or other.kinematic:
            # ── wall collision (infinite mass) ──
            vel_into = self.velocity[0] * nx + self.velocity[1] * ny
            if vel_into >= 0:
                return  # already separating

            restitution = self.bounciness
            if abs(vel_into) < REST_THRESHOLD:
                restitution = 0.0  # treat as resting — kill velocity dead

            self.velocity[0] -= (1 + restitution) * vel_into * nx
            self.velocity[1] -= (1 + restitution) * vel_into * ny
            self._apply_friction(normal)
        else:
            # ── two dynamic bodies — share impulse by mass ──
            rel_vx = self.velocity[0] - other.velocity[0]
            rel_vy = self.velocity[1] - other.velocity[1]
            rel_into = rel_vx * nx + rel_vy * ny
            if rel_into >= 0:
                return  # already separating

            restitution = (self.bounciness + other.bounciness) / 2
            if abs(rel_into) < REST_THRESHOLD:
                restitution = 0.0

            inv_mass_sum = (1 / self.mass) + (1 / other.mass)
            j = -(1 + restitution) * rel_into / inv_mass_sum

            self.velocity[0] += (j / self.mass) * nx
            self.velocity[1] += (j / self.mass) * ny
            other.velocity[0] -= (j / other.mass) * nx
            other.velocity[1] -= (j / other.mass) * ny

            self._apply_friction(normal)

    def _apply_friction(self, normal: tuple[float, float]):
        """Damp the velocity component tangential (parallel) to the surface."""
        if self.friction <= 0:
            return
        nx, ny = normal
        # tangent is perpendicular to normal
        tx, ty = -ny, nx
        vel_tangent = self.velocity[0] * tx + self.velocity[1] * ty
        self.velocity[0] -= vel_tangent * self.friction * tx
        self.velocity[1] -= vel_tangent * self.friction * ty

    # LIFECYCLE
    def on_start(self):
        pymod.Game.get().physics.register(self)

    def on_destroy(self):
        pymod.Game.get().physics.unregister(self)

    def fixed_update(self) -> None:
        """Integrate motion on the fixed timestep."""
        print(f"fixed_update running, velocity: {self.velocity}, y: {self.owner.y}")
        if self.kinematic:
            # kinematic bodies still move by their velocity if set,
            # but ignore gravity, drag, and forces
            dt = pymod.time.fixed_delta
            self.owner.x += self.velocity[0] * dt
            self.owner.y += self.velocity[1] * dt
            self._force_accum = [0.0, 0.0]
            self._torque_accum = 0.0
            return

        dt = pymod.time.fixed_delta
        gravity = pymod.Game.get().physics.gravity

        # apply gravity
        self.velocity[0] += gravity[0] * self.gravity_scale * dt
        self.velocity[1] += gravity[1] * self.gravity_scale * dt

        # apply accumulated forces (F = ma → a = F/m)
        self.velocity[0] += (self._force_accum[0] / self.mass) * dt
        self.velocity[1] += (self._force_accum[1] / self.mass) * dt
        self.angular_velocity += (self._torque_accum / self.mass) * dt

        # apply drag
        if self.linear_drag > 0:
            factor = max(0.0, 1.0 - self.linear_drag * dt)
            self.velocity[0] *= factor
            self.velocity[1] *= factor
        if self.angular_drag > 0:
            self.angular_velocity *= max(0.0, 1.0 - self.angular_drag * dt)

        # apply constraints
        if self.freeze_x:
            self.velocity[0] = 0.0
        if self.freeze_y:
            self.velocity[1] = 0.0
        if self.freeze_rotation:
            self.angular_velocity = 0.0

        # integrate position and rotation
        self.owner.x += self.velocity[0] * dt
        self.owner.y += self.velocity[1] * dt
        if not self.freeze_rotation:
            self.owner.rotation = getattr(self.owner, "rotation", 0.0) + self.angular_velocity * dt

        # clear accumulators
        self._force_accum = [0.0, 0.0]
        self._torque_accum = 0.0
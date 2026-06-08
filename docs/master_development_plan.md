# Remibot Console Master Development Plan

This plan reconciles the product brief with the current repository state. It is written for future contributors and should be treated as the active roadmap unless superseded by a newer architecture decision.

## Product Positioning

Remibot Console is a developer-oriented upper-computer for a 5-DOF kitchen robot arm. The primary user is expected to understand the robot internals. The product should therefore prioritize information density, fast debugging, and clear state provenance over consumer-style simplification.

Target environments:

- Development: Ubuntu with ROS2 Humble, optionally Windows for UI-only mock work.
- Deployment: Jetson Orin Nano class device.
- Simulation and visualization: RViz/MoveIt for planning debug, MuJoCo/offscreen rendering as the primary in-window 3D viewport path.

## Decisions To Keep

- GUI stack: PySide6.
- Mock mode must remain runnable without ROS2.
- GUI must not publish `/joint_states`.
- GUI must not mutate displayed joint state with requested targets.
- ROS2 mode should command through controller actions/services, currently `/arm_controller/follow_joint_trajectory`.
- Persistent runtime data belongs under `data/`.
- UI should be a workflow coordinator, not the safety authority.

## Brief Items Accepted

### Data Directory Policy

The repository now reserves:

```text
data/
  waypoints/
  oscilloscope/
  safety_profiles/
  motor_mapping/
  calibration/
  identification/
  policies/
```

Current JSON files in `data/` remain supported, but new generated artifacts should use the directories above.

### MJCF Discovery Contract

The application now accepts an optional MJCF path in this priority order:

1. `--mjcf PATH`
2. `REMIBOT_MJCF`
3. `data/config.yaml` key `mjcf_path`
4. `None`, meaning the UI should fall back to non-MuJoCo visualization

This prepares the project for MuJoCo integration without pretending that the viewport is already implemented.

### Near-Term Feature Order

The recommended next tasks are:

1. MuJoCo viewport integration or confirmed viewport scaffold.
2. Oscilloscope tab with CSV export.
3. Motor ID mapping panel.
4. Mode manager ROS2 interface skeleton.
5. Gravity compensation workflow.
6. Safety profile/session parameter panel.

Gravity compensation should not be implemented as a standalone button before a mode manager exists.

## Brief Items Modified

### Visualization Direction

The product direction is to avoid a C++ RViz rewrite unless it becomes unavoidable. The current project has already proven that RViz window capture works but has drawbacks:

- requires RViz to be open
- captures the full window, not only the render panel
- has visible latency
- may be brittle across window managers

Adopted direction:

- Primary embedded 3D path: MuJoCo/offscreen rendering in the Qt window when an MJCF model is available.
- RViz role: keep RViz external for MoveIt planning and desktop debugging.
- Transitional bridge: keep RViz capture available but make it opt-in once MuJoCo is stable.
- Jetson fallback: keep a lightweight 2D renderer with J1 top view, J2-J4 side view, and J5 roll view.
- Contingency: use C++ Qt/RViz only if MuJoCo/offscreen cannot provide the required debugging workflow.

### Claimed Existing `mujoco_viewport.py`

The brief states that `qt_operator_console/mujoco_viewport.py` already exists. It does not exist in the current repository. Do not wire UI code to that file until it is actually added.

### Flat `qt_operator_console/*.py` Layout

The brief proposes future files such as `qt_operator_console/oscilloscope_widget.py`. The current implementation is package-based:

```text
qt_operator_console/kitchen_qt/
  backend/
  ui/
  ui/widgets/
```

New widgets should preferably live under `qt_operator_console/kitchen_qt/ui/widgets/` or a similarly scoped subpackage unless a larger refactor is explicitly planned.

## Task Backlog

### Task A: MuJoCo Viewport

Goal: replace window capture as the main embedded visualization path.

Required work:

- Add a real `MujocoViewport` widget.
- Add a dependency strategy for `mujoco>=3.0.0` without making simple mock installs fragile.
- Use `find_mjcf()` to locate the model.
- Feed joint state into the viewport through Qt signals.
- Keep a mock viewport fallback.

Acceptance criteria:

- `python kitchen_arm_gui.py --backend mock` still opens without MuJoCo installed.
- With a valid MJCF path, the Workbench shows an embedded rendered model.
- No RViz window capture is required for the embedded viewport.
- RViz can still be launched externally for MoveIt debugging without being required by the Qt viewport.

### Task B: Oscilloscope

Goal: add a dense telemetry plot for joint debugging.

Required work:

- Add a pyqtgraph-based widget.
- Buffer at least 500 samples per joint.
- Support pause/resume.
- Save CSV to `data/oscilloscope/YYYYMMDD_HHMMSS.csv`.
- Work in mock mode.

Initial signals:

- joint position
- joint velocity
- effort/current when available

### Task C: Motor ID Mapping

Goal: make CAN ID to joint mapping visible and testable.

Data file:

```text
data/motor_mapping/default.yaml
```

Required UI:

- scan bus
- show CAN ID, joint name, firmware, temperature, status
- jog selected actuator after confirmation
- save/load/export YAML

Mock behavior:

- return five fake actuators
- jog logs only

### Task D: Bringup Cleanup

Current state:

- `start_joy_control` defaults to false.
- `start_rviz_capture` defaults to true as a bridge.
- `start_renderer` defaults to false to avoid fighting RViz capture.
- The fallback renderer publishes a separate three-view 2D image stream unless deliberately remapped.

Future adjustment:

- When MuJoCo/offscreen viewport is stable, make RViz capture opt-in rather than default.

### Task E: Safety Panel

Goal: expose safety wrapper parameters without making GUI the safety authority.

Session parameters:

- policy scale
- max joint delta per step
- max joint velocity
- torque warn/stop ratios
- per-joint overrides

Profile files:

```text
data/safety_profiles/*.yaml
```

ROS2 requirement:

- safety wrapper node must expose dynamic parameters before UI controls are enabled.

### Task F: Mode Manager

Goal: define the mode authority interface before gravity compensation UI.

Needed modes:

```text
IDLE
MANUAL
GRAVITY_COMP
TEACHING
HOMING
POLICY
FAULT
ESTOP
```

Implementation note:

- A proper service needs a custom interface with `mode_name`, `success`, and `reason`.
- Do not fake this with a service that cannot carry the target mode.
- Until custom interfaces are added, a topic-based prototype can publish current mode but should not be treated as final command authority.

### Task G: Gravity Compensation

Only implement after Task F.

Workflow:

1. stop current command source
2. move home or safe pose
3. disable motors if required
4. switch controller mode
5. re-enable motors
6. verify telemetry
7. enter `GRAVITY_COMP`

During transition:

- disable GUI slider commands
- disable joystick command output
- block planner execution

### Task H: `mjlab/` And Policy-To-Real

Add only when policy deployment becomes active:

```text
mjlab/
  envs/
  train/
  policies/
  deploy/
  calibration/
```

Policy metadata must include observation/action definitions, joint order, control frequency, and action scaling.

### Task I: Policy Deploy Panel

Depends on:

- policy node
- safety wrapper
- mode manager
- motor mapping

Required checks:

- policy `joint_order` must match current motor mapping
- mismatch should block or warn before execution

### Task J: Identification Wizard

Goal: support friction, inertia, and zero-offset identification.

Outputs:

```text
data/identification/
data/calibration/
```

The wizard should be step-based and must require homing, safe workspace, and an active safety profile before motion.

## Implementation Rules

- New UI widgets must have mock behavior.
- New persistent files must be written under `data/`.
- UI controls without backend support should be disabled or visibly marked as unavailable.
- Threads must communicate with Qt widgets through signals or locked state.
- Do not introduce raw motor commands from the GUI.
- Do not implement gravity compensation before a mode manager interface exists.

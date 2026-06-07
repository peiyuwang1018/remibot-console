"""Qt main window for the kitchen arm operator console."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDoubleSpinBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QPushButton,
    QRadioButton,
    QSlider,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..backend.base import ArmBackend
from ..config import CONTROL_MODES, JOINTS, SPEED_LEVELS, TOOLS, UI_HZ
from ..models import RobotState
from ..storage import JsonStore
from .theme import STYLE_SHEET
from .widgets.plot import MultiLinePlot


STATUS_COLORS = {"READY": "#66c9a4", "HOMING": "#e8b955", "ESTOP": "#d66c75", "TEACHING": "#7ab2f0"}
CONTACT_COLORS = {"No Contact": "#66c9a4", "Contact": "#e8b955", "Wedged": "#e0845d"}
HOMING_COLORS = {"pending": "#8c99ad", "in_progress": "#e8b955", "done": "#66c9a4", "failed": "#d66c75"}
WORLD_COLORS = {"SimulationOnly": "#7ab2f0", "HardwareConnected": "#e8b955", "HardwareLive": "#66c9a4", "HybridMirror": "#b58cff"}
HARDWARE_COLORS = {"Disconnected": "#8c99ad", "Mock": "#7ab2f0", "ROS graph": "#e8b955", "Connected": "#66c9a4", "Fault": "#d66c75"}
AUTHORITY_COLORS = {"GUI": "#7ab2f0", "Joystick": "#e8b955", "Planner": "#b58cff", "TeachingDrag": "#66c9a4", "Safety": "#d66c75"}


class MainWindow(QMainWindow):
    def __init__(self, state: RobotState, backend: ArmBackend, store: JsonStore, data_dir: Path) -> None:
        super().__init__()
        self.state = state
        self.backend = backend
        self.store = store
        self.data_dir = data_dir
        self.setWindowTitle("Kitchen Arm Operator Console - Qt")
        self.resize(1360, 860)
        self.setStyleSheet(STYLE_SHEET)

        self.backend.state_changed.connect(self.refresh)
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.refresh)
        self.refresh_timer.start(int(1000 / UI_HZ))

        self._build()
        self.backend.start()

    def closeEvent(self, event) -> None:  # noqa: N802 - Qt API
        self.backend.stop()
        super().closeEvent(event)

    def _build(self) -> None:
        root = QWidget()
        layout = QVBoxLayout(root)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)
        layout.addWidget(self._build_top_bar())

        self.tabs = QTabWidget()
        self.tabs.addTab(self._workbench_tab(), "Workbench")
        self.tabs.addTab(self._homing_tab(), "Homing")
        self.tabs.addTab(self._tuning_tab(), "Motors and Tuning")
        self.tabs.addTab(self._tools_tab(), "Tools")
        self.tabs.addTab(self._visualization_tab(), "Visualization")
        self.tabs.addTab(self._logs_tab(), "Logs")
        layout.addWidget(self.tabs, 1)
        self.setCentralWidget(root)

    def _panel(self, title: str | None = None) -> tuple[QFrame, QVBoxLayout]:
        frame = QFrame()
        frame.setObjectName("Panel")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)
        if title:
            label = QLabel(title)
            label.setObjectName("SectionTitle")
            layout.addWidget(label)
        return frame, layout

    def _build_top_bar(self) -> QFrame:
        bar = QFrame()
        bar.setObjectName("TopBar")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(12)

        self.status_label = self._pill("READY")
        self.world_label = self._pill("World: SimulationOnly")
        self.hardware_label = self._pill("Hardware: Disconnected")
        self.homing_state_label = self._pill("Homing: pending")
        self.authority_label = self._pill("Authority: GUI")
        self.backend_label = self._pill("mock disconnected")
        self.contact_label = self._pill("No Contact")
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(CONTROL_MODES)
        self.mode_combo.currentTextChanged.connect(self.backend.request_mode)
        self.tool_combo = QComboBox()
        self.tool_combo.addItems(TOOLS)
        self.tool_combo.currentTextChanged.connect(self._set_tool)
        estop = QPushButton("E-STOP")
        estop.setObjectName("Danger")
        estop.clicked.connect(lambda: self.backend.set_estop(not self.state.snapshot()["estop"]))

        for text, widget in [
            ("World", self.world_label),
            ("Hardware", self.hardware_label),
            ("Homing", self.homing_state_label),
            ("Backend", self.backend_label),
            ("Mode", self.mode_combo),
            ("Authority", self.authority_label),
            ("Tool", self.tool_combo),
            ("Contact", self.contact_label),
        ]:
            label = QLabel(text)
            label.setObjectName("Muted")
            layout.addWidget(label)
            layout.addWidget(widget)
        layout.addStretch(1)
        layout.addWidget(estop)
        return bar

    def _pill(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("Pill")
        return label

    def _workbench_tab(self) -> QWidget:
        page = QWidget()
        layout = QHBoxLayout(page)

        left, left_layout = self._panel("Live State")
        left.setMinimumWidth(480)
        self._build_joint_telemetry_panel(left_layout)
        left_layout.addSpacing(8)
        self._build_manual_operation_panel(left_layout)

        center, center_layout = self._panel("Joint Command")
        self._build_joint_command_panel(center_layout)

        right, right_layout = self._panel("Waypoints And Teaching")
        right.setMinimumWidth(360)
        self._build_waypoint_panel(right_layout)

        layout.addWidget(left, 0)
        layout.addWidget(center, 1)
        layout.addWidget(right, 0)
        return page

    def _build_joint_telemetry_panel(self, layout: QVBoxLayout) -> None:
        self.joint_table = QTableWidget(len(JOINTS), 6)
        self.joint_table.setHorizontalHeaderLabels(["Joint", "I (A)", "q (rad)", "dq (rad/s)", "Temp", "Fault"])
        self.joint_table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        for col, width in enumerate([56, 78, 86, 92, 70, 62]):
            self.joint_table.setColumnWidth(col, width)
        self.joint_table.verticalHeader().setVisible(False)
        self.joint_table.setAlternatingRowColors(True)
        layout.addWidget(self.joint_table)
        self.pose_label = QLabel("xyz: --\nrpy: --")
        self.pose_label.setObjectName("Pill")
        layout.addWidget(self.pose_label)
        self.signal_combo = QComboBox()
        self.signal_combo.addItems(["Current", "Position", "Velocity"])
        layout.addWidget(self.signal_combo)
        self.signal_plot = MultiLinePlot()
        self.signal_plot.setMinimumHeight(180)
        layout.addWidget(self.signal_plot, 1)

    def _build_manual_operation_panel(self, layout: QVBoxLayout) -> None:
        layout.addWidget(QLabel("Control source"))
        self.joystick_label = self._pill("Joystick: unknown")
        self.control_source_label = self._pill("Active: GUI")
        layout.addWidget(self.joystick_label)
        layout.addWidget(self.control_source_label)
        mode_row = QHBoxLayout()
        self.cartesian_radio = QRadioButton("Cartesian")
        self.joint_radio = QRadioButton("Joint")
        self.cartesian_radio.setChecked(True)
        mode_row.addWidget(self.cartesian_radio)
        mode_row.addWidget(self.joint_radio)
        layout.addLayout(mode_row)
        speed_row = QHBoxLayout()
        for speed in SPEED_LEVELS:
            button = QRadioButton(speed)
            button.setChecked(speed == "Slow")
            speed_row.addWidget(button)
        layout.addLayout(speed_row)
        quick_row = QHBoxLayout()
        for text, slot in [
            ("Enter Teaching", self.backend.enter_teaching),
            ("Exit Teaching", self.backend.exit_teaching),
            ("Start Homing", self.backend.start_homing),
        ]:
            btn = QPushButton(text)
            btn.clicked.connect(slot)
            quick_row.addWidget(btn)
        layout.addLayout(quick_row)

    def _build_joint_command_panel(self, layout: QVBoxLayout) -> None:
        self.manual_sliders: dict[str, QSlider] = {}
        for joint in JOINTS:
            row = QHBoxLayout()
            label = QLabel(joint)
            label.setFixedWidth(32)
            row.addWidget(label)
            slider = QSlider(Qt.Horizontal)
            slider.setRange(-3140, 3140)
            slider.sliderReleased.connect(self._preview_slider_pose)
            self.manual_sliders[joint] = slider
            row.addWidget(slider, 1)
            layout.addLayout(row)
        preview = QPushButton("Preview Sliders in RViz")
        preview.clicked.connect(self._preview_slider_pose)
        layout.addWidget(preview)
        send_row = QHBoxLayout()
        self.manual_joint = QComboBox()
        self.manual_joint.addItems(JOINTS)
        self.manual_target = QDoubleSpinBox()
        self.manual_target.setRange(-3.14, 3.14)
        self.manual_target.setDecimals(3)
        self.manual_target.setSingleStep(0.01)
        send = QPushButton("Send Target")
        send.clicked.connect(self._send_manual_target)
        send_row.addWidget(self.manual_joint)
        send_row.addWidget(self.manual_target)
        send_row.addWidget(send)
        layout.addLayout(send_row)
        layout.addStretch(1)

    def _build_waypoint_panel(self, layout: QVBoxLayout) -> None:
        self.wp_name = QLineEdit()
        self.wp_name.setPlaceholderText("Waypoint name")
        self.wp_desc = QLineEdit()
        self.wp_desc.setPlaceholderText("Description")
        save = QPushButton("Save Current Pose")
        save.clicked.connect(self._save_waypoint)
        layout.addWidget(self.wp_name)
        layout.addWidget(self.wp_desc)
        layout.addWidget(save)
        self.waypoint_list = QListWidget()
        layout.addWidget(self.waypoint_list, 1)
        buttons = QHBoxLayout()
        preview = QPushButton("Preview")
        preview.clicked.connect(self._preview_selected_waypoint)
        execute = QPushButton("Plan/Execute")
        execute.clicked.connect(self._execute_selected_waypoint)
        delete = QPushButton("Delete")
        delete.clicked.connect(self._delete_selected_waypoint)
        buttons.addWidget(preview)
        buttons.addWidget(execute)
        buttons.addWidget(delete)
        layout.addLayout(buttons)
        layout.addSpacing(8)
        self.recording_label = self._pill("Inactive - 0 points")
        toggle = QPushButton("Start/Stop Recording")
        toggle.clicked.connect(self._toggle_recording)
        save_rec = QPushButton("Save Recording")
        save_rec.clicked.connect(self._save_recording)
        clear_rec = QPushButton("Clear Recording")
        clear_rec.clicked.connect(self._clear_recording)
        layout.addWidget(self.recording_label)
        rec_buttons = QHBoxLayout()
        rec_buttons.addWidget(toggle)
        rec_buttons.addWidget(save_rec)
        rec_buttons.addWidget(clear_rec)
        layout.addLayout(rec_buttons)

    def _monitor_tab(self) -> QWidget:
        page = QWidget()
        layout = QHBoxLayout(page)
        left, left_layout = self._panel("Joint Telemetry")
        left.setMinimumWidth(500)
        self.joint_table = QTableWidget(len(JOINTS), 6)
        self.joint_table.setHorizontalHeaderLabels(["Joint", "I (A)", "q (rad)", "dq (rad/s)", "Temp", "Fault"])
        self.joint_table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        for col, width in enumerate([56, 78, 86, 92, 70, 62]):
            self.joint_table.setColumnWidth(col, width)
        self.joint_table.verticalHeader().setVisible(False)
        self.joint_table.setAlternatingRowColors(True)
        left_layout.addWidget(self.joint_table)
        self.pose_label = QLabel("xyz: --\nrpy: --")
        self.pose_label.setObjectName("Pill")
        left_layout.addWidget(self.pose_label)
        self.signal_combo = QComboBox()
        self.signal_combo.addItems(["Current", "Position", "Velocity"])
        left_layout.addWidget(self.signal_combo)

        right, right_layout = self._panel("Rolling Signal Plot")
        self.signal_plot = MultiLinePlot()
        right_layout.addWidget(self.signal_plot, 1)
        layout.addWidget(left, 0)
        layout.addWidget(right, 1)
        return page

    def _teleop_tab(self) -> QWidget:
        page = QWidget()
        layout = QHBoxLayout(page)
        left, left_layout = self._panel("Manual Operation")
        left_layout.addWidget(QLabel("Control space"))
        self.cartesian_radio = QRadioButton("Cartesian")
        self.joint_radio = QRadioButton("Joint")
        self.cartesian_radio.setChecked(True)
        left_layout.addWidget(self.cartesian_radio)
        left_layout.addWidget(self.joint_radio)
        left_layout.addWidget(QLabel("Speed"))
        for speed in SPEED_LEVELS:
            button = QRadioButton(speed)
            button.setChecked(speed == "Slow")
            left_layout.addWidget(button)
        left_layout.addSpacing(10)
        left_layout.addWidget(QLabel("Control source"))
        self.joystick_label = self._pill("Joystick: unknown")
        self.control_source_label = self._pill("Active: GUI")
        left_layout.addWidget(self.joystick_label)
        left_layout.addWidget(self.control_source_label)
        left_layout.addStretch(1)
        for text, slot in [
            ("Enter Teaching", self.backend.enter_teaching),
            ("Exit Teaching", self.backend.exit_teaching),
            ("Start Homing", self.backend.start_homing),
        ]:
            btn = QPushButton(text)
            btn.clicked.connect(slot)
            left_layout.addWidget(btn)

        right, right_layout = self._panel("Joint Command")
        self.manual_sliders: dict[str, QSlider] = {}
        for joint in JOINTS:
            row = QHBoxLayout()
            row.addWidget(QLabel(joint))
            slider = QSlider(Qt.Horizontal)
            slider.setRange(-3140, 3140)
            slider.sliderReleased.connect(self._preview_slider_pose)
            self.manual_sliders[joint] = slider
            row.addWidget(slider, 1)
            right_layout.addLayout(row)
        preview = QPushButton("Preview Sliders in RViz")
        preview.clicked.connect(self._preview_slider_pose)
        right_layout.addWidget(preview)
        send_row = QHBoxLayout()
        self.manual_joint = QComboBox()
        self.manual_joint.addItems(JOINTS)
        self.manual_target = QDoubleSpinBox()
        self.manual_target.setRange(-3.14, 3.14)
        self.manual_target.setDecimals(3)
        self.manual_target.setSingleStep(0.01)
        send = QPushButton("Send Target")
        send.clicked.connect(self._send_manual_target)
        send_row.addWidget(self.manual_joint)
        send_row.addWidget(self.manual_target)
        send_row.addWidget(send)
        right_layout.addLayout(send_row)
        layout.addWidget(left, 0)
        layout.addWidget(right, 1)
        return page

    def _waypoint_tab(self) -> QWidget:
        page = QWidget()
        layout = QHBoxLayout(page)
        left, left_layout = self._panel("Save Current Pose")
        self.wp_name = QLineEdit()
        self.wp_name.setPlaceholderText("Waypoint name")
        self.wp_desc = QLineEdit()
        self.wp_desc.setPlaceholderText("Description")
        save = QPushButton("Save Waypoint")
        save.clicked.connect(self._save_waypoint)
        left_layout.addWidget(self.wp_name)
        left_layout.addWidget(self.wp_desc)
        left_layout.addWidget(save)
        left_layout.addSpacing(12)
        self.recording_label = self._pill("Inactive - 0 points")
        toggle = QPushButton("Start/Stop Recording")
        toggle.clicked.connect(self._toggle_recording)
        save_rec = QPushButton("Save Recording")
        save_rec.clicked.connect(self._save_recording)
        clear_rec = QPushButton("Clear Recording")
        clear_rec.clicked.connect(self._clear_recording)
        left_layout.addWidget(QLabel("Teaching Recording"))
        left_layout.addWidget(self.recording_label)
        left_layout.addWidget(toggle)
        left_layout.addWidget(save_rec)
        left_layout.addWidget(clear_rec)
        left_layout.addStretch(1)

        right, right_layout = self._panel("Pose Library")
        self.waypoint_list = QListWidget()
        right_layout.addWidget(self.waypoint_list, 1)
        buttons = QHBoxLayout()
        preview = QPushButton("Preview")
        preview.setFixedWidth(130)
        preview.clicked.connect(self._preview_selected_waypoint)
        execute = QPushButton("Plan/Execute")
        execute.setFixedWidth(130)
        execute.clicked.connect(self._execute_selected_waypoint)
        delete = QPushButton("Delete")
        delete.setFixedWidth(130)
        delete.clicked.connect(self._delete_selected_waypoint)
        buttons.addWidget(preview)
        buttons.addWidget(execute)
        buttons.addWidget(delete)
        buttons.addStretch(1)
        right_layout.addLayout(buttons)
        layout.addWidget(left, 0)
        layout.addWidget(right, 1)
        return page

    def _homing_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        panel, panel_layout = self._panel("Homing State Machine")
        start = QPushButton("Start Homing Sequence")
        start.clicked.connect(self.backend.start_homing)
        panel_layout.addWidget(start)
        self.homing_grid = QGridLayout()
        self.homing_labels: dict[str, QLabel] = {}
        for row, step in enumerate(self.state.homing_steps):
            self.homing_grid.addWidget(QLabel(step), row, 0)
            label = self._pill("pending")
            self.homing_labels[step] = label
            self.homing_grid.addWidget(label, row, 1)
        panel_layout.addLayout(self.homing_grid)
        panel_layout.addStretch(1)
        layout.addWidget(panel)
        return page

    def _tuning_tab(self) -> QWidget:
        page = QWidget()
        layout = QHBoxLayout(page)
        left, left_layout = self._panel("PID Parameters")
        self.pid_joint = QComboBox()
        self.pid_joint.addItems(JOINTS)
        self.pid_kp = self._spin(18.0, 0.0, 500.0)
        self.pid_ki = self._spin(0.0, 0.0, 100.0)
        self.pid_kd = self._spin(0.8, 0.0, 100.0)
        for label, widget in [("Joint", self.pid_joint), ("Kp", self.pid_kp), ("Ki", self.pid_ki), ("Kd", self.pid_kd)]:
            left_layout.addWidget(QLabel(label))
            left_layout.addWidget(widget)
        write = QPushButton("Write PID")
        write.clicked.connect(self._write_pid)
        left_layout.addWidget(write)
        self.step_amp = self._spin(0.15, 0.0, 1.0)
        left_layout.addWidget(QLabel("Step amplitude"))
        left_layout.addWidget(self.step_amp)
        run_step = QPushButton("Run Step Test")
        run_step.clicked.connect(self._run_step)
        left_layout.addWidget(run_step)
        self.step_result = self._pill("No step result")
        left_layout.addWidget(self.step_result)
        self.pid_history_list = QListWidget()
        left_layout.addWidget(self.pid_history_list, 1)

        right, right_layout = self._panel("Step Response")
        self.step_plot = MultiLinePlot()
        right_layout.addWidget(self.step_plot, 1)
        layout.addWidget(left, 0)
        layout.addWidget(right, 1)
        return page

    def _tools_tab(self) -> QWidget:
        page = QWidget()
        layout = QHBoxLayout(page)
        left, left_layout = self._panel("Tool Identification")
        self.tool_id_combo = QComboBox()
        self.tool_id_combo.addItems(TOOLS)
        identify = QPushButton("Identify Tool")
        identify.clicked.connect(self._identify_tool)
        self.tool_info = self._pill("Mass: --\nCOM: --\nResidual: --")
        left_layout.addWidget(self.tool_id_combo)
        left_layout.addWidget(identify)
        left_layout.addWidget(self.tool_info)
        left_layout.addStretch(1)

        right, right_layout = self._panel("Tool Library")
        self.tool_list = QListWidget()
        right_layout.addWidget(self.tool_list, 1)
        layout.addWidget(left, 0)
        layout.addWidget(right, 1)
        return page

    def _visualization_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        panel, panel_layout = self._panel("Visualization Host")
        text = QLabel(
            "RViz is managed by the ROS2 bringup launch.\n\n"
            "The console should interact through ROS2 topics, services, and actions while RViz follows /joint_states, "
            "robot_description, TF, markers, and the MoveIt planning scene."
        )
        text.setAlignment(Qt.AlignCenter)
        text.setWordWrap(True)
        text.setObjectName("Pill")
        panel_layout.addWidget(text, 1)
        layout.addWidget(panel)
        return page

    def _logs_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        clear = QPushButton("Clear Log")
        clear.clicked.connect(self._clear_logs)
        layout.addWidget(self.log_box, 1)
        layout.addWidget(clear, 0, Qt.AlignLeft)
        return page

    def _spin(self, value: float, minimum: float, maximum: float) -> QDoubleSpinBox:
        spin = QDoubleSpinBox()
        spin.setRange(minimum, maximum)
        spin.setDecimals(3)
        spin.setSingleStep(0.1)
        spin.setValue(value)
        return spin

    def refresh(self) -> None:
        snap = self.state.snapshot()
        self.status_label.setText(snap["status"])
        self.status_label.setStyleSheet(f"color: {STATUS_COLORS.get(snap['status'], '#e6ebf4')};")
        self.world_label.setText(f"World: {snap['world']}")
        self.world_label.setStyleSheet(f"color: {WORLD_COLORS.get(snap['world'], '#e6ebf4')};")
        self.hardware_label.setText(f"Hardware: {snap['hardware']}")
        self.hardware_label.setStyleSheet(f"color: {HARDWARE_COLORS.get(snap['hardware'], '#e6ebf4')};")
        homing_text = "homed" if snap["homed"] else ("homing" if snap["homing_active"] else "not homed")
        self.homing_state_label.setText(f"Homing: {homing_text}")
        self.homing_state_label.setStyleSheet(f"color: {'#66c9a4' if snap['homed'] else ('#e8b955' if snap['homing_active'] else '#8c99ad')};")
        self.authority_label.setText(f"Authority: {snap['control_source']}")
        self.authority_label.setStyleSheet(f"color: {AUTHORITY_COLORS.get(snap['control_source'], '#e6ebf4')};")
        self.backend_label.setText(f"{snap['backend']} {'connected' if snap['connected'] else 'disconnected'}")
        self.contact_label.setText(snap["contact"])
        self.contact_label.setStyleSheet(f"color: {CONTACT_COLORS.get(snap['contact'], '#e6ebf4')};")
        joystick_text = "Joystick: active" if snap["joystick_active"] else ("Joystick: connected" if snap["joystick_connected"] else "Joystick: not connected")
        self.joystick_label.setText(joystick_text)
        self.joystick_label.setStyleSheet(f"color: {'#66c9a4' if snap['joystick_connected'] else '#8c99ad'};")
        self.control_source_label.setText(f"Active: {snap['control_source']}")
        self.control_source_label.setStyleSheet(f"color: {'#e8b955' if snap['control_source'] == 'Joystick' else '#7ab2f0'};")
        self._set_combo_silent(self.mode_combo, snap["mode"])
        self._set_combo_silent(self.tool_combo, snap["tool"])

        for row, joint in enumerate(JOINTS):
            js = snap["joints"][joint]
            values = [joint, f"{js.current:+.2f}", f"{js.position:+.2f}", f"{js.velocity:+.2f}", f"{js.temperature:.1f}", js.fault]
            for col, value in enumerate(values):
                item = self.joint_table.item(row, col)
                if item is None:
                    item = QTableWidgetItem()
                    self.joint_table.setItem(row, col, item)
                item.setText(value)
                item.setTextAlignment(Qt.AlignCenter)
                if col == 5:
                    item.setForeground(Qt.green if value == "OK" else Qt.yellow)
            slider = self.manual_sliders[joint]
            if not slider.isSliderDown():
                slider.setValue(int(js.position * 1000))

        pose = snap["pose"]
        self.pose_label.setText(
            f"xyz: {pose.xyz[0]:+.3f}, {pose.xyz[1]:+.3f}, {pose.xyz[2]:+.3f} m\n"
            f"rpy: {pose.rpy[0]:+.3f}, {pose.rpy[1]:+.3f}, {pose.rpy[2]:+.3f} rad"
        )
        signal = self.signal_combo.currentText()
        self.signal_plot.set_series(snap["histories"][signal])
        self.step_plot.set_series(snap["step_history"])

        self.recording_label.setText(("Recording" if snap["recording"] else "Inactive") + f" - {snap['recorded_count']} points")
        for step, status in snap["homing_steps"].items():
            if step in self.homing_labels:
                label = self.homing_labels[step]
                label.setText(status)
                label.setStyleSheet(f"color: {HOMING_COLORS.get(status, '#e6ebf4')};")

        if snap["step_results"]:
            result = snap["step_results"]
            self.step_result.setText(
                f"rise={result['rise_time_s']:.2f}s  overshoot={result['overshoot_pct']:.1f}%  settle={result['settling_time_s']:.2f}s"
            )
        elif snap["step_running"]:
            self.step_result.setText("Running...")

        self._refresh_waypoints(snap)
        self._refresh_pid_history(snap)
        self._refresh_tools(snap)
        self.log_box.setPlainText("\n".join(entry.text for entry in snap["logs"][-180:]))

    def _set_combo_silent(self, combo: QComboBox, value: str) -> None:
        if combo.currentText() == value:
            return
        combo.blockSignals(True)
        combo.setCurrentText(value)
        combo.blockSignals(False)

    def _set_tool(self, tool: str) -> None:
        with self.state.lock:
            self.state.tool = tool
        self.state.log(f"Current tool selected: {tool}")
        self.refresh()

    def _send_manual_target(self) -> None:
        self.backend.send_joint_target(self.manual_joint.currentText(), self.manual_target.value())

    def _preview_slider_pose(self) -> None:
        targets = {joint: slider.value() / 1000.0 for joint, slider in self.manual_sliders.items()}
        self.backend.preview_joint_targets(targets)

    def _save_waypoint(self) -> None:
        name = self.wp_name.text().strip()
        if not name:
            self.state.log("Waypoint name is required", "WARN")
            self.refresh()
            return
        snap = self.state.snapshot()
        with self.state.lock:
            self.state.waypoints[name] = {
                "q": [snap["joints"][joint].position for joint in JOINTS],
                "pose_xyz": snap["pose"].xyz,
                "desc": self.wp_desc.text().strip(),
                "tags": ["operator"],
            }
        self.store.save_waypoints(self.state)
        self.state.log(f"Waypoint saved: {name}")
        self.refresh()

    def _refresh_waypoints(self, snap: dict) -> None:
        selected = self.waypoint_list.currentItem().text().split("  ")[0] if self.waypoint_list.currentItem() else ""
        self.waypoint_list.clear()
        for name, wp in snap["waypoints"].items():
            self.waypoint_list.addItem(f"{name}  -  {wp.get('desc', '')}")
        matches = self.waypoint_list.findItems(selected, Qt.MatchStartsWith) if selected else []
        if matches:
            self.waypoint_list.setCurrentItem(matches[0])

    def _selected_waypoint_name(self) -> str:
        item = self.waypoint_list.currentItem()
        return item.text().split("  ")[0] if item else ""

    def _selected_waypoint_targets(self) -> dict[str, float]:
        name = self._selected_waypoint_name()
        waypoint = self.state.snapshot()["waypoints"].get(name)
        if not waypoint:
            return {}
        return {joint: float(target) for joint, target in zip(JOINTS, waypoint["q"])}

    def _preview_selected_waypoint(self) -> None:
        name = self._selected_waypoint_name()
        targets = self._selected_waypoint_targets()
        if not targets:
            return
        self.backend.preview_joint_targets(targets)
        self.state.log(f"Waypoint preview sent: {name}")
        self.refresh()

    def _execute_selected_waypoint(self) -> None:
        name = self._selected_waypoint_name()
        targets = self._selected_waypoint_targets()
        if not targets:
            return
        self.backend.execute_joint_targets(targets)
        self.state.log(f"Waypoint plan/execute sent: {name}")
        self.refresh()

    def _delete_selected_waypoint(self) -> None:
        name = self._selected_waypoint_name()
        if not name:
            return
        with self.state.lock:
            self.state.waypoints.pop(name, None)
        self.store.save_waypoints(self.state)
        self.state.log(f"Waypoint deleted: {name}")
        self.refresh()

    def _toggle_recording(self) -> None:
        snap = self.state.snapshot()
        if not snap["teaching_active"]:
            self.backend.enter_teaching()
        self.backend.set_recording(not snap["recording"])

    def _save_recording(self) -> None:
        with self.state.lock:
            points = list(self.state.recorded_points)
        if not points:
            self.state.log("No teaching points to save", "WARN")
            self.refresh()
            return
        path = self.store.save_teaching(points)
        self.state.log(f"Teaching trajectory saved: {path}")
        self.refresh()

    def _clear_recording(self) -> None:
        with self.state.lock:
            self.state.recorded_points.clear()
        self.state.log("Teaching recording cleared")
        self.refresh()

    def _write_pid(self) -> None:
        self.backend.write_pid(self.pid_joint.currentText(), self.pid_kp.value(), self.pid_ki.value(), self.pid_kd.value())
        self.store.save_pid_history(self.state)
        self.refresh()

    def _run_step(self) -> None:
        self.backend.run_step_test(self.pid_joint.currentText(), self.step_amp.value())

    def _refresh_pid_history(self, snap: dict) -> None:
        self.pid_history_list.clear()
        for item in reversed(snap["pid_history"][-12:]):
            self.pid_history_list.addItem(
                f"{item.get('time', '')}  {item.get('joint')}  Kp={item.get('kp')} Ki={item.get('ki')} Kd={item.get('kd')}"
            )

    def _identify_tool(self) -> None:
        self.backend.identify_tool(self.tool_id_combo.currentText())
        self.store.save_tools(self.state)
        self.refresh()

    def _refresh_tools(self, snap: dict) -> None:
        self.tool_list.clear()
        for name, info in snap["tools"].items():
            self.tool_list.addItem(f"{name}  mass={info.get('mass', '--')} kg  residual={info.get('residual', '--')}")
        info = snap["tools"].get(self.tool_id_combo.currentText(), {})
        self.tool_info.setText(f"Mass: {info.get('mass', '--')} kg\nCOM: {info.get('com', '--')}\nResidual: {info.get('residual', '--')} Nm")

    def _clear_logs(self) -> None:
        with self.state.lock:
            self.state.logs.clear()
        self.state.log("Log cleared")
        self.refresh()


def run_qt_app(window: MainWindow) -> int:
    app = QApplication.instance()
    owns_app = app is None
    if app is None:
        app = QApplication([])
    window.show()
    return app.exec() if owns_app else 0

"""
Simulation controls component.

Provides playback controls for simulation mode.
"""

import logging
from typing import Optional

import streamlit as st

from src.session.global_session import GlobalSession
from src.session.simulation_controller import SimulationController

logger = logging.getLogger(__name__)


class SimulationControls:
    """
    Simulation playback controls.

    Provides:
    - Play/Pause button
    - Speed selector
    - Time scrubber
    - Jump controls
    """

    SPEED_OPTIONS = [1.0, 1.25, 1.5, 1.75, 2.0, 2.5, 3.0]

    @staticmethod
    def render(
        session: GlobalSession,
        controller: Optional[SimulationController] = None
    ) -> None:
        """
        Render simulation controls.

        Args:
            session: Global session state
            controller: Simulation controller (optional)
        """
        if not session.is_simulation():
            return

        col1, col2 = st.columns(2)

        with col1:
            if session.simulation_paused:
                btn = st.button("▶️", use_container_width=True, help="Play")
                if btn:
                    session.toggle_pause()
                    if controller:
                        controller.play()
                    st.rerun()
            else:
                btn = st.button("⏸️", use_container_width=True, help="Pause")
                if btn:
                    session.toggle_pause()
                    if controller:
                        controller.pause()
                    st.rerun()

        with col2:
            btn = st.button("⏮️", use_container_width=True, help="Restart")
            if btn:
                if controller:
                    controller.restart()
                session.simulation_paused = True
                st.rerun()

        speed_labels = [f"{s}x" for s in SimulationControls.SPEED_OPTIONS]
        current_idx = SimulationControls.SPEED_OPTIONS.index(
            session.simulation_speed
        )

        new_speed_idx = st.select_slider(
            "Speed",
            options=range(len(SimulationControls.SPEED_OPTIONS)),
            value=current_idx,
            format_func=lambda x: speed_labels[x]
        )

        new_speed = SimulationControls.SPEED_OPTIONS[new_speed_idx]

        if new_speed != session.simulation_speed:
            session.set_simulation_speed(new_speed)
            if controller:
                controller.set_speed(new_speed)
            st.rerun()

        col1, col2 = st.columns(2)

        with col1:
            btn = st.button("⏪", use_container_width=True, help="-30s")
            if btn:
                if controller:
                    controller.jump_backward(30)
                st.rerun()

        with col2:
            btn = st.button("⏩", use_container_width=True, help="+30s")
            if btn:
                if controller:
                    controller.jump_forward(30)
                st.rerun()

        if controller:
            progress = controller.get_progress() / 100.0
            st.progress(
                progress,
                text=f"{controller.get_progress():.0f}%"
            )

            elapsed = controller.get_elapsed_time()
            remaining = controller.get_remaining_time()
            st.caption(
                f"⏱️ {int(elapsed.total_seconds() // 60)}m "
                f"| ⏳ {int(remaining.total_seconds() // 60)}m left"
            )

        with st.expander("⚙️ Advanced", expanded=False):
            if controller and session.race_context:
                target_lap = st.number_input(
                    "Jump to Lap",
                    min_value=1,
                    max_value=session.race_context.total_laps,
                    value=session.race_context.current_lap,
                    step=1
                )
                if st.button("⏭️ Go to Lap", use_container_width=True):
                    controller.jump_to_lap(target_lap)
                    st.rerun()

            jump_minutes = st.number_input(
                "Jump Minutes",
                min_value=-60,
                max_value=60,
                value=0,
                step=1
            )
            if st.button("⏩ Jump Time", use_container_width=True):
                if controller:
                    controller.jump_forward(jump_minutes * 60)
                st.rerun()

        st.divider()

    @staticmethod
    def get_playback_status(session: GlobalSession) -> str:
        """
        Get human-readable playback status.

        Args:
            session: Global session state

        Returns:
            Status string
        """
        if not session.is_simulation():
            return "N/A (Live Mode)"

        if session.simulation_paused:
            return f"⏸️ Paused ({session.simulation_speed}x)"
        else:
            return f"▶️ Playing ({session.simulation_speed}x)"

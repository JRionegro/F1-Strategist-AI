"""
Live session info component.

Displays information about active and upcoming F1 sessions.
"""

import logging
from typing import List

import streamlit as st

from src.session.global_session import RaceContext
from src.session.live_detector import get_live_session_detector

logger = logging.getLogger(__name__)


class LiveSessionInfo:
    """
    Displays live session information and status.

    Shows:
    - Active session detection
    - Time until session start
    - Upcoming sessions
    """

    @staticmethod
    def render_live_status(live_context: RaceContext) -> None:
        """
        Render live session status banner.

        Args:
            live_context: Active session context
        """
        st.success(
            f"🔴 **LIVE SESSION DETECTED!** | "
            f"{live_context.circuit_name} | "
            f"{live_context.session_type.value} | "
            f"Started: {live_context.session_date.strftime('%H:%M UTC')}"
        )

    @staticmethod
    def render_upcoming_sessions(days_ahead: int = 7) -> None:
        """
        Render upcoming sessions panel.

        Args:
            days_ahead: Number of days to look ahead
        """
        detector = get_live_session_detector()
        upcoming = detector.get_upcoming_sessions(days_ahead)

        if not upcoming:
            st.info("No upcoming sessions in the next 7 days.")
            return

        st.subheader("📅 Upcoming Sessions")

        for session in upcoming[:5]:  # Show max 5
            col1, col2, col3, col4 = st.columns([2, 2, 2, 1])

            with col1:
                st.write(f"**{session.circuit_name}**")

            with col2:
                st.write(session.session_type.value)

            with col3:
                date_str = session.session_date.strftime("%b %d, %H:%M")
                st.write(date_str)

            with col4:
                # Calculate time until
                from datetime import datetime

                now = datetime.now()
                if session.session_date.tzinfo:
                    session_date = session.session_date.replace(tzinfo=None)
                else:
                    session_date = session.session_date

                delta = session_date - now

                if delta.days > 0:
                    st.caption(f"in {delta.days}d")
                elif delta.seconds > 3600:
                    hours = delta.seconds // 3600
                    st.caption(f"in {hours}h")
                else:
                    minutes = delta.seconds // 60
                    st.caption(f"in {minutes}m")

    @staticmethod
    def render_session_countdown(session: RaceContext) -> None:
        """
        Render countdown to session start.

        Args:
            session: Session context
        """
        from datetime import datetime

        now = datetime.now()
        session_date = session.session_date

        if session_date.tzinfo:
            session_date = session_date.replace(tzinfo=None)

        delta = session_date - now

        if delta.total_seconds() > 0:
            # Session hasn't started
            days = delta.days
            hours = delta.seconds // 3600
            minutes = (delta.seconds % 3600) // 60

            if days > 0:
                countdown = f"{days}d {hours}h {minutes}m"
            elif hours > 0:
                countdown = f"{hours}h {minutes}m"
            else:
                countdown = f"{minutes}m"

            st.info(
                f"⏱️ Session starts in: **{countdown}** | "
                f"{session_date.strftime('%b %d, %H:%M UTC')}"
            )
        else:
            # Session in progress or ended
            elapsed = -delta
            hours = int(elapsed.total_seconds() // 3600)
            minutes = int((elapsed.total_seconds() % 3600) // 60)

            if hours > 0:
                elapsed_str = f"{hours}h {minutes}m"
            else:
                elapsed_str = f"{minutes}m"

            st.success(
                f"🔴 **LIVE** | Elapsed: {elapsed_str} | "
                f"{session.session_type.value}"
            )

    @staticmethod
    def render_sidebar_live_indicator(has_live_session: bool) -> None:
        """
        Render live session indicator in sidebar.

        Args:
            has_live_session: Whether there's an active session
        """
        if has_live_session:
            st.sidebar.markdown(
                """
                <div style="
                    background-color: #ff0000;
                    color: white;
                    padding: 10px;
                    border-radius: 5px;
                    text-align: center;
                    font-weight: bold;
                    margin-bottom: 10px;
                    animation: pulse 2s infinite;
                ">
                    🔴 LIVE SESSION
                </div>
                <style>
                    @keyframes pulse {
                        0%, 100% { opacity: 1; }
                        50% { opacity: 0.7; }
                    }
                </style>
                """,
                unsafe_allow_html=True
            )

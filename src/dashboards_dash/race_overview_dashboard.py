"""
Race Overview Dashboard - Real-time leaderboard using OpenF1 APIs.

Shows live positions, gaps, tire compounds using Intervals API for accuracy.
"""

import logging
from typing import Optional
from datetime import datetime

import dash_bootstrap_components as dbc
import pandas as pd
import requests
from dash import dash_table, html

logger = logging.getLogger(__name__)

# Tire compound colors
TIRE_COLORS = {
    "SOFT": "#FF0000",
    "MEDIUM": "#FFA500",
    "HARD": "#FFFFFF",
    "INTERMEDIATE": "#00FF00",
    "WET": "#0000FF",
}

# Team colors (2025 season)
TEAM_COLORS = {
    'Red Bull Racing': '#3671C6',
    'Ferrari': '#E8002D',
    'Mercedes': '#27F4D2',
    'McLaren': '#FF8000',
    'Aston Martin': '#229971',
    'Alpine': '#FF87BC',
    'Williams': '#64C4FF',
    'RB': '#6692FF',
    'Kick Sauber': '#52E252',
    'Haas F1 Team': '#B6BABD',
}


class RaceOverviewDashboard:
    """Real-time leaderboard dashboard using OpenF1 APIs."""

    def __init__(self, openf1_provider):
        """
        Initialize Race Overview Dashboard.

        Args:
            openf1_provider: OpenF1DataProvider instance
        """
        self.provider = openf1_provider
        self._cached_session_key = None
        self._cached_positions = None
        self._cached_intervals = None
        self._cached_stints = None
        self._cached_drivers = None

    def render(
        self,
        session_key: Optional[int] = None,
        simulation_time: Optional[float] = None,
        session_start_time: Optional[pd.Timestamp] = None
    ):
        """
        Render the Race Overview Dashboard with real-time leaderboard.

        Args:
            session_key: OpenF1 session key
            simulation_time: Current simulation time in seconds from session start
            session_start_time: Session start timestamp from SimulationController

        Returns:
            Dash component tree for the dashboard
        """
        if session_key is None:
            return html.Div(
                [
                    html.I(
                        className="fas fa-flag-checkered fa-3x mb-3",
                        style={"color": "#e10600"}
                    ),
                    html.H5("No session loaded", className="text-muted"),
                    html.P(
                        "Please select a race session from the sidebar.",
                        className="small text-muted"
                    ),
                ],
                className="text-center p-5",
            )

        try:
            logger.info(
                f"Loading Race Overview for session {session_key} "
                f"at simulation time {simulation_time}s"
            )

            # Cache data to avoid 429 rate limiting from multiple API calls
            if (
                self._cached_session_key != session_key or
                self._cached_positions is None
            ):
                logger.info(
                    f"Loading fresh data for session {session_key} "
                    f"(cache miss)"
                )
                try:
                    positions = self.provider.get_positions(
                        session_key=session_key
                    )
                    intervals = self.provider.get_intervals(
                        session_key=session_key
                    )
                    stints = self.provider.get_stints(session_key=session_key)
                    drivers = self.provider.get_drivers(session_key=session_key)
                    
                    # Only cache if we got valid data (not empty due to 429)
                    if not positions.empty:
                        self._cached_session_key = session_key
                        self._cached_positions = positions
                        self._cached_intervals = intervals
                        self._cached_stints = stints
                        self._cached_drivers = drivers
                        logger.info(
                            f"Cached {len(positions)} position records, "
                            f"{len(intervals)} intervals, {len(stints)} stints, "
                            f"{len(drivers)} drivers"
                        )
                    else:
                        logger.warning(
                            "Got empty data from API (likely 429), "
                            "using previous cache if available"
                        )
                        # Use previous cache if available
                        if self._cached_positions is not None:
                            positions = self._cached_positions
                            intervals = self._cached_intervals
                            stints = self._cached_stints
                            drivers = self._cached_drivers
                        else:
                            # No cache available, show error
                            return html.Div(
                                [
                                    html.I(
                                        className="fas fa-hourglass-half fa-3x mb-3",
                                        style={"color": "#ffc107"}
                                    ),
                                    html.H5(
                                        "API Rate Limit Reached",
                                        className="text-warning"
                                    ),
                                    html.P(
                                        "The OpenF1 API is temporarily rate-limiting requests. "
                                        "The system is automatically retrying with exponential backoff...",
                                        className="small text-muted mb-2"
                                    ),
                                    html.P(
                                        "Please wait 5-10 seconds and the session will load automatically.",
                                        className="small text-muted"
                                    ),
                                    html.Div(
                                        [
                                            html.Div(
                                                className="spinner-border text-warning mt-3",
                                                role="status"
                                            ),
                                            html.Span(
                                                "Retrying...",
                                                className="sr-only"
                                            )
                                        ]
                                    )
                                ],
                                className="text-center p-5",
                            )
                except requests.HTTPError as e:
                    if e.response and e.response.status_code == 429:
                        logger.error("Rate limit exceeded after retries")
                        return html.Div(
                            [
                                html.I(
                                    className="fas fa-clock fa-3x mb-3",
                                    style={"color": "#dc3545"}
                                ),
                                html.H5(
                                    "API Rate Limit Exceeded",
                                    className="text-danger"
                                ),
                                html.P(
                                    "Too many requests to OpenF1 API. "
                                    "Please wait 1-2 minutes before changing sessions.",
                                    className="small text-muted mb-2"
                                ),
                                html.P(
                                    "Tip: Avoid switching sessions rapidly to prevent rate limiting.",
                                    className="small text-info"
                                ),
                            ],
                            className="text-center p-5",
                        )
                    else:
                        logger.error(f"HTTP error loading data: {e}")
                        # Try to use cache if available
                        if self._cached_positions is not None:
                            logger.info("Using cached data due to HTTP error")
                            positions = self._cached_positions
                            intervals = self._cached_intervals
                            stints = self._cached_stints
                            drivers = self._cached_drivers
                        else:
                            return html.Div(
                                [
                                    html.I(
                                        className="fas fa-exclamation-circle fa-3x mb-3",
                                        style={"color": "#dc3545"}
                                    ),
                                    html.H5(
                                        "Error Loading Session",
                                        className="text-danger"
                                    ),
                                    html.P(
                                        f"HTTP Error: {str(e)}",
                                        className="small text-muted"
                                    ),
                                ],
                                className="text-center p-5",
                            )
                except Exception as e:
                    logger.error(f"Error loading data: {e}")
                    # Try to use cache if available
                    if self._cached_positions is not None:
                        logger.info("Using cached data due to error")
                        positions = self._cached_positions
                        intervals = self._cached_intervals
                        stints = self._cached_stints
                        drivers = self._cached_drivers
                    else:
                        raise
            else:
                logger.info(f"Using cached data for session {session_key}")
                positions = self._cached_positions
                intervals = self._cached_intervals
                stints = self._cached_stints
                drivers = self._cached_drivers

            if positions.empty:
                return html.Div(
                    [
                        html.I(
                            className="fas fa-exclamation-triangle fa-3x mb-3",
                            style={"color": "#ffc107"}
                        ),
                        html.H5(
                            "No position data available",
                            className="text-warning"
                        ),
                        html.P(
                            "This session may not have started yet "
                            "or data is not available.",
                            className="small text-muted"
                        ),
                    ],
                    className="text-center p-5",
                )

            # Filter positions by simulation time
            if simulation_time is not None and session_start_time is not None:
                # Convert simulation_time to absolute timestamp
                # using session_start_time from SimulationController
                current_timestamp = session_start_time + pd.Timedelta(
                    seconds=simulation_time
                )
                
                logger.info(
                    f"Current simulation timestamp: {current_timestamp} "
                    f"(session_start={session_start_time}, "
                    f"elapsed={simulation_time:.1f}s)"
                )
                
                # Get all positions at or before current simulation time
                filtered_positions = positions[
                    positions['Timestamp'] <= current_timestamp
                ]
                
                logger.info(
                    f"Filtered positions: {len(filtered_positions)} out of "
                    f"{len(positions)} at time {simulation_time:.1f}s"
                )
                
                if filtered_positions.empty:
                    # No data yet at this time
                    latest_time = session_start_time
                    latest_positions = pd.DataFrame()
                else:
                    # Get the MOST RECENT position for EACH driver
                    # (not just drivers at the exact latest timestamp)
                    latest_positions = (
                        filtered_positions
                        .sort_values('Timestamp')
                        .groupby('DriverNumber')
                        .tail(1)
                        .sort_values('Position')
                    )
                    latest_time = filtered_positions['Timestamp'].max()
                    logger.info(
                        f"Latest positions (per driver) at {latest_time}: "
                        f"{len(latest_positions)} drivers"
                    )
            else:
                # No simulation time - use all data (latest per driver)
                latest_positions = (
                    positions
                    .sort_values('Timestamp')
                    .groupby('DriverNumber')
                    .tail(1)
                    .sort_values('Position')
                )
                latest_time = positions['Timestamp'].max()

            # Merge with intervals for gap information
            if (
                intervals is not None and
                not intervals.empty and
                not latest_positions.empty
            ):
                # Filter intervals by simulation time
                if simulation_time is not None and session_start_time is not None:
                    current_timestamp = session_start_time + pd.Timedelta(
                        seconds=simulation_time
                    )
                    filtered_intervals = intervals[
                        intervals['Timestamp'] <= current_timestamp
                    ]
                    logger.info(
                        f"Filtered intervals: {len(filtered_intervals)} out of "
                        f"{len(intervals)}"
                    )
                    if not filtered_intervals.empty:
                        # Get the MOST RECENT interval for EACH driver
                        latest_intervals = (
                            filtered_intervals
                            .sort_values('Timestamp')
                            .groupby('DriverNumber')
                            .tail(1)
                        )
                        latest_interval_time = filtered_intervals['Timestamp'].max()
                        logger.info(
                            f"Latest intervals (per driver) at {latest_interval_time}: "
                            f"{len(latest_intervals)} records"
                        )
                    else:
                        latest_intervals = pd.DataFrame()
                        logger.warning("No intervals available at this time")
                else:
                    # Get the most recent interval for each driver
                    latest_intervals = (
                        intervals
                        .sort_values('Timestamp')
                        .groupby('DriverNumber')
                        .tail(1)
                    )
                    latest_interval_time = intervals['Timestamp'].max()
                
                if not latest_intervals.empty:
                    # Merge positions with intervals, stints, and drivers
                    leaderboard_data = latest_positions.merge(
                    latest_intervals[[
                        'DriverNumber',
                        'GapToLeader',
                        'Interval'
                    ]],
                    on='DriverNumber',
                    how='left'
                )
                    logger.info(
                        f"Merged data: {len(leaderboard_data)} rows with "
                        f"gaps/intervals"
                    )
                else:
                    leaderboard_data = latest_positions.copy()
                    leaderboard_data['GapToLeader'] = 0.0
                    leaderboard_data['Interval'] = 0.0
                    logger.warning(
                        "Using positions without intervals (no interval data)"
                    )
            else:
                leaderboard_data = latest_positions.copy()
                leaderboard_data['GapToLeader'] = 0.0
                leaderboard_data['Interval'] = 0.0
                logger.warning(
                    "Using positions without intervals "
                    "(intervals empty or positions empty)"
                )

            # Get REAL lap data from OpenF1 API (ALWAYS, not just when stints exist)
            try:
                logger.info(f"\n{'='*80}")
                logger.info(f"CALLING OPENF1 API get_laps()")
                logger.info(f"{'='*80}")
                logger.info(f"session_key: {session_key}")
                logger.info(f"simulation_time: {simulation_time}")
                
                all_laps = self.provider.get_laps(
                    session_key=session_key
                )
                
                logger.info(f"\n{'='*80}")
                logger.info(f"OPENF1 API RESPONSE")
                logger.info(f"{'='*80}")
                logger.info(f"Total lap records received: {len(all_laps)}")
                if not all_laps.empty:
                    logger.info(f"Columns in response: {all_laps.columns.tolist()}")
                    logger.info(f"Unique lap numbers: {sorted(all_laps['LapNumber'].unique())}")
                    logger.info(f"Unique driver numbers: {sorted(all_laps['DriverNumber'].unique())}")
                    logger.info(f"First 5 rows:\n{all_laps.head()}")
                    
                    # DETAILED ANALYSIS: First 5 laps structure
                    logger.info(f"\n{'='*80}")
                    logger.info(f"DETAILED ANALYSIS OF FIRST 5 LAPS")
                    logger.info(f"{'='*80}")
                    for lap_num in [1, 2, 3, 4, 5]:
                        lap_data = all_laps[all_laps['LapNumber'] == lap_num]
                        if not lap_data.empty:
                            logger.info(f"\n--- LAP {lap_num} ---")
                            logger.info(f"Total records: {len(lap_data)}")
                            logger.info(f"Drivers in this lap: {sorted(lap_data['DriverNumber'].unique())}")
                            
                            # Check timestamps
                            sample_driver = lap_data.iloc[0]
                            logger.info(f"Sample driver #{sample_driver['DriverNumber']}:")
                            logger.info(f"  LapStartTime: {sample_driver.get('LapStartTime', 'N/A')}")
                            logger.info(f"  LapEndTime: {sample_driver.get('LapEndTime', 'N/A')}")
                            logger.info(f"  DateStart: {sample_driver.get('DateStart', 'N/A')}")
                            
                            # Count how many have valid timestamps
                            valid_start = lap_data['LapStartTime'].notna().sum()
                            valid_end = lap_data['LapEndTime'].notna().sum()
                            logger.info(f"  Valid LapStartTime: {valid_start}/{len(lap_data)}")
                            logger.info(f"  Valid LapEndTime: {valid_end}/{len(lap_data)}")
                        else:
                            logger.info(f"\n--- LAP {lap_num}: NO DATA ---")
            except Exception as e:
                logger.error(f"Error loading lap data: {e}")
                all_laps = pd.DataFrame()

            # Calculate dynamic tire age from stints based on ACTUAL lap numbers
            if stints is not None and not stints.empty:
                logger.info(
                    f"Calculating tire age for {len(leaderboard_data)} "
                    f"drivers with {len(stints)} stints"
                )
                
                # Build lists for tire data
                tire_ages = []
                compounds = []
                pit_stops = []
                
                # DEBUG: Log all driver numbers in leaderboard
                driver_numbers_in_leaderboard = leaderboard_data['DriverNumber'].tolist()
                logger.info(f"ALL DRIVERS IN LEADERBOARD: {driver_numbers_in_leaderboard}")
                logger.info(f"Is ALO (#14) in leaderboard? {14 in driver_numbers_in_leaderboard}")
                
                # Calculate tire age for each driver based on ACTUAL lap
                for idx, row in leaderboard_data.iterrows():
                    driver_num = row['DriverNumber']
                    
                    tire_age = 0
                    compound = 'UNKNOWN'
                    current_lap = 1
                    driver_laps = pd.DataFrame()  # Initialize to fix Pylance error
                    
                    # Get driver's actual current lap from lap data PER DRIVER
                    is_alonso = (driver_num == 14)
                    if not all_laps.empty and 'DriverNumber' in all_laps.columns:
                        # CRITICAL: Filter laps for THIS driver ONLY
                        driver_laps = all_laps[
                            all_laps['DriverNumber'] == driver_num
                        ].copy()
                        
                        # DEBUG: Check if ALO has lap data
                        if is_alonso:
                            logger.info(f"\n{'='*80}")
                            logger.info(f"ALO DRIVER-SPECIFIC LAP FILTERING")
                            logger.info(f"{'='*80}")
                            logger.info(f"DriverNumber filter: {driver_num}")
                            logger.info(f"Total laps in all_laps: {len(all_laps)}")
                            logger.info(f"ALO laps after filtering: {len(driver_laps)} laps")
                            logger.info(f"ALO columns: {driver_laps.columns.tolist()}")
                            logger.info(f"ALO simulation_time: {simulation_time}")
                            logger.info(f"ALO session_start_time: {session_start_time}")
                            if len(driver_laps) > 0:
                                logger.info(f"ALO lap numbers: {sorted(driver_laps['LapNumber'].unique())}")
                        
                        if not driver_laps.empty:
                            if (
                                simulation_time is not None
                                and session_start_time is not None
                                and 'LapStartTime' in driver_laps.columns
                            ):
                                # Get the driver's first lap start time
                                driver_laps_sorted = driver_laps.sort_values('LapNumber')
                                first_lap_start = driver_laps_sorted['LapStartTime'].iloc[0]
                                last_lap_start = driver_laps_sorted['LapStartTime'].iloc[-1]
                                
                                # Calculate simulation timestamp relative to session start
                                # Ensure both values are not None before arithmetic
                                sim_timestamp = session_start_time + pd.Timedelta(
                                    seconds=float(simulation_time)
                                )
                                
                                # Initialize started_laps for logging
                                started_laps = pd.DataFrame()
                                
                                # Filter out laps with NaT (formation lap) FIRST
                                valid_laps = driver_laps[
                                    driver_laps['LapStartTime'].notna()
                                ].copy()
                                
                                if valid_laps.empty:
                                    current_lap = int(valid_laps['LapNumber'].min()) if not valid_laps.empty else 2
                                elif simulation_time == 0:
                                    # At simulation start, use the FIRST valid lap from OpenF1
                                    # (typically lap 2, which is the first racing lap after formation)
                                    current_lap = int(valid_laps['LapNumber'].min())
                                else:
                                    # Find the lap currently IN PROGRESS
                                    # This is the lap that started MOST RECENTLY before sim_timestamp
                                    # and either hasn't ended yet OR ended after sim_timestamp
                                    
                                    started_laps = valid_laps[
                                        valid_laps['LapStartTime'] <= sim_timestamp
                                    ]
                                    
                                    if not started_laps.empty and 'LapNumber' in started_laps.columns:
                                        # Sort by LapStartTime descending to get most recent lap first
                                        started_laps_sorted = started_laps.sort_values(
                                            'LapStartTime', ascending=False
                                        )
                                        
                                        # The current lap is the FIRST (most recent) lap that:
                                        # 1. Started before sim_timestamp
                                        # 2. Either has no end time OR ended after sim_timestamp
                                        for _, lap_row in started_laps_sorted.iterrows():
                                            lap_start = lap_row['LapStartTime']
                                            lap_end = lap_row.get('LapEndTime', pd.NaT)
                                            
                                            # If lap has no end time, it's the current lap
                                            if pd.isna(lap_end):
                                                current_lap = int(lap_row['LapNumber'])
                                                break
                                            # If lap ended after sim_timestamp, it's still in progress
                                            elif lap_end > sim_timestamp:
                                                current_lap = int(lap_row['LapNumber'])
                                                break
                                        else:
                                            # If no lap found, use the first one that started
                                            current_lap = int(started_laps_sorted.iloc[0]['LapNumber'])
                                    else:
                                        current_lap = 1
                                
                                # DETAILED LOGGING FOR ALONSO
                                if is_alonso:
                                    logger.info(f"\n{'='*80}")
                                    logger.info(f"ALO CURRENT LAP CALCULATION (DRIVER #14 ONLY)")
                                    logger.info(f"{'='*80}")
                                    logger.info(f"sim_timestamp: {sim_timestamp}")
                                    logger.info(f"valid_laps count: {len(valid_laps)}")
                                    logger.info(f"started_laps count: {len(started_laps)}")
                                    logger.info(f"Driver Number: {driver_num}")
                                    logger.info(f"Simulation Time: {simulation_time}s")
                                    logger.info(f"Session Start Time: {session_start_time}")
                                    logger.info(f"Sim Timestamp: {sim_timestamp}")
                                    logger.info(f"First Lap Start: {first_lap_start}")
                                    logger.info(f"Last Lap Start: {last_lap_start}")
                                    logger.info(f"Total Laps in Data: {len(driver_laps_sorted)}")
                                    logger.info(f"Started Laps Count: {len(started_laps)}")
                                    logger.info(f"CALCULATED CURRENT LAP: {current_lap}")
                                    logger.info(f"Time since first lap: {(sim_timestamp - first_lap_start).total_seconds()}s")
                                    if not started_laps.empty:
                                        logger.info(f"Last started lap number: {started_laps['LapNumber'].max()}")
                                        logger.info(f"Last started lap LapStartTime: {started_laps.iloc[-1]['LapStartTime']}")
                            else:
                                # If no simulation time, use latest lap
                                if 'LapNumber' in driver_laps.columns:
                                    current_lap = int(driver_laps['LapNumber'].max())
                                else:
                                    current_lap = 1
                    
                    # Get driver's stints sorted by stint number
                    driver_stints = stints[
                        stints['DriverNumber'] == driver_num
                    ].sort_values('StintNumber')
                    
                    # DEBUG: Log stint details for ALO
                    if is_alonso:
                        logger.info(f"\n--- RAW STINT DATA FOR ALO ---")
                        for idx, s in driver_stints.iterrows():
                            logger.info(
                                f"  Stint {s.get('StintNumber', 'N/A')}: "
                                f"StintStart={s.get('StintStart', 'N/A')}, "
                                f"StintEnd={s.get('StintEnd', 'N/A')}, "
                                f"Compound={s.get('Compound', 'N/A')}, "
                                f"TyreAge={s.get('TyreAge', 'N/A')}"
                            )
                        logger.info(f"Current lap for pit stop calculation: {current_lap}")
                        logger.info(f"⚠️ CRITICAL: Is this the REAL lap number we're on?")
                    
                    # Calculate number of pit stops COMPLETED up to current lap
                    # A pit stop is COMPLETED when driver STARTS a new stint (not stint 1)
                    # IMPORTANT: Only count if current lap is PAST the stint start lap
                    num_pit_stops = 0
                    for _, stint in driver_stints.iterrows():
                        stint_start = stint.get('StintStart', 0)
                        stint_number = stint.get('StintNumber', 1)
                        
                        if is_alonso:
                            logger.info(
                                f"  Checking stint {stint_number}: "
                                f"start={stint_start}, current_lap={current_lap}, "
                                f"started={stint_start <= current_lap if pd.notna(stint_start) else False}"
                            )
                        
                        # Pit stop completed = STARTED a new stint (not stint 1)
                        # BUT: only if current lap > stint start (already in that stint)
                        if pd.notna(stint_start) and current_lap > stint_start and stint_number > 1:
                            num_pit_stops += 1
                            if is_alonso:
                                logger.info(f"    -> Pit stop counted! Total now: {num_pit_stops}")
                    
                    if not driver_stints.empty:
                        # Find current stint based on actual lap number
                        current_stint = None
                        for _, stint in driver_stints.iterrows():
                            stint_start = stint.get('StintStart', 0)
                            stint_end = stint.get('StintEnd', 999)
                            
                            if pd.notna(stint_start) and stint_start <= current_lap:
                                if pd.isna(stint_end) or current_lap <= stint_end:
                                    current_stint = stint
                                    break
                        
                        # If no exact match, use last stint
                        if current_stint is None:
                            current_stint = driver_stints.iloc[-1]
                        
                        # Calculate tire age using REAL lap numbers from OpenF1
                        # Note: Formation lap (lap 1) does wear tires
                        # Internal calculation uses actual OpenF1 lap numbers
                        tyre_age_at_start = max(
                            0, int(current_stint.get('TyreAge', 1)) - 1
                        )
                        stint_start_lap = int(current_stint.get('StintStart', 1))
                        stint_end_lap = current_stint.get('StintEnd', 'N/A')
                        stint_number = int(current_stint.get('StintNumber', 1))
                        
                        # Calculate COMPLETED laps in this stint (not just started)
                        # A lap is completed ONLY if its LapEndTime has passed
                        completed_laps_in_stint = 0
                        
                        # Only calculate if we have valid timestamps (fix Pylance errors)
                        if (
                            session_start_time is not None 
                            and simulation_time is not None
                            and not driver_laps.empty
                        ):
                            sim_timestamp = session_start_time + pd.Timedelta(
                                seconds=float(simulation_time)
                            )
                        
                            for lap_num in range(stint_start_lap, current_lap + 1):
                                lap_row = driver_laps[
                                    driver_laps['LapNumber'] == lap_num
                                ]
                                if not lap_row.empty:
                                    lap_end = lap_row.iloc[0].get('LapEndTime', pd.NaT)
                                    # Count as completed ONLY if LapEndTime exists and has passed
                                    if pd.notna(lap_end) and lap_end <= sim_timestamp:
                                        completed_laps_in_stint += 1
                        
                        # INTERNAL tire age (uses COMPLETED laps only)
                        tire_age_internal = max(
                            0,
                            tyre_age_at_start + completed_laps_in_stint
                        )
                        
                        # VISUAL tire age: In first stint, formation lap is already counted
                        # in tyre_age_at_start (which is 0 + formation = starts at 0 after -1 adjustment)
                        # So tire_age_visual = tire_age_internal (formation lap already counted)
                        tire_age = tire_age_internal
                        
                        compound = current_stint.get('Compound', 'UNKNOWN')
                        
                        # DETAILED LOGGING FOR ALONSO
                        if is_alonso:
                            logger.info(f"\n--- ALO TIRE AGE CALCULATION (DRIVER #14) ---")
                            logger.info(f"✅ INTERNAL Current lap (OpenF1): {current_lap}")
                            logger.info(f"📊 VISUAL Current lap (Racing): {current_lap - 1}")
                            logger.info(f"⚠️  THIS IS CALCULATED FROM DRIVER #14 LAPS ONLY")
                            logger.info(f"Total Stints: {len(driver_stints)}")
                            logger.info(f"🔧 Pit Stops CALCULATED: {num_pit_stops}")
                            logger.info(f"Current Stint Number: {stint_number}")
                            logger.info(f"Stint Start Lap: {stint_start_lap}")
                            logger.info(f"Stint End Lap: {stint_end_lap}")
                            logger.info(
                                f"Tyre Age at Start of this stint: {tyre_age_at_start}"
                            )
                            logger.info(
                                f"Laps COMPLETED in this stint: {completed_laps_in_stint} (NOT just started)"
                            )
                            logger.info(f"Current Compound: {compound}")
                            logger.info(f"🏁 TIRE AGE (includes formation lap): {tire_age}")
                            logger.info(
                                f"Formula: {tyre_age_at_start} + "
                                f"{completed_laps_in_stint} COMPLETED laps = {tire_age}"
                            )
                            logger.info(f"\nAll stints summary:")
                            for _, s in driver_stints.iterrows():
                                logger.info(
                                    f"  Stint {s.get('StintNumber', '?')}: "
                                    f"Laps {s.get('StintStart', '?')}-{s.get('StintEnd', '?')}, "
                                    f"{s.get('Compound', '?')}, "
                                    f"Age at start: {s.get('TyreAge', '?')}"
                                )
                            logger.info(f"{'='*80}\n")
                        
                        # Debug logging for first driver
                        elif idx == 0:
                            logger.info(
                                f"Driver #{driver_num}: REAL lap={current_lap}, "
                                f"stint_start={stint_start_lap}, "
                                f"tyre_age_at_start={tyre_age_at_start}, "
                                f"calculated_age={tire_age}, compound={compound}"
                            )
                    
                    tire_ages.append(tire_age)
                    compounds.append(compound)
                    pit_stops.append(num_pit_stops)
                
                # Assign all at once
                leaderboard_data['TyreAge'] = tire_ages
                leaderboard_data['Compound'] = compounds
                leaderboard_data['PitStops'] = pit_stops
                
                # Log sample tire data for debugging
                if not leaderboard_data.empty:
                    sample = leaderboard_data.iloc[0]
                    logger.info(f"Sample tire data - Driver #{sample['DriverNumber']}: {sample['Compound']} ({sample['TyreAge']} laps), Pit Stops: {sample['PitStops']}")
                    
                    # Find ALO to log his specific data
                    alo_data = leaderboard_data[leaderboard_data['DriverNumber'] == '14']
                    if not alo_data.empty:
                        alo_row = alo_data.iloc[0]
                        logger.info(f"\n🔍 ALO FINAL DATA IN LEADERBOARD:")
                        logger.info(f"  Driver #: {alo_row['DriverNumber']}")
                        logger.info(f"  Position: {alo_row.get('Position', 'N/A')}")
                        logger.info(f"  Tire Age: {alo_row['TyreAge']} laps")
                        logger.info(f"  Compound: {alo_row['Compound']}")
                        logger.info(f"  Pit Stops: {alo_row['PitStops']}")
                        logger.info(f"  👉 These values will be DISPLAYED in the UI")
            else:
                logger.warning("No stint data available for tire age calculation")
                leaderboard_data['Compound'] = 'UNKNOWN'
                leaderboard_data['TyreAge'] = 0
                leaderboard_data['PitStops'] = 0

            # Merge with drivers for names and team
            if drivers is not None and not drivers.empty:
                leaderboard_data = leaderboard_data.merge(
                    drivers[[
                        'DriverNumber',
                        'Abbreviation',
                        'TeamName'
                    ]],
                    on='DriverNumber',
                    how='left',
                    suffixes=('', '_driver')
                )

            # Build leaderboard table
            leaderboard_table = self._build_leaderboard_table(
                leaderboard_data
            )

            # Session info is embedded in the data
            session_name = 'Race'
            meeting_name = 'Grand Prix'

            # Build dashboard
            return dbc.Container(
                [
                    # Leaderboard (header removed to save space)
                    dbc.Row(
                        [
                            dbc.Col(
                                leaderboard_table,
                                width=12,
                            ),
                        ],
                        style={"margin": "0"},
                    ),
                ],
                fluid=True,
                className="p-0",
                style={"overflow": "hidden", "height": "100%"},
            )

        except Exception as e:
            logger.error(
                f"Error rendering Race Overview Dashboard: {e}",
                exc_info=True
            )
            return html.Div(
                [
                    html.I(
                        className="fas fa-times-circle fa-3x mb-3",
                        style={"color": "#dc3545"}
                    ),
                    html.H5("Error loading dashboard", className="text-danger"),
                    html.P(f"{str(e)}", className="small text-muted"),
                ],
                className="text-center p-5",
            )

    def _build_leaderboard_table(self, leaderboard_data: pd.DataFrame):
        """
        Build leaderboard table with positions, gaps, and tire info.

        Args:
            leaderboard_data: DataFrame with position, driver, gap, tire data

        Returns:
            dash_table.DataTable component
        """
        if leaderboard_data.empty:
            return html.Div(
                "No leaderboard data available",
                className="text-center text-muted p-3",
            )

        # Prepare table data
        table_rows = []
        for _, row in leaderboard_data.iterrows():
            position = int(row['Position'])
            driver = row.get(
                'Abbreviation',
                f"#{row['DriverNumber']}"
            )

            # Format gaps
            gap_to_leader = row.get('GapToLeader', None)
            if position == 1:
                gap_str = "Leader"
            elif gap_to_leader is None or pd.isna(gap_to_leader):
                gap_str = "-"
            elif abs(gap_to_leader) < 0.001:  # Very close to 0
                gap_str = "-"
            else:
                gap_str = f"+{gap_to_leader:.3f}s"

            interval = row.get('Interval', None)
            if position == 1:
                interval_str = "-"
            elif interval is None or pd.isna(interval):
                interval_str = "-"
            elif abs(interval) < 0.001:  # Very close to 0
                interval_str = "-"
            else:
                interval_str = f"+{interval:.3f}s"

            # Tire info
            compound = row.get('Compound', 'UNKNOWN')
            tire_age = row.get('TyreAge', 0)
            if pd.isna(tire_age):
                tire_age = 0

            # Map compound to color circle (using emoji circles for compactness)
            tire_colors = {
                'SOFT': '🔴',
                'MEDIUM': '🟡',
                'HARD': '⚪',
                'INTERMEDIATE': '🟢',
                'WET': '🔵',
                'UNKNOWN': '⚫'
            }
            tire_circle = tire_colors.get(compound, '⚫')
            
            # Display tire age (already correctly calculated including formation lap)
            tire_str = f"{tire_circle} {int(tire_age)}"
            
            # Pit stops
            pit_stops = row.get('PitStops', 0)
            if pd.isna(pit_stops):
                pit_stops = 0

            # Get team name for color mapping
            team_name = row.get('TeamName', '')

            table_rows.append({
                "Pos": position,
                "Driver": driver,
                "Gap": gap_str,
                "Interval": interval_str,
                "Tire": tire_str,
                "Stops": int(pit_stops),
                "TeamName": team_name,  # Hidden column for conditional styling
            })

        # Build style_data_conditional with team colors for Driver column
        style_conditional = [
            # Highlight leader (keep white text for all columns except Driver)
            {
                "if": {"filter_query": "{Pos} = 1"},
                "backgroundColor": "#FFD700",
                "fontWeight": "bold",
            },
            # Highlight top 3
            {
                "if": {"filter_query": "{Pos} <= 3"},
                "backgroundColor": "#3a3a3a",
            },
        ]
        
        # Add team color rules for Driver column
        for team_name, color in TEAM_COLORS.items():
            style_conditional.append({
                "if": {
                    "filter_query": f"{{TeamName}} = '{team_name}'",
                    "column_id": "Driver"
                },
                "color": color,
                "fontWeight": "bold",
            })

        # Create table
        return dash_table.DataTable(
            id="race-overview-table",
            columns=[
                {"name": "Pos", "id": "Pos"},
                {"name": "Driver", "id": "Driver"},
                {"name": "Gap", "id": "Gap"},
                {"name": "Int", "id": "Interval"},
                {"name": "Tire", "id": "Tire"},
                {"name": "Stops", "id": "Stops"},
                {"name": "", "id": "TeamName"},  # Hidden via CSS
            ],
            data=table_rows,
            style_table={
                "overflowX": "auto",
                "backgroundColor": "#1e1e1e",
                "maxHeight": "420px",
                "overflowY": "auto"
            },
            style_header={
                "backgroundColor": "#e10600",
                "color": "white",
                "fontWeight": "bold",
                "textAlign": "center",
                "border": "1px solid #444",
                "padding": "1px 4px",
                "fontSize": "11px",
                "height": "14px",
                "lineHeight": "12px",
            },
            style_cell={
                "backgroundColor": "#2d2d2d",
                "color": "white",
                "border": "1px solid #444",
                "textAlign": "center",
                "fontSize": "11px",
                "padding": "1px 2px",
                "minWidth": "40px",
                "maxWidth": "100px",
                "height": "12px",
                "lineHeight": "10px",
            },
            css=[
                # Hide TeamName column
                {"selector": ".dash-cell.column-6", "rule": "display: none;"},
                {"selector": ".dash-header.column-6", "rule": "display: none;"},
            ],
            style_data_conditional=style_conditional,  # type: ignore
        )

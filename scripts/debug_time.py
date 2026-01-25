"""Debug script to check Time column in laps data."""
import fastf1
import pandas as pd

# Enable cache
fastf1.Cache.enable_cache('cache')

# Load session
session = fastf1.get_session(2025, 'Abu Dhabi', 'R')
session.load()

print(f"Session start: {session.session_info.get('StartDate')}")
print(f"\nFirst 5 laps Time values:")
print(session.laps[['DriverNumber', 'LapNumber', 'Time', 'LapStartTime']].head(10))
print(f"\nTime column dtype: {session.laps['Time'].dtype}")
print(f"\nSample Time values:")
print(session.laps['Time'].head(20))

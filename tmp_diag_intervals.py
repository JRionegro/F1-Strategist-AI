import pandas as pd
from src.dashboards_dash.race_overview_dashboard import RaceOverviewDashboard
pos=pd.read_parquet('data/races/2025/2025-11-30_lusail/positions.parquet')
ints=pd.read_parquet('data/races/2025/2025-11-30_lusail/intervals.parquet')
session_start=pd.Timestamp('2025-11-30 16:00:00+00:00')
d=RaceOverviewDashboard(None)
off=d._infer_interval_filter_offset_seconds(ints, session_start)
print('inferred_off', off)
for t in [0,30,60,90,120,150,180,210,240,300]:
    pos_f=pos[pd.to_datetime(pos['Timestamp'], errors='coerce') <= (session_start + pd.Timedelta(seconds=t))]
    int_f=ints[pd.to_datetime(ints['Timestamp'], errors='coerce') <= (session_start + pd.Timedelta(seconds=t+off))]
    if pos_f.empty:
        print(f't={t:>3}s rows=0 nz_gap=0 nz_int=0')
        continue
    latest_pos=pos_f.sort_values('Timestamp').groupby('DriverNumber', as_index=False).last()
    latest_int=int_f.sort_values('Timestamp').groupby('DriverNumber', as_index=False).last() if not int_f.empty else pd.DataFrame(columns=['DriverNumber','GapToLeader','Interval'])
    merged=latest_pos.merge(latest_int[['DriverNumber','GapToLeader','Interval']], on='DriverNumber', how='left')
    nz_gap=pd.to_numeric(merged.get('GapToLeader'), errors='coerce').fillna(0).ne(0).sum()
    nz_int=pd.to_numeric(merged.get('Interval'), errors='coerce').fillna(0).ne(0).sum()
    print(f't={t:>3}s rows={len(merged)} nz_gap={nz_gap} nz_int={nz_int}')

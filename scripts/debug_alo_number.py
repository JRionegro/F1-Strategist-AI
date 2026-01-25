"""Check Alonso's driver number in the current race."""
import sys
sys.path.insert(0, 'src')

from data.openf1_data_provider import OpenF1DataProvider

# Session key for Abu Dhabi 2025
session_key = 9839

provider = OpenF1DataProvider()

# Get all drivers
drivers_response = provider.get_drivers(session_key)

# Convert to DataFrame if it's not already
import pandas as pd
if isinstance(drivers_response, pd.DataFrame):
    drivers = drivers_response.to_dict('records')
else:
    drivers = drivers_response

print("\n" + "="*80)
print("ALL DRIVERS IN SESSION 9839 (Abu Dhabi 2025)")
print("="*80)
print(f"Type of drivers: {type(drivers)}")
print(f"Number of drivers: {len(drivers)}")
print()

# Check all fields available
if drivers:
    print("Available fields:", drivers[0].keys())
    print()

for driver in drivers:
    if isinstance(driver, dict):
        # Try different fields that might contain the number
        driver_num = (driver.get('driver_number') or 
                     driver.get('DriverNumber') or
                     driver.get('number') or
                     'N/A')
        name = f"{driver.get('first_name', '')} {driver.get('last_name', '')}"
        abbr = driver.get('name_acronym', '?')
        
        # Show all driver info
        if 'ALONSO' in name.upper() or abbr == 'ALO':
            print(f">>> ALO FOUND - Full data: {driver}")
            print()
    else:
        print(f"Unexpected driver type: {type(driver)} - {driver}")
        continue
    
    # Highlight Alonso
    if 'ALONSO' in name.upper() or abbr == 'ALO':
        print(f">>> #{driver_num} - {abbr} - {name} <<<")
    else:
        print(f"#{driver_num} - {abbr} - {name}")

print("="*80 + "\n")

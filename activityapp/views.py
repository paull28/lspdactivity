from django.shortcuts import render, redirect
import json

def getData():
    import pandas as pd
    from datetime import datetime
    from collections import defaultdict

    # Read the CSV files
    callsign_data = pd.read_csv("https://docs.google.com/spreadsheets/d/1gQurpy4YSW2raqbEsg2heAt0aiU1cUDe7_nB647kd_g/export?format=csv")
    clock_data = pd.read_csv("https://docs.google.com/spreadsheets/d/1YKIQ3uPqaHRfu0GKrRfHiZF_WCz2ks1KG4x3AH_oMQk/export?format=csv")

    callsign_data.to_csv("static/data/callsigns.csv", index=False)  # Set index=False to avoid saving row numbers
    clock_data.to_csv("static/data/clocks.csv", index=False)


    # Create a lookup for valid hexes with their callsigns
    hex_to_callsign = {row['Steam Hex']: row['Callsign'] for _, row in callsign_data.iterrows()}
    valid_hexes = set(hex_to_callsign.keys())

    # Preprocess: Remove rows without valid callsigns
    clock_data = clock_data[clock_data["Hex"].isin(valid_hexes)]

    # Helper class to store intervals
    class Interval:
        def __init__(self, hex_value, start, end):
            self.hex_value = hex_value
            self.start = start
            self.end = end

    # Function to convert date and time to datetime object
    def convert_to_datetime(date_str, time_str):
        if pd.isna(time_str) or time_str.lower() == 'nan':
            return None
        try:
            return datetime.strptime(f"{date_str} {time_str}", "%d/%m/%Y %H:%M:%S")
        except ValueError:
            return None

    # Prepare interval list for sorting
    intervals = []
    for _, row in clock_data.iterrows():
        start_time = convert_to_datetime(row["Date"], row["In"])
        end_time = convert_to_datetime(row["Date"], row["Out"])
        
        # Set end_time to 30 mins after start_time if it is NaN
        if start_time and (end_time is None):
            end_time = start_time + pd.Timedelta(minutes=30)
        
        if start_time and end_time:
            intervals.append(Interval(row["Hex"], start_time, end_time))

    # Sort intervals by start time for efficient processing
    intervals.sort(key=lambda x: x.start)

    # Function to detect overlaps using sweep line technique
    def find_overlaps(intervals):
        active_intervals = []
        overlap_dict = defaultdict(lambda: defaultdict(int))

        for interval in intervals:
            # Remove expired intervals
            active_intervals = [i for i in active_intervals if i.end > interval.start]

            # Check for overlaps with active intervals
            for active in active_intervals:
                overlap_start = max(interval.start, active.start)
                overlap_end = min(interval.end, active.end)
                
                if overlap_start < overlap_end:  # Only count positive overlaps
                    overlap_time = (overlap_end - overlap_start).total_seconds()
                    overlap_dict[interval.hex_value][active.hex_value] += overlap_time
                    overlap_dict[active.hex_value][interval.hex_value] += overlap_time  # Bidirectional overlap
            
            # Add current interval to active list
            active_intervals.append(interval)

        return overlap_dict

    # Find overlaps efficiently
    overlap_results = find_overlaps(intervals)

    # Convert seconds to HH:MM:SS format
    def seconds_to_hms(seconds):
        hours, remainder = divmod(seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{int(hours):02}:{int(minutes):02}:{int(seconds):02}"

    ''' # Initialize empty results matrix
    callsign_list = list(hex_to_callsign.values())
    matrix = {call: {other_call: "" for other_call in callsign_list} for call in callsign_list}

    # Populate matrix with overlap times
    for hex1, overlaps in overlap_results.items():
        callsign1 = hex_to_callsign[hex1]
        for hex2, overlap_time in overlaps.items():
            callsign2 = hex_to_callsign[hex2]
            matrix[callsign1][callsign2] = seconds_to_hms(overlap_time)

    # Convert to DataFrame and save
    df_matrix = pd.DataFrame(matrix)
    output_file = "overlap_matrix2.csv"
    df_matrix.to_csv(output_file)

    print(f"Overlap matrix saved to {output_file}")'''

    import json

    # Prepare the overlap data for JSON export with complete sorting
    overlap_json = {}

    for hex1, overlaps in overlap_results.items():
        callsign1 = hex_to_callsign[hex1]
        # Sort the sub-dictionary by callsign keys
        sorted_sub_dict = dict(sorted({
            hex_to_callsign[hex2]: seconds_to_hms(overlap_time) 
            for hex2, overlap_time in overlaps.items()
        }.items()))
        
        overlap_json[callsign1] = sorted_sub_dict

    # Sort the main dictionary by callsign keys
    sorted_overlap_json = dict(sorted(overlap_json.items()))

    # Save the sorted JSON data to a text file with indentation
    output_json_file = "static/data/overlap_data.json"
    with open(output_json_file, "w") as json_file:
        json.dump(sorted_overlap_json, json_file, indent=4)

    print(f"Fully sorted overlap data saved to {output_json_file}")

    return sorted_overlap_json

def getCallsigns():
    import json

    callsigns = {}

    with open('static/data/callsigns.csv', 'r') as file:
        for line in file:
            print(line)
            parts = line.strip().split(',')
            print(parts)
            if parts[0] == "True":  # Only process active entries
                callsign = parts[1]
                full_name = f"{parts[2]} {parts[3]}"
                callsigns[callsign] = f"{callsign} | {full_name}"

    # Write to JSON file
    with open('static/data/callsigns.json', 'w') as json_file:
        json.dump(callsigns, json_file, indent=4)

# Create your views here.
def home(request):
    data = None
    callsigns = None
    try:
        with open('static/data/overlap_data.json') as f:
            data = json.load(f)
        with open('static/data/callsigns.json') as f:
            callsigns = json.load(f)
    except:
        pass
    context = {"data": data, "callsigns" : callsigns}
    return render(request, 'activityapp/home.html', context)

def refresh(request):
    getData()
    getCallsigns()
    response = redirect('/')
    return response
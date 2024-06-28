import json

def extract_times(json_string):
    # Parse the JSON string
    data = json.loads(json_string)
    
    # Extract start and end times as floats
    start_time = float(data[0]["start"])
    end_time = float(data[0]["end"])
    
    # Convert to integers
    start_time_int = int(start_time)
    end_time_int = int(end_time)
    
    return start_time_int, end_time_int

# Example JSON string (cleaned up)
json_string = '''
[{
    "start": "473.62",
    "content": "This is where he got stuck last time. Oh my god, dude, it's coming down to the wire. I still got time. Oh, this is a high probability of an explosion coming up. No! I forgot it. There's ten seconds left! Oh! Wait! You can just jump! Let's just jump! One time! Jump! You did it! YEAH!",
    "end": "512.86"
}]
'''

# Call the function to extract times
start_time, end_time = extract_times(json_string)
print(f"Start Time: {start_time}")
print(f"End Time: {end_time}")

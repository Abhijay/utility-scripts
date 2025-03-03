import subprocess
import re

# Expected screen type mapping (assumes contextual IDs)
SCREEN_MAP = {
    "MacBook built in screen": "1",
    "27 inch external screen": "2",
    "32 inch external screen": "3"
}

EXPECTED_SETTINGS = {
    "1": {"res": "1512x982", "hz": "120", "origin": "(-1512,458)", "degree": "0"},
    "2": {"res": "2560x1440", "hz": "60", "origin": "(0,0)", "degree": "0"},
    "3": {"res": "1800x3200", "hz": "60", "origin": "(2560,-675)", "degree": "90"}
}

def get_displayplacer_list():
    """Runs `displayplacer list` and returns the output."""
    try:
        result = subprocess.run(["displayplacer", "list"], capture_output=True, text=True, check=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Error running displayplacer: {e}")
        return None

def parse_displayplacer_output(output):
    """Parses `displayplacer list` output to extract Persistent screen IDs mapped to screen types."""
    screens = {}
    current_screen = {}

    for line in output.split("\n"):
        line = line.strip()

        # Detect a new display block
        if line.startswith("Persistent screen id:"):
            if "id" in current_screen and "type" in current_screen:  # Save previous display before starting a new one
                screens[current_screen["type"]] = current_screen["id"]

            current_screen = {"id": line.split(": ")[1]}  # Start a new screen entry

        elif line.startswith("Type:"):
            current_screen["type"] = line.split(": ")[1]

    # Save the last parsed display
    if "id" in current_screen and "type" in current_screen:
        screens[current_screen["type"]] = current_screen["id"]

    print("\n=== Matched Screen ID Mapping ===")
    for screen_type, screen_id in screens.items():
        print(f"  {screen_type}: {screen_id}")
    print("================================\n")

    return screens

def build_displayplacer_command(screen_ids):
    """Constructs the `displayplacer set` command dynamically using persistent screen IDs."""
    command = ["displayplacer"]
    
    for screen_type, context_id in SCREEN_MAP.items():
        if screen_type in screen_ids:
            persistent_id = screen_ids[screen_type]
            settings = EXPECTED_SETTINGS[context_id]
            command.append(
                f'id:{persistent_id} res:{settings["res"]} hz:{settings["hz"]} color_depth:8 '
                f'enabled:true scaling:on origin:{settings["origin"]} degree:{settings["degree"]}'
            )
        else:
            print(f"⚠️ Warning: Expected screen type '{screen_type}' not found!")  # Debug log

    return command

def apply_display_configuration():
    """Main function to parse screen IDs and apply the correct display settings."""
    output = get_displayplacer_list()
    if not output:
        return

    screen_ids = parse_displayplacer_output(output)

    # Ensure we have all expected screen types
    missing_screens = [st for st in SCREEN_MAP.keys() if st not in screen_ids]
    if missing_screens:
        print("\n❌ Error: Could not find all expected screens. Missing:", ", ".join(missing_screens))
        return

    # Build and execute the `displayplacer` command
    command = build_displayplacer_command(screen_ids)
    print("\n✅ Running command:", " ".join(command), "\n")
    subprocess.run(command)

if __name__ == "__main__":
    apply_display_configuration()

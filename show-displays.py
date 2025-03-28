import sys
import re
from math import gcd, ceil


def compute_monitor_gcd(mon):
    """Compute the gcd for a monitor's effective resolution.
    If rotated 90 or 270, swap width and height."""
    res = mon.get('res', '')
    try:
        w_str, h_str = res.split('x')
        w = int(w_str)
        h = int(h_str)
    except Exception:
        return 1
    rot = mon.get('rot', '0')
    if rot in ('90', '270'):
        w, h = h, w  # swap for rotated monitor
    return gcd(w, h)


def effective_resolution(mon):
    """Return effective (width, height) after taking rotation into account."""
    res = mon.get('res', '')
    try:
        w_str, h_str = res.split('x')
        w = int(w_str)
        h = int(h_str)
    except Exception:
        return (0, 0)
    rot = mon.get('rot', '0')
    if rot in ('90', '270'):
        return (h, w)
    else:
        return (w, h)


def parse_displayplacer_list(input_text):
    """
    Parses the displayplacer list output.
    Extracts:
      - Contextual screen id (used as monitor id)
      - Resolution (e.g. "2560x1440")
      - Origin (as tuple of ints)
      - Rotation (as a string)
    Returns a list of monitor dictionaries.
    """
    blocks = re.split(r'\n\s*\n', input_text.strip())
    monitors = []
    for block in blocks:
        lines = block.strip().splitlines()
        mon = {}
        for line in lines:
            if line.startswith('Contextual screen id:'):
                mon['id'] = line.split(':', 1)[1].strip()
            elif line.startswith('Resolution:'):
                mon['res'] = line.split(':', 1)[1].strip()
            elif line.startswith('Origin:'):
                m = re.search(r'\(([-\d]+),\s*([-\d]+)\)', line)
                if m:
                    mon['origin'] = (int(m.group(1)), int(m.group(2)))
            elif line.startswith('Rotation:'):
                mon['rot'] = line.split(':', 1)[1].strip().split()[0]
        if 'id' in mon and 'origin' in mon and 'res' in mon and 'rot' in mon:
            monitors.append(mon)
    return monitors


def choose_scale(monitors):
    """
    Compute a scale factor to reduce the pixel grid.
    Here we compute each monitor's gcd (of its effective resolution) and choose the maximum,
    so that at least one monitor divides exactly.
    (You can adjust this logic if you want a different granularity.)
    """
    gcds = [compute_monitor_gcd(mon) for mon in monitors]
    scale = max(gcds) if gcds else 1
    return scale


def compute_scaled_properties(mon, scale):
    """
    For a given monitor, compute:
      - effective width and height (swapping if rotated)
      - scaled width and height (using ceil to not lose any part)
      - scaled origin (rounded)
    Returns a dict with keys: 'scaled_origin', 'scaled_width', 'scaled_height'
    """
    w, h = effective_resolution(mon)
    scaled_width = ceil(w / scale)
    scaled_height = ceil(h / scale)
    ox, oy = mon['origin']
    # Divide the origin by scale and round to nearest integer.
    scaled_origin = (round(ox / scale), round(oy / scale))
    return {
        'scaled_origin': scaled_origin,
        'scaled_width': scaled_width,
        'scaled_height': scaled_height,
    }


def build_grid(monitors, scale):
    """
    Computes the scaled properties for each monitor, then determines the
    overall bounding box.
    Returns:
      - grid: a 2D list (list of lists) of characters (initially spaces)
      - offset: (offset_x, offset_y) to map monitor coordinates into grid
      indices
      - monitor_props: list of monitor dicts with added scaled properties.
    """
    monitor_props = []
    # Compute scaled properties for each monitor.
    for mon in monitors:
        props = compute_scaled_properties(mon, scale)
        mon.update(props)
        monitor_props.append(mon)

    # Determine bounding box:
    min_x = min(mon['scaled_origin'][0] for mon in monitor_props)
    min_y = min(mon['scaled_origin'][1] for mon in monitor_props)
    max_x = max(mon['scaled_origin'][0] + mon['scaled_width'] for mon in monitor_props)
    max_y = max(mon['scaled_origin'][1] + mon['scaled_height'] for mon in monitor_props)

    width = max_x - min_x
    height = max_y - min_y

    # Add extra vertical space for desk and person (at least 10 rows)
    extra_height = 10
    height += extra_height

    # Create grid (list of list of characters), initialize with spaces.
    grid = [[' ' for _ in range(width + 1)] for _ in range(height + 1)]
    offset = (-min_x, -min_y)
    return grid, offset, monitor_props


def draw_rectangle(grid, offset, mon, label=''):
    """
    Draws a rectangle representing a monitor on the grid.
    The monitor's top-left is (x, y) = mon['scaled_origin'] plus the offset.
    Its size is (mon['scaled_width'], mon['scaled_height']).
    Draw borders with '+' at corners, '-' for horizontal edges, and '|' for vertical edges.
    Optionally, put the monitor's id (or label) in the center.
    """
    ox, oy = mon['scaled_origin']
    w = mon['scaled_width']
    h = mon['scaled_height']
    off_x, off_y = offset
    # Convert to grid coordinates:
    x0 = ox + off_x
    y0 = oy + off_y
    x1 = x0 + w - 1
    y1 = y0 + h - 1

    # Draw corners:
    if 0 <= y0 < len(grid) and 0 <= x0 < len(grid[0]):
        grid[y0][x0] = '+'
    if 0 <= y0 < len(grid) and 0 <= x1 < len(grid[0]):
        grid[y0][x1] = '+'
    if 0 <= y1 < len(grid) and 0 <= x0 < len(grid[0]):
        grid[y1][x0] = '+'
    if 0 <= y1 < len(grid) and 0 <= x1 < len(grid[0]):
        grid[y1][x1] = '+'

    # Draw top and bottom horizontal edges.
    for x in range(x0 + 1, x1):
        if 0 <= y0 < len(grid) and 0 <= x < len(grid[0]):
            grid[y0][x] = '-'
        if 0 <= y1 < len(grid) and 0 <= x < len(grid[0]):
            grid[y1][x] = '-'
    # Draw left and right vertical edges.
    for y in range(y0 + 1, y1):
        if 0 <= y < len(grid) and 0 <= x0 < len(grid[0]):
            grid[y][x0] = '|'
        if 0 <= y < len(grid) and 0 <= x1 < len(grid[0]):
            grid[y][x1] = '|'

    # Optionally, place the monitor's id (centered) inside the rectangle.
    mid_x = (x0 + x1) // 2
    mid_y = (y0 + y1) // 2
    id_str = mon.get('id', '')
    for i, ch in enumerate(id_str):
        if mid_y < len(grid) and mid_x + i < len(grid[0]):
            grid[mid_y][mid_x + i] = ch


def print_grid(grid):
    for row in grid:
        print(''.join(row))


def draw_desk(grid):
    """
    Draws a 2D desk under the monitors in the grid.
    """
    # Find the dimensions of the grid
    height = len(grid)
    width = len(grid[0]) if height > 0 else 0

    if height < 5 or width < 5:
        return  # Grid too small for desk

    # Find the bottom of the lowest monitor
    lowest_row = 0
    for row in range(height):
        if any(cell in '+|-' for cell in grid[row]):
            lowest_row = max(lowest_row, row)

    # Add some space between monitors and desk
    desk_row = min(lowest_row + 3, height - 8)

    # Draw the desk with 2D appearance

    # Desk top
    for x in range(width):
        if desk_row < height:
            grid[desk_row][x] = '='

    # Desk front edge
    if desk_row + 1 < height:
        for x in range(width):
            grid[desk_row + 1][x] = '#'

    # Desk legs - more substantial
    leg_positions = [width // 5, 4 * width // 5]
    for leg_x in leg_positions:
        for y in range(desk_row + 2, min(desk_row + 5, height)):
            if 0 <= leg_x < width:
                grid[y][leg_x] = '║'
            if 0 <= leg_x + 1 < width:
                grid[y][leg_x + 1] = '║'

    # Desk corner shadows
    if 0 < desk_row + 1 < height and width > 1:
        grid[desk_row + 1][0] = '['
        grid[desk_row + 1][width - 1] = ']'


def draw_keyboard(grid):
    """
    Draws a 2D keyboard on the desk.
    """
    height = len(grid)
    width = len(grid[0]) if height > 0 else 0

    if height < 8 or width < 10:
        return  # Grid too small for keyboard

    # Find the desk row
    desk_row = None
    for row in range(height - 3, 0, -1):
        if any(cell == '=' for cell in grid[row]):
            desk_row = row
            break

    if desk_row is None:
        return

    # Draw keyboard on the desk
    keyboard_width = min(14, width // 3)
    keyboard_start = (width - keyboard_width) // 2

    # Draw keyboard outline with 2D appearance
    keyboard_row = desk_row - 1
    if keyboard_row >= 0:
        # Top edge of keyboard
        for x in range(keyboard_start, keyboard_start + keyboard_width):
            if x < width:
                grid[keyboard_row][x] = '_'

        # Side edges and bottom of keyboard
        if keyboard_row + 1 < height:
            if keyboard_start < width:
                grid[keyboard_row + 1][keyboard_start] = '['
            keyboard_end = keyboard_start + keyboard_width - 1
            if keyboard_end < width:
                grid[keyboard_row + 1][keyboard_end] = ']'

            # Keys
            for x in range(keyboard_start + 1, keyboard_end):
                if x < width:
                    # Alternate key appearances for 2D effect
                    if (x - keyboard_start) % 2 == 0:
                        grid[keyboard_row + 1][x] = '█'
                    else:
                        grid[keyboard_row + 1][x] = '▒'


def draw_person(grid):
    """
    Draws a simple stick figure person facing the monitors.
    """
    height = len(grid)
    width = len(grid[0]) if height > 0 else 0

    if height < 10 or width < 5:
        return  # Grid too small for person

    # Find the desk row
    desk_row = None
    for row in range(height - 3, 0, -1):
        if any(cell == '=' for cell in grid[row]):
            desk_row = row
            break

    if desk_row is None:
        return

    # Calculate person position
    person_x = width // 2

    # Draw chair
    chair_top_row = desk_row + 2
    if chair_top_row < height - 2:
        chair_width = 5
        chair_start = max(0, person_x - chair_width // 2)
        chair_end = min(width, chair_start + chair_width)

        # Chair back
        for x in range(chair_start, chair_end):
            if chair_top_row < height:
                grid[chair_top_row][x] = '-'
        if chair_start < width:
            grid[chair_top_row + 1][chair_start] = '|'
        if chair_end - 1 < width:
            grid[chair_top_row + 1][chair_end - 1] = '|'

    # Draw head (at chair height)
    head_row = desk_row + 2
    if head_row < height:
        grid[head_row][person_x] = 'O'

    # Draw body
    if head_row + 1 < height:
        grid[head_row + 1][person_x] = '|'
    if head_row + 2 < height:
        grid[head_row + 2][person_x] = '|'

    # Draw arms (like typing on keyboard)
    arms_row = head_row + 1
    if arms_row < height:
        if person_x - 1 >= 0:
            grid[arms_row][person_x - 1] = '/'
        if person_x + 1 < width:
            grid[arms_row][person_x + 1] = '\\'

    # Draw legs
    legs_row = head_row + 3
    if legs_row < height:
        if person_x - 1 >= 0:
            grid[legs_row][person_x - 1] = '/'
        if person_x + 1 < width:
            grid[legs_row][person_x + 1] = '\\'


def main():
    # Read input from standard input.
    try:
        import subprocess

        input_text = subprocess.check_output(['displayplacer', 'list'], text=True)
    except (subprocess.SubprocessError, FileNotFoundError):
        print(
            'Error executing displayplacer. Make sure it is installed and in your PATH.'
        )
        print(
            'You can install it with: brew tap jakehilborn/jakehilborn && '
            'brew install displayplacer'
        )
        sys.exit(1)
    if not input_text.strip():
        print('No output from displayplacer list command.')
        sys.exit(1)

    monitors = parse_displayplacer_list(input_text)
    if not monitors:
        print('No monitors parsed from input.')
        sys.exit(1)

    scale = choose_scale(monitors)
    grid, offset, monitor_props = build_grid(monitors, scale)
    print('Drawing monitor rectangles onto grid...')
    for mon in monitor_props:
        draw_rectangle(grid, offset, mon, label=mon.get('id', ''))

    # Add desk, keyboard and person
    draw_desk(grid)
    draw_keyboard(grid)
    draw_person(grid)

    print('\nFinal ASCII Grid (each cell is a scaled unit):')
    print_grid(grid)


if __name__ == '__main__':
    main()

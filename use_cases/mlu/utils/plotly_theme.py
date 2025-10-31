"""
Custom Plotly theme matching frontend globals.css
Converts OKLCH colors to RGB for Plotly compatibility
"""
import colorsys
import math

def oklch_to_rgb(l, c, h):
    """
    Convert OKLCH to RGB
    L: lightness (0-1)
    C: chroma (0-0.4)
    H: hue (0-360 degrees)
    """
    # OKLCH is complex - using approximation via LAB
    # For production, you'd use a proper color library
    # This is a simplified conversion

    # Convert to LAB (approximate)
    L_lab = l * 100
    a = c * math.cos(math.radians(h)) * 100
    b = c * math.sin(math.radians(h)) * 100

    # LAB to XYZ
    fy = (L_lab + 16) / 116
    fx = a / 500 + fy
    fz = fy - b / 200

    def f_inv(t):
        delta = 6/29
        if t > delta:
            return t ** 3
        else:
            return 3 * delta ** 2 * (t - 4/29)

    # Reference white D65
    Xn, Yn, Zn = 0.95047, 1.00000, 1.08883

    X = Xn * f_inv(fx)
    Y = Yn * f_inv(fy)
    Z = Zn * f_inv(fz)

    # XYZ to RGB (sRGB)
    R =  3.2404542 * X - 1.5371385 * Y - 0.4985314 * Z
    G = -0.9692660 * X + 1.8760108 * Y + 0.0415560 * Z
    B =  0.0556434 * X - 0.2040259 * Y + 1.0572252 * Z

    # Gamma correction
    def gamma_correct(c):
        if c <= 0.0031308:
            return 12.92 * c
        else:
            return 1.055 * (c ** (1/2.4)) - 0.055

    R = max(0, min(1, gamma_correct(R)))
    G = max(0, min(1, gamma_correct(G)))
    B = max(0, min(1, gamma_correct(B)))

    return (int(R * 255), int(G * 255), int(B * 255))

def rgb_to_hex(r, g, b):
    """Convert RGB tuple to hex string"""
    return f'#{r:02x}{g:02x}{b:02x}'

def oklch_to_hex(l, c, h):
    """Convert OKLCH directly to hex"""
    r, g, b = oklch_to_rgb(l, c, h)
    return rgb_to_hex(r, g, b)

# Light theme colors (from globals.css :root)
LIGHT_THEME = {
    'background': oklch_to_hex(1, 0, 0),  # white
    'foreground': oklch_to_hex(0.141, 0.005, 285.823),  # dark text
    'primary': oklch_to_hex(0.623, 0.214, 259.815),  # blue
    'secondary': oklch_to_hex(0.967, 0.001, 286.375),  # light gray
    'muted': oklch_to_hex(0.552, 0.016, 285.938),  # muted text
    'border': oklch_to_hex(0.92, 0.004, 286.32),  # light border
    'chart_1': oklch_to_hex(0.646, 0.222, 41.116),
    'chart_2': oklch_to_hex(0.6, 0.118, 184.704),
    'chart_3': oklch_to_hex(0.398, 0.07, 227.392),
    'chart_4': oklch_to_hex(0.828, 0.189, 84.429),
    'chart_5': oklch_to_hex(0.769, 0.188, 70.08),
}

# Dark theme colors (from globals.css .dark)
DARK_THEME = {
    'background': oklch_to_hex(0.141, 0.005, 285.823),  # dark bg
    'foreground': oklch_to_hex(0.985, 0, 0),  # white text
    'primary': oklch_to_hex(0.546, 0.245, 262.881),  # blue
    'secondary': oklch_to_hex(0.274, 0.006, 286.033),  # dark gray
    'muted': oklch_to_hex(0.705, 0.015, 286.067),  # muted text
    'border': 'rgba(255, 255, 255, 0.1)',  # oklch(1 0 0 / 10%) - rgba format for Plotly
    'chart_1': oklch_to_hex(0.488, 0.243, 264.376),
    'chart_2': oklch_to_hex(0.696, 0.17, 162.48),
    'chart_3': oklch_to_hex(0.769, 0.188, 70.08),
    'chart_4': oklch_to_hex(0.627, 0.265, 303.9),
    'chart_5': oklch_to_hex(0.645, 0.246, 16.439),
}

def get_plotly_template(theme='light'):
    """
    Create a custom Plotly template matching globals.css theme

    Args:
        theme: 'light' or 'dark'

    Returns:
        dict: Plotly layout configuration
    """
    colors = DARK_THEME if theme == 'dark' else LIGHT_THEME

    template = {
        'layout': {
            'paper_bgcolor': colors['background'],
            'plot_bgcolor': colors['background'],
            'font': {
                'color': colors['foreground'],
                'family': 'system-ui, sans-serif'
            },
            'xaxis': {
                'gridcolor': colors['border'],
                'linecolor': colors['border'],
                'tickcolor': colors['foreground'],
                'title': {'font': {'color': colors['foreground']}},
                'tickfont': {'color': colors['muted']},
            },
            'yaxis': {
                'gridcolor': colors['border'],
                'linecolor': colors['border'],
                'tickcolor': colors['foreground'],
                'title': {'font': {'color': colors['foreground']}},
                'tickfont': {'color': colors['muted']},
            },
            'colorway': [
                colors['chart_1'],
                colors['chart_2'],
                colors['chart_3'],
                colors['chart_4'],
                colors['chart_5'],
                colors['primary'],
            ],
            'title': {
                'font': {'color': colors['foreground']}
            },
            'legend': {
                'font': {'color': colors['foreground']},
                'bgcolor': colors['background'],
                'bordercolor': colors['border']
            },
            'hoverlabel': {
                'bgcolor': colors['secondary'],
                'bordercolor': colors['border'],
                'font': {'color': colors['foreground']}
            }
        }
    }

    return template

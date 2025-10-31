"""
Helper script to inject responsive CSS into all existing HTML visualization files.
Run this after generating visualizations to make them full-width in the frontend.
"""

from pathlib import Path
import re

def inject_responsive_css(html_file: Path):
    """Inject responsive CSS into a Plotly HTML file to make it full-width."""
    if not html_file.exists():
        return False

    with open(html_file, 'r', encoding='utf-8') as f:
        html_content = f.read()

    # Check if already injected
    if 'plotly-responsive-styles' in html_content:
        return False

    responsive_css = """
    <style id="plotly-responsive-styles">
        body { margin: 0; padding: 0; overflow-x: hidden; }
        .plotly-graph-div { width: 100% !important; min-width: 100% !important; }
        .js-plotly-plot { width: 100% !important; }
    </style>
    """

    # Inject before </head>
    if '</head>' in html_content:
        html_content = html_content.replace('</head>', f'{responsive_css}</head>', 1)
    else:
        # No head tag, inject at start of body
        html_content = responsive_css + html_content

    with open(html_file, 'w', encoding='utf-8') as f:
        f.write(html_content)

    return True

if __name__ == '__main__':
    # Process all HTML files in MLU results
    results_dir = Path(__file__).parent.parent / 'results'

    if not results_dir.exists():
        print(f"❌ Results directory not found: {results_dir}")
        exit(1)

    html_files = list(results_dir.glob('*.html'))

    if not html_files:
        print(f"❌ No HTML files found in {results_dir}")
        exit(1)

    print(f"🔧 Making {len(html_files)} HTML files responsive...")

    updated_count = 0
    for html_file in html_files:
        if inject_responsive_css(html_file):
            print(f"   ✅ {html_file.name}")
            updated_count += 1
        else:
            print(f"   ⏭️  {html_file.name} (already responsive)")

    print(f"\n✅ Updated {updated_count}/{len(html_files)} files")

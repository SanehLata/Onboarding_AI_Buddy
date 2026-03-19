# save_graph.py — run once locally to generate the image
from graph import onboarding_graph
from pathlib import Path

# Requires: pip install grandalf  OR  pip install playwright + playwright install chromium
png_bytes = onboarding_graph.get_graph().draw_mermaid_png()

output_path = Path("docs/graph_diagram.png")
output_path.parent.mkdir(exist_ok=True)
output_path.write_bytes(png_bytes)
print(f"Graph saved to {output_path}")
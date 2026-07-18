"""Assemble results/frames/frame_*.jpg into results/demo.gif (run after capture)."""
import glob
from PIL import Image

frames = [Image.open(f).convert("P", palette=Image.ADAPTIVE, colors=128)
          for f in sorted(glob.glob("results/frames/frame_*.jpg"))]
frames[0].save("results/demo.gif", save_all=True, append_images=frames[1:],
               duration=120, loop=0, optimize=True)
print(f"wrote results/demo.gif ({len(frames)} frames)")

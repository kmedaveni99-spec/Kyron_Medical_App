from PIL import Image
from collections import Counter

img1 = Image.open("Screenshot 2026-03-17 at 7.39.59 PM.png")
print(f"Screenshot 1: {img1.size} ({img1.mode})")

img2 = Image.open("Screenshot 2026-03-17 at 7.40.31 PM.png")
print(f"Screenshot 2: {img2.size} ({img2.mode})")

logo = Image.open("kyron_medical_logo.jpeg")
print(f"Logo: {logo.size} ({logo.mode})")

pixels = list(img1.convert("RGB").getdata())
sampled = pixels[::200]
counts = Counter(sampled)
print("\nTop colors in Screenshot 1:")
for color, cnt in counts.most_common(15):
    r, g, b = color
    print(f"  #{r:02x}{g:02x}{b:02x} (RGB {r},{g},{b}): {cnt}")

logo_px = list(logo.convert("RGB").getdata())
logo_s = logo_px[::5]
lcounts = Counter(logo_s)
print("\nTop colors in Logo:")
for color, cnt in lcounts.most_common(10):
    r, g, b = color
    print(f"  #{r:02x}{g:02x}{b:02x} (RGB {r},{g},{b}): {cnt}")


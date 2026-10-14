"""Cut the player sheet into transparent per-direction frames.

Run via ./build.sh sprites (inside Docker). Usage: extract_sprites.py <sheet> <out_dir>
"""
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

COLUMNS = 4
# The generated sheet's rows are not evenly spaced; these are measured pixel bands.
ROW_BANDS = {0: (0, 345), 1: (345, 690), 2: (690, 1025)}
ROW_DIRECTIONS = {0: "north", 1: "south", 2: "west"}
OUTPUT_HEIGHT = 112


def remove_background(cell: Image.Image) -> Image.Image:
    """Segment the character from the blurry gradient background with GrabCut."""
    rgb = np.array(cell.convert("RGB"))
    height, width = rgb.shape[:2]

    mask = np.full((height, width), cv2.GC_PR_BGD, dtype=np.uint8)
    margin_x, margin_y = int(width * 0.12), int(height * 0.02)
    mask[margin_y : height - margin_y, margin_x : width - margin_x] = cv2.GC_PR_FGD
    # Definite background: the outer frame, and the shadow band below the feet.
    mask[:margin_y, :] = cv2.GC_BGD
    mask[height - int(height * 0.03) :, :] = cv2.GC_BGD
    mask[:, :margin_x] = cv2.GC_BGD
    mask[:, width - margin_x :] = cv2.GC_BGD
    # Definite foreground: the centre of the body.
    mask[int(height * 0.35) : int(height * 0.7), int(width * 0.38) : int(width * 0.62)] = cv2.GC_FGD

    background_model = np.zeros((1, 65), np.float64)
    foreground_model = np.zeros((1, 65), np.float64)
    cv2.grabCut(rgb[:, :, ::-1].copy(), mask, None, background_model, foreground_model, 8, cv2.GC_INIT_WITH_MASK)

    foreground = np.where((mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD), 255, 0).astype(np.uint8)
    # Keep only the largest connected blob and smooth its edge.
    count, labels, stats, _ = cv2.connectedComponentsWithStats(foreground)
    if count > 1:
        largest = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
        foreground = np.where(labels == largest, 255, 0).astype(np.uint8)
    foreground = cv2.morphologyEx(foreground, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))

    # Smooth regions without edges (the blurred floor shadow) are not part of the character.
    edges = cv2.Canny(cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY), 40, 110)
    edges = cv2.dilate(edges, np.ones((5, 5), np.uint8))
    edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, np.ones((31, 31), np.uint8))
    filled = edges.copy()
    flood_mask = np.zeros((height + 2, width + 2), np.uint8)
    cv2.floodFill(filled, flood_mask, (0, 0), 255)
    textured = edges | cv2.bitwise_not(filled)
    foreground = cv2.bitwise_and(foreground, textured)
    foreground = cv2.morphologyEx(foreground, cv2.MORPH_OPEN, np.ones((7, 7), np.uint8))
    count, labels, stats, _ = cv2.connectedComponentsWithStats(foreground)
    if count > 1:
        largest = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
        foreground = np.where(labels == largest, 255, 0).astype(np.uint8)
    foreground = cv2.GaussianBlur(foreground, (5, 5), 0)

    rgba = np.dstack([rgb, foreground])
    return Image.fromarray(rgba, "RGBA")


def main(sheet_path: str, out_dir: str) -> None:
    sheet = Image.open(sheet_path).convert("RGB")
    cell_width = sheet.width // COLUMNS
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    for row, direction in ROW_DIRECTIONS.items():
        band_top, band_bottom = ROW_BANDS[row]
        for column in range(COLUMNS):
            box = (column * cell_width, band_top, (column + 1) * cell_width, band_bottom)
            frame = remove_background(sheet.crop(box))
            bounds = frame.getbbox()
            frame = frame.crop(bounds)
            scale = OUTPUT_HEIGHT / frame.height
            frame = frame.resize((max(1, round(frame.width * scale)), OUTPUT_HEIGHT), Image.LANCZOS)
            frame.save(out_path / f"player_{direction}_{column}.png")
    print("wrote", len(list(out_path.glob("player_*.png"))), "frames")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])

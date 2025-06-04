#!/usr/bin/env python3
import cv2
import numpy as np
from PIL import Image

# Load the two QR codes
actual = cv2.imread('actual_current_qr.png', cv2.IMREAD_GRAYSCALE)
predicted = cv2.imread('predicted_current_qr.png', cv2.IMREAD_GRAYSCALE)

# Make sure they're the same size
if actual.shape != predicted.shape:
    predicted = cv2.resize(predicted, (actual.shape[1], actual.shape[0]))

# Compare pixel by pixel
diff = cv2.absdiff(actual, predicted)
num_diff_pixels = np.count_nonzero(diff)
total_pixels = actual.shape[0] * actual.shape[1]

print(f"Image size: {actual.shape}")
print(f"Different pixels: {num_diff_pixels}")
print(f"Total pixels: {total_pixels}")
print(f"Similarity: {(1 - num_diff_pixels/total_pixels) * 100:.2f}%")

# Check if they're identical
if num_diff_pixels == 0:
    print("\n✓ QR CODES ARE IDENTICAL!")
    print("The prediction was 100% correct!")
else:
    print(f"\n✗ QR codes differ by {num_diff_pixels} pixels")
    
    # Save difference image
    cv2.imwrite('qr_diff.png', diff)
    print("Difference image saved to qr_diff.png")
#!/usr/bin/env python3
import sys
import cv2
from pyzbar.pyzbar import decode

if len(sys.argv) != 2:
    print("Usage: python decode_single_qr.py <image_path>")
    sys.exit(1)

img_path = sys.argv[1]
img = cv2.imread(img_path)

if img is None:
    print(f"Error: Could not read image from {img_path}")
    sys.exit(1)

decoded_objects = decode(img)

if decoded_objects:
    for obj in decoded_objects:
        print(f"Type: {obj.type}")
        print(f"Data: {obj.data.decode('utf-8')}")
else:
    print("No QR code found in the image")
#!/usr/bin/env python3
"""QR code utilities for AI World Fair prototype."""

import base64
import json
import zlib

import qrcode
from qrcode.image.svg import SvgPathImage


def generate_badge_qr(name: str, github: str, topic: str) -> str:
    """Generate QR code from badge data as base64-encoded SVG."""
    data = {"name": name, "github": github, "topic": topic}
    json_str = json.dumps(data, separators=(',', ':'))
    compressed = zlib.compress(json_str.encode('utf-8'), level=9)
    encoded = base64.b64encode(compressed).decode('ascii')

    svg_image = qrcode.make(encoded, image_factory=SvgPathImage)
    svg_str = svg_image.to_string(encoding='unicode')
    return svg_str


def decode_contact_qr(raw_json: str) -> dict:
    """Validate and parse contact JSON structure."""
    try:
        data = json.loads(raw_json)
        return {
            "valid": True,
            "name": data.get("name", ""),
            "github": data.get("github", ""),
            "topic": data.get("topic", ""),
        }
    except (json.JSONDecodeError, TypeError):
        return {
            "valid": False,
            "error": "Invalid JSON format",
        }


if __name__ == "__main__":
    import sys
    if len(sys.argv) >= 4:
        qr = generate_badge_qr(sys.argv[1], sys.argv[2], sys.argv[3])
        print(qr)
    else:
        qr = generate_badge_qr("Test User", "testuser", "RAG Systems")
        print("QR SVG:", qr)

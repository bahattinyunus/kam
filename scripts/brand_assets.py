import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import numpy as np


def render_kam_mark(size: int, glow: bool = False) -> Image.Image:
    """
    Renders the iconic 3-piece monolithic KAM logo with 4x supersampling.
    """
    ss = 4
    S = size * ss
    canvas = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)

    def scale_pts(pts):
        return [(int(x * S / 1024.0), int(y * S / 1024.0)) for x, y in pts]

    # Top Sovereign Singularity Diamond (Electric Ice-Cyan #00E5FF)
    diamond = scale_pts([(512, 130), (572, 252), (512, 374), (452, 252)])
    # Left Monolithic Wing (Stark White #FFFFFF)
    left_wing = scale_pts([
        (436, 286), (496, 400), (416, 548), (496, 700),
        (496, 896), (344, 608), (242, 666)
    ])
    # Right Monolithic Wing (Stark White #FFFFFF)
    right_wing = scale_pts([
        (588, 286), (528, 400), (608, 548), (528, 700),
        (528, 896), (680, 608), (782, 666)
    ])

    if glow:
        glow_layer = Image.new("RGBA", (S, S), (0, 0, 0, 0))
        gdraw = ImageDraw.Draw(glow_layer)
        gdraw.polygon(diamond, fill=(0, 229, 255, 180))
        gdraw.polygon(left_wing, fill=(0, 229, 255, 110))
        gdraw.polygon(right_wing, fill=(0, 229, 255, 110))
        glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(radius=S * 0.04))
        canvas = Image.alpha_composite(canvas, glow_layer)
        draw = ImageDraw.Draw(canvas)

    draw.polygon(diamond, fill=(0, 229, 255, 255))
    draw.polygon(left_wing, fill=(255, 255, 255, 255))
    draw.polygon(right_wing, fill=(255, 255, 255, 255))

    return canvas.resize((size, size), Image.Resampling.LANCZOS)


def create_hud_badge(width: int = 236, height: int = 58) -> Image.Image:
    """
    Creates an aerospace defense HUD badge with the monolithic KAM mark and typography.
    """
    ss = 4
    W, H = width * ss, height * ss
    badge = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(badge)

    # Obsidian glass pill background
    draw.rounded_rectangle(
        [2, 2, W - 3, H - 3],
        radius=12 * ss,
        fill=(5, 9, 16, 208),
        outline=(0, 229, 255, 115),
        width=ss,
    )

    # Left vertical cyan accent bar
    draw.rounded_rectangle(
        [10 * ss, 12 * ss, 13 * ss, H - 12 * ss],
        radius=ss,
        fill=(0, 229, 255, 235),
    )

    # Downsample base plate first
    badge_small = badge.resize((width, height), Image.Resampling.LANCZOS)

    # Paste high-precision KAM mark
    mark_size = height - 12
    mark = render_kam_mark(mark_size, glow=True)
    badge_small.alpha_composite(mark, (18, 6))

    # Draw crisp typography
    d_small = ImageDraw.Draw(badge_small)
    try:
        font_title = ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf", 19)
        font_sub = ImageFont.truetype("C:/Windows/Fonts/consolab.ttf", 9)
    except Exception:
        font_title = ImageFont.load_default()
        font_sub = ImageFont.load_default()

    d_small.text((70, 10), "K A M", fill=(255, 255, 255, 250), font=font_title)
    d_small.text((70, 34), "AUTONOMOUS EDGE CORE", fill=(0, 229, 255, 215), font=font_sub)

    return badge_small


def upgrade_cockpit_mfd(img: Image.Image) -> Image.Image:
    """
    Replaces the circular center MFD inside kam_cyber_cockpit_hud.jpg
    with the sovereign monolithic KAM logo and avionics telemetry rings.
    """
    out = img.convert("RGBA")
    cx, cy, r = 688, 520, 86

    ss = 4
    D = (r * 2) * ss
    mfd = Image.new("RGBA", (D, D), (0, 0, 0, 0))
    mdraw = ImageDraw.Draw(mfd)

    # Dark avionics CRT/OLED background inside circular bezel
    mdraw.ellipse([0, 0, D - 1, D - 1], fill=(4, 11, 20, 252))

    # Concentric radar rings
    for frac, alpha in [(0.92, 160), (0.72, 95), (0.48, 65)]:
        rad = int((D // 2) * frac)
        c = D // 2
        mdraw.ellipse(
            [c - rad, c - rad, c + rad, c + rad],
            outline=(0, 229, 255, alpha),
            width=ss,
        )

    # Subtle polar crosshair lines
    c = D // 2
    mdraw.line([(c, int(D * 0.06)), (c, int(D * 0.94))], fill=(0, 229, 255, 55), width=ss)
    mdraw.line([(int(D * 0.06), c), (int(D * 0.94), c)], fill=(0, 229, 255, 55), width=ss)

    mfd_small = mfd.resize((r * 2, r * 2), Image.Resampling.LANCZOS)

    # Composite glowing KAM mark right in the center of the cockpit MFD
    mark_sz = int(r * 1.48)
    mark = render_kam_mark(mark_sz, glow=True)
    offset = (r * 2 - mark_sz) // 2
    mfd_small.alpha_composite(mark, (offset, offset))

    out.alpha_composite(mfd_small, (cx - r, cy - r))
    return out


def upgrade_hero_fuselage(img: Image.Image) -> Image.Image:
    """
    Cleans old glowing markings on the stealth jet hull in kam_hero_banner.jpg
    and brands the aircraft fuselage with an angled monolithic KAM emblem.
    """
    arr = np.array(img.convert("RGB")).copy()

    # Smoothly replace bright cyan rune pixels in the two hull regions with local dark hull tone
    for y1, y2, x1, x2 in [(420, 456, 598, 632), (412, 447, 745, 812)]:
        patch = arr[y1:y2, x1:x2]
        mask = (patch[:, :, 2] > 65) | (patch[:, :, 1] > 65)
        dark_pixels = patch[~mask]
        fill_color = np.array([26, 34, 43], dtype=np.uint8) if len(dark_pixels) == 0 else np.median(dark_pixels, axis=0).astype(np.uint8)
        patch[mask] = fill_color
        arr[y1:y2, x1:x2] = patch

    out = Image.fromarray(arr).convert("RGBA")
    for box in [(596, 418, 634, 458), (743, 410, 814, 449)]:
        region = out.crop(box).filter(ImageFilter.GaussianBlur(radius=2.5))
        out.paste(region, box[:2])

    # Stamp tactical low-observable KAM insignia on the stealth hull
    hull_mark = render_kam_mark(42, glow=True).rotate(-14, resample=Image.Resampling.BICUBIC, expand=True)
    r, g, b, a = hull_mark.split()
    a = a.point(lambda p: int(p * 0.88))
    hull_mark = Image.merge("RGBA", (r, g, b, a))
    out.alpha_composite(hull_mark, (754, 408))

    return out


def main():
    badge = create_hud_badge(236, 58)

    configs = [
        ("assets/kam_hero_banner.jpg", "bottom_right", True, False),
        ("assets/kam_ebpf_neural_system.jpg", "bottom_right", False, False),
        ("assets/kam_jit_self_healing.jpg", "top_left", False, False),
        ("assets/kam_swarm_active_inference.jpg", "bottom_right", False, False),
        ("assets/kam_cyber_cockpit_hud.jpg", "top_left", False, True),
        ("assets/kam_active_inference_chaos.jpg", "bottom_right", False, False),
        ("assets/kam_uav_tactical_edge.jpg", "bottom_right", False, False),
    ]

    for path, pos, is_hero, is_cockpit in configs:
        if not os.path.exists(path):
            continue
        im = Image.open(path).convert("RGBA")
        if is_hero:
            im = upgrade_hero_fuselage(im)
        if is_cockpit:
            im = upgrade_cockpit_mfd(im)

        W, H = im.size
        bw, bh = badge.size
        if pos == "bottom_right":
            xy = (W - bw - 24, H - bh - 20)
        else:
            xy = (24, 20)

        im.alpha_composite(badge, xy)
        im.convert("RGB").save(path, quality=95, subsampling=0)
        print(f"[BRANDED] {path} -> {pos}")


if __name__ == "__main__":
    main()

"""Material palette helpers for the configurator UI."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


CUSTOM_PALETTE_KEY = "custom"


@dataclass(frozen=True)
class ThemeVariant:
    surface: str
    surface_variant: str
    text_primary: str
    text_secondary: str
    accent: str
    accent_hover: str
    accent_pressed: str
    chip_background: str
    chip_text: str
    nav_background: str
    nav_text: str
    nav_selected: str
    nav_hover: str
    card_background: str
    card_border: str
    input_background: str
    input_border: str


@dataclass(frozen=True)
class ThemePalette:
    display_name: str
    light: ThemeVariant
    dark: ThemeVariant


PALETTES: Dict[str, ThemePalette] = {
    "oceanic": ThemePalette(
        display_name="Oceanic",
        light=ThemeVariant(
            surface="#F8FAFC",
            surface_variant="#E2E8F0",
            text_primary="#0F172A",
            text_secondary="#475569",
            accent="#2563EB",
            accent_hover="#1D4ED8",
            accent_pressed="#1E40AF",
            chip_background="rgba(37, 99, 235, 0.15)",
            chip_text="#1E3A8A",
            nav_background="#E2E8F0",
            nav_text="#1E3A8A",
            nav_selected="rgba(37, 99, 235, 0.25)",
            nav_hover="rgba(37, 99, 235, 0.15)",
            card_background="#FFFFFF",
            card_border="rgba(148, 163, 184, 0.35)",
            input_background="#FFFFFF",
            input_border="rgba(148, 163, 184, 0.4)",
        ),
        dark=ThemeVariant(
            surface="#0F172A",
            surface_variant="#1E293B",
            text_primary="#F8FAFC",
            text_secondary="#94A3B8",
            accent="#38BDF8",
            accent_hover="#0EA5E9",
            accent_pressed="#0284C7",
            chip_background="rgba(56, 189, 248, 0.18)",
            chip_text="#E2E8F0",
            nav_background="#0B1120",
            nav_text="#E2E8F0",
            nav_selected="rgba(14, 165, 233, 0.25)",
            nav_hover="rgba(14, 165, 233, 0.15)",
            card_background="#16213A",
            card_border="rgba(30, 41, 59, 0.6)",
            input_background="#111827",
            input_border="rgba(148, 163, 184, 0.35)",
        ),
    ),
    "midnight": ThemePalette(
        display_name="Midnight Violet",
        light=ThemeVariant(
            surface="#FDF4FF",
            surface_variant="#F5D0FE",
            text_primary="#312E81",
            text_secondary="#5B21B6",
            accent="#7C3AED",
            accent_hover="#6D28D9",
            accent_pressed="#5B21B6",
            chip_background="rgba(124, 58, 237, 0.18)",
            chip_text="#4C1D95",
            nav_background="#F3E8FF",
            nav_text="#4C1D95",
            nav_selected="rgba(124, 58, 237, 0.25)",
            nav_hover="rgba(124, 58, 237, 0.12)",
            card_background="#FFFFFF",
            card_border="rgba(167, 139, 250, 0.45)",
            input_background="#FFFFFF",
            input_border="rgba(167, 139, 250, 0.6)",
        ),
        dark=ThemeVariant(
            surface="#1E1B4B",
            surface_variant="#2E1065",
            text_primary="#EDE9FE",
            text_secondary="#C7D2FE",
            accent="#A855F7",
            accent_hover="#9333EA",
            accent_pressed="#7E22CE",
            chip_background="rgba(168, 85, 247, 0.2)",
            chip_text="#EDE9FE",
            nav_background="#18143A",
            nav_text="#EDE9FE",
            nav_selected="rgba(168, 85, 247, 0.3)",
            nav_hover="rgba(168, 85, 247, 0.18)",
            card_background="#2A1E55",
            card_border="rgba(168, 85, 247, 0.35)",
            input_background="#21194A",
            input_border="rgba(193, 166, 255, 0.45)",
        ),
    ),
    "emerald": ThemePalette(
        display_name="Emerald",
        light=ThemeVariant(
            surface="#ECFDF5",
            surface_variant="#D1FAE5",
            text_primary="#064E3B",
            text_secondary="#047857",
            accent="#10B981",
            accent_hover="#059669",
            accent_pressed="#047857",
            chip_background="rgba(16, 185, 129, 0.18)",
            chip_text="#065F46",
            nav_background="#D1FAE5",
            nav_text="#065F46",
            nav_selected="rgba(16, 185, 129, 0.25)",
            nav_hover="rgba(16, 185, 129, 0.12)",
            card_background="#FFFFFF",
            card_border="rgba(134, 239, 172, 0.45)",
            input_background="#FFFFFF",
            input_border="rgba(52, 211, 153, 0.55)",
        ),
        dark=ThemeVariant(
            surface="#022C22",
            surface_variant="#064E3B",
            text_primary="#ECFDF5",
            text_secondary="#6EE7B7",
            accent="#34D399",
            accent_hover="#10B981",
            accent_pressed="#0F9D76",
            chip_background="rgba(52, 211, 153, 0.22)",
            chip_text="#ECFDF5",
            nav_background="#03201B",
            nav_text="#ECFDF5",
            nav_selected="rgba(52, 211, 153, 0.28)",
            nav_hover="rgba(52, 211, 153, 0.15)",
            card_background="#064E3B",
            card_border="rgba(16, 185, 129, 0.35)",
            input_background="#043D2E",
            input_border="rgba(110, 231, 183, 0.45)",
        ),
    ),
    "sunrise": ThemePalette(
        display_name="Sunrise",
        light=ThemeVariant(
            surface="#FFF7ED",
            surface_variant="#FFEDD5",
            text_primary="#7C2D12",
            text_secondary="#C2410C",
            accent="#F97316",
            accent_hover="#EA580C",
            accent_pressed="#C2410C",
            chip_background="rgba(249, 115, 22, 0.18)",
            chip_text="#9A3412",
            nav_background="#FFE4C7",
            nav_text="#9A3412",
            nav_selected="rgba(249, 115, 22, 0.25)",
            nav_hover="rgba(249, 115, 22, 0.12)",
            card_background="#FFFFFF",
            card_border="rgba(253, 186, 116, 0.45)",
            input_background="#FFFFFF",
            input_border="rgba(251, 146, 60, 0.55)",
        ),
        dark=ThemeVariant(
            surface="#1F1306",
            surface_variant="#2F1809",
            text_primary="#FFEDD5",
            text_secondary="#FED7AA",
            accent="#FB923C",
            accent_hover="#F97316",
            accent_pressed="#EA580C",
            chip_background="rgba(251, 146, 60, 0.22)",
            chip_text="#FFEDD5",
            nav_background="#170D04",
            nav_text="#FFEDD5",
            nav_selected="rgba(251, 146, 60, 0.28)",
            nav_hover="rgba(251, 146, 60, 0.16)",
            card_background="#2F1809",
            card_border="rgba(251, 146, 60, 0.35)",
            input_background="#251104",
            input_border="rgba(253, 186, 116, 0.45)",
        ),
    ),
    "orchid": ThemePalette(
        display_name="Orchid",
        light=ThemeVariant(
            surface="#FDF2F8",
            surface_variant="#FCE7F3",
            text_primary="#831843",
            text_secondary="#BE185D",
            accent="#EC4899",
            accent_hover="#DB2777",
            accent_pressed="#BE185D",
            chip_background="rgba(236, 72, 153, 0.18)",
            chip_text="#9D174D",
            nav_background="#FBCFE8",
            nav_text="#9D174D",
            nav_selected="rgba(236, 72, 153, 0.25)",
            nav_hover="rgba(236, 72, 153, 0.12)",
            card_background="#FFFFFF",
            card_border="rgba(251, 207, 232, 0.45)",
            input_background="#FFFFFF",
            input_border="rgba(244, 114, 182, 0.6)",
        ),
        dark=ThemeVariant(
            surface="#3B0A2A",
            surface_variant="#500724",
            text_primary="#FCE7F3",
            text_secondary="#FBCFE8",
            accent="#F472B6",
            accent_hover="#EC4899",
            accent_pressed="#DB2777",
            chip_background="rgba(244, 114, 182, 0.2)",
            chip_text="#FCE7F3",
            nav_background="#310720",
            nav_text="#FCE7F3",
            nav_selected="rgba(244, 114, 182, 0.3)",
            nav_hover="rgba(244, 114, 182, 0.18)",
            card_background="#500724",
            card_border="rgba(236, 72, 153, 0.35)",
            input_background="#42061E",
            input_border="rgba(251, 207, 232, 0.4)",
        ),
    ),
    "amber": ThemePalette(
        display_name="Amber",
        light=ThemeVariant(
            surface="#FFFBEB",
            surface_variant="#FEF3C7",
            text_primary="#78350F",
            text_secondary="#B45309",
            accent="#F59E0B",
            accent_hover="#D97706",
            accent_pressed="#B45309",
            chip_background="rgba(245, 158, 11, 0.18)",
            chip_text="#92400E",
            nav_background="#FDE68A",
            nav_text="#92400E",
            nav_selected="rgba(245, 158, 11, 0.25)",
            nav_hover="rgba(245, 158, 11, 0.12)",
            card_background="#FFFFFF",
            card_border="rgba(253, 230, 138, 0.45)",
            input_background="#FFFFFF",
            input_border="rgba(250, 204, 21, 0.55)",
        ),
        dark=ThemeVariant(
            surface="#271806",
            surface_variant="#422006",
            text_primary="#FEF3C7",
            text_secondary="#FDE68A",
            accent="#FBBF24",
            accent_hover="#F59E0B",
            accent_pressed="#D97706",
            chip_background="rgba(251, 191, 36, 0.22)",
            chip_text="#FEF3C7",
            nav_background="#1D1204",
            nav_text="#FEF3C7",
            nav_selected="rgba(251, 191, 36, 0.28)",
            nav_hover="rgba(251, 191, 36, 0.16)",
            card_background="#422006",
            card_border="rgba(251, 191, 36, 0.32)",
            input_background="#341905",
            input_border="rgba(251, 191, 36, 0.4)",
        ),
    ),
    "slate": ThemePalette(
        display_name="Slate",
        light=ThemeVariant(
            surface="#F9FAFB",
            surface_variant="#E5E7EB",
            text_primary="#111827",
            text_secondary="#4B5563",
            accent="#475569",
            accent_hover="#334155",
            accent_pressed="#1F2937",
            chip_background="rgba(71, 85, 105, 0.18)",
            chip_text="#1E293B",
            nav_background="#E5E7EB",
            nav_text="#1E293B",
            nav_selected="rgba(71, 85, 105, 0.25)",
            nav_hover="rgba(71, 85, 105, 0.12)",
            card_background="#FFFFFF",
            card_border="rgba(148, 163, 184, 0.45)",
            input_background="#FFFFFF",
            input_border="rgba(148, 163, 184, 0.5)",
        ),
        dark=ThemeVariant(
            surface="#111827",
            surface_variant="#1F2937",
            text_primary="#F9FAFB",
            text_secondary="#CBD5F5",
            accent="#64748B",
            accent_hover="#475569",
            accent_pressed="#334155",
            chip_background="rgba(100, 116, 139, 0.18)",
            chip_text="#F1F5F9",
            nav_background="#0F172A",
            nav_text="#F1F5F9",
            nav_selected="rgba(100, 116, 139, 0.3)",
            nav_hover="rgba(100, 116, 139, 0.18)",
            card_background="#1F2937",
            card_border="rgba(71, 85, 105, 0.45)",
            input_background="#16213A",
            input_border="rgba(100, 116, 139, 0.4)",
        ),
    ),
    "forest": ThemePalette(
        display_name="Forest",
        light=ThemeVariant(
            surface="#F1F5F9",
            surface_variant="#E2E8F0",
            text_primary="#1B4332",
            text_secondary="#2D6A4F",
            accent="#40916C",
            accent_hover="#2D6A4F",
            accent_pressed="#1B4332",
            chip_background="rgba(64, 145, 108, 0.18)",
            chip_text="#1B4332",
            nav_background="#E2E8F0",
            nav_text="#1B4332",
            nav_selected="rgba(64, 145, 108, 0.25)",
            nav_hover="rgba(64, 145, 108, 0.12)",
            card_background="#FFFFFF",
            card_border="rgba(148, 163, 184, 0.4)",
            input_background="#FFFFFF",
            input_border="rgba(74, 222, 128, 0.4)",
        ),
        dark=ThemeVariant(
            surface="#0B271E",
            surface_variant="#123524",
            text_primary="#E7F8EF",
            text_secondary="#A7F3D0",
            accent="#52B788",
            accent_hover="#40916C",
            accent_pressed="#2D6A4F",
            chip_background="rgba(82, 183, 136, 0.22)",
            chip_text="#E7F8EF",
            nav_background="#071812",
            nav_text="#E7F8EF",
            nav_selected="rgba(82, 183, 136, 0.28)",
            nav_hover="rgba(82, 183, 136, 0.16)",
            card_background="#123524",
            card_border="rgba(82, 183, 136, 0.35)",
            input_background="#0E2A1E",
            input_border="rgba(167, 243, 208, 0.4)",
        ),
    ),
    "rose": ThemePalette(
        display_name="Rose",
        light=ThemeVariant(
            surface="#FFF1F2",
            surface_variant="#FFE4E6",
            text_primary="#881337",
            text_secondary="#BE123C",
            accent="#F43F5E",
            accent_hover="#E11D48",
            accent_pressed="#BE123C",
            chip_background="rgba(244, 63, 94, 0.18)",
            chip_text="#9F1239",
            nav_background="#FECDD3",
            nav_text="#9F1239",
            nav_selected="rgba(244, 63, 94, 0.25)",
            nav_hover="rgba(244, 63, 94, 0.12)",
            card_background="#FFFFFF",
            card_border="rgba(254, 205, 211, 0.45)",
            input_background="#FFFFFF",
            input_border="rgba(244, 63, 94, 0.55)",
        ),
        dark=ThemeVariant(
            surface="#44121D",
            surface_variant="#4C0519",
            text_primary="#FFE4E6",
            text_secondary="#FECDD3",
            accent="#FB7185",
            accent_hover="#F43F5E",
            accent_pressed="#E11D48",
            chip_background="rgba(251, 113, 133, 0.22)",
            chip_text="#FFE4E6",
            nav_background="#320C14",
            nav_text="#FFE4E6",
            nav_selected="rgba(251, 113, 133, 0.3)",
            nav_hover="rgba(251, 113, 133, 0.18)",
            card_background="#4C0519",
            card_border="rgba(244, 63, 94, 0.35)",
            input_background="#3B0413",
            input_border="rgba(251, 113, 133, 0.45)",
        ),
    ),
    "graphite": ThemePalette(
        display_name="Graphite",
        light=ThemeVariant(
            surface="#F4F4F5",
            surface_variant="#E4E4E7",
            text_primary="#18181B",
            text_secondary="#3F3F46",
            accent="#27272A",
            accent_hover="#18181B",
            accent_pressed="#09090B",
            chip_background="rgba(39, 39, 42, 0.18)",
            chip_text="#27272A",
            nav_background="#E4E4E7",
            nav_text="#27272A",
            nav_selected="rgba(39, 39, 42, 0.25)",
            nav_hover="rgba(39, 39, 42, 0.12)",
            card_background="#FFFFFF",
            card_border="rgba(161, 161, 170, 0.45)",
            input_background="#FFFFFF",
            input_border="rgba(113, 113, 122, 0.45)",
        ),
        dark=ThemeVariant(
            surface="#09090B",
            surface_variant="#18181B",
            text_primary="#F4F4F5",
            text_secondary="#D4D4D8",
            accent="#52525B",
            accent_hover="#3F3F46",
            accent_pressed="#27272A",
            chip_background="rgba(82, 82, 91, 0.22)",
            chip_text="#F4F4F5",
            nav_background="#050505",
            nav_text="#F4F4F5",
            nav_selected="rgba(82, 82, 91, 0.28)",
            nav_hover="rgba(82, 82, 91, 0.16)",
            card_background="#18181B",
            card_border="rgba(82, 82, 91, 0.35)",
            input_background="#121212",
            input_border="rgba(82, 82, 91, 0.4)",
        ),
    ),
}


def _hex_to_rgb(color: str) -> tuple[int, int, int]:
    color = color.lstrip("#")
    return int(color[0:2], 16), int(color[2:4], 16), int(color[4:6], 16)


def _rgb_to_hex(r: int, g: int, b: int) -> str:
    return f"#{max(0, min(255, r)):02X}{max(0, min(255, g)):02X}{max(0, min(255, b)):02X}"


def _mix(color_a: str, color_b: str, factor: float) -> str:
    ra, ga, ba = _hex_to_rgb(color_a)
    rb, gb, bb = _hex_to_rgb(color_b)
    r = int(ra + (rb - ra) * factor)
    g = int(ga + (gb - ga) * factor)
    b = int(ba + (bb - ba) * factor)
    return _rgb_to_hex(r, g, b)


def _derive_custom_variant(mode: str, primary: str, surface: str, text: str) -> ThemeVariant:
    if mode == "light":
        accent_hover = _mix(primary, "#000000", 0.1)
        accent_pressed = _mix(primary, "#000000", 0.2)
        surface_variant = _mix(surface, "#000000", 0.05)
        text_secondary = _mix(text, surface, 0.45)
        nav_background = _mix(surface, primary, 0.08)
        nav_selected = _mix(primary, text, 0.75)
        nav_hover = _mix(primary, surface, 0.15)
        chip_background = "rgba(255, 255, 255, 0.4)"
        chip_text = text
        card_background = _mix(surface, "#FFFFFF", 0.8)
        card_border = "rgba(0, 0, 0, 0.08)"
        input_background = card_background
        input_border = "rgba(0, 0, 0, 0.12)"
    else:
        accent_hover = _mix(primary, "#FFFFFF", 0.15)
        accent_pressed = _mix(primary, "#000000", 0.2)
        surface_variant = _mix(surface, "#FFFFFF", 0.08)
        text_secondary = _mix(text, surface_variant, 0.25)
        nav_background = _mix(surface, "#000000", 0.08)
        nav_selected = _mix(primary, "#FFFFFF", 0.3)
        nav_hover = _mix(primary, "#FFFFFF", 0.18)
        chip_background = "rgba(255, 255, 255, 0.12)"
        chip_text = text
        card_background = _mix(surface, "#FFFFFF", 0.08)
        card_border = "rgba(255, 255, 255, 0.1)"
        input_background = _mix(surface, "#000000", 0.05)
        input_border = "rgba(255, 255, 255, 0.18)"

    return ThemeVariant(
        surface=surface,
        surface_variant=surface_variant,
        text_primary=text,
        text_secondary=text_secondary,
        accent=primary,
        accent_hover=accent_hover,
        accent_pressed=accent_pressed,
        chip_background=chip_background,
        chip_text=chip_text,
        nav_background=nav_background,
        nav_text=text,
        nav_selected=nav_selected,
        nav_hover=nav_hover,
        card_background=card_background,
        card_border=card_border,
        input_background=input_background,
        input_border=input_border,
    )


def _coerce_hex(value: str, fallback: str) -> str:
    value = value.strip().upper()
    if len(value) == 6:
        value = f"#{value}"
    if len(value) == 7 and all(c in "0123456789ABCDEF#" for c in value):
        return value
    return fallback


def resolve_theme_variant(
    *,
    mode: str,
    palette_key: str,
    custom_primary: str,
    custom_surface: str,
    custom_text: str,
) -> ThemeVariant:
    mode_normalised = "light" if mode.lower() == "light" else "dark"
    palette_key_normalised = palette_key.lower()

    if palette_key_normalised == CUSTOM_PALETTE_KEY:
        primary = _coerce_hex(custom_primary or "#2563EB", "#2563EB")
        surface = _coerce_hex(custom_surface or ("#F8FAFC" if mode_normalised == "light" else "#0F172A"),
                              "#F8FAFC" if mode_normalised == "light" else "#0F172A")
        text = _coerce_hex(custom_text or ("#0F172A" if mode_normalised == "light" else "#F8FAFC"),
                           "#0F172A" if mode_normalised == "light" else "#F8FAFC")
        variant = _derive_custom_variant(mode_normalised, primary, surface, text)
    else:
        palette = PALETTES.get(palette_key_normalised, PALETTES["oceanic"])
        variant = palette.light if mode_normalised == "light" else palette.dark

    return variant


def build_stylesheet(
    *,
    mode: str,
    palette_key: str,
    custom_primary: str,
    custom_surface: str,
    custom_text: str,
) -> str:
    variant = resolve_theme_variant(
        mode=mode,
        palette_key=palette_key,
        custom_primary=custom_primary,
        custom_surface=custom_surface,
        custom_text=custom_text,
    )

    return f"""
QWidget {{
    background: transparent;
    color: {variant.text_primary};
    font-family: 'Segoe UI', 'Roboto', sans-serif;
    font-size: 14px;
}}
QFrame#MaterialSurface {{
    background: {variant.surface};
    border-radius: 28px;
}}
QWidget#MaterialTitleBar {{
    background: transparent;
}}
#MaterialAppTitle {{
    font-size: 24px;
    font-weight: 600;
    color: {variant.accent};
}}
#MaterialSubtitle {{
    font-size: 13px;
    color: {variant.text_secondary};
}}
#StatusChip {{
    border-radius: 16px;
    padding: 6px 16px;
    background: {variant.chip_background};
    color: {variant.chip_text};
}}
QWidget#QuickActions {{
    background: {variant.surface_variant};
    border-radius: 24px;
}}
QToolButton#IconButton {{
    background: transparent;
    border: none;
    border-radius: 18px;
    padding: 10px;
    color: {variant.text_secondary};
}}
QWidget#QuickActions QToolButton#IconButton {{
    padding: 8px;
}}
QToolButton#IconButton:hover {{
    background: {variant.nav_hover};
    color: {variant.accent};
}}
QToolButton#IconButton:pressed {{
    background: {variant.nav_selected};
    color: {variant.accent};
}}
QToolButton#WindowControl {{
    background: transparent;
    border: none;
    border-radius: 14px;
    padding: 6px;
}}
QToolButton#WindowControl:hover {{
    background: {variant.nav_hover};
}}
QToolButton#WindowControl:pressed {{
    background: {variant.nav_selected};
}}
QFrame#NavigationRail {{
    background: {variant.nav_background};
    border-top-left-radius: 28px;
    border-bottom-left-radius: 28px;
    border-right: 1px solid {variant.card_border};
}}
#NavigationHeading {{
    font-size: 13px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.14em;
    color: {variant.text_secondary};
}}
QWidget#NavigationFooter {{
    background: {variant.surface_variant};
    border-radius: 22px;
}}
QToolButton#ThemeToggle {{
    border: none;
    border-radius: 16px;
    padding: 6px 14px;
    font-size: 18px;
}}
QToolButton#ThemeToggle[mode="light"] {{
    background: {variant.chip_background};
    color: {variant.chip_text};
}}
QToolButton#ThemeToggle[mode="dark"] {{
    background: rgba(255, 255, 255, 0.08);
    color: {variant.text_primary};
}}
QToolButton#ThemeToggle:hover {{
    background: {variant.nav_hover};
}}
#NavVersion {{
    color: {variant.text_secondary};
    font-weight: 500;
}}
QListWidget#MaterialNav {{
    background: transparent;
    border: none;
    padding: 4px 0;
    color: {variant.nav_text};
}}
QListWidget#MaterialNav::item {{
    padding: 12px 18px;
    margin: 2px 0;
    border-radius: 14px;
}}
QListWidget#MaterialNav::item:selected {{
    background: {variant.nav_selected};
    color: #FFFFFF;
}}
QListWidget#MaterialNav::item:hover {{
    background: {variant.nav_hover};
}}
#MaterialTitle {{
    font-size: 18px;
    font-weight: 600;
    color: {variant.accent};
}}
#MaterialCard {{
    background: {variant.card_background};
    border-radius: 18px;
    padding: 16px;
    border: 1px solid {variant.card_border};
}}
QListWidget#MaterialCardList {{
    background: {variant.card_background};
    border-radius: 18px;
    padding: 12px;
    border: 1px solid {variant.card_border};
}}
QGroupBox {{
    border: 1px solid {variant.card_border};
    border-radius: 18px;
    margin-top: 18px;
    background: {variant.card_background};
    padding-top: 22px;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 20px;
    top: 10px;
    padding: 0 6px;
    color: {variant.text_secondary};
    font-weight: 600;
}}
QScrollArea {{
    background: transparent;
    border: none;
}}
QScrollBar:vertical {{
    width: 12px;
    background: transparent;
}}
QScrollBar::handle:vertical {{
    background: {variant.surface_variant};
    border-radius: 6px;
}}
QScrollBar::handle:vertical:hover {{
    background: {variant.nav_hover};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
QComboBox, QSpinBox, QDoubleSpinBox, QTextEdit, QLineEdit {{
    border-radius: 12px;
    padding: 8px 14px;
    border: 1px solid {variant.input_border};
    background: {variant.input_background};
    color: {variant.text_primary};
}}
QComboBox QAbstractItemView {{
    background: {variant.surface_variant};
    selection-background-color: {variant.accent};
    selection-color: #FFFFFF;
    border-radius: 12px;
}}
QPushButton {{
    border-radius: 18px;
    padding: 10px 28px;
    background: {variant.accent};
    color: #FFFFFF;
    border: none;
}}
QPushButton:hover {{
    background: {variant.accent_hover};
}}
QPushButton:pressed {{
    background: {variant.accent_pressed};
}}
QCheckBox {{
    padding: 6px 0;
    color: {variant.text_primary};
}}
"""


__all__ = ["PALETTES", "CUSTOM_PALETTE_KEY", "build_stylesheet", "resolve_theme_variant"]

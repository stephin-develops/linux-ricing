#!/usr/bin/env python3
"""
torii-fetch: fastfetch with your image on the left and the specs framed inside a torii gate.

fastfetch can't pad values to a fixed width, so the right-hand pillar would be ragged.
This script reads your specs from fastfetch, pads every line to a fixed width, writes a
config with the torii drawn as static lines, and then runs fastfetch with that config.

Usage:   python3 torii-fetch.py            (run it instead of `fastfetch`)
         python3 torii-fetch.py --preview  (print the torii only, no fastfetch needed)
"""
import getpass, json, os, re, socket, subprocess, sys, tempfile, unicodedata

HERE = os.path.dirname(os.path.abspath("tori"))

# ---- things you may want to tweak ------------------------------------------------
IMAGE      = os.path.join(HERE, "pi2.png")
LOGO_TYPE  = "kitty-direct"      # or kitty-direct / sixel / iterm / chafa
IMG_COLS   = 36          # image width in terminal cells
IMG_ROWS   = 24          # 36 cols x 24 rows ~ 3:4, matches a 1200x1600 image
WIDTH      = 60          # torii width in cells
PILLAR_X   = 4           # how far the pillars sit in from the beam ends
# -------------------------------------------------------------------------------

RED, WHITE, DIM, RST = "\x1b[31m", "\x1b[37m", "\x1b[90m", "\x1b[0m"

SPECS = [  # kanji, label, fastfetch module
    ("基", "OS",       "os"),
    ("機", "Host",     "host"),
    ("核", "Kernel",   "kernel"),
    ("時", "Uptime",   "uptime"),
    ("包", "Packages", "packages"),
    ("殻", "Shell",    "shell"),
    ("窓", "WM",       "wm"),
    ("端", "Terminal", "terminal"),
    ("脳", "CPU",      "cpu"),
    ("絵", "GPU",      "gpu"),
    ("憶", "Memory",   "memory"),
    ("蔵", "Disk",     "disk"),
]

def cells(s):
    """Width in terminal cells (CJK characters take two)."""
    return sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in s)

def fit(s, n):
    """Truncate to n cells with an ellipsis."""
    if cells(s) <= n:
        return s
    out = ""
    for c in s:
        if cells(out + c) > n - 1:
            break
        out += c
    return out + "…"

def clean(v):
    v = re.sub(r"\((R|TM|tm|r)\)", "", v)
    v = re.sub(r"\s+with Radeon Graphics", "", v)
    return re.sub(r"\s{2,}", " ", v).strip()

def fetch_values():
    cfg = {"modules": [{"type": m, "key": "k_" + m} for _, _, m in SPECS],
           "display": {"separator": ": "}}
    with tempfile.NamedTemporaryFile("w", suffix=".jsonc", delete=False) as f:
        json.dump(cfg, f)
        path = f.name
    vals = {}
    try:
        out = subprocess.run(["fastfetch", "-c", path, "--logo", "none", "--pipe", "true"],
                             capture_output=True, text=True).stdout
        for line in out.splitlines():
            m = re.match(r"k_(\w+): (.*)", line.strip())
            if m:
                vals[m.group(1)] = clean(m.group(2))
    finally:
        os.unlink(path)
    return vals

def build_rows(vals):
    W, p = WIDTH, PILLAR_X
    inner = W - 2 * p - 4
    def line(content_plain, content_col, pad_left=0):
        """Row with both pillars; content is placed inside, right-padded to the inner width."""
        used = pad_left + cells(content_plain)
        fill = " " * max(0, inner - used)
        return (" " * p + RED + "██" + RST + " " * pad_left + content_col + fill + RED + "██" + RST)
    blank = line("", "")
    rows = []
    # kasagi (top beam), shimaki, then pillars with the nuki (second beam)
    rows.append(RED + "██" + "▄" * (W - 4) + "██" + RST)
    rows.append(RED + "▀" + "█" * (W - 2) + "▀" + RST)
    rows.append(" " * 3 + RED + "▀" * (W - 6) + RST)
    rows.append(blank)
    rows.append(" " * (p - 2) + RED + "█" * (W - 2 * (p - 2)) + RST)
    # header: user@host centred
    head = f"{getpass.getuser()}@{socket.gethostname()}"
    head = fit(head, inner - 2)
    left = (inner - cells(head)) // 2
    rows.append(line(head, RED + head + RST, pad_left=left))
    rows.append(line("─" * inner, DIM + "─" * inner + RST))
    # specs
    for kanji, label, mod in SPECS:
        val = vals.get(mod, "n/a")
        room = inner - (1 + 2 + 1 + 8 + 1)
        val = fit(val, room)
        plain = f" {kanji} {label:<8} {val}"
        col = f" {RED}{kanji}{RST} {WHITE}{label:<8}{RST} {val}"
        rows.append(line(plain, col))
    rows.append(line("─" * inner, DIM + "─" * inner + RST))
    dots = " ".join("●" for _ in range(8))
    colors = " ".join(f"\x1b[{c}m●{RST}" for c in (31, 32, 33, 34, 35, 36, 37, 90))
    rows.append(line(dots, colors, pad_left=(inner - cells(dots)) // 2))
    rows.append(blank)
    # pillar bases (kamebara)
    gap1 = W - 2 * (p - 1) - 8
    gap2 = W - 2 * (p - 2) - 12
    rows.append(" " * (p - 1) + RED + "████" + RST + " " * gap1 + RED + "████" + RST)
    rows.append(" " * (p - 2) + RED + "▀▀▀▀▀▀" + RST + " " * gap2 + RED + "▀▀▀▀▀▀" + RST)
    return rows

def main():
    preview = "--preview" in sys.argv
    if preview:
        vals = dict(os="Arch Linux x86_64", host="Lenovo IdeaPad 5 Pro", kernel="Linux 6.11.2",
                    uptime="3 hours, 12 mins", packages="1204 (pacman)", shell="zsh 5.9",
                    wm="Hyprland", terminal="kitty 0.36",
                    cpu="AMD Ryzen 7 5800H (16) @ 4.46 GHz", gpu="NVIDIA GeForce RTX 3050",
                    memory="5.2 GiB / 15.4 GiB (34%)", disk="212 GiB / 475 GiB (45%)")
    else:
        vals = fetch_values()
    rows = build_rows(vals)
    if preview:
        print("\n".join(rows))
        return
    cfg = {
        "$schema": "https://github.com/fastfetch-cli/fastfetch/raw/dev/doc/json_schema.json",
        "logo": {"type": LOGO_TYPE, "source": IMAGE, "width": IMG_COLS, "height": IMG_ROWS,
                 "padding": {"top": 0, "left": 2, "right": 3}},
        "display": {"separator": ""},
        "modules": [{"type": "custom", "format": r} for r in rows],
    }
    out = os.path.join(HERE, "torii.generated.jsonc")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=1)
    subprocess.run(["fastfetch", "-c", out])

if __name__ == "__main__":
    main()

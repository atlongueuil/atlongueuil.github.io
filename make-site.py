#!/usr/bin/env python3
from markdown import markdown
from pathlib import Path
import shutil
import hashlib
import jinja2


HEADER = """\
<!doctype html>
<html lang="fr">
<head>
  <meta charset="utf-8">
  <link rel="stylesheet" href="static/style.css">
  <title>{{ title }} - {{ page.text }}</title>
</head>
<body>
  <header>
    <img src="static/logo.png" />
    <nav>
    {% for name, text in pages.items() %}
      <li><a href="{{ name }}.html">{{ text }}</a></li>
    {% endfor %}
    </nav>
  </header>
  <main>
"""

FOOTER = """
  </main>
  <footer>
    <p>{{ copyright }}</p>
  </footer>
</body>
</html>
"""

SEATING = """
<table>
  <tr>
    <th>{{ what }}</th><th>{{ where }}</th><th>{{ when }}</th>
  </tr>
  <tr>
    <td colspan="3"><img src="{{ svg }}" /></td>
  </tr>
</table>
"""


def draw_svg(reserved):
    size = 40

    def make_args(args):
        return " ".join(f'{k}="{v}"' for k, v in args.items())

    def draw_text(x, y, size, text, fill="black", **kwargs):
        args = make_args(
            {
                "x": x,
                "y": y,
                "dominant-baseline": "middle",
                "text-anchor": "middle",
                "font-family": "sans-serif",
                "font-size": size,
                "fill": fill,
            }
            | kwargs
        )
        return f"<text {args}>{text}</text>"

    def draw_rect(x, y, w, h, stroke="black", fill="none"):
        args = make_args(
            {
                "x": x,
                "y": y,
                "width": w,
                "height": h,
                "stroke": stroke,
                "fill": fill,
            }
        )
        return f"<rect {args} />"

    def draw_seat(x, y, k, color):
        return "\n".join(
            [
                f'<g transform="translate({x},{y}) scale(1.6)">',
                "  " + draw_rect(-10, -10, 20, 20, fill=color),
                "  " + draw_text(0, 0, 9, str(k), dy=".1em"),
                "</g>",
            ]
        )

    # create a grid of seats (note that there's no "I" row)
    ls = [i * 2 + 1 for i in reversed(range(12))]
    rs = [i * 2 + 2 for i in range(12)]
    cols = ls[:6] + [0, -1, 0] + ls[6:] + rs[:6] + [0, -1, 0] + rs[6:]
    rows = "ABCDEFGHJKLMNOPQ"
    seats = []
    seats += [cols[:] for _ in range(2)]
    seats += [[0] * 2 + cols[2:-2] + [0] * 2 for _ in range(8)]
    seats += [[0] * 2 + cols[2:-4] + [0] * 4]
    seats += [[0] * 6 + cols[6:-6] + [0] * 6 for _ in range(4)]
    seats += [[0] * 6 + cols[6:13] + [0] * 4 + cols[-13:-6] + [0] * 6]
    assert len(seats) == len(rows)
    assert all(len(cols) == len(row) for row in seats)

    w = size * len(cols) + 2 * size
    h = size * len(rows) + 6 * size
    stage = size * 2
    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}">',
        # draw the stage at the front
        draw_rect(0, 0, w, stage, stroke="none", fill="#8bc34a"),
        draw_text(w / 2, stage / 2 + 5, 24, "Scène", "white"),
        # draw the production at the back
        draw_rect(0, h - stage, w, stage, stroke="none", fill="#8bc34a"),
        draw_text(w / 2, h - stage / 2 + 5, 24, "Régie", "white"),
    ]

    for j, row in enumerate(seats):
        for i, k in enumerate(row):
            if k == 0:
                continue
            x = size * (i + 1.5)
            y = size * (j + 3.5)
            if k < 0:
                svg.append(draw_text(x, y, 20, str(rows[j])))
            else:
                color = "none"
                if k > 20:
                    color = "yellow"
                seat = f"{rows[j]}{k}"
                if seat in reserved:
                    color = "#ffcccb"
                svg.append(draw_seat(x, y, k, color))

    svg.append("</svg>")
    return "\n".join(svg)


def build_site(root):
    # prepare the directory where the static site will be generated
    if root.exists():
        shutil.rmtree(root)
    root.mkdir()

    Path(root, "static").mkdir()
    shutil.copy("site/logo.png", Path(root, "static"))
    shutil.copy("site/style.css", Path(root, "static"))

    # setup labels for navigation
    pages = {
        "index": "Accueil",
        "programme": "Programme",
        "qui-sommes-nous": "Qui sommes-nous ?",
        "realisations": "Réalisations",
        "commanditaires": "Commanditaires",
        "contact": "Contact",
        "vente-de-billets": "Vente de billets",
    }

    # setup HTML templates
    env = jinja2.Environment(autoescape=True)
    header = env.from_string(HEADER)
    footer = env.from_string(FOOTER)
    seating = env.from_string(SEATING)
    context = {
        "organization": "l'Atelier théâtral de Longueuil",
        "pages": pages,
        "copyright": "© Atelier théâtral de Longueuil",
    }

    # convert to markdown and gather images
    texts = {}
    for name in pages.keys():
        directory = name if name != "index" else "acceuil"

        md = markdown(
            Path("site", directory, "page.md").read_text(),
            extensions=["extra", "smarty"],
            extension_configs={
                "smarty": {
                    "smart_dashes": True,
                    "smart_quotes": True,
                    "smart_angled_quotes": True,
                    "smart_ellipses": True,
                }
            },
        )

        images = []
        for file in Path("site", directory).iterdir():
            ext = file.suffix.lower()
            if ext in [".jpg", ".jpeg", ".png"]:
                images.append(file)
                uid = hashlib.sha1(str(file).encode()).hexdigest()
                dst = f"static/{uid}{ext}"
                img = f'src="{file.name}"'
                md = md.replace(img, f'src="{dst}"')
                shutil.copy(file, Path(root, dst))

        texts[name] = md

    for csv in sorted(Path("site", "vente-de-billets").glob("*.txt")):
        reserved = []
        lines = csv.read_text().splitlines()
        lines = [line for line in lines if not line.startswith("#")]
        for line in lines[3:]:
            line = line.strip()
            if line:
                reserved.append(line)
        svg = f"static/{csv.stem}.svg"
        Path(root, svg).write_text(draw_svg(reserved))
        what, where, when = lines[:3]
        texts["vente-de-billets"] += seating.render(
            {
                "what": what,
                "where": where,
                "when": when,
                "svg": svg,
            }
        )

    for name, text in pages.items():
        context["page"] = {"name": name, "text": text}
        html = header.render(context) + texts[name] + footer.render(context)
        Path(root, f"{name}.html").write_text(html)


if __name__ == "__main__":
    build_site(Path(".www"))

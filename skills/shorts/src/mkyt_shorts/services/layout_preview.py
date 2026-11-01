"""Vista previa del layout: el fotograma con una cuadricula de coordenadas y los recuadros marcados."""
import cv2

from mkyt_shorts.domain.media import REF_H, REF_W

COLORS = {"tile": (0, 220, 0), "default": (0, 200, 255), "banner": (255, 120, 0), "footer": (255, 0, 200), "drop": (120, 120, 255)}


def draw_grid(img, step=120):
    for x in range(0, REF_W, step):
        cv2.line(img, (x, 0), (x, REF_H), (255, 255, 255), 1)
        cv2.putText(img, str(x), (x + 3, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 3)
        cv2.putText(img, str(x), (x + 3, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)
    for y in range(0, REF_H, step):
        cv2.line(img, (0, y), (REF_W, y), (255, 255, 255), 1)
        cv2.putText(img, str(y), (3, y + 14), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 3)
        cv2.putText(img, str(y), (3, y + 14), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)


def render_preview(layout, frame):
    """Devuelve la imagen (1440x810) con cuadricula y recuadros de `layout`."""
    img = frame.copy()
    overlay = img.copy()
    draw_grid(overlay)
    img = cv2.addWeighted(overlay, 0.35, img, 0.65, 0)

    def box(rect, label, color):
        x, y, w, h = rect
        cv2.rectangle(img, (x, y), (x + w, y + h), color, 4)
        cv2.putText(img, label, (x + 8, y + 32), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 0), 5)
        cv2.putText(img, label, (x + 8, y + 32), cv2.FONT_HERSHEY_SIMPLEX, 1.0, color, 2)

    for k, t in layout["tiles"].items():
        box(t["rect"], k + (" (defecto)" if k == layout.get("default_tile") else ""), COLORS["default" if k == layout.get("default_tile") else "tile"])
    for d in layout.get("detected", {}).get("descartados", []):
        box(d["rect"], "descartado", COLORS["drop"])
    if layout.get("banner_rect"):
        box(layout["banner_rect"], "banner", COLORS["banner"])
    if layout.get("footer_rect"):
        box(layout["footer_rect"], "pie", COLORS["footer"])
    return cv2.resize(img, (1440, 810), interpolation=cv2.INTER_AREA)

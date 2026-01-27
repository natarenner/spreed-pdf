from pathlib import Path
from weasyprint import HTML, CSS
import re

HTML_FILE = Path("assets/auditoria.html")
OUT_PDF = Path("auditoria-fit.pdf")

def render_with_height_mm(height_mm: int):
    html_str = HTML_FILE.read_text(encoding="utf-8")

    # substitui --pageH: ...mm no :root
    html_str = re.sub(r'--pageH:\s*\d+mm\s*;', f'--pageH: {height_mm}mm;', html_str)

    doc = HTML(string=html_str, base_url=str(HTML_FILE.parent.resolve())).render(media_type="screen")
    return doc

# limites (ajuste se seu conteúdo for maior)
low = 400      # mm
high = 5000    # mm

best = None

# primeiro, garante que HIGH cabe em 1 página
doc_high = render_with_height_mm(high)
if len(doc_high.pages) != 1:
    raise RuntimeError(f"Mesmo com {high}mm ainda deu {len(doc_high.pages)} páginas. Aumente o high.")

# busca binária pela menor altura que ainda dá 1 página
while low <= high:
    mid = (low + high) // 2
    doc = render_with_height_mm(mid)
    pages = len(doc.pages)

    if pages == 1:
        best = mid
        high = mid - 1
    else:
        low = mid + 1

if best is None:
    raise RuntimeError("Não achei uma altura que caiba em 1 página. Verifique o HTML/CSS.")

# render final com a melhor altura encontrada
final_doc = render_with_height_mm(best)
final_doc.write_pdf(str(OUT_PDF))

print(f"Altura mínima encontrada: {best}mm (1 página)")
print(f"PDF gerado: {OUT_PDF}")

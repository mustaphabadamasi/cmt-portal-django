import os
from io import BytesIO
from django.http import HttpResponse
from django.template.loader import get_template
from django.conf import settings

CMT_LOGO  = os.path.join(settings.BASE_DIR, "static", "images", "cmt_logo.png.png")
FUDMA_LOGO = os.path.join(settings.BASE_DIR, "static", "images", "fudma_logo.png_optimized_250.png")

def render_to_pdf(template_path, context):
    from xhtml2pdf import pisa
    context["CMT_LOGO"]   = CMT_LOGO
    context["FUDMA_LOGO"] = FUDMA_LOGO
    template  = get_template(template_path)
    html      = template.render(context)
    result    = BytesIO()
    pdf       = pisa.pisaDocument(BytesIO(html.encode("UTF-8")), result)
    if not pdf.err:
        return HttpResponse(result.getvalue(), content_type="application/pdf")
    return HttpResponse("PDF generation error", status=500)

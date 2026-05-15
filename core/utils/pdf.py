import os
from django.template.loader import render_to_string
from django.conf import settings
from weasyprint import HTML, CSS
from weasyprint.text.fonts import FontConfiguration


def generate_pdf(template_name: str, context: dict) -> bytes:
    font_config = FontConfiguration()
    html_string = render_to_string(template_name, context)

    base_url = f"file://{settings.BASE_DIR}/"

    pdf_bytes = HTML(
        string=html_string,
        base_url=base_url
    ).write_pdf(
        font_config=font_config
    )
    return pdf_bytes

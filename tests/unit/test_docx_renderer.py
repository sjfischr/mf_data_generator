from docx import Document

from lambdas.shared.docx_renderer import markdown_to_docx


def test_markdown_to_docx():
    markdown = """# Heading

**Bold paragraph**

- Bullet one
- Bullet two

| Item | Value |
|---|---|
| Units | 200 |

"""
    data = markdown_to_docx(
        markdown,
        property_name="Test Property",
        lender_name="NorthBridge",
        title="Lender Narrative",
    )

    from io import BytesIO

    doc = Document(BytesIO(data))
    headings = [p.text for p in doc.paragraphs if p.style.name.startswith("Heading")]
    assert "Heading" in headings
    assert "Bold paragraph" in [p.text for p in doc.paragraphs]
    assert len(doc.tables) == 1
    assert doc.tables[0].cell(1, 0).text == "Units"

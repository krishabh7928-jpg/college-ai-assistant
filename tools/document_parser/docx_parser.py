from docx import Document


def extract_docx_text(file_path):
	document = Document(file_path)

	text = []

	for paragraph in document.paragraphs:
		if paragraph.text.strip():
			text.append(paragraph.text)

	return "\n".join(text)

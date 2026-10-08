import pymupdf


def extract_pdf_text(file_path):
	try:
		with pymupdf.open(file_path) as document:
			text_parts = []

			for page in document:
				page_text = page.get_text("text").strip()
				if page_text:
					text_parts.append(page_text)

		return "\n\n".join(text_parts)

	except Exception as error:
		print(f"PDF extraction error: {error}")
		return ""

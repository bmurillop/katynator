"""Tests for email_parser — no DB, no filesystem (everything in memory)."""
import textwrap
from datetime import timezone

from app.pipeline.email_parser import parse_raw_email

_PLAIN_EMAIL = textwrap.dedent("""\
    From: banco@example.com
    To: finance@family.local
    Subject: Estado de cuenta Abril 2026
    Date: Thu, 17 Apr 2026 08:00:00 -0600
    MIME-Version: 1.0
    Content-Type: text/plain; charset=utf-8

    Estimado cliente, adjuntamos su estado de cuenta.
    Saldo actual: $415.40
""").encode()

_HTML_EMAIL = textwrap.dedent("""\
    From: banco@example.com
    To: finance@family.local
    Subject: Resumen mensual
    Date: Thu, 17 Apr 2026 08:00:00 -0600
    MIME-Version: 1.0
    Content-Type: text/html; charset=utf-8

    <html><body>
    <p>Estimado cliente,</p>
    <p>Su saldo es <strong>$415.40</strong></p>
    </body></html>
""").encode()

_MULTIPART_WITH_PDF = (
    b"From: banco@example.com\r\n"
    b"To: finance@family.local\r\n"
    b"Subject: Estado de cuenta\r\n"
    b"Date: Thu, 17 Apr 2026 08:00:00 -0600\r\n"
    b"MIME-Version: 1.0\r\n"
    b"Content-Type: multipart/mixed; boundary=\"boundary42\"\r\n"
    b"\r\n"
    b"--boundary42\r\n"
    b"Content-Type: text/plain; charset=utf-8\r\n"
    b"\r\n"
    b"Por favor revise el adjunto.\r\n"
    b"\r\n"
    b"--boundary42\r\n"
    b"Content-Type: application/pdf\r\n"
    b"Content-Disposition: attachment; filename=\"estado_cuenta.pdf\"\r\n"
    b"Content-Transfer-Encoding: base64\r\n"
    b"\r\n"
    b"JVBERi0xLjQ="  # minimal PDF-like base64 (not a valid PDF, just bytes)
    b"\r\n"
    b"--boundary42--\r\n"
)


class TestPlainTextEmail:
    def test_subject_extracted(self):
        parsed = parse_raw_email(_PLAIN_EMAIL)
        assert "Abril 2026" in parsed.subject

    def test_sender_extracted(self):
        parsed = parse_raw_email(_PLAIN_EMAIL)
        assert "banco@example.com" in parsed.sender

    def test_body_text_extracted(self):
        parsed = parse_raw_email(_PLAIN_EMAIL)
        assert len(parsed.body_texts) == 1
        assert "estado de cuenta" in parsed.body_texts[0].lower()

    def test_no_pdf_attachments(self):
        parsed = parse_raw_email(_PLAIN_EMAIL)
        assert parsed.pdf_attachments == []

    def test_received_at_parsed(self):
        parsed = parse_raw_email(_PLAIN_EMAIL)
        assert parsed.received_at.year == 2026
        assert parsed.received_at.month == 4


class TestHtmlEmail:
    def test_html_converted_to_text(self):
        parsed = parse_raw_email(_HTML_EMAIL)
        assert len(parsed.body_texts) == 1
        text = parsed.body_texts[0]
        # HTML tags stripped
        assert "<p>" not in text
        assert "<strong>" not in text
        # Content preserved
        assert "415.40" in text

    def test_no_pdf_attachments(self):
        parsed = parse_raw_email(_HTML_EMAIL)
        assert parsed.pdf_attachments == []


class TestMultipartWithPdf:
    def test_body_text_extracted(self):
        parsed = parse_raw_email(_MULTIPART_WITH_PDF)
        assert len(parsed.body_texts) >= 1
        assert "adjunto" in parsed.body_texts[0].lower()

    def test_pdf_attachment_found(self):
        parsed = parse_raw_email(_MULTIPART_WITH_PDF)
        assert len(parsed.pdf_attachments) == 1

    def test_pdf_filename_preserved(self):
        parsed = parse_raw_email(_MULTIPART_WITH_PDF)
        filename, _ = parsed.pdf_attachments[0]
        assert filename == "estado_cuenta.pdf"

    def test_pdf_bytes_non_empty(self):
        parsed = parse_raw_email(_MULTIPART_WITH_PDF)
        _, pdf_bytes = parsed.pdf_attachments[0]
        assert len(pdf_bytes) > 0


class TestEdgeCases:
    def test_missing_date_uses_now(self):
        raw = b"From: a@b.com\r\nSubject: X\r\n\r\nBody"
        parsed = parse_raw_email(raw)
        assert parsed.received_at is not None

    def test_empty_body_produces_no_texts(self):
        raw = b"From: a@b.com\r\nSubject: X\r\nContent-Type: text/plain\r\n\r\n"
        parsed = parse_raw_email(raw)
        # Empty payload → filtered out
        assert all(t.strip() for t in parsed.body_texts)

import os
import unittest
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from threading import Barrier
from unittest.mock import Mock, patch
from zipfile import ZIP_DEFLATED, ZipFile

import numpy as np
from docx import Document
from fastapi.testclient import TestClient

with patch.dict(os.environ, {'OPENAI_API_KEY': ''}), patch('dotenv.load_dotenv'):
    from app import main

from app.utils import io


def pdf_bytes(text):
    """Build a one-page PDF with an accurate cross-reference table."""
    stream = f'BT /F1 12 Tf 20 50 Td ({text}) Tj ET'.encode('ascii')
    objects = (
        b'<< /Type /Catalog /Pages 2 0 R >>',
        b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
        b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 200 100] '
        b'/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>',
        b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',
        b'<< /Length %d >>\nstream\n%s\nendstream' % (len(stream), stream),
    )
    pdf = BytesIO(b'%PDF-1.4\n')
    pdf.seek(0, 2)
    offsets = []
    for number, body in enumerate(objects, start=1):
        offsets.append(pdf.tell())
        pdf.write(b'%d 0 obj\n%s\nendobj\n' % (number, body))
    xref = pdf.tell()
    pdf.write(b'xref\n0 %d\n0000000000 65535 f \n' % (len(objects) + 1))
    for offset in offsets:
        pdf.write(b'%010d 00000 n \n' % offset)
    pdf.write(b'trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n' % (len(objects) + 1, xref))
    return pdf.getvalue()


def docx_bytes(text):
    document = Document()
    document.add_paragraph(text)
    stream = BytesIO()
    document.save(stream)
    return stream.getvalue()


class UploadTests(unittest.TestCase):
    def setUp(self):
        self.adapter = Mock(spec=main.LLMAdapter)
        self.adapter.get_embeddings.side_effect = lambda texts: np.ones((len(texts), 2))
        self.adapter.search_similar.return_value = (np.array([[0]]), np.array([[1.0]]))
        self.adapter.analyze_clause_similarity.return_value = {'similarity_score': 80}
        self.adapter.assess_contract_risk.side_effect = self.assess_risk
        self.enterContext(patch.object(main, 'llm_adapter', self.adapter))
        self.enterContext(patch.object(main, 'llm_risk_agent', main.LLMRiskAgent(self.adapter)))
        self.enterContext(patch.object(main, 'llm_available', True))
        self.enterContext(patch.object(main, 'TEMPLATES', {
            'master_service_agreement': {'clauses': [('clause_001:Payment', 'Pay within 30 days.')]},
        }))
        self.enterContext(patch.object(main, 'template_index', None))
        self.client = self.enterContext(TestClient(main.app))

    @staticmethod
    def assess_risk(contract_text, template_clauses, matched_clauses):
        # Echo both inputs so the test checks the matched text and the full contract.
        return {
            'overall_risk_score': 30,
            'risk_band': 'LOW',
            'global_risks': [contract_text.strip(), matched_clauses[0]['body'].strip()],
        }

    def upload(self, filename, content):
        return self.client.post('/analyze', files={'file': (filename, content, 'application/octet-stream')})

    def test_sample_contract_runs_the_analysis_with_a_cold_index(self):
        with open('data/contracts/sample_contract_acme.md', 'rb') as sample:
            response = self.upload('sample_contract_acme.md', sample.read())
        self.assertEqual(response.status_code, 200, response.text)
        result = response.json()
        self.assertTrue(result['llm_analysis'])
        self.assertEqual(result['overall_risk'], 30)
        self.assertEqual(result['template_name'], 'master_service_agreement')
        self.assertEqual(result['clause_results'], [])
        self.assertGreaterEqual(self.adapter.get_embeddings.call_count, 3)

    def test_invalid_uploads_never_call_the_model_on_a_cold_index(self):
        cases = (
            ('contract.doc', b'Text.', 415),
            ('contract.pdf', b'not a pdf', 422),
            ('contract.pdf', b'%PDF-1.4\nnot a PDF object\n%%EOF\n', 422),
            ('contract.pdf', pdf_bytes(''), 422),
            ('contract.docx', b'PK\x03\x04not a valid archive', 422),
            ('contract.docx', docx_bytes(''), 422),
            ('contract.txt', b'\xff\xfe', 422),
            ('contract.md', b'  \n  ', 422),
            ('contract.txt', b'a' * (io.MAX_UPLOAD_BYTES + 1), 413),
        )
        for filename, content, status in cases:
            with self.subTest(filename=filename, status=status):
                response = self.upload(filename, content)
                self.assertEqual(response.status_code, status, response.text)
                self.assertIn('error', response.json())
        self.assertEqual(self.adapter.mock_calls, [])

    def test_docx_expansion_limit_applies_before_parsing_or_model_calls(self):
        content = BytesIO()
        with ZipFile(content, 'w', compression=ZIP_DEFLATED) as archive:
            archive.writestr('word/document.xml', b'a' * 2_048)
        with patch.object(io, 'MAX_DOCX_EXPANDED_BYTES', 1_024), patch.object(io, 'Document') as parser:
            response = self.upload('contract.docx', content.getvalue())
        self.assertEqual(response.status_code, 413, response.text)
        parser.assert_not_called()
        self.assertEqual(self.adapter.mock_calls, [])

    def test_concurrent_pdf_and_docx_requests_keep_their_own_text(self):
        cases = [
            ('contract.PDF', pdf_bytes, 'The buyer pays invoice alpha.'),
            ('contract.PDF', pdf_bytes, 'The buyer pays invoice bravo.'),
            ('contract.DOCX', docx_bytes, 'The buyer pays invoice charlie.'),
            ('contract.DOCX', docx_bytes, 'The buyer pays invoice delta.'),
        ]
        uploads = [(filename, build(contract_text)) for filename, build, contract_text in cases]

        def overlap_parser(parser):
            barrier = Barrier(2, timeout=5)

            def parse(source):
                barrier.wait()
                return parser(source)

            return parse

        with patch.object(io, 'pdf_extract_text', overlap_parser(io.pdf_extract_text)), \
                patch.object(io, '_docx_text', overlap_parser(io._docx_text)), \
                ThreadPoolExecutor(max_workers=len(uploads)) as executor:
            responses = list(executor.map(lambda upload: self.upload(*upload), uploads))
        for (_, _, contract_text), response in zip(cases, responses):
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json()['global_flags'], [contract_text, contract_text])


if __name__ == '__main__':
    unittest.main()

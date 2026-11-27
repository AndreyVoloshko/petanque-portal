from datetime import date
from unittest.mock import patch

from django.test import SimpleTestCase
from django.urls import reverse

from federation.models.document import Document, DocumentCategory


class DocumentsPresentationTests(SimpleTestCase):
    @patch('federation.views.documents.Document.objects.filter')
    @patch('federation.views.documents.DocumentCategory.objects.filter')
    def test_documents_load_their_own_assets_and_use_the_download_route(self, categories, documents):
        category = DocumentCategory(pk=1, code='rules', name='Rules')
        document = Document(
            pk=1, category=category, name='Tournament rules', document_date=date(2026, 2, 4),
            file='documents/tournament-rules.pdf', download_count=3,
        )
        categories.return_value.order_by.return_value = [category]
        documents.return_value.select_related.return_value = [document]
        self.client.cookies['gdpr_agree'] = '1'

        response = self.client.get(reverse('documents'))
        self.assertContains(response, '/vite/assets/documents-', count=1)
        self.assertContains(response, 'defer src="/static/documents.js?v=', count=1)
        self.assertNotContains(response, 'style-v2.css')
        self.assertNotContains(response, '/vite/assets/tournament-badges-')
        self.assertContains(response, 'id="documentsCategory"', count=1)
        self.assertNotContains(response, 'jquery.min.js')
        self.assertNotContains(response, 'portal-ui.js')
        self.assertNotContains(response, 'facebook-jssdk')
        self.assertContains(response, 'data-category="rules"')
        self.assertContains(response, '<time datetime="2026-02-04">', count=1)
        self.assertContains(response, f'href="{reverse("document_download", args=[document.pk])}"', count=2)

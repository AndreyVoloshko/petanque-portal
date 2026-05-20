from django.shortcuts import render
from django.utils.translation import gettext_lazy as _
from federation.models.document import Document, DocumentCategory


def documents(request):

    documents_objects = []

    categories = DocumentCategory.objects.filter(is_active=True).order_by('order', 'name')

    for category in categories:
        documents = Document.objects.filter(category=category, is_active=True)

        if documents:
            documents_objects.append({
                'category_name': category.name,
                'category_id': category.code,
                'documents': documents
            })

    return render(request, 'documents/documents.html', {
        'documents': documents_objects,
        'page_title': _("Documents"),
    })

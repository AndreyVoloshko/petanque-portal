from django.db.models import F
from django.shortcuts import render, get_object_or_404, redirect
from django.utils.translation import gettext_lazy as _

from federation.models.document import Document, DocumentCategory


def documents(request):
    categories = DocumentCategory.objects.filter(is_active=True).order_by('order', 'name')
    all_documents = Document.objects.filter(is_active=True).select_related('category')

    documents_by_category = []
    total_count = 0
    for category in categories:
        cat_docs = [d for d in all_documents if d.category_id == category.id]
        if cat_docs:
            documents_by_category.append({
                'category_name': category.name,
                'category_id': category.code,
                'documents': cat_docs,
                'count': len(cat_docs),
            })
            total_count += len(cat_docs)

    popular_documents = sorted(all_documents, key=lambda d: d.download_count, reverse=True)[:5]

    return render(request, 'documents/documents.html', {
        'documents': documents_by_category,
        'all_documents': list(all_documents),
        'popular_documents': popular_documents,
        'total_count': total_count,
        'page_title': _("Documents"),
    })


def document_download(request, pk):
    document = get_object_or_404(Document, pk=pk, is_active=True)
    Document.objects.filter(pk=pk).update(download_count=F('download_count') + 1)
    return redirect(document.file.url)

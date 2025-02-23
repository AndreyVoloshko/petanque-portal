from django.shortcuts import render
from federation.models.document import Document


def documents(request):

    documents_objects = []

    for category in Document.CATEGORIES:
        documents = Document.objects.filter(category=category[0], is_active=True)

        if documents:
            documents_objects.append({
                'category_name': category[1],
                'category_id': category[0],
                'documents': documents
            })

    return render(request, 'documents/documents.html', {
        'documents': documents_objects,
        'page_title': "Документи",
    })
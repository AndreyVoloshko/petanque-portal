from django.apps import apps


def get_model(model_name):
    return apps.get_model('federation', model_name)
from django.shortcuts import render


def inicio(request):

    return render(request, 'tienda/index.html')


def login_usuario(request):
    return render(request, 'tienda/login.html')

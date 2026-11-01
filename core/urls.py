from django.contrib import admin
from django.urls import path
from tienda import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.inicio, name='inicio'),
    path('producto/<int:producto_id>/',
         views.detalle_producto, name='detalle_producto'),
    path('login/', views.login_view, name='login'),
    path('registro/', views.registro_view, name='registro'),
    path('logout/', views.logout_view, name='logout'),
    path('carrito/', views.ver_carrito, name='ver_carrito'),
    path('carrito/agregar/<int:producto_id>/',
         views.agregar_al_carrito, name='agregar_al_carrito'),
    path('carrito/actualizar/<int:producto_id>/',
         views.actualizar_carrito, name='actualizar_carrito'),
    path('carrito/eliminar/<int:producto_id>/',
         views.eliminar_del_carrito, name='eliminar_del_carrito'),
    path('carrito/vaciar/', views.vaciar_carrito, name='vaciar_carrito'),
    path('factura/', views.generar_factura, name='generar_factura'),
    path('factura/<str:numero_factura>/',
         views.ver_factura_guardada, name='ver_factura_guardada'),
    path('panel/', views.panel_view, name='panel'),
    path('panel/producto/guardar/',
         views.guardar_producto, name='guardar_producto'),
    path('panel/categoria/agregar/',
         views.agregar_categoria, name='agregar_categoria'),
    path('panel/pedido/estado/<str:numero_factura>/',
         views.cambiar_estado_pedido, name='cambiar_estado_pedido'),
    path('panel/usuario/guardar/', views.guardar_usuario, name='guardar_usuario'),
]

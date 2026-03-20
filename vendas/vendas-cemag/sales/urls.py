from django.urls import path

from . import views

urlpatterns = [
    # Core
    path("", views.home, name="home"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("quotes/create/", views.create_quote, name="create-quote"),
    path("quotes/consult/", views.consult_price, name="consult-price"),
    path("api/programacao/prazo-entrega/", views.prazo_entrega, name="prazo-entrega"),
    path("api/vendors/", views.vendors, name="vendors-list"),
    path("api/vendors/sync/", views.sync, name="vendors-sync"),
    
    # Carrinho de compras
    path("api/cart/add/", views.add_to_cart, name="cart-add"),
    path("api/cart/list/", views.list_cart, name="cart-list"),
    path("api/cart/update/<int:item_id>/", views.update_cart_item, name="cart-update"),
    path("api/cart/delete/<int:item_id>/", views.delete_cart_item, name="cart-delete"),
    path("api/cart/clear/", views.clear_cart, name="cart-clear"),
    
    # Favoritos
    path("api/favorites/list/", views.list_favorites, name="favorites-list"),
    path("api/favorites/add/", views.add_favorite, name="favorites-add"),
    path("api/favorites/delete/", views.delete_favorite, name="favorites-delete"),
    
    # Ploomes 
    path("api/ploomes/quotes/", views.ploomes_quotes, name="ploomes-quotes"),
    path("api/ploomes/contacts-search/", views.ploomes_contacts_search, name="ploomes-contacts-search"),
    path("api/ploomes/contacts-company/", views.ploomes_contacts_company, name="ploomes-contacts-company"),
    path("api/ploomes/payment-options/", views.ploomes_payment_options, name="ploomes-payment-options"),
    path("api/ploomes/payment-id/", views.ploomes_payment_id, name="ploomes-payment-id"),
    path("api/ploomes/color-id/", views.ploomes_color_id, name="ploomes-color-id"),
    path("api/ploomes/product-id/", views.ploomes_product_id, name="ploomes-product-id"),
    path("api/ploomes/deals/update-contact/", views.ploomes_update_deal_contact, name="ploomes-update-deal-contact"),
    path("api/ploomes/deals/win/", views.ploomes_win_deal, name="ploomes-win-deal"),
    path("api/ploomes/deals/lose/", views.ploomes_lose_deal, name="ploomes-lose-deal"),
    path("api/ploomes/deals/loss-reasons/", views.ploomes_loss_reasons, name="ploomes-loss-reasons"),
    path("api/ploomes/orders/mirror/", views.ploomes_order_mirror, name="ploomes-order-mirror"),
    path("api/ploomes/sales/create/", views.ploomes_create_sale, name="ploomes-create-sale"),
    path("api/ploomes/quote-detail/", views.ploomes_quote_detail, name="ploomes-quote-detail"),
    path("api/ploomes/quote-info/", views.ploomes_quote_info, name="ploomes-quote-info"),
    path("api/ploomes/quotes/<int:quote_id>/review/", views.ploomes_quote_review, name="ploomes-quote-review"),
    path("api/ploomes/cities/validate/", views.ploomes_validate_city, name="ploomes-validate-city"),
    path("api/ploomes/cities/search/", views.ploomes_cities_search, name="ploomes-cities-search"),
    path("api/ploomes/companies/search/", views.ploomes_companies_search, name="ploomes-companies-search"),
    path("api/ploomes/companies/create/", views.ploomes_create_company, name="ploomes-create-company"),
    path("api/ploomes/contacts/create/", views.ploomes_create_contact, name="ploomes-create-contact"),
    path("api/ploomes/users/", views.ploomes_users, name="ploomes-users"),
    path("api/ploomes/users-debug/", views.ploomes_users_debug, name="ploomes-users-debug"),
    path("api/ploomes/contact-price-list/", views.ploomes_contact_price_list, name="ploomes-contact-price-list"),
    path("manage-users/", views.ploomes_manage_users, name="manage-users"),
    path("api/ploomes/create-user-access/", views.ploomes_create_user_access, name="create-user-access"),
    path("api/ploomes/update-user-access/", views.ploomes_update_user_access, name="update-user-access"),
    path("api/family-photo/", views.family_photo, name="family-photo"),
    path("api/product-photo/", views.family_photo, name="product-photo"),  # alias
    path("api/ploomes/quotes/create/", views.ploomes_create_quote, name="ploomes-create-quote"),
    path("api/ploomes/deals/create/", views.ploomes_create_deal, name="ploomes-create-deal"),

    # Preços e produtos
    path("json/produtos/", views.json_produtos_innovaro, name="json_produtos_innovaro"),
    path("json/precos/", views.json_precos_produto, name="json_precos_produto"),

]

from pathlib import Path

from django import forms
from django.conf import settings
from django.contrib import admin, messages
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import redirect, render
from django.urls import reverse
from PIL import Image

from .models import CartItem, FavoriteItem, PortalUser, Vendor, FamilyPhoto, GrupoPrazo, PriceList


@admin.register(Vendor)
class VendorAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "region", "email", "is_active")
    search_fields = ("code", "name", "region", "email")
    list_filter = ("is_active", "region")


@admin.register(PortalUser)
class PortalUserAdmin(admin.ModelAdmin):
    list_display = ("login", "name", "owner_id", "price_list", "price_lists_display", "created_at")
    search_fields = ("login", "name", "owner_id", "price_list", "price_lists__name")
    list_filter = ("price_list", "price_lists")

    @admin.display(description="Listas de Preco")
    def price_lists_display(self, obj):
        return ", ".join(obj.price_lists.values_list("name", flat=True))


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ("owner_id", "product_code", "list_name", "price", "final_price", "quantity", "created_at")
    search_fields = ("product_code", "description", "owner_id", "list_name")


@admin.register(FavoriteItem)
class FavoriteItemAdmin(admin.ModelAdmin):
    list_display = ("owner_id", "product_code", "list_code", "created_at")
    search_fields = ("owner_id", "product_code", "list_code", "description")


@admin.register(FamilyPhoto)
class FamilyPhotoAdmin(admin.ModelAdmin):
    list_display = ("family", "product", "uploaded_at")
    search_fields = ("family", "product")


@admin.register(GrupoPrazo)
class GrupoPrazoAdmin(admin.ModelAdmin):
    list_display = ("grupo_code", "grupo_desc", "modified_at")
    search_fields = ("grupo_code", "grupo_desc")


@admin.register(PriceList)
class PriceListAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)


class StaticImageUploadForm(forms.Form):
    IMAGE_CHOICES = [
        ("categoria", "Categoria"),
        ("produto", "Produto"),
    ]

    image_type = forms.ChoiceField(
        label="Destino da imagem",
        choices=IMAGE_CHOICES,
        widget=forms.RadioSelect,
    )
    image_file = forms.ImageField(
        label="Arquivo da imagem",
        help_text=(
            "O nome do arquivo deve ser exatamente o c\u00f3digo do produto (ex.: CBH5) "
            "ou o nome da categoria (ex.: Graneleira). Formatos aceitos: JPG, JPEG, PNG ou WEBP. "
            "A imagem ser\u00e1 salva com extens\u00e3o .jpg automaticamente."
        ),
    )

    def clean_image_file(self):
        file = self.cleaned_data["image_file"]
        filename = Path(file.name).name  # evita caminhos arbitr\u00e1rios
        allowed_ext = {".jpg", ".jpeg", ".png", ".webp"}

        if Path(filename).suffix.lower() not in allowed_ext:
            raise forms.ValidationError("Use imagens JPG, JPEG, PNG ou WEBP.")

        file.name = filename
        return file


@staff_member_required
def upload_static_image(request):
    replaced = False

    if request.method == "POST":
        form = StaticImageUploadForm(request.POST, request.FILES)

        if form.is_valid():
            image_type = form.cleaned_data["image_type"]
            image_file = form.cleaned_data["image_file"]
            filename = Path(image_file.name).name
            stem = Path(filename).stem
            target_filename = f"{stem}.jpg"

            target_dir = settings.BASE_DIR / "static" / "img" / image_type
            target_dir.mkdir(parents=True, exist_ok=True)

            target_path = target_dir / target_filename
            replaced = target_path.exists()

            image_file.seek(0)
            image = Image.open(image_file)
            if image.mode in ("RGBA", "LA", "P"):
                image = image.convert("RGB")
            image.save(target_path, format="JPEG", quality=90)

            action = "substitu\u00edda" if replaced else "adicionada"
            messages.success(
                request,
                f"Imagem {target_filename} {action} em static/img/{image_type}.",
            )
            return redirect(reverse("upload-static-image"))
    else:
        form = StaticImageUploadForm()

    context = {
        **admin.site.each_context(request),
        "title": "Upload de imagens est\u00e1ticas",
        "form": form,
    }

    return render(request, "admin/static_image_upload.html", context)

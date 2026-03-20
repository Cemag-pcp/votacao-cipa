from django.db import models
from django.contrib.auth.hashers import is_password_usable, make_password


class Vendor(models.Model):
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=255)
    email = models.EmailField(blank=True)
    region = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=50, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.code} - {self.name}"


class PortalUser(models.Model):
    login = models.CharField(max_length=150, unique=True, null=True, blank=True)
    owner_id = models.PositiveIntegerField(unique=True)
    name = models.CharField(max_length=150)
    price_list = models.CharField(max_length=100, null=True, blank=True)
    price_lists = models.ManyToManyField("PriceList", blank=True)
    password = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Usuário do Portal"
        verbose_name_plural = "Usuários do Portal"

    def __str__(self):
        return f"{self.login} - {self.name} (OwnerId: {self.owner_id})"

    def save(self, *args, **kwargs):
        if self.password and not is_password_usable(self.password):
            self.password = make_password(self.password)
        elif self.password and not self.password.startswith("pbkdf2_"):
            self.password = make_password(self.password)
        super().save(*args, **kwargs)


class PriceList(models.Model):
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Lista de Preco"
        verbose_name_plural = "Listas de Preco"

    def __str__(self):
        return self.name


class CartItem(models.Model):
    owner_id = models.PositiveIntegerField()
    product_code = models.CharField(max_length=100)
    description = models.TextField()
    list_name = models.CharField(max_length=150, blank=True)
    color = models.CharField(max_length=50, blank=True)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    final_price = models.DecimalField(max_digits=12, decimal_places=2)
    favorite = models.BooleanField(default=False)
    quantity = models.PositiveIntegerField(default=1)
    observacao = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.product_code} - {self.description}"


class FavoriteItem(models.Model):
    owner_id = models.PositiveIntegerField()
    product_code = models.CharField(max_length=100)
    list_code = models.CharField(max_length=150, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("owner_id", "product_code", "list_code")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.product_code} ({self.list_code})"


class FamilyPhoto(models.Model):
    family = models.CharField(max_length=150, db_index=True)  # ex: FTC4300R
    product = models.CharField(max_length=255, blank=True)
    image = models.ImageField(upload_to="product_photos/")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self):
        label = self.product or "foto"
        return f"{self.family} - {label}"


class GrupoPrazo(models.Model):

    grupo_code = models.CharField(max_length=100, db_index=True, unique=True)
    grupo_desc = models.CharField(max_length=100, db_index=True)
    prazo = models.IntegerField()
    modified_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.grupo_code


class ProdutoInnovaro(models.Model):
    """
    Model para armazenar produtos da API Innovaro
    """
    codigo = models.CharField(max_length=100, unique=True, db_index=True, verbose_name="Código")
    chave = models.PositiveIntegerField(unique=True, db_index=True, verbose_name="Chave")
    nome = models.TextField(verbose_name="Nome")
    modelo = models.CharField(max_length=100, blank=True, db_index=True, verbose_name="Modelo")
    classe = models.CharField(max_length=150, blank=True, db_index=True, verbose_name="Classe")
    desc_generica = models.CharField(max_length=150, blank=True, verbose_name="Descrição Genérica")
    modelo_simples = models.CharField(max_length=100, blank=True, verbose_name="Modelo Simples")

    # Características técnicas
    tamanho = models.CharField(max_length=50, blank=True, verbose_name="Tamanho")
    capacidade = models.CharField(max_length=50, blank=True, verbose_name="Capacidade")
    rodado = models.CharField(max_length=50, blank=True, verbose_name="Rodado")
    mola_freio = models.CharField(max_length=50, blank=True, verbose_name="Mola/Freio")
    mola = models.CharField(max_length=10, blank=True, verbose_name="Mola", choices=[("C", "Com mola"), ("S", "Sem mola")])
    freio = models.CharField(max_length=10, blank=True, verbose_name="Freio", choices=[("C", "Com freio"), ("S", "Sem freio")])
    eixo = models.CharField(max_length=50, blank=True, verbose_name="Eixo")
    pneu = models.CharField(max_length=50, blank=True, verbose_name="Pneu")
    cor = models.CharField(max_length=50, blank=True, verbose_name="Cor")
    funcionalidade = models.CharField(max_length=150, blank=True, verbose_name="Funcionalidade")
    observacao = models.TextField(blank=True, verbose_name="Observação")
    
    # Flags
    crm = models.BooleanField(default=False, db_index=True, verbose_name="CRM")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Atualizado em")

    class Meta:
        ordering = ["codigo"]
        verbose_name = "Produto Innovaro"
        verbose_name_plural = "Produtos Innovaro"
        indexes = [
            models.Index(fields=["codigo", "crm"]),
            models.Index(fields=["modelo", "crm"]),
        ]

    def __str__(self):
        return f"{self.codigo} - {self.nome}"


class PrecoProduto(models.Model):
    """
    Model para armazenar preços de produtos da API Innovaro
    """
    # Informações da tabela de preço
    tabela_codigo = models.CharField(max_length=100, db_index=True, verbose_name="Código da Tabela")
    tabela_nome = models.CharField(max_length=255, verbose_name="Nome da Tabela")
    
    # Informações do produto
    produto = models.CharField(max_length=255, db_index=True, verbose_name="Produto")
    valor = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Valor")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Atualizado em")

    class Meta:
        ordering = ["tabela_nome", "produto"]
        verbose_name = "Preço de Produto"
        verbose_name_plural = "Preços de Produtos"
        unique_together = [("tabela_codigo", "produto")]
        indexes = [
            models.Index(fields=["tabela_codigo", "produto"]),
            models.Index(fields=["produto"]),
            models.Index(fields=["tabela_codigo"]),
        ]

    def __str__(self):
        return f"{self.produto} - {self.tabela_nome}: R$ {self.valor}"


class Cores(models.Model):

    cor_id = models.PositiveIntegerField(unique=True, db_index=True, verbose_name="ID da Cor")
    descricao = models.CharField(max_length=100, verbose_name="Descrição da Cor")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Atualizado em")

    def __str__(self):
        return f"{self.descricao} (ID: {self.cor_id})"


class FormaPagamento(models.Model):

    table_id = models.PositiveIntegerField(db_index=True, verbose_name="TableId (Ploomes)")
    pagamento_id = models.PositiveIntegerField(db_index=True, verbose_name="ID da Forma de Pagamento")
    descricao = models.CharField(max_length=150, verbose_name="Descrição")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Atualizado em")

    class Meta:
        verbose_name = "Forma de Pagamento"
        verbose_name_plural = "Formas de Pagamento"
        unique_together = ("table_id", "pagamento_id")
        ordering = ["descricao"]
        indexes = [
            models.Index(fields=["table_id", "pagamento_id"]),
        ]

    def __str__(self):
        return f"{self.descricao} (TableId: {self.table_id} | ID: {self.pagamento_id})"

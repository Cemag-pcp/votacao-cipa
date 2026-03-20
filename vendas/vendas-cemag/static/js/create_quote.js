(() => {
  const form = document.getElementById("quoteForm");
  const alertBox = document.getElementById("alertArea");
  const alertCart = document.getElementById("alertCart");
  const submitBtn = document.getElementById("submitQuote");
  const spinner = document.getElementById("spinnerSubmit");
  const revendaInput = document.getElementById("revendaNome");
  const revendaDropdown = document.getElementById("revendaNomeDropdown");
  const revendaList = document.getElementById("revendaOptions");
  const revendaIdHidden = document.getElementById("revendaId");
  const ufIdHidden = document.getElementById("ufId");
  const contatoInput = document.getElementById("revendaContato");
  const contatoDropdown = document.getElementById("revendaContatoDropdown");
  const contatoIdHidden = document.getElementById("revendaContatoId");
  const paymentSelect = document.getElementById("paymentSelect");
  const paymentIdHidden = document.getElementById("formaPagamentoId"); // TableId 32062
  const paymentIdTipo2Hidden = document.getElementById("formaPagamentoIdTipo2"); // TableId 31965
  
  const colorIdMap = new Map();
  const colorNameById = new Map();
  const urlParams = new URLSearchParams(window.location.search);
  const isRevision = urlParams.get("revision") === "1";
  const isConsultMode = typeof window.isConsultMode !== 'undefined' ? window.isConsultMode : false;
  const revisionQuoteId = urlParams.get("quoteId") || null;
  let revisionDealId = null;
  let revisionPersonId = null;

  const defaultColors = ["Laranja", "Verde", "Vermelha", "Amarela", "Azul"];
  const loadingOverlay = document.getElementById("loadingOverlay");
  const formSection = document.getElementById("formSection");
  const catalogSection = document.getElementById("catalogSection");

  // Helper para obter owner_id
  function getOwnerId() {
    return form?.owner_id?.value || document.querySelector('[name="owner_id"]')?.value || null;
  }

  let allowedPriceListsOverride = null;

  function setAllowedPriceLists(list) {
    allowedPriceListsOverride = Array.isArray(list) && list.length ? list : null;
  }

  // Helper para obter listas permitidas
  function getAllowedPriceLists() {
    if (allowedPriceListsOverride && allowedPriceListsOverride.length) {
      return allowedPriceListsOverride.slice();
    }
    const raw =
      form?.dataset?.priceLists ||
      document.querySelector("[data-price-lists]")?.dataset?.priceLists ||
      "";
    if (!raw) return [];
    return raw
      .split("||")
      .map((item) => item.trim())
      .filter(Boolean);
  }

  function getProfileId() {
    const raw = form?.dataset?.profileId || document.querySelector("[data-profile-id]")?.dataset?.profileId || "";
    const parsed = Number(raw);
    return Number.isFinite(parsed) ? parsed : null;
  }

  // Helper para obter price list preferida
  function getPriceList() {
    const preferred =
      form?.dataset?.priceList || document.querySelector("[data-price-list]")?.dataset?.priceList || null;
    if (preferred) return preferred;
    const allowed = getAllowedPriceLists();
    return allowed.length ? allowed[0] : null;
  }

  // Helper para obter valores de revenda (do form principal ou do confirm)
  function getRevendaValues() {
    return {
      nome: revendaInput?.value?.trim() || confirmRevendaInput?.value?.trim() || "",
      id: revendaIdHidden?.value || confirmRevendaIdHidden?.value || null,
      contatoId: contatoIdHidden?.value || confirmContatoIdHidden?.value || null,
      ufId: ufIdHidden?.value || confirmUfIdHidden?.value || null,
    };
  }
  const productSection = document.getElementById("productSection");
  const priceListFilter = document.getElementById("priceListFilter");
  const catalogGrid = document.getElementById("catalogGrid");
  const catalogEmpty = document.getElementById("catalogEmpty");
  const catalogSearch = document.getElementById("catalogSearch");
  const cartOverlay = document.getElementById("cartOverlay");
  const cartTableBody = document.getElementById("cartTableBody");
  const cartEmpty = document.getElementById("cartEmpty");
  const cartTotalValue = document.getElementById("cartTotalValue");
  const closeCart = document.getElementById("closeCart");
  const cartFloatingBtn = document.getElementById("cartFloatingBtn");
  const cartCountBadge = document.getElementById("cartCountBadge");
  const confirmOverlay = document.getElementById("confirmOverlay");
  const confirmTableBody = document.getElementById("confirmTableBody");
  const confirmCardsBody = document.getElementById("confirmCardsBody");
  const confirmSummary = document.getElementById("confirmSummary");
  const confirmNotes = document.getElementById("confirmNotes");
  const closeConfirm = document.getElementById("closeConfirm");
  const confirmCartBtn = document.getElementById("confirmCartBtn");
  const clearCartBtn = document.getElementById("clearCartBtn");
  const saveOrderBtn = document.getElementById("saveOrderBtn");
  const formaPagamentoId = document.getElementById("formaPagamentoId");
  const filters = {
    modeloSimples: document.getElementById("filtroModeloSimples"),
    categoria: document.getElementById("filtroCategoria"),
    modelo: document.getElementById("filtroModelo"),
    eixo: document.getElementById("filtroEixo"),
    mola: document.getElementById("filtroMola"),
    freio: document.getElementById("filtroFreio"),
    tamanho: document.getElementById("filtroTamanho"),
    rodado: document.getElementById("filtroRodado"),
    pneu: document.getElementById("filtroPneu"),
    opcionais: document.getElementById("filtroOpcionais"),
  };
  const categoriaCards = document.getElementById("categoriaCards");
  const modeloCards = document.getElementById("modeloCards");
  const modeloSimplesCards = document.getElementById("modeloSimplesCards");
  const btnVoltarButtons = Array.from(document.querySelectorAll(".btn-voltar-catalogo"));
  const etapaModeloSimples = document.getElementById("etapaModeloSimples");
  const etapaCategoria = document.getElementById("etapaCategoria");
  const etapaModelo = document.getElementById("etapaModelo");
  const etapaOutros = document.getElementById("etapaOutrosFiltros");
  const btnToggleFiltros = document.getElementById("btnToggleFiltros");
  const filtrosModal = document.getElementById("filtrosModal");
  const filtrosModalBody = document.getElementById("filtrosModalBody");

  const suggestionMap = new Map();
  const contactMap = new Map();
  let contactOptions = [];
  const productByCode = new Map();
  const productIdCache = new Map();
  let productsData = [];
  let catalogData = [];
  let mergedRows = [];
  let lastFormState = null;
  const favoritesCache = new Map();

  const baseOpcoes = [
    "À prazo - 1x",
    "À prazo - 2x",
    "À prazo - 3x",
    "À prazo - 4x",
    "À prazo - 5x",
    "À prazo - 6x",
    "À prazo - 7x",
    "À prazo - 8x",
    "À prazo - 9x",
    "À prazo - 10x",
    "À Vista",
    "Antecipado",
    "Cartao de Credito",
    "Personalizado",
  ];

  const placeholderImage =
    "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 400 240'><defs><linearGradient id='g' x1='0' y1='0' x2='1' y2='1'><stop offset='0%' stop-color='%23334457'/><stop offset='100%' stop-color='%23121a2b'/></linearGradient></defs><rect width='400' height='240' fill='url(%23g)'/><text x='200' y='125' text-anchor='middle' fill='%23cfd7e3' font-family='Arial, sans-serif' font-size='20'>Foto do produto</text></svg>";
  const placeholderCard =
    "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 400 200'><defs><linearGradient id='g' x1='0' y1='0' x2='1' y2='1'><stop offset='0%' stop-color='%232c3648'/><stop offset='100%' stop-color='%2310182a'/></linearGradient></defs><rect width='400' height='200' fill='url(%23g)'/><text x='200' y='110' text-anchor='middle' fill='%23d0dae6' font-family='Arial, sans-serif' font-size='20'>Selecione</text></svg>";

  const normalize = (text) =>
    (text || "")
      .toString()
      .normalize("NFD")
      .replace(/\p{Diacritic}/gu, "")
      .toLowerCase()
      .trim();

  function setRevendaDropdownVisible(isVisible) {
    if (!revendaDropdown) return;
    revendaDropdown.classList.toggle("d-none", !isVisible);
  }

  function renderRevendaDropdownMessage(message) {
    if (!revendaDropdown) return;
    revendaDropdown.innerHTML = "";
    const item = document.createElement("button");
    item.type = "button";
    item.className = "list-group-item list-group-item-action disabled";
    item.textContent = message;
    revendaDropdown.appendChild(item);
    setRevendaDropdownVisible(true);
  }

  function clearRevendaDropdown() {
    if (!revendaDropdown) return;
    revendaDropdown.innerHTML = "";
    setRevendaDropdownVisible(false);
  }

  function setContatoDropdownVisible(dropdownEl, isVisible) {
    if (!dropdownEl) return;
    dropdownEl.classList.toggle("d-none", !isVisible);
  }

  function renderContatoDropdownMessage(dropdownEl, message) {
    if (!dropdownEl) return;
    dropdownEl.innerHTML = "";
    const item = document.createElement("button");
    item.type = "button";
    item.className = "list-group-item list-group-item-action disabled";
    item.textContent = message;
    dropdownEl.appendChild(item);
    setContatoDropdownVisible(dropdownEl, true);
  }

  function clearContatoDropdown(dropdownEl) {
    if (!dropdownEl) return;
    dropdownEl.innerHTML = "";
    setContatoDropdownVisible(dropdownEl, false);
  }

  function renderContatoDropdownItems(dropdownEl, items, onSelect) {
    if (!dropdownEl) return;
    dropdownEl.innerHTML = "";

    if (!items || !items.length) {
      renderContatoDropdownMessage(dropdownEl, "Nenhum contato encontrado");
      return;
    }

    items.forEach((it) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "list-group-item list-group-item-action";
      btn.textContent = it.name || "";
      btn.dataset.id = it.id || "";
      btn.dataset.name = it.name || "";
      btn.addEventListener("mousedown", (ev) => {
        ev.preventDefault();
        onSelect({ name: btn.dataset.name || "", id: btn.dataset.id || "" });
      });
      dropdownEl.appendChild(btn);
    });

    setContatoDropdownVisible(dropdownEl, true);
  }

  function selectContato({ name, id }) {
    if (contatoInput) contatoInput.value = name || "";
    if (contatoIdHidden) contatoIdHidden.value = id ? String(id) : "";
    clearContatoDropdown(contatoDropdown);
  }

  function attachContatoDropdownBehavior(inputEl, dropdownEl, onSelect) {
    if (!inputEl || !dropdownEl) return;

    inputEl.addEventListener("input", () => {
      const term = (inputEl.value || "").trim();
      if (!contactOptions.length) {
        clearContatoDropdown(dropdownEl);
        return;
      }
      const normalizedTerm = normalize(term);
      const filtered = normalizedTerm
        ? contactOptions.filter((it) => normalize(it.name).includes(normalizedTerm))
        : contactOptions;
      renderContatoDropdownItems(dropdownEl, filtered, onSelect);
    });

    inputEl.addEventListener("focus", () => {
      if (!contactOptions.length) return;
      renderContatoDropdownItems(dropdownEl, contactOptions, onSelect);
    });

    inputEl.addEventListener("blur", () => {
      setTimeout(() => {
        clearContatoDropdown(dropdownEl);
      }, 150);
    });
  }

  function selectRevenda({ name, id, uf }) {
    if (revendaInput) revendaInput.value = name || "";
    revendaIdHidden.value = id ? String(id) : "";
    if (ufIdHidden) ufIdHidden.value = uf || "";

    // Reset dependentes
    contactMap.clear();
    contactOptions = [];
    contatoInput.value = "";
    contatoInput.disabled = true;
    contatoIdHidden.value = "";
    clearContatoDropdown(contatoDropdown);
    resetPaymentSelect();

    clearRevendaDropdown();
    if (id) {
      const ownerId = getOwnerId();
      if (ownerId) {
        fetchContatos(id, ownerId);
        fetchPaymentOptions(id);
      }
    }
  }


  function showAlert(message, type = "info") {
    alertBox.innerHTML = `
      <div class="alert alert-${type} alert-dismissible fade show" role="alert">
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
      </div>
    `;
  }

  function showFloatingCart(message) {
    if (!alertCart) return showAlert(message, "success");
    alertCart.textContent = message;
    alertCart.classList.remove("d-none");
    setTimeout(() => alertCart.classList.add("d-none"), 2500);
  }

  async function loadQuoteProducts(items = []) {
    if (!Array.isArray(items) || !items.length) return;
    try {
      await clearCartItems();
    } catch (_) {}
    
    // Processar todos os itens em paralelo ao invés de sequencialmente
    const addToCartPromises = items.map((it) => {
      const qty = Number(it.quantity) || 1;
      const discount = 100 * ((it.original_price - it.unit_price) / it.original_price);
      const unit = Number(it.unit_price) || Number(it.price) || 0;
      
      return addToCart({
        product_code: it.product_code || "",
        description: it.description || "",
        list_name: "",
        color: it.color_id || "",
        price: it.original_price,
        discount_percent: discount,
        final_price: it.total,
        favorite: false,
        quantity: qty,
      });
    });
    
    // Aguardar todas as adições ao carrinho em paralelo
    await Promise.all(addToCartPromises);
    await fetchCartItems(false);
  }

  function findContactNameById(id) {
    for (const [name, val] of contactMap.entries()) {
      if (String(val) === String(id)) return name;
    }
    return "";
  }

  function setLoading(isLoading) {
    submitBtn.disabled = isLoading;
    submitBtn.textContent = isLoading ? "aguarde..." : "Continuar";
    if (spinner) spinner.classList.toggle("d-none", !isLoading);
  }

  async function fetchRevendas(term, ownerId, targetDropdown = null) {
    if (!term || term.length < 2) return;
    try {
      const url = `/api/ploomes/contacts-search/?term=${encodeURIComponent(term)}&owner=${ownerId}&top=40`;
      const res = await fetch(url);
      if (!res.ok) return;
      const data = await res.json();
      suggestionMap.clear();
      
      if (revendaList) revendaList.innerHTML = "";
      if (revendaDropdown) revendaDropdown.innerHTML = "";
      
      // Se foi passado um dropdown específico, limpa ele também
      if (targetDropdown) {
        targetDropdown.innerHTML = "";
      }
      
      (data.results || []).forEach((item) => {
        const uf = item?.City?.State?.Short || "";
        suggestionMap.set(item.Name, item.Id);
        
        // Adiciona ao datalist se existir
        if (revendaList) {
          const option = document.createElement("option");
          option.value = item.Name;
          if (uf) option.dataset.uf = uf;
          revendaList.appendChild(option);
        }

        // Renderiza no dropdown principal se existir
        if (revendaDropdown) {
          const btn = document.createElement("button");
          btn.type = "button";
          btn.className = "list-group-item list-group-item-action";
          btn.textContent = uf ? `${item.Name} (${uf})` : item.Name;
          btn.dataset.id = item.Id;
          btn.dataset.name = item.Name;
          btn.dataset.uf = uf;
          btn.addEventListener("mousedown", (ev) => {
            ev.preventDefault();
            selectRevenda({
              name: btn.dataset.name || "",
              id: btn.dataset.id || "",
              uf: btn.dataset.uf || "",
            });
          });
          revendaDropdown.appendChild(btn);
        }
        
        // Renderiza no dropdown alternativo se foi passado
        if (targetDropdown) {
          const btn = document.createElement("button");
          btn.type = "button";
          btn.className = "list-group-item list-group-item-action";
          btn.textContent = uf ? `${item.Name} (${uf})` : item.Name;
          btn.dataset.id = item.Id;
          btn.dataset.name = item.Name;
          btn.dataset.uf = uf;
          targetDropdown.appendChild(btn);
        }
      });

      const hasResults = (data.results || []).length > 0;
      if (!hasResults) {
        if (revendaDropdown) {
          renderRevendaDropdownMessage("Nenhuma revenda encontrada");
        }
        if (targetDropdown) {
          targetDropdown.innerHTML = '<div class="list-group-item text-secondary">Nenhuma revenda encontrada</div>';
          targetDropdown.classList.remove("d-none");
        }
      } else {
        if (revendaDropdown) {
          setRevendaDropdownVisible(true);
        }
        if (targetDropdown) {
          targetDropdown.classList.remove("d-none");
        }
      }
    } catch (_) {
      /* falha silenciosa */
    }
  }

  async function fetchContatos(companyId, ownerId, options = {}) {
    if (!companyId) return;
    const { showDropdown = true } = options;
    try {
      const url = `/api/ploomes/contacts-company/?company_id=${companyId}&owner=${ownerId}`;
      if (contatoInput) {
        contatoInput.disabled = false;
      }
      if (showDropdown) {
        renderContatoDropdownMessage(contatoDropdown, "Carregando...");
      } else {
        clearContatoDropdown(contatoDropdown);
      }
      const res = await fetch(url);
      if (!res.ok) return;
      const data = await res.json();
      contactMap.clear();
      contactOptions = (data.results || [])
        .filter((item) => item && item.Name)
        .map((item) => ({ name: item.Name, id: item.Id }));

      contactOptions.forEach((item) => {
        contactMap.set(item.name, item.id);
      });

      if (contatoInput) {
        contatoInput.disabled = contactOptions.length === 0;
      }

      if (showDropdown) {
        renderContatoDropdownItems(contatoDropdown, contactOptions, selectContato);
      }
    } catch (_) {
      /* falha silenciosa */
    }
  }
  
  function computePaymentOptions(listaCliente) {

    const opcoes = baseOpcoes || []; 
    
    if (!listaCliente || !listaCliente.length) return [];

    const condicoes = [];

    listaCliente.forEach((condicao) => {
      // 1. Normalizamos apenas para COMPARAR (saber se é 'a prazo', 'á prazo', etc.)
      const normalized = condicao
        .normalize("NFD")
        .replace(/\p{Diacritic}/gu, "")
        .toLowerCase()
        .trim();

      // Caso 1: A Vista
      if (normalized === "a vista" && listaCliente.length === 1) {
        condicoes.push("A Vista"); // Mantém como está na API
        return;
      }

      // Caso 2: Antecipado
      if (normalized === "antecipado" && listaCliente.length === 1) {
        condicoes.push("Antecipado");
        return;
      }

      // Caso 3: À Prazo (AQUI ESTAVA O ERRO PRINCIPAL)
      if (normalized.startsWith("a prazo")) {
        const num = parseInt(condicao.replace(/\D+/g, ""), 10);
        if (num) {
          for (let i = 1; i <= num; i++) {
            // CORREÇÃO: Adicionada a crase manualmente na string formatada
            condicoes.push(`À prazo - ${i}x`); 
          }
        }
        // Adiciona as opções padrão
        condicoes.push("A Vista", "Antecipado");
        return;
      }

      // Caso 4: Outros (Cartão, Personalizado, etc.)
      // CORREÇÃO: Não usamos mais o .replace diacritic aqui. 
      // Usamos a string original apenas com trim(), preservando acentos (ex: "Cartão").
      condicoes.push(condicao.trim(), "A Vista", "Antecipado");
    });

    // Remove duplicatas
    const uniq = Array.from(new Set(condicoes));

    // Ordenação baseada no array baseOpcoes
    uniq.sort((a, b) => {
      const ia = opcoes.indexOf(a);
      const ib = opcoes.indexOf(b);
      if (ia === -1 && ib === -1) return a.localeCompare(b);
      if (ia === -1) return 1;
      if (ib === -1) return -1;
      return ia - ib;
    });

    return uniq;
  }

  function resetPaymentSelect(message = "Selecione uma revenda") {
    if (!paymentSelect) return;
    paymentSelect.innerHTML = `<option value="">${message}</option>`;
    paymentSelect.value = "";
    paymentSelect.disabled = true;
    if (paymentIdHidden) paymentIdHidden.value = "";
    if (paymentIdTipo2Hidden) paymentIdTipo2Hidden.value = "";
  }

  async function fetchAllPayments() {
    try {
      // Removemos o filtro específico da URL para trazer tudo
      const res = await fetch(`/api/ploomes/payment-id/`, {
        headers: { Accept: "application/json" },
      });

      if (!res.ok) return [];

      const json = await res.json();
      
      // Acessamos a propriedade .data conforme o JSON que você enviou
      return Array.isArray(json.data) ? json.data : [];
    } catch (error) {
      console.error("Erro ao buscar pagamentos:", error);
      return [];
    }
  }

  async function fetchColorId(name) {
    if (!name) return null;
    try {
      const res = await fetch(`/api/ploomes/color-id/?color=${encodeURIComponent(name)}`, {
        headers: { Accept: "application/json" },
      });
      if (!res.ok) return null;
      const data = await res.json();
      return data.id ?? null;
    } catch (_) {
      return null;
    }
  }

  async function ensureColorIds(names = defaultColors) {
    if (colorIdMap.size >= names.length) return;
    const entries = await Promise.all(
      names.map(async (name) => {
        const id = await fetchColorId(name);
        return { name, id };
      })
    );
    entries.forEach(({ name, id }) => {
      const key = name || "";
      const val = id ?? key;
      colorIdMap.set(key, val);
      colorNameById.set(String(val), key);
    });
  }

  async function fetchProductByCode(code) {
    if (!code) return null;
    if (productIdCache.has(code)) return productIdCache.get(code);
    try {
      const res = await fetch(`/api/ploomes/product-id/?code=${encodeURIComponent(code)}`, {
        headers: { Accept: "application/json" },
      });
      if (!res.ok) {
        productIdCache.set(code, null);
        return null;
      }
      const data = await res.json();
      productIdCache.set(code, data);
      return data;
    } catch (_) {
      productIdCache.set(code, null);
      return null;
    }
  }

  function buildLocalPhotoPath(kind, family) {
    if (!family) return null;
    const safe = encodeURIComponent(String(family).trim());
    return `/static/img/${kind}/${safe}.jpg`;
  }

  function setCardPhoto(imgEl, family, meta, kind = "produto") {
    
    console.log(meta);

    if (!imgEl) return;
    imgEl.src = placeholderImage;
    imgEl.alt = (meta?.nome || meta?.descricao || `Produto ${family || ""}`).toString();
    const url = buildLocalPhotoPath(kind, family);
    if (!url) return;
    imgEl.onerror = () => {
      imgEl.onerror = null;
      imgEl.src = placeholderImage;
    };
    imgEl.src = url;
  }

  function resolveColorName(value) {
    if (!value) return "";
    return colorNameById.get(String(value)) || Array.from(colorIdMap.entries()).find(([, id]) => String(id) === String(value))?.[0] || value;
  }

  function fillColorOptions(selectEl, selectedValue = "") {
    if (!selectEl) return;
    selectEl.innerHTML = "";
    // const optBlank = document.createElement("option");
    // optBlank.value = "";
    // optBlank.textContent = "Selecione";
    // selectEl.appendChild(optBlank);
    colorIdMap.forEach((id, name) => {
      const opt = document.createElement("option");
      opt.value = id ?? name;
      opt.textContent = name;
      opt.dataset.label = name;
      if (String(opt.value) === String(selectedValue)) {
        opt.selected = true;
      }
      selectEl.appendChild(opt);
    });
  }

  async function fetchPaymentOptions(companyId, targetSelect = null) {
    const selectElement = targetSelect || paymentSelect;
    
    if (!companyId) {
      if (selectElement) {
        selectElement.innerHTML = `<option value="">Selecione uma revenda</option>`;
        selectElement.value = "";
        selectElement.disabled = true;
      }
      return;
    }

    try {
      // INICIA AS DUAS REQUISIÇÕES AO MESMO TEMPO (Paralelismo)
      const clientOptionsPromise = fetch(`/api/ploomes/payment-options/?contact_id=${companyId}`);
      const allPayments = await fetchAllPayments();
      const paymentsTipo1 = allPayments.filter((opt) => opt.TableId === 32062); // forma_pagamento_id
      const paymentsTipo2 = allPayments.filter((opt) => opt.TableId === 32062); // forma_pagamento_tipo_2

      // Aguarda a resposta da API
      const resClient = await clientOptionsPromise;
      
      if (!resClient.ok) {
        if (selectElement) {
          selectElement.innerHTML = `<option value="">Nao foi possivel carregar condicoes</option>`;
          selectElement.value = "";
          selectElement.disabled = true;
        }
        return;
      }

      // Processa os dados do cliente
      const dataClient = await resClient.json();
      const contacts = dataClient.results || [];
      const listaOpcoesCliente = [];
      const FIELD_ID = 189049;

      contacts.forEach((c) => {
        (c.OtherProperties || []).forEach((prop) => {
          if (prop.FieldId === FIELD_ID && prop.ObjectValueName) {
            listaOpcoesCliente.push(prop.ObjectValueName);
          }
        });
      });

      const condicoes = computePaymentOptions(listaOpcoesCliente);

      if (!condicoes.length) {
        if (selectElement) {
          selectElement.innerHTML = `<option value="">Sem condicoes para este cliente</option>`;
          selectElement.value = "";
          selectElement.disabled = true;
        }
        return;
      }

      // Aguarda a resposta da API de IDs (que já estava carregando em background)
      const allPaymentsData = await paymentsTipo1;

      // Cria os Mapas
      const paymentMapTipo1 = new Map();
      paymentsTipo1.forEach((item) => {
        if (item.Name && item.Id) {
          // Dica: Usar .trim() evita erros se houver espaços sobrando no cadastro
          paymentMapTipo1.set(item.Name.trim(), item.Id);
        }
      });
      const paymentMapTipo2 = new Map();
      paymentsTipo2.forEach((item) => {
        if (item.Name && item.Id) {
          paymentMapTipo2.set(item.Name.trim(), item.Id);
        }
      });

      // Mapeia e Renderiza
      const mapped = condicoes.map((opt) => {
        const labelTrim = opt.trim();
        const foundIdTipo1 = paymentMapTipo1.get(labelTrim);
        const foundIdTipo2 = paymentMapTipo2.get(labelTrim);
        return {
          id: foundIdTipo1 ?? foundIdTipo2 ?? null,
          idTipo1: foundIdTipo1 ?? null,
          idTipo2: foundIdTipo2 ?? null,
          label: opt,
        };
      });

      // Limpa e popula o Select
      if (!selectElement) return;
      
      selectElement.innerHTML = `<option value="">Selecione</option>`;
      
      // Fragmento de documento para manipular o DOM apenas 1 vez (performance)
      const fragment = document.createDocumentFragment();

      mapped.forEach(({ id, idTipo1, idTipo2, label }) => {
        const option = document.createElement("option");
        // Se tiver ID usa o ID, se não tiver, usa o Label (como fallback)
        option.value = id ?? label; 
        option.textContent = label;
        option.dataset.label = label;
        option.dataset.idTipo1 = idTipo1 ?? "";
        option.dataset.idTipo2 = idTipo2 ?? "";
        fragment.appendChild(option);
      });

      selectElement.appendChild(fragment);
      selectElement.disabled = false;
      selectElement.dispatchEvent(new Event("change"));

    } catch (error) {
      console.error(error);
      if (selectElement) {
        selectElement.innerHTML = `<option value="">Nao foi possivel carregar condicoes</option>`;
        selectElement.value = "";
        selectElement.disabled = true;
      }
    }
  }
  
  async function createPloomesDeal(customPayload = {}) {
    const revendaValues = getRevendaValues();
    
    const payload = {
      nomeCliente: customPayload.nomeCliente || customPayload.title || revendaValues.nome,
      ContactId: customPayload.ContactId ?? customPayload.contact_id ?? (revendaValues.id ? Number(revendaValues.id) : null),
      PersonId: customPayload.PersonId ?? customPayload.person_id ?? (revendaValues.contatoId ? Number(revendaValues.contatoId) : null),
      OwnerId: customPayload.OwnerId ?? customPayload.owner_id ?? (getOwnerId() ? Number(getOwnerId()) : null),
      PaymentId: customPayload.PaymentId ?? customPayload.payment_id ?? (paymentIdHidden?.value || confirmPaymentIdHidden?.value ? Number(paymentIdHidden?.value || confirmPaymentIdHidden?.value) : null),
      PaymentIdTipo2: customPayload.PaymentIdTipo2 ?? customPayload.payment_id_tipo2 ?? (paymentIdTipo2Hidden?.value || confirmPaymentIdTipo2Hidden?.value ? Number(paymentIdTipo2Hidden?.value || confirmPaymentIdTipo2Hidden?.value) : null),
      PaymentName: customPayload.PaymentName ?? customPayload.payment_name ?? customPayload.paymentName ?? undefined,
      notes: customPayload.notes ?? "",
      products: customPayload.products ?? [],
    };

    if (!payload.nomeCliente || !payload.ContactId) {
      showToast("Informe o cliente e selecione uma revenda antes de criar a ordem.", "warning");
      return null;
    }

    try {
      const res = await fetch("/api/ploomes/deals/create/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      let data = {};
      try {
        data = await res.json();
      } catch (_) {
        data = {};
      }
      if (!res.ok) {
        const detail = data?.detail || `Erro ${res.status}`;
        showToast(`Falha ao criar ordem: ${detail}`, "danger");
        return null;
      }
      showToast("Ordem criada no Ploomes.",' success');
      return data;
    } catch (err) {
      showToast(`Falha ao criar ordem: ${err.message}`, "danger");
      return null;
    }
  }

  async function resolvePriceListForCustomer(revendaId) {
    if (!revendaId) return null;
    const res = await fetch(`/api/ploomes/contact-price-list/?contact_id=${encodeURIComponent(revendaId)}`, {
      headers: { Accept: "application/json" },
    });
    if (!res.ok) {
      const detail = await res.json().catch(() => ({}));
      throw new Error(detail.detail || "Falha ao consultar lista de preco do cliente.");
    }
    const data = await res.json();
    return data?.price_list || null;
  }

  async function submitQuote(event) {
    event.preventDefault();
    const formData = new FormData(form);
    const ownerId = Number(formData.get("owner_id"));
    const revendaNome = formData.get("revenda_nome")?.trim();
    const paymentOpt = paymentSelect.selectedOptions?.[0];
    const paymentId = paymentOpt?.dataset?.idTipo1 || paymentOpt?.value?.trim() || "";
    const paymentIdTipo2 = paymentOpt?.dataset?.idTipo2 || "";
    const paymentLabel = paymentOpt?.dataset?.label || paymentOpt?.textContent || "";
    const revendaId = revendaIdHidden.value ? Number(revendaIdHidden.value) : null;
    const contatoRevenda = formData.get("revenda_contato") || "";
    const contatoId = contatoIdHidden.value ? Number(contatoIdHidden.value) : null;

    if (paymentIdHidden) paymentIdHidden.value = paymentId || "";
    if (paymentIdTipo2Hidden) paymentIdTipo2Hidden.value = paymentIdTipo2 || "";

    if (!ownerId || !revendaNome || !paymentId) {
      showToast("Preencha nome da revenda e condicao de pagamento.", "warning");
      return;
    }

    lastFormState = {
      revenda: revendaNome,
      contato: contatoRevenda,
      pagamentoId: paymentId,
      pagamentoNome: paymentLabel || paymentId,
      contatoId: contatoId,
      revendaId: revendaId,
      pagamentoIdTipo2: paymentIdTipo2 || "",
    };

      setLoading(true);
      try {
        const profileId = getProfileId();
        let allowedListsForLoad = null;
        let allowAllPriceLists = false;
        if (profileId === 1) {
          setAllowedPriceLists(null);
          allowedListsForLoad = null;
          allowAllPriceLists = true;
        } else {
          if (!revendaId) {
            throw new Error("Selecione a revenda para buscar a lista de preco.");
          }
          const clientList = await resolvePriceListForCustomer(revendaId);
          if (!clientList) {
            throw new Error("Lista de preco nao encontrada para esta revenda.");
          }
          allowedListsForLoad = [clientList];
          setAllowedPriceLists(allowedListsForLoad);
          if (form) {
            form.dataset.priceList = clientList;
          }
        }
        await loadCatalog(allowedListsForLoad, allowAllPriceLists);
        catalogSection.classList.remove("d-none");
        cartFloatingBtn.classList.remove("d-none");
        const productSection = document.getElementById("productSection");
        if (productSection) productSection.classList.add("d-none");
      fetchCartItems(false);
    } catch (error) {
      showToast(`Falha ao continuar: ${error.message}`, "danger");
    } finally {
      setLoading(false);
    }
  }

  async function loadCatalog(allowedLists, allowAll) {
    const [prodRes, priceRes] = await Promise.all([
      fetch("/json/produtos"),
      fetch("/json/precos/"),
    ]);

    const prodJson = await prodRes.json();
    const priceJson = await priceRes.json();

    productsData = prodJson.produtos || [];
    catalogData = priceJson.tabelaPreco || [];
    const allowedPriceLists = Array.isArray(allowedLists) ? allowedLists : getAllowedPriceLists();
    if (!allowAll) {
      if (!allowedPriceLists.length) {
        catalogData = [];
      } else {
        catalogData = catalogData.filter((item) => {
          const name = item?.nome || item?.codigo || "";
          return allowedPriceLists.includes(name);
        });
      }
    }

    console.log(catalogData);

    productByCode.clear();
    productsData.forEach((p) => {
      if (p.codigo) {
        productByCode.set(String(p.codigo).trim(), p);
      }
    });

    mergedRows = [];

    catalogData.forEach((list) => {
      (list.precos || []).forEach((p) => {
        const produtoCodigo = String(p.produto || "").trim();
        const meta = productByCode.get(produtoCodigo);

        if (meta && meta.crm === true) {
          mergedRows.push({
            listCode: list.codigo || list.nome || "",
            listName: list.nome || list.codigo || "",
            code: produtoCodigo,
            desc: p.descricao || p.produto || "",
            priceText: p.valor,
            priceValue: parsePrice(p.valor),
            meta,
          });
        }
      });
    });

    fillPriceListFilter();
    renderTable();
  }

  function updateFilterOptions(rows, activeFilters) {
    const optionSets = {
      modeloSimples: new Set(),
      categoria: new Set(),
      modelo: new Set(),
      eixo: new Set(),
      mola: new Set(),
      freio: new Set(),
      tamanho: new Set(),
      rodado: new Set(),
      pneu: new Set(),
      opcionais: new Set(),
    };
    const modeloSimplesCategoriaMap = new Map();
    const modeloSimplesCategoriaModeloMap = new Map();

    rows.forEach((row) => {
      const meta = row.metaFieldMap || {};
      Object.keys(optionSets).forEach((key) => {
        if (meta[key]) optionSets[key].add(meta[key]);
      });
      if (meta.modeloSimples && meta.categoria) {
        if (!modeloSimplesCategoriaMap.has(meta.modeloSimples)) {
          modeloSimplesCategoriaMap.set(meta.modeloSimples, new Set());
        }
        modeloSimplesCategoriaMap.get(meta.modeloSimples).add(meta.categoria);
      }
      if (meta.modeloSimples && meta.categoria && meta.modelo) {
        const key = `${meta.modeloSimples}|||${meta.categoria}`;
        if (!modeloSimplesCategoriaModeloMap.has(key)) {
          modeloSimplesCategoriaModeloMap.set(key, new Set());
        }
        modeloSimplesCategoriaModeloMap.get(key).add(meta.modelo);
      }
    });

    Object.entries(filters).forEach(([key, select]) => {
      const current = select.value;
      select.innerHTML = "";
      const optAll = document.createElement("option");
      optAll.value = "";
      optAll.textContent = "Todos";
      select.appendChild(optAll);
      const sourceValues =
        key === "mola" || key === "freio"
          ? ["sim", "nao"]
          : (() => {
              const values = Array.from(optionSets[key]).sort((a, b) => a.localeCompare(b));
              // Para pneu, sempre oferecer a opção de "sem pneus"
              if (key === "pneu" && !values.includes("sem pneus")) values.unshift("sem pneus");
              return values;
            })();

      sourceValues.forEach((val) => {
        const opt = document.createElement("option");
        opt.value = val;
        opt.textContent =
          key === "mola" || key === "freio"
            ? val ? val.charAt(0).toUpperCase() + val.slice(1) : "Todos"
            : val || "Todos";
        select.appendChild(opt);
      });

      if (optionSets[key].has(current)) {
        select.value = current;
      } else if (["sim", "nao"].includes(current) && (key === "mola" || key === "freio")) {
        select.value = current;
      }
    });

    const modeloSimplesOptions = Array.from(optionSets.modeloSimples)
      .filter((val) => val && String(val).trim().length)
      .sort((a, b) => a.localeCompare(b));
    renderModeloSimplesCards(modeloSimplesOptions, filters.modeloSimples.value || "");
    const categoriasForModeloSimples =
      modeloSimplesCategoriaMap.get(filters.modeloSimples.value) || new Set();
    renderCategoriaCards(Array.from(categoriasForModeloSimples), filters.categoria.value || "");
    const modelosForCategoria =
      modeloSimplesCategoriaModeloMap.get(`${filters.modeloSimples.value}|||${filters.categoria.value}`) ||
      new Set();
    renderModeloCards(Array.from(modelosForCategoria), filters.modelo.value || "");

    renderModalFilters(optionSets);
  }

  function fillPriceListFilter() {
    priceListFilter.innerHTML = "";
    catalogData.forEach((item, idx) => {
      const opt = document.createElement("option");
      opt.value = item.codigo || item.nome || `lista-${idx}`;
      opt.textContent = item.nome || item.codigo || `Lista ${idx + 1}`;
      priceListFilter.appendChild(opt);
    });
    if (catalogData.length === 0) {
      const opt = document.createElement("option");
      opt.value = "";
      opt.textContent = "Nenhuma lista disponivel";
      priceListFilter.appendChild(opt);
    }
    const preferred = getPriceList();
    if (preferred) {
      const opt = Array.from(priceListFilter.options).find((o) => o.textContent === preferred || o.value === preferred);
      if (opt) priceListFilter.value = opt.value;
    }
  }

  function parsePrice(text) {
    if (typeof text === 'number') return text;
    if (!text) return 0;
    // Se vier como string de centavos (ex: "2833500"), divide por 100
    const cleaned = text.replace(/\./g, '').replace(',', '.').replace(/[^0-9.]/g, '');
    let num = parseFloat(cleaned);
    // Se for inteiro grande, assume centavos e divide por 100
    if (num > 100000) num = num / 100;
    return Number.isNaN(num) ? 0 : num;
  }

  function toggleSelectVisibility() {
    const hasModeloSimples = Boolean(filters.modeloSimples?.value);
    const hasCategoria = Boolean(filters.categoria?.value);
    const hasModelo = Boolean(filters.modelo?.value);
    if (filters.categoria) filters.categoria.classList.toggle("d-none", !hasCategoria);
    // if (filters.modelo) filters.modelo.classList.toggle("d-none", !hasModelo);

    const canShowOthers = hasCategoria && hasModelo;
    if (etapaModeloSimples) etapaModeloSimples.classList.toggle("d-none", hasModeloSimples);
    if (etapaCategoria) etapaCategoria.classList.toggle("d-none", !hasModeloSimples || hasCategoria);
    if (etapaModelo) etapaModelo.classList.toggle("d-none", !hasCategoria);
    if (btnVoltarButtons.length) {
      btnVoltarButtons.forEach((btn) => btn.classList.toggle("d-none", !hasModeloSimples));
    }

    if (etapaOutros) etapaOutros.classList.toggle("d-none", !canShowOthers);
    if (priceListFilter) priceListFilter.classList.toggle("d-none", !canShowOthers);

    if (!canShowOthers && filtrosModal) {
        const modal = bootstrap.Modal.getInstance(filtrosModal);
        if (modal) modal.hide();
    }

    updateBackButton();
  }

  function updateBackButton() {
    if (!btnVoltarButtons.length) return;
    const hasModeloSimples = Boolean(filters.modeloSimples?.value);
    const hasCategoria = Boolean(filters.categoria?.value);
    const hasModelo = Boolean(filters.modelo?.value);

    if (!hasModeloSimples) {
      btnVoltarButtons.forEach((btn) => btn.classList.add("d-none"));
      return;
    }

    btnVoltarButtons.forEach((btn) => btn.classList.remove("d-none"));
    if (hasModelo) {
      btnVoltarButtons.forEach((btn) => (btn.textContent = "Voltar para modelo"));
    } else if (hasCategoria) {
      btnVoltarButtons.forEach((btn) => (btn.textContent = "Voltar para categoria"));
    } else {
      btnVoltarButtons.forEach((btn) => (btn.textContent = "Voltar para modelo simples"));
    }
  }

  function renderModeloSimplesCards(options = [], selectedValue = "") {
    if (!modeloSimplesCards) return;
    modeloSimplesCards.innerHTML = "";
    options.sort((a, b) => a.localeCompare(b));
    options.forEach((opt) => {
      const col = document.createElement("div");
      col.className = "col";
      col.innerHTML = `
        <div class="card h-100 bg-dark border border-secondary-subtle catalog-card text-light select-modelo-simples" data-value="${opt}">
          <div class="catalog-photo-wrapper ratio ratio-16x9 mb-2">
            <img class="catalog-photo" src="${buildLocalPhotoPath("modelo_simples", opt) || placeholderCard}" alt="${opt}" loading="lazy" onerror="this.src='${placeholderCard}'">
          </div>
          <div class="card-body py-2">
            <div class="d-flex align-items-center justify-content-between">
              <span class="fw-semibold">${opt}</span>
              <span class="badge ${selectedValue === opt ? "bg-success" : "bg-secondary"}">${selectedValue === opt ? "Selecionado" : "Escolher"}</span>
            </div>
          </div>
        </div>
      `;
      col.querySelector(".select-modelo-simples").addEventListener("click", () => {
        filters.modeloSimples.value = opt;
        filters.categoria.value = "";
        filters.modelo.value = "";
        toggleSelectVisibility();
        renderTable();
      });
      modeloSimplesCards.appendChild(col);
    });
  }

  function renderCategoriaCards(options = [], selectedValue = "") {
    if (!categoriaCards) return;
    categoriaCards.innerHTML = "";
    const hasModeloSimples = filters.modeloSimples?.value;
    if (!hasModeloSimples) {
      categoriaCards.innerHTML = `<div class="text-secondary">Selecione um modelo simples primeiro.</div>`;
      return;
    }
    options.sort((a, b) => a.localeCompare(b));
    options.forEach((opt) => {
      const col = document.createElement("div");
      col.className = "col";
      col.innerHTML = `
        <div class="card h-100 bg-dark border border-secondary-subtle catalog-card text-light select-categoria" data-value="${opt}">
          <div class="ratio ratio-16x9 mb-2">
            <div class="d-flex align-items-center justify-content-center text-center px-3 rounded-top" style="background: linear-gradient(135deg, rgba(148,163,184,.2), rgba(71,85,105,.35));">
              <span class="fw-semibold fs-5">${opt}</span>
            </div>
          </div>
          <div class="card-body py-2">
            <div class="d-flex align-items-center justify-content-between">
              <span class="fw-semibold">${opt}</span>
              <span class="badge ${selectedValue === opt ? "bg-success" : "bg-secondary"}">${selectedValue === opt ? "Selecionado" : "Escolher"}</span>
            </div>
          </div>
        </div>
      `;
      col.querySelector(".select-categoria").addEventListener("click", () => {
        filters.categoria.value = opt;
        filters.modelo.value = "";
        toggleSelectVisibility();
        renderTable();
      });
      categoriaCards.appendChild(col);
    });
  }

  function renderModeloCards(options = [], selectedValue = "") {
    if (!modeloCards) return;
    modeloCards.innerHTML = "";
    const hasCategoria = filters.categoria?.value;
    if (!hasCategoria) {
      modeloCards.innerHTML = `<div class="text-secondary">Selecione uma categoria primeiro.</div>`;
      return;
    }

    options.sort((a, b) => a.localeCompare(b));
    options.forEach((opt) => {
      const col = document.createElement("div");
      col.className = "col";
      col.innerHTML = `
        <div class="card h-100 bg-dark border border-secondary-subtle catalog-card text-light select-modelo" data-value="${opt}">
          <div class="catalog-photo-wrapper ratio ratio-16x9 mb-2">
            <img class="catalog-photo" src="${buildLocalPhotoPath("produto", opt) || placeholderCard}" alt="${opt}" loading="lazy" onerror="this.src='${placeholderCard}'">
          </div>
          <div class="card-body py-2">
            <div class="d-flex align-items-center justify-content-between">
              <span class="fw-semibold">${opt}</span>
              <span class="badge ${selectedValue === opt ? "bg-success" : "bg-secondary"}">${selectedValue === opt ? "Selecionado" : "Escolher"}</span>
            </div>
          </div>
        </div>
      `;
      col.querySelector(".select-modelo").addEventListener("click", () => {
        filters.modelo.value = opt;
        toggleSelectVisibility();
        renderTable();
        const productSection = document.getElementById("productSection");
        if (productSection) productSection.classList.remove("d-none");
      });
      modeloCards.appendChild(col);
    });
  }

  async function renderTable() {
    const selectedList = priceListFilter.value;
    const searchTerm = normalize(catalogSearch?.value || "");
    const activeFilters = Object.fromEntries(
      Object.entries(filters).map(([key, el]) => [key, (el.value || "").toLowerCase().trim()])
    );
    const hasModelSelected = Boolean(filters.modelo?.value);
    const productSection = document.getElementById("productSection");
    toggleSelectVisibility();
    const molaFilterValue = (filters.mola?.value || "").toLowerCase().trim();
    const freioFilterValue = (filters.freio?.value || "").toLowerCase().trim();
    delete activeFilters.mola;
    delete activeFilters.freio;
    await ensureColorIds();

    const favorites = await getFavoritesCached(selectedList);
    const favoriteCodes = new Set(favorites.map((f) => f.product_code));

    const rows = mergedRows.filter((row) => {
      if (selectedList && row.listCode !== selectedList && row.listName !== selectedList) return false;
      return true;
    });

    const filteredRows = rows
      .map((row) => {
        const meta = row.meta || {};

        row.metaFieldMap = {
          modeloSimples: meta.modelo_simples ?? "",
          categoria: meta.desc_generica ?? "",
          modelo: meta.modelo ?? "",
          eixo: meta.eixo ?? "",
          mola: (meta.mola || "").toUpperCase(),
          tamanho: meta.tamanho ?? "",
          rodado: meta.rodado ?? "",
          // Campo vazio significa sem pneus; padroniza para filtrar
          pneu: meta.pneu ? meta.pneu : "sem pneus",
          opcionais: meta.funcionalidade ? meta.funcionalidade : "sem opcionais",
          freio: (meta.freio || "").toUpperCase(),
        };
        
        // Converter códigos C/S para sim/nao para os filtros
        const molaCode = row.metaFieldMap.mola || "";
        const freioCode = row.metaFieldMap.freio || "";
        row.metaFieldMap.mola = molaCode === "C" ? "sim" : molaCode === "S" ? "nao" : "";
        row.metaFieldMap.freio = freioCode === "C" ? "sim" : freioCode === "S" ? "nao" : "";

        return row;
      })
      .filter((row) =>
        Object.entries(activeFilters).every(([key, term]) => {
          if (!term) return true;

          const value = normalize(row.metaFieldMap[key] ?? "");
          const filter = normalize(term);

          // Filtros por card/select devem casar exatamente com a opção escolhida.
          return value === filter;
        }) &&
        (!searchTerm ||
          normalize(row.meta?.modelo_simples ?? "").includes(searchTerm) ||
          normalize(row.meta?.desc_generica ?? "").includes(searchTerm) ||
          normalize(row.meta?.modelo ?? "").includes(searchTerm))
      );

    // Filtro para mola (valores "sim" ou "nao" já estão no metaFieldMap)
    const filteredByMolaFreio = filteredRows.filter((row) => {
      const molaFilter = (molaFilterValue || "").toLowerCase().trim();
      const freioFilter = (freioFilterValue || "").toLowerCase().trim();
      
      const rowMola = (row.metaFieldMap.mola || "").toLowerCase().trim();
      const rowFreio = (row.metaFieldMap.freio || "").toLowerCase().trim();
      
      // Se não há filtro, passa
      if (!molaFilter && !freioFilter) return true;
      
      // Se há filtro de mola, verifica
      if (molaFilter && rowMola !== molaFilter) return false;
      
      // Se há filtro de freio, verifica
      if (freioFilter && rowFreio !== freioFilter) return false;
      
      return true;
    });

    filteredByMolaFreio.sort((a, b) => {
      const isAFav = favoriteCodes.has(a.code);
      const isBFav = favoriteCodes.has(b.code);
      if (isAFav && !isBFav) return -1;
      if (!isAFav && isBFav) return 1;
      return 0;
    });

    if (catalogGrid) catalogGrid.innerHTML = "";
    const hasResults = filteredByMolaFreio.length > 0;
    if (catalogEmpty) catalogEmpty.classList.toggle("d-none", hasResults);
    updateFilterOptions(filteredByMolaFreio, activeFilters);

    if (!hasModelSelected) {
      if (productSection) productSection.classList.add("d-none");
      return;
    }
    if (!hasResults) {
      if (productSection) productSection.classList.add("d-none");
      return;
    }
    if (productSection) productSection.classList.remove("d-none");

    filteredByMolaFreio.forEach((row) => {
      const { desc, code, listName, priceText, priceValue, meta } = row;
      const isFavorite = favoriteCodes.has(code);
      const familyName = meta.modelo || meta.descGenerica || "";
      const molaCode = (row.metaFieldMap.mola || "").toUpperCase();
      const freioFlag = (row.metaFieldMap.freio || "").toLowerCase();
      const molaLabel = molaCode ? (molaCode[0] === "C" ? "Com mola" : "Sem mola") : "";
      const freioLabel = freioFlag ? (freioFlag === "sim" ? "Com freio" : "Sem freio") : "";
      const badges = [
        { label: "Modelo", value: meta.modelo },
        { label: "Eixo", value: meta.eixo },
        { label: "Mola", value: molaLabel },
        { label: "Freio", value: freioLabel },
        { label: "Tam", value: meta.tamanho },
        { label: "Rodado", value: meta.rodado },
        { label: "Pneu", value: meta.pneu },
        { label: "Opc.", value: meta.funcionalidade },
      ]
        .filter((item) => item.value)
        .map(
          (item) =>
            `<span class="badge bg-dark border fw-normal">${item.label}: ${item.value}</span>`
        )
        .join("");

      const col = document.createElement("div");
      col.className = "col";
      const priceTextFormatted = (typeof priceValue === 'number')
        ? priceValue.toLocaleString('pt-BR', { minimumFractionDigits: 2 })
        : (parseFloat(priceValue) || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2 });
      
      col.innerHTML = `
        <div class="card catalog-card h-100">
          <div class="catalog-photo-wrapper ratio ratio-16x9 bg-dark-subtle">
            <img class="catalog-photo" alt="${meta.nome || desc || code}" loading="lazy">
          </div>
          <div class="card-body d-flex flex-column gap-2">
            <div class="d-flex justify-content-between align-items-start">
              <div>
                <div class="small text-uppercase">Familia</div>
                <div class="fw-semibold">${meta.modelo || "-"}</div>
              </div>
              <span class="badge bg-secondary border border-secondary">${code}</span>
            </div>
            <p class="small mb-1">${meta.nome || desc || ""}</p>
            <div class="small">Lista: ${listName || "-"}</div>
            <div class="d-flex flex-wrap gap-1 mb-1">${badges}</div>
            <div>
              <label class="form-label form-label-sm mb-1">Cor</label>
              <select class="form-select form-select-sm color-select"></select>
            </div>
            <div>
              <label class="form-label form-label-sm mb-1">Opções de preço</label>
              <select class="form-select form-select-sm price-select" data-base="${priceValue}">
                <option value="${priceValue}">${priceText}</option>
              </select>
            </div>
            <div class="row g-2">
              <div class="col-6">
                <label class="form-label form-label-sm mb-1">% desc.</label>
                <input type="number" class="form-control form-control-sm discount-input" value="0" min="0" max="100">
              </div>
              <div class="col-6">
                <label class="form-label form-label-sm mb-1">Preço final</label>
                <input type="text" class="form-control form-control-sm price-final" value="${priceTextFormatted}" readonly>
              </div>
            </div>
            <div class="d-flex align-items-center justify-content-between mt-auto">
              <div class="form-check form-switch toggle-favorite mb-0">
                <input class="form-check-input" type="checkbox" ${isFavorite ? "checked" : ""}>
                <label class="form-check-label small">Favorito</label>
              </div>
              <button class="btn btn-success btn-sm add-cart-btn" data-code="${code}">Adicionar</button>
            </div>
          </div>
        </div>
      `;

      const discountInput = col.querySelector(".discount-input");
      const priceSelect = col.querySelector(".price-select");
      const finalInput = col.querySelector(".price-final");
      const colorSelect = col.querySelector(".color-select");
      const addBtn = col.querySelector(".add-cart-btn");
      const toggleFavorite = col.querySelector(".toggle-favorite");
      const img = col.querySelector(".catalog-photo");

      setCardPhoto(img, familyName, meta, "produto");

      const recalc = () => {
        const base = parseFloat(priceSelect.value) || 0;
        const perc = Math.max(0, Math.min(100, Number(discountInput.value) || 0));
        const final = base * (1 - perc / 100);
        const formatted = final.toLocaleString("pt-BR", { minimumFractionDigits: 2 });
        finalInput.value = formatted;
        try { finalInput.setAttribute('value', formatted); } catch (e) { /* ignore */ }
        finalInput.dataset.manual = "0";
      };

      discountInput.addEventListener("input", () => {
        finalInput.dataset.manual = "0";
        recalc();
      });
      priceSelect.addEventListener("change", () => {
        finalInput.dataset.manual = "0";
        recalc();
      });
      finalInput.addEventListener("input", () => {
        finalInput.dataset.manual = "1";
      });
      fillColorOptions(colorSelect);
      recalc();

      addBtn.addEventListener("click", async () => {
        const selectedColorOption = colorSelect?.selectedOptions?.[0];
        // Recalcula o preço final a partir dos valores atuais antes de enviar
        if (finalInput.dataset.manual !== "1") {
          try {
            recalc();
          } catch (e) {
            /* noop */
          }
        }
        const finalPrice = parsePrice(finalInput.value);

        const originalLabel = addBtn.innerHTML;
        addBtn.disabled = true;
        addBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>';
        try {
          await addToCart({
          product_code: code,
          description: meta.nome || desc,
          list_name: listName || "",
          color: colorSelect?.value || "",
          color_name: selectedColorOption?.dataset?.label || selectedColorOption?.textContent || "",
          price: parsePrice(priceSelect.value) || priceValue,
          discount_percent: Number(discountInput.value) || 0,
          final_price: finalPrice,
          favorite: false,
          quantity: 1,
        });
        } finally {
          addBtn.disabled = false;
          addBtn.innerHTML = originalLabel;
        }
      });

      toggleFavorite.addEventListener("change", (event) => {
        sendToggleFavorite(event.target.checked, {
          product_code: code,
          price_list: priceListFilter.value,
        });
      });

      if (catalogGrid) catalogGrid.appendChild(col);
    });

    updateFilterOptions(filteredByMolaFreio, activeFilters);
  }

  function sendToggleFavorite(isOn, item) {
    const state = isOn ? "on" : "off";

    if (state === 'on') {

      fetch("/api/favorites/add/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify(item)
      })
      .then((response) => response.json())
      .then((data) => console.log("Resposta do servidor:", data))
      .catch((error) => console.error("Erro ao enviar toggle:", error));
    } else {
            fetch("/api/favorites/delete/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify(item)
      })
      .then((response) => response.json())
      .then((data) => console.log("Resposta do servidor:", data))
      .catch((error) => console.error("Erro ao enviar toggle:", error));

    }
  }

  async function addToCart(item) {
    try {
      const res = await fetch("/api/cart/add/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(item),
      });
      if (!res.ok) throw new Error(`Erro ${res.status}`);
      showToast("Item adicionado no carrinho de compras.", 'success');
      fetchCartItems(false);
    } catch (err) {
      showToast(`Falha ao adicionar no carrinho: ${err.message}`, "danger");
    }
  }
 
  async function fetchFavoriteItens(priceList) {
    try {
      const res = await fetch(`/api/favorites/list/?priceList=${priceList}`, { headers: { Accept: "application/json" } });
      if (!res.ok) throw new Error(`Erro ${res.status}`);
      const data = await res.json();
      const items = data.items || [];
      return items;  // Retorna um array com os itens favoritos
    } catch (err) {
      showToast(`Falha ao carregar lista de favoritos: ${err.message}`, "danger");
      return [];
    }
  }

  function updateCartBadge(itemsOrCount = []) {
    if (!cartCountBadge || !cartFloatingBtn) return;

    const totalQty = Array.isArray(itemsOrCount)
      ? itemsOrCount.reduce((sum, item) => sum + (Number(item.quantity) || 0), 0)
      : Number(itemsOrCount) || 0;
    
    const shouldShow = totalQty > 0 && !cartFloatingBtn.classList.contains("d-none");
    cartCountBadge.textContent = totalQty;
    cartCountBadge.classList.toggle("d-none", !shouldShow);
  }

  async function fetchCartItems(shouldRender = true) {
    try {
      const res = await fetch("/api/cart/list/", { headers: { Accept: "application/json" } });
      if (!res.ok) throw new Error(`Erro ${res.status}`);
      const data = await res.json();
      const items = data.items || [];
      updateCartBadge(items);
      if (items.length && cartFloatingBtn) {
        cartFloatingBtn.classList.remove("d-none");
      }
      // Habilita/desabilita o botão de confirmar carrinho
      if (confirmCartBtn) {
        confirmCartBtn.disabled = items.length === 0;
      }
      if (shouldRender) await renderCart(items);
      return items;
    } catch (err) {
      updateCartBadge([]);
      // Desabilita o botão em caso de erro
      if (confirmCartBtn) {
        confirmCartBtn.disabled = true;
      }
      showToast(`Falha ao carregar carrinho: ${err.message}`, "danger");
      return [];
    }
  }

  async function renderCart(items) {
    if (!cartTableBody || !cartOverlay) return;
    await ensureColorIds();
    cartTableBody.innerHTML = "";
    if (!items.length) {
      cartEmpty?.classList.remove("d-none");
      if (cartTotalValue) cartTotalValue.textContent = "R$ 0,00";
      // Desabilita o botão quando o carrinho está vazio
      if (confirmCartBtn) confirmCartBtn.disabled = true;
    } else {
      cartEmpty?.classList.add("d-none");
      // Habilita o botão quando há itens no carrinho
      if (confirmCartBtn) confirmCartBtn.disabled = false;
    }

    console.log("itens: ", items);

    let totalGeral = 0;
    items.forEach((item) => {
      const tr = document.createElement("tr");
      const basePrice = parsePrice(item.price);
      const discount = Math.max(0, parseFloat(item.discount_percent) || 0);
      const qty = item.quantity || 1;
      // const finalUnit = parsePrice((basePrice * (1 - discount / 100)) || 0);
      // const finalUnitDisplay = (Number(finalUnit) || 0).toFixed(2);
      const unitFinal = (Number(basePrice) || 0) * (1 - discount / 100);
      const total = unitFinal * qty;
      totalGeral += total;
      
      tr.innerHTML = `
        <td data-label="Cód.">${item.product_code}</td>
        <td data-label="Item">${item.description}</td>
        <td data-label="Cor">
          <select class="form-select form-select-sm cart-color"></select>
        </td>
        <td data-label="Preço"><input type="number" class="form-control form-control-sm cart-price" step="0.01" value="${Number(basePrice || 0).toFixed(2)}" data-base="${basePrice}" disabled></td>
        <td data-label="Desc.%"><input type="number" class="form-control form-control-sm cart-discount" step="0.01" value="${item.discount_percent || 0}" min="0" max="100"></td>
        <td data-label="Preço unit."><input type="number" class="form-control form-control-sm cart-unit-price" step="0.01" value="${unitFinal.toFixed(2)}"></td>
        <td data-label="Qtd"><input type="number" class="form-control form-control-sm cart-qty" min="1" value="${qty}"></td>
        <td data-label="Total"><input type="text" class="form-control form-control-sm cart-total" value="R$ ${total.toLocaleString("pt-BR", { minimumFractionDigits: 2 })}" readonly></td>
        <td data-label=""><button class="btn btn-sm btn-outline-danger cart-remove">Excluir</button></td>
      `;
      const colorInput = tr.querySelector(".cart-color");
      const priceInput = tr.querySelector(".cart-price");
      const discountInput = tr.querySelector(".cart-discount");
      const unitPriceInput = tr.querySelector(".cart-unit-price");
      const qtyInput = tr.querySelector(".cart-qty");
      const totalInput = tr.querySelector(".cart-total");
      const removeBtn = tr.querySelector(".cart-remove");

      const clampDiscount = (value) => Math.max(0, Math.min(100, Number(value) || 0));

      const round2 = (value) => {
        const n = Number(value);
        if (!Number.isFinite(n)) return 0;
        return Math.round(n * 100) / 100;
      };

      // Flag para saber se o usuário está editando manualmente o preço unitário
      let manualUnitPriceEdit = false;

      const recalcFromDiscount = () => {
        const base = parseFloat(priceInput.dataset.base || "0") || 0;
        const discountPerc = clampDiscount(discountInput.value);
        const qty = Math.max(1, parseInt(qtyInput.value, 10) || 1);

        const unitPrice = round2(base * (1 - discountPerc / 100));
        
        // Só atualiza o preço unitário se não estiver em edição manual
        if (!manualUnitPriceEdit) {
          unitPriceInput.value = unitPrice.toFixed(2);
        }

        const total = parseFloat(unitPriceInput.value || "0") * qty;
        if (totalInput) {
          totalInput.value = `R$ ${total.toLocaleString("pt-BR", { minimumFractionDigits: 2 })}`;
          try { totalInput.setAttribute("value", totalInput.value); } catch (_) {}
        }
        updateCartTotalFromDom();
      };

      const recalcFromUnitPrice = () => {
        // Quando o preço unitário é alterado manualmente, recalcula o desconto
        const base = parseFloat(priceInput.dataset.base || "0") || 0;
        const unitPrice = parseFloat(unitPriceInput.value || "0") || 0;
        const qty = Math.max(1, parseInt(qtyInput.value, 10) || 1);

        // Calcula o desconto baseado no preço unitário informado
        if (base > 0) {
          const calculatedDiscount = round2(((base - unitPrice) / base) * 100);
          discountInput.value = Math.max(0, Math.min(100, calculatedDiscount)).toFixed(2);
        }

        const total = unitPrice * qty;
        if (totalInput) {
          totalInput.value = `R$ ${total.toLocaleString("pt-BR", { minimumFractionDigits: 2 })}`;
          try { totalInput.setAttribute("value", totalInput.value); } catch (_) {}
        }
        updateCartTotalFromDom();
      };

      const recalcTotal = () => {
        // Apenas recalcula o total sem alterar desconto ou preço unitário
        const unitPrice = parseFloat(unitPriceInput.value || "0") || 0;
        const qty = Math.max(1, parseInt(qtyInput.value, 10) || 1);
        const total = unitPrice * qty;
        
        if (totalInput) {
          totalInput.value = `R$ ${total.toLocaleString("pt-BR", { minimumFractionDigits: 2 })}`;
          try { totalInput.setAttribute("value", totalInput.value); } catch (_) {}
        }
        updateCartTotalFromDom();
      };

      const save = async () => {
        const base = parseFloat(priceInput.dataset.base || "0") || 0;
        const discountPerc = clampDiscount(discountInput.value);
        const unitPrice = parseFloat(unitPriceInput.value || "0") || 0;
        const qty = Math.max(1, parseInt(qtyInput.value, 10) || 1);
        await updateCartItem(item.id, {
          color: colorInput.value,
          price: base,
          discount_percent: discountPerc,
          final_price: unitPrice,
          quantity: qty,
        });
      };

      fillColorOptions(colorInput, item.color);
      colorInput.addEventListener("change", save);
      
      // Quando o desconto muda, recalcula o preço unitário
      discountInput.addEventListener("input", () => {
        manualUnitPriceEdit = false;
        recalcFromDiscount();
      });
      
      discountInput.addEventListener("change", () => {
        if (!discountInput.value || Number(discountInput.value) < 0) discountInput.value = 0;
        if (Number(discountInput.value) > 100) discountInput.value = 100;
        manualUnitPriceEdit = false;
        recalcFromDiscount();
        save();
      });

      // Quando o preço unitário é editado manualmente
      unitPriceInput.addEventListener("focus", () => {
        manualUnitPriceEdit = true;
      });

      unitPriceInput.addEventListener("input", () => {
        recalcTotal();
      });

      unitPriceInput.addEventListener("change", () => {
        if (!unitPriceInput.value || Number(unitPriceInput.value) < 0) unitPriceInput.value = 0;
        recalcFromUnitPrice();
        save();
        manualUnitPriceEdit = false;
      });

      // Quando a quantidade muda, apenas recalcula o total
      qtyInput.addEventListener("input", () => {
        recalcTotal();
      });

      qtyInput.addEventListener("change", () => {
        if (!qtyInput.value || Number(qtyInput.value) < 1) qtyInput.value = 1;
        recalcTotal();
        save();
      });

      removeBtn.addEventListener("click", async () => {
        const originalLabel = removeBtn.innerHTML;
        removeBtn.disabled = true;
        removeBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>';
        try {
          await deleteCartItem(item.id);
          await fetchCartItems();
        } finally {
          removeBtn.disabled = false;
          removeBtn.innerHTML = originalLabel;
        }
      });

      cartTableBody.appendChild(tr);
      recalcFromDiscount();
      colorInput.dispatchEvent(new Event("change"));
    });
    if (cartTotalValue) {
      cartTotalValue.textContent = `R$ ${totalGeral.toLocaleString("pt-BR", { minimumFractionDigits: 2 })}`;
    }
    cartOverlay.classList.remove("d-none");
  }

  async function showConfirmation() {
    const items = await fetchCartItems();
    if (!confirmOverlay || !confirmCardsBody || !confirmSummary) return;
    await ensureColorIds();

    confirmCardsBody.innerHTML = "";
    let total = 0;
    const productsInfo = await Promise.all(
      items.map(async (it) => ({
        item: it,
        productInfo: await fetchProductByCode(it.product_code),
      }))
    );

    productsInfo.forEach(({ item: it, productInfo }) => {
      const qty = it.quantity || 1;
      const price = parseFloat(it.price) || parseFloat(it.final_price) || 0;
      const discount = Math.max(0, parseFloat(it.discount_percent) || 0);
      const unitWithDiscount = price * (1 - discount / 100);
      const itemTotal = unitWithDiscount * qty;
      total += itemTotal;

      // Renderiza como card
      const col = document.createElement("div");
      col.className = "col-12 col-md-6 col-lg-4 mb-3";
      col.innerHTML = `
        <div class="card h-100 border border-primary shadow-sm">
          <div class="card-body">
            <h6 class="fw-bold mb-2">${it.description}</h6>
            <ul class="list-unstyled mb-2">
              <li><strong>Cód:</strong> ${it.product_code}</li>
              <li><strong>Cor:</strong> ${resolveColorName(it.color)}</li>
              <li><strong>Qtd:</strong> ${qty}</li>
              <li><strong>Desconto:</strong> ${discount}%</li>
              <li><strong>Preço un.:</strong> R$ ${unitWithDiscount.toLocaleString("pt-BR", { minimumFractionDigits: 2 })}</li>
              <li><strong>Total:</strong> R$ ${itemTotal.toLocaleString("pt-BR", { minimumFractionDigits: 2 })}</li>
            </ul>
          </div>
        </div>
      `;
      confirmCardsBody.appendChild(col);
    });

    // Atualiza o valor total no footer
    const confirmTotalValue = document.getElementById("confirmTotalValue");
    if (confirmTotalValue) {
      confirmTotalValue.textContent = `Total: R$ ${total.toLocaleString("pt-BR", { minimumFractionDigits: 2 })}`;
    }

    if (!isRevision && confirmSummary) {
      const resumo = [
        `Revenda: ${lastFormState?.revenda || "—"}`,
        `Contato: ${lastFormState?.contato || "—"}`,
        `Pagamento: ${lastFormState?.pagamentoNome || lastFormState?.pagamentoId || "—"}`,
        `Total: R$ ${total.toLocaleString("pt-BR", { minimumFractionDigits: 2 })}`,
      ].join(" | ");
      confirmSummary.textContent = resumo;
      confirmSummary.classList.remove("d-none");
    } else if (confirmSummary) {
      confirmSummary.classList.add("d-none");
    }
    confirmOverlay.classList.remove("d-none");
  }

  function updateCartTotalFromDom() {
    if (!cartTableBody || !cartTotalValue) return;
    let total = 0;
    let totalQty = 0;
    cartTableBody.querySelectorAll("tr").forEach((tr) => {
      const unitPriceEl = tr.querySelector(".cart-unit-price");
      const qty = parseInt(tr.querySelector(".cart-qty")?.value || "1", 10) || 1;
      const unitPrice = parseFloat(unitPriceEl?.value || "0") || 0;
      total += unitPrice * qty;
      totalQty += qty;
    });
    cartTotalValue.textContent = `R$ ${total.toLocaleString("pt-BR", { minimumFractionDigits: 2 })}`;
    updateCartBadge(totalQty);
  }

  async function updateCartItem(id, payload) {
    await fetch(`/api/cart/update/${id}/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  }

  async function deleteCartItem(id) {
    await fetch(`/api/cart/delete/${id}/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
    });
  }

  function formatCurrencyBRL(value) {
    const num = Number(value) || 0;
    return `R$ ${num.toLocaleString("pt-BR", { minimumFractionDigits: 2 })}`;
  }

  function buildProposalClipboardText(items = []) {
    let total = 0;
    const blocks = items.map((it) => {
      const qty = Number(it.quantity) || 1;
      const unitPrice = Number(it.final_price) || Number(it.price) || 0;
      const subtotal = unitPrice * qty;
      total += subtotal;
      const description = (it.description === null || it.description === undefined || it.description === "")
        ? "null"
        : String(it.description);

      return [
        `Produto: ${it.product_code || ""}`,
        `Descrição: ${description}`,
        `Cor: ${resolveColorName(it.color)}`,
        `Quantidade: ${qty}`,
        `Preço unitário: ${formatCurrencyBRL(unitPrice)}`,
        `Subtotal: ${formatCurrencyBRL(subtotal)}`,
      ].join("\n");
    });

    return `${blocks.join("\n\n")}\n\nTotal: ${formatCurrencyBRL(total)}`;
  }

  async function copyToClipboard(text) {
    if (!text) return;
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(text);
      return;
    }
    const ta = document.createElement("textarea");
    ta.value = text;
    ta.setAttribute("readonly", "");
    ta.style.position = "fixed";
    ta.style.left = "-9999px";
    document.body.appendChild(ta);
    ta.select();
    document.execCommand("copy");
    document.body.removeChild(ta);
  }

  async function clearCartItems() {
    const res = await fetch("/api/cart/clear/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
    });
    if (!res.ok) {
      throw new Error(`Erro ${res.status}`);
    }
  }

  if (cartFloatingBtn) {
    cartFloatingBtn.addEventListener("click", async () => {
      const originalLabel = cartFloatingBtn.innerHTML;
      cartFloatingBtn.disabled = true;
      cartFloatingBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>';
      try {
        await fetchCartItems();
      } finally {
        cartFloatingBtn.disabled = false;
        cartFloatingBtn.innerHTML = originalLabel;
      }
    });
  }
  if (confirmCartBtn) {
    confirmCartBtn.addEventListener("click", async () => {

      // desabiiltar botão e mostrar loading
      confirmCartBtn.disabled = true;
      confirmCartBtn.innerHTML = 'aguarde...';

      await showConfirmation();

      confirmCartBtn.innerHTML = 'Continuar';
      confirmCartBtn.disabled = false;

    });
  }
  if (clearCartBtn) {
    clearCartBtn.addEventListener("click", async () => {
      const confirmed = window.confirm("Deseja limpar todos os itens do carrinho?");
      if (!confirmed) return;
      const originalLabel = clearCartBtn.innerHTML;
      clearCartBtn.disabled = true;
      clearCartBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>';
      try {
        await clearCartItems();
        await fetchCartItems();
        // Desabilita o botão após limpar o carrinho
        if (confirmCartBtn) confirmCartBtn.disabled = true;
        showToast("Carrinho limpo.", 'success');
      } catch (err) {
        showToast(`Falha ao limpar carrinho: ${err.message}`, "danger");
      } finally {
        clearCartBtn.disabled = false;
        clearCartBtn.innerHTML = originalLabel;
      }
    });
  }
  if (closeCart && cartOverlay) {
    closeCart.addEventListener("click", () => cartOverlay.classList.add("d-none"));
  }
  if (closeConfirm && confirmOverlay) {
    closeConfirm.addEventListener("click", () => confirmOverlay.classList.add("d-none"));
  }
  if (saveOrderBtn) {
    saveOrderBtn.addEventListener("click", async () => {

      saveOrderBtn.disabled = true;
      saveOrderBtn.innerHTML = 'aguarde...';

      const resetSaveBtn = () => {
        saveOrderBtn.disabled = false;
        saveOrderBtn.innerHTML = 'Salvar';
      };

      const paymentSelectSource = (isRevision && typeof confirmPaymentSelect !== "undefined" && confirmPaymentSelect)
        ? confirmPaymentSelect
        : paymentSelect;
      const paymentOpt = paymentSelectSource?.selectedOptions?.[0];
      const paymentIdTipo2 = paymentOpt?.dataset?.idTipo2 || "";
      const paymentIdSelected = paymentOpt?.dataset?.idTipo1 || paymentOpt?.value || "";
      
      const cartItems = await fetchCartItems(false);
      try {
        const proposalText = buildProposalClipboardText(cartItems);
        await copyToClipboard(proposalText);
        showToast("Resumo da proposta copiado para a área de transferência.", "success");
      } catch (copyErr) {
        showToast("Não foi possível copiar o resumo da proposta.", "warning");
      }

      const products = await Promise.all(
        cartItems.map(async (it, idx) => {
          const qty = Number(it.quantity) || 1;
          const discount = Math.max(0, Number(it.discount_percent) || 0);
          const originalPrice = Number(it.price) || 0;
          const unitPrice = Number(it.final_price) || 0;
          const prodInfo = await fetchProductByCode(it.product_code);
          return {
            code: it.product_code,
            product_id: prodInfo?.id || null,
            group_id: prodInfo?.group_id || null,
            color_id: Number(it.color) || null,
            color_name: resolveColorName(it.color) || "",
            quantity: qty,
            original_price: originalPrice,
            unit_price: unitPrice,
            discount_percent: discount,
            total: unitPrice * qty,
            ordination: idx,
          };
        })
      );

      const ownerId = getOwnerId() ? Number(getOwnerId()) : null;
      
      // Em modo consulta ou revisão, busca dos campos de confirmação
      const useConfirmFields = isRevision || isConsultMode;
      
      const nomeClienteValue = useConfirmFields
        ? (confirmRevendaInput?.value || "")
        : (revendaInput?.value || "");
      const contactIdValue = useConfirmFields
        ? (confirmRevendaIdHidden?.value || "")
        : (revendaIdHidden?.value || "");
      const personIdValue = useConfirmFields
        ? (confirmContatoIdHidden?.value || "")
        : (contatoIdHidden?.value || "");
      const ufValue = useConfirmFields
        ? (confirmUfIdHidden?.value || "")
        : (ufIdHidden?.value || "");
      const paymentName = paymentOpt?.dataset?.label || "";

      const payload = {
        nomeCliente: lastFormState?.revenda || String(nomeClienteValue).trim(),
        ContactId: contactIdValue ? Number(contactIdValue) : null,
        PersonId: personIdValue ? Number(personIdValue) : null,
        OwnerId: ownerId,
        PaymentId: lastFormState?.pagamentoId || Number(paymentIdSelected) || (paymentSelectSource?.value ? Number(paymentSelectSource.value) : null),
        PaymentIdTipo2: paymentIdTipo2 || lastFormState?.pagamentoIdTipo2 || null,
        PaymentName: lastFormState?.pagamentoNome || paymentName,
        notes: confirmNotes?.value?.trim() || "",
        products,
      };

      let dealId = null;
      if (isRevision) {
        dealId = revisionDealId;
        if (!dealId) {
          showToast("Falha ao obter DealId da proposta em revisão.", "danger");
          resetSaveBtn();
          return;
        }
      } else {
        // 1) Cria a Deal primeiro
        const dealResp = await createPloomesDeal(payload);
        dealId = dealResp?.deal_id || dealResp?.DealId || dealResp?.Id || dealResp?.id;
        if (!dealId) {
          showToast("Falha ao obter DealId para criar a proposta.", "danger");
          resetSaveBtn();
          return;
        }
      }

      // Payload simplificado que o backend transforma para o formato final do Ploomes
      const quotePayload = {
        DealId: dealId,
        OwnerId: payload.OwnerId,
        PaymentId: payload.PaymentId,
        PaymentIdTipo2: payload.PaymentIdTipo2,
        paymentName: payload.PaymentName,
        uf: ufValue,
        observacao: payload.notes,
        PersonId: isRevision ? revisionPersonId : null,
        products,
      };

      try {
        const url = isRevision && revisionQuoteId
          ? `/api/ploomes/quotes/${revisionQuoteId}/review/`
          : "/api/ploomes/quotes/create/";

        const res = await fetch(url, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(quotePayload),
        });
        const data = await res.json().catch(() => ({}));

        if (!res.ok) {
          const detail = data?.detail || `Erro ${res.status}`;
          showToast(isRevision ? `Falha ao revisar proposta: ${detail}` : `Falha ao criar proposta: ${detail}`, "danger");
          resetSaveBtn();
          return;
        }
        showToast(isRevision ? "Revisão feita com sucesso." : "Ordem e proposta criadas com sucesso.", "success");
        setTimeout(() => {
          window.location.href = "/";
        }, 500);
      } catch (err) {
        showToast(isRevision ? `Falha ao revisar proposta: ${err.message}` : `Falha ao criar proposta: ${err.message}`, "danger");
        resetSaveBtn();
      }

      resetSaveBtn();

    });
  }

  async function initRevisionMode() {
    if (!isRevision) return;
    
    // Mostrar spinner de carregamento
    if (loadingOverlay) {
      loadingOverlay.classList.remove("d-none");
      loadingOverlay.style.display = "flex";
    }
    
    // Esconder a seção do formulário em modo de revisão
    if (formSection) {
      formSection.classList.add("d-none");
    }
    
    try {
      setLoading(true);
      const quoteId = revisionQuoteId;

      // Executar loadCatalog e fetch de quote details em PARALELO
      // Estas operações são independentes e podem rodar simultaneamente
      const profileId = getProfileId();
      const allowAll = profileId === 1;
      const userLists = allowAll ? [] : getAllowedPriceLists();
      setAllowedPriceLists(userLists);

      const [catalogResult, quoteDetailResult] = await Promise.allSettled([
        loadCatalog(userLists, allowAll),
        fetch(`/api/ploomes/quote-detail/?quote_id=${quoteId}`)
          .then(resp => {
            console.log("Resposta /api/ploomes/quote-detail/ - Status:", resp.status, resp.statusText);
            return resp.json().then(detail => {
              console.log("Resposta /api/ploomes/quote-detail/ - JSON:", detail);
              return { resp, detail };
            });
          })
      ]);

      console.log("quoteDetailResult:", quoteDetailResult);

      // Processar resultado do catálogo
      if (catalogResult.status === 'fulfilled') {
        catalogSection.classList.remove("d-none");
      } else {
        console.error("Erro ao carregar catálogo:", catalogResult.reason);
        showToast("Erro ao carregar o catálogo de produtos.", "warning");
      }

      // Processar resultado dos detalhes da cotação
      if (quoteDetailResult.status === 'fulfilled') {
        const { resp, detail } = quoteDetailResult.value;
        console.log("Detalhes da cotação processados:", { resp, detail });
        // Os dados principais estão em detail.quote
        const quote = detail.quote || {};
        console.log("Produtos da cotação:", detail.products);
        if (resp.ok) {
          // Carregar produtos da cotação
          await loadQuoteProducts(detail.products || []);
          cartFloatingBtn.classList.remove("d-none");

          // Guardar DealId para submissão da revisão
          revisionDealId = quote?.DealId || quote?.deal_id || null;
          revisionPersonId = quote?.PersonId || null;

          // Preencher campos do formulário de confirmação com dados da cotação
          if (quote.ContactName && confirmRevendaInput) {
            confirmRevendaInput.value = quote.ContactName;
            if (quote.ContactId && confirmRevendaIdHidden) {
              confirmRevendaIdHidden.value = quote.ContactId;
              suggestionMap.set(quote.ContactName, quote.ContactId);

              const ownerId = getOwnerId();
              if (ownerId) await fetchContatos(quote.ContactId, ownerId, { showDropdown: false });
              confirmContatoInput.disabled = false;
              if (!isRevision) {
                renderContatoDropdownItems(
                  confirmContatoDropdown,
                  contactOptions,
                  ({ name, id }) => {
                    if (confirmContatoInput) confirmContatoInput.value = name || "";
                    if (confirmContatoIdHidden) confirmContatoIdHidden.value = id ? String(id) : "";
                    clearContatoDropdown(confirmContatoDropdown);
                  }
                );
              } else {
                clearContatoDropdown(confirmContatoDropdown);
              }

              await fetchPaymentOptions(quote.ContactId);
              
              // Aguarda um pouco para garantir que as opções foram renderizadas
              await new Promise(resolve => setTimeout(resolve, 100));
              
              confirmPaymentSelect.innerHTML = paymentSelect.innerHTML;
              confirmPaymentSelect.disabled = false;

              // Faz o match do pagamento usando o ID (PaymentId)
              // O PaymentId é o identificador único e confiável
              if ((quote.PaymentId || quote.PaymentId1) && confirmPaymentSelect) {
                const paymentId = String(quote.PaymentId || quote.PaymentId1);
                const options = Array.from(confirmPaymentSelect.options);
                
                console.log("Tentando encontrar pagamento por ID:", { 
                  paymentId,
                  PaymentId: quote.PaymentId,
                  PaymentId1: quote.PaymentId1 
                });

                // Procura a opção que corresponde ao ID
                const matchingOption = options.find(opt => {
                  const optValue = (opt.value || "").trim();
                  return optValue === paymentId;
                });

                if (matchingOption) {
                  confirmPaymentSelect.value = matchingOption.value;
                  console.log("✓ Pagamento encontrado por ID:", { 
                    value: matchingOption.value,
                    text: matchingOption.textContent
                  });
                  
                  if (quote.PaymentId2 && confirmPaymentIdTipo2Hidden) {
                    confirmPaymentIdTipo2Hidden.value = quote.PaymentId2;
                  }
                  confirmPaymentSelect.dispatchEvent(new Event("change"));
                } else {
                  console.warn(`✗ Pagamento não encontrado com ID: "${paymentId}"`);
                  console.log("IDs disponíveis no select:", options.map(o => o.value).filter(v => v));
                }
              } else {
                console.warn("Nenhum PaymentId disponível na cotação");
              }
            }
          }

          if (quote.PersonName && confirmContatoInput) {
            confirmContatoInput.value = quote.PersonName;
            if (quote.PersonId && confirmContatoIdHidden) {
              confirmContatoIdHidden.value = quote.PersonId;
              contactMap.set(quote.PersonName, quote.PersonId);
            }
          }

          // Preenche o campo de observações
          if (quote.Notes && confirmNotes) {
            confirmNotes.value = quote.Notes;
            console.log("✓ Observações carregadas:", quote.Notes);
          }
        } else {
          console.error("Resposta não OK:", resp.status);
          showToast("Erro ao carregar detalhes da cotação.", "warning");
        }
      } else {
        console.error("Erro ao buscar detalhes da cotação:", quoteDetailResult.reason);
        showToast(`Falha ao carregar itens da revisão: ${quoteDetailResult.reason?.message || 'Erro desconhecido'}`, "danger");
      }

    } catch (err) {
      console.error("Erro ao aplicar revisão", err);
      showToast("Erro ao carregar a revisão. Por favor, tente novamente.", "danger");
    } finally {
      setLoading(false);
      
      // Esconder spinner após tudo carregar
      if (loadingOverlay) {
        loadingOverlay.style.display = "none";
        loadingOverlay.classList.add("d-none");
      }
      
      // Mostrar campos de formulário no painel de confirmação
      const confirmFormFields = document.getElementById("confirmFormFields");
      if (confirmFormFields) {
        confirmFormFields.classList.remove("d-none");
      }
      
      // Não abrir automaticamente o painel de confirmação em modo de revisão
      // (Removido conforme solicitado)
    }
  }

  // Elementos do formulário de confirmação (revisão)
  const confirmRevendaInput = document.getElementById("confirmRevendaNome");
  const confirmRevendaList = document.getElementById("confirmRevendaOptions");
  const confirmRevendaIdHidden = document.getElementById("confirmRevendaId");
  const confirmUfIdHidden = document.getElementById("confirmUfId");
  const confirmContatoInput = document.getElementById("confirmRevendaContato");
  const confirmContatoDropdown = document.getElementById("confirmRevendaContatoDropdown");
  const confirmContatoIdHidden = document.getElementById("confirmRevendaContatoId");
  const confirmPaymentSelect = document.getElementById("confirmPaymentSelect");
  const confirmPaymentIdHidden = document.getElementById("confirmFormaPagamentoId");
  const confirmPaymentIdTipo2Hidden = document.getElementById("confirmFormaPagamentoIdTipo2");

  // Event listeners para o formulário de confirmação (revisão)
  let confirmDebounceTimeout;
  if (confirmRevendaInput) {
    confirmRevendaInput.disabled = isRevision; // Desabilita em modo revisão

    confirmRevendaInput.addEventListener("input", () => {
      const term = confirmRevendaInput.value.trim();
      confirmRevendaIdHidden.value = "";
      if (confirmUfIdHidden) confirmUfIdHidden.value = "";
      confirmContatoInput.value = "";
      confirmContatoIdHidden.value = "";
      clearContatoDropdown(confirmContatoDropdown);
      confirmContatoInput.disabled = true;

      // Se o campo for apagado, resetar/desabilitar o select de pagamento
      if (!term && confirmPaymentSelect) {
        confirmPaymentSelect.innerHTML = '<option value="">Selecione uma revenda</option>';
        confirmPaymentSelect.value = "";
        confirmPaymentSelect.disabled = true;
        if (confirmPaymentIdHidden) confirmPaymentIdHidden.value = "";
        if (confirmPaymentIdTipo2Hidden) confirmPaymentIdTipo2Hidden.value = "";
      }

      if (confirmDebounceTimeout) clearTimeout(confirmDebounceTimeout);
      if (term && term.length >= 2) {
        confirmDebounceTimeout = setTimeout(() => {
          const ownerId = getOwnerId();
          if (!ownerId) return;
          
          // Renderizar "Carregando..." no dropdown
          const confirmRevendaDropdown = document.getElementById("confirmRevendaNomeDropdown");
          if (confirmRevendaDropdown) {
            confirmRevendaDropdown.innerHTML = '<div class="list-group-item text-secondary">Carregando...</div>';
            confirmRevendaDropdown.classList.remove("d-none");
          }
          
          // Passa o dropdown de destino para renderização direta
          fetchRevendas(term, ownerId, confirmRevendaDropdown).then(() => {
            // Copiar opções para o datalist de confirmação (se existir)
            if (confirmRevendaList && revendaList) {
              confirmRevendaList.innerHTML = revendaList.innerHTML;
            }
            
            // Adicionar event listeners aos botões do dropdown
            if (confirmRevendaDropdown) {
              confirmRevendaDropdown.querySelectorAll("button").forEach(btn => {
                btn.addEventListener("mousedown", (ev) => {
                  ev.preventDefault();
                  const name = btn.dataset.name || "";
                  const id = btn.dataset.id || "";
                  const uf = btn.dataset.uf || "";
                  
                  if (confirmRevendaInput) confirmRevendaInput.value = name;
                  if (confirmRevendaIdHidden) confirmRevendaIdHidden.value = id;
                  if (confirmUfIdHidden) confirmUfIdHidden.value = uf;
                  
                  suggestionMap.set(name, id);
                  confirmRevendaDropdown.innerHTML = "";
                  confirmRevendaDropdown.classList.add("d-none");
                  
                  // Trigger change event
                  if (confirmRevendaInput) {
                    confirmRevendaInput.dispatchEvent(new Event("change"));
                  }
                });
              });
            }
          });
        }, 250);
      } else {
        // Limpar dropdown se o termo for muito curto
        const confirmRevendaDropdown = document.getElementById("confirmRevendaNomeDropdown");
        if (confirmRevendaDropdown) {
          confirmRevendaDropdown.innerHTML = "";
          confirmRevendaDropdown.classList.add("d-none");
        }
      }
    });

    // Esconder dropdown ao sair do campo
    confirmRevendaInput.addEventListener("blur", () => {
      setTimeout(() => {
        const confirmRevendaDropdown = document.getElementById("confirmRevendaNomeDropdown");
        if (confirmRevendaDropdown) {
          confirmRevendaDropdown.classList.add("d-none");
        }
      }, 150);
    });

    // Mostrar dropdown ao focar novamente se já houver resultados
    confirmRevendaInput.addEventListener("focus", () => {
      const confirmRevendaDropdown = document.getElementById("confirmRevendaNomeDropdown");
      if (confirmRevendaDropdown && confirmRevendaDropdown.children.length) {
        confirmRevendaDropdown.classList.remove("d-none");
      }
    });

    confirmRevendaInput.addEventListener("change", () => {
      const name = confirmRevendaInput.value.trim();
      const id = suggestionMap.get(name);
      if (confirmRevendaIdHidden) confirmRevendaIdHidden.value = id ? id : "";
      if (confirmUfIdHidden) {
        let uf = "";
        if (revendaList && revendaList.options) {
          Array.from(revendaList.options).forEach((opt) => {
            if (opt.value === name) {
              uf = opt.dataset.uf || "";
            }
          });
        }
        confirmUfIdHidden.value = uf;
      }
      if (confirmContatoInput) confirmContatoInput.value = "";
      if (confirmContatoIdHidden) confirmContatoIdHidden.value = "";
      clearContatoDropdown(confirmContatoDropdown);
      if (confirmContatoInput) confirmContatoInput.disabled = true;
      if (id) {
        const ownerId = getOwnerId();
        if (ownerId) {
          const shouldAutoOpen = !isRevision;
          fetchContatos(id, ownerId, { showDropdown: shouldAutoOpen }).then(() => {
            if (confirmContatoInput) confirmContatoInput.disabled = false;
            if (shouldAutoOpen) {
              renderContatoDropdownItems(
                confirmContatoDropdown,
                contactOptions,
                ({ name, id }) => {
                  if (confirmContatoInput) confirmContatoInput.value = name || "";
                  if (confirmContatoIdHidden) confirmContatoIdHidden.value = id ? String(id) : "";
                  clearContatoDropdown(confirmContatoDropdown);
                }
              );
            } else {
              clearContatoDropdown(confirmContatoDropdown);
            }
          });
          fetchPaymentOptions(id, confirmPaymentSelect).then(() => {
            // Em modo consulta, não há paymentSelect para copiar
            // As opções já foram renderizadas diretamente no confirmPaymentSelect
          });
        }
      }
    });
  }

  if (confirmContatoInput) {
    attachContatoDropdownBehavior(
      confirmContatoInput,
      confirmContatoDropdown,
      ({ name, id }) => {
        if (confirmContatoInput) confirmContatoInput.value = name || "";
        if (confirmContatoIdHidden) confirmContatoIdHidden.value = id ? String(id) : "";
        clearContatoDropdown(confirmContatoDropdown);
      }
    );
    confirmContatoInput.addEventListener("change", () => {
      const name = confirmContatoInput.value.trim();
      const id = contactMap.get(name);
      confirmContatoIdHidden.value = id ? id : "";
    });
  }

  if (confirmPaymentSelect) {
    confirmPaymentSelect.addEventListener("change", () => {
      if (confirmPaymentIdHidden) {
        const opt = confirmPaymentSelect.selectedOptions?.[0];
        confirmPaymentIdHidden.value = opt?.dataset?.idTipo1 || confirmPaymentSelect.value || "";
      }
      if (confirmPaymentIdTipo2Hidden) {
        const opt = confirmPaymentSelect.selectedOptions?.[0];
        confirmPaymentIdTipo2Hidden.value = opt?.dataset?.idTipo2 || "";
      }
    });
  }

  let debounceTimeout;
  if (revendaInput) {
    revendaInput.addEventListener("input", () => {
      const term = revendaInput.value.trim();
      if (revendaIdHidden) revendaIdHidden.value = "";
      if (ufIdHidden) ufIdHidden.value = "";
      if (contatoInput) contatoInput.value = "";
      if (contatoIdHidden) contatoIdHidden.value = "";
      contactMap.clear();
      contactOptions = [];
      if (contatoInput) contatoInput.disabled = true;
      clearContatoDropdown(contatoDropdown);
      resetPaymentSelect();

      if (!term || term.length < 2) {
        clearRevendaDropdown();
        if (debounceTimeout) clearTimeout(debounceTimeout);
        return;
      }

      renderRevendaDropdownMessage("Carregando...");
      if (debounceTimeout) clearTimeout(debounceTimeout);
      debounceTimeout = setTimeout(() => {
        const ownerId = form?.owner_id?.value || document.querySelector('[name="owner_id"]')?.value;
        if (ownerId) {
          fetchRevendas(term, ownerId).catch(() => {
            renderRevendaDropdownMessage("Falha ao buscar revendas");
          });
        }
      }, 250);
    });

    // Esconde a lista ao sair do campo (com pequeno delay para permitir clique)
    revendaInput.addEventListener("blur", () => {
      setTimeout(() => {
        clearRevendaDropdown();
      }, 150);
    });

    // Mostra novamente se já houver resultados no dropdown
    revendaInput.addEventListener("focus", () => {
      if (revendaDropdown && revendaDropdown.children.length) {
        setRevendaDropdownVisible(true);
      }
    });
  }

  if (contatoInput) {
    contatoInput.addEventListener("change", () => {
      const name = contatoInput.value.trim();
      const id = contactMap.get(name);
      if (contatoIdHidden) contatoIdHidden.value = id ? id : "";
    });
    
    attachContatoDropdownBehavior(contatoInput, contatoDropdown, selectContato);
  }

  // Estado inicial
  if (revendaDropdown) {
    clearRevendaDropdown();
  }

  if (priceListFilter) {
    priceListFilter.addEventListener("change", renderTable);
  }
  if (catalogSearch) {
    let searchTimeout;
    catalogSearch.addEventListener("input", () => {
      if (searchTimeout) clearTimeout(searchTimeout);
      searchTimeout = setTimeout(() => {
        renderTable();
      }, 250);
    });
  }
  Object.values(filters).forEach((el) => {
    if (el) el.addEventListener("input", renderTable);
  });
  
  if (paymentSelect) {
    paymentSelect.addEventListener("change", () => {
      if (!paymentIdHidden) return;
      const selVal = paymentSelect.value || "";
      const opt = paymentSelect.selectedOptions?.[0];
      paymentIdHidden.value = opt?.dataset?.idTipo1 || selVal;
    });
    paymentSelect.addEventListener("change", () => {
      if (!paymentIdTipo2Hidden) return;
      const selVal = paymentSelect.value || "";
      const opt = paymentSelect.selectedOptions?.[0];
      paymentIdTipo2Hidden.value = opt?.dataset?.idTipo2 || selVal;
    });
  }
  if (btnVoltarButtons.length) {
    btnVoltarButtons.forEach((btnVoltar) => {
      btnVoltar.addEventListener("click", () => {
        if (filters.modelo?.value) {
          filters.modelo.value = "";

          Object.entries(filters).forEach(([key, filter]) => {
            if (key !== "categoria" && key !== "modeloSimples") {
              filter.value = "";
            }
          });
        } else if (filters.categoria?.value) {
          filters.categoria.value = "";
          filters.modelo.value = "";
          Object.entries(filters).forEach(([key, filter]) => {
            if (key !== "modeloSimples") {
              filter.value = "";
            }
          });
        } else {
          filters.modeloSimples.value = "";
          Object.entries(filters).forEach(([key, filter]) => {
            filter.value = "";
          });
        }

        toggleSelectVisibility();
        updateBackButton();
      renderTable();
      });
    });
  }

  async function getFavoritesCached(listCode) {
    const key = listCode || "";
    if (favoritesCache.has(key)) return favoritesCache.get(key);
    const favorites = await fetchFavoriteItens(listCode);
    favoritesCache.set(key, favorites);
    return favorites;
  }

  function renderModalFilters(optionSets) {
    if (!filtrosModalBody) return;
    const config = [
      { key: "eixo", label: "Eixo" },
      { key: "mola", label: "Mola" },
      { key: "freio", label: "Freio" },
      { key: "capacidade", label: "Capacidade" },
      { key: "tamanho", label: "Tamanho" },
      { key: "rodado", label: "Rodado" },
      { key: "pneu", label: "Pneu" },
      { key: "opcionais", label: "Opcionais" },
    ];

    filtrosModalBody.innerHTML = "";

    // Adicionar botão de limpar todos os filtros
    const clearAllDiv = document.createElement("div");
    clearAllDiv.className = "col-12 mb-3";
    clearAllDiv.innerHTML = `
      <button type="button" class="btn btn-outline-danger w-100 clear-all-filters">
        <i class="bi bi-x-circle"></i> Limpar todos os filtros
      </button>
    `;
    filtrosModalBody.appendChild(clearAllDiv);

    config.forEach(({ key, label }) => {
      const baseValues = Array.from(optionSets[key] || []).sort((a, b) => a.localeCompare(b));
      const values = baseValues.length
        ? baseValues
        : key === "mola" || key === "freio"
          ? ["sim", "nao"]
          : baseValues;

      const currentVal = filters[key]?.value || "";
      const col = document.createElement("div");
      col.className = "col-md-6";
      const chips = values
        .map((val) => {
          const isActive = currentVal === val;
          return `
            <button type="button" class="btn btn-sm ${isActive ? "btn-primary" : "btn-outline-secondary"} me-2 mb-2 filtro-chip" data-key="${key}" data-value="${val}">
              ${val ? val.charAt(0).toUpperCase() + val.slice(1) : "Todos"}
            </button>
          `;
        })
        .join("");

      col.innerHTML = `
        <div class="border rounded-3 p-3 h-100">
          <div class="d-flex justify-content-between align-items-center mb-2">
            <span class="fw-semibold">${label}</span>
            <button type="button" class="btn btn-link btn-sm text-secondary reset-filter" data-key="${key}">Limpar</button>
          </div>
          <div>${chips || "<small class='text-secondary'>Nenhuma opçao</small>"}</div>
        </div>
      `;
      filtrosModalBody.appendChild(col);
    });

    // Event listener para botão "Limpar todos os filtros"
    const clearAllBtn = filtrosModalBody.querySelector(".clear-all-filters");
    if (clearAllBtn) {
      clearAllBtn.addEventListener("click", () => {
        Object.entries(filters).forEach(([key, filter]) => {
          // Não limpa categoria e modelo
          if (key !== "categoria" && key !== "modelo") {
            filter.value = "";
          }
        });
        renderTable();
      });
    }

    filtrosModalBody.querySelectorAll(".filtro-chip").forEach((btn) => {
      btn.addEventListener("click", () => {
        const key = btn.dataset.key;
        const val = btn.dataset.value || "";
        if (filters[key]) {
          filters[key].value = val;
          renderTable();
        }
      });
    });

    filtrosModalBody.querySelectorAll(".reset-filter").forEach((btn) => {
      btn.addEventListener("click", () => {
        const key = btn.dataset.key;
        if (filters[key]) {
          filters[key].value = "";
          renderTable();
        }
      });
    });
  }
  if (btnToggleFiltros && filtrosModal) {
    btnToggleFiltros.addEventListener("click", () => {
      const modal = bootstrap.Modal.getOrCreateInstance(filtrosModal, { backdrop: false, keyboard: true });
      modal.show();
    });
  }

  // Inicializa modo consulta ou revisão
  if (isConsultMode) {
    // Modo "Consultar Preço" - mostra o catálogo logo de cara
    if (loadingOverlay) {
      loadingOverlay.classList.remove("d-none");
      loadingOverlay.style.display = "flex";
    }
    if (formSection) {
      formSection.classList.add("d-none");
    }
    
    // Carrega o catálogo apenas com as listas do usuário
    const profileId = getProfileId();
    const allowAll = profileId === 1;
    const userLists = allowAll ? [] : getAllowedPriceLists();
    setAllowedPriceLists(userLists);
    loadCatalog(userLists, allowAll)
      .then(() => {
        catalogSection.classList.remove("d-none");
        if (loadingOverlay) {
          loadingOverlay.style.display = "none";
          loadingOverlay.classList.add("d-none");
        }
      })
      .catch((err) => {
        console.error("Erro ao carregar catálogo:", err);
        showToast("Erro ao carregar catálogo de produtos.", "danger");
        if (loadingOverlay) {
          loadingOverlay.style.display = "none";
          loadingOverlay.classList.add("d-none");
        }
      });
  } else if (isRevision) {
    initRevisionMode();
  }

  // Carrega carrinho existente ao abrir a página
  fetchCartItems(false);

  resetPaymentSelect();
  
  // Apenas adiciona listener no form se não estiver em modo consulta
  if (form && !isConsultMode) {
    form.addEventListener("submit", submitQuote);
  }
})();

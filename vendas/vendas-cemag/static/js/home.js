(() => {
  if (window.__homeScrollHandler) {
    window.removeEventListener("scroll", window.__homeScrollHandler);
    window.__homeScrollHandler = null;
  }

  const elements = {
    cards: document.getElementById("cardsContainer"),
    alert: document.getElementById("alertArea"),
    loadBtn: document.getElementById("loadBtn"),
    refreshBtn: document.getElementById("refreshBtn"),
    login: document.getElementById("inputLogin"),
    status: document.getElementById("statusFilter"),
    aceiteExterno: document.getElementById("aceiteExternoFilter"),
    aprovacaoDesconto: document.getElementById("aprovacaoDescontoFilter"),
    revenda: document.getElementById("revendaFilter"),
    deliveryDeadlineStatusAvulsa: document.getElementById("deliveryDeadlineStatusAvulsa"),
    deliveryDeadlineStatusFechada: document.getElementById("deliveryDeadlineStatusFechada"),
    deliveryDeadlineAvulsa: document.getElementById("deliveryDeadlineAvulsa"),
    deliveryDeadlineFechada: document.getElementById("deliveryDeadlineFechada"),
    // totalDeals: document.getElementById("metricTotal"),
    // totalAmount: document.getElementById("metricAmount"),
    openDeals: document.getElementById("metricOpen"),
    spinner: document.getElementById("spinnerArea"),
    contactModal: document.getElementById("contactModal"),
    contactModalSelect: document.getElementById("contactModalSelect"),
    contactModalSave: document.getElementById("contactModalSave"),
    contactModalSpinner: document.getElementById("contactModalSpinner"),
    contactModalEmpty: document.getElementById("contactModalEmpty"),
    winDealModal: document.getElementById("winDealModal"),
    winDealClient: document.getElementById("winDealClient"),
    winDealContact: document.getElementById("winDealContact"),
    winDealAmount: document.getElementById("winDealAmount"),
    winDealPayment: document.getElementById("winDealPayment"),
    winDealConfirm: document.getElementById("winDealConfirm"),
    loseDealModal: document.getElementById("loseDealModal"),
    loseDealReasonSelect: document.getElementById("loseDealReasonSelect"),
    loseDealConfirm: document.getElementById("loseDealConfirm"),
  };

  const statusLabels = {
    1: { text: "Aberto", cls: "badge-open" },
    2: { text: "Ganho", cls: "badge-won" },
    3: { text: "Perdido", cls: "badge-lost" },
  };
  const contactsCache = new Map();
  const bootstrapModal = elements.contactModal ? new bootstrap.Modal(elements.contactModal) : null;
  const winDealBootstrapModal = elements.winDealModal ? new bootstrap.Modal(elements.winDealModal) : null;
  const loseDealBootstrapModal = elements.loseDealModal ? new bootstrap.Modal(elements.loseDealModal) : null;
  let modalState = { companyId: null, targetCard: null, selectedId: null, dealId: null };
  let winDealState = { dealId: null, quoteId: null, targetCard: null };
  let loseDealState = { dealId: null, targetCard: null };

  function formatIsoDateToBr(value) {
    if (!value) return "--/--/----";
    const dt = new Date(value);
    if (Number.isNaN(dt.getTime())) return "--/--/----";
    return dt.toLocaleDateString("pt-BR");
  }

  async function fetchDeliveryDeadline() {
    if (!elements.deliveryDeadlineStatusAvulsa || !elements.deliveryDeadlineStatusFechada) return;
    elements.deliveryDeadlineStatusAvulsa.textContent = "Carregando";
    elements.deliveryDeadlineStatusAvulsa.className = "badge bg-secondary status-chip";
    elements.deliveryDeadlineStatusFechada.textContent = "Carregando";
    elements.deliveryDeadlineStatusFechada.className = "badge bg-secondary status-chip";
    try {
      const response = await fetch("/api/programacao/prazo-entrega/", { headers: { Accept: "application/json" } });
      const data = await response.json();
      if (!response.ok) throw new Error(data?.detail || `Erro ${response.status}`);

      const prazoAvulsa = formatIsoDateToBr(data.prazo_carreta_avulsa);
      const prazoFechada = formatIsoDateToBr(data.prazo_carga_fechada);

      if (elements.deliveryDeadlineAvulsa) {
        elements.deliveryDeadlineAvulsa.textContent = `Para carretas avulsas, o prazo de entrega é: ${prazoAvulsa}.`;
      }
      if (elements.deliveryDeadlineFechada) {
        elements.deliveryDeadlineFechada.textContent = `Para cargas fechadas, o prazo de entrega é: ${prazoFechada}.`;
      }
      elements.deliveryDeadlineStatusAvulsa.textContent = "Atualizado";
      elements.deliveryDeadlineStatusAvulsa.className = "badge bg-success status-chip";
      elements.deliveryDeadlineStatusFechada.textContent = "Atualizado";
      elements.deliveryDeadlineStatusFechada.className = "badge bg-success status-chip";
    } catch (error) {
      if (elements.deliveryDeadlineAvulsa) {
        elements.deliveryDeadlineAvulsa.textContent = "Para carretas avulsas, o prazo de entrega é: indisponível.";
      }
      if (elements.deliveryDeadlineFechada) {
        elements.deliveryDeadlineFechada.textContent = "Para cargas fechadas, o prazo de entrega é: indisponível.";
      }
      elements.deliveryDeadlineStatusAvulsa.textContent = "Erro";
      elements.deliveryDeadlineStatusAvulsa.className = "badge bg-danger status-chip";
      elements.deliveryDeadlineStatusFechada.textContent = "Erro";
      elements.deliveryDeadlineStatusFechada.className = "badge bg-danger status-chip";
      console.error("Falha ao carregar prazo de entrega:", error);
    }
  }

  async function fetchContactsByCompany(companyId) {
    if (!companyId) return [];
    if (contactsCache.has(companyId)) return contactsCache.get(companyId);
    try {
      const owner = elements.login?.dataset?.owner || elements.login?.value || "";
      const url = `/api/ploomes/contacts-company/?company_id=${companyId}${owner ? `&owner=${owner}` : ""}`;
      const res = await fetch(url, { headers: { Accept: "application/json" } });
      if (!res.ok) return [];
      const data = await res.json();
      const results = data.results || [];
      contactsCache.set(companyId, results);
      return results;
    } catch (_) {
      return [];
    }
  }

  const PAGE_SIZE = 10;
  let currentDeals = [];
  let currentSkip = 0;
  let hasMore = true;
  let isLoading = false;

  async function fetchQuotes(reset = false) {
    if (!elements.login || !elements.cards) return;
    if (isLoading) return;
    const idLogin = elements.login.value.trim();
    if (!idLogin) {
      showToast("Informe o Login (OwnerId).", "warning");
      return;
    }
    if (reset) {
      currentSkip = 0;
      hasMore = true;
      currentDeals = [];
      elements.cards.innerHTML = "";
    }
    const params = new URLSearchParams({
      owner_id: idLogin,
      top: PAGE_SIZE,
      skip: currentSkip,
      status: elements.status.value,
      aceite: elements.aceiteExterno.value,
      aprovacao: elements.aprovacaoDesconto.value,
      revenda: elements.revenda.value.trim(),
    });
    clearAlert();
    isLoading = true;
    setLoading(true);
    try {
      const res = await fetch(`/api/ploomes/quotes/?${params.toString()}`);
      if (!res.ok) throw new Error(`Erro ${res.status}: ${res.statusText}`);
      const data = await res.json();
      console.log(data);
      const newDeals = Array.isArray(data.value) ? data.value : [];
      currentDeals = reset ? newDeals : currentDeals.concat(newDeals);
      if (newDeals.length < PAGE_SIZE) {
        hasMore = false;
      } else {
        currentSkip += PAGE_SIZE;
      }
      renderMetrics(currentDeals);
      renderCards(currentDeals);
    } catch (error) {
      showToast(`Falha ao buscar cotações: ${error.message}`, "danger");
      if (reset) {
        currentDeals = [];
        renderMetrics(currentDeals);
        renderCards([]);
      }
    } finally {
      isLoading = false;
      setLoading(false);
    }
  }

  function renderMetrics(deals) {
    if (!elements.openDeals) return;

    const total = deals.length;
    const totalAmount = deals.reduce((sum, d) => sum + (d.Amount || 0), 0);
    const open = deals.filter((d) => (d.Deal?.StatusId ?? 0) === 1).length;
    const openAmount = deals.reduce((sum, d) => (d.Deal?.StatusId === 1 ? sum + (d.Amount || 0) : sum), 0);
    const now = new Date();
    const currentMonth = now.getMonth();
    const currentYear = now.getFullYear();
    const wonMonth = deals.filter((d) => {
      if (d.Deal?.StatusId !== 2 || !d.CreateDate) return false;
      const dt = new Date(d.CreateDate);
      return dt.getMonth() === currentMonth && dt.getFullYear() === currentYear;
    });
    const wonMonthAmount = wonMonth.reduce((sum, d) => sum + (d.Amount || 0), 0);
    const wonMonthCount = wonMonth.length;

    // elements.totalDeals.textContent = total;
    // elements.totalAmount.textContent = `R$ ${totalAmount.toLocaleString("pt-BR", { minimumFractionDigits: 2 })}`;
    elements.openDeals.textContent = open;
    if (document.getElementById("metricOpenAmount"))
      document.getElementById("metricOpenAmount").textContent = `R$ ${openAmount.toLocaleString("pt-BR", {
        minimumFractionDigits: 2,
      })}`;
    if (document.getElementById("metricWonMonthAmount"))
      document.getElementById("metricWonMonthAmount").textContent = `R$ ${wonMonthAmount.toLocaleString("pt-BR", {
        minimumFractionDigits: 2,
      })}`;
    if (document.getElementById("metricWonMonthCount"))
      document.getElementById("metricWonMonthCount").textContent = wonMonthCount;
  }

  function renderCards(deals) {
    if (!elements.cards) return;
    elements.cards.innerHTML = "";
    if (!deals.length) {
      elements.cards.innerHTML = '<div class="col-12 text-center text-secondary">Nenhum resultado.</div>';
      return;
    }

    deals.forEach((deal) => {
      const contactName = deal.ContactName || deal.Deal?.PersonName || "--";
      const dealId = deal.DealId ?? "--";
      const reviewNumber = deal.ReviewNumber ?? deal.Deal?.ReviewNumber ?? "--";
      const amount = deal.Amount ?? 0;
      const createDate = new Date(deal.CreateDate).toLocaleDateString("pt-BR");
      const linkPDF = deal.DocumentUrl || "#";
      const contactId = deal.Deal?.PersonId;
      const personName = deal.Deal?.PersonName ?? "--";
      const companyId = deal.Deal?.ContactId ?? deal.ContactId ?? null;
      const statusId = deal.Deal?.StatusId ?? "--";
      const statusIdNum = Number(statusId);
      const status = statusLabels[statusId] || { text: "Outro", cls: "badge-other" };
      const externalAcceptedBool = deal.ExternallyAccepted === true;
      const externalAccepted = externalAcceptedBool ? "Sim" : "Não";
      const approvalRaw = deal.ApprovalStatusId;
      const approvalLabels = { 1: "Aguardando", 2: "Aprovado", null: "N/A" };
      const approvalStatus =
        approvalRaw === null ? approvalLabels[null] : approvalLabels[approvalRaw] || approvalRaw || "--";
      const linkAccepted = `https://documents.ploomes.com/?k=${deal.Key}&entity=quote`;
      const showWin = externalAcceptedBool && statusId !== 2 && statusId !== 3 && contactId !== null;
      const showLose = statusId !== 2 && statusId !== 3;
      const showReview = statusIdNum === 1;
      const showMirror = statusId === 2;
      const botaoAceiteHTML = (approvalRaw !== 1)
        ? `<a class="btn btn-sm btn-primary" href="${linkAccepted}" target="_blank">Ver Proposta</a>`
        : '';
      const card = document.createElement("div");
      card.className = "col-12 col-md-6 col-xl-4";
      card.innerHTML = `
        <div class="card h-100 deal-card">
          <div class="card-body d-flex flex-column gap-2">
            <div class="d-flex justify-content-between align-items-start">
              <div>
        <h5 class="card-title mb-1">${contactName}</h5>
        <div class="d-flex align-items-center gap-2 flex-wrap">
          <small class="muted contact-label ${!contactId ? "text-danger fw-semibold" : ""}" data-contact-id="${contactId}">
            ${contactId ? `${personName}` : "Contato obrigatorio!"}
          </small>
          <button type="button" class="btn btn-link btn-sm p-0 text-secondary text-decoration-none edit-contact-btn" data-company-id="${companyId || ""}" data-selected-id="${contactId}" data-deal-id="${dealId}">editar</button>
        </div>
              </div>
              <span class="badge status-chip ${status.cls}">${status.text}</span>
            </div>
            <div class="deal-meta">
              <span>Negocio #${dealId}</span>
              <span>Revisao ${reviewNumber}</span>
              <span>Criado em ${createDate}</span>
            </div>
            <div class="d-flex justify-content-between align-items-center">
              <span class="deal-amount">R$ ${amount.toLocaleString("pt-BR")}</span>
              <span class="muted">Aceite externo: <strong>${externalAccepted}</strong></span>
            </div>
            <div class="deal-info">
              <span class="muted">Aprovacao desc.: <strong>${approvalStatus}</strong></span>
            </div>
            <div class="d-flex gap-1 flex-wrap align-items-center deal-actions">
              ${botaoAceiteHTML}
              <a class="btn btn-sm btn-outline-light" href="${linkPDF}" target="_blank">PDF</a>
              ${showReview ? `<button class="btn btn-sm btn-outline-warning btn-review" data-quote-id="${deal.Id || deal.QuoteId || dealId}" data-company-id="${companyId || ""}" data-contact-id="${contactId || ""}" data-contact-name="${personName || contactName}" data-company-name="${contactName}">Revisar</button>` : ""}
              ${showLose ? `<button class="btn btn-sm btn-outline-danger btn-lose" data-deal-id="${dealId}">Perder</button>` : ""}
              ${showMirror ? `<button class="btn btn-sm btn-outline-info text-light btn-mirror" data-deal-id="${dealId}">Espelho</button>` : ""}
              <button class="btn btn-sm btn-success btn-win ${showWin ? "" : "d-none"}" data-deal-id="${dealId}" data-client-name="${contactName}" data-contact-name="${personName || 'N/A'}" data-amount="${amount.toLocaleString("pt-BR")}">Ganhar</button>
            </div>
          </div>
        </div>
      `;
      card.dataset.statusId = statusId;
      card.dataset.externalAccepted = externalAcceptedBool ? "1" : "0";
      elements.cards.appendChild(card);

      const editBtn = card.querySelector(".edit-contact-btn");
      if (editBtn && companyId && bootstrapModal) {
        editBtn.addEventListener("click", async () => {
          modalState = {
            companyId,
            targetCard: card,
            selectedId: editBtn.dataset.selectedId || "",
            dealId: editBtn.dataset.dealId || null,
          };
          elements.contactModalSelect.innerHTML = `<option value="">Selecione</option>`;
          elements.contactModalSpinner?.classList.remove("d-none");
          elements.contactModalEmpty?.classList.add("d-none");
          bootstrapModal.show();

          const contacts = await fetchContactsByCompany(companyId);
          elements.contactModalSpinner?.classList.add("d-none");
          if (!contacts.length) {
            elements.contactModalEmpty?.classList.remove("d-none");
            return;
          }
          contacts.forEach((c) => {
            const opt = document.createElement("option");
            opt.value = c.Id;
            opt.textContent = c.Name || c.Id;
            if (String(c.Id) === String(modalState.selectedId)) opt.selected = true;
            elements.contactModalSelect.appendChild(opt);
          });
        });
      }
    });
  }

  if (elements.contactModalSave && bootstrapModal) {
    elements.contactModalSave.addEventListener("click", async () => {
      elements.contactModalSave.innerHTML = 'aguarde...';
      elements.contactModalSave.disabled = true;

      const selected = elements.contactModalSelect.value;
      const selectedText = elements.contactModalSelect.selectedOptions?.[0]?.textContent || selected;
      if (modalState.targetCard && selected) {
        try {
          const res = await fetch("/api/ploomes/deals/update-contact/", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ deal_id: modalState.dealId, contact_id: Number(selected) }),
          });
          const data = await res.json();
          if (!res.ok) {
            const detail = data?.detail || `Erro ${res.status}`;
            showToast(`Falha ao atualizar contato: ${detail}`, "danger");
            return;
          }
          const label = modalState.targetCard.querySelector(".contact-label");
          if (label) {
            label.textContent = `Contato: ${selectedText}`;
            label.dataset.contactId = selected;
          }
          const btn = modalState.targetCard.querySelector(".edit-contact-btn");
          if (btn) btn.dataset.selectedId = selected;

          const winBtn = modalState.targetCard.querySelector(".btn-win");
          if (winBtn) {
            const stId = modalState.targetCard.dataset.statusId;
            const external = modalState.targetCard.dataset.externalAccepted === "1";
            const shouldShow = external && stId !== "2" && stId !== "3" && selected;
            winBtn.classList.toggle("d-none", !shouldShow);
          }
          if (label) {
            label.classList.remove("text-danger", "fw-semibold");
          }
          showToast("Contato atualizado com sucesso.", "success");

        } catch (err) {
          showToast(`Falha ao atualizar contato: ${err.message}`, "danger");
        } finally {
          elements.contactModalSave.innerHTML = 'Aplicar';
          elements.contactModalSave.disabled = false;
        }
      }
      bootstrapModal.hide();
      elements.contactModalSave.innerHTML = 'Aplicar';
      elements.contactModalSave.disabled = false;
    });
  }

  if (elements.winDealConfirm && winDealBootstrapModal) {
    elements.winDealConfirm.addEventListener("click", async () => {
      elements.winDealConfirm.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Confirmando...';
      elements.winDealConfirm.disabled = true;

      try {
        const res = await fetch("/api/ploomes/deals/win/", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ deal_id: winDealState.dealId }),
        });
        const data = await res.json();
        
        if (!res.ok) {
          const detail = data?.detail || `Erro ${res.status}`;
          showToast(`Falha ao ganhar negócio: ${detail}`, "danger");
          return;
        }

        if (winDealState.targetCard) {
          winDealState.targetCard.dataset.statusId = "2";
          const statusBadge = winDealState.targetCard.querySelector(".card-title .badge");
          if (statusBadge) {
            statusBadge.className = "badge badge-won";
            statusBadge.textContent = "Ganho";
          }
          const winBtn = winDealState.targetCard.querySelector(".btn-win");
          if (winBtn) {
            winBtn.classList.add("d-none");
          }
        }

        showToast("Negócio marcado como ganho com sucesso!", "success");

        // Criar venda após ganhar o deal
        try {
          const resCreateSale = await fetch("/api/ploomes/sales/create/", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ 
              deal_id: winDealState.dealId,
              quote_id: winDealState.quoteId
            }),
          });
          const saleData = await resCreateSale.json();
          
          if (!resCreateSale.ok) {
            const saleDetail = saleData?.detail || `Erro ${resCreateSale.status}`;
            showToast(`Aviso: Venda não pôde ser criada: ${saleDetail}`, "warning");
          } else {
            showToast("Venda criada com sucesso!", "success");
          }
        } catch (saleErr) {
          showToast(`Aviso: Erro ao criar venda: ${saleErr.message}`, "warning");
        }

        winDealBootstrapModal.hide();

      } catch (err) {
        showToast(`Falha ao ganhar negócio: ${err.message}`, "danger");
      } finally {
        elements.winDealConfirm.innerHTML = 'Confirmar';
        elements.winDealConfirm.disabled = false;
      }
    });
  }

  elements.cards.addEventListener("click", (e) => {
    const reviewBtn = e.target.closest(".btn-review");
    if (reviewBtn) {
      const quoteId = reviewBtn.dataset.quoteId;
      const companyId = reviewBtn.dataset.companyId;
      const companyName = reviewBtn.dataset.companyName;
      const contactId = reviewBtn.dataset.contactId;
      const contactName = reviewBtn.dataset.contactName;
      const paymentId = reviewBtn.dataset.paymentId;

      if (!quoteId) {
        showToast("Proposta sem ID para revisão.", "warning");
        return;
      }
      const payload = {
        quoteId,
        companyId,
        contactId,
        contactName,
        companyName,
      };
      localStorage.setItem("quoteReview", JSON.stringify(payload));
      window.location.href = "/quotes/create/?revision=1&quoteId=" + quoteId;
      return;
    }

    const winBtn = e.target.closest(".btn-win");
    if (winBtn && winDealBootstrapModal) {
      const card = winBtn.closest(".card");
      if (!card) return;

      const dealId = winBtn.dataset.dealId;
      const clientName = winBtn.dataset.clientName || "N/A";
      const contactName = winBtn.dataset.contactName || "N/A";
      const amountText = winBtn.dataset.amount || "R$ 0,00";
      // const paymentText = winBtn.dataset.payment || "N/A";

      winDealState = {
        dealId: dealId,
        quoteId: dealId,
        targetCard: card,
      };

      elements.winDealClient.textContent = clientName;
      elements.winDealContact.textContent = contactName;
      elements.winDealAmount.textContent = amountText;
      // elements.winDealPayment.textContent = paymentText;

      winDealBootstrapModal.show();
    }

    const loseBtn = e.target.closest(".btn-lose");
    if (loseBtn && loseDealBootstrapModal) {
      const card = loseBtn.closest(".card");
      if (!card) return;
      const dealId = loseBtn.dataset.dealId;
      loseDealState = { dealId, targetCard: card };

      // Clear and load reasons
      elements.loseDealReasonSelect.innerHTML = '<option value="">Selecione...</option>';
      fetch('/api/ploomes/deals/loss-reasons/?pipeline_id=37808')
        .then(res => res.json())
        .then(data => {
          const reasons = data.data || [];
          if (!reasons.length) {
            document.getElementById('loseDealReasonEmpty')?.classList.remove('d-none');
            return;
          }
          document.getElementById('loseDealReasonEmpty')?.classList.add('d-none');
          reasons.forEach(r => {
            const opt = document.createElement('option');
            opt.value = r.Id;
            opt.textContent = r.Name;
            elements.loseDealReasonSelect.appendChild(opt);
          });
        })
        .catch(() => {
          showToast('Falha ao carregar motivos de perda.', 'danger');
        });

      loseDealBootstrapModal.show();
    }

    const mirrorBtn = e.target.closest('.btn-mirror');
    if (mirrorBtn) {
      const dealId = mirrorBtn.dataset.dealId;
      if (!dealId) return;
      mirrorBtn.disabled = true;
      mirrorBtn.textContent = 'Abrindo...';
      fetch(`/api/ploomes/orders/mirror/?deal_id=${dealId}`)
        .then(res => res.json().then(body => ({ ok: res.ok, body })))
        .then(({ ok, body }) => {
          if (!ok) {
            const detail = body?.detail || 'Erro ao buscar espelho';
            showToast(detail, 'danger');
            return;
          }
          if (body?.document_url) {
            window.open(body.document_url, '_blank');
          } else {
            showToast('URL do espelho não encontrada.', 'warning');
          }
        })
        .catch(() => showToast('Falha ao carregar espelho.', 'danger'))
        .finally(() => {
          mirrorBtn.disabled = false;
          mirrorBtn.textContent = 'Espelho';
        });
    }
  });

  if (elements.loseDealConfirm && loseDealBootstrapModal) {
    elements.loseDealConfirm.addEventListener('click', async () => {
      const reasonId = elements.loseDealReasonSelect.value;
      if (!reasonId) {
        showToast('Selecione um motivo de perda.', 'warning');
        return;
      }
      elements.loseDealConfirm.disabled = true;
      elements.loseDealConfirm.textContent = 'Confirmando...';
      try {
        const res = await fetch('/api/ploomes/deals/lose/', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ deal_id: loseDealState.dealId, loss_reason_id: Number(reasonId) }),
        });
        const data = await res.json();
        if (!res.ok) {
          const detail = data?.detail || `Erro ${res.status}`;
          showToast(`Falha ao perder negócio: ${detail}`, 'danger');
          return;
        }

        if (loseDealState.targetCard) {
          loseDealState.targetCard.dataset.statusId = '3';
          const statusBadge = loseDealState.targetCard.querySelector('.card-title .badge');
          if (statusBadge) {
            statusBadge.className = 'badge badge-lost';
            statusBadge.textContent = 'Perdido';
          }
          const winBtnEl = loseDealState.targetCard.querySelector('.btn-win');
          if (winBtnEl) winBtnEl.classList.add('d-none');
          const loseBtnEl = loseDealState.targetCard.querySelector('.btn-lose');
          if (loseBtnEl) loseBtnEl.classList.add('d-none');
        }

        showToast('Negócio marcado como perdido.', 'success');
        loseDealBootstrapModal.hide();
      } catch (err) {
        showToast(`Falha ao perder negócio: ${err.message}`, 'danger');
      } finally {
        elements.loseDealConfirm.disabled = false;
        elements.loseDealConfirm.textContent = 'Confirmar perda';
      }
    });
  }

  function clearAlert() {
    if (!elements.alert) return;
    elements.alert.innerHTML = "";
  }

  function setLoading(isLoading) {
    if (elements.loadBtn) {
      elements.loadBtn.disabled = isLoading;
      elements.loadBtn.textContent = isLoading ? "Buscando..." : "Buscar";
    }
    if (elements.refreshBtn) {
      elements.refreshBtn.disabled = isLoading;
    }
    if (elements.spinner) {
      elements.spinner.classList.toggle("d-none", !isLoading);
    }
  }

  if (elements.login && elements.login.dataset.owner) {
    elements.login.value = elements.login.dataset.owner;
  }

  function resetAndFetch() {
    fetchQuotes(true);
  }

  elements.loadBtn?.addEventListener("click", resetAndFetch);
  elements.refreshBtn?.addEventListener("click", resetAndFetch);

  const handleScroll = () => {
    const nearBottom = window.innerHeight + window.scrollY >= document.body.offsetHeight - 200;
    if (nearBottom && hasMore && !isLoading) {
      fetchQuotes(false);
    }
  };
  window.__homeScrollHandler = handleScroll;
  window.addEventListener("scroll", handleScroll);

  function initHomePage() {
    if (!elements.login || !elements.loadBtn || !elements.cards) return;
    fetchDeliveryDeadline(); // nao bloqueia renderizacao do restante da pagina
    if (elements.login && elements.login.value) {
      resetAndFetch();
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initHomePage, { once: true });
  } else {
    initHomePage();
  }
})();

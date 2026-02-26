document.addEventListener('DOMContentLoaded', () => {
    // --- Elements ---
    const tablesWrapper = document.getElementById('tablesWrapper');
    const statsContainer = document.getElementById('statsContainer');
    const searchInput = document.getElementById('searchInput');

    // Modals
    const productModal = document.getElementById('productModal');
    const deleteModal = document.getElementById('deleteModal');
    const testModal = document.getElementById('testModal');

    // Views
    const productsView = document.getElementById('productsView');
    const settingsView = document.getElementById('settingsView');
    const navItems = document.querySelectorAll('.nav-item');
    const navStoreSubmenu = document.getElementById('navStoreSubmenu');
    const headerTitle = document.querySelector('.header-title h1');
    const headerDesc = document.querySelector('.header-title p');
    const btnAddProduct = document.getElementById('btnAddProduct');

    // Forms & Inputs
    const productForm = document.getElementById('productForm');
    const formMode = document.getElementById('formMode');
    const inputId = document.getElementById('productId');
    const inputName = document.getElementById('productName');
    const inputStore = document.getElementById('productStore');
    const inputPackSize = document.getElementById('productPackSize');
    const inputUrl = document.getElementById('productUrl');
    const modalTitle = document.getElementById('modalTitle');

    const deleteProductId = document.getElementById('deleteProductId');
    const deleteProductName = document.getElementById('deleteProductName');

    // State
    let products = [];
    let settings = { enabled_stores: [] };
    let currentStoreFilter = 'all';

    // Settings elements
    const storeTogglesContainer = document.getElementById('storeTogglesContainer');
    const settingsForm = document.getElementById('settingsForm');

    const storeNames = {
        'nofrills': 'No Frills',
        'foodbasics': 'Food Basics',
        'metro': 'Metro'
    };

    // --- Initialization ---
    init();

    async function init() {
        await fetchSettings();
        await fetchProducts();
        setupNavigation();
    }

    // --- API Interactions ---
    async function fetchProducts() {
        try {
            const res = await fetch('/api/products');
            products = await res.json();
            renderDashboard(products);
        } catch (error) {
            showToast('Failed to load products', 'error');
        }
    }

    async function saveProduct(productData, mode) {
        try {
            const url = mode === 'add' ? '/api/products' : `/api/products/${productData.id}`;
            const method = mode === 'add' ? 'POST' : 'PUT';

            // Clean up empty pack_size
            if (productData.pack_size === "") {
                productData.pack_size = null;
            } else if (productData.pack_size) {
                productData.pack_size = parseFloat(productData.pack_size);
            }

            const res = await fetch(url, {
                method: method,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(productData)
            });

            if (!res.ok) {
                const err = await res.json();
                throw new Error(err.detail || 'Failed to save product');
            }

            showToast(`Product ${mode === 'add' ? 'added' : 'updated'} successfully`);
            closeModal(productModal);
            fetchProducts();
        } catch (error) {
            showToast(error.message, 'error');
        }
    }

    async function toggleActiveStatus(id, currentStatus) {
        try {
            const res = await fetch(`/api/products/${id}/toggle`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ active: !currentStatus })
            });

            if (!res.ok) throw new Error('Failed to toggle status');

            showToast(`Product ${!currentStatus ? 'activated' : 'paused'}`);
            fetchProducts();
        } catch (error) {
            showToast(error.message, 'error');
        }
    }

    async function deleteProduct(id) {
        try {
            const res = await fetch(`/api/products/${id}`, { method: 'DELETE' });
            if (!res.ok) throw new Error('Failed to delete product');

            showToast('Product deleted');
            closeModal(deleteModal);
            fetchProducts();
        } catch (error) {
            showToast(error.message, 'error');
        }
    }

    async function fetchSettings() {
        try {
            const res = await fetch('/api/settings');
            settings = await res.json();
            renderSettingsForm();
            renderSidebar();
        } catch (error) {
            showToast('Failed to load settings', 'error');
        }
    }

    async function saveSettings(e) {
        e.preventDefault();

        // Collect enabled stores from checkboxes
        const checkboxes = storeTogglesContainer.querySelectorAll('input[type="checkbox"]');
        const enabledStores = [];
        checkboxes.forEach(cb => {
            if (cb.checked) enabledStores.push(cb.value);
        });

        try {
            const res = await fetch('/api/settings', {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ enabled_stores: enabledStores })
            });
            if (!res.ok) throw new Error('Failed to save settings');

            settings = await res.json();
            showToast('Settings saved successfully');
            renderSidebar();
            // Re-render dashboard if store filter is no longer enabled
            if (currentStoreFilter !== 'all' && !settings.enabled_stores.includes(currentStoreFilter)) {
                currentStoreFilter = 'all';
                document.getElementById('navAllProducts').click();
            } else {
                fetchProducts(); // Refresh products to reflect changed enabled states
            }
        } catch (error) {
            showToast(error.message, 'error');
        }
    }

    // --- View Navigation ---
    function setupNavigation() {
        navItems.forEach(item => {
            if (item.id === 'navAllProducts') {
                item.addEventListener('click', (e) => {
                    e.preventDefault();
                    switchView('products');
                    currentStoreFilter = 'all';
                    updateActiveNav(item);
                    renderDashboard(products);
                });
            } else if (item.id === 'navSettings') {
                item.addEventListener('click', (e) => {
                    e.preventDefault();
                    switchView('settings');
                    updateActiveNav(item);
                });
            }
        });

        settingsForm.addEventListener('submit', saveSettings);
    }

    function switchView(viewName) {
        if (viewName === 'products') {
            productsView.style.display = 'block';
            settingsView.style.display = 'none';
            statsContainer.style.display = 'grid';
            headerTitle.textContent = 'Product Management';
            headerDesc.textContent = 'Manage retail URLs and scraping configurations';
            btnAddProduct.style.display = 'inline-flex';
        } else if (viewName === 'settings') {
            productsView.style.display = 'none';
            settingsView.style.display = 'block';
            statsContainer.style.display = 'none';
            headerTitle.textContent = 'Settings';
            headerDesc.textContent = 'Configure global tracker behaviors';
            btnAddProduct.style.display = 'none';
        }
    }

    function updateActiveNav(activeElement) {
        document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));
        document.querySelectorAll('.submenu-item').forEach(el => el.classList.remove('active'));
        activeElement.classList.add('active');
    }

    function renderSidebar() {
        navStoreSubmenu.innerHTML = '';
        settings.enabled_stores.forEach(store => {
            const a = document.createElement('a');
            a.href = '#';
            a.className = 'submenu-item nav-item';
            a.innerHTML = `<i class="fa-solid fa-store" style="color: var(--brand-${store})"></i> ${storeNames[store] || store}`;

            a.addEventListener('click', (e) => {
                e.preventDefault();
                switchView('products');
                currentStoreFilter = store;
                updateActiveNav(a);
                // Filter products and re-render
                renderDashboard(products);
            });

            if (currentStoreFilter === store) {
                a.classList.add('active');
            }

            navStoreSubmenu.appendChild(a);
        });
    }

    function renderSettingsForm() {
        storeTogglesContainer.innerHTML = '';
        Object.keys(storeNames).forEach(storeKey => {
            const isEnabled = settings.enabled_stores.includes(storeKey);
            const div = document.createElement('div');
            div.className = 'toggle-wrapper';
            div.style.marginBottom = '1rem';
            div.innerHTML = `
                <label style="display: flex; align-items: center; cursor: pointer;">
                    <input type="checkbox" value="${storeKey}" ${isEnabled ? 'checked' : ''} style="margin-right: 10px; width: 1.2rem; height: 1.2rem;">
                    <span style="font-weight: 500">${storeNames[storeKey]}</span>
                </label>
            `;
            storeTogglesContainer.appendChild(div);
        });
    }

    // --- Rendering ---
    function renderDashboard(data) {
        renderStats(data);

        // Filter based on store selection in sidebar
        let displayData = data;
        if (currentStoreFilter !== 'all') {
            displayData = data.filter(p => p.store === currentStoreFilter);
        }

        // Group by store
        const grouped = displayData.reduce((acc, p) => {
            if (!acc[p.store]) acc[p.store] = [];
            acc[p.store].push(p);
            return acc;
        }, {});

        tablesWrapper.innerHTML = '';

        if (Object.keys(grouped).length === 0) {
            tablesWrapper.innerHTML = '<div class="store-section"><div class="store-header">No products found</div></div>';
            return;
        }

        const storeNames = {
            'nofrills': 'No Frills',
            'foodbasics': 'Food Basics',
            'metro': 'Metro'
        };

        for (const [store, storeProducts] of Object.entries(grouped)) {
            // Only show groups for enabled stores (unless there are products somehow)
            // if we are looking at 'all', but strictly, user might have old data.

            const section = document.createElement('div');
            section.className = 'store-section';

            const activeCount = storeProducts.filter(p => p.active !== false).length;

            // Build Table HTML
            let trs = storeProducts.map(p => {
                const isActive = p.active !== false;
                const statusHtml = isActive
                    ? `<span class="status-badge status-active"><i class="fa-solid fa-check-circle"></i> Active</span>`
                    : `<span class="status-badge status-paused"><i class="fa-solid fa-pause-circle"></i> Paused</span>`;

                const packHtml = p.pack_size ? `<br><small>Pack: ${p.pack_size}</small>` : '';

                return `
                    <tr>
                        <td>
                            <div class="status-wrapper" style="cursor: pointer" onclick="window.toggleProduct('${p.id}', ${isActive})" title="Click to toggle status">
                                ${statusHtml}
                            </div>
                        </td>
                        <td class="td-id">${p.id}</td>
                        <td class="td-name">${p.name} ${packHtml}</td>
                        <td class="td-url"><a href="${p.url}" target="_blank" title="${p.url}">${p.url.substring(0, 45)}...</a></td>
                        <td class="td-actions">
                            <button class="btn-icon" onclick="window.editProduct('${p.id}')" title="Edit"><i class="fa-solid fa-pen"></i></button>
                            ${isActive
                        ? `<button class="btn-icon pause" onclick="window.toggleProduct('${p.id}', ${isActive})" title="Pause"><i class="fa-solid fa-pause"></i></button>`
                        : `<button class="btn-icon" onclick="window.toggleProduct('${p.id}', ${isActive})" title="Activate"><i class="fa-solid fa-play"></i></button>`
                    }
                            <button class="btn-icon test" style="color: var(--accent-primary);" onclick="window.testProduct('${p.id}')" title="Test Scraper"><i class="fa-solid fa-vial"></i></button>
                            <button class="btn-icon delete" onclick="window.confirmDelete('${p.id}', '${p.name.replace(/'/g, "\\'")}')" title="Delete"><i class="fa-solid fa-trash"></i></button>
                        </td>
                    </tr>
                `;
            }).join('');

            section.innerHTML = `
                <div class="store-header">
                    <span style="color: var(--brand-${store})"><i class="fa-solid fa-store"></i></span>
                    ${storeNames[store] || store}
                    <span class="badge">${activeCount} / ${storeProducts.length}</span>
                </div>
                <div style="overflow-x: auto;">
                    <table>
                        <thead>
                            <tr>
                                <th style="width: 120px">Status</th>
                                <th style="width: 15%">ID</th>
                                <th>Name</th>
                                <th>URL</th>
                                <th style="width: 120px">Actions</th>
                            </tr>
                        </thead>
                        <tbody>${trs}</tbody>
                    </table>
                </div>
            `;
            tablesWrapper.appendChild(section);
        }
    }

    function renderStats(data) {
        const total = data.length;
        const active = data.filter(p => p.active !== false).length;
        const nofrills = data.filter(p => p.store === 'nofrills').length;
        const foodbasics = data.filter(p => p.store === 'foodbasics').length;
        const metro = data.filter(p => p.store === 'metro').length;

        statsContainer.innerHTML = `
            <div class="stat-card">
                <div class="stat-icon" style="background: rgba(59, 130, 246, 0.1); color: var(--accent-primary)">
                    <i class="fa-solid fa-boxes-stacked"></i>
                </div>
                <div class="stat-info">
                    <h3>Total Products</h3>
                    <p>${total} <span style="font-size: 0.8rem; color: var(--text-secondary); font-weight: 500;">(${active} active)</span></p>
                </div>
            </div>
            <div class="stat-card brand-nofrills">
                <div class="stat-icon"><i class="fa-solid fa-shop"></i></div>
                <div class="stat-info">
                    <h3>No Frills</h3>
                    <p>${nofrills}</p>
                </div>
            </div>
            <div class="stat-card brand-foodbasics">
                <div class="stat-icon"><i class="fa-solid fa-store-alt"></i></div>
                <div class="stat-info">
                    <h3>Food Basics</h3>
                    <p>${foodbasics}</p>
                </div>
            </div>
             <div class="stat-card brand-metro">
                <div class="stat-icon"><i class="fa-solid fa-shopping-basket"></i></div>
                <div class="stat-info">
                    <h3>Metro</h3>
                    <p>${metro}</p>
                </div>
            </div>
        `;
    }

    // --- Search Logic ---
    searchInput.addEventListener('input', (e) => {
        const term = e.target.value.toLowerCase();
        if (!term) {
            renderDashboard(products);
            return;
        }

        const filtered = products.filter(p =>
            p.name.toLowerCase().includes(term) ||
            p.id.toLowerCase().includes(term) ||
            p.store.toLowerCase().includes(term)
        );
        renderDashboard(filtered);
    });

    // --- Modal Logic ---
    function openModal(modal) {
        modal.classList.add('active');
    }

    function closeModal(modal) {
        modal.classList.remove('active');
        if (modal === productModal) productForm.reset();
    }

    document.getElementById('btnAddProduct').addEventListener('click', () => {
        formMode.value = 'add';
        modalTitle.textContent = 'Add Product';
        inputId.readOnly = false;
        inputId.style.opacity = '1';
        openModal(productModal);
    });

    document.getElementById('btnCloseModal').addEventListener('click', () => closeModal(productModal));
    document.getElementById('btnCancelModal').addEventListener('click', () => closeModal(productModal));

    document.getElementById('btnCancelDelete').addEventListener('click', () => closeModal(deleteModal));

    document.getElementById('btnCloseTestModal').addEventListener('click', () => closeModal(testModal));
    document.getElementById('btnOkTestModal').addEventListener('click', () => closeModal(testModal));

    // Form Submit
    productForm.addEventListener('submit', (e) => {
        e.preventDefault();
        const data = {
            id: inputId.value.trim(),
            name: inputName.value.trim(),
            store: inputStore.value,
            url: inputUrl.value.trim(),
            pack_size: inputPackSize.value.trim()
        };
        saveProduct(data, formMode.value);
    });

    // Delete Confirm
    document.getElementById('btnConfirmDelete').addEventListener('click', () => {
        deleteProduct(deleteProductId.value);
    });

    // --- Global Handlers (For inline HTML event calls) ---
    window.editProduct = (id) => {
        const p = products.find(prod => prod.id === id);
        if (!p) return;

        formMode.value = 'edit';
        modalTitle.textContent = 'Edit Product';

        inputId.value = p.id;
        inputId.readOnly = true;     // Cannot edit ID
        inputId.style.opacity = '0.5';

        inputName.value = p.name;
        inputStore.value = p.store;
        inputUrl.value = p.url;
        inputPackSize.value = p.pack_size || '';

        openModal(productModal);
    };

    window.toggleProduct = (id, currentStatus) => toggleActiveStatus(id, currentStatus);

    window.confirmDelete = (id, name) => {
        deleteProductId.value = id;
        deleteProductName.textContent = name;
        openModal(deleteModal);
    };

    window.testProduct = async (id) => {
        const resultPre = document.getElementById('testResultPre');
        const loading = document.getElementById('testLoading');

        resultPre.style.display = 'none';
        loading.style.display = 'block';
        openModal(testModal);

        try {
            const res = await fetch(`/api/products/${id}/test`, {
                method: 'POST'
            });
            const data = await res.json();

            resultPre.textContent = JSON.stringify(data, null, 2);
            resultPre.style.display = 'block';
            loading.style.display = 'none';
        } catch (error) {
            resultPre.textContent = JSON.stringify({ error: error.message }, null, 2);
            resultPre.style.display = 'block';
            loading.style.display = 'none';
            showToast('Test execution failed', 'error');
        }
    };

    // --- Toast Notifications ---
    function showToast(message, type = 'success') {
        const container = document.getElementById('toastContainer');
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;

        const icon = type === 'success' ? 'fa-check-circle' : 'fa-exclamation-circle';

        toast.innerHTML = `
            <i class="fa-solid ${icon}"></i>
            <span>${message}</span>
        `;

        container.appendChild(toast);

        setTimeout(() => {
            toast.style.animation = 'fadeOut 0.3s ease forwards';
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }
});

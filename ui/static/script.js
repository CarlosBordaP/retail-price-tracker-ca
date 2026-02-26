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
    const historyView = document.getElementById('historyView');
    const navItems = document.querySelectorAll('.nav-item');
    const navHistory = document.getElementById('navHistory');
    const navStoreSubmenu = document.getElementById('navStoreSubmenu');
    const headerTitle = document.getElementById('mainTitle');
    const headerDesc = document.getElementById('mainDesc');
    const btnAddProduct = document.getElementById('btnAddProduct');

    // History & Tracker Elements
    const historyTableBody = document.getElementById('historyTableBody');
    const historyTableHeader = document.getElementById('historyTableHeader');
    const btnRunScraper = document.getElementById('btnRunScraper');
    const scraperTracker = document.getElementById('scraperTracker');
    const trackerMessage = document.getElementById('trackerMessage');
    const trackerProgressFill = document.getElementById('trackerProgressFill');
    const trackerStats = document.getElementById('trackerStats');
    let trackingIntervalName = null;

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

        navHistory.addEventListener('click', (e) => {
            e.preventDefault();
            switchView('history');
            updateActiveNav(navHistory);
            fetchHistory(); // Reload history when clicked
        });

        settingsForm.addEventListener('submit', saveSettings);

        btnRunScraper.addEventListener('click', startScraper);
    }

    function switchView(viewName) {
        if (viewName === 'products') {
            productsView.style.display = 'block';
            settingsView.style.display = 'none';
            historyView.style.display = 'none';
            statsContainer.style.display = 'grid';
            headerTitle.textContent = 'Product Management';
            headerDesc.textContent = 'Manage retail URLs and scraping configurations';
            btnAddProduct.style.display = 'inline-flex';
        } else if (viewName === 'settings') {
            productsView.style.display = 'none';
            settingsView.style.display = 'block';
            historyView.style.display = 'none';
            statsContainer.style.display = 'none';
            headerTitle.textContent = 'Settings';
            headerDesc.textContent = 'Configure global tracker behaviors';
            btnAddProduct.style.display = 'none';
        } else if (viewName === 'history') {
            productsView.style.display = 'none';
            settingsView.style.display = 'none';
            historyView.style.display = 'block';
            statsContainer.style.display = 'none';
            headerTitle.textContent = 'Historical Data';
            headerDesc.textContent = 'View price trends over the last 7 recorded days';
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

    // --- History & Scraper Execution ---
    async function fetchHistory() {
        try {
            historyTableBody.innerHTML = '<tr><td colspan="9" style="text-align:center">Loading history...</td></tr>';
            const res = await fetch('/api/history');
            const data = await res.json();
            renderHistoryTable(data);
        } catch (error) {
            historyTableBody.innerHTML = '<tr><td colspan="9" style="text-align:center;color:var(--accent-warning);">Failed to load history data</td></tr>';
        }
    }

    function renderHistoryTable(data) {
        // Collect all distinct dates from the dataset
        const allDatesSet = new Set();
        data.forEach(item => {
            Object.keys(item.history || {}).forEach(d => allDatesSet.add(d));
        });

        // Sort dates chronologically
        const dates = Array.from(allDatesSet).sort();
        // Keep only last 7
        const last7Dates = dates.slice(-7);

        // Render header
        historyTableHeader.innerHTML = `
            <th>Store</th>
            <th>Product Name</th>
        `;
        last7Dates.forEach(d => {
            const th = document.createElement('th');
            th.textContent = d;
            historyTableHeader.appendChild(th);
        });

        // Render body
        historyTableBody.innerHTML = '';
        if (data.length === 0) {
            historyTableBody.innerHTML = `<tr><td colspan="${last7Dates.length + 2}" style="text-align:center">No historical data available.</td></tr>`;
            return;
        }

        data.forEach(item => {
            const tr = document.createElement('tr');

            // Store badge
            const tdStore = document.createElement('td');
            const storeName = storeNames[item.store] || item.store;
            tdStore.innerHTML = `<span class="badge" style="background-color: var(--bg-hover); color: var(--brand-${item.store})"><i class="fa-solid fa-store"></i> ${storeName}</span>`;
            tr.appendChild(tdStore);

            // Product name
            const tdName = document.createElement('td');
            tdName.textContent = item.name;
            tr.appendChild(tdName);

            // History columns
            last7Dates.forEach(d => {
                const td = document.createElement('td');
                const price = item.history[d];
                if (price !== undefined) {
                    td.className = 'price-cell';
                    td.textContent = `$${price.toFixed(2)}`;
                } else {
                    td.className = 'price-cell empty';
                    td.textContent = '-';
                }
                tr.appendChild(td);
            });

            historyTableBody.appendChild(tr);
        });
    }

    async function startScraper() {
        btnRunScraper.disabled = true;
        try {
            const res = await fetch('/api/scrape/start', { method: 'POST' });
            if (!res.ok) {
                const err = await res.json();
                throw new Error(err.detail || 'Failed to start scraper');
            }
            showToast('Scraper started successfully');

            // Show tracker UI
            scraperTracker.style.display = 'flex';
            btnRunScraper.style.display = 'none';

            // Begin polling status
            if (trackingIntervalName) clearInterval(trackingIntervalName);
            pollScraperStatus();
            trackingIntervalName = setInterval(pollScraperStatus, 2000);

        } catch (error) {
            showToast(error.message, 'error');
            btnRunScraper.disabled = false;
        }
    }

    async function pollScraperStatus() {
        try {
            const res = await fetch('/api/scrape/status');
            const state = await res.json();

            if (state.status === 'idle' || state.status === 'error') {
                // UI if it finished before opening or error immediately
                if (trackingIntervalName) clearInterval(trackingIntervalName);
                scraperTracker.style.display = 'none';
                btnRunScraper.style.display = 'inline-flex';
                btnRunScraper.disabled = false;
                return;
            }

            // Update UI
            const percentage = state.total > 0 ? (state.progress / state.total) * 100 : 0;
            trackerProgressFill.style.width = `${percentage}%`;
            trackerStats.textContent = `${state.progress}/${state.total}`;
            trackerMessage.textContent = state.current_product;

            if (state.status === 'running') {
                trackerProgressFill.classList.add('running');
            } else {
                trackerProgressFill.classList.remove('running');
                trackerMessage.textContent = 'Completed!';

                // Allow user to close it or reset after a delay
                if (trackingIntervalName) clearInterval(trackingIntervalName);
                setTimeout(() => {
                    scraperTracker.style.display = 'none';
                    btnRunScraper.style.display = 'inline-flex';
                    btnRunScraper.disabled = false;
                    // Refresh history if we are on that view
                    if (historyView.style.display === 'block') {
                        fetchHistory();
                    }
                }, 3000);
            }

        } catch (error) {
            console.error('Error polling status:', error);
        }
    }
});

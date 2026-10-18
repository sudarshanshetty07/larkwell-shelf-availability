/* Larkwell Shelf Availability — frontend JS (fictitious retailer, synthetic data)
   36-column schema, product/store hierarchy, consensus_reason + consensus_reason_retail
   Personas: Head Office (Store / Category) | Retail (Regional Manager / Store Manager) */

// --- Feedback Context ---
var messageContext = {};  // msgId → {question, answer, sql}
var pendingFeedback = null;  // {conversationId, messageId} for thumbs-down modal

// --- App State ---
var AppState = {
  persona: 'support_centre',
  subView: 'store',
  currentTab: 'dashboard',
  issueFilter: 'all',
  lowFilter: 'both',
  scopeFilter: 'owned',
  storeAgg: 'store',
  productAgg: 'category',
  drillPath: [],
  selectedStore: '',
  selectedDivision: '',
  selectedArea: '',
  dashboardData: null,
  briefingData: null,
  chatConversationId: null,
  storeList: [],
  filterData: {},
  divisionData: {},
  charts: {},
  visibleColumns: {
    product: true, upc: true, store: true, issue: true, reason_code: true,
    supplier_short_qty: true, scarcity_qty: true, waste_qty: true,
    under_forecast_qty: true, under_space_qty: true, stockfile_adjustment_qty: false,
    supplier: false, depot: false, category: false, super_group: false, product_group: false,
    division: false, area: false, site_trading_group: false
  }
};

var ALL_PRODUCT_COLS = [
  {key: 'product', label: 'Product'},
  {key: 'upc', label: 'UPC'},
  {key: 'store', label: 'Store'},
  {key: 'issue', label: 'Status'},
  {key: 'reason_code', label: 'Reason Code'},
  {key: 'supplier_short_qty', label: 'Supplier Short Qty'},
  {key: 'scarcity_qty', label: 'Scarcity Qty'},
  {key: 'waste_qty', label: 'Waste Qty'},
  {key: 'under_forecast_qty', label: 'Forecast Deficit'},
  {key: 'under_space_qty', label: 'Space Deficit'},
  {key: 'stockfile_adjustment_qty', label: 'Stockfile Adj Qty'},
  {key: 'supplier', label: 'Supplier'},
  {key: 'depot', label: 'Depot'},
  {key: 'category', label: 'Category'},
  {key: 'super_group', label: 'Department'},
  {key: 'product_group', label: 'Product Group'},
  {key: 'division', label: 'Division'},
  {key: 'area', label: 'Area'},
  {key: 'site_trading_group', label: 'Format'}
];

// --- RBAC State ---
var UserRole = {
  email: '',
  persona: null,
  store_filter: null,
  division_filter: null,
  is_admin: true,
  authenticated: false
};

// --- Init ---
document.addEventListener('DOMContentLoaded', function() {
  loadUserRole();
});

function loadUserRole() {
  fetch('/api/me').then(function(r) {
    if (r.status === 403) {
      return r.json().then(function(err) {
        document.querySelector('.main').innerHTML = '<div class="empty-state"><div class="empty-state-icon">&#128274;</div><div class="empty-state-title">Access Denied</div><div class="empty-state-text">Your account (' + escHtml(err.email || 'unknown') + ') is not configured for this application. Contact your admin to request access.</div></div>';
        return null;
      });
    }
    return r.json();
  }).then(function(data) {
    if (!data) return;
    UserRole = data;
    applyRoleDefaults(data);
    loadStores();
    loadFilters();
    updateUI();
    loadDashboard();
  }).catch(function() {
    // Fallback: run as admin (local dev)
    loadStores();
    loadFilters();
    updateUI();
    loadDashboard();
  });
}

function applyRoleDefaults(role) {
  // Set defaults from API response
  AppState.persona = role.default_persona || 'support_centre';
  AppState.subView = role.default_view || 'store';

  // Set persona dropdown to match
  var dropdown = document.getElementById('persona-dropdown');
  if (dropdown) {
    // Only show personas the user has access to
    var allowed = role.allowed_personas || [];
    dropdown.innerHTML = '';
    if (allowed.indexOf('support_centre') !== -1) {
      dropdown.innerHTML += '<option value="support_centre">Head Office</option>';
    }
    if (allowed.indexOf('retail') !== -1) {
      dropdown.innerHTML += '<option value="retail">Retail</option>';
    }
    dropdown.value = AppState.persona;

    // Hide dropdown if only one persona available
    dropdown.style.display = (allowed.length > 1) ? '' : 'none';
  }

  // Pre-select store if role has store_filter
  if (role.store_filter) {
    AppState.selectedStore = role.store_filter;
  }

  // Pre-select division if role has division_filter
  if (role.division_filter) {
    AppState.selectedDivision = role.division_filter;
  }
}

// ================================================================
// PERSONA & VIEW MANAGEMENT
// ================================================================

function getApiPersona() {
  if (AppState.persona === 'retail') {
    return AppState.subView === 'regional_manager' ? 'retail_regional' : 'retail_store_manager';
  }
  return AppState.subView === 'category' ? 'support_centre_category' : 'support_centre_store';
}

function onPersonaChange() {
  var sel = document.getElementById('persona-dropdown');
  AppState.persona = sel.value;
  AppState.drillPath = [];
  if (sel.value === 'support_centre') {
    AppState.subView = 'store';
  } else {
    AppState.subView = 'regional_manager';
  }
  updateUI();
  AppState.dashboardData = null;
  if (AppState.currentTab === 'dashboard') loadDashboard();
  else if (AppState.currentTab === 'briefing' && !hasBriefing()) {
    showTab('dashboard', document.getElementById('nav-dashboard'));
  }
}

function setSubView(view, btn) {
  AppState.subView = view;
  AppState.drillPath = [];
  document.querySelectorAll('.seg-btn').forEach(function(b) { b.classList.remove('active'); });
  btn.classList.add('active');
  updateUI();
  AppState.dashboardData = null;
  if (AppState.currentTab === 'dashboard') loadDashboard();
  else if (AppState.currentTab === 'briefing' && !hasBriefing()) {
    showTab('dashboard', document.getElementById('nav-dashboard'));
  }
}

function hasBriefing() {
  return AppState.persona === 'support_centre' && AppState.subView === 'store';
}

function updateUI() {
  updateSubViewToggle();
  updateNavTabs();
  updateSidebarVisibility();
  updateBreadcrumb();
}

function updateSubViewToggle() {
  var toggle = document.getElementById('subview-toggle');
  var allowedViews = (UserRole.allowed_views || {})[AppState.persona] || [];

  // Hide toggle if only one subview available for current persona
  if (allowedViews.length <= 1) {
    toggle.style.display = 'none';
    return;
  }

  // Build buttons dynamically from allowed views
  var viewLabels = {
    'store': 'Store', 'category': 'Category',
    'regional_manager': 'Regional Manager', 'store_manager': 'Store Manager'
  };
  toggle.innerHTML = allowedViews.map(function(v) {
    var active = (v === AppState.subView) ? ' active' : '';
    return '<button class="seg-btn' + active + '" data-view="' + v + '" onclick="setSubView(\'' + v + '\', this)">' + viewLabels[v] + '</button>';
  }).join('');
  toggle.style.display = '';
}

function updateNavTabs() {
  var briefNav = document.getElementById('nav-briefing');
  briefNav.style.display = hasBriefing() ? '' : 'none';
}

function updateSidebarVisibility() {
  var storeSection = document.getElementById('store-section');
  var divSection = document.getElementById('division-section');
  // Store dropdown: Head Office Store (briefing/chat) OR Retail Store Manager (all tabs)
  var showStore = (AppState.persona === 'support_centre' && AppState.subView === 'store' &&
    (AppState.currentTab === 'briefing' || AppState.currentTab === 'chat')) ||
    (AppState.persona === 'retail' && AppState.subView === 'store_manager');
  storeSection.style.display = showStore ? '' : 'none';
  // Division filter: only for Retail Regional Manager
  divSection.style.display = (AppState.persona === 'retail' && AppState.subView === 'regional_manager') ? '' : 'none';
}

// ================================================================
// TAB NAVIGATION
// ================================================================

function showTab(name, btn) {
  document.querySelectorAll('.tab-content').forEach(function(t) { t.classList.remove('active'); });
  document.querySelectorAll('.nav-btn').forEach(function(b) { b.classList.remove('active'); });
  document.getElementById('tab-' + name).classList.add('active');
  btn.classList.add('active');
  AppState.currentTab = name;
  updateSidebarVisibility();
  if (name === 'chat' && !AppState.suggestionsLoaded) { AppState.suggestionsLoaded = true; renderSuggestedQuestions(); }
  if (name === 'dashboard' && !AppState.dashboardData && AppState.drillPath.length === 0) {
    loadDashboard();
  }
  updateBreadcrumb();
}

// ================================================================
// DATA LOADING
// ================================================================

function loadStores() {
  fetch('/api/stores').then(function(r) { return r.json(); }).then(function(d) {
    AppState.storeList = d.stores || [];
    renderStoreResults(AppState.storeList);
    // If RBAC pre-assigned a store, auto-select it
    if (AppState.selectedStore && AppState.storeList.indexOf(AppState.selectedStore) !== -1) {
      selectStore(AppState.selectedStore);
    }
  });
}

function renderStoreResults(stores) {
  var panel = document.getElementById('store-search-results');
  if (!panel) return;
  if (stores.length === 0) {
    panel.innerHTML = '<div class="store-search-item" style="color:var(--text-sub);cursor:default">No stores found</div>';
  } else {
    panel.innerHTML = stores.map(function(s) {
      return '<div class="store-search-item" onclick="selectStore(\'' + escAttr(s).replace(/'/g, "\\'") + '\')">' + escHtml(s) + '</div>';
    }).join('');
  }
}

function filterStores(query) {
  var q = (query || '').toLowerCase().trim();
  var filtered = AppState.storeList.filter(function(s) {
    return s.toLowerCase().indexOf(q) !== -1;
  });
  renderStoreResults(filtered);
  var panel = document.getElementById('store-search-results');
  if (panel) panel.style.display = 'block';
}

function showStoreResults() {
  var input = document.getElementById('store-search-input');
  var q = (input ? input.value : '').toLowerCase().trim();
  var filtered = q ? AppState.storeList.filter(function(s) { return s.toLowerCase().indexOf(q) !== -1; }) : AppState.storeList;
  renderStoreResults(filtered);
  var panel = document.getElementById('store-search-results');
  if (panel) panel.style.display = 'block';
}

function selectStore(name) {
  AppState.selectedStore = name;
  var input = document.getElementById('store-search-input');
  var panel = document.getElementById('store-search-results');
  var chip = document.getElementById('store-selected-chip');
  if (input) { input.value = ''; input.style.display = 'none'; }
  if (panel) panel.style.display = 'none';
  if (chip) {
    chip.style.display = 'flex';
    // Hide clear button if user is locked to this store
    var locked = !UserRole.is_admin && UserRole.store_filter;
    chip.innerHTML = '<span>' + escHtml(name) + '</span>' +
      (locked ? '<span class="chip-lock">&#128274;</span>' : '<span class="chip-clear" onclick="clearStoreSelection()">&#10005;</span>');
  }
  // Hide the input wrap
  var inputWrap = document.querySelector('#store-search-wrap .store-search-input-wrap');
  if (inputWrap) inputWrap.style.display = 'none';
  onStoreChange();
}

function clearStoreSelection() {
  // Non-admin users with a locked store filter cannot clear
  if (!UserRole.is_admin && UserRole.store_filter) return;
  AppState.selectedStore = '';
  var input = document.getElementById('store-search-input');
  var chip = document.getElementById('store-selected-chip');
  var inputWrap = document.querySelector('#store-search-wrap .store-search-input-wrap');
  if (input) { input.value = ''; input.style.display = ''; }
  if (chip) chip.style.display = 'none';
  if (inputWrap) inputWrap.style.display = '';
}

// Close store search results on outside click
document.addEventListener('click', function(e) {
  var wrap = document.getElementById('store-search-wrap');
  var panel = document.getElementById('store-search-results');
  if (wrap && panel && !wrap.contains(e.target)) {
    panel.style.display = 'none';
  }
});

function loadFilters() {
  fetch('/api/filters').then(function(r) { return r.json(); }).then(function(d) {
    AppState.filterData = d;
  });
  fetch('/api/divisions').then(function(r) { return r.json(); }).then(function(d) {
    AppState.divisionData = d.divisions || {};
    var sel = document.getElementById('division-select');
    sel.innerHTML = '<option value="">All Divisions</option>' +
      Object.keys(AppState.divisionData).map(function(div) {
        return '<option value="' + escAttr(div) + '">' + escHtml(div) + '</option>';
      }).join('');
    // If RBAC pre-assigned a division, auto-select it
    if (AppState.selectedDivision) {
      sel.value = AppState.selectedDivision;
      onDivisionChange();
    }
  });
}

function onStoreChange() {
  var store = AppState.selectedStore;
  if (!store) return;
  if (AppState.persona === 'retail' && AppState.subView === 'store_manager') {
    // Store Manager: filter dashboard by selected store
    AppState.drillPath = [];
    updateBreadcrumb();
    if (AppState.currentTab === 'dashboard') loadDashboard();
  } else {
    // Head Office: store selection loads briefing but stays on current tab if chat
    if (AppState.currentTab === 'chat') {
      // Stay on chat — just update the store context
      loadBriefing(store);
    } else if (AppState.currentTab === 'briefing') {
      loadBriefing(store);
    } else {
      showTab('briefing', document.getElementById('nav-briefing'));
      loadBriefing(store);
    }
  }
}

function onDivisionChange() {
  var div = document.getElementById('division-select').value;
  AppState.selectedDivision = div;
  AppState.selectedArea = '';
  var areaSel = document.getElementById('area-select');
  if (div && AppState.divisionData[div]) {
    areaSel.innerHTML = '<option value="">All Areas</option>' +
      AppState.divisionData[div].map(function(a) { return '<option value="' + escAttr(a) + '">' + escHtml(a) + '</option>'; }).join('');
  } else {
    areaSel.innerHTML = '<option value="">All Areas</option>';
  }
  AppState.drillPath = [];
  updateBreadcrumb();
  loadDashboard();
}

function onAreaChange() {
  AppState.selectedArea = document.getElementById('area-select').value;
  AppState.drillPath = [];
  updateBreadcrumb();
  loadDashboard();
}

// ================================================================
// TOGGLES
// ================================================================

function setIssueFilter(val) {
  AppState.issueFilter = val;
  reloadCurrentLevel();
}

function setLowFilter(val) {
  AppState.lowFilter = val;
  reloadCurrentLevel();
}

function setScopeFilter(val) {
  AppState.scopeFilter = val;
  reloadCurrentLevel();
}

function reloadCurrentLevel() {
  if (AppState.drillPath.length > 0) {
    loadDrillLevel();
  } else {
    loadDashboard();
  }
}

function getFilteredMetricLabel() {
  if (AppState.issueFilter === 'gaps') return 'Gaps';
  if (AppState.issueFilter === 'lows') {
    if (AppState.lowFilter === 'sales') return 'Sales Lows';
    if (AppState.lowFilter === 'space') return 'Space Lows';
    return 'Lows';
  }
  if (AppState.lowFilter === 'sales') return 'Gaps + Sales Lows';
  if (AppState.lowFilter === 'space') return 'Gaps + Space Lows';
  return 'Gaps + Lows';
}

function getFilteredMetricValue(item) {
  if (AppState.issueFilter === 'gaps') return parseInt(item.gaps) || 0;
  if (AppState.issueFilter === 'lows') {
    if (AppState.lowFilter === 'sales') return parseInt(item.sales_lows) || 0;
    if (AppState.lowFilter === 'space') return parseInt(item.space_lows) || 0;
    return parseInt(item.lows) || 0;
  }
  if (AppState.lowFilter === 'sales') return (parseInt(item.gaps) || 0) + (parseInt(item.sales_lows) || 0);
  if (AppState.lowFilter === 'space') return (parseInt(item.gaps) || 0) + (parseInt(item.space_lows) || 0);
  return (parseInt(item.gaps) || 0) + (parseInt(item.lows) || 0);
}

function getFilteredPct(item) {
  var total = parseInt(item.total_pls) || 0;
  if (total === 0) return 0;
  return Math.round(getFilteredMetricValue(item) * 1000 / total) / 10;
}

function setStoreAgg(val) {
  AppState.storeAgg = val;
  reloadCurrentLevel();
}

function setProductAgg(val) {
  AppState.productAgg = val;
  reloadCurrentLevel();
}

// ================================================================
// DRILL-DOWN
// ================================================================

function drillDown(dimension, value) {
  AppState.drillPath.push({level: dimension, value: value, label: value});
  updateBreadcrumb();
  loadDrillLevel();
}

function drillUp() {
  if (AppState.drillPath.length === 0) return;
  AppState.drillPath.pop();
  updateBreadcrumb();
  if (AppState.drillPath.length === 0) loadDashboard();
  else loadDrillLevel();
}

function drillTo(index) {
  if (index < 0) { AppState.drillPath = []; updateBreadcrumb(); loadDashboard(); return; }
  AppState.drillPath = AppState.drillPath.slice(0, index + 1);
  updateBreadcrumb();
  loadDrillLevel();
}

function updateBreadcrumb() {
  var bar = document.getElementById('drill-breadcrumb');
  var trail = document.getElementById('breadcrumb-trail');
  if (AppState.drillPath.length === 0 || AppState.currentTab !== 'dashboard') {
    bar.style.display = 'none'; return;
  }
  bar.style.display = '';
  var html = '<span class="breadcrumb-item breadcrumb-root" onclick="drillTo(-1)">Home</span>';
  AppState.drillPath.forEach(function(step, i) {
    html += '<span class="breadcrumb-sep">&#8250;</span>';
    if (i === AppState.drillPath.length - 1) {
      html += '<span class="breadcrumb-item breadcrumb-current">' + escHtml(step.label) + '</span>';
    } else {
      html += '<span class="breadcrumb-item breadcrumb-link" onclick="drillTo(' + i + ')">' + escHtml(step.label) + '</span>';
    }
  });
  html += '<span class="breadcrumb-depth">' + AppState.drillPath.length + '</span>';
  trail.innerHTML = html;
}

function getNextDrillDimension() {
  var depth = AppState.drillPath.length;
  if (AppState.persona === 'support_centre' && AppState.subView === 'store') {
    if (depth === 0) return AppState.storeAgg;
    if (depth === 1) return AppState.productAgg;
    return 'product';
  }
  if (AppState.persona === 'support_centre' && AppState.subView === 'category') {
    if (depth === 0) return AppState.productAgg;
    if (depth === 1) return AppState.storeAgg;
    return 'product';
  }
  if (AppState.persona === 'retail' && AppState.subView === 'regional_manager') {
    if (depth === 0) return 'store';
    if (depth === 1) return AppState.productAgg;
    return 'product';
  }
  if (AppState.persona === 'retail' && AppState.subView === 'store_manager') {
    if (depth === 0) return AppState.productAgg;
    return 'product';
  }
  return 'product';
}

function buildDrillParams() {
  var params = new URLSearchParams();
  params.set('persona', getApiPersona());
  params.set('issue_filter', AppState.issueFilter);
  params.set('low_filter', AppState.lowFilter);
  params.set('scope_filter', AppState.scopeFilter);
  params.set('store_agg', AppState.storeAgg);
  params.set('product_agg', AppState.productAgg);
  if (AppState.selectedDivision) params.set('division', AppState.selectedDivision);
  if (AppState.selectedArea) params.set('area', AppState.selectedArea);
  // Retail Store Manager: auto-filter by selected store
  if (AppState.persona === 'retail' && AppState.subView === 'store_manager' && AppState.selectedStore) {
    params.set('store', AppState.selectedStore);
  }
  // Set filters from drill path
  AppState.drillPath.forEach(function(step) {
    var col = step.level;
    if (col === 'store' || col === 'division' || col === 'area' || col === 'stg') params.set(col, step.value);
    else if (col === 'category') params.set('category', step.value);
    else if (col === 'superGroup') params.set('super_group', step.value);
    else if (col === 'productGroup') params.set('product_group', step.value);
    else if (col === 'cluster') params.set('cluster', step.value);
  });
  return params;
}

function loadDrillLevel() {
  var nextDim = getNextDrillDimension();
  var params = buildDrillParams();
  params.set('drill_dimension', nextDim);

  var container = document.getElementById('dashboard-content');
  container.innerHTML = renderSkeleton();

  fetch('/api/drill?' + params.toString())
    .then(function(r) { if (!r.ok) throw new Error('Server error (' + r.status + ')'); return r.json(); })
    .then(function(d) { renderDrillResults(d, nextDim); })
    .catch(function(e) { container.innerHTML = errorState(e.message); });
}

// ================================================================
// DASHBOARD
// ================================================================

function loadDashboard() {
  var container = document.getElementById('dashboard-content');
  container.innerHTML = renderSkeleton();

  var params = new URLSearchParams();
  params.set('persona', getApiPersona());
  params.set('issue_filter', AppState.issueFilter);
  params.set('low_filter', AppState.lowFilter);
  params.set('scope_filter', AppState.scopeFilter);
  params.set('store_agg', AppState.storeAgg);
  params.set('product_agg', AppState.productAgg);
  if (AppState.selectedDivision) params.set('division', AppState.selectedDivision);
  if (AppState.selectedArea) params.set('area', AppState.selectedArea);
  if (AppState.persona === 'retail' && AppState.subView === 'store_manager' && AppState.selectedStore) {
    params.set('store', AppState.selectedStore);
  }

  fetch('/api/dashboard?' + params.toString())
    .then(function(r) { if (!r.ok) throw new Error('Server error (' + r.status + ')'); return r.json(); })
    .then(function(d) { AppState.dashboardData = d; renderDashboard(d); })
    .catch(function(e) { container.innerHTML = errorState(e.message); });
}

function renderDashboard(data) {
  var container = document.getElementById('dashboard-content');
  var totals = data.totals || {};
  var reasons = data.reasons || [];
  var table = data.table || [];
  var isPivot = data.pivot_mode === true;

  var html = '';

  // KPI cards
  html += '<div class="kpi-grid">';
  html += kpiCard('GAPs', fmtNum(totals.gaps), (totals.pct_pls_gap || 0) + '% of PLs', 'accent-red');
  html += kpiCard('LOWs', fmtNum(totals.lows), 'Sales: ' + fmtNum(totals.sales_lows) + ' | Space: ' + fmtNum(totals.space_lows), 'accent-amber');
  html += kpiCard('Known Gaps', fmtNum(totals.known_gaps), '', 'accent-blue');
  html += kpiCard('Upstream', fmtNum(totals.upstream_count), 'Supply chain issues', '');
  html += '</div>';

  // Toggles
  html += renderToggles();

  // Charts row
  html += '<div class="charts-row">';
  html += '<div class="chart-card"><div class="chart-card-header"><div class="chart-title">Reason Code Distribution</div></div><div class="chart-wrap"><canvas id="chart-reasons"></canvas></div></div>';
  if (isPivot) {
    html += '<div class="chart-card"><div class="chart-card-header"><div class="chart-title">Top Stores by Reason Code</div></div><div class="chart-wrap"><canvas id="chart-agg"></canvas></div></div>';
  } else {
    html += '<div class="chart-card"><div class="chart-card-header"><div class="chart-title">Top by ' + getFilteredMetricLabel() + '</div></div><div class="chart-wrap"><canvas id="chart-agg"></canvas></div></div>';
  }
  html += '</div>';

  // Aggregation selector
  html += renderAggSelector();

  // Table
  html += '<div class="section-title-row"><div class="section-title">Ranked by Gaps + Lows</div>';
  html += '<div class="search-wrap"><svg class="search-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg>';
  html += '<input type="text" class="store-search" id="dash-search" placeholder="Search..." oninput="filterDashTable()"></div></div>';
  html += '<div class="table-wrapper" id="dash-table"></div>';

  container.innerHTML = html;

  // Render charts
  renderReasonChart(reasons);
  if (isPivot) {
    renderPivotStackedChart(table);
    renderPivotTable(table, getNextDrillDimension());
  } else {
    renderAggChart(table);
    renderAggTable(table);
  }
}

function renderToggles() {
  var html = '<div class="toggle-bar">';
  // Issue toggle
  html += '<div class="toggle-group">';
  html += '<span class="toggle-label">Show</span>';
  html += toggleBtn('all', 'All', AppState.issueFilter, 'setIssueFilter');
  html += toggleBtn('gaps', 'Gaps', AppState.issueFilter, 'setIssueFilter');
  html += toggleBtn('lows', 'Lows', AppState.issueFilter, 'setIssueFilter');
  html += '</div>';
  // Low sub-toggle (only when showing lows or all)
  if (AppState.issueFilter !== 'gaps') {
    html += '<span class="toggle-sep"></span>';
    html += '<div class="toggle-group">';
    html += '<span class="toggle-label">Lows</span>';
    html += toggleBtn('both', 'Both', AppState.lowFilter, 'setLowFilter');
    html += toggleBtn('sales', 'Sales', AppState.lowFilter, 'setLowFilter');
    html += toggleBtn('space', 'Space', AppState.lowFilter, 'setLowFilter');
    html += '</div>';
  }
  // Scope toggle (only for Head Office)
  if (AppState.persona === 'support_centre') {
    html += '<span class="toggle-sep"></span>';
    html += '<div class="toggle-group">';
    html += '<span class="toggle-label">Scope</span>';
    html += toggleBtn('owned', 'Owned', AppState.scopeFilter, 'setScopeFilter');
    html += toggleBtn('franchise', 'Franchise', AppState.scopeFilter, 'setScopeFilter');
    html += toggleBtn('all', 'All', AppState.scopeFilter, 'setScopeFilter');
    html += '</div>';
  }
  html += '</div>';
  return html;
}

function toggleBtn(value, label, current, fn) {
  var cls = value === current ? 'toggle-btn active' : 'toggle-btn';
  return '<button class="' + cls + '" onclick="' + fn + '(\'' + value + '\')">' + label + '</button>';
}

function renderAggSelector() {
  var persona = getApiPersona();
  var html = '<div class="agg-selector">';
  if (persona === 'support_centre_store' || persona === 'retail_regional') {
    html += '<span class="agg-label">Group by:</span>';
    html += aggBtn('division', 'Division', AppState.storeAgg, 'setStoreAgg');
    html += aggBtn('stg', 'Format', AppState.storeAgg, 'setStoreAgg');
    html += aggBtn('store', 'Store', AppState.storeAgg, 'setStoreAgg');
  } else {
    html += '<span class="agg-label">Group by:</span>';
    html += aggBtn('cluster', 'Cluster', AppState.productAgg, 'setProductAgg');
    html += aggBtn('category', 'Category', AppState.productAgg, 'setProductAgg');
    html += aggBtn('superGroup', 'Department', AppState.productAgg, 'setProductAgg');
    html += aggBtn('productGroup', 'Product Group', AppState.productAgg, 'setProductAgg');
  }
  html += '</div>';
  return html;
}

function aggBtn(value, label, current, fn) {
  var cls = value === current ? 'agg-btn active' : 'agg-btn';
  return '<button class="' + cls + '" onclick="' + fn + '(\'' + value + '\')">' + label + '</button>';
}

// ================================================================
// RENDER DRILL RESULTS
// ================================================================

function renderDrillResults(data, dimension) {
  var container = document.getElementById('dashboard-content');
  var items = data.items || [];
  var summary = data.summary || {};
  var isTerminal = data.terminal;
  var isPivot = data.pivot_mode === true;

  var html = '';

  // KPIs for current scope
  html += '<div class="kpi-grid">';
  html += kpiCard('GAPs', fmtNum(summary.gaps), '', 'accent-red');
  html += kpiCard('LOWs', fmtNum(summary.lows), 'Sales: ' + fmtNum(summary.sales_lows) + ' | Space: ' + fmtNum(summary.space_lows), 'accent-amber');
  html += '</div>';

  // Toggles still active during drill
  html += renderToggles();

  if (isPivot && isTerminal) {
    // Pivot terminal: products with reason code columns
    html += '<div class="section-title-row"><div class="section-title">Products — Reason Code Breakdown</div></div>';
    html += '<div class="table-wrapper" id="pivot-terminal-table"></div>';
    container.innerHTML = html;
    renderPivotTerminalTable(items);
  } else if (isPivot && !isTerminal) {
    // Pivot intermediate: categories/groups with reason code columns
    html += renderDrillAggSelector();
    html += '<div class="chart-card" style="margin-bottom:14px"><div class="chart-card-header"><div class="chart-title">' + escHtml(dimension) + ' — Reason Code Breakdown</div></div><div class="chart-wrap"><canvas id="chart-drill"></canvas></div></div>';
    html += '<div class="table-wrapper" id="drill-table"></div>';
    container.innerHTML = html;
    renderPivotDrillChart(items);
    renderPivotTable(items, getNextDrillDimension());
  } else if (isTerminal) {
    // Standard terminal view with show/hide columns
    html += renderColumnToggle();
    html += '<div class="table-wrapper" id="terminal-table"></div>';
    container.innerHTML = html;
    renderTerminalTable(items);
  } else {
    // Standard aggregation selector for next level
    html += renderDrillAggSelector();
    html += '<div class="chart-card" style="margin-bottom:14px"><div class="chart-card-header"><div class="chart-title">' + escHtml(dimension) + ' Breakdown</div></div><div class="chart-wrap"><canvas id="chart-drill"></canvas></div></div>';
    html += '<div class="table-wrapper" id="drill-table"></div>';
    container.innerHTML = html;
    renderDrillChart(items, dimension);
    renderDrillTable(items, dimension);
  }
}

function renderDrillAggSelector() {
  var depth = AppState.drillPath.length;
  var persona = getApiPersona();
  var html = '<div class="agg-selector">';

  // Determine what level we're about to show
  if (persona === 'support_centre_store') {
    if (depth === 1) {
      // Inside a store, now showing product agg
      html += '<span class="agg-label">Product level:</span>';
      html += aggBtn('category', 'Category', AppState.productAgg, 'setProductAgg');
      html += aggBtn('superGroup', 'Department', AppState.productAgg, 'setProductAgg');
      html += aggBtn('productGroup', 'Product Group', AppState.productAgg, 'setProductAgg');
    }
  } else if (persona === 'support_centre_category') {
    if (depth === 1) {
      html += '<span class="agg-label">Store level:</span>';
      html += aggBtn('division', 'Division', AppState.storeAgg, 'setStoreAgg');
      html += aggBtn('stg', 'Format', AppState.storeAgg, 'setStoreAgg');
      html += aggBtn('store', 'Store', AppState.storeAgg, 'setStoreAgg');
    }
  } else if (persona === 'retail_regional') {
    if (depth === 1) {
      html += '<span class="agg-label">Product level:</span>';
      html += aggBtn('category', 'Category', AppState.productAgg, 'setProductAgg');
      html += aggBtn('superGroup', 'Department', AppState.productAgg, 'setProductAgg');
      html += aggBtn('productGroup', 'Product Group', AppState.productAgg, 'setProductAgg');
    }
  }

  html += '</div>';
  return html;
}

function renderColumnToggle() {
  var visible = ALL_PRODUCT_COLS.filter(function(c) { return AppState.visibleColumns[c.key]; }).length;
  var total = ALL_PRODUCT_COLS.length;
  var html = '<div class="col-popover-wrap" id="col-popover-wrap">';
  html += '<div class="col-popover-backdrop" id="col-popover-backdrop" onclick="closeColumnPopover()"></div>';
  html += '<button class="col-popover-trigger" id="col-popover-trigger" onclick="toggleColumnPopover()">';
  html += '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 3h7a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-7m0-18H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h7m0-18v18"/><path d="M3 9h18M3 15h18"/></svg>';
  html += '<span>Columns</span>';
  html += '<span class="col-count">' + visible + '/' + total + '</span>';
  html += '</button>';
  html += '<div class="col-popover-panel" id="col-popover-panel">';
  html += '<div class="col-popover-header">';
  html += '<span class="col-popover-title">Visible Columns</span>';
  html += '<div class="col-popover-actions">';
  html += '<button class="col-popover-action" onclick="colShowAll()">Show All</button>';
  html += '<button class="col-popover-action" onclick="colReset()">Reset</button>';
  html += '</div></div>';
  html += '<div class="col-popover-list">';
  ALL_PRODUCT_COLS.forEach(function(col) {
    var checked = AppState.visibleColumns[col.key] ? ' checked' : '';
    html += '<div class="col-popover-item" onclick="toggleColumn(\'' + col.key + '\')">';
    html += '<input type="checkbox"' + checked + ' tabindex="-1">';
    html += '<label>' + escHtml(col.label) + '</label>';
    html += '</div>';
  });
  html += '</div></div></div>';
  return html;
}

function toggleColumnPopover() {
  var panel = document.getElementById('col-popover-panel');
  var trigger = document.getElementById('col-popover-trigger');
  var backdrop = document.getElementById('col-popover-backdrop');
  if (!panel) return;
  var isOpen = panel.classList.contains('open');
  if (isOpen) {
    closeColumnPopover();
  } else {
    panel.classList.add('open');
    trigger.classList.add('open');
    backdrop.classList.add('open');
  }
}

function closeColumnPopover() {
  var panel = document.getElementById('col-popover-panel');
  var trigger = document.getElementById('col-popover-trigger');
  var backdrop = document.getElementById('col-popover-backdrop');
  if (panel) panel.classList.remove('open');
  if (trigger) trigger.classList.remove('open');
  if (backdrop) backdrop.classList.remove('open');
}

function toggleColumn(key) {
  AppState.visibleColumns[key] = !AppState.visibleColumns[key];
  // Update count badge
  var visible = ALL_PRODUCT_COLS.filter(function(c) { return AppState.visibleColumns[c.key]; }).length;
  var countEl = document.querySelector('#col-popover-wrap .col-count');
  if (countEl) countEl.textContent = visible + '/' + ALL_PRODUCT_COLS.length;
  // Update checkbox state in popover
  var panel = document.getElementById('col-popover-panel');
  if (panel) {
    var items = panel.querySelectorAll('.col-popover-item');
    items.forEach(function(item, i) {
      var cb = item.querySelector('input[type="checkbox"]');
      if (cb && ALL_PRODUCT_COLS[i]) cb.checked = AppState.visibleColumns[ALL_PRODUCT_COLS[i].key];
    });
  }
  // Re-render table
  var table = document.getElementById('terminal-table');
  if (table && table._data) renderTerminalTable(table._data);
}

function colShowAll() {
  ALL_PRODUCT_COLS.forEach(function(c) { AppState.visibleColumns[c.key] = true; });
  refreshColumnPopover();
}

function colReset() {
  var defaults = {product:true, upc:true, store:true, issue:true, reason_code:true, supplier_short_qty:true, scarcity_qty:true, waste_qty:true, under_forecast_qty:true, under_space_qty:true};
  ALL_PRODUCT_COLS.forEach(function(c) { AppState.visibleColumns[c.key] = !!defaults[c.key]; });
  refreshColumnPopover();
}

function refreshColumnPopover() {
  var visible = ALL_PRODUCT_COLS.filter(function(c) { return AppState.visibleColumns[c.key]; }).length;
  var countEl = document.querySelector('#col-popover-wrap .col-count');
  if (countEl) countEl.textContent = visible + '/' + ALL_PRODUCT_COLS.length;
  var panel = document.getElementById('col-popover-panel');
  if (panel) {
    var items = panel.querySelectorAll('.col-popover-item');
    items.forEach(function(item, i) {
      var cb = item.querySelector('input[type="checkbox"]');
      if (cb && ALL_PRODUCT_COLS[i]) cb.checked = AppState.visibleColumns[ALL_PRODUCT_COLS[i].key];
    });
  }
  var table = document.getElementById('terminal-table');
  if (table && table._data) renderTerminalTable(table._data);
}

function renderTerminalTable(items) {
  var el = document.getElementById('terminal-table');
  if (!el) return;
  el._data = items;

  var cols = ALL_PRODUCT_COLS.filter(function(c) { return AppState.visibleColumns[c.key]; });

  var html = '<table><thead><tr>';
  cols.forEach(function(c) {
    var isNum = c.key.indexOf('_qty') !== -1;
    html += '<th' + (isNum ? ' class="num"' : '') + '>' + escHtml(c.label) + '</th>';
  });
  html += '</tr></thead><tbody>';

  if (!items.length) {
    html += '<tr><td colspan="' + cols.length + '" style="text-align:center;padding:20px;color:var(--text-sub)">No data at this level</td></tr>';
  }

  items.forEach(function(item) {
    html += '<tr>';
    cols.forEach(function(c) {
      var val = item[c.key] || '';
      if (c.key === 'issue') {
        var badge = val === 'GAP' ? 'badge-critical' : val === 'LOW' ? 'badge-warning' : 'badge-healthy';
        html += '<td><span class="badge ' + badge + '">' + escHtml(val) + '</span></td>';
      } else if (c.key.indexOf('_qty') !== -1) {
        var num = parseFloat(val) || 0;
        html += '<td class="num">' + (num > 0 ? '<strong>' + fmtNum(Math.round(num)) + '</strong>' : '<span style="color:var(--text-dim)">-</span>') + '</td>';
      } else {
        html += '<td>' + escHtml(val) + '</td>';
      }
    });
    html += '</tr>';
  });
  html += '</tbody></table>';
  html += '<div class="table-footer">Showing ' + items.length + ' product-locations</div>';
  el.innerHTML = html;
}

function renderDrillTable(items, dimension) {
  var el = document.getElementById('drill-table');
  if (!el) return;

  // Sort by filtered metric descending
  var sorted = items.slice().sort(function(a, b) { return getFilteredMetricValue(b) - getFilteredMetricValue(a); });

  var html = '<table><thead><tr>';
  html += '<th>Name</th><th class="num">Gaps</th><th class="num">Lows</th><th class="num">Sales</th><th class="num">Space</th><th class="num">% ' + getFilteredMetricLabel() + '</th><th>Top Reason</th>';
  html += '</tr></thead><tbody>';

  sorted.forEach(function(item) {
    var pct = getFilteredPct(item);
    var badgeClass = pct > 5 ? 'badge-critical' : pct > 2 ? 'badge-warning' : 'badge-healthy';
    var topReason = (item.reasons && item.reasons.length > 0) ? item.reasons[0].code + ' (' + item.reasons[0].pct + '%)' : '';
    html += '<tr class="drillable-row" onclick="drillDown(\'' + escAttr(dimension) + '\', \'' + escAttr(item.name) + '\')">';
    html += '<td>' + escHtml(item.name) + ' <span class="drill-indicator">&#8250;</span></td>';
    html += '<td class="num">' + fmtNum(item.gaps) + '</td>';
    html += '<td class="num">' + fmtNum(item.lows) + '</td>';
    html += '<td class="num">' + fmtNum(item.sales_lows) + '</td>';
    html += '<td class="num">' + fmtNum(item.space_lows) + '</td>';
    html += '<td class="num"><span class="badge ' + badgeClass + '">' + pct + '%</span></td>';
    html += '<td>' + escHtml(topReason) + '</td>';
    html += '</tr>';
  });
  html += '</tbody></table>';
  html += '<div class="table-footer">Showing ' + sorted.length + ' items</div>';
  el.innerHTML = html;
}

function renderAggTable(items) {
  var el = document.getElementById('dash-table');
  if (!el) return;
  el._allData = items;

  // Sort by filtered metric descending
  var sorted = items.slice().sort(function(a, b) { return getFilteredMetricValue(b) - getFilteredMetricValue(a); });

  var persona = getApiPersona();
  var dimLabel = (persona === 'support_centre_store' || persona === 'retail_regional') ? 'Store' : 'Category';

  var html = '<table><thead><tr>';
  html += '<th>' + dimLabel + '</th><th class="num">Gaps</th><th class="num">Lows</th><th class="num">Sales</th><th class="num">Space</th><th class="num">% ' + getFilteredMetricLabel() + '</th><th>Top Reason</th>';
  html += '</tr></thead><tbody>';

  sorted.forEach(function(item) {
    var pct = getFilteredPct(item);
    var badgeClass = pct > 5 ? 'badge-critical' : pct > 2 ? 'badge-warning' : 'badge-healthy';
    var topReason = (item.reasons && item.reasons.length > 0) ? item.reasons[0].code + ' (' + item.reasons[0].pct + '%)' : '';
    var nextDim = getNextDrillDimension();
    html += '<tr class="drillable-row" onclick="drillDown(\'' + escAttr(nextDim) + '\', \'' + escAttr(item.name) + '\')">';
    html += '<td>' + escHtml(item.name) + ' <span class="drill-indicator">&#8250;</span></td>';
    html += '<td class="num">' + fmtNum(item.gaps) + '</td>';
    html += '<td class="num">' + fmtNum(item.lows) + '</td>';
    html += '<td class="num">' + fmtNum(item.sales_lows) + '</td>';
    html += '<td class="num">' + fmtNum(item.space_lows) + '</td>';
    html += '<td class="num"><span class="badge ' + badgeClass + '">' + pct + '%</span></td>';
    html += '<td>' + escHtml(topReason) + '</td>';
    html += '</tr>';
  });
  html += '</tbody></table>';
  html += '<div class="table-footer">Showing ' + sorted.length + ' items</div>';
  el.innerHTML = html;
}

function filterDashTable() {
  var el = document.getElementById('dash-table');
  if (!el || !el._allData) return;
  var query = (document.getElementById('dash-search') || {}).value || '';
  query = query.toLowerCase().trim();
  var filtered = query ? el._allData.filter(function(r) { return (r.name || '').toLowerCase().indexOf(query) !== -1; }) : el._allData;
  // Use pivot table if in pivot mode
  if (AppState.dashboardData && AppState.dashboardData.pivot_mode) {
    renderPivotTable(filtered, getNextDrillDimension());
  } else {
    renderAggTable(filtered);
  }
}

// ================================================================
// CHARTS
// ================================================================

function renderReasonChart(reasons) {
  destroyChart('chart-reasons');
  var ctx = document.getElementById('chart-reasons');
  if (!ctx || !reasons.length) return;
  var labels = reasons.map(function(r) { return r.reason_code || 'Unknown'; });
  var values = reasons.map(function(r) { return parseInt(r.count) || 0; });
  var colors = ['#c8102e','#d97706','#7A2048','#1e5a7a','#949494','#5B8C3A','#b45309','#3d5a80','#6b7280','#0e7490','#7c3aed'];

  AppState.charts['chart-reasons'] = new Chart(ctx, {
    type: 'doughnut',
    data: { labels: labels, datasets: [{ data: values, backgroundColor: colors.slice(0, labels.length), borderColor: '#fff', borderWidth: 2 }] },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { position: 'right', labels: { font: { size: 11 }, color: '#707070' } } }
    }
  });
}

function renderAggChart(items) {
  destroyChart('chart-agg');
  var ctx = document.getElementById('chart-agg');
  if (!ctx || !items.length) return;
  // Sort by filtered metric % descending for chart
  var sorted = items.slice().sort(function(a, b) { return getFilteredPct(b) - getFilteredPct(a); });
  var top = sorted.slice(0, 15);
  var labels = top.map(function(i) { return i.name || ''; });
  var chartData = top.map(function(i) { return getFilteredPct(i); });
  var metricLabel = getFilteredMetricLabel();
  var barColor = AppState.issueFilter === 'lows' ? '#d97706' : '#c8102e';

  AppState.charts['chart-agg'] = new Chart(ctx, {
    type: 'bar',
    data: { labels: labels, datasets: [{ label: '% ' + metricLabel, data: chartData, backgroundColor: barColor, borderRadius: 2 }] },
    options: {
      indexAxis: 'y', responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { grid: { color: 'rgba(0,0,0,.06)' }, ticks: { color: '#707070', font: { size: 11 } }, title: { display: true, text: '% PLs with ' + metricLabel } },
        y: { grid: { display: false }, ticks: { color: '#707070', font: { size: 10 } } }
      },
      onClick: function(event, elements) {
        if (elements.length === 0) return;
        var idx = elements[0].index;
        var label = labels[idx];
        if (label) drillDown(getNextDrillDimension(), label);
      }
    }
  });
}

function renderDrillChart(items, dimension) {
  destroyChart('chart-drill');
  var ctx = document.getElementById('chart-drill');
  if (!ctx || !items.length) return;
  var sorted = items.slice().sort(function(a, b) { return getFilteredPct(b) - getFilteredPct(a); });
  var top = sorted.slice(0, 15);
  var labels = top.map(function(i) { return i.name || ''; });
  var chartData = top.map(function(i) { return getFilteredPct(i); });
  var metricLabel = getFilteredMetricLabel();
  var barColor = AppState.issueFilter === 'lows' ? '#d97706' : '#c8102e';

  AppState.charts['chart-drill'] = new Chart(ctx, {
    type: 'bar',
    data: { labels: labels, datasets: [{ label: '% ' + metricLabel, data: chartData, backgroundColor: barColor, borderRadius: 2 }] },
    options: {
      indexAxis: 'y', responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { grid: { color: 'rgba(0,0,0,.06)' }, ticks: { color: '#707070', font: { size: 11 } } },
        y: { grid: { display: false }, ticks: { color: '#707070', font: { size: 10 } } }
      },
      onClick: function(event, elements) {
        if (elements.length === 0) return;
        var idx = elements[0].index;
        var label = labels[idx];
        if (label) drillDown(dimension, label);
      }
    }
  });
}

function destroyChart(key) {
  if (AppState.charts[key]) { AppState.charts[key].destroy(); delete AppState.charts[key]; }
}

// ================================================================
// PIVOT TABLE — Reason Code Breakdown (Head Office Store view)
// ================================================================

var PIVOT_COLS = [
  {key: 'for_investigation', label: 'For Investigation'},
  {key: 'forecast', label: 'Forecast'},
  {key: 'known_gap', label: 'Known Gap'},
  {key: 'low_depot_stock', label: 'Low Depot Stock'},
  {key: 'partially_supplied', label: 'Partially Supplied'},
  {key: 'stockfile_adj', label: 'Stockfile Adj'},
  {key: 'waste', label: 'Waste'},
  {key: 'other', label: 'Other'}
];

function renderPivotTable(items, drillDimension) {
  var el = document.getElementById('dash-table') || document.getElementById('drill-table');
  if (!el) return;
  el._allData = items;

  var sorted = items.slice().sort(function(a, b) { return (parseInt(b.grand_total)||0) - (parseInt(a.grand_total)||0); });

  var html = '<table class="pivot-table"><thead><tr>';
  html += '<th>Name</th>';
  PIVOT_COLS.forEach(function(c) { html += '<th class="num">' + c.label + '</th>'; });
  html += '<th class="num pivot-total">Grand Total</th>';
  html += '</tr></thead><tbody>';

  if (!sorted.length) {
    html += '<tr><td colspan="' + (PIVOT_COLS.length + 2) + '" style="text-align:center;padding:20px;color:var(--text-sub)">No data at this level</td></tr>';
  }

  sorted.forEach(function(item) {
    html += '<tr class="drillable-row" onclick="drillDown(\'' + escAttr(drillDimension) + '\', \'' + escAttr(item.name) + '\')">';
    html += '<td>' + escHtml(item.name) + ' <span class="drill-indicator">&#8250;</span></td>';
    PIVOT_COLS.forEach(function(c) {
      var val = parseInt(item[c.key]) || 0;
      html += '<td class="num">' + (val > 0 ? fmtNum(val) : '<span class="pivot-zero">-</span>') + '</td>';
    });
    var gt = parseInt(item.grand_total) || 0;
    html += '<td class="num pivot-total"><strong>' + fmtNum(gt) + '</strong></td>';
    html += '</tr>';
  });

  // Grand total row
  var totals = {};
  PIVOT_COLS.forEach(function(c) { totals[c.key] = 0; });
  totals.grand_total = 0;
  sorted.forEach(function(item) {
    PIVOT_COLS.forEach(function(c) { totals[c.key] += parseInt(item[c.key]) || 0; });
    totals.grand_total += parseInt(item.grand_total) || 0;
  });
  html += '<tr class="pivot-totals-row">';
  html += '<td><strong>Grand Total</strong></td>';
  PIVOT_COLS.forEach(function(c) {
    html += '<td class="num"><strong>' + fmtNum(totals[c.key]) + '</strong></td>';
  });
  html += '<td class="num pivot-total"><strong>' + fmtNum(totals.grand_total) + '</strong></td>';
  html += '</tr>';

  html += '</tbody></table>';
  html += '<div class="table-footer">Showing ' + sorted.length + ' items</div>';
  el.innerHTML = html;
}

function renderPivotTerminalTable(items) {
  var el = document.getElementById('pivot-terminal-table');
  if (!el) return;

  var sorted = items.slice().sort(function(a, b) { return (parseInt(b.grand_total)||0) - (parseInt(a.grand_total)||0); });

  var html = '<table class="pivot-table"><thead><tr>';
  html += '<th>Product</th><th>Store</th>';
  PIVOT_COLS.forEach(function(c) { html += '<th class="num">' + c.label + '</th>'; });
  html += '<th class="num pivot-total">Grand Total</th>';
  html += '</tr></thead><tbody>';

  if (!sorted.length) {
    html += '<tr><td colspan="' + (PIVOT_COLS.length + 3) + '" style="text-align:center;padding:20px;color:var(--text-sub)">No data at this level</td></tr>';
  }

  sorted.forEach(function(item) {
    html += '<tr>';
    html += '<td>' + escHtml(item.product || '') + '</td>';
    html += '<td>' + escHtml(item.store || '') + '</td>';
    PIVOT_COLS.forEach(function(c) {
      var val = parseInt(item[c.key]) || 0;
      html += '<td class="num">' + (val > 0 ? fmtNum(val) : '<span class="pivot-zero">-</span>') + '</td>';
    });
    var gt = parseInt(item.grand_total) || 0;
    html += '<td class="num pivot-total"><strong>' + fmtNum(gt) + '</strong></td>';
    html += '</tr>';
  });

  // Grand total row
  var totals = {};
  PIVOT_COLS.forEach(function(c) { totals[c.key] = 0; });
  totals.grand_total = 0;
  sorted.forEach(function(item) {
    PIVOT_COLS.forEach(function(c) { totals[c.key] += parseInt(item[c.key]) || 0; });
    totals.grand_total += parseInt(item.grand_total) || 0;
  });
  html += '<tr class="pivot-totals-row">';
  html += '<td colspan="2"><strong>Grand Total</strong></td>';
  PIVOT_COLS.forEach(function(c) {
    html += '<td class="num"><strong>' + fmtNum(totals[c.key]) + '</strong></td>';
  });
  html += '<td class="num pivot-total"><strong>' + fmtNum(totals.grand_total) + '</strong></td>';
  html += '</tr>';

  html += '</tbody></table>';
  html += '<div class="table-footer">Showing ' + sorted.length + ' products</div>';
  el.innerHTML = html;
}

function renderPivotStackedChart(items) {
  destroyChart('chart-agg');
  var ctx = document.getElementById('chart-agg');
  if (!ctx || !items.length) return;

  var sorted = items.slice().sort(function(a, b) { return (parseInt(b.grand_total)||0) - (parseInt(a.grand_total)||0); });
  var top = sorted.slice(0, 10);
  var labels = top.map(function(i) { return i.name || ''; });

  var colors = ['#c8102e','#d97706','#7A2048','#1e5a7a','#949494','#5B8C3A','#b45309','#3d5a80'];
  var datasets = PIVOT_COLS.map(function(col, idx) {
    return {
      label: col.label,
      data: top.map(function(i) { return parseInt(i[col.key]) || 0; }),
      backgroundColor: colors[idx % colors.length],
      borderRadius: 1
    };
  });

  AppState.charts['chart-agg'] = new Chart(ctx, {
    type: 'bar',
    data: { labels: labels, datasets: datasets },
    options: {
      indexAxis: 'y', responsive: true, maintainAspectRatio: false,
      plugins: { legend: { position: 'bottom', labels: { font: { size: 10 }, color: '#707070', boxWidth: 12 } } },
      scales: {
        x: { stacked: true, grid: { color: 'rgba(0,0,0,.06)' }, ticks: { color: '#707070', font: { size: 11 } } },
        y: { stacked: true, grid: { display: false }, ticks: { color: '#707070', font: { size: 10 } } }
      },
      onClick: function(event, elements) {
        if (elements.length === 0) return;
        var idx = elements[0].index;
        var label = labels[idx];
        if (label) drillDown(getNextDrillDimension(), label);
      }
    }
  });
}

function renderPivotDrillChart(items) {
  destroyChart('chart-drill');
  var ctx = document.getElementById('chart-drill');
  if (!ctx || !items.length) return;

  var sorted = items.slice().sort(function(a, b) { return (parseInt(b.grand_total)||0) - (parseInt(a.grand_total)||0); });
  var top = sorted.slice(0, 10);
  var labels = top.map(function(i) { return i.name || ''; });

  var colors = ['#c8102e','#d97706','#7A2048','#1e5a7a','#949494','#5B8C3A','#b45309','#3d5a80'];
  var datasets = PIVOT_COLS.map(function(col, idx) {
    return {
      label: col.label,
      data: top.map(function(i) { return parseInt(i[col.key]) || 0; }),
      backgroundColor: colors[idx % colors.length],
      borderRadius: 1
    };
  });

  AppState.charts['chart-drill'] = new Chart(ctx, {
    type: 'bar',
    data: { labels: labels, datasets: datasets },
    options: {
      indexAxis: 'y', responsive: true, maintainAspectRatio: false,
      plugins: { legend: { position: 'bottom', labels: { font: { size: 10 }, color: '#707070', boxWidth: 12 } } },
      scales: {
        x: { stacked: true, grid: { color: 'rgba(0,0,0,.06)' }, ticks: { color: '#707070', font: { size: 11 } } },
        y: { stacked: true, grid: { display: false }, ticks: { color: '#707070', font: { size: 10 } } }
      },
      onClick: function(event, elements) {
        if (elements.length === 0) return;
        var idx = elements[0].index;
        var label = labels[idx];
        if (label) drillDown(getNextDrillDimension(), label);
      }
    }
  });
}

// ================================================================
// MORNING BRIEFING
// ================================================================

function loadBriefing(storeName) {
  var el = document.getElementById('briefing-content');
  el.innerHTML = renderSkeleton();

  fetch('/api/store-briefing/' + encodeURIComponent(storeName) + '?persona=' + getApiPersona())
    .then(function(r) { return r.json(); })
    .then(function(d) { AppState.briefingData = d; renderBriefing(d); })
    .catch(function(e) { el.innerHTML = errorState(e.message); });
}

function renderBriefing(data) {
  var el = document.getElementById('briefing-content');
  var kpi = data.kpis || {};
  var reasons = data.reasons || [];

  var gaps = parseInt(kpi.gaps) || 0;
  var storeName = AppState.selectedStore || 'your store';

  var html = '';

  // Export PDF button
  html += '<div class="briefing-toolbar">';
  html += '<button class="export-btn" onclick="exportBriefingPDF()">';
  html += '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/></svg>';
  html += ' Export PDF';
  html += '</button>';
  html += '</div>';

  // Printable content wrapper (this div gets captured for PDF)
  html += '<div id="briefing-printable">';

  // Morning greeting
  html += '<div class="briefing-greeting">';
  html += '<p>Good morning <strong>' + escHtml(storeName) + '</strong> &#128578;</p>';
  html += '<p>You have opened with <strong>' + fmtNum(gaps) + ' Expected Gaps</strong> this morning, we will review and action all of the supply chain gaps below, but wanted to share the reason codes and category breakdown for your information:</p>';
  html += '</div>';

  // Reason code breakdown
  if (reasons.length > 0) {
    html += '<div class="briefing-section-title">Reason Code Breakdown</div>';
    html += '<ul class="briefing-bullets">';
    reasons.forEach(function(r) {
      html += '<li><span class="bullet-count">' + fmtNum(r.count) + '</span><span class="bullet-pct">(' + r.pct + '%)</span>' + escHtml(r.reason_code || 'Unknown') + '</li>';
    });
    html += '</ul>';
  }

  // Category × Reason Code Breakdown (pivot table)
  var catReason = data.category_reason_breakdown || [];
  if (catReason.length > 0) {
    AppState.briefingCatReason = catReason;
    AppState.briefingCatSelected = catReason.map(function(c) { return c.category; });
    html += '<div class="briefing-section-title">Category Breakdown by Reason Code</div>';
    html += '<div class="briefing-cat-filter-row" id="briefing-cat-filter-row">';
    html += renderBriefingCatFilter(catReason);
    html += '</div>';
    html += '<div class="table-wrapper" id="briefing-cat-table-wrap">';
    html += renderBriefingCatTable(catReason);
    html += '</div>';
  }

  html += '</div>'; // close briefing-printable

  el.innerHTML = html;
}

function exportBriefingPDF() {
  var element = document.getElementById('briefing-printable');
  if (!element) return;
  var storeName = (AppState.selectedStore || 'Store').replace(/[^a-zA-Z0-9_-]/g, '_');
  var today = new Date().toISOString().split('T')[0];
  var filename = storeName + '_morning_briefing_' + today + '.pdf';

  var opt = {
    margin: [10, 10, 10, 10],
    filename: filename,
    image: { type: 'jpeg', quality: 0.98 },
    html2canvas: { scale: 2, useCORS: true, letterRendering: true },
    jsPDF: { unit: 'mm', format: 'a4', orientation: 'landscape' },
    pagebreak: { mode: ['avoid-all', 'css', 'legacy'] }
  };

  html2pdf().set(opt).from(element).save();
}

// --- Briefing: Category Reason Filter & Table ---

function renderBriefingCatFilter(catReason) {
  var allCats = catReason.map(function(c) { return c.category; });
  var selected = AppState.briefingCatSelected || allCats;
  var allSelected = selected.length === allCats.length;
  var html = '<div class="col-popover-wrap" style="position:relative;display:inline-block">';
  html += '<button class="col-popover-trigger" onclick="toggleBriefingCatPopover()">';
  html += '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 6h18M3 12h18M3 18h18"/></svg>';
  html += ' Categories (' + selected.length + '/' + allCats.length + ')';
  html += '</button>';
  html += '<div class="col-popover-panel" id="briefing-cat-popover" style="display:none">';
  html += '<div class="col-popover-header">';
  html += '<span onclick="briefingCatShowAll()" class="col-popover-action">Show All</span>';
  html += '<span onclick="briefingCatClearAll()" class="col-popover-action">Clear All</span>';
  html += '</div>';
  html += '<div class="col-popover-list">';
  allCats.forEach(function(cat) {
    var checked = selected.indexOf(cat) !== -1 ? 'checked' : '';
    html += '<label class="col-popover-item"><input type="checkbox" ' + checked + ' onchange="toggleBriefingCat(\'' + escHtml(cat).replace(/'/g, "\\'") + '\')"> ' + escHtml(cat) + '</label>';
  });
  html += '</div></div></div>';
  // Export button
  html += ' <button class="export-btn" onclick="exportBriefingCatCSV()">';
  html += '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>';
  html += ' Export';
  html += '</button>';
  return html;
}

function renderBriefingCatTable(catReason) {
  var selected = AppState.briefingCatSelected || [];
  var filtered = catReason.filter(function(c) { return selected.indexOf(c.category) !== -1; });

  // Compute totals row
  var totals = { for_investigation: 0, forecast: 0, known_gap: 0, low_depot_stock: 0, partially_supplied: 0, stockfile_adjustment: 0, waste: 0, other: 0, grand_total: 0 };
  filtered.forEach(function(c) {
    totals.for_investigation += parseInt(c.for_investigation) || 0;
    totals.forecast += parseInt(c.forecast) || 0;
    totals.known_gap += parseInt(c.known_gap) || 0;
    totals.low_depot_stock += parseInt(c.low_depot_stock) || 0;
    totals.partially_supplied += parseInt(c.partially_supplied) || 0;
    totals.stockfile_adjustment += parseInt(c.stockfile_adjustment) || 0;
    totals.waste += parseInt(c.waste) || 0;
    totals.other += parseInt(c.other) || 0;
    totals.grand_total += parseInt(c.grand_total) || 0;
  });

  var html = '<table><thead><tr>';
  html += '<th>Category</th><th class="num">For Investigation</th><th class="num">Forecast</th><th class="num">Known Gap</th>';
  html += '<th class="num">Low Depot Stock</th><th class="num">Partially Supplied</th><th class="num">Stockfile Adj</th>';
  html += '<th class="num">Waste</th><th class="num">Other</th><th class="num">Grand Total</th>';
  html += '</tr></thead><tbody>';
  filtered.forEach(function(c) {
    html += '<tr><td>' + escHtml(c.category) + '</td>';
    html += '<td class="num">' + fmtNum(c.for_investigation) + '</td>';
    html += '<td class="num">' + fmtNum(c.forecast) + '</td>';
    html += '<td class="num">' + fmtNum(c.known_gap) + '</td>';
    html += '<td class="num">' + fmtNum(c.low_depot_stock) + '</td>';
    html += '<td class="num">' + fmtNum(c.partially_supplied) + '</td>';
    html += '<td class="num">' + fmtNum(c.stockfile_adjustment) + '</td>';
    html += '<td class="num">' + fmtNum(c.waste) + '</td>';
    html += '<td class="num">' + fmtNum(c.other) + '</td>';
    html += '<td class="num"><strong>' + fmtNum(c.grand_total) + '</strong></td>';
    html += '</tr>';
  });
  // Grand total row
  html += '<tr class="table-total-row"><td><strong>Grand Total</strong></td>';
  html += '<td class="num"><strong>' + fmtNum(totals.for_investigation) + '</strong></td>';
  html += '<td class="num"><strong>' + fmtNum(totals.forecast) + '</strong></td>';
  html += '<td class="num"><strong>' + fmtNum(totals.known_gap) + '</strong></td>';
  html += '<td class="num"><strong>' + fmtNum(totals.low_depot_stock) + '</strong></td>';
  html += '<td class="num"><strong>' + fmtNum(totals.partially_supplied) + '</strong></td>';
  html += '<td class="num"><strong>' + fmtNum(totals.stockfile_adjustment) + '</strong></td>';
  html += '<td class="num"><strong>' + fmtNum(totals.waste) + '</strong></td>';
  html += '<td class="num"><strong>' + fmtNum(totals.other) + '</strong></td>';
  html += '<td class="num"><strong>' + fmtNum(totals.grand_total) + '</strong></td>';
  html += '</tr>';
  html += '</tbody></table>';
  html += '<div class="table-footer">Showing ' + filtered.length + ' of ' + catReason.length + ' categories</div>';
  return html;
}

function toggleBriefingCatPopover() {
  var panel = document.getElementById('briefing-cat-popover');
  if (!panel) return;
  panel.style.display = panel.style.display === 'none' ? 'block' : 'none';
}

function toggleBriefingCat(cat) {
  var idx = AppState.briefingCatSelected.indexOf(cat);
  if (idx === -1) { AppState.briefingCatSelected.push(cat); }
  else { AppState.briefingCatSelected.splice(idx, 1); }
  refreshBriefingCatTable();
  refreshBriefingCatFilterBtn();
}

function briefingCatShowAll() {
  AppState.briefingCatSelected = (AppState.briefingCatReason || []).map(function(c) { return c.category; });
  refreshBriefingCatTable();
  refreshBriefingCatUI();
}

function briefingCatClearAll() {
  AppState.briefingCatSelected = [];
  refreshBriefingCatTable();
  refreshBriefingCatUI();
}

function refreshBriefingCatTable() {
  var wrap = document.getElementById('briefing-cat-table-wrap');
  if (wrap) wrap.innerHTML = renderBriefingCatTable(AppState.briefingCatReason || []);
}

function refreshBriefingCatFilterBtn() {
  var row = document.getElementById('briefing-cat-filter-row');
  if (row) row.innerHTML = renderBriefingCatFilter(AppState.briefingCatReason || []);
  // Re-open the popover since user is still interacting
  var panel = document.getElementById('briefing-cat-popover');
  if (panel) panel.style.display = 'block';
}

function refreshBriefingCatUI() {
  var row = document.getElementById('briefing-cat-filter-row');
  if (row) row.innerHTML = renderBriefingCatFilter(AppState.briefingCatReason || []);
  var panel = document.getElementById('briefing-cat-popover');
  if (panel) panel.style.display = 'block';
}

// --- Export Category Breakdown to CSV ---
function exportBriefingCatCSV() {
  var selected = AppState.briefingCatSelected || [];
  var data = (AppState.briefingCatReason || []).filter(function(c) { return selected.indexOf(c.category) !== -1; });
  if (data.length === 0) return;

  var headers = ['Category','For Investigation','Forecast','Known Gap','Low Depot Stock','Partially Supplied','Stockfile Adj','Waste','Other','Grand Total'];
  var rows = [headers.join(',')];

  var totals = { for_investigation: 0, forecast: 0, known_gap: 0, low_depot_stock: 0, partially_supplied: 0, stockfile_adjustment: 0, waste: 0, other: 0, grand_total: 0 };
  data.forEach(function(c) {
    rows.push([
      '"' + (c.category || '').replace(/"/g, '""') + '"',
      c.for_investigation || 0, c.forecast || 0, c.known_gap || 0,
      c.low_depot_stock || 0, c.partially_supplied || 0, c.stockfile_adjustment || 0,
      c.waste || 0, c.other || 0, c.grand_total || 0
    ].join(','));
    totals.for_investigation += parseInt(c.for_investigation) || 0;
    totals.forecast += parseInt(c.forecast) || 0;
    totals.known_gap += parseInt(c.known_gap) || 0;
    totals.low_depot_stock += parseInt(c.low_depot_stock) || 0;
    totals.partially_supplied += parseInt(c.partially_supplied) || 0;
    totals.stockfile_adjustment += parseInt(c.stockfile_adjustment) || 0;
    totals.waste += parseInt(c.waste) || 0;
    totals.other += parseInt(c.other) || 0;
    totals.grand_total += parseInt(c.grand_total) || 0;
  });
  rows.push(['"Grand Total"', totals.for_investigation, totals.forecast, totals.known_gap, totals.low_depot_stock, totals.partially_supplied, totals.stockfile_adjustment, totals.waste, totals.other, totals.grand_total].join(','));

  var csv = rows.join('\n');
  var blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
  var url = URL.createObjectURL(blob);
  var a = document.createElement('a');
  var storeName = (AppState.selectedStore || 'all_stores').replace(/[^a-zA-Z0-9]/g, '_');
  var dateStr = new Date().toISOString().slice(0, 10);
  a.href = url;
  a.download = storeName + '_category_breakdown_' + dateStr + '.csv';
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

// ================================================================
// CHAT
// ================================================================

function sendChat() {
  var input = document.getElementById('chat-input');
  var msg = input.value.trim();
  if (!msg) return;
  input.value = '';

  var messagesEl = document.getElementById('chat-messages');
  messagesEl.innerHTML += '<div class="chat-bubble user"><div class="chat-bubble-content">' + escHtml(msg) + '</div></div>';
  messagesEl.innerHTML += '<div class="chat-bubble assistant" id="chat-loading"><div class="chat-bubble-content"><em id="chat-loading-text">Thinking…</em></div></div>';
  messagesEl.scrollTop = messagesEl.scrollHeight;

  var body = { message: msg, conversation_id: AppState.chatConversationId };
  if (AppState.selectedStore) body.store_name = AppState.selectedStore;

  fetch('/api/chat', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body) })
    .then(function(r) { return r.json(); })
    .then(function(d) {
      var loadEl = document.getElementById('chat-loading');
      if (loadEl) loadEl.remove();
      AppState.chatConversationId = d.conversation_id || null;
      var convId = d.conversation_id || '';
      var msgId = d.message_id || '';
      var rawText = d.text || 'No response received.';

      // Store context for feedback linkage
      if (msgId) {
        messageContext[msgId] = { question: msg, answer: rawText, sql: d.sql || '' };
      }

      // Render markdown (marked.js loaded in index.html)
      var content = '';
      try { content = marked.parse(rawText); } catch(e) { content = escHtml(rawText); }
      // If Genie returned a data table, render it as a styled table
      if (d.columns && d.rows && d.rows.length > 0) {
        content += '<div class="chat-table"><table><thead><tr>' +
          d.columns.map(function(c) { return '<th>' + escHtml(c) + '</th>'; }).join('') +
          '</tr></thead><tbody>' +
          d.rows.slice(0, 20).map(function(row) { return '<tr>' + row.map(function(v) { return '<td>' + escHtml(v || '') + '</td>'; }).join('') + '</tr>'; }).join('') +
          '</tbody></table></div>';
      }
      content += chatSource(d);
      // Feedback buttons (thumbs up/down)
      var feedbackHtml = '';
      if (convId && msgId) {
        feedbackHtml = '<div class="feedback-row">' +
          '<button class="feedback-btn" onclick="submitFeedback(\'' + convId + '\',\'' + msgId + '\',true,this)" title="Helpful">' +
            '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M7 22V11L2 13V22H7ZM7 11L11.5 2C12.9 2 14 3.1 14 4.5V9H20.1C20.6 9 21.1 9.2 21.4 9.6C21.7 10 21.8 10.5 21.7 11L19.7 20C19.5 20.9 18.7 21.5 17.8 21.5H7"/></svg>' +
          '</button>' +
          '<button class="feedback-btn" onclick="submitFeedback(\'' + convId + '\',\'' + msgId + '\',false,this)" title="Not helpful">' +
            '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M17 2V13L22 11V2H17ZM17 13L12.5 22C11.1 22 10 20.9 10 19.5V15H3.9C3.4 15 2.9 14.8 2.6 14.4C2.3 14 2.2 13.5 2.3 13L4.3 4C4.5 3.1 5.3 2.5 6.2 2.5H17"/></svg>' +
          '</button>' +
        '</div>';
      }
      messagesEl.innerHTML += '<div class="chat-bubble assistant"><div class="chat-bubble-content">' + content + feedbackHtml + '</div></div>';
      messagesEl.scrollTop = messagesEl.scrollHeight;
    })
    .catch(function(e) {
      var loadEl = document.getElementById('chat-loading');
      if (loadEl) loadEl.remove();
      messagesEl.innerHTML += '<div class="chat-bubble assistant"><div class="chat-bubble-content">Error: ' + escHtml(e.message) + '</div></div>';
    });
}

function renderSuggestedQuestions() {
  var el = document.getElementById('suggested-questions');
  if (!el) return;
  fetch('/api/suggested-questions')
    .then(function(r) { return r.json(); })
    .then(function(d) {
      var qs = (d && d.questions) || [];
      if (!qs.length) return;
      el.innerHTML = '<div class="suggested-label">Try a deep-dive question</div>' +
        qs.map(function(q) { return '<button class="suggested-chip" data-q="' + escHtml(q) + '" onclick="askSuggested(this)">' + escHtml(q) + '</button>'; }).join('');
    })
    .catch(function() {});
}

function askSuggested(btn) {
  var q = btn.getAttribute('data-q');
  if (!q) return;
  var input = document.getElementById('chat-input');
  input.value = q;
  sendChat();
}

// --- Feedback ---
function submitFeedback(convId, msgId, isPositive, btn) {
  var row = btn.parentElement;
  row.querySelectorAll('.feedback-btn').forEach(function(b) {
    b.classList.remove('active-up', 'active-down');
    b.style.pointerEvents = 'none';
  });
  btn.classList.add(isPositive ? 'active-up' : 'active-down');

  var ctx = messageContext[msgId] || {};
  fetch('/api/feedback', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      conversation_id: convId,
      message_id: msgId,
      is_positive: isPositive,
      comment: '',
      question: ctx.question || '',
      answer: ctx.answer || '',
      sql: ctx.sql || ''
    })
  }).catch(function() {});

  // Thumbs down → show feedback modal
  if (!isPositive) {
    pendingFeedback = { conversationId: convId, messageId: msgId };
    document.getElementById('feedback-modal').style.display = 'flex';
    document.getElementById('feedback-comment').value = '';
    document.getElementById('feedback-comment').focus();
  }
}

function closeFeedbackModal(e) {
  if (e && e.target !== e.currentTarget) return;
  document.getElementById('feedback-modal').style.display = 'none';
  pendingFeedback = null;
}

function submitFeedbackComment() {
  if (!pendingFeedback) return;
  var comment = document.getElementById('feedback-comment').value.trim();
  if (comment) {
    var ctx = messageContext[pendingFeedback.messageId] || {};
    fetch('/api/feedback', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        conversation_id: pendingFeedback.conversationId,
        message_id: pendingFeedback.messageId,
        is_positive: false,
        comment: comment,
        question: ctx.question || '',
        answer: ctx.answer || '',
        sql: ctx.sql || ''
      })
    }).catch(function() {});
  }
  closeFeedbackModal();
}

// ================================================================
// HELPERS
// ================================================================

function escHtml(s) { if (!s) return ''; return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'); }
function escAttr(s) { if (!s) return ''; return String(s).replace(/\\/g,'\\\\').replace(/'/g,"\\'").replace(/"/g,'&quot;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }
function fmtNum(v) { var n = parseInt(v) || 0; return n.toLocaleString(); }

function kpiCard(label, value, sub, accent) {
  var cls = accent ? 'kpi-card ' + accent : 'kpi-card';
  return '<div class="' + cls + '"><div class="kpi-label">' + escHtml(label) + '</div><div class="kpi-value">' + value + '</div><div class="kpi-sub">' + escHtml(sub) + '</div></div>';
}

function healthClass(score) { return score >= 70 ? 'health-good' : score >= 40 ? 'health-ok' : 'health-bad'; }

function renderSkeleton() {
  return '<div class="kpi-grid kpi-grid-5">' +
    '<div class="kpi-card skeleton"><div class="skeleton-line w60"></div><div class="skeleton-line-lg w80"></div><div class="skeleton-line w40"></div></div>'.repeat(5) +
    '</div>';
}

function errorState(msg) {
  return '<div class="empty-state"><div class="empty-state-icon">&#9888;</div><div class="empty-state-title">Error</div><div class="empty-state-text">' + escHtml(msg) + '</div></div>';
}


// ================================================================
// SHELF SCAN (SST) - barcode scan -> status + reason code
// ================================================================
var _sstClock = null;

function openSST(btn) {
  showTab('sst', btn);
  populateSstStores();
  updateHandheldTime();
  if (!_sstClock) _sstClock = setInterval(updateHandheldTime, 60000);
}

function populateSstStores() {
  var sel = document.getElementById('sst-store');
  if (!sel) return;
  var stores = (typeof AppState !== 'undefined' && AppState.storeList) || [];
  if (sel.dataset.filled === '1') return;
  sel.innerHTML = '<option value="">Select store...</option>' +
    stores.map(function(s){ return '<option value="' + escAttr(s) + '">' + escHtml(s) + '</option>'; }).join('');
  sel.dataset.filled = '1';
  if (!sel.value && stores.length) {
    sel.value = (stores.indexOf('Covent Garden') !== -1) ? 'Covent Garden' : stores[0];
    onSstStoreChange();
  }
}

function onSstStoreChange() {
  document.getElementById('sst-screen-content').innerHTML =
    '<div class="sst-idle"><div class="sst-idle-icon">&#128247;</div><div class="sst-idle-text">Scan a product barcode (UPC)<br>to view status &amp; reason</div></div>';
  document.getElementById('sst-upc').value = '';
  loadSstSamples();
  loadStoreActions(document.getElementById('sst-store').value);
}

function loadSstSamples() {
  var store = document.getElementById('sst-store').value;
  var wrap = document.getElementById('sst-samples');
  var dl = document.getElementById('sst-upc-list');
  if (!store) { wrap.innerHTML = ''; dl.innerHTML = ''; return; }
  fetch('/api/sst-samples?store=' + encodeURIComponent(store)).then(function(r){ return r.json(); }).then(function(d){
    var s = d.samples || [];
    dl.innerHTML = s.map(function(x){ return '<option value="' + escAttr(x.upc) + '">' + escAttr(x.product) + '</option>'; }).join('');
    wrap.innerHTML = '<span class="sst-samples-label">Quick scan:</span>' + s.map(function(x){
      return '<button class="sst-sample-chip" data-upc="' + escAttr(x.upc) + '" onclick="quickScan(this.dataset.upc)">' + escHtml(x.product) + '</button>';
    }).join('');
  }).catch(function(){ wrap.innerHTML = ''; });
}

function quickScan(upc) {
  document.getElementById('sst-upc').value = upc;
  scanSST();
}

function scanSST() {
  var store = document.getElementById('sst-store').value;
  var upc = document.getElementById('sst-upc').value.trim();
  var screen = document.getElementById('sst-screen-content');
  if (!store || !upc) {
    screen.innerHTML = '<div class="sst-idle"><div class="sst-idle-text" style="color:#f88">Select a store and enter a UPC</div></div>';
    return;
  }
  screen.innerHTML = '<div class="sst-idle"><div class="sst-idle-icon">&#8987;</div><div class="sst-idle-text">Scanning...</div></div>';
  fetch('/api/sst-lookup?store=' + encodeURIComponent(store) + '&upc=' + encodeURIComponent(upc))
    .then(function(r){ return r.json(); })
    .then(function(data){
      if (data.status === 'NOT_FOUND') {
        screen.innerHTML = '<div class="sst-idle" style="padding-top:60px"><div class="sst-idle-icon">&#10068;</div><div class="sst-idle-text">' + escHtml(data.message || 'Not ranged here') + '</div></div>';
        return;
      }
      if (data.status === 'NO_ISSUE') {
        screen.innerHTML = '<div style="text-align:center;padding-top:44px"><div class="sst-idle-icon" style="color:#00e676">&#10003;</div>' +
          '<div class="sst-result-product" style="margin-top:8px">' + escHtml(data.sst_display.product) + '</div>' +
          '<div class="sst-status-pill available">AVAILABLE</div>' +
          '<div class="sst-idle-text" style="color:#8f8;margin-top:6px">No gap - on shelf</div>' + sstTiming(data) + '</div>';
        return;
      }
      var d = data.sst_display;
      var statusClass = (d.status === 'GAP') ? 'gap' : 'low';
      var statusLabel = (d.status === 'LOW' && d.low_type) ? ('LOW - ' + (d.low_type === 'SALES_LOW' ? 'Sales' : 'Space')) : d.status;
      var qtyRow = d.qty_label ? ('<div class="sst-result-row"><span class="label">' + escHtml(d.qty_label) + '</span><span class="value">' + escHtml(String(Math.round(d.qty || 0))) + '</span></div>') : '';
      var actionsHtml = (d.actions || []).map(function(a) {
        return '<button class="sst-action-btn" onclick="recordAction(\'' + escAttr(store) + '\',\'' + escAttr(upc) + '\',\'' + escAttr(a.type) + '\',this)">' + escHtml(a.label) + '</button>';
      }).join('');
      var alsoFound = (d.evidence_found || '').split(',').filter(function(x) { return x && x !== d.reason_code; });
      screen.innerHTML =
        '<div class="sst-result">' +
          '<div class="sst-result-product">' + escHtml(d.product) + '</div>' +
          '<div class="sst-status-pill ' + statusClass + '">' + escHtml(statusLabel) + '</div>' +
          '<div class="sst-reason-box"><div class="sst-reason-label">REASON CODE</div><div class="sst-reason-code">' + escHtml(d.reason_code || '-') + '</div>' +
            (d.reason_text ? '<div class="sst-reason-text">' + escHtml(d.reason_text) + '</div>' : '') + '</div>' +
          '<div class="sst-result-row"><span class="label">Category</span><span class="value">' + escHtml(d.category || '-') + '</span></div>' +
          '<div class="sst-result-row"><span class="label">Supplier</span><span class="value">' + escHtml(d.supplier || '-') + '</span></div>' +
          '<div class="sst-result-row"><span class="label">Depot</span><span class="value">' + escHtml(d.depot || '-') + '</span></div>' +
          qtyRow +
          (alsoFound.length ? '<div class="sst-result-row"><span class="label">Also found</span><span class="value">' + escHtml(alsoFound.join(', ')) + '</span></div>' : '') +
          '<div class="sst-ai-insight"><div class="sst-ai-insight-header">&#9733; Next best action</div><div class="sst-ai-insight-text" id="sst-ai-text">Generating...</div></div>' +
          (actionsHtml ? '<div class="sst-actions-row">' + actionsHtml + '</div>' : '') +
          sstTiming(data) +
        '</div>';
      fetchSstExplain(store, upc, data.event);
    })
    .catch(function(e){ screen.innerHTML = '<div class="sst-idle"><div class="sst-idle-text" style="color:#f88">Error: ' + escHtml(String(e)) + '</div></div>'; });
}

function fetchSstExplain(store, upc, event) {
  var el = document.getElementById('sst-ai-text');
  fetch('/api/sst-explain', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ store: store, upc: upc, event_data: event }) })
    .then(function(r){ return r.json(); })
    .then(function(d){ if (el) el.textContent = d.explanation || 'No explanation available.'; })
    .catch(function(){ if (el) el.textContent = 'Unable to generate AI explanation.'; });
}

function updateHandheldTime() {
  var el = document.getElementById('handheld-time');
  if (el) el.textContent = new Date().toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' });
}


// ================================================================
// CHAT SOURCE LABELS
// ================================================================
function chatSource(d) {
  if (d.source === 'curated') {
    return '<div class="chat-source">Curated analysis: a fixed SQL analysis computed live from today\'s data</div>';
  }
  if (d.source === 'genie') {
    if (!d.sql) return '<div class="chat-source">Answered by Genie</div>';
    return '<div class="chat-source">Answered by Genie · <a href="#" onclick="this.parentElement.nextElementSibling.style.display=\'block\';this.remove();return false;">show the SQL</a></div>' +
      '<pre class="chat-sql" style="display:none">' + escHtml(d.sql) + '</pre>';
  }
  return '';
}

// ================================================================
// SHELF SCAN: timing, colleague actions
// ================================================================
function sstTiming(data) {
  if (data.lookup_ms === undefined) return '';
  var src = data.served_by === 'lakebase' ? 'Lakebase' : 'SQL warehouse';
  return '<div class="sst-timing">Answered from ' + src + ' in ' + Math.round(data.lookup_ms) + ' ms</div>';
}

var ACTION_LABELS = {
  RAISED_SHORTAGE_QUERY: 'Raised shortage query', FILLED_FROM_STOCKROOM: 'Filled from stockroom',
  CHASED_BLOCKED_ORDER: 'Chased blocked order', CORRECTED_STOCK_FILE: 'Corrected stock file',
  RAISED_ORDER: "Raised today's order", CHECKED_DATE_CODES: 'Checked date codes',
  REQUESTED_ORDER_REVIEW: 'Asked for order review', FILLED_WITH_ALTERNATIVE: 'Filled with alternative',
  CONFIRMED_PLANNED_GAP: 'Confirmed planned gap', ESCALATED_TO_ANALYST: 'Escalated to analyst'
};

function recordAction(store, upc, type, btn) {
  btn.disabled = true;
  fetch('/api/actions', { method: 'POST', headers: {'Content-Type': 'application/json'},
                          body: JSON.stringify({ store: store, upc: upc, action_type: type }) })
    .then(function(r) { return r.json().then(function(j) { if (!r.ok) throw new Error(j.detail || r.status); return j; }); })
    .then(function() {
      btn.textContent = '✓ ' + (ACTION_LABELS[type] || type) + ' - logged';
      btn.classList.add('done');
      loadStoreActions(store);
    })
    .catch(function(e) { btn.disabled = false; btn.textContent = 'Retry: ' + (ACTION_LABELS[type] || type); });
}

function loadStoreActions(store) {
  var el = document.getElementById('sst-actions');
  if (!el) return;
  if (!store) { el.innerHTML = ''; return; }
  fetch('/api/actions?store=' + encodeURIComponent(store))
    .then(function(r) { return r.json(); })
    .then(function(d) {
      var acts = d.actions || [];
      var list = acts.length ? acts.map(function(a) {
        var t = (a.created_at || '').slice(11, 16);
        return '<div class="action-item"><div class="action-top"><span class="action-label">' + escHtml(ACTION_LABELS[a.action_type] || a.action_type) +
          '</span><span class="action-time">' + escHtml(t) + '</span></div><div class="action-product">' + escHtml(a.product || a.upc) +
          ' · ' + escHtml((a.root_cause || '').replace(/_/g, ' ').toLowerCase()) + '</div></div>';
      }).join('') : '<div class="action-empty">No actions logged at this store yet. Scan a gap and record what you did.</div>';
      el.innerHTML = '<div class="action-panel-title">Actions logged at ' + escHtml(store) + '</div>' + list +
        '<div class="action-note">Saved to Lakebase in milliseconds. Lakehouse Sync copies each action to Unity Catalog, where head office and Genie can see it.</div>';
    })
    .catch(function() { el.innerHTML = ''; });
}

// ================================================================
// DATA JOURNEY: raw files to actions, with live counts
// ================================================================
function openJourney(btn) {
  showTab('journey', btn);
  loadJourney();
}

function loadJourney() {
  var el = document.getElementById('journey-content');
  fetch('/api/journey')
    .then(function(r) { return r.json(); })
    .then(function(d) { el.innerHTML = renderJourney(d); })
    .catch(function(e) { el.innerHTML = errorState('Could not load the data journey: ' + e.message); });
}

function renderJourney(d) {
  var m = {};
  (d.checks || []).forEach(function(c) { m[c.stage + '.' + c.metric] = c; });
  function v(key) { var c = m[key]; return c ? fmtNum(c.value) : '-'; }
  function ok(keys) {
    var all = keys.map(function(k) { return m[k]; }).filter(function(c) { return c; });
    if (!all.length) return '';
    return all.every(function(c) { return c.passed === 'true' || c.passed === true; }) ?
      '<span class="journey-ok">✓ checks passed</span>' : '<span class="journey-bad">check failed</span>';
  }
  var lb = d.lakebase || {}, loop = d.loop || {};
  var anyCheck = (d.checks || [])[0] || {};
  var stages = [
    { n: '1', t: 'Raw files land', p: 'Lakeflow · UC volume', big: v('raw.rows_landed'), unit: 'rows in ' + v('raw.files_landed') + ' files',
      lines: ['Store stock, deliveries, orders, stock counts, waste and allocations', 'CSV and JSON lines, as the source systems send them'], ok: ok(['raw.rows_landed']) },
    { n: '2', t: 'Bronze', p: 'Lakeflow · Auto Loader', big: v('bronze.rows_ingested'), unit: 'rows ingested',
      lines: ['Every row kept as received, with its source file', 'Matches the source manifest row for row'], ok: ok(['bronze.rows_ingested']) },
    { n: '3', t: 'Silver', p: 'Lakeflow · expectations', big: v('silver.rows_dropped') , unit: 'bad rows dropped',
      lines: [v('silver.duplicates_removed') + ' re-sent duplicates removed', 'Every feed typed and quality-checked'], ok: ok(['silver.rows_dropped', 'silver.duplicates_removed']) },
    { n: '4', t: 'Gold', p: 'Lakeflow · root-cause rules', big: v('gold.exceptions'), unit: 'gaps and lows explained',
      lines: [v('gold.product_locations') + ' product-locations', v('gold.answer_key_matches') + ' match the answer key exactly', v('gold.multi_evidence_exceptions') + ' had more than one kind of evidence'],
      ok: ok(['gold.exceptions', 'gold.answer_key_matches']) },
    { n: '5', t: 'Governed', p: 'Unity Catalog', big: (m['governance.availability_pct'] ? m['governance.availability_pct'].value + '%' : '-'), unit: 'on-shelf availability',
      lines: ['One metric view defines every KPI', 'Lineage, tags and least-privilege grants'], ok: ok(['governance.availability_pct']) },
    { n: '6', t: 'Served', p: 'Lakebase', big: lb.serving_rows ? fmtNum(lb.serving_rows) : '-', unit: 'rows synced for Shelf Scan',
      lines: ['Point lookups in milliseconds', 'Live query just now: ' + (lb.query_ms !== undefined ? Math.round(lb.query_ms) + ' ms' : '-')], ok: '' },
    { n: '7', t: 'Intelligent', p: 'Gen AI · Genie', big: lb.recommendations !== undefined ? fmtNum(lb.recommendations) : '-', unit: 'next best actions written',
      lines: [(lb.scans !== undefined ? fmtNum(lb.scans) : '-') + ' Shelf Scans logged', 'Genie answers questions in plain English'], ok: '' },
    { n: '8', t: 'Acted on', p: 'Lakebase → Unity Catalog', big: lb.actions !== undefined ? fmtNum(lb.actions) : '-', unit: 'colleague actions',
      lines: [(loop.actions_in_uc !== undefined ? fmtNum(loop.actions_in_uc) : '-') + ' already back in Unity Catalog', 'Lakehouse Sync closes the loop'], ok: '' }
  ];
  var cards = stages.map(function(s) {
    return '<div class="journey-card"><div class="journey-step">' + s.n + '</div><div class="journey-title">' + escHtml(s.t) + '</div>' +
      '<div class="journey-product">' + escHtml(s.p) + '</div><div class="journey-big">' + s.big + '</div><div class="journey-unit">' + escHtml(s.unit) + '</div>' +
      s.lines.map(function(l) { return '<div class="journey-line">' + escHtml(l) + '</div>'; }).join('') + s.ok + '</div>';
  }).join('<div class="journey-arrow">&#8594;</div>');
  return '<div class="journey-header"><div class="journey-heading">How today\'s data got here</div>' +
    '<div class="journey-sub">Business date ' + escHtml(anyCheck.business_date || '-') + ' · pipeline checks from the daily run at ' + escHtml((anyCheck.run_at || '').slice(0, 16).replace('T', ' ')) +
    ' · Lakebase counts are live</div></div><div class="journey-flow">' + cards + '</div>';
}

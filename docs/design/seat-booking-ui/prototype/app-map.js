'use strict';

/* ==========================================================================
   地图视口：缩放 / 平移 / 双指 / 键盘 / 座位选择
   ========================================================================== */

const ZOOM_MIN = 0.5;
const ZOOM_MAX = 2.5;

const MAPS = {
  student: {
    viewport: $('#studentMapViewport'),
    stage: $('#studentMapStage'),
    zoomLabel: $('#studentZoom'),
    x: 0,
    y: 0,
    z: 1,
    autoFit: true,
    pointers: new Map(),
    pan: null,
    pinch: null,
    seatDrag: null,
    tableDrag: null,
    pending: null,
  },
  admin: {
    viewport: $('#adminMapViewport'),
    stage: $('#adminMapStage'),
    zoomLabel: $('#adminZoom'),
    x: 0,
    y: 0,
    z: 1,
    autoFit: true,
    pointers: new Map(),
    pan: null,
    pinch: null,
    seatDrag: null,
    tableDrag: null,
    pending: null,
  },
};

function applyViewport(mode) {
  const map = MAPS[mode];
  if (!map || !map.stage) return;
  const { stage } = map;
  stage.style.transform = `translate(${map.x}px, ${map.y}px) scale(${map.z})`;
  stage.style.setProperty('--seat-fs', `${clamp(8, 10 / map.z, 18)}px`);
  stage.style.setProperty('--desk-fs', `${clamp(7, 9 / map.z, 16)}px`);
  stage.style.setProperty('--label-fs', `${clamp(9, 10 / map.z, 18)}px`);
  stage.style.setProperty('--icon-size', `${clamp(8, 9 / map.z, 16)}px`);
  stage.style.setProperty('--status-size', `${clamp(8, 9 / map.z, 15)}px`);
  stage.style.setProperty('--flag-fs', `${clamp(6, 7 / map.z, 12)}px`);
  stage.dataset.lod = map.z < 0.62 ? 'far' : map.z < 1.12 ? 'mid' : 'near';
  if (map.zoomLabel) map.zoomLabel.textContent = `${Math.round(map.z * 100)}%`;
}

function clampMapViewport(mode) {
  const map = MAPS[mode];
  if (!map) return;
  const rect = map.viewport.getBoundingClientRect();
  if (rect.width === 0 || rect.height === 0) return;
  const contentWidth = ROOM.w * map.z;
  const contentHeight = ROOM.h * map.z;
  const limitX = Math.min(120, rect.width * 0.26);
  const limitY = Math.min(120, rect.height * 0.26);
  if (contentWidth <= rect.width) {
    map.x = (rect.width - contentWidth) / 2;
  } else {
    map.x = clamp(map.x, rect.width - contentWidth - limitX, limitX);
  }
  if (contentHeight <= rect.height) {
    map.y = (rect.height - contentHeight) / 2;
  } else {
    map.y = clamp(map.y, rect.height - contentHeight - limitY, limitY);
  }
}

function fitMap(mode) {
  const map = MAPS[mode];
  if (!map) return;
  const rect = map.viewport.getBoundingClientRect();
  if (!rect.width || !rect.height) return;
  const pad = rect.width < 520 ? 10 : 30;
  const z = clamp(Math.min((rect.width - pad * 2) / ROOM.w, (rect.height - pad * 2) / ROOM.h), ZOOM_MIN, ZOOM_MAX);
  map.z = z;
  map.x = (rect.width - ROOM.w * z) / 2;
  map.y = (rect.height - ROOM.h * z) / 2;
  map.autoFit = true;
  clampMapViewport(mode);
  applyViewport(mode);
}

function resetMap(mode) {
  const map = MAPS[mode];
  if (!map) return;
  const rect = map.viewport.getBoundingClientRect();
  map.z = 1;
  map.x = (rect.width - ROOM.w) / 2;
  map.y = (rect.height - ROOM.h) / 2;
  map.autoFit = false;
  clampMapViewport(mode);
  applyViewport(mode);
}

function zoomAt(mode, clientX, clientY, nextZ) {
  const map = MAPS[mode];
  if (!map) return;
  const rect = map.viewport.getBoundingClientRect();
  if (!rect.width || !rect.height) return;
  const localX = clientX - rect.left;
  const localY = clientY - rect.top;
  const worldX = (localX - map.x) / map.z;
  const worldY = (localY - map.y) / map.z;
  map.z = clamp(nextZ, ZOOM_MIN, ZOOM_MAX);
  map.x = localX - worldX * map.z;
  map.y = localY - worldY * map.z;
  map.autoFit = false;
  clampMapViewport(mode);
  applyViewport(mode);
}

function zoomBy(mode, factor) {
  const map = MAPS[mode];
  const rect = map.viewport.getBoundingClientRect();
  zoomAt(mode, rect.left + rect.width / 2, rect.top + rect.height / 2, map.z * factor);
}

function startPinch(mode) {
  const map = MAPS[mode];
  const points = [...map.pointers.values()];
  if (points.length < 2) return;
  const [a, b] = points;
  const rect = map.viewport.getBoundingClientRect();
  const midX = (a.x + b.x) / 2 - rect.left;
  const midY = (a.y + b.y) / 2 - rect.top;
  map.pinch = {
    distance: Math.max(1, Math.hypot(a.x - b.x, a.y - b.y)),
    z: map.z,
    x: map.x,
    y: map.y,
    worldX: (midX - map.x) / map.z,
    worldY: (midY - map.y) / map.z,
  };
  map.pan = null;
  map.pending = null;
}

function updatePinch(mode) {
  const map = MAPS[mode];
  const points = [...map.pointers.values()];
  if (points.length < 2 || !map.pinch) return;
  const [a, b] = points;
  const rect = map.viewport.getBoundingClientRect();
  const midX = (a.x + b.x) / 2 - rect.left;
  const midY = (a.y + b.y) / 2 - rect.top;
  const distance = Math.max(1, Math.hypot(a.x - b.x, a.y - b.y));
  map.z = clamp(map.pinch.z * (distance / map.pinch.distance), ZOOM_MIN, ZOOM_MAX);
  map.x = midX - map.pinch.worldX * map.z;
  map.y = midY - map.pinch.worldY * map.z;
  map.autoFit = false;
  clampMapViewport(mode);
  applyViewport(mode);
}

function focusAdjacentSeat(currentId, key) {
  const current = SEAT_MAP[currentId];
  if (!current) return;
  const cx = current.x + current.w / 2;
  const cy = current.y + current.h / 2;
  const direction = {
    ArrowRight: [1, 0],
    ArrowLeft: [-1, 0],
    ArrowDown: [0, 1],
    ArrowUp: [0, -1],
  }[key];
  if (!direction) return;
  let best = null;
  let bestScore = Infinity;
  SEATS.forEach((seat) => {
    if (seat.id === currentId) return;
    const dx = seat.x + seat.w / 2 - cx;
    const dy = seat.y + seat.h / 2 - cy;
    const forward = dx * direction[0] + dy * direction[1];
    if (forward <= 4) return;
    const perpendicular = Math.abs(dx * direction[1] - dy * direction[0]);
    const score = forward + perpendicular * 0.55;
    if (score < bestScore) {
      bestScore = score;
      best = seat;
    }
  });
  if (best) {
    const element = $(`.seat[data-seat-id="${best.id}"]`, MAPS.student.stage);
    element?.focus({ preventScroll: true });
    element?.scrollIntoView({ block: 'nearest', inline: 'nearest' });
  }
}

function bindMapInteractions(mode) {
  const map = MAPS[mode];
  if (!map || !map.viewport) return;
  const { viewport } = map;

  viewport.addEventListener(
    'wheel',
    (event) => {
      event.preventDefault();
      const factor = Math.exp(-event.deltaY * 0.0016);
      zoomAt(mode, event.clientX, event.clientY, map.z * factor);
    },
    { passive: false },
  );

  viewport.addEventListener('dblclick', (event) => {
    if (event.target.closest('.seat')) return;
    zoomAt(mode, event.clientX, event.clientY, map.z * 1.35);
  });

  viewport.addEventListener('pointerover', (event) => {
    const desk = event.target.closest('.desk');
    if (!desk) return;
    desk.classList.add('is-table-hover');
    $$(`.seat[data-table-id="${desk.dataset.tableId}"]`, map.stage).forEach((chair) => {
      chair.classList.add('is-table-hover');
    });
  });

  viewport.addEventListener('pointerout', (event) => {
    const desk = event.target.closest('.desk');
    if (!desk || desk.contains(event.relatedTarget)) return;
    desk.classList.remove('is-table-hover');
    $$(`.seat[data-table-id="${desk.dataset.tableId}"]`, map.stage).forEach((chair) => {
      chair.classList.remove('is-table-hover');
    });
  });

  viewport.addEventListener('pointerdown', (event) => {
    if (event.pointerType === 'mouse' && event.button !== 0) return;
    const seatElement = event.target.closest('.seat');
    map.pointers.set(event.pointerId, { x: event.clientX, y: event.clientY });
    if (map.pointers.size === 2) {
      startPinch(mode);
      return;
    }
    map.pending = {
      seatId: seatElement?.dataset.seatId || null,
      x: event.clientX,
      y: event.clientY,
      shiftKey: event.shiftKey,
    };
    const deskElement = event.target.closest('.desk');
    if (mode === 'admin' && state.adminTab === 'layout' && !isReadonly() && deskElement) {
      startTableDrag(mode, deskElement, event);
      return;
    }
    if (mode === 'admin' && state.adminTab === 'layout' && !isReadonly() && seatElement) {
      startSeatDrag(mode, seatElement, event);
      return;
    }
    map.pan = {
      startX: event.clientX,
      startY: event.clientY,
      originX: map.x,
      originY: map.y,
      moved: false,
    };
    try {
      viewport.setPointerCapture(event.pointerId);
    } catch {
      /* 指针捕获在部分触控设备上不可用，继续使用普通事件 */
    }
  });

  viewport.addEventListener('pointermove', (event) => {
    if (!map.pointers.has(event.pointerId)) return;
    map.pointers.set(event.pointerId, { x: event.clientX, y: event.clientY });
    if (map.pointers.size >= 2) {
      if (!map.pinch) startPinch(mode);
      updatePinch(mode);
      return;
    }
    if (map.seatDrag) {
      updateSeatDrag(mode, event);
      return;
    }
    if (map.tableDrag) {
      updateTableDrag(mode, event);
      return;
    }
    if (!map.pan) return;
    const dx = event.clientX - map.pan.startX;
    const dy = event.clientY - map.pan.startY;
    if (!map.pan.moved && Math.hypot(dx, dy) > 4) map.pan.moved = true;
    if (map.pan.moved) {
      map.x = map.pan.originX + dx;
      map.y = map.pan.originY + dy;
      map.autoFit = false;
      clampMapViewport(mode);
      applyViewport(mode);
    }
  });

  const finishPointer = (event) => {
    const hadPointers = map.pointers.size;
    map.pointers.delete(event.pointerId);
    if (map.seatDrag) {
      finishSeatDrag(mode, event);
      return;
    }
    if (map.tableDrag) {
      finishTableDrag(mode, event);
      return;
    }
    if (map.pinch) {
      if (map.pointers.size < 2) {
        map.pinch = null;
        map.pan = null;
      }
      return;
    }
    if (map.pan) {
      const moved = map.pan.moved;
      const pending = map.pending;
      map.pan = null;
      map.pending = null;
      if (!moved && pending?.seatId) {
        if (mode === 'student') selectStudentSeat(pending.seatId);
        else selectAdminSeat(pending.seatId, pending.shiftKey);
      }
      return;
    }
    if (hadPointers <= 1) map.pending = null;
    try {
      viewport.releasePointerCapture(event.pointerId);
    } catch {
      /* 捕获可能已经释放 */
    }
  };
  viewport.addEventListener('pointerup', finishPointer);
  viewport.addEventListener('pointercancel', finishPointer);

  viewport.addEventListener('keydown', (event) => {
    const seatElement = event.target.closest('.seat');
    if (seatElement) {
      if (event.key.startsWith('Arrow')) {
        event.preventDefault();
        focusAdjacentSeat(seatElement.dataset.seatId, event.key);
        return;
      }
      return;
    }
    const step = event.shiftKey ? 80 : 32;
    if (event.key === 'ArrowLeft' || event.key === 'ArrowRight' || event.key === 'ArrowUp' || event.key === 'ArrowDown') {
      event.preventDefault();
      if (event.key === 'ArrowLeft') map.x += step;
      if (event.key === 'ArrowRight') map.x -= step;
      if (event.key === 'ArrowUp') map.y += step;
      if (event.key === 'ArrowDown') map.y -= step;
      map.autoFit = false;
      clampMapViewport(mode);
      applyViewport(mode);
      return;
    }
    if (event.key === '+' || event.key === '=') {
      event.preventDefault();
      zoomBy(mode, 1.2);
    } else if (event.key === '-' || event.key === '_') {
      event.preventDefault();
      zoomBy(mode, 1 / 1.2);
    } else if (event.key === '0') {
      event.preventDefault();
      resetMap(mode);
    } else if (event.key.toLowerCase() === 'f') {
      event.preventDefault();
      fitMap(mode);
    }
  });

  viewport.addEventListener('click', (event) => {
    if (event.detail !== 0) return;
    const seat = event.target.closest('.seat');
    if (!seat) return;
    if (mode === 'student') selectStudentSeat(seat.dataset.seatId);
    else selectAdminSeat(seat.dataset.seatId, event.shiftKey);
  });
}

/* ------------------------------ 座位选择 ------------------------------ */
function syncTableSelection(mode) {
  const stage = mode === 'student' ? MAPS.student?.stage : MAPS.admin?.stage;
  if (!stage) return;
  const selectedIds = mode === 'student'
    ? (state.selectedSeatId ? [state.selectedSeatId] : [])
    : [...state.adminSelected];
  const selectedTables = new Set(selectedIds.map((id) => SEAT_MAP[id]?.tableId).filter(Boolean));
  $$('.desk', stage).forEach((desk) => {
    desk.classList.toggle('is-table-selected', selectedTables.has(desk.dataset.tableId));
  });
}

function updateListSelection() {
  $$('#studentListBody .seat-row').forEach((row) => {
    const selected = row.dataset.listSeat === state.selectedSeatId;
    row.classList.toggle('is-selected', selected);
    row.setAttribute('aria-pressed', String(selected));
  });
}

function selectStudentSeat(id) {
  const seat = SEAT_MAP[id];
  if (!seat) return;
  if (!isFilterMatch(seat)) {
    toast('这个座位不在当前筛选结果中，先清除筛选再选择。', 'warn');
    return;
  }
  state.selectedSeatId = id;
  updateSeatSelection();
  renderBookingCard();
  renderMobileBar();
  updateListSelection();
}

function selectAdminSeat(id, add = false) {
  const seat = SEAT_MAP[id];
  if (!seat) return;
  if (add) {
    if (state.adminSelected.has(id)) state.adminSelected.delete(id);
    else state.adminSelected.add(id);
  } else {
    state.adminSelected.clear();
    state.adminSelected.add(id);
  }
  updateSeatSelection();
  renderAdminInspector();
}

function findNearestFree(seat) {
  const from = seat || selectedSeat() || SEATS[0];
  const cx = from.x + from.w / 2;
  const cy = from.y + from.h / 2;
  return SEATS
    .filter((candidate) => currentStatus(candidate) === 'free' && candidate.id !== from.id)
    .sort((a, b) => {
      const da = Math.hypot(a.x + a.w / 2 - cx, a.y + a.h / 2 - cy);
      const db = Math.hypot(b.x + b.w / 2 - cx, b.y + b.h / 2 - cy);
      const sameAreaA = a.area === from.area ? 0 : 1;
      const sameAreaB = b.area === from.area ? 0 : 1;
      return sameAreaA - sameAreaB || da - db;
    })[0] || null;
}

function findAlternativeSeats(count = 3) {
  const from = selectedSeat() || SEATS[0];
  const cx = from.x + from.w / 2;
  const cy = from.y + from.h / 2;
  return SEATS
    .filter((seat) => currentStatus(seat) === 'free')
    .sort((a, b) => {
      const da = Math.hypot(a.x + a.w / 2 - cx, a.y + a.h / 2 - cy);
      const db = Math.hypot(b.x + b.w / 2 - cx, b.y + b.h / 2 - cy);
      const areaA = a.area === from.area ? 0 : 1;
      const areaB = b.area === from.area ? 0 : 1;
      return areaA - areaB || da - db;
    })
    .slice(0, count);
}

function focusSeatOnMap(seat) {
  if (!seat) return;
  if (state.view !== 'map') setView('map');
  if (window.innerWidth <= 920) {
    $('#studentMapShell')?.scrollIntoView({ block: 'center', behavior: 'smooth' });
  }
  const map = MAPS.student;
  requestAnimationFrame(() => {
    const rect = map.viewport.getBoundingClientRect();
    if (!rect.width) return;
    const z = clamp(Math.max(map.z, 1.15), ZOOM_MIN, ZOOM_MAX);
    map.z = z;
    map.x = rect.width / 2 - (seat.x + seat.w / 2) * z;
    map.y = rect.height / 2 - (seat.y + seat.h / 2) * z;
    map.autoFit = false;
    clampMapViewport('student');
    applyViewport('student');
  });
}

function findFreeSeat() {
  const candidates = filteredSeats().filter((seat) => currentStatus(seat) === 'free');
  if (!candidates.length) {
    toast('当前筛选下没有空位，试试「全部」。', 'warn');
    return;
  }
  const seat = candidates[0];
  selectStudentSeat(seat.id);
  focusSeatOnMap(seat);
  $('#studentMapShell')?.scrollIntoView({ block: 'center', behavior: 'smooth' });
  toast(`已定位到 ${seat.id}，${areaOf(seat).name}。`, 'success');
}

/* ------------------------------ 日期 / 时间 / 筛选 / 视图 ------------------------------ */
function setDate(offset) {
  if (offset === 0 && !CAN_BOOK_TODAY) {
    toast('今天已过最后一个可预约时段，已保留明天。', 'warn');
    return;
  }
  state.dateOffset = offset;
  if (offset === 0 && state.start <= NOW_MIN) {
    state.start = clamp(Math.ceil((NOW_MIN + 1) / SLOT_MIN) * SLOT_MIN, OPEN_MIN, CLOSE_MIN - 30);
    state.end = Math.min(state.start + 120, CLOSE_MIN);
  }
  renderDates();
  renderFilters();
  renderTimeRail();
  renderTimeSummary();
  updateSeatStates();
  updateStudentMapMeta();
  renderBookingCard();
  renderMobileBar();
  if (state.view === 'list') renderList();
  renderAdminChrome();
}

function applyTimeRange(start, end, options = {}) {
  let nextStart = clamp(Math.round(start / SLOT_MIN) * SLOT_MIN, OPEN_MIN, CLOSE_MIN - SLOT_MIN);
  let nextEnd = clamp(Math.round(end / SLOT_MIN) * SLOT_MIN, nextStart + SLOT_MIN, CLOSE_MIN);
  let clampedDuration = false;
  if (nextEnd - nextStart > MAX_BOOKING_MIN) {
    nextEnd = nextStart + MAX_BOOKING_MIN;
    clampedDuration = true;
  }
  if (nextEnd <= nextStart) nextEnd = Math.min(nextStart + SLOT_MIN, CLOSE_MIN);
  state.start = nextStart;
  state.end = nextEnd;
  renderDates();
  renderFilters();
  renderTimeRail();
  renderTimeSummary();
  updateSeatStates();
  updateStudentMapMeta();
  renderBookingCard();
  renderMobileBar();
  if (state.view === 'list') renderList();
  renderAdminChrome();
  if (options.notify && clampedDuration) toast('单次预约最长 4 小时，已自动收敛结束时间。', 'warn');
}

function setFilter(id) {
  if (!FILTERS.some((filter) => filter.id === id)) return;
  state.filter = id;
  if (state.selectedSeatId) {
    const seat = selectedSeat();
    if (seat && !isFilterMatch(seat)) {
      state.selectedSeatId = null;
      toast('已选座位不在新筛选结果中，已清空选择。', 'warn');
    }
  }
  renderFilters();
  $$('#studentMapStage .seat').forEach((element) => {
    const seat = SEAT_MAP[element.dataset.seatId];
    element.classList.toggle('is-dimmed', !isFilterMatch(seat));
  });
  $$('#studentMapStage .desk').forEach((element) => {
    const table = TABLE_MAP[element.dataset.tableId];
    element.classList.toggle('is-dimmed', Boolean(table) && !table.seatIds.some((id) => isFilterMatch(SEAT_MAP[id])));
  });
  updateSeatSelection();
  updateStudentMapMeta();
  renderBookingCard();
  renderMobileBar();
  if (state.view === 'list') renderList();
  renderAdminChrome();
}

function setView(view) {
  state.view = view;
  const mapShell = $('#studentMapShell');
  const listView = $('#studentListView');
  const mapFooter = $('.map-footer', $('#studentView'));
  const isList = view === 'list';
  mapShell.hidden = isList;
  listView.hidden = !isList;
  if (mapFooter) mapFooter.hidden = isList;
  $$('.view-switch__btn[data-view]').forEach((button) => {
    const active = button.dataset.view === view;
    button.classList.toggle('is-active', active);
    button.setAttribute('aria-pressed', String(active));
  });
  if (isList) renderList();
  else requestAnimationFrame(() => fitMap('student'));
}

/* ------------------------------ 拖拽布局 ------------------------------ */
function snapshotLayout() {
  return JSON.stringify({
    seats: SEATS.map((seat) => ({ ...seat, tags: [...seat.tags] })),
    tables: TABLES.map((table) => ({ ...table, tags: [...table.tags], seatIds: [...table.seatIds] })),
  });
}

function pushLayoutUndo(snapshot) {
  state.undoStack.push(snapshot || snapshotLayout());
  if (state.undoStack.length > 50) state.undoStack.shift();
  state.redoStack = [];
}

function restoreLayout(snapshot) {
  const parsed = JSON.parse(snapshot);
  const seatData = Array.isArray(parsed) ? parsed : parsed.seats || [];
  const tableData = Array.isArray(parsed) ? null : parsed.tables || null;
  if (tableData) {
    TABLES.length = 0;
    Object.keys(TABLE_MAP).forEach((key) => delete TABLE_MAP[key]);
    tableData.forEach((item) => {
      TABLES.push(item);
      TABLE_MAP[item.id] = item;
    });
  }
  SEATS.length = 0;
  Object.keys(SEAT_MAP).forEach((key) => delete SEAT_MAP[key]);
  seatData.forEach((item) => {
    item.rotation = item.rotation || 0;
    SEATS.push(item);
    SEAT_MAP[item.id] = item;
  });
  state.dirty = true;
  reconcileSelections();
  renderMap('admin');
  renderAdminChrome();
}

function reconcileSelections() {
  if (state.selectedSeatId && !SEAT_MAP[state.selectedSeatId]) state.selectedSeatId = null;
  [...state.adminSelected].forEach((id) => {
    if (!SEAT_MAP[id]) state.adminSelected.delete(id);
  });
}

function startSeatDrag(mode, seatElement, event) {
  const map = MAPS[mode];
  const seat = SEAT_MAP[seatElement.dataset.seatId];
  if (!seat) return;
  map.seatDrag = {
    element: seatElement,
    seat,
    snapshot: snapshotLayout(),
    startX: event.clientX,
    startY: event.clientY,
    originX: seat.x,
    originY: seat.y,
    shiftKey: event.shiftKey,
    moved: false,
  };
  map.pending = { seatId: seat.id, shiftKey: event.shiftKey, x: event.clientX, y: event.clientY };
  seatElement.classList.add('is-dragging');
  try {
    map.viewport.setPointerCapture(event.pointerId);
  } catch {
    /* ignore */
  }
}

function clearGuides() {
  $$('.align-guide', MAPS.admin.stage).forEach((guide) => guide.remove());
}

function updateSeatDrag(mode, event) {
  const map = MAPS[mode];
  const drag = map.seatDrag;
  if (!drag) return;
  const dx = (event.clientX - drag.startX) / map.z;
  const dy = (event.clientY - drag.startY) / map.z;
  if (!drag.moved && Math.hypot(dx, dy) > 2) drag.moved = true;
  if (!drag.moved) return;
  let nextX = clamp(Math.round((drag.originX + dx) / 10) * 10, 24, ROOM.w - drag.seat.w - 20);
  let nextY = clamp(Math.round((drag.originY + dy) / 10) * 10, 24, ROOM.h - drag.seat.h - 20);
  clearGuides();
  let guideX = null;
  let guideY = null;
  SEATS.forEach((other) => {
    if (other.id === drag.seat.id) return;
    if (Math.abs(nextX - other.x) < 4) {
      nextX = other.x;
      guideX = other.x;
    }
    if (Math.abs(nextX + drag.seat.w - (other.x + other.w)) < 4) {
      nextX = other.x + other.w - drag.seat.w;
      guideX = other.x + other.w;
    }
    if (Math.abs(nextY - other.y) < 4) {
      nextY = other.y;
      guideY = other.y;
    }
    if (Math.abs(nextY + drag.seat.h - (other.y + other.h)) < 4) {
      nextY = other.y + other.h - drag.seat.h;
      guideY = other.y + other.h;
    }
  });
  drag.seat.x = nextX;
  drag.seat.y = nextY;
  drag.element.style.left = `${nextX}px`;
  drag.element.style.top = `${nextY}px`;
  if (guideX !== null) {
    const guide = document.createElement('span');
    guide.className = 'align-guide align-guide--v';
    guide.style.left = `${guideX}px`;
    MAPS.admin.stage.appendChild(guide);
  }
  if (guideY !== null) {
    const guide = document.createElement('span');
    guide.className = 'align-guide align-guide--h';
    guide.style.top = `${guideY}px`;
    MAPS.admin.stage.appendChild(guide);
  }
}

function finishSeatDrag(mode, event) {
  const map = MAPS[mode];
  const drag = map.seatDrag;
  if (!drag) return;
  clearGuides();
  drag.element.classList.remove('is-dragging');
  map.seatDrag = null;
  map.pan = null;
  if (drag.moved) {
    pushLayoutUndo(drag.snapshot);
    state.dirty = true;
    renderAdminInspector();
    renderAdminChrome();
  } else if (drag.seat.id) {
    selectAdminSeat(drag.seat.id, drag.shiftKey);
  }
  map.pending = null;
  try {
    map.viewport.releasePointerCapture(event.pointerId);
  } catch {
    /* ignore */
  }
}

/* 编辑模式下拖桌子：整张桌与围绕它的椅子一起移动 */
function startTableDrag(mode, deskElement, event) {
  const map = MAPS[mode];
  const table = TABLE_MAP[deskElement.dataset.tableId];
  if (!table) return;
  const seats = table.seatIds.map((id) => SEAT_MAP[id]).filter(Boolean);
  map.tableDrag = {
    element: deskElement,
    table,
    seats,
    snapshot: snapshotLayout(),
    startX: event.clientX,
    startY: event.clientY,
    originX: table.x,
    originY: table.y,
    seatOrigins: seats.map((seat) => ({ seat, x: seat.x, y: seat.y })),
    moved: false,
  };
  deskElement.classList.add('is-dragging');
  try {
    map.viewport.setPointerCapture(event.pointerId);
  } catch {
    /* ignore */
  }
}

function updateTableDrag(mode, event) {
  const map = MAPS[mode];
  const drag = map.tableDrag;
  if (!drag) return;
  const dx = (event.clientX - drag.startX) / map.z;
  const dy = (event.clientY - drag.startY) / map.z;
  if (!drag.moved && Math.hypot(dx, dy) > 2) drag.moved = true;
  if (!drag.moved) return;
  const nextX = clamp(Math.round((drag.originX + dx) / 10) * 10, 20, ROOM.w - drag.table.w - 20);
  const nextY = clamp(Math.round((drag.originY + dy) / 10) * 10, 20, ROOM.h - drag.table.h - 20);
  const deltaX = nextX - drag.originX;
  const deltaY = nextY - drag.originY;
  drag.table.x = nextX;
  drag.table.y = nextY;
  drag.element.style.left = `${nextX}px`;
  drag.element.style.top = `${nextY}px`;
  drag.seatOrigins.forEach(({ seat, x, y }) => {
    seat.x = x + deltaX;
    seat.y = y + deltaY;
    const chair = $(`.seat[data-seat-id="${seat.id}"]`, MAPS.admin.stage);
    if (chair) {
      chair.style.left = `${seat.x}px`;
      chair.style.top = `${seat.y}px`;
    }
  });
}

function finishTableDrag(mode, event) {
  const map = MAPS[mode];
  const drag = map.tableDrag;
  if (!drag) return;
  drag.element.classList.remove('is-dragging');
  map.tableDrag = null;
  if (drag.moved) {
    pushLayoutUndo(drag.snapshot);
    state.dirty = true;
    renderAdminChrome();
  }
  try {
    map.viewport.releasePointerCapture(event.pointerId);
  } catch {
    /* ignore */
  }
}

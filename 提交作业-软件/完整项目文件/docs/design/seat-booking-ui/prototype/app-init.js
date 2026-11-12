'use strict';

/* ==========================================================================
   初始化与全局事件
   ========================================================================== */

function setTheme(theme) {
  document.documentElement.dataset.theme = theme;
  try {
    localStorage.setItem('ssr-seat-theme', theme);
  } catch {
    /* ignore */
  }
  const button = $('#themeToggle');
  if (button) {
    button.setAttribute('aria-label', theme === 'dark' ? '切换浅色模式' : '切换深色模式');
    button.title = theme === 'dark' ? '切换浅色模式' : '切换深色模式';
  }
}

function switchMode(mode) {
  state.mode = mode;
  const isAdmin = mode === 'admin';
  $('#studentView').hidden = isAdmin;
  $('#adminView').hidden = !isAdmin;
  $$('.demo-switch__btn[data-mode]').forEach((button) => {
    const active = button.dataset.mode === mode;
    button.classList.toggle('is-active', active);
    button.setAttribute('aria-pressed', String(active));
  });
  document.title = isAdmin ? '座位运营台 · 静园自习室 A-201' : '预约座位 · 静园自习室 A-201';
  if (isAdmin) {
    renderAdminChrome();
    renderMap('admin');
    requestAnimationFrame(() => fitMap('admin'));
  } else {
    requestAnimationFrame(() => fitMap('student'));
  }
}

function handleSheetAction(action, element) {
  switch (action) {
    case 'close':
      closeSheet();
      break;
    case 'review-booking':
      closeSheet();
      window.setTimeout(() => openSheet('booking'), 80);
      break;
    case 'submit-booking':
      submitBooking();
      break;
    case 'find-alternative': {
      const seat = findNearestFree(selectedSeat());
      closeSheet();
      if (!seat) {
        toast('附近暂时没有空位，试试改时间段。', 'warn');
        return;
      }
      selectStudentSeat(seat.id);
      focusSeatOnMap(seat);
      toast(`已改选 ${seat.id}，${areaOf(seat).name}。`, 'success');
      break;
    }
    case 'pick-alternative': {
      const id = element?.dataset.seatId;
      const seat = id ? SEAT_MAP[id] : null;
      closeSheet();
      if (seat) {
        selectStudentSeat(seat.id);
        focusSeatOnMap(seat);
        toast(`已改选 ${seat.id}，时间保持不变。`, 'success');
      }
      break;
    }
    case 'change-time':
      closeSheet();
      $('#timeRail')?.scrollIntoView({ block: 'center', behavior: 'smooth' });
      setTimeout(() => $('.slot.is-range-start')?.focus(), 380);
      break;
    case 'view-reservations':
      closeSheet();
      toast('已打开「我的预约」（演示）。', 'success');
      break;
    case 'continue':
      closeSheet();
      break;
    case 'message-user':
      toast('已打开站内消息（演示）。', 'success');
      break;
    case 'resolve-conflict':
      closeSheet();
      addLog(`处理冲突 <strong>${state.activeConflictId || 'CF-20261107-01'}</strong>，保留有效预约并记录处理结果`);
      renderAdminChrome();
      toast('冲突已标记处理，操作已写入日志。', 'success');
      break;
    case 'choose-room': {
      const name = element?.dataset.room || ROOM.name;
      ROOM.name = name;
      state.roomName = name;
      const nameElement = $('.room-card__name');
      if (nameElement) nameElement.textContent = name;
      closeSheet();
      toast(`已切换到 ${name}。`, 'success');
      break;
    }
    case 'apply-import':
      applyImport();
      break;
    default:
      break;
  }
}

function handleStudentAction(action) {
  switch (action) {
    case 'open-booking':
    case 'open-booking-mobile':
      openSheet('booking');
      break;
    case 'open-summary':
      openSheet('summary');
      break;
    case 'open-mine':
      toast('已打开「我的预约」，可以在这里签到或取消。', 'success');
      break;
    case 'find-alternative': {
      const seat = findNearestFree(selectedSeat());
      if (!seat) {
        toast('当前筛选下没有空位，试试清除筛选。', 'warn');
        return;
      }
      selectStudentSeat(seat.id);
      focusSeatOnMap(seat);
      toast(`已为你改选 ${seat.id}，${areaOf(seat).name}。`, 'success');
      break;
    }
    case 'clear-filter':
      setFilter('all');
      break;
    case 'view-rules':
      openSheet('rules');
      break;
    case 'retry-map':
      showMapState('loading');
      window.setTimeout(() => {
        state.forceState = '';
        showMapState('');
        renderMap('student');
        fitMap('student');
        toast('地图已重新加载。', 'success');
      }, 900);
      break;
    case 'switch-list':
      showMapState('');
      setView('list');
      break;
    case 'next-slot': {
      const current = activeSlot();
      let target = -1;
      for (let offset = 1; offset < SLOT_COUNT; offset += 1) {
        const index = current + offset;
        if (index >= SLOT_COUNT) break;
        if (freeCountAtSlot(index) > 0) {
          target = index;
          break;
        }
      }
      if (target < 0) {
        toast('今天后面也没有空位了，试试明天。', 'warn');
        return;
      }
      const slotStart = OPEN_MIN + target * SLOT_MIN;
      state.forceState = '';
      showMapState('');
      applyTimeRange(slotStart, Math.min(slotStart + 120, CLOSE_MIN));
      toast('已切换到下一个有空位的时段。', 'success');
      break;
    }
    default:
      break;
  }
}

function bindGlobalEvents() {
  document.addEventListener('click', (event) => {
    const target = event.target;

    const modeButton = target.closest('[data-mode]');
    if (modeButton) {
      switchMode(modeButton.dataset.mode);
      return;
    }

    const dateButton = target.closest('[data-date-offset]');
    if (dateButton) {
      setDate(Number(dateButton.dataset.dateOffset));
      return;
    }

    const filterButton = target.closest('[data-filter]');
    if (filterButton) {
      setFilter(filterButton.dataset.filter);
      return;
    }

    const viewButton = target.closest('[data-view]');
    if (viewButton) {
      setView(viewButton.dataset.view);
      return;
    }

    const listSeat = target.closest('[data-list-seat]');
    if (listSeat) {
      const seat = SEAT_MAP[listSeat.dataset.listSeat];
      if (seat) {
        selectStudentSeat(seat.id);
        focusSeatOnMap(seat);
      }
      return;
    }

    const mapAction = target.closest('[data-map-action]');
    if (mapAction) {
      const mode = mapAction.dataset.map || 'student';
      const action = mapAction.dataset.mapAction;
      const map = MAPS[mode];
      if (action === 'zoom-in') zoomBy(mode, 1.2);
      if (action === 'zoom-out') zoomBy(mode, 1 / 1.2);
      if (action === 'fit') fitMap(mode);
      if (action === 'reset') resetMap(mode);
      if (map) map.autoFit = action === 'fit';
      return;
    }

    const mapStateAction = target.closest('[data-map-state-action]');
    if (mapStateAction) {
      const action = mapStateAction.dataset.mapStateAction;
      if (action === 'retry') handleStudentAction('retry-map');
      if (action === 'list') handleStudentAction('switch-list');
      if (action === 'next-slot') handleStudentAction('next-slot');
      return;
    }

    const sheetAction = target.closest('[data-sheet-action]');
    if (sheetAction) {
      handleSheetAction(sheetAction.dataset.sheetAction, sheetAction);
      return;
    }

    const adminAction = target.closest('[data-admin-action]');
    if (adminAction) {
      handleAdminAction(adminAction.dataset.adminAction, adminAction);
      return;
    }

    const tool = target.closest('[data-tool]');
    if (tool) {
      handleAdminTool(tool.dataset.tool);
      return;
    }

    const studentAction = target.closest('[data-action]');
    if (studentAction) {
      handleStudentAction(studentAction.dataset.action);
      return;
    }

    const adminTab = target.closest('[data-admin-tab]');
    if (adminTab) {
      switchAdminTab(adminTab.dataset.adminTab);
      return;
    }

    if (target.closest('#themeToggle')) {
      const next = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
      setTheme(next);
      return;
    }

    if (target.closest('#switchRoomBtn')) {
      openSheet('rooms');
      return;
    }

    if (target.closest('#scrollSeatBtn')) {
      findFreeSeat();
      return;
    }

    if (target.closest('#listBackToMap')) {
      setView('map');
      return;
    }

    if (target.closest('#adminRefreshBtn')) {
      renderAdminChrome();
      toast('占用已刷新（演示）。', 'success');
      return;
    }

    if (target.closest('#sheetClose') || target.closest('#overlay')) {
      closeSheet();
      return;
    }

    if (target.closest('#confirmLayer') && target.id === 'confirmLayer') {
      closeConfirm();
      return;
    }

    const ruleLink = target.closest('a[href="#rules"]');
    if (ruleLink) {
      event.preventDefault();
      openSheet('rules');
    }
  });

  $('#adminInspector')?.addEventListener('change', (event) => {
    const field = event.target.closest('[data-admin-field]');
    if (!field || isReadonly()) return;
    const seats = adminSelectionSeats();
    if (seats.length !== 1) return;
    applyAdminField(field.dataset.adminField, field.value, seats[0]);
  });

  $('#adminRole')?.addEventListener('change', (event) => {
    state.adminRole = event.target.value;
    renderAdminChrome();
    renderMap('admin');
    if (isReadonly()) toast('已切换为系统管理员：只读预览。', 'warn');
    else toast('已切换为自习室管理员：可编辑。', 'success');
  });

  $('#confirmActions')?.addEventListener('click', (event) => {
    const button = event.target.closest('[data-confirm-action]');
    if (!button) return;
    if (button.dataset.confirmAction === 'cancel') {
      closeConfirm();
      return;
    }
    const reasonInput = $('#confirmReason');
    const reason = reasonInput ? reasonInput.value.trim() : '';
    if (confirmState?.requireReason && reason.length < 2) {
      toast('请填写操作原因（至少 2 个字）。', 'warn');
      reasonInput?.focus();
      return;
    }
    const shouldClose = confirmState?.onConfirm ? confirmState.onConfirm(reason) : true;
    if (shouldClose !== false) closeConfirm();
  });

  bindTimeRail();
  bindKeyboardShortcuts();
  bindResize();
}

function updateTimeDragTip(clientX) {
  const tip = $('#timeDragTip');
  const rail = $('#timeRail');
  if (!tip || !rail) return;
  const rect = rail.getBoundingClientRect();
  tip.hidden = false;
  tip.textContent = `${timeText()} · ${durationHours()} 小时`;
  tip.style.left = `${clamp(clientX - rect.left, 40, rect.width - 40)}px`;
}

function hideTimeDragTip() {
  const tip = $('#timeDragTip');
  if (tip) tip.hidden = true;
}

function bindTimeRail() {
  const rail = $('#timeRail');
  if (!rail) return;

  rail.addEventListener('pointerdown', (event) => {
    const slot = event.target.closest('.slot');
    if (!slot || slot.disabled) return;
    const start = Number(slot.dataset.slotStart);
    timeDrag = { anchor: start, moved: false };
    applyTimeRange(start, Math.min(start + 120, CLOSE_MIN));
    updateTimeDragTip(event.clientX);
    try {
      rail.setPointerCapture(event.pointerId);
    } catch {
      /* ignore */
    }
    event.preventDefault();
  });

  rail.addEventListener('pointermove', (event) => {
    if (!timeDrag) return;
    const hit = document.elementFromPoint(event.clientX, event.clientY)?.closest('.slot');
    if (!hit || hit.disabled) return;
    const slotStart = Number(hit.dataset.slotStart);
    timeDrag.moved = true;
    if (slotStart < timeDrag.anchor) {
      applyTimeRange(slotStart, Math.min(timeDrag.anchor + SLOT_MIN, CLOSE_MIN));
    } else {
      applyTimeRange(timeDrag.anchor, Math.min(slotStart + SLOT_MIN, timeDrag.anchor + MAX_BOOKING_MIN));
    }
    updateTimeDragTip(event.clientX);
  });

  const finish = () => {
    timeDrag = null;
    hideTimeDragTip();
  };
  rail.addEventListener('pointerup', finish);
  rail.addEventListener('pointercancel', finish);

  rail.addEventListener('click', (event) => {
    if (event.detail !== 0) return;
    const slot = event.target.closest('.slot');
    if (!slot || slot.disabled) return;
    const start = Number(slot.dataset.slotStart);
    applyTimeRange(start, Math.min(start + 120, CLOSE_MIN));
  });
}

function bindKeyboardShortcuts() {
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') {
      if (!$('#confirmLayer').hidden) {
        closeConfirm();
        return;
      }
      if (state.sheetOpen) {
        closeSheet();
        return;
      }
    }

    if (state.sheetOpen && event.key === 'Tab') {
      const sheet = $('#sheet');
      const focusables = $$('button:not([disabled]), [href], input:not([disabled]), textarea:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])', sheet);
      if (!focusables.length) return;
      const first = focusables[0];
      const last = focusables[focusables.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
      return;
    }

    if (!$('#confirmLayer').hidden && event.key === 'Tab') {
      const buttons = $$('#confirmActions button, #confirmReason');
      if (!buttons.length) return;
      const first = buttons[0];
      const last = buttons[buttons.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
      return;
    }

    const tag = document.activeElement?.tagName?.toLowerCase();
    const inField = tag === 'input' || tag === 'textarea' || tag === 'select';
    if (state.mode === 'admin' && state.adminTab === 'layout' && !isReadonly() && !inField) {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'z') {
        event.preventDefault();
        if (event.shiftKey) redoLayout();
        else undoLayout();
        return;
      }
      if (event.key.toLowerCase() === 'r') {
        event.preventDefault();
        rotateSelectedSeat();
        return;
      }
      if (event.key === 'Delete' || event.key === 'Backspace') {
        event.preventDefault();
        deleteSelectedSeats();
        return;
      }
    }
  });

  window.addEventListener('beforeunload', (event) => {
    if (!state.dirty) return;
    event.preventDefault();
    event.returnValue = '';
  });
}

function bindResize() {
  let timer = null;
  window.addEventListener('resize', () => {
    if (timer) window.clearTimeout(timer);
    timer = window.setTimeout(() => {
      if (state.mode === 'student') {
        if (MAPS.student.autoFit) fitMap('student');
        else {
          clampMapViewport('student');
          applyViewport('student');
        }
      } else {
        if (MAPS.admin.autoFit) fitMap('admin');
        else {
          clampMapViewport('admin');
          applyViewport('admin');
        }
      }
    }, 120);
  });
}

/* 演示状态：通过 ?state=loading|error|empty|conflict|success|limit 预览 */
function startDemoState() {
  if (state.mode !== 'student') return;
  const kind = state.forceState;
  if (kind === 'loading' || kind === 'error' || kind === 'empty') {
    state.selectedSeatId = null;
    if (kind === 'empty') {
      SEATS.forEach((seat) => {
        if (currentStatus(seat) === 'free') state.statusOverrides[seat.id] = 'taken';
      });
      updateSeatStates();
      updateStudentMapMeta();
      renderFilters();
      renderTimeRail();
      renderTimeSummary();
      renderDates();
    }
    renderBookingCard();
    renderMobileBar();
    if (kind === 'loading' || kind === 'error') {
      $('#freeCount').textContent = '—';
      $('#mapMeta').textContent = kind === 'loading' ? '正在同步 A-201 的布局与占用…' : '座位数据暂不可用，请重试';
      $$('#filters .filter-chip__count').forEach((count) => { count.textContent = '—'; });
      $('#timeSummary').innerHTML = `
        <strong class="time-summary__range">${timeText()}</strong>
        <span class="time-summary__meta">${kind === 'loading' ? '正在同步空位…' : '空位数据暂不可用'}</span>`;
    }
    showMapState(kind);
    return;
  }
  if (kind === 'summary') {
    state.selectedSeatId = 'C-03';
    updateSeatSelection();
    renderBookingCard();
    renderMobileBar();
    if (query.get('instant') === '1') openSheet('summary');
    else window.setTimeout(() => openSheet('summary'), 420);
    return;
  }
  if (kind === 'conflict') {
    state.selectedSeatId = 'C-03';
    state.statusOverrides['C-03'] = 'taken';
    updateSeatStates();
    updateStudentMapMeta();
    renderFilters();
    renderTimeRail();
    renderTimeSummary();
    renderDates();
    renderBookingCard();
    renderMobileBar();
    if (query.get('instant') === '1') openSheet('conflict');
    else window.setTimeout(() => openSheet('conflict'), 420);
    return;
  }
  if (kind === 'success') {
    state.selectedSeatId = 'C-03';
    state.statusOverrides['C-03'] = 'mine';
    const seat = SEAT_MAP['C-03'];
    successInfo = {
      seat,
      code: `A201-${pad2(selectedDate().date.getMonth() + 1)}${pad2(selectedDate().date.getDate())}-042`,
      date: dateText(),
      start: state.start,
      end: state.end,
    };
    updateSeatStates();
    updateStudentMapMeta();
    renderFilters();
    renderTimeRail();
    renderTimeSummary();
    renderDates();
    renderBookingCard();
    renderMobileBar();
    if (query.get('instant') === '1') openSheet('success');
    else window.setTimeout(() => openSheet('success'), 420);
    return;
  }
  if (kind === 'limit') {
    state.forceState = 'limit';
    renderBookingCard();
    renderMobileBar();
  }
}

function init() {
  if (query.get('instant') === '1') document.documentElement.classList.add('ssr-instant');
  let storedTheme = 'light';
  try {
    storedTheme = localStorage.getItem('ssr-seat-theme') || 'light';
  } catch {
    storedTheme = 'light';
  }
  setTheme(storedTheme === 'dark' ? 'dark' : 'light');

  // 管理端初始标签与权限
  $$('.admin-tab').forEach((button) => {
    button.classList.toggle('is-active', button.dataset.adminTab === state.adminTab);
  });
  state.editing = state.adminTab === 'layout';

  renderDates();
  renderTimeRail();
  renderTimeSummary();
  renderFilters();
  renderMap('student');
  renderMap('admin');
  renderBookingCard();
  renderMobileBar();
  renderList();
  renderAdminChrome();

  bindMapInteractions('student');
  bindMapInteractions('admin');
  bindGlobalEvents();

  window.setInterval(() => {
    demoClock.setSeconds(demoClock.getSeconds() + 1);
    const live = $('#adminLive');
    if (live) live.innerHTML = `<span class="live-dot"></span><span>实时 · 10s</span><strong>${clockText()}</strong>`;
    const stamp = $('#adminStamp');
    if (stamp) stamp.textContent = `最后同步 ${clockText()}`;
  }, 1000);

  requestAnimationFrame(() => {
    fitMap('student');
    if (state.mode === 'admin') {
      switchMode('admin');
    } else {
      switchMode('student');
    }
    if (query.get('instant') === '1') startDemoState();
    else window.setTimeout(startDemoState, 260);
    if (query.get('scroll') === 'map') {
      window.setTimeout(() => {
        $('#studentMapShell')?.scrollIntoView({ block: 'start', behavior: 'instant' });
      }, 500);
    }
  });
}

init();

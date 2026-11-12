'use strict';

/* ==========================================================================
   交互层：预约提交 / 冲突 / 管理操作 / 浮层与反馈
   ========================================================================== */

let lastFocusedElement = null;
let confirmState = null;
let successInfo = null;
let timeDrag = null;

/* ------------------------------ 反馈 ------------------------------ */
function toast(message, kind = 'success') {
  const region = $('#toasts');
  if (!region) return;
  const icon = kind === 'error' ? ICONS.alert : kind === 'warn' ? ICONS.info : ICONS.check;
  const item = document.createElement('div');
  item.className = `toast toast--${kind}`;
  item.innerHTML = `${icon}<span>${escapeHtml(message)}</span>`;
  region.appendChild(item);
  window.setTimeout(() => {
    item.style.opacity = '0';
    item.style.transform = 'translateY(6px)';
    window.setTimeout(() => item.remove(), 220);
  }, 3200);
}

function showMapState(kind) {
  const element = $('#studentMapState');
  if (!element) return;
  if (!kind) {
    element.hidden = true;
    element.innerHTML = '';
    element.removeAttribute('role');
    return;
  }
  element.hidden = false;
  element.className = 'map-state';
  element.setAttribute('role', 'status');
  if (kind === 'loading') {
    element.classList.add('map-state--loading');
    element.innerHTML = `
      <div class="map-state__spinner" aria-hidden="true"></div>
      <h3 style="font-size:18px">正在读取座位</h3>
      <p>同步 A-201 的布局与时段占用…</p>
      <div class="skeleton skeleton-line"></div>
      <div class="skeleton skeleton-line"></div>`;
    return;
  }
  if (kind === 'error') {
    element.innerHTML = `
      <div class="map-state__icon">${ICONS.alert}</div>
      <h3>地图加载失败</h3>
      <p>座位数据暂时没有回来。你的日期和时段已保留，可以重试，也可以先切换到列表视图。</p>
      <div class="map-state__actions">
        <button type="button" class="btn btn--sm btn--primary" data-map-state-action="retry">重新加载</button>
        <button type="button" class="btn btn--sm" data-map-state-action="list">切换到列表</button>
      </div>`;
    return;
  }
  if (kind === 'empty') {
    element.innerHTML = `
      <div class="map-state__icon">${ICONS.seats}</div>
      <h3>这个时段暂时没有空位</h3>
      <p>${timeText()} 的可约座位已满。试试相邻时段，或者换一个日期；你的筛选条件不会丢。</p>
      <div class="map-state__actions">
        <button type="button" class="btn btn--sm btn--primary" data-map-state-action="next-slot">看下一个时段</button>
        <button type="button" class="btn btn--sm" data-map-state-action="list">查看列表</button>
      </div>`;
  }
}

/* ------------------------------ 浮层 ------------------------------ */
function sheetTemplate(kind) {
  const seat = selectedSeat();
  if (kind === 'summary') {
    if (!seat) {
      return {
        title: '预约摘要',
        eyebrow: 'MOBILE SUMMARY',
        body: '<p class="sheet-note">先在地图上选择一个座位。</p><div class="sheet-actions"><button type="button" class="btn" data-sheet-action="close">收起</button></div>',
      };
    }
    const status = currentStatus(seat);
    return {
      title: '预约摘要',
      eyebrow: 'MOBILE SUMMARY',
      body: `
        <div class="booking-seat">
          <p class="booking-seat__eyebrow">${tableOf(seat)?.label || ''} 桌 · ${areaOf(seat).en}</p>
          <div class="booking-seat__row">
            <strong class="booking-seat__no">${seat.id}</strong>
            <span class="booking-seat__zone">${areaOf(seat).name}<br>${typeLabels(seat).join(' · ') || '普通座'}</span>
          </div>
        </div>
        <div class="summary-rows">
          <div class="summary-row"><span class="summary-row__label">DATE</span><span class="summary-row__value">${dateText()}</span></div>
          <div class="summary-row"><span class="summary-row__label">TIME</span><span class="summary-row__value mono">${timeText()}</span></div>
          <div class="summary-row"><span class="summary-row__label">DURATION</span><span class="summary-row__value">${durationHours()} 小时</span></div>
          <div class="summary-row"><span class="summary-row__label">STATUS</span><span class="summary-row__value">${STATUS[status].label}</span></div>
        </div>
        <div class="sheet-total"><span>本次预约</span><strong>免费</strong></div>
        <div class="sheet-actions">
          <button type="button" class="btn btn--ghost" data-sheet-action="close">收起</button>
          ${status === 'free'
            ? '<button type="button" class="btn btn--primary" data-sheet-action="review-booking">查看详情并确认</button>'
            : '<button type="button" class="btn" data-sheet-action="find-alternative">找附近空位</button>'}
        </div>
        <p class="sheet-note">摘要与地图选择同步；确认前不会提交预约。</p>`,
    };
  }

  if (kind === 'booking') {
    if (!seat) return { title: '先选一个座位', eyebrow: 'BOOKING SUMMARY', body: '<p class="sheet-note">回到地图，点击一个空位。</p>' };
    const status = currentStatus(seat);
    if (status !== 'free') {
      return {
        title: '这个座位不可预约',
        eyebrow: 'SEAT UNAVAILABLE',
        body: `<div class="conflict-banner">${ICONS.info}<span>当前座位为「${STATUS[status].label}」，不能提交预约。你可以换一个空位，或调整时间。</span></div>
          <div class="sheet-actions"><button type="button" class="btn btn--primary" data-sheet-action="find-alternative">看看附近空位</button><button type="button" class="btn btn--ghost" data-sheet-action="close">关闭</button></div>`,
      };
    }
    return {
      title: '确认预约',
      eyebrow: 'BOOKING SUMMARY',
      body: `
        <div class="summary-rows">
          <div class="summary-row"><span class="summary-row__label">SEAT</span><span class="summary-row__value mono">${seat.id} · ${areaOf(seat).name}</span></div>
          <div class="summary-row"><span class="summary-row__label">DATE</span><span class="summary-row__value">${dateText()}</span></div>
          <div class="summary-row"><span class="summary-row__label">TIME</span><span class="summary-row__value mono">${timeText()}</span></div>
          <div class="summary-row"><span class="summary-row__label">DURATION</span><span class="summary-row__value">${durationHours()} 小时</span></div>
          <div class="summary-row"><span class="summary-row__label">CHECK-IN</span><span class="summary-row__value mono">${checkinWindow()}</span></div>
        </div>
        <div class="sheet-total"><span>本次预约</span><strong>免费</strong></div>
        <div class="rule-checks">
          <div class="rule-check">${ICONS.check}<span>同一时段仅保留一笔有效预约；重复点击不会生成第二笔。</span></div>
          <div class="rule-check">${ICONS.check}<span>座位会在服务端再次校验；若刚被抢占，会保留时间并给出可选空位。</span></div>
        </div>
        <div class="sheet-actions">
          <button type="button" class="btn btn--ghost" data-sheet-action="close">再想想</button>
          <button type="button" class="btn btn--primary" data-sheet-action="submit-booking">确认预约</button>
        </div>
        <p class="sheet-note">提交成功后，请在 ${checkinWindow()} 内签到。</p>`,
    };
  }

  if (kind === 'success') {
    const info = successInfo || {
      seat: selectedSeat(),
      code: 'A201-1107-042',
      start: state.start,
      end: state.end,
      date: dateText(),
    };
    return {
      title: '预约已确认',
      eyebrow: 'RESERVATION CONFIRMED',
      body: `
        <div class="success-mark">${ICONS.check}</div>
        <h3 class="success-title">位置留好了</h3>
        <p class="success-copy">${info.seat?.id || 'C-03'} · ${info.date} · ${minutesToTime(info.start)}–${minutesToTime(info.end)}</p>
        <div class="summary-rows">
          <div class="summary-row"><span class="summary-row__label">RESERVATION</span><span class="summary-row__value mono">${info.code}</span></div>
          <div class="summary-row"><span class="summary-row__label">CHECK-IN WINDOW</span><span class="summary-row__value mono">${checkinWindow(info.start)}</span></div>
          <div class="summary-row"><span class="summary-row__label">ROOM</span><span class="summary-row__value">${ROOM.name}</span></div>
        </div>
        <div class="sheet-actions">
          <button type="button" class="btn btn--primary" data-sheet-action="view-reservations">查看我的预约</button>
          <button type="button" class="btn btn--ghost" data-sheet-action="continue">继续选座</button>
        </div>
        <p class="sheet-note">签到前 15 分钟会收到站内提醒。超时未签到将按规则释放座位。</p>`,
    };
  }

  if (kind === 'conflict') {
    const alternatives = findAlternativeSeats(3);
    return {
      title: '座位刚被抢占',
      eyebrow: 'CONFLICT / 409',
      body: `
        <div class="conflict-banner">${ICONS.alert}<span><strong>该座位已被抢占。</strong>请换座或改时间。你的日期和时段已保留，可以一键改选附近空位。</span></div>
        <div class="summary-rows">
          <div class="summary-row"><span class="summary-row__label">WANTED</span><span class="summary-row__value mono">${seat?.id || '—'} · ${timeText()}</span></div>
          <div class="summary-row"><span class="summary-row__label">SERVER</span><span class="summary-row__value mono">刚刚更新 · 409 CONFLICT</span></div>
        </div>
        <div class="inspector-head" style="margin:14px 0 7px"><div><h3 style="margin:0;font-family:var(--font-display);font-size:15px">附近可约</h3><p>同区域优先，距离由近到远</p></div></div>
        <div class="alternative-list">
          ${alternatives.length ? alternatives.map((item) => `
            <button type="button" class="alternative" data-sheet-action="pick-alternative" data-seat-id="${item.id}">
              <span><strong>${item.id}</strong><br><span>${areaOf(item).name} · ${typeLabels(item).slice(0, 2).join(' · ') || '普通座'}</span></span>
              <span>可约 →</span>
            </button>`).join('') : '<p class="sheet-note">附近暂时没有空位，试试改时间。</p>'}
        </div>
        <div class="sheet-actions">
          <button type="button" class="btn btn--primary" data-sheet-action="change-time">改时间段</button>
          <button type="button" class="btn btn--ghost" data-sheet-action="close">稍后再说</button>
        </div>`,
    };
  }

  if (kind === 'rooms') {
    const rooms = [
      { name: '静园自习室 A-201', floor: '2F · 东侧', seats: 28, free: countStatuses().free, active: true },
      { name: '静园自习室 A-202', floor: '2F · 西侧', seats: 24, free: 11, active: false },
      { name: '北馆自习室 B-103', floor: '1F · 北馆', seats: 36, free: 19, active: false },
    ];
    return {
      title: '换一间自习室',
      eyebrow: 'ROOM SWITCHER',
      body: `<div class="alternative-list">${rooms.map((room) => `
        <button type="button" class="alternative" data-sheet-action="choose-room" data-room="${escapeHtml(room.name)}">
          <span><strong style="font-family:var(--font-ui);font-size:11px">${room.name}</strong><br><span>${room.floor} · ${room.seats} 座 · 余 ${room.free}</span></span>
          <span style="color:${room.active ? 'var(--brand)' : 'var(--ink-3)'}">${room.active ? '当前' : '切换 →'}</span>
        </button>`).join('')}</div>
        <p class="sheet-note">多自习室共用同一套布局与状态模型；切换后地图会重新适配。</p>`,
    };
  }

  if (kind === 'rules') {
    return {
      title: '预约与签到规则',
      eyebrow: 'HOUSE RULES',
      body: `
        <div class="rule-checks">
          <div class="rule-check">${ICONS.check}<span><strong>可约范围：</strong>最多提前 7 天；今天只能选尚未开始的时段。</span></div>
          <div class="rule-check">${ICONS.check}<span><strong>时间粒度：</strong>30 分钟一档，单次最长 4 小时，结束时间不得晚于闭馆。</span></div>
          <div class="rule-check">${ICONS.check}<span><strong>数量限制：</strong>每位同学每天最多 2 条有效预约；同一时段只能约 1 个座位。</span></div>
          <div class="rule-check">${ICONS.check}<span><strong>签到窗口：</strong>开始前 15 分钟至开始后 15 分钟；超时未签到会释放座位并记违约。</span></div>
          <div class="rule-check">${ICONS.check}<span><strong>违约规则：</strong>累计 3 次违约将限制预约 7 天；取消规则以取消时点为准。</span></div>
          <div class="rule-check is-warn">${ICONS.info}<span><strong>本期免费：</strong>页面展示「免费」，不提供支付、押金或代他人预约入口。</span></div>
        </div>
        <p class="sheet-note">规则数值来自系统统一配置；本原型不修改任何业务口径。</p>`,
    };
  }

  if (kind === 'import') {
    return {
      title: '导入座位坐标',
      eyebrow: 'LAYOUT IMPORT / JSON',
      body: `
        <p class="sheet-note" style="text-align:left">按房间导入 JSON 坐标；必须包含 id、x、y。系统会先校验重复编号、越界与分区引用，全部通过后才写入。</p>
        <label class="inspector-field" style="margin-top:10px"><span>JSON / CSV</span>
          <textarea id="importJson" rows="10" style="width:100%;padding:10px;background:var(--surface-2);border:1px solid var(--line);border-radius:8px;font-family:var(--font-mono);font-size:10px">[
  { "id": "W-01", "x": 60, "y": 70, "w": 48, "h": 64, "rotation": 0 },
  { "id": "W-02", "x": 112, "y": 70, "w": 48, "h": 64, "rotation": 0 }
]</textarea>
        </label>
        <div class="inspector-note">CSV 表头：id,area,x,y,w,h,rotation。演示版仅更新已存在的座位坐标；新增座位需后端布局接口。</div>
        <div class="sheet-actions">
          <button type="button" class="btn btn--ghost" data-sheet-action="close">取消</button>
          <button type="button" class="btn btn--primary" data-sheet-action="apply-import">校验并导入</button>
        </div>`,
    };
  }

  if (kind === 'admin-conflict') {
    const conflict = CONFLICTS.find((item) => item.id === state.activeConflictId) || CONFLICTS[0];
    return {
      title: `处理冲突 ${conflict.id}`,
      eyebrow: 'CONFLICT RESOLUTION',
      body: `
        <div class="conflict-banner">${ICONS.alert}<span>${conflict.note}</span></div>
        <div class="summary-rows">
          <div class="summary-row"><span class="summary-row__label">SEAT</span><span class="summary-row__value mono">${conflict.seat}</span></div>
          <div class="summary-row"><span class="summary-row__label">TIME</span><span class="summary-row__value mono">${conflict.time}</span></div>
          <div class="summary-row"><span class="summary-row__label">USER</span><span class="summary-row__value">${conflict.user} · 已脱敏</span></div>
        </div>
        <p class="sheet-note" style="text-align:left">请先确认保留哪一笔有效预约。此操作会写入操作日志；取消预约不记违约。</p>
        <div class="sheet-actions">
          <button type="button" class="btn btn--ghost" data-sheet-action="message-user">联系用户</button>
          <button type="button" class="btn btn--primary" data-sheet-action="resolve-conflict">保留并按规则处理</button>
        </div>`,
    };
  }

  if (kind === 'reservation-admin') {
    return {
      title: '预约详情',
      eyebrow: 'RESERVATION / READ ONLY',
      body: `
        <div class="summary-rows">
          <div class="summary-row"><span class="summary-row__label">RESERVATION</span><span class="summary-row__value mono">R202611070042</span></div>
          <div class="summary-row"><span class="summary-row__label">USER</span><span class="summary-row__value">王** · 2023****21</span></div>
          <div class="summary-row"><span class="summary-row__label">SEAT</span><span class="summary-row__value mono">${selectedSeat()?.id || 'C-03'} · ${areaOf(selectedSeat() || SEATS[0]).name}</span></div>
          <div class="summary-row"><span class="summary-row__label">WINDOW</span><span class="summary-row__value mono">${timeText()}</span></div>
          <div class="summary-row"><span class="summary-row__label">STATUS</span><span class="summary-row__value">待使用</span></div>
        </div>
        <div class="sheet-actions">
          <button type="button" class="btn btn--ghost" data-sheet-action="close">关闭</button>
          <button type="button" class="btn btn--primary" data-sheet-action="message-user">发送站内消息</button>
        </div>
        <p class="sheet-note">管理员只读身份信息；姓名与学号已脱敏，不提供修改入口。</p>`,
    };
  }

  return {
    title: '提示',
    eyebrow: 'INFORMATION',
    body: `<p class="sheet-note">该功能在演示版中未展开。</p><div class="sheet-actions"><button type="button" class="btn" data-sheet-action="close">关闭</button></div>`,
  };
}

function openSheet(kind, payload = {}) {
  const sheet = $('#sheet');
  const overlay = $('#overlay');
  if (!sheet || !overlay) return;
  if (payload.conflictId) state.activeConflictId = payload.conflictId;
  const template = sheetTemplate(kind);
  $('#sheetEyebrow').textContent = template.eyebrow;
  $('#sheetTitle').textContent = template.title;
  $('#sheetBody').innerHTML = template.body;
  sheet.classList.toggle('sheet--summary', kind === 'summary');
  lastFocusedElement = document.activeElement;
  overlay.hidden = false;
  sheet.hidden = false;
  state.sheetOpen = true;
  document.body.style.overflow = 'hidden';
  requestAnimationFrame(() => {
    $('#sheetClose')?.focus({ preventScroll: true });
    if (kind === 'import') $('#importJson')?.focus({ preventScroll: true });
  });
}

function closeSheet() {
  const sheet = $('#sheet');
  const overlay = $('#overlay');
  if (!sheet || sheet.hidden) return;
  sheet.hidden = true;
  sheet.classList.remove('sheet--summary');
  overlay.hidden = true;
  state.sheetOpen = false;
  document.body.style.overflow = '';
  if (lastFocusedElement && typeof lastFocusedElement.focus === 'function') {
    lastFocusedElement.focus({ preventScroll: true });
  }
}

function openConfirm(options) {
  const layer = $('#confirmLayer');
  if (!layer) return;
  confirmState = options;
  $('#confirmEyebrow').textContent = options.eyebrow || 'HIGH RISK ACTION';
  $('#confirmTitle').textContent = options.title;
  $('#confirmBody').innerHTML = options.body || '';
  const confirmLabel = options.confirmLabel || '确认';
  $('#confirmActions').innerHTML = `
    <button type="button" class="btn btn--ghost" data-confirm-action="cancel">取消</button>
    <button type="button" class="btn ${options.danger ? 'btn--danger' : 'btn--primary'}" data-confirm-action="ok">${escapeHtml(confirmLabel)}</button>`;
  layer.hidden = false;
  document.body.style.overflow = 'hidden';
  requestAnimationFrame(() => {
    const target = options.requireReason ? $('#confirmReason') : $('[data-confirm-action="ok"]');
    target?.focus({ preventScroll: true });
  });
}

function closeConfirm() {
  $('#confirmLayer').hidden = true;
  confirmState = null;
  if (!state.sheetOpen) document.body.style.overflow = '';
}

function submitBooking() {
  const seat = selectedSeat();
  if (!seat || state.submitting) return;
  if (currentStatus(seat) !== 'free') {
    toast('该座位当前不可预约，请重新选择。', 'warn');
    closeSheet();
    return;
  }
  const intent = `${seat.id}|${state.dateOffset}|${state.start}|${state.end}`;
  if (state.confirmedIntent === intent && successInfo) {
    openSheet('success');
    return;
  }
  state.submitting = true;
  const button = $('[data-sheet-action="submit-booking"]');
  if (button) {
    button.disabled = true;
    button.innerHTML = '<span class="btn__spinner" aria-hidden="true"></span>提交中…';
  }
  window.setTimeout(() => {
    state.submitting = false;
    if (state.forceState === 'conflict') {
      state.statusOverrides[seat.id] = 'taken';
      state.forceState = '';
      updateSeatStates();
      updateStudentMapMeta();
      renderFilters();
      renderTimeRail();
      renderTimeSummary();
      renderDates();
      renderBookingCard();
      renderMobileBar();
      renderAdminChrome();
      openSheet('conflict');
      return;
    }
    state.statusOverrides[seat.id] = 'mine';
    state.confirmedSeatId = seat.id;
    state.confirmedIntent = intent;
    state.dailyUsed = Math.min(2, state.dailyUsed + 1);
    const stamp = `${pad2(selectedDate().date.getMonth() + 1)}${pad2(selectedDate().date.getDate())}`;
    successInfo = {
      seat,
      code: `A201-${stamp}-${String(100 + (hash(intent) % 900))}`,
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
    if (state.view === 'list') renderList();
    renderAdminChrome();
    openSheet('success');
    toast('预约成功，记得在签到窗口内签到。', 'success');
  }, 820);
}

/* ------------------------------ 管理操作 ------------------------------ */
function addLog(text, actor = '周岚') {
  state.logs.unshift({ time: clockText().slice(0, 8), actor, text });
  if (state.logs.length > 40) state.logs.pop();
}

function applyStatusToSeats(seats, status, reason) {
  seats.forEach((seat) => {
    state.statusOverrides[seat.id] = status;
  });
  const ids = seats.map((seat) => seat.id).join('、');
  addLog(`将 <strong>${ids}</strong> 调整为「${STATUS[status].label}」，原因「${escapeHtml(reason)}」`);
  renderMap('admin');
  renderAdminChrome();
  toast(`${seats.length} 个座位已调整为「${STATUS[status].label}」。`, 'success');
}

function openStatusConfirm(status, seats) {
  if (isReadonly()) {
    toast('系统管理员为只读权限，不能执行该操作。', 'warn');
    return;
  }
  if (!seats.length) {
    toast('先选择至少一个座位。', 'warn');
    return;
  }
  const meta = STATUS[status];
  const body = `
    <p>将 <strong>${seats.length}</strong> 个座位调整为「${meta.label}」。以下有效预约不会被自动取消；执行后会进入冲突队列，由你决定后续处理。</p>
    <div class="confirm__list">
      <div><span>座位</span><strong>${seats.map((seat) => seat.id).join('、')}</strong></div>
      <div><span>受影响预约</span><strong>${Math.min(seats.length, 3)} 笔（示例）</strong></div>
      <div><span>执行人</span><strong>周岚 · 自习室管理员</strong></div>
    </div>
    <label class="inspector-field" style="margin-top:10px"><span>操作原因（必填，20–200 字）</span>
      <textarea id="confirmReason" rows="3" style="width:100%;padding:8px;background:var(--surface-2);border:1px solid var(--line);border-radius:7px;font-size:10px" placeholder="例如：插座检修，预计 2 小时恢复"></textarea>
    </label>
    <p class="sheet-note" style="text-align:left">服务端会重新校验权限、资源状态与有效预约，并记录操作日志。</p>`;
  openConfirm({
    title: `调整为「${meta.label}」`,
    eyebrow: 'RESOURCE STATUS / CONFIRM',
    body,
    confirmLabel: '确认调整',
    danger: status === 'off' || status === 'fix',
    requireReason: true,
    onConfirm: (reason) => {
      applyStatusToSeats(seats, status, reason);
      return true;
    },
  });
}

function releaseHold() {
  if (isReadonly()) {
    toast('系统管理员为只读权限。', 'warn');
    return;
  }
  const seat = SEAT_MAP['Q-03'];
  openConfirm({
    title: '释放临时保留',
    eyebrow: 'HOLD RELEASE / CONFIRM',
    body: `<p>释放 <strong>Q-03</strong> 的临时保留，让它重新回到可预约状态？</p>
      <div class="confirm__list"><div><span>座位</span><strong>Q-03 · 静音角</strong></div><div><span>保留原因</span><strong>设备调试</strong></div><div><span>剩余</span><strong>04:32</strong></div></div>
      <label class="inspector-field" style="margin-top:10px"><span>释放原因</span><textarea id="confirmReason" rows="2" style="width:100%;padding:8px;background:var(--surface-2);border:1px solid var(--line);border-radius:7px;font-size:10px" placeholder="例如：调试完成"></textarea></label>`,
    confirmLabel: '释放座位',
    onConfirm: (reason) => {
      state.statusOverrides['Q-03'] = 'free';
      addLog(`释放 <strong>Q-03</strong> 的临时保留，原因「${escapeHtml(reason || '调试完成')}」`);
      renderMap('admin');
      renderAdminChrome();
      toast('Q-03 已恢复可用。', 'success');
      return true;
    },
  });
}

function saveLayout(showToast = true) {
  if (isReadonly()) {
    toast('系统管理员为只读权限。', 'warn');
    return false;
  }
  try {
    localStorage.setItem('ssr-seat-layout-demo', JSON.stringify(SEATS));
  } catch {
    /* 原型可能运行在禁用 localStorage 的环境 */
  }
  state.dirty = false;
  state.lastSavedAt = clockText().slice(0, 5);
  addLog(`保存布局草稿 v${state.layoutVersion}，共 ${SEATS.length} 个座位`);
  renderAdminChrome();
  if (showToast) toast('布局草稿已保存。', 'success');
  return true;
}

function publishLayout() {
  if (isReadonly()) {
    toast('系统管理员为只读权限。', 'warn');
    return;
  }
  openConfirm({
    title: '发布布局',
    eyebrow: 'LAYOUT PUBLISH / CONFIRM',
    body: `<p>发布后会更新学生端的地图与座位坐标，并生成新的布局版本。已产生的预约不受影响。</p>
      <div class="confirm__list"><div><span>当前版本</span><strong>v${state.layoutVersion}</strong></div><div><span>目标版本</span><strong>v${state.layoutVersion + 1}</strong></div><div><span>座位数</span><strong>${SEATS.length}</strong></div><div><span>未保存更改</span><strong>${state.dirty ? '有' : '无'}</strong></div></div>`,
    confirmLabel: '发布新版本',
    danger: true,
    onConfirm: () => {
      saveLayout(false);
      state.layoutVersion += 1;
      addLog(`发布布局 <strong>v${state.layoutVersion}</strong>，同步 ${SEATS.length} 个座位`);
      renderAdminChrome();
      toast(`布局 v${state.layoutVersion} 已发布。`, 'success');
      return true;
    },
  });
}

function pushLayoutHistory() {
  pushLayoutUndo(snapshotLayout());
}

function addSeat() {
  if (isReadonly()) return toast('系统管理员为只读权限。', 'warn');
  pushLayoutHistory();
  let index = 1;
  while (SEAT_MAP[`N-${pad2(index)}`] || TABLE_MAP[`T-N${pad2(index)}`]) index += 1;
  const tableId = `T-N${pad2(index)}`;
  const seat = {
    id: `N-${pad2(index)}`,
    tableId,
    area: 'central',
    x: 430,
    y: 226,
    w: 30,
    h: 30,
    chair: 'n',
    type: 'normal',
    tags: [],
  };
  const table = {
    id: tableId,
    area: 'central',
    x: 408,
    y: 258,
    w: 64,
    h: 42,
    shape: 'rect',
    label: `N${index}`,
    meta: '1 座',
    tags: [],
    seatIds: [seat.id],
  };
  SEATS.push(seat);
  SEAT_MAP[seat.id] = seat;
  TABLES.push(table);
  TABLE_MAP[table.id] = table;
  state.dirty = true;
  state.adminSelected.clear();
  state.adminSelected.add(seat.id);
  renderMap('admin');
  renderAdminChrome();
  toast(`已新增 ${seat.id}（${table.label} 桌），可拖拽调整位置。`, 'success');
}

function deleteSelectedSeats() {
  if (isReadonly()) return toast('系统管理员为只读权限。', 'warn');
  const seats = adminSelectionSeats();
  if (!seats.length) return toast('先选择要删除的座位。', 'warn');
  openConfirm({
    title: `删除 ${seats.length} 个座位`,
    eyebrow: 'LAYOUT DELETE / CONFIRM',
    body: `<p>从当前布局中删除 <strong>${seats.map((seat) => seat.id).join('、')}</strong>。历史预约不会被删除；但请确认这些座位没有正在使用的预约。</p>
      <div class="confirm__list"><div><span>布局</span><strong>v${state.layoutVersion}</strong></div><div><span>删除后座位数</span><strong>${SEATS.length - seats.length}</strong></div></div>
      <p class="sheet-note" style="text-align:left">删除可以通过撤销恢复。</p>`,
    confirmLabel: '删除座位',
    danger: true,
    onConfirm: () => {
      pushLayoutHistory();
      seats.forEach((seat) => {
        const index = SEATS.findIndex((item) => item.id === seat.id);
        if (index >= 0) SEATS.splice(index, 1);
        delete SEAT_MAP[seat.id];
        const table = tableOf(seat);
        if (table) {
          table.seatIds = table.seatIds.filter((id) => id !== seat.id);
          if (table.seatIds.length === 0) {
            const tableIndex = TABLES.findIndex((item) => item.id === table.id);
            if (tableIndex >= 0) TABLES.splice(tableIndex, 1);
            delete TABLE_MAP[table.id];
          }
        }
      });
      state.adminSelected.clear();
      state.dirty = true;
      renderMap('admin');
      renderAdminChrome();
      toast(`已删除 ${seats.length} 个座位，可撤销。`, 'warn');
      return true;
    },
  });
}

function rotateSelectedSeat() {
  if (isReadonly()) return toast('系统管理员为只读权限。', 'warn');
  const seats = adminSelectionSeats();
  if (seats.length !== 1) return toast('先选择 1 个座位再旋转。', 'warn');
  pushLayoutHistory();
  seats[0].rotation = ((seats[0].rotation || 0) + 15) % 360;
  state.dirty = true;
  renderMap('admin');
  renderAdminInspector();
  toast(`${seats[0].id} 已旋转到 ${seats[0].rotation}°。`, 'success');
}

function undoLayout() {
  if (isReadonly()) return;
  const snapshot = state.undoStack.pop();
  if (!snapshot) return toast('没有可撤销的操作。', 'warn');
  state.redoStack.push(snapshotLayout());
  restoreLayout(snapshot);
  renderAdminChrome();
  toast('已撤销上一步。', 'success');
}

function redoLayout() {
  if (isReadonly()) return;
  const snapshot = state.redoStack.pop();
  if (!snapshot) return toast('没有可重做的操作。', 'warn');
  state.undoStack.push(snapshotLayout());
  restoreLayout(snapshot);
  renderAdminChrome();
  toast('已重做。', 'success');
}

function applyAdminField(field, value, seat) {
  if (isReadonly()) return;
  pushLayoutHistory();
  if (field === 'type') {
    seat.type = value;
  } else if (field === 'rotation') {
    seat.rotation = Number(value) || 0;
  } else {
    const number = Number(value);
    if (!Number.isFinite(number)) return;
    seat[field] = field === 'w' ? clamp(number, 30, 140) : field === 'h' ? clamp(number, 30, 140) : clamp(number, 20, ROOM[field === 'x' ? 'w' : 'h'] - 20);
  }
  state.dirty = true;
  renderMap('admin');
  renderAdminChrome();
}

function handleAdminAction(action, element) {
  const seats = adminSelectionSeats();
  switch (action) {
    case 'lock':
      openStatusConfirm('locked', seats.length ? seats : adminSelectionSeats());
      break;
    case 'fix':
      openStatusConfirm('fix', seats.length ? seats : adminSelectionSeats());
      break;
    case 'off':
      openStatusConfirm('locked', seats.length ? seats : adminSelectionSeats());
      break;
    case 'restore':
      if (seats[0]) {
        state.statusOverrides[seats[0].id] = 'free';
        addLog(`将 <strong>${seats[0].id}</strong> 恢复为可用`);
        renderMap('admin');
        renderAdminChrome();
        toast(`${seats[0].id} 已恢复可用。`, 'success');
      }
      break;
    case 'lock-area': {
      if (isReadonly()) return toast('系统管理员为只读权限。', 'warn');
      const area = seats[0] ? areaOf(seats[0]) : AREAS[0];
      const areaSeats = SEATS.filter((seat) => seat.area === area.id);
      openConfirm({
        title: `锁定 ${area.name}`,
        eyebrow: 'AREA LOCK / CONFIRM',
        body: `<p>将 <strong>${area.name}</strong> 的 <strong>${areaSeats.length}</strong> 个座位全部锁定。锁定不会取消已有预约；受影响预约会进入冲突队列。</p>
          <div class="confirm__list"><div><span>区域</span><strong>${area.name}</strong></div><div><span>座位数</span><strong>${areaSeats.length}</strong></div><div><span>现有预约</span><strong>3 笔（示例）</strong></div></div>
          <label class="inspector-field" style="margin-top:10px"><span>锁定原因（必填）</span><textarea id="confirmReason" rows="2" style="width:100%;padding:8px;background:var(--surface-2);border:1px solid var(--line);border-radius:7px;font-size:10px" placeholder="例如：区域设备维护"></textarea></label>`,
        confirmLabel: '锁定整区',
        danger: true,
        requireReason: true,
        onConfirm: (reason) => {
          applyStatusToSeats(areaSeats, 'locked', reason);
          return true;
        },
      });
      break;
    }
    case 'batch-lock':
      openStatusConfirm('locked', seats);
      break;
    case 'batch-fix':
      openStatusConfirm('fix', seats);
      break;
    case 'batch-off':
      openStatusConfirm('locked', seats);
      break;
    case 'clear-selection':
      state.adminSelected.clear();
      updateSeatSelection();
      renderAdminInspector();
      break;
    case 'conflicts':
      switchAdminTab('monitor');
      break;
    case 'open-reservation':
      openSheet('reservation-admin');
      break;
    case 'message-user':
      toast('已打开站内消息（演示）。', 'success');
      break;
    case 'release-hold':
      releaseHold();
      break;
    case 'save':
      saveLayout();
      break;
    case 'publish':
      publishLayout();
      break;
    case 'import':
      openSheet('import');
      break;
    case 'add':
      addSeat();
      break;
    case 'delete':
      deleteSelectedSeats();
      break;
    case 'rotate':
      rotateSelectedSeat();
      break;
    case 'undo':
      undoLayout();
      break;
    case 'redo':
      redoLayout();
      break;
    case 'refresh':
      renderAdminChrome();
      toast('占用已刷新（演示）。', 'success');
      break;
    case 'permissions':
      openSheet('rules');
      break;
    case 'open-log':
      switchAdminTab('ops');
      break;
    case 'conflict':
      state.activeConflictId = element?.dataset.conflictId;
      openSheet('admin-conflict', { conflictId: element?.dataset.conflictId });
      break;
    default:
      break;
  }
}

function handleAdminTool(tool) {
  if (isReadonly()) {
    toast('系统管理员为只读权限，不能执行编辑操作。', 'warn');
    return;
  }
  if (tool === 'select') {
    toast('选择工具：单击座位，Shift 加选。', 'success');
    return;
  }
  if (tool === 'batch') {
    if (state.adminSelected.size < 2) toast('按住 Shift 点击可多选座位。', 'warn');
    else renderAdminInspector();
    return;
  }
  handleAdminAction(tool);
}

/* ------------------------------ 导入 ------------------------------ */
function parseImportPayload(text) {
  const trimmed = text.trim();
  if (!trimmed) throw new Error('内容为空');
  if (trimmed.startsWith('[') || trimmed.startsWith('{')) {
    const parsed = JSON.parse(trimmed);
    const rows = Array.isArray(parsed) ? parsed : parsed.seats;
    if (!Array.isArray(rows)) throw new Error('JSON 需要座位数组或 { seats: [] }');
    return rows;
  }
  const lines = trimmed.split(/\r?\n/).filter(Boolean);
  if (lines.length < 2) throw new Error('CSV 至少需要表头与一行数据');
  const headers = lines[0].split(',').map((item) => item.trim());
  if (!headers.includes('id') || !headers.includes('x') || !headers.includes('y')) {
    throw new Error('CSV 表头必须包含 id,x,y');
  }
  return lines.slice(1).map((line) => {
    const cells = line.split(',').map((item) => item.trim());
    return Object.fromEntries(headers.map((header, index) => [header, cells[index]]));
  });
}

function applyImport() {
  const textarea = $('#importJson');
  if (!textarea) return;
  try {
    const rows = parseImportPayload(textarea.value);
    const seen = new Set();
    const updates = [];
    const invalid = [];
    rows.forEach((item) => {
      if (!item.id || seen.has(item.id)) {
        invalid.push(`重复/缺少编号：${item.id || '—'}`);
        return;
      }
      seen.add(item.id);
      const seat = SEAT_MAP[item.id];
      if (!seat) {
        invalid.push(`布局中不存在：${item.id}`);
        return;
      }
      const values = ['x', 'y', 'w', 'h', 'rotation'].reduce((result, field) => {
        if (item[field] !== undefined && item[field] !== '' && Number.isFinite(Number(item[field]))) {
          result[field] = Number(item[field]);
        }
        return result;
      }, {});
      if ((values.x !== undefined && (values.x < 0 || values.x > ROOM.w)) || (values.y !== undefined && (values.y < 0 || values.y > ROOM.h))) {
        invalid.push(`越界：${item.id}`);
        return;
      }
      updates.push({ seat, values });
    });
    if (!updates.length && invalid.length) throw new Error(invalid[0]);
    pushLayoutHistory();
    updates.forEach(({ seat, values }) => Object.assign(seat, values));
    const updated = updates.length;
    state.dirty = true;
    renderMap('admin');
    renderAdminChrome();
    closeSheet();
    toast(`已校验并更新 ${updated} 个座位${invalid.length ? `，${invalid.length} 行被跳过` : ''}。`, invalid.length ? 'warn' : 'success');
  } catch (error) {
    toast(`导入失败：${error.message}。请检查 JSON / CSV 格式。`, 'error');
  }
}


/* ------------------------------ 学生端渲染 ------------------------------ */
function renderDates() {
  const rail = $('#dateRail');
  const activeCounts = countStatuses();
  rail.innerHTML = DATES.map((item) => {
    const isTodayPast = item.offset === 0 && !CAN_BOOK_TODAY;
    const count = item.offset === state.dateOffset
      ? activeCounts.free
      : freeCountAtSlot(item.offset === 0 ? activeSlot() : 4, item.offset);
    const active = item.offset === state.dateOffset;
    return `
      <button type="button" class="date-chip${active ? ' is-active' : ''}${item.offset === 0 ? ' is-today' : ''}"
        data-date-offset="${item.offset}" aria-pressed="${active}" ${isTodayPast ? 'disabled' : ''}
        aria-label="${item.longLabel}，剩余 ${count} 个空位">
        <span class="date-chip__day">${item.dayLabel}</span>
        <span class="date-chip__date">${item.dateLabel}</span>
        <span class="date-chip__meta">余 ${count}</span>
      </button>`;
  }).join('');
}

function renderTimeRail() {
  const rail = $('#timeRail');
  const startIndex = Math.round((state.start - OPEN_MIN) / SLOT_MIN);
  const endIndex = Math.round((state.end - OPEN_MIN) / SLOT_MIN);
  const isToday = state.dateOffset === 0;
  const slots = Array.from({ length: SLOT_COUNT }, (_, index) => {
    const slotStart = OPEN_MIN + index * SLOT_MIN;
    const slotEnd = slotStart + SLOT_MIN;
    const free = freeCountAtSlot(index);
    const past = isToday && slotStart <= NOW_MIN;
    const inRange = index >= startIndex && index < endIndex;
    const isStart = index === startIndex;
    const isEnd = index === endIndex - 1;
    const high = free <= 7;
    const bar = clamp(Math.round((free / SEATS.length) * 100), 7, 100);
    const isHour = index % 2 === 0;
    return `
      <button type="button" class="slot${isHour ? ' is-hour' : ''}${inRange ? ' is-in-range' : ''}${isStart ? ' is-range-start' : ''}${isEnd ? ' is-range-end' : ''}${past ? ' is-past' : ''}${high ? ' is-high' : ''}"
        data-slot-index="${index}" data-slot-start="${slotStart}" aria-pressed="${inRange}"
        ${past ? 'disabled' : ''} aria-label="${minutesToTime(slotStart)} 到 ${minutesToTime(slotEnd)}，${past ? '已过' : `可约 ${free} 座`}">
        <span class="slot__bar" style="--bar:${bar}%"></span>
      </button>`;
  }).join('');
  const scale = [0, 4, 8, 12, 16, 20]
    .map((index) => `<span style="left:${(index / SLOT_COUNT) * 100}%">${minutesToTime(OPEN_MIN + index * SLOT_MIN)}</span>`)
    .join('');
  const showNow = isToday && NOW_MIN >= OPEN_MIN && NOW_MIN <= CLOSE_MIN;
  const nowLeft = ((NOW_MIN - OPEN_MIN) / (CLOSE_MIN - OPEN_MIN)) * 100;
  rail.innerHTML = slots
    + `<div class="time-scale" aria-hidden="true">${scale}</div>`
    + (showNow
      ? `<div class="time-now" style="left:${nowLeft}%" aria-hidden="true"><span>现在</span></div>`
      : '');
}

function renderTimeSummary() {
  const free = freeCountAtSlot(activeSlot());
  const filterText = state.filter === 'all' ? '' : ` · 符合筛选 ${filteredSeats().length} 座`;
  $('#timeSummary').innerHTML = `
    <strong class="time-summary__range">${timeText()}</strong>
    <span class="time-summary__meta"><span class="time-summary__free">${free} 个空位</span> · ${durationHours()} 小时${filterText}</span>`;
}

function renderFilters() {
  const filters = $('#filters');
  filters.innerHTML = FILTERS.map((filter) => {
    const count = SEATS.filter((seat) => (
      (filter.id === 'all' || seat.tags.includes(filter.id)) &&
      currentStatus(seat) === 'free'
    )).length;
    const active = state.filter === filter.id;
    return `
      <button type="button" class="filter-chip${active ? ' is-active' : ''}" data-filter="${filter.id}"
        aria-pressed="${active}">
        ${filter.icon ? ICONS[filter.icon] : ''}
        ${filter.label}
        <span class="filter-chip__count">${count}</span>
      </button>`;
  }).join('');
}

function typeIcons(seat) {
  const order = ['power', 'accessible', 'vip', 'pair', 'window', 'quiet'];
  return order
    .filter((tag) => seat.tags.includes(tag))
    .slice(0, 2)
    .map((tag) => ICONS[tag])
    .join('');
}

function seatAria(seat, status, mode) {
  const labels = typeLabels(seat).join('、') || '普通座';
  const table = tableOf(seat);
  const stateLabel = STATUS[status].label;
  const action = status === 'free' ? '按回车选择该座位' : '按回车查看座位信息';
  const prefix = mode === 'admin' ? '管理视图，' : '';
  return `${prefix}座位 ${seat.id}，${table?.label || ''}桌，${areaOf(seat).name}，${labels}，当前${stateLabel}。${action}。`;
}

function tableIcons(table) {
  const order = ['power', 'accessible', 'vip', 'pair', 'window', 'quiet'];
  return order
    .filter((tag) => table.tags.includes(tag))
    .slice(0, 2)
    .map((tag) => ICONS[tag])
    .join('');
}

function tableHTML(table, mode = 'student') {
  const selectedIds = mode === 'student' ? [state.selectedSeatId] : [...state.adminSelected];
  const selected = table.seatIds.some((id) => selectedIds.includes(id));
  const dimmed = mode === 'student' && state.filter !== 'all'
    && !table.seatIds.some((id) => SEAT_MAP[id] && isFilterMatch(SEAT_MAP[id]));
  return `
    <div class="desk desk--${table.shape}${selected ? ' is-table-selected' : ''}${dimmed ? ' is-dimmed' : ''}"
      data-table-id="${table.id}" data-area="${table.area}" role="img"
      aria-label="${escapeHtml(`桌子 ${table.label}，${table.meta}`)}"
      style="left:${table.x}px;top:${table.y}px;width:${table.w}px;height:${table.h}px">
      <span class="desk__label">
        <strong>${table.label}</strong>
        <span class="desk__icons" aria-hidden="true">${tableIcons(table)}</span>
        <em>${table.meta}</em>
      </span>
    </div>`;
}

function seatHTML(seat, mode = 'student') {
  const rawStatus = mode === 'admin' && currentStatus(seat) === 'mine' ? 'taken' : currentStatus(seat);
  const selected = mode === 'student'
    ? state.selectedSeatId === seat.id
    : state.adminSelected.has(seat.id);
  const dimmed = mode === 'student' && !isFilterMatch(seat);
  const editing = mode === 'admin' && state.adminTab === 'layout' && !isReadonly();
  const shortId = seat.id.split('-').pop();
  const statusIcon = STATUS[rawStatus].icon ? ICONS[STATUS[rawStatus].icon] : '';
  const flag = STATUS[rawStatus].flag;
  const rotation = seat.rotation || 0;
  return `
    <button type="button"
      class="seat seat--${rawStatus} seat--${seat.chair}${selected ? ' is-selected' : ''}${dimmed ? ' is-dimmed' : ''}${editing ? ' is-editing' : ''}${selected && mode === 'admin' ? ' is-admin-selected' : ''}"
      style="left:${seat.x}px;top:${seat.y}px;--w:${seat.w}px;--h:${seat.h}px;width:${seat.w}px;height:${seat.h}px;rotate:${rotation}deg"
      data-seat-id="${seat.id}" data-table-id="${seat.tableId}" data-area="${seat.area}" data-status="${rawStatus}"
      aria-pressed="${selected}" aria-label="${escapeHtml(seatAria(seat, rawStatus, mode))}">
      <span class="seat__back" aria-hidden="true"></span>
      <span class="seat__pad">
        <span class="seat__no"><span class="seat__no-full">${seat.id}</span><span class="seat__no-short">${shortId}</span></span>
        ${statusIcon ? `<span class="seat__status-icon" aria-hidden="true">${statusIcon}</span>` : ''}
      </span>
      ${flag ? `<span class="seat__flag" aria-hidden="true">${flag}</span>` : ''}
    </button>`;
}

function floorArch() {
  return `
    <svg class="floor__arch" viewBox="0 0 760 580" aria-hidden="true">
      <path class="wall" d="M52 20 H46 Q20 20 20 46 V514 Q20 540 46 540 H618 M704 540 H714 Q740 540 740 514 V46 Q740 20 714 20 H500" />
      <path class="window-line" d="M52 20 H500" />
      <path class="window-line" d="M52 26 H500" opacity=".42" />
      ${Array.from({ length: 12 }, (_, index) => `<path class="window-tick" d="M${68 + index * 36} 20 V26" />`).join('')}
      <path class="door-arc" d="M618 540 V454 A86 86 0 0 1 704 540" />
      <path class="thin" d="M492 44 V528 M44 412 H716" />
      <path class="aisle" d="M500 44 V412 M44 422 H716" />
      <text x="276" y="13" text-anchor="middle">北窗 · NATURAL LIGHT</text>
      <text x="661" y="557" text-anchor="middle">主入口 · ENTRANCE</text>
      <text x="503" y="286" text-anchor="middle" transform="rotate(90 503 286)">主通道 / AISLE</text>
      <path class="thin" d="M672 566 H716 M672 562 V570 M716 562 V570" />
      <text x="694" y="576" text-anchor="middle">1m</text>
    </svg>`;
}

function buildFloor(mode) {
  const areas = AREAS.map((area) => `
    <div class="zone zone--${area.id}" style="left:${area.x}px;top:${area.y}px;width:${area.w}px;height:${area.h}px">
      <div class="zone__label"><strong>${area.name}</strong><em>${area.en}</em></div>
    </div>`).join('');
  const tables = TABLES.map((table) => tableHTML(table, mode)).join('');
  const seats = SEATS.map((seat) => seatHTML(seat, mode)).join('');
  return `
    <div class="floor">
      ${floorArch()}
      ${areas}
      <div class="facility facility--desk" style="left:310px;top:462px;width:150px;height:62px">
        <strong>前台</strong><span>SERVICE</span>
      </div>
      <div class="facility facility--column" style="left:306px;top:216px" aria-hidden="true"></div>
      <div class="facility facility--column" style="left:306px;top:420px" aria-hidden="true"></div>
      <div class="facility facility--plant" style="left:708px;top:66px" aria-hidden="true"></div>
      <div class="facility facility--plant" style="left:708px;top:486px" aria-hidden="true"></div>
      ${tables}
      ${seats}
    </div>`;
}

function renderMap(mode) {
  const stage = mode === 'student' ? $('#studentMapStage') : $('#adminMapStage');
  if (!stage) return;
  const activeId = document.activeElement?.classList?.contains('seat') && stage.contains(document.activeElement)
    ? document.activeElement.dataset.seatId
    : null;
  stage.innerHTML = buildFloor(mode);
  stage.classList.toggle('is-editing', mode === 'admin' && state.adminTab === 'layout' && !isReadonly());
  stage.dataset.mode = mode;
  syncTableSelection(mode);
  applyViewport(mode);
  if (activeId) {
    requestAnimationFrame(() => $(`.seat[data-seat-id="${activeId}"]`, stage)?.focus({ preventScroll: true }));
  }
}

function updateStudentMapMeta() {
  const counts = countStatuses();
  $('#freeCount').textContent = String(counts.free);
  $('#mapMeta').textContent = `${TABLES.length} 桌 · ${counts.free} 空闲 · ${counts.taken + counts.mine} 已约 · ${counts.fix} 维修 · ${counts.locked + counts.held} 未开放/保留`;
}

function updateSeatSelection() {
  $$('#studentMapStage .seat').forEach((element) => {
    const selected = element.dataset.seatId === state.selectedSeatId;
    element.classList.toggle('is-selected', selected);
    element.setAttribute('aria-pressed', String(selected));
  });
  $$('#adminMapStage .seat').forEach((element) => {
    const selected = state.adminSelected.has(element.dataset.seatId);
    element.classList.toggle('is-selected', selected);
    element.classList.toggle('is-admin-selected', selected);
    element.setAttribute('aria-pressed', String(selected));
  });
  syncTableSelection('student');
  syncTableSelection('admin');
}

function updateSeatStates() {
  const activeId = document.activeElement?.classList?.contains('seat')
    ? document.activeElement.dataset.seatId
    : null;
  ['student', 'admin'].forEach((mode) => {
    const stage = mode === 'student' ? $('#studentMapStage') : $('#adminMapStage');
    if (!stage) return;
    $$('.seat', stage).forEach((element) => {
      const seat = SEAT_MAP[element.dataset.seatId];
      const rawStatus = mode === 'admin' && currentStatus(seat) === 'mine' ? 'taken' : currentStatus(seat);
      Object.keys(STATUS).forEach((key) => element.classList.remove(`seat--${key}`));
      element.classList.add(`seat--${rawStatus}`);
      element.dataset.status = rawStatus;
      element.setAttribute('aria-label', seatAria(seat, rawStatus, mode));
      const flag = STATUS[rawStatus].flag;
      let flagElement = $('.seat__flag', element);
      if (flag) {
        if (!flagElement) {
          flagElement = document.createElement('span');
          flagElement.className = 'seat__flag';
          flagElement.setAttribute('aria-hidden', 'true');
          element.appendChild(flagElement);
        }
        flagElement.textContent = flag;
      } else if (flagElement) {
        flagElement.remove();
      }
      const iconHost = $('.seat__status-icon', element);
      const icon = STATUS[rawStatus].icon;
      if (icon) {
        if (!iconHost) {
          const span = document.createElement('span');
          span.className = 'seat__status-icon';
          span.setAttribute('aria-hidden', 'true');
          span.innerHTML = ICONS[icon];
          $('.seat__pad', element).appendChild(span);
        } else {
          iconHost.innerHTML = ICONS[icon];
        }
      } else if (iconHost) {
        iconHost.remove();
      }
      if (mode === 'admin') {
        const seatSelected = state.adminSelected.has(seat.id);
        element.classList.toggle('is-selected', seatSelected);
        element.classList.toggle('is-admin-selected', seatSelected);
        element.setAttribute('aria-pressed', String(seatSelected));
      } else {
        const selected = seat.id === state.selectedSeatId;
        element.classList.toggle('is-selected', selected);
        element.setAttribute('aria-pressed', String(selected));
      }
    });
  });
  syncTableSelection('student');
  syncTableSelection('admin');
  if (activeId) {
    requestAnimationFrame(() => {
      const element = $(`.seat[data-seat-id="${activeId}"]`);
      element?.focus({ preventScroll: true });
    });
  }
}

/* ------------------------------ 预约摘要 ------------------------------ */
function renderBookingCard() {
  const card = $('#bookingCard');
  const seat = selectedSeat();
  if (!seat) {
    card.innerHTML = `
      <div class="booking-head"><h2>预约摘要</h2><span>BOOKING / 01</span></div>
      <div class="booking-empty">
        <div class="booking-empty__art">${ICONS.seats}</div>
        <h3>先挑一个座位</h3>
        <p>点击地图上的空位，这里会显示日期、时段与签到提醒。</p>
      </div>`;
    return;
  }

  const status = currentStatus(seat);
  const statusMeta = STATUS[status];
  const canBook = status === 'free' && state.forceState !== 'limit';
  const tags = typeLabels(seat);
  const limitReached = state.forceState === 'limit';
  const ruleChecks = status === 'free'
    ? [
        { ok: true, text: '30 分钟粒度，时段已对齐' },
        { ok: true, text: `单次 ${durationHours()} 小时，上限 4 小时` },
        { ok: true, text: '今日已约 1 / 2 条' },
        { ok: true, text: `签到窗口 ${checkinWindow()}` },
      ]
    : [];

  card.innerHTML = `
    <div class="booking-head"><h2>预约摘要</h2><span>BOOKING / 01</span></div>
    <div class="booking-seat">
      <p class="booking-seat__eyebrow">SELECTED SEAT · ${tableOf(seat)?.label || ''} TABLE · ${areaOf(seat).en}</p>
      <div class="booking-seat__row">
        <strong class="booking-seat__no">${seat.id}</strong>
        <span class="booking-seat__zone">${areaOf(seat).name}<br>${typeLabels(seat).join(' · ') || '普通座'}</span>
      </div>
      <div class="booking-tags">${tags.map((tag) => `<span class="tag">${tag}</span>`).join('')}</div>
    </div>
    <div class="summary-rows">
      <div class="summary-row"><span class="summary-row__label">DATE</span><span class="summary-row__value">${dateText()}</span></div>
      <div class="summary-row"><span class="summary-row__label">TIME</span><span class="summary-row__value mono">${timeText()}</span></div>
      <div class="summary-row"><span class="summary-row__label">DURATION</span><span class="summary-row__value">${durationHours()} 小时</span></div>
      <div class="summary-row"><span class="summary-row__label">STATUS</span><span class="summary-row__value">${statusMeta.label}</span></div>
    </div>
    ${status !== 'free' ? `
      <div class="booking-note">${status === 'mine' ? ICONS.check : ICONS.info}
        <span>${status === 'mine'
          ? `这是你在 ${timeText()} 的预约，签到后即可使用。`
          : `该座位当前${statusMeta.label}，不能提交预约。请换一个空位或调整时间。`}</span>
      </div>` : ''}
    ${limitReached ? `
      <div class="booking-note">${ICONS.alert}
        <span>今日预约已达上限（2 / 2 条）。可以改到明天，或先取消一条未开始的预约。</span>
      </div>` : ''}
    ${ruleChecks.length ? `<div class="rule-checks">
      ${ruleChecks.map((item) => `<div class="rule-check">${ICONS.check}<span>${item.text}</span></div>`).join('')}
    </div>` : ''}
    <div class="booking-total"><span>本次预约</span><strong>免费<small> / 当前版本</small></strong></div>
    ${limitReached
      ? `<button type="button" class="btn" disabled>今日预约已达上限</button>`
      : status === 'free'
        ? `<button type="button" class="btn btn--primary" data-action="open-booking">确认预约</button>`
        : status === 'mine'
          ? `<button type="button" class="btn" data-action="open-mine">查看我的预约</button>`
          : `<button type="button" class="btn" data-action="find-alternative">看看附近空位</button>`}
    <button type="button" class="booking-secondary" data-action="view-rules">预约前先看规则 →</button>
  `;
}

function renderMobileBar() {
  const bar = $('#mobileBar');
  const seat = selectedSeat();
  if (!seat) {
    bar.innerHTML = `
      <div class="mobile-bar__seat"><span class="mobile-bar__no">—</span><div class="mobile-bar__meta"><strong>先选一个座位</strong><span>${timeText()}</span></div></div>
      <button class="btn btn--primary" type="button" disabled>确认预约</button>`;
    return;
  }
  const status = currentStatus(seat);
  const canBook = status === 'free' && state.forceState !== 'limit';
  bar.innerHTML = `
    <button class="mobile-bar__seat" type="button" data-action="open-summary" aria-label="查看预约摘要">
      <span class="mobile-bar__no">${seat.id}</span>
      <div class="mobile-bar__meta">
        <strong>${areaOf(seat).name} · ${STATUS[status].label}</strong>
        <span>${dateText()} · ${timeText()} · 免费</span>
      </div>
    </button>
    ${state.forceState === 'limit'
      ? '<button class="btn" type="button" disabled>已达上限</button>'
      : canBook
        ? `<button class="btn btn--primary" type="button" data-action="open-booking">确认预约</button>`
        : `<button class="btn" type="button" data-action="find-alternative">找空位</button>`}`;
}

/* ------------------------------ 列表视图 ------------------------------ */
function renderList() {
  const body = $('#studentListBody');
  const seats = filteredSeats();
  if (!seats.length) {
    body.innerHTML = `
      <div class="map-state" style="position:static;min-height:260px;background:transparent;backdrop-filter:none">
        <div class="map-state__icon">${ICONS.seats}</div>
        <h3>没有符合筛选的座位</h3>
        <p>试试「全部」，或换一个区域 / 时段。筛选不会改变座位在地图上的位置。</p>
        <div class="map-state__actions"><button type="button" class="btn btn--sm" data-action="clear-filter">清除筛选</button></div>
      </div>`;
    return;
  }
  body.innerHTML = AREAS.map((area) => {
    const areaSeats = seats.filter((seat) => seat.area === area.id);
    if (!areaSeats.length) return '';
    return `
      <section class="area-block" aria-labelledby="list-${area.id}">
        <div class="area-block__head"><h3 id="list-${area.id}">${area.name}</h3><span>${areaSeats.length} 座 · ${area.en}</span></div>
        <div class="seat-list">
          ${areaSeats.map((seat) => {
            const status = currentStatus(seat);
            const selected = state.selectedSeatId === seat.id;
            return `
              <button type="button" class="seat-row${selected ? ' is-selected' : ''}" data-list-seat="${seat.id}"
                aria-pressed="${selected}" aria-label="${escapeHtml(seatAria(seat, status, 'student'))}">
                <span class="seat-row__no">${seat.id}</span>
                <span class="seat-row__meta">${tableOf(seat)?.label || ''} 桌 · ${typeLabels(seat).slice(0, 2).join(' · ') || '普通座'}</span>
                <span class="seat-row__state"><i class="seat-row__dot" style="--state-line:var(--seat-${status}-line)"></i>${STATUS[status].label}</span>
              </button>`;
          }).join('')}
        </div>
      </section>`;
  }).join('');
}

'use strict';

/* ==========================================================================
   管理端渲染：占用监控 / 布局编辑 / 运营日志
   ========================================================================== */

const CONFLICTS = [
  {
    id: 'CF-20261107-01',
    seat: 'C-05',
    time: '10:00–12:00',
    user: '王**',
    note: '同一座位出现两笔有效预约，需保留一笔并联系另一位用户',
    level: '高',
  },
  {
    id: 'CF-20261107-02',
    seat: 'P-02',
    time: '14:00–16:00',
    user: '李**',
    note: '锁定操作与已确认预约重叠，等待管理员选择保留策略',
    level: '中',
  },
];

function isReadonly() {
  return state.adminRole === 'system';
}

function adminSelectionSeats() {
  return [...state.adminSelected].map((id) => SEAT_MAP[id]).filter(Boolean);
}

function statusBadge(seat) {
  const status = currentStatus(seat) === 'mine' ? 'taken' : currentStatus(seat);
  const meta = STATUS[status];
  return `<span class="status-badge" style="--state-bg:var(--seat-${status}-bg);--state-fg:var(--seat-${status}-fg);--state-line:var(--seat-${status}-line)"><i></i>${meta.label}</span>`;
}

function adminKpiHTML() {
  const counts = countStatuses();
  const total = SEATS.length;
  const occupied = counts.taken + counts.mine;
  const rate = Math.round((occupied / total) * 100);
  const attention = counts.fix + counts.locked + counts.held;
  const spark = [35, 42, 38, 56, 48, 62, 58, 74]
    .map((height) => `<i style="height:${height}%"></i>`)
    .join('');
  return `
    <article class="kpi kpi--accent">
      <div class="kpi__label">SEAT UTILIZATION</div>
      <div class="kpi__value">${rate}<small>%</small></div>
      <div class="kpi__foot">${occupied} / ${total} 座被占用</div>
      <div class="kpi__spark">${spark}</div>
    </article>
    <article class="kpi">
      <div class="kpi__label">AVAILABLE NOW</div>
      <div class="kpi__value">${counts.free}<small>座</small></div>
      <div class="kpi__foot">当前时段可预约</div>
    </article>
    <article class="kpi">
      <div class="kpi__label">OCCUPIED / IN USE</div>
      <div class="kpi__value">${occupied}<small>单</small></div>
      <div class="kpi__foot">已预约 ${counts.taken} · 使用中 ${counts.mine}</div>
    </article>
    <article class="kpi kpi--warn">
      <div class="kpi__label">NEEDS ATTENTION</div>
      <div class="kpi__value">${attention}<small>座</small></div>
      <div class="kpi__foot">维修 ${counts.fix} · 锁定 ${counts.locked} · 保留 ${counts.held}</div>
    </article>
    <article class="kpi">
      <div class="kpi__label">CONFLICT QUEUE</div>
      <div class="kpi__value">${CONFLICTS.length}<small>单</small></div>
      <div class="kpi__foot">需要管理员决策</div>
    </article>`;
}

function toneStatusBadge(level) {
  const bg = level === '高' ? 'var(--danger-soft)' : 'var(--amber-soft)';
  const fg = level === '高' ? 'var(--danger-ink)' : 'var(--amber-ink)';
  const line = level === '高' ? 'var(--danger)' : 'var(--amber)';
  return `<span class="status-badge" style="--state-bg:${bg};--state-fg:${fg};--state-line:${line}"><i></i>${level}风险</span>`;
}

function logListHTML(limit = 3) {
  return `<ul class="log-list">${state.logs.slice(0, limit).map((item) => `
    <li class="log-item">
      <time>${item.time} · ${item.actor}</time>
      <p>${item.text}</p>
    </li>`).join('')}</ul>`;
}

function conflictCardsHTML() {
  return CONFLICTS.map((item) => `
    <div class="ops-block">
      <h3>${item.seat} · ${toneStatusBadge(item.level)}</h3>
      <p>${item.note}</p>
      <div class="ops-block__meta">
        <span>${item.id} · ${item.time} · ${item.user}</span>
        <button type="button" class="btn btn--sm" data-admin-action="conflict" data-conflict-id="${item.id}">处理</button>
      </div>
    </div>`).join('');
}

function renderAdminKpis() {
  $('#adminKpis').innerHTML = adminKpiHTML();
}

function renderAdminTools() {
  const toolsByTab = {
    monitor: [
      { icon: 'select', label: '选择', action: 'select' },
      { icon: 'layers', label: '批量', action: 'batch' },
      { icon: 'lock', label: '锁区', action: 'lock-area' },
      { icon: 'wrench', label: '维修', action: 'batch-fix' },
      { icon: 'message', label: '冲突', action: 'conflicts' },
    ],
    layout: [
      { icon: 'select', label: '选择', action: 'select' },
      { icon: 'plus', label: '新增', action: 'add' },
      { icon: 'rotate', label: '旋转', action: 'rotate' },
      { icon: 'trash', label: '删除', action: 'delete' },
      { icon: 'undo', label: '撤销', action: 'undo' },
      { icon: 'redo', label: '重做', action: 'redo' },
      { icon: 'save', label: '保存', action: 'save' },
      { icon: 'upload', label: '导入', action: 'import' },
    ],
    ops: [
      { icon: 'refresh', label: '刷新', action: 'refresh' },
      { icon: 'hourglass', label: '释放', action: 'release-hold' },
      { icon: 'shield', label: '权限', action: 'permissions' },
      { icon: 'message', label: '日志', action: 'open-log' },
    ],
  };
  const tools = toolsByTab[state.adminTab] || toolsByTab.monitor;
  const readonly = isReadonly();
  $('#adminTools').innerHTML = tools.map((tool) => {
    const disabled = readonly || (tool.action === 'undo' && !state.undoStack.length) || (tool.action === 'redo' && !state.redoStack.length);
    return `<button type="button" class="tool-btn${tool.action === 'delete' || tool.action === 'batch-off' ? ' tool-btn--danger' : ''}${tool.action === 'select' && state.adminTab !== 'layout' ? ' is-active' : ''}"
      data-tool="${tool.action}" ${disabled ? 'disabled aria-disabled="true"' : ''} title="${tool.label}">
      ${ICONS[tool.icon]}<span>${tool.label}</span>
    </button>`;
  }).join('');
}

function inspectorEmptyHTML() {
  if (state.adminTab === 'layout') {
    const readonly = isReadonly();
    return `
      <div class="inspector-head"><div><h2>布局设置</h2><p>GRID 10px · SNAP ON</p></div><span class="status-badge" style="--state-bg:var(--brand-soft);--state-fg:var(--brand)"><i></i>v${state.layoutVersion}</span></div>
      <div class="inspector-seat"><strong>760 × 580</strong><span>房间逻辑坐标 · 1 单位 ≈ 1cm</span></div>
      <div class="inspector-note">拖拽座位移动，自动吸附 10px 网格；靠近其他座位时显示对齐线。<kbd>R</kbd> 旋转，<kbd>⌘Z</kbd> 撤销。</div>
      <div class="inspector-actions">
        <button type="button" class="btn btn--sm" data-admin-action="save" ${readonly ? 'disabled' : ''}>保存草稿</button>
        <button type="button" class="btn btn--sm btn--primary" data-admin-action="publish" ${readonly ? 'disabled' : ''}>发布布局</button>
      </div>
      <div class="inspector-section">
        <div class="ops-block__meta" style="border-top:0;padding-top:0;margin-top:14px">
          <span>最后保存 ${state.lastSavedAt}</span>
          <span style="color:${state.dirty ? 'var(--amber-ink)' : 'var(--brand)'}">${state.dirty ? '有未保存更改' : '已同步'}</span>
        </div>
        <button type="button" class="btn btn--sm" style="width:100%;margin-top:8px" data-admin-action="import" ${readonly ? 'disabled' : ''}>${ICONS.upload} 导入 JSON / CSV</button>
      </div>
      <div class="inspector-section">
        <div class="inspector-head"><div><h3 style="margin:0;font-family:var(--font-display);font-size:15px">区域分布</h3><p>6 个区域 · 28 座</p></div><span class="status-badge" style="--state-bg:var(--brand-wash);--state-fg:var(--brand)"><i></i>${AREAS.length}</span></div>
        <div class="batch-list">
          ${AREAS.map((area) => {
            const count = SEATS.filter((seat) => seat.area === area.id).length;
            return `<div class="batch-item"><span>${area.name}</span><span>${count} 座 · ${area.en}</span></div>`;
          }).join('')}
        </div>
      </div>
      <div class="inspector-section">
        <div class="inspector-head"><div><h3 style="margin:0;font-family:var(--font-display);font-size:15px">快捷键</h3><p>布局编辑</p></div></div>
        <div class="inspector-note" style="border-left-color:var(--brand);margin-top:0"><kbd>R</kbd> 旋转 15° · <kbd>Delete</kbd> 删除 · <kbd>⌘Z</kbd> 撤销 · <kbd>Shift⌘Z</kbd> 重做 · 按住 <kbd>Alt</kbd> 临时关闭吸附</div>
      </div>`;
  }

  if (state.adminTab === 'ops') {
    return `
      <div class="inspector-head"><div><h2>运营与日志</h2><p>IMMUTABLE AUDIT TRAIL</p></div><span class="status-badge" style="--state-bg:var(--brand-soft);--state-fg:var(--brand)"><i></i>实时</span></div>
      <div class="ops-block">
        <h3>超时未签到自动释放</h3>
        <p>系统每 10 秒同步一次占用；释放动作由服务端定时任务执行，前端只展示倒计时和结果。</p>
        <div class="ops-block__meta"><span>下一个任务 · Q-03 · 04:32</span><button type="button" class="btn btn--sm" data-admin-action="release-hold" ${isReadonly() ? 'disabled' : ''}>立即释放</button></div>
      </div>
      <div class="inspector-section">
        <div class="inspector-head"><div><h3 style="margin:0;font-family:var(--font-display);font-size:15px">操作日志</h3><p>仅展示最近 20 条</p></div></div>
        ${logListHTML(20)}
      </div>`;
  }

  return `
    <div class="inspector-head"><div><h2>运营概览</h2><p>${clockText()} · AUTO REFRESH 10s</p></div><span class="status-badge" style="--state-bg:var(--brand-soft);--state-fg:var(--brand)"><i></i>实时</span></div>
    <div class="inspector-section">
      <div class="inspector-head"><div><h3 style="margin:0;font-family:var(--font-display);font-size:15px">冲突订单</h3><p>先列影响，再决策；不自动取消</p></div><span class="status-badge" style="--state-bg:var(--danger-soft);--state-fg:var(--danger)"><i></i>${CONFLICTS.length}</span></div>
      ${conflictCardsHTML()}
    </div>
    <div class="inspector-section">
      <div class="ops-block">
        <h3>临时保留 · Q-03</h3>
        <p>管理员保留了该座位用于设备调试。保留到期后自动回到可用状态。</p>
        <div class="ops-block__meta"><span>剩余 04:32</span><button type="button" class="btn btn--sm" data-admin-action="release-hold" ${isReadonly() ? 'disabled' : ''}>释放</button></div>
      </div>
    </div>
    <div class="inspector-section">
      <div class="inspector-head"><div><h3 style="margin:0;font-family:var(--font-display);font-size:15px">最近操作</h3><p>自动记录操作者与原因</p></div><button type="button" class="btn btn--sm" data-admin-action="open-log">全部</button></div>
      ${logListHTML(3)}
    </div>`;
}

function inspectorSeatHTML(seat) {
  const status = currentStatus(seat);
  const area = areaOf(seat);
  const readonly = isReadonly();
  const isLayout = state.adminTab === 'layout';
  const isOccupied = status === 'taken' || status === 'mine';
  const canRestore = status === 'locked' || status === 'fix' || status === 'held';
  return `
    <div class="inspector-head">
      <div><h2>座位 ${seat.id}</h2><p>${area.name} · ${typeLabels(seat).join(' / ') || '普通座'} · ${tableOf(seat)?.label || '—'} 桌</p></div>
      ${statusBadge(seat)}
    </div>
    <div class="inspector-seat"><strong>${seat.id}</strong><span>${tableOf(seat)?.meta || ''} · 椅子 ${seat.w} × ${seat.h}</span></div>

    ${isOccupied ? `
      <div class="inspector-note">
        占用时段 <strong>${timeText()}</strong><br>
        用户 王** · 学号 2023****21<br>
        ${status === 'mine' ? '已签到，使用中' : '待使用 · 签到窗口 ' + checkinWindow()}
      </div>
      <div class="inspector-actions">
        <button type="button" class="btn btn--sm" data-admin-action="open-reservation">查看预约</button>
        <button type="button" class="btn btn--sm" data-admin-action="message-user" ${readonly ? 'disabled' : ''}>发消息</button>
      </div>
    ` : ''}

    <div class="inspector-section">
      <div class="inspector-grid">
        <label class="inspector-field"><span>TYPE</span>
          <select data-admin-field="type" ${readonly ? 'disabled' : ''}>
            ${Object.entries(TYPE_LABEL).map(([value, label]) => `<option value="${value}" ${seat.type === value ? 'selected' : ''}>${label}</option>`).join('')}
          </select>
        </label>
        <label class="inspector-field"><span>STATUS</span>
          <select disabled>
            <option>${STATUS[status].label}</option>
          </select>
        </label>
        ${isLayout ? `
          <label class="inspector-field"><span>X / CM</span><input type="number" value="${seat.x}" data-admin-field="x" ${readonly ? 'disabled' : ''}></label>
          <label class="inspector-field"><span>Y / CM</span><input type="number" value="${seat.y}" data-admin-field="y" ${readonly ? 'disabled' : ''}></label>
          <label class="inspector-field"><span>W / CM</span><input type="number" value="${seat.w}" data-admin-field="w" ${readonly ? 'disabled' : ''}></label>
          <label class="inspector-field"><span>H / CM</span><input type="number" value="${seat.h}" data-admin-field="h" ${readonly ? 'disabled' : ''}></label>
          <label class="inspector-field"><span>ROTATION</span><input type="number" step="15" value="${seat.rotation || 0}" data-admin-field="rotation" ${readonly ? 'disabled' : ''}></label>
          <label class="inspector-field"><span>PRICE</span><input value="免费" disabled></label>
        ` : ''}
      </div>
      <div class="inspector-note">资源状态与「时段占用」分开管理。调整资源状态不会自动取消任何预约；系统会先列出受影响预约，再要求二次确认。</div>
      <div class="inspector-actions">
        ${canRestore
          ? `<button type="button" class="btn btn--sm btn--primary" data-admin-action="restore" ${readonly ? 'disabled' : ''}>恢复可用</button>`
          : `<button type="button" class="btn btn--sm" data-admin-action="lock" ${readonly ? 'disabled' : ''}>锁定</button>
             <button type="button" class="btn btn--sm" data-admin-action="fix" ${readonly ? 'disabled' : ''}>维修</button>
             <button type="button" class="btn btn--sm" data-admin-action="off" ${readonly ? 'disabled' : ''}>停用</button>`}
      </div>
      ${isLayout ? `<div class="inspector-actions">
        <button type="button" class="btn btn--sm" data-admin-action="rotate" ${readonly ? 'disabled' : ''}>旋转 15°</button>
        <button type="button" class="btn btn--sm" data-admin-action="delete" ${readonly ? 'disabled' : ''}>删除座位</button>
      </div>` : ''}
    </div>`;
}

function inspectorBatchHTML(seats) {
  const readonly = isReadonly();
  return `
    <div class="inspector-head">
      <div><h2>已选 ${seats.length} 座</h2><p>${[...new Set(seats.map((seat) => areaOf(seat).name))].join(' · ')}</p></div>
      <span class="status-badge" style="--state-bg:var(--brand-soft);--state-fg:var(--brand)"><i></i>批量</span>
    </div>
    <div class="batch-count"><strong>${seats.length}</strong><span>个座位将被调整</span></div>
    <div class="batch-list">${seats.slice(0, 8).map((seat) => `<div class="batch-item"><span>${seat.id}</span><span>${STATUS[currentStatus(seat)].label}</span></div>`).join('')}${seats.length > 8 ? `<div class="batch-item"><span>…</span><span>另 ${seats.length - 8} 座</span></div>` : ''}</div>
    <div class="inspector-note">批量操作会先展示受影响的有效预约清单。确认后执行；预约不会被静默取消。</div>
    <div class="inspector-actions">
      <button type="button" class="btn btn--sm" data-admin-action="batch-lock" ${readonly ? 'disabled' : ''}>批量锁定</button>
      <button type="button" class="btn btn--sm" data-admin-action="batch-fix" ${readonly ? 'disabled' : ''}>批量维修</button>
      <button type="button" class="btn btn--sm btn--danger" data-admin-action="batch-off" ${readonly ? 'disabled' : ''}>批量停用</button>
    </div>
    <div class="inspector-actions">
      <button type="button" class="btn btn--sm btn--ghost" data-admin-action="clear-selection" style="flex:1">清空选择</button>
    </div>`;
}

function renderAdminInspector() {
  const inspector = $('#adminInspector');
  const seats = adminSelectionSeats();
  if (seats.length === 0) {
    inspector.innerHTML = inspectorEmptyHTML();
  } else if (seats.length === 1) {
    inspector.innerHTML = inspectorSeatHTML(seats[0]);
  } else {
    inspector.innerHTML = inspectorBatchHTML(seats);
  }
}

function renderAdminChrome() {
  const readonly = isReadonly();
  const counts = countStatuses();
  $('#adminView').classList.toggle('is-readonly', readonly);
  $('#adminBanner').hidden = !readonly;
  $('#adminModePill').textContent = readonly
    ? '只读预览'
    : state.adminTab === 'layout'
      ? '布局编辑'
      : state.adminTab === 'ops'
        ? '运营视图'
        : '监控模式';
  $('#adminMapMeta').textContent = `${SEATS.length} 座 / ${TABLES.length} 桌 · ${counts.free} 空闲 · ${counts.taken + counts.mine} 已约 · ${counts.fix} 维修 · ${counts.locked} 锁定 · ${counts.held} 保留`;
  $('#adminLive').innerHTML = `<span class="live-dot"></span><span>实时 · 10s</span><strong>${clockText()}</strong>`;
  $('#adminStamp').textContent = `最后同步 ${clockText()}`;
  $('#editorGridHint').hidden = !(state.adminTab === 'layout' && !readonly);
  $('#adminRole').value = state.adminRole;
  renderAdminKpis();
  renderAdminTools();
  renderAdminInspector();
}

function renderAdminShell() {
  renderAdminChrome();
}

function switchAdminTab(tab) {
  if (state.adminTab === tab) return;
  state.adminTab = tab;
  state.editing = tab === 'layout';
  state.adminSelected.clear();
  $$('.admin-tab').forEach((button) => {
    button.classList.toggle('is-active', button.dataset.adminTab === tab);
  });
  renderAdminChrome();
  renderMap('admin');
}

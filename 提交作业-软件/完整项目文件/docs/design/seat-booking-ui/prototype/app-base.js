'use strict';

/* ==========================================================================
   「纸间座标」座位预约原型 · 数据层
   - 学生端 / 管理端共用场景、状态与业务派生
   - 仅用于设计评审与交互验证，不连接真实后端
   ========================================================================== */

/* ------------------------------ 基础工具 ------------------------------ */
const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => Array.from(root.querySelectorAll(selector));
const clamp = (value, min, max) => Math.min(max, Math.max(min, value));
const pad2 = (value) => String(value).padStart(2, '0');
const minutesToTime = (minutes) => `${pad2(Math.floor(minutes / 60))}:${pad2(minutes % 60)}`;
const timeToMinutes = (text) => {
  const [hour, minute] = text.split(':').map(Number);
  return hour * 60 + minute;
};
const shortMoney = (value) => (value === 0 ? '免费' : `¥${value}`);
const escapeHtml = (value) =>
  String(value).replace(/[&<>"']/g, (char) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[char]);

function hash(text) {
  let value = 2166136261;
  for (let index = 0; index < text.length; index += 1) {
    value ^= text.charCodeAt(index);
    value = Math.imul(value, 16777619);
  }
  return value >>> 0;
}

const ICONS = {
  window:
    '<svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><rect x="4" y="4" width="16" height="16" rx="2" stroke="currentColor" stroke-width="1.7"/><path d="M12 4v16M4 12h16" stroke="currentColor" stroke-width="1.7"/></svg>',
  power:
    '<svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="m13 2-8 12h6l-1 8 8-12h-6l1-8Z" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round"/></svg>',
  quiet:
    '<svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M19.5 15.2A7.8 7.8 0 0 1 8.8 4.5 8.2 8.2 0 1 0 19.5 15.2Z" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round"/></svg>',
  accessible:
    '<svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><circle cx="12" cy="4.5" r="2" stroke="currentColor" stroke-width="1.7"/><path d="M12 8v6h4.5l2.5 5M12 11.5H8.5M7.5 14a5 5 0 1 0 5 5" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/></svg>',
  star:
    '<svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="m12 3 2.8 5.7 6.2.9-4.5 4.4 1.1 6.2-5.6-3-5.6 3 1.1-6.2L3 9.6l6.2-.9L12 3Z" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round"/></svg>',
  pair:
    '<svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><circle cx="8" cy="8" r="3" stroke="currentColor" stroke-width="1.7"/><circle cx="16" cy="16" r="3" stroke="currentColor" stroke-width="1.7"/><path d="m10.2 9.8 3.6 3.6" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/></svg>',
  clock:
    '<svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><circle cx="12" cy="12" r="8.2" stroke="currentColor" stroke-width="1.8"/><path d="M12 7.5V12l3 2" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg>',
  check:
    '<svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="m5 12.5 4.5 4.5L19 6.8" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>',
  lock:
    '<svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><rect x="5" y="10" width="14" height="10" rx="2" stroke="currentColor" stroke-width="1.8"/><path d="M8 10V7.8a4 4 0 0 1 8 0V10" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg>',
  wrench:
    '<svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M14.5 6.5a4.5 4.5 0 0 0-6.1 6.1L3 18l3 3 5.4-5.4a4.5 4.5 0 0 0 6.1-6.1l-3 3-2.4-2.4 3-3Z" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round"/></svg>',
  hourglass:
    '<svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M7 3h10M7 21h10M7 3c0 5 5 5 5 9s-5 4-5 9M17 3c0 5-5 5-5 9s5 4 5 9" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg>',
  info:
    '<svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><circle cx="12" cy="12" r="8.5" stroke="currentColor" stroke-width="1.8"/><path d="M12 10.5V17M12 7.2v.2" stroke="currentColor" stroke-width="1.9" stroke-linecap="round"/></svg>',
  alert:
    '<svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M12 3 2.8 20h18.4L12 3Z" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"/><path d="M12 9v5M12 17.2v.2" stroke="currentColor" stroke-width="1.9" stroke-linecap="round"/></svg>',
  arrow:
    '<svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M4 12h15M13 6l6 6-6 6" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>',
  close:
    '<svg viewBox="0 0 20 20" fill="none" aria-hidden="true"><path d="m5 5 10 10M15 5 5 15" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/></svg>',
  refresh:
    '<svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M19 8a7.5 7.5 0 1 0 1 5" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/><path d="M19 3v5h-5" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>',
  select:
    '<svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="m5 3 13 7-5.7 1.3L9.5 17 5 3Z" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round"/></svg>',
  hand:
    '<svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M8 11V5.5a1.5 1.5 0 0 1 3 0V11m0-4.5a1.5 1.5 0 0 1 3 0V11m0-3.5a1.5 1.5 0 0 1 3 0V13m0-2.5a1.5 1.5 0 0 1 3 0V15a6 6 0 0 1-6 6h-1.5a6 6 0 0 1-4.7-2.3L5.2 14a1.6 1.6 0 0 1 2.5-2l1.3 1.4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>',
  plus:
    '<svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M12 4v16M4 12h16" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg>',
  trash:
    '<svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M4 7h16M9 3h6l1 4H8l1-4ZM7 7l1 14h8l1-14" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/></svg>',
  rotate:
    '<svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M20 8V3l-2 2a8 8 0 1 0 1.2 10" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>',
  undo:
    '<svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M9 7 4 12l5 5" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/><path d="M4 12h8a7 7 0 0 1 7 7" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg>',
  redo:
    '<svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="m15 7 5 5-5 5" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/><path d="M20 12h-8a7 7 0 0 0-7 7" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg>',
  save:
    '<svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M5 4h12l3 3v13H4V4h1Z" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round"/><path d="M8 4v6h8V4M8 20v-6h8v6" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round"/></svg>',
  upload:
    '<svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M12 16V4m0 0L7 9m5-5 5 5M4 15v5h16v-5" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>',
  layers:
    '<svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="m12 3 9 5-9 5-9-5 9-5Z" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round"/><path d="m3 12 9 5 9-5M3 16l9 5 9-5" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round"/></svg>',
  grid:
    '<svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><rect x="4" y="4" width="16" height="16" rx="1" stroke="currentColor" stroke-width="1.6"/><path d="M4 10h16M4 15h16M10 4v16M15 4v16" stroke="currentColor" stroke-width="1.2"/></svg>',
  message:
    '<svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M4 5h16v11H9l-5 4V5Z" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round"/></svg>',
  shield:
    '<svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M12 3 5 6v6c0 4.5 3 7.5 7 9 4-1.5 7-4.5 7-9V6l-7-3Z" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round"/><path d="m9 12 2 2 4-4" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/></svg>',
  seats:
    '<svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M5 10V6a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2v4M4 10h16v7H4v-7Z" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round"/><path d="M7 17v3M17 17v3" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/></svg>',
  users:
    '<svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><circle cx="9" cy="8" r="3" stroke="currentColor" stroke-width="1.7"/><path d="M3.5 19a5.5 5.5 0 0 1 11 0M16 5.5a3 3 0 0 1 0 5.8M17 14a5 5 0 0 1 3.5 5" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/></svg>',
};

/* ------------------------------ 场景数据 ------------------------------ */
const ROOM = { w: 760, h: 580, name: '静园自习室 A-201', floor: '2F · 东侧' };
const OPEN_MIN = 8 * 60;
const CLOSE_MIN = 22 * 60;
const SLOT_MIN = 30;
const MAX_BOOKING_MIN = 240;
const SLOT_COUNT = (CLOSE_MIN - OPEN_MIN) / SLOT_MIN;
const WEEKDAY = ['周日', '周一', '周二', '周三', '周四', '周五', '周六'];

const NOW = new Date();
const TODAY = new Date(NOW.getFullYear(), NOW.getMonth(), NOW.getDate());
const NOW_MIN = NOW.getHours() * 60 + NOW.getMinutes();
const CAN_BOOK_TODAY = NOW_MIN < CLOSE_MIN - SLOT_MIN;

const AREAS = [
  { id: 'window', name: '窗边静区', en: 'WINDOW QUIET', x: 44, y: 44, w: 448, h: 150, tone: 'sage' },
  { id: 'pair', name: '双人研习舱', en: 'PAIR POD', x: 512, y: 44, w: 204, h: 150, tone: 'amber' },
  { id: 'central', name: '中央开放区', en: 'OPEN DESK', x: 44, y: 216, w: 448, h: 196, tone: 'amber' },
  { id: 'power', name: '电源长桌', en: 'POWER BAR', x: 512, y: 216, w: 204, h: 196, tone: 'sage' },
  { id: 'quiet', name: '静音角', en: 'SILENT NOOK', x: 44, y: 430, w: 248, h: 106, tone: 'slate' },
  { id: 'accessible', name: '无障碍位', en: 'ACCESS', x: 500, y: 430, w: 216, h: 106, tone: 'blue' },
];

const AREA_MAP = Object.fromEntries(AREAS.map((area) => [area.id, area]));

/* 家具模型：桌子是空间对象，椅子才是可预约对象。
   每张桌子在 room 逻辑坐标中占一个矩形；椅子围绕桌边摆放，开口朝向桌面。 */
const TABLES = [
  {
    id: 'T-W1', area: 'window', x: 62, y: 106, w: 184, h: 44, shape: 'rect',
    label: 'W1', meta: '4 座', tags: ['window', 'quiet'],
    seatIds: ['W-01', 'W-02', 'W-03', 'W-04'],
  },
  {
    id: 'T-W2', area: 'window', x: 282, y: 106, w: 184, h: 44, shape: 'rect',
    label: 'W2', meta: '4 座', tags: ['window', 'quiet'],
    seatIds: ['W-05', 'W-06', 'W-07', 'W-08'],
  },
  {
    id: 'T-P1', area: 'pair', x: 548, y: 102, w: 132, h: 44, shape: 'capsule',
    label: 'P1', meta: '2 座 · 对坐', tags: ['pair', 'power'],
    seatIds: ['P-01', 'P-02'],
  },
  {
    id: 'T-C1', area: 'central', x: 56, y: 290, w: 96, h: 42, shape: 'rect',
    label: 'C1', meta: '2 座', tags: [],
    seatIds: ['C-01', 'C-02'],
  },
  {
    id: 'T-C2', area: 'central', x: 162, y: 290, w: 96, h: 42, shape: 'rect',
    label: 'C2', meta: '2 座', tags: ['power', 'vip'],
    seatIds: ['C-03', 'C-04'],
  },
  {
    id: 'T-C3', area: 'central', x: 268, y: 290, w: 96, h: 42, shape: 'rect',
    label: 'C3', meta: '2 座', tags: [],
    seatIds: ['C-05', 'C-06'],
  },
  {
    id: 'T-C4', area: 'central', x: 374, y: 290, w: 96, h: 42, shape: 'rect',
    label: 'C4', meta: '2 座', tags: ['power'],
    seatIds: ['C-07', 'C-08'],
  },
  {
    id: 'T-PWR', area: 'power', x: 582, y: 246, w: 62, h: 146, shape: 'rect',
    label: 'PWR', meta: '4 座 · 长桌', tags: ['power'],
    seatIds: ['PWR-01', 'PWR-02', 'PWR-03', 'PWR-04'],
  },
  {
    id: 'T-Q1', area: 'quiet', x: 166, y: 460, w: 56, h: 44, shape: 'round',
    label: 'Q1', meta: '4 座', tags: ['quiet'],
    seatIds: ['Q-01', 'Q-02', 'Q-03', 'Q-04'],
  },
  {
    id: 'T-A1', area: 'accessible', x: 520, y: 450, w: 174, h: 42, shape: 'capsule',
    label: 'A1', meta: '2 座 · 宽敞', tags: ['accessible'],
    seatIds: ['A-01', 'A-02'],
  },
];

const TABLE_MAP = Object.fromEntries(TABLES.map((table) => [table.id, table]));

const SEATS = [
  // 窗边静区：两张四人长桌，长边各两椅，面向窗 / 背窗
  { id: 'W-01', tableId: 'T-W1', area: 'window', x: 84, y: 74, w: 30, h: 30, chair: 'n', type: 'quiet', tags: ['window', 'quiet'] },
  { id: 'W-02', tableId: 'T-W1', area: 'window', x: 162, y: 74, w: 30, h: 30, chair: 'n', type: 'quiet', tags: ['window', 'quiet'] },
  { id: 'W-03', tableId: 'T-W1', area: 'window', x: 84, y: 152, w: 30, h: 30, chair: 's', type: 'quiet', tags: ['window', 'quiet'] },
  { id: 'W-04', tableId: 'T-W1', area: 'window', x: 162, y: 152, w: 30, h: 30, chair: 's', type: 'quiet', tags: ['window', 'quiet'] },
  { id: 'W-05', tableId: 'T-W2', area: 'window', x: 304, y: 74, w: 30, h: 30, chair: 'n', type: 'quiet', tags: ['window', 'quiet'] },
  { id: 'W-06', tableId: 'T-W2', area: 'window', x: 382, y: 74, w: 30, h: 30, chair: 'n', type: 'quiet', tags: ['window', 'quiet'] },
  { id: 'W-07', tableId: 'T-W2', area: 'window', x: 304, y: 152, w: 30, h: 30, chair: 's', type: 'quiet', tags: ['window', 'quiet'] },
  { id: 'W-08', tableId: 'T-W2', area: 'window', x: 382, y: 152, w: 30, h: 30, chair: 's', type: 'quiet', tags: ['window', 'quiet'] },

  // 双人研习舱：一张对坐双人桌
  { id: 'P-01', tableId: 'T-P1', area: 'pair', x: 598, y: 70, w: 32, h: 30, chair: 'n', type: 'pair', tags: ['pair', 'power'] },
  { id: 'P-02', tableId: 'T-P1', area: 'pair', x: 598, y: 148, w: 32, h: 30, chair: 's', type: 'vip', tags: ['pair', 'power', 'vip'] },

  // 中央开放区：四张两人桌并排，每张两侧各一椅
  { id: 'C-01', tableId: 'T-C1', area: 'central', x: 89, y: 258, w: 30, h: 30, chair: 'n', type: 'normal', tags: [] },
  { id: 'C-02', tableId: 'T-C1', area: 'central', x: 89, y: 334, w: 30, h: 30, chair: 's', type: 'normal', tags: [] },
  { id: 'C-03', tableId: 'T-C2', area: 'central', x: 195, y: 258, w: 30, h: 30, chair: 'n', type: 'normal', tags: ['power'] },
  { id: 'C-04', tableId: 'T-C2', area: 'central', x: 195, y: 334, w: 30, h: 30, chair: 's', type: 'vip', tags: ['vip'] },
  { id: 'C-05', tableId: 'T-C3', area: 'central', x: 301, y: 258, w: 30, h: 30, chair: 'n', type: 'normal', tags: [] },
  { id: 'C-06', tableId: 'T-C3', area: 'central', x: 301, y: 334, w: 30, h: 30, chair: 's', type: 'normal', tags: ['power'] },
  { id: 'C-07', tableId: 'T-C4', area: 'central', x: 407, y: 258, w: 30, h: 30, chair: 'n', type: 'normal', tags: ['power'] },
  { id: 'C-08', tableId: 'T-C4', area: 'central', x: 407, y: 334, w: 30, h: 30, chair: 's', type: 'normal', tags: [] },

  // 电源长桌：一张竖向长桌，两侧各两椅
  { id: 'PWR-01', tableId: 'T-PWR', area: 'power', x: 548, y: 262, w: 30, h: 30, chair: 'w', type: 'power', tags: ['power'] },
  { id: 'PWR-02', tableId: 'T-PWR', area: 'power', x: 646, y: 262, w: 30, h: 30, chair: 'e', type: 'power', tags: ['power'] },
  { id: 'PWR-03', tableId: 'T-PWR', area: 'power', x: 548, y: 340, w: 30, h: 30, chair: 'w', type: 'power', tags: ['power'] },
  { id: 'PWR-04', tableId: 'T-PWR', area: 'power', x: 646, y: 340, w: 30, h: 30, chair: 'e', type: 'power', tags: ['power'] },

  // 静音角：一张四人圆桌，四向各一椅
  { id: 'Q-01', tableId: 'T-Q1', area: 'quiet', x: 180, y: 434, w: 28, h: 22, chair: 'n', type: 'quiet', tags: ['quiet'] },
  { id: 'Q-02', tableId: 'T-Q1', area: 'quiet', x: 180, y: 506, w: 28, h: 22, chair: 's', type: 'quiet', tags: ['quiet', 'power'] },
  { id: 'Q-03', tableId: 'T-Q1', area: 'quiet', x: 136, y: 464, w: 28, h: 22, chair: 'w', type: 'quiet', tags: ['quiet'] },
  { id: 'Q-04', tableId: 'T-Q1', area: 'quiet', x: 224, y: 464, w: 28, h: 22, chair: 'e', type: 'quiet', tags: ['quiet'] },

  // 无障碍位：一张宽桌，两把同向椅，靠近入口
  { id: 'A-01', tableId: 'T-A1', area: 'accessible', x: 560, y: 500, w: 36, h: 26, chair: 's', type: 'accessible', tags: ['accessible'] },
  { id: 'A-02', tableId: 'T-A1', area: 'accessible', x: 644, y: 500, w: 36, h: 26, chair: 's', type: 'accessible', tags: ['accessible', 'power'] },
];

const SEAT_MAP = Object.fromEntries(SEATS.map((seat) => [seat.id, seat]));

function tableOf(seat) {
  return TABLE_MAP[seat?.tableId] || null;
}

const TYPE_LABEL = {
  normal: '普通座',
  quiet: '安静座',
  power: '电源座',
  accessible: '无障碍座',
  vip: '长时段座',
  pair: '双人桌',
};

const TAG_LABEL = {
  window: '靠窗',
  quiet: '安静',
  power: '带电源',
  accessible: '无障碍',
  vip: '长时段',
  pair: '双人桌',
};

const FILTERS = [
  { id: 'all', label: '全部', icon: null },
  { id: 'window', label: '靠窗', icon: 'window' },
  { id: 'power', label: '带电源', icon: 'power' },
  { id: 'quiet', label: '安静', icon: 'quiet' },
  { id: 'accessible', label: '无障碍', icon: 'accessible' },
  { id: 'pair', label: '双人桌', icon: 'pair' },
  { id: 'vip', label: '长时段', icon: 'star' },
];

const STATUS = {
  free: { label: '空闲', flag: '', icon: null, badge: '可预约' },
  taken: { label: '已被预约', flag: '', icon: 'clock', badge: '占用中' },
  mine: { label: '我的预约', flag: '我的', icon: 'check', badge: '我的' },
  held: { label: '临时保留', flag: '保留', icon: 'hourglass', badge: '保留' },
  locked: { label: '未开放', flag: '锁', icon: 'lock', badge: '未开放' },
  fix: { label: '维修中', flag: '修', icon: 'wrench', badge: '维修' },
};

const BLUEPRINT = {
  'W-02': 'taken',
  'W-05': 'mine',
  'W-06': 'taken',
  'W-08': 'fix',
  'C-02': 'taken',
  'C-05': 'taken',
  'C-06': 'taken',
  'PWR-02': 'taken',
  'PWR-04': 'locked',
  'Q-03': 'held',
  'Q-04': 'fix',
};

const DATES = Array.from({ length: 7 }, (_, offset) => {
  const date = new Date(TODAY);
  date.setDate(TODAY.getDate() + offset);
  return {
    offset,
    date,
    iso: `${date.getFullYear()}-${pad2(date.getMonth() + 1)}-${pad2(date.getDate())}`,
    dayLabel: offset === 0 ? '今天' : offset === 1 ? '明天' : WEEKDAY[date.getDay()],
    dateLabel: `${pad2(date.getMonth() + 1)}.${pad2(date.getDate())}`,
    longLabel: `${date.getMonth() + 1} 月 ${date.getDate()} 日 ${WEEKDAY[date.getDay()]}`,
  };
});

const defaultOffset = CAN_BOOK_TODAY ? 0 : 1;
const defaultStart = CAN_BOOK_TODAY
  ? clamp(Math.ceil((NOW_MIN + 1) / SLOT_MIN) * SLOT_MIN, OPEN_MIN, CLOSE_MIN - 60)
  : 600;

/* ------------------------------ 状态 ------------------------------ */
const query = new URLSearchParams(window.location.search);
const state = {
  mode: query.get('mode') === 'admin' ? 'admin' : 'student',
  dateOffset: defaultOffset,
  blueprintDate: defaultOffset,
  start: defaultStart,
  end: Math.min(defaultStart + 120, CLOSE_MIN),
  filter: 'all',
  view: 'map',
  selectedSeatId: 'C-03',
  confirmedSeatId: null,
  confirmedIntent: null,
  submitting: false,
  dailyUsed: 1,
  forceState: query.get('state') || '',
  sheetOpen: false,
  adminTab: query.get('tab') === 'layout' ? 'layout' : 'monitor',
  adminRole: query.get('role') === 'system' ? 'system' : 'manager',
  adminSelected: new Set(),
  editing: query.get('tab') === 'layout',
  dirty: false,
  layoutVersion: 12,
  logs: [
    { time: '10:12:26', actor: '周岚', text: '将 <strong>W-08</strong> 标记为维修中，原因「桌面松动」' },
    { time: '10:08:02', actor: '系统', text: '自动释放超时未签到座位 <strong>C-06</strong> 的预约' },
    { time: '09:54:41', actor: '周岚', text: '锁定 <strong>PWR-04</strong>，原因「插座检修」' },
    { time: '09:30:00', actor: '系统', text: '布局版本 <strong>v12</strong> 已同步到 28 个座位' },
  ],
  statusOverrides: {},
  undoStack: [],
  redoStack: [],
  lastSavedAt: '10:20',
  roomName: ROOM.name,
};

if (state.dateOffset === 0 && state.start <= NOW_MIN) {
  state.start = clamp(Math.ceil((NOW_MIN + 1) / SLOT_MIN) * SLOT_MIN, OPEN_MIN, CLOSE_MIN - 30);
  state.end = Math.min(state.start + 120, CLOSE_MIN);
}

/* ------------------------------ 状态计算 ------------------------------ */
const activeSlot = () => Math.floor((state.start - OPEN_MIN) / SLOT_MIN);
const selectedDate = () => DATES[state.dateOffset];
const isBlueprintSlot = (slotIndex = activeSlot(), dateOffset = state.dateOffset) =>
  dateOffset === state.blueprintDate && slotIndex === 4 && state.start === 600 && state.end === 720;

function isMineWindow(slotIndex = activeSlot(), dateOffset = state.dateOffset) {
  return dateOffset === state.blueprintDate && slotIndex >= 4 && slotIndex < 8;
}

function statusFor(seat, slotIndex = activeSlot(), dateOffset = state.dateOffset) {
  if (state.statusOverrides[seat.id]) return state.statusOverrides[seat.id];
  if (state.confirmedSeatId === seat.id) return 'mine';
  if (seat.id === 'W-08' || seat.id === 'Q-04') return 'fix';
  if (seat.id === 'PWR-04') return 'locked';
  if (seat.id === 'Q-03') return 'held';
  if (seat.id === 'W-05' && isMineWindow(slotIndex, dateOffset)) return 'mine';
  if (isBlueprintSlot(slotIndex, dateOffset)) return BLUEPRINT[seat.id] || 'free';
  const value = hash(`${seat.id}|${dateOffset}|${slotIndex}`) % 100;
  if (value < 26) return 'taken';
  return 'free';
}

function currentStatus(seat) {
  return statusFor(seat, activeSlot(), state.dateOffset);
}

function countStatuses() {
  const counts = { free: 0, taken: 0, mine: 0, held: 0, locked: 0, fix: 0 };
  SEATS.forEach((seat) => {
    counts[currentStatus(seat)] += 1;
  });
  return counts;
}

function isFilterMatch(seat) {
  return state.filter === 'all' || seat.tags.includes(state.filter);
}

function filteredSeats() {
  return SEATS.filter(isFilterMatch);
}

function freeCountAtSlot(slotIndex, dateOffset = state.dateOffset) {
  return SEATS.filter((seat) => statusFor(seat, slotIndex, dateOffset) === 'free').length;
}

function selectedSeat() {
  return SEAT_MAP[state.selectedSeatId] || null;
}

function areaOf(seat) {
  return AREA_MAP[seat.area] || AREAS[0];
}

function typeLabels(seat) {
  const labels = [];
  if (seat.type && seat.type !== 'normal') labels.push(TYPE_LABEL[seat.type]);
  seat.tags.forEach((tag) => {
    if (tag !== seat.type && TAG_LABEL[tag]) labels.push(TAG_LABEL[tag]);
  });
  return [...new Set(labels)];
}

function dateText() {
  return selectedDate().longLabel;
}

function timeText(start = state.start, end = state.end) {
  return `${minutesToTime(start)} — ${minutesToTime(end)}`;
}

function durationHours(start = state.start, end = state.end) {
  const hours = (end - start) / 60;
  return Number.isInteger(hours) ? `${hours}` : hours.toFixed(1);
}

function checkinWindow(start = state.start) {
  const from = Math.max(OPEN_MIN, start - 15);
  const to = Math.min(CLOSE_MIN, start + 15);
  return `${minutesToTime(from)}–${minutesToTime(to)}`;
}

const demoClock = new Date();
demoClock.setHours(10, 24, 3, 0);
const clockText = () => `${pad2(demoClock.getHours())}:${pad2(demoClock.getMinutes())}:${pad2(demoClock.getSeconds())}`;

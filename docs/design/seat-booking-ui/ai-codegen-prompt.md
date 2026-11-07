# AI 前端代码生成 Prompt

> 用法：把本文件中的 **Prompt 1** 先交给能读取仓库的 AI（Claude Code / Cursor / Codex），生成共享层；再分别用 **Prompt 2**、**Prompt 3** 生成学生端和管理端。  
> 生成后必须运行 `npm run type-check`、`npm run build`，并逐项对照 [`README.md`](README.md) §7 验收。  
> 禁止让 AI 复制任何第三方品牌 Logo、插画、图标包或文案；只允许借鉴信息架构与交互模式。

---

## Prompt 1：共享设计系统与地图底座

```text
你是本项目（Vue 3 + TypeScript + Vite + Element Plus + Pinia + SCSS）的资深前端工程师。请先在仓库中阅读：
- frontend/src/views/student/SeatBookingView.vue
- frontend/src/utils/useSeatBooking.ts
- frontend/src/utils/bookingRules.ts
- frontend/src/components/booking/SeatMatrix.vue
- frontend/src/components/booking/SeatCell.vue
- frontend/src/views/admin/SeatManageView.vue
- frontend/src/types/index.ts
- frontend/src/assets/styles/index.scss

任务：实现「纸间座标 / Paper Coordinates」座位预约模块的共享层。遵循当前业务规则（2026-11-07 起预约粒度 5 分钟）；不要改动后端接口；不要删除任何已有页面。

一、业务硬约束
1. 时间区间左闭右开 [s,e)，粒度 5 分钟；单次最长 4 小时；最多提前 7 天；每人每天最多 2 条有效预约；同一用户同一时段不能重叠。
2. 座位资源状态只有：可用 / 维修中 / 停用。严禁把「已预约 / 使用中 / 我的预约」写入 seat.status。
3. 地图状态是派生值：
   type SeatSlotState = 'free' | 'taken' | 'mine' | 'held' | 'locked' | 'fix'
   - resourceStatus 可用 + 该时段无有效预约 = free
   - resourceStatus 可用 + 他人有效预约 = taken
   - resourceStatus 可用 + 当前用户有效预约 = mine
   - 管理员临时保留 = held（P1；未实现时不要伪造）
   - 停用 / 区域锁定 = locked
   - 维修中 = fix
4. 本期免费，不实现支付、押金、代他人预约、双人/多座预约。
5. 学生端不得显示编辑入口；管理端高风险操作必须二次确认；系统管理员在当前权限矩阵下只读。

二、视觉令牌
在 frontend/src/styles/seat-experience.scss 中定义，作用域 .seat-experience，不要覆盖 :root 的全站品牌色。
浅色：
--paper:#F3EFE5; --surface:#FFFCF5; --surface-2:#FAF6EC;
--ink:#1F241F; --ink-2:#555D53; --ink-3:#6B7268;
--line:#DFD8C8; --line-strong:#C4BAA7;
--brand:#0E7164; --brand-hover:#0A5C52; --brand-soft:#DDEEE8; --brand-wash:#EDF5F1;
--amber:#A8610A; --amber-ink:#7A4504; --amber-soft:#FBF0D9;
--danger:#B93A2B; --danger-ink:#8E2A1F; --danger-soft:#F9E6E1;
--slate:#5F665D; --slate-soft:#ECE9DF;
--focus:#0E7164; --brand-halo:rgba(14,113,100,.22);
桌子木材：#E8D4AD / #D8BB88 / #AD8959 / #A8854F；
字体：
--font-display: 'Fraunces','Noto Serif SC','Songti SC',serif;
--font-ui: 'Noto Sans SC','HarmonyOS Sans SC','PingFang SC','Microsoft YaHei',sans-serif;
--font-mono: 'IBM Plex Mono','SFMono-Regular',Consolas,monospace;
座位状态（背景 / 描边 / 文字）：
free #E7F3EE / #0E7164 / #0A5C52，实线，无图标
taken #F2EDE2 / #B49A70 / #6E5B3E，虚线 + 时钟（降饱和，不抢视觉）
mine #F5C86A / #8C5A00 / #3F2A00，双线 + 勾
held #E7E1D3 / #8B7B5F / #5E5138，实线 + 斜纹 + 沙漏
locked #EAE7DE / #6B7069 / #4A514A，点线 + 锁
fix #F7E4DF / #B93A2B / #8E2A1F，实线 + 斜纹 + 扳手
要求：每个状态至少同时有颜色、边框线型、图标、可见文本/图例；不允许只靠颜色。

三、类型
新建 frontend/src/types/seat-map.ts，定义：
- RoomLayout { roomId; width; height; grid; version; updatedAt }
- TableLayout { tableId; areaId; label; shape:'rect'|'capsule'|'round'; x; y; w; h; rotation; zIndex; seatIds:number[] }
- SeatLayout { seatId; tableId; x; y; w; h; rotation; orientation:'n'|'s'|'e'|'w' }
- Area { id; roomId; name; en; x; y; w; h; tone }
- TableView extends TableLayout { area; seats: SeatView[] }
- SeatView extends Seat { layout; table; area; slotState; price:0; tags:string[] }
- TimeRange { start:string; end:string }
- Viewport { x;y;z }
- BookingIntent { roomId; seatId; date; range; idempotencyKey }
- ConflictResponse { code; message; serverTime; conflictSeatIds; alternatives?; canChangeTime }
- LayoutPayload / LayoutSaveResult（tables + seats + version）
不要使用 any；确实需要时写明理由。

四、地图组件（Table / Seat 分离）
实现：
- components/seat-map/RoomShell.vue：墙、窗带、门、前台、主通道、比例尺。SVG，pointer-events:none。
- components/seat-map/AreaLabel.vue：区域名 + 英文，低倍率隐藏英文。
- components/seat-map/TableFurniture.vue：桌椅中的“桌子”，div（不可点，不渲染 button）。杉木色桌面 + 1px 深木描边 + 向下 4px 挤出阴影；桌心显示桌号（W1/C2/PWR/Q1）、属性图标、座数。hover 加 is-hover；编辑模式可整桌拖拽。
- components/seat-map/SeatItem.vue：桌椅中的“椅子”，真实 <button>，aria-label / aria-pressed。半圆托件 + 坐垫，靠背在远离桌面的方向，开口朝向桌面；座号显示在椅面；状态只作用在坐垫（颜色 + 线型 + 图标 + 图例）；hover 只抬升该椅；选中时椅子双环 + 勾，并且对应桌子加 is-table-selected（描边点亮 + 柔和外发光）。
- components/seat-map/SeatMapCanvas.vue：
  - props: room, areas, tables, seats, selection, hoveredId, hoveredTableId, mode('student'|'admin'|'editor'), viewport, readOnly
  - emits: select, hover, table-hover, viewport-change, seat-drag, table-drag, seat-resize
  - 28 椅 / 10 桌用 DOM；>300 椅预留 CanvasRenderer 接口。
  - 地图容器 touch-action:none；滚轮/双指缩放；单指/鼠标拖拽；按钮缩放；fit/reset。
  - 点击语义：椅子选中；桌子不选中（学生端点击桌子只平移地图）；hover 桌子整桌轻亮，hover 椅子只亮该椅。
- components/seat-map/MapToolbar.vue：放大/缩小/适配/复位/列表切换；aria-label。
- components/seat-map/LegendPanel.vue：details/summary 可折叠；summary 常驻迷你三色点（空闲 / 已约 / 我的）+ 完整六态；完整项包含色块、线型、图标。
- components/seat-map/SeatListFallback.vue：按区域 + 桌号分组，虚拟列表接口预留；与地图同源状态，键盘可用。

五、地图交互规格
- transform: translate(x,y) scale(z)，transform-origin:0 0；z ∈ [0.5,2.5]。
- 焦点缩放：
  wx=(px-tx)/z; wy=(py-ty)/z; z'=clamp(z*factor); tx'=px-wx*z'; ty'=py-wy*z'
- 滚轮 factor=exp(-deltaY*0.0016)，以光标为焦点，preventDefault。
- 双指：记录起始距离/中点/世界坐标；按距离比缩放，保持中点不动。
- 平移边界：内容大于视口时至少保留 min(120px,26%) 可见；内容小于视口时居中。
- 标签：椅子字号 clamp(8, 10/z, 18)，桌子字号 clamp(7, 9/z, 16)（均为房间单位）；z<0.62 隐藏桌型 / 座数 / 类型图标与旗标，椅号显示末两位；0.62–1.12 显示完整椅号 + 桌号 + 座数；>1.12 显示全部。
- 键盘：地图方向键平移；座位方向键空间导航；Enter/Space 选择；+/- 缩放；0 复位；F 适配；Esc 关闭浮层。
- 点击阈值 4px，拖拽超过阈值不触发选择。

六、状态与请求
不要把流程写在组件里；新建 composables：
- useSeatMapViewport.ts：x/y/z、fit、reset、zoomAt、pan、clamp、键盘、双指。
- useSeatLayout.ts：布局加载、草稿、脏状态、保存/发布、版本冲突。
- useSeatSelection.ts：selectedSeatId、hoveredId、筛选、derived summary。
保留现有 useSeatBooking 作为学生业务数据源；不要复制它的规则校验。

七、质量
- 所有按钮有 type="button"。
- 焦点可见；Sheet 有焦点陷阱；aria-live 宣告状态变化。
- 支持 prefers-reduced-motion / prefers-contrast。
- 颜色不硬编码在组件里，只引用 CSS 变量。
- 输出代码必须能通过 vue-tsc --noEmit。

先只输出共享层文件与改动说明；不要一次性重写页面。
```

---

## Prompt 2：学生端「预约座位」页面

```text
在已完成的共享层基础上，重写 frontend/src/views/student/SeatBookingView.vue，并新增：
- components/booking/DateRail.vue
- components/booking/TimeRail.vue
- components/booking/BookingSummary.vue
- components/booking/MobileActionBar.vue
- components/booking/ReservationSheet.vue
- components/booking/ConflictSheet.vue
- components/booking/SuccessSheet.vue

一、结构
桌面（≥1280）：
页头（房间卡片 + 规则）→ 日期带 → 时间带 → 筛选/地图|列表 → 三栏（规则 rail / 地图 / 摘要）。
移动（<920）：
页头 → 日期 → 时间 → 筛选 → 地图 → 固定底部摘要栏；点击「确认预约」打开底部 Sheet。
地图是主视图，列表是兜底；不要用传统表单式座位网格替代地图。

二、日期 / 时间
- 日期 7 天，今天起；过去日期禁用；显示余位。
- 时间 08:00–22:00，5 分钟格、30 分钟主刻度；每小时细刻度 + 08/10/12… 小时标签；今天且当前时刻在开放区间时显示琥珀「现在」指针。
- 点击起点再点终点；支持拖动；拖动时跟随指针显示范围 + 时长 tooltip；结束时间对齐 5 分钟；最长 4 小时，超出自动收敛并 toast；开始/结束同一格时自动 +5 分钟；今天已开始时段可以进入只读查看，地图保留，提交由 C6 拦截。
- 显示范围、时长、空位数、免费；不可用时段置灰。
- 改日期/时间后保留已选座位；如果已选座位在新时段不可用，保留选择但禁用提交并解释，不静默清空。
- 规则不再占用左侧整栏：收进工具栏「规则」按钮 / Sheet，把横向空间还给地图。

三、座位与摘要
- 点击空闲**椅子** → 摘要显示座号、桌号、区域、日期、时段、时长、状态、免费；不直接弹提交框。点击桌子不选中。
- 点击「确认预约」→ ReservationSheet；摘要数据与地图选择同源。
- 点击他人的已约 / 维修 / 锁定 / 保留：显示原因与「附近空位」，不选中为可提交。
- 点击「我的预约」：显示「这是你的预约」+ 查看我的预约，不允许重复预约。
- 筛选只淡化不匹配椅子，不重排地图；清除筛选后恢复。
- 图例 summary 常驻迷你三态点；展开显示六态完整图例。
- 免费，不显示支付入口。

四、提交与冲突
- 提交按钮点击后立即 disabled + spinner；同一 BookingIntent 复用幂等键；重复点击不产生多笔。
- 成功：显示预约号、座位、日期、时段、签到窗口（开始前 15 分钟至开始后 15 分钟）；主按钮「查看我的预约」，次按钮「继续选座」。
- 409 SEAT_TAKEN：标题「座位刚被抢占」；正文「该座位已被抢占。请换座或改时间。你的日期和时段已保留。」；列出同区域优先的 3 个空位；不自动改选。
- 每日上限 / 账号受限 / 规则失败：摘要内联错误 + 解释 + 修改入口。
- 成功后不要整页重新拉 available-seats（会把本人冲突算进去导致空表）；只把该座位局部标为 mine。

五、移动端
- 摘要不占右栏；底部固定摘要栏，点击座位信息打开半屏摘要抽屉（sheet--summary，max-height 58vh），内容含桌号 / 时间 / 免费 / 「查看详情并确认」。
- 地图保持全屏手势；底部栏不阻挡地图控制。
- 图例缩为迷你态，不遮挡地图。

六、异步状态
- 首屏：地图轮廓骨架 +「正在读取座位与时段占用…」；不要整页 spinner。
- 地图失败：错误卡 +「重新加载」「切换到列表」；保留日期/时段/筛选；数据未同步时禁止提交。
- 筛选无结果：地图保留淡化 +「没有符合筛选的座位」+「清除筛选」。
- 时段已满：地图可见但全部占用 +「看下一个时段」/「查看列表」。
- 空房间：房间轮廓 +「这间自习室还没有录入座位」+ 管理员入口；不显示「可约 0」冒充正常。
- 401 / 登录过期：跳登录并保留 returnUrl。

七、无障碍
- 地图区域 aria-label；每把椅子 aria-label 含座号/桌号/区域/类型/状态/操作；状态变化用 aria-live=polite。
- 键盘：Tab 到座位，方向键空间移动，Enter/Space 选择，Esc 关闭 Sheet。
- Sheet 焦点陷阱；关闭后焦点回到触发按钮。
- 正文对比度 4.5:1；图形 3:1；200% zoom 不丢功能；支持 reduced-motion。
- 颜色之外必须有图标/线型/文本。

八、API 适配
- 优先复用现有 useSeatBooking 的取数/规则/幂等逻辑。
- 若缺少「全部桌子 + 椅子 + 占用」接口，先定义 api 层函数与类型，使用 MSW mock 返回完整 10 桌 / 28 椅地图；不要用 available-seats 伪造占用。
- 不要修改现有 API path/字段而不评估兼容性；新增接口时同步 MSW 与类型。

九、验收
- 10 桌 / 28 椅完整可见；椅子围绕桌边；点击椅子才选中；缩放 0.5–2.5；适配/复位可用；六态灰度可辨。
- 选座 → 摘要 → 提交 → 成功闭环；冲突可恢复；重复提交只 1 笔。
- 390px 可用；键盘可完成选座；列表与地图同源。
- npm run type-check / npm run build 通过。
```

---

## Prompt 3：管理端「座位运营台」页面

```text
在共享层与学生端完成后，重写 frontend/src/views/admin/SeatManageView.vue，并新增：
- components/admin/AdminKpiStrip.vue
- components/admin/AdminToolRail.vue
- components/admin/AdminInspector.vue
- components/admin/AdminLayoutEditor.vue
- components/admin/ImpactConfirmDialog.vue
- components/admin/LayoutImportDialog.vue
- components/admin/ConflictQueuePanel.vue
- components/admin/OperationLogPanel.vue

一、结构
页头：房间选择、权限角色、实时同步时间、刷新。
KPI：上座率、当前空闲、占用中、需关注、冲突队列。
Tabs：占用监控 / 布局编辑 / 运营与日志。
三栏：工具 rail / 地图 / 检查器；<1080 时检查器下移。
地图与学生端同一坐标与渲染器；编辑模式打开网格、吸附、对齐线。

二、监控
- 10 秒轮询；显示最后同步；页面隐藏暂停；30 秒未同步显示过期提示；保留当前选择。
- 点击座位 → 单座检查器：资源状态、时段占用、预约摘要、锁定/维修/停用/恢复。
- Shift 点击多选 → 批量检查器：批量锁定/维修/停用/清空。
- 「一键锁定整区」：按当前选择区域或默认区域，展示影响座位数 + 预约数，原因必填，二次确认。
- 冲突订单：列出座位、时段、脱敏用户、原因；处理动作写入日志；不显示手机号/邮箱原值。
- 超时释放：显示倒计时与「立即释放」；释放由服务端执行，前端只展示结果。
- 高风险动作统一：影响清单 → 原因 → 二次确认 → 日志；不得自动取消预约。

三、布局编辑
- 工具：选择、新增、旋转、删除、撤销、重做、保存、导入。
- 拖拽移动：拖桌子时桌子与同 tableId 的椅子一起移动；拖单椅只移动该椅；10px 吸附；靠近其他对象显示水平/垂直对齐线；按住 Alt 临时关闭吸附。
- 旋转：15° 步进；缩放：W/H 输入或拖拽手柄（本 PR 至少实现输入）；检查器显示所属桌号与桌型。
- 多选：Shift 点击；复制/粘贴/删除；撤销/重做 50 步。
- 保存草稿 / 发布版本；发布二次确认。
- 版本冲突：409 时显示「布局已被其他管理员修改」，保留本地未保存状态，提供刷新差异/重试；禁止直接覆盖。
- 导入 JSON/CSV：dry-run 先校验重复编号、越界、未知区域、缺字段；逐行错误；正式导入原子化。
- 未保存离开页面 beforeunload 确认。
- 系统管理员只读：横幅、按钮禁用、不能拖拽；服务端仍校验。

四、运营与日志
- 操作日志：时间、操作者、动作、座位、原因、影响预约、结果；只读、可筛选。
- 权限矩阵：学生无编辑入口；自习室管理员可操作；系统管理员只读。
- 不实现导出（当前范围排除）。

五、无障碍与质量
- 工具栏按钮 aria-label；地图键盘可用；检查器表单 label 关联。
- 颜色之外状态有图标/线型；对比度达标。
- API 适配：复用现有 /seats/occupancy、/seats/status、/seats/conflicts；布局接口新增时同步类型/MSW/错误处理。
- npm run type-check / npm run build 通过。
```

---

## 给 AI 的额外约束（可附在任意 Prompt 后）

```text
- 不要复制任何第三方品牌的 Logo、图标、插画、配色方案或文案。只借鉴信息架构与交互模式。
- 不要用 @ts-ignore 或 any 绕过类型问题；不要删除已有功能；不要改后端业务规则。
- 不要用浏览器原生 alert/confirm；使用项目现有 ElMessage / ElMessageBox 或自建 Confirm 组件。
- 不要为了「看起来高级」加入无意义的渐变、玻璃拟态、发光、3D 翻转或游戏化动效。
- 不要把状态只做成颜色；至少同时提供图标、线型或文字。
- 不要在没有接口时把 Mock 冒充真实实现；明确标注 mock 与 TODO。
- 输出前运行 type-check/build，并在说明中记录实际命令与结果。
```

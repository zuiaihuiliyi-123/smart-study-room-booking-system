"""Service 层统一约定。

- **查询方法**（list/get/count）只读，不 commit、不 rollback；
- **命令方法**（create/update/cancel/…）自己拥有且只拥有一个事务，
  推荐使用 `app.core.transactions.transaction(db)` 包住全部写操作；
- 事务提交后再发站内通知（`notification_service.notify_safe` 使用独立会话）；
- API 层只负责参数校验与依赖注入，不自行开启业务事务。

`reservation_query_service` / `reservation_command_service` 是拆分后的示例；
`reservation_service` 保留兼容门面，保证既有调用方接口不变。
"""


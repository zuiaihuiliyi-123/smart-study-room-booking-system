/**
 * NFR-006 个人信息脱敏。
 *
 * 依据（需求规格说明书第 6.1 节 NFR-006 验收标准）：
 * 「Given 管理员查询用户列表、When 查看结果、Then 手机号与邮箱以掩码呈现」。
 *
 * 边界说明：脱敏**只在界面层**发生，接口仍返回原值；本文件不写入任何数据，
 * 也不做不可逆哈希（管理员在必要时需要看到原值，属后端授权范围，本版不做展示入口）。
 */

const HIDDEN = '—'

function isBlank(value: string | null | undefined): boolean {
  return (value ?? '').trim() === ''
}

/** 通用短串掩码：保留首尾各 1～2 位，中间用 `***` 代替。 */
function maskGeneric(text: string): string {
  if (text.length <= 2) return '*'.repeat(text.length)
  if (text.length <= 5) return `${text.slice(0, 1)}***${text.slice(-1)}`
  return `${text.slice(0, 2)}***${text.slice(-2)}`
}

/**
 * 手机号 / 工号类数字串：保留前 3 位与后 4 位（`13800001234` → `138****1234`）。
 * 位数不足以保留时退回通用掩码，不猜测号段。
 */
export function maskPhone(value: string | null | undefined): string {
  if (isBlank(value)) return HIDDEN
  const text = (value ?? '').replace(/\s+/g, '')
  if (/^\d{7,}$/.test(text)) {
    return `${text.slice(0, 3)}****${text.slice(-4)}`
  }
  return maskGeneric(text)
}

/** 邮箱：保留首字母与完整域名（`student@zju.edu.cn` → `s******@zju.edu.cn`）。 */
export function maskEmail(value: string | null | undefined): string {
  if (isBlank(value)) return HIDDEN
  const text = (value ?? '').trim()
  const at = text.lastIndexOf('@')
  if (at <= 0) return maskGeneric(text)
  const local = text.slice(0, at)
  const domain = text.slice(at)
  const head = local.slice(0, 1)
  const stars = '*'.repeat(Math.max(3, local.length - 1))
  return `${head}${stars}${domain}`
}

/** 联系方式（手机号或邮箱，FR-040 中用户唯一可自改的字段）：按形态选择掩码方式。 */
export function maskContact(value: string | null | undefined): string {
  if (isBlank(value)) return HIDDEN
  const text = (value ?? '').trim()
  if (text.includes('@')) return maskEmail(text)
  if (/^[\d\s-]+$/.test(text)) return maskPhone(text)
  return maskGeneric(text)
}

/** 联系方式形态说明：用于列头 tooltip，向使用者说明「看到的是掩码而非原值」。 */
export function contactKindLabel(value: string | null | undefined): string {
  if (isBlank(value)) return '未填写'
  return (value ?? '').includes('@') ? '邮箱' : '手机号'
}

import dayjs from 'dayjs'

export function formatDateTime(value?: string | null): string {
  return value ? dayjs(value).format('YYYY-MM-DD HH:mm') : '-'
}

export function formatDate(value?: string | null): string {
  return value ? dayjs(value).format('YYYY-MM-DD') : '-'
}

export function reservationStatusType(
  status: string,
): 'success' | 'info' | 'warning' | 'danger' | 'primary' {
  const map: Record<string, 'success' | 'info' | 'warning' | 'danger' | 'primary'> = {
    待使用: 'primary',
    使用中: 'success',
    已完成: 'info',
    已取消: 'warning',
    已违约: 'danger',
  }
  return map[status] ?? 'info'
}

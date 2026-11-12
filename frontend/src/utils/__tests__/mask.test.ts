import { describe, expect, it } from 'vitest'

import { contactKindLabel, maskContact, maskEmail, maskPhone } from '@/utils/mask'

describe('maskPhone', () => {
  it('保留前 3 位与后 4 位', () => {
    expect(maskPhone('13800001234')).toBe('138****1234')
    expect(maskPhone('138 0000 1234')).toBe('138****1234')
  })

  it('位数不足时退回通用掩码', () => {
    expect(maskPhone('123456')).toBe('12***56')
    expect(maskPhone('42')).toBe('**')
  })

  it('空值返回占位符', () => {
    expect(maskPhone('')).toBe('—')
    expect(maskPhone(null)).toBe('—')
  })
})

describe('maskEmail', () => {
  it('保留首字母与完整域名', () => {
    expect(maskEmail('student@zju.edu.cn')).toBe('s******@zju.edu.cn')
    expect(maskEmail('ab@x.cn')).toBe('a***@x.cn')
  })

  it('非邮箱结构退回通用掩码', () => {
    expect(maskEmail('wechat:abc')).toBe('we***bc')
    expect(maskEmail(undefined)).toBe('—')
  })
})

describe('maskContact / contactKindLabel', () => {
  it('按手机号或邮箱自动选择掩码', () => {
    expect(maskContact('13800001234')).toBe('138****1234')
    expect(maskContact('student@zju.edu.cn')).toBe('s******@zju.edu.cn')
    expect(maskContact('other-contact')).toBe('ot***ct')
    expect(maskContact(null)).toBe('—')
  })

  it('识别联系方式形态', () => {
    expect(contactKindLabel('13800001234')).toBe('手机号')
    expect(contactKindLabel('student@zju.edu.cn')).toBe('邮箱')
    expect(contactKindLabel('')).toBe('未填写')
  })
})

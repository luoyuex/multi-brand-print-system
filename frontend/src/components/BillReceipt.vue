<template>
  <!-- 外卖小票风格对账单：固定窄幅 420px，供 html2canvas 截图成 PNG。
       排版对齐原后端模板 bill.html，数据直接取自 bill 对象。 -->
  <div class="receipt">
    <div class="title">对账单</div>
    <div class="subtitle">STATEMENT</div>
    <hr class="divider" />

    <div class="meta">
      <div class="row"><span class="label">客户</span><span class="val">{{ bill.customer }}</span></div>
      <div class="row"><span class="label">账期</span><span class="val">{{ periodText }}</span></div>
      <div class="row"><span class="label">单号</span><span class="val"><template v-if="bill.id">#{{ bill.id }}　</template>共 {{ bill.order_count }} 单</span></div>
    </div>

    <hr class="divider" />

    <div v-for="day in days" :key="day.key" class="day">
      <div class="day-head">
        <span>{{ singleDay ? '商品明细' : `${day.dateStr} 周${day.weekday}` }}</span>
        <span class="cnt">{{ day.items.length }} 项</span>
      </div>
      <table>
        <tr v-for="(item, i) in day.items" :key="i" class="item">
          <td class="name">
            {{ item.product_name }}<span v-if="item.spec" class="spec">{{ item.spec }}</span><span v-if="item.is_replacement" class="tag-rep">补</span>
          </td>
          <td class="calc">
            <template v-if="item.is_replacement">补发</template>
            <template v-else>{{ fmtQty(item.qty) }} × {{ money(item.price) }}</template>
          </td>
          <td class="sub" :class="{ 'rep-sub': item.is_replacement }">
            {{ item.is_replacement ? '0' : money(item.subtotal) }}
          </td>
        </tr>
      </table>
      <div v-if="!singleDay" class="day-sub">当日小计 <b>¥{{ money(day.subtotal) }}</b></div>
    </div>

    <div class="total">
      <span class="lab">合计金额</span>
      <span class="amt">¥{{ money(bill.total_amount) }}</span>
    </div>

    <div class="footer">
      水果质量问题24小时内包赔<br />
      出账时间 {{ generatedAt }}
      <div v-if="bill.paid"><span class="stamp paid">已收款</span></div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  bill: { type: Object, required: true },
})

const WEEK = ['日', '一', '二', '三', '四', '五', '六']

function money(v) {
  return Number(v || 0).toFixed(2)
}
function fmtQty(v) {
  const f = Number(v || 0)
  return Number.isInteger(f) ? String(f) : String(Number(f.toFixed(2)))
}

const singleDay = computed(() => props.bill.period_start === props.bill.period_end)

const periodText = computed(() =>
  singleDay.value
    ? props.bill.period_start
    : `${props.bill.period_start} ~ ${props.bill.period_end}`
)

// 出账时间：created_at 转「YYYY-MM-DD HH:mm」
const generatedAt = computed(() => {
  const raw = props.bill.created_at
  if (!raw) return ''
  const d = new Date(raw)
  if (Number.isNaN(d.getTime())) return String(raw).slice(0, 16).replace('T', ' ')
  const p = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`
})

// 按 order_date 分组（items 落库时已按订单时间有序），算出日期串、周几、当日小计
const days = computed(() => {
  const map = new Map()
  for (const it of props.bill.items || []) {
    const key = it.order_date || '-'
    if (!map.has(key)) map.set(key, { key, date: it.order_date, items: [], subtotal: 0 })
    const g = map.get(key)
    g.items.push(it)
    g.subtotal += it.is_replacement ? 0 : Number(it.subtotal || 0)
  }
  return [...map.values()].map((g) => {
    let dateStr = ''
    let weekday = ''
    if (g.date) {
      const d = new Date(g.date)
      if (!Number.isNaN(d.getTime())) {
        const p = (n) => String(n).padStart(2, '0')
        dateStr = `${p(d.getMonth() + 1)}-${p(d.getDate())}`
        weekday = WEEK[d.getDay()]
      }
    }
    return { ...g, dateStr, weekday }
  })
})
</script>

<style scoped>
/* 与原 bill.html 排版一致 */
.receipt {
  width: 420px;
  background: #fff;
  font-family: "Microsoft YaHei", "微软雅黑", "PingFang SC", sans-serif;
  color: #1a1a1a;
  padding: 22px 24px 26px;
  box-sizing: border-box;
}
.receipt * { box-sizing: border-box; margin: 0; padding: 0; }

.title { text-align: center; font-size: 22px; font-weight: 800; letter-spacing: 2px; }
.subtitle { text-align: center; font-size: 12px; color: #999; margin-top: 4px; letter-spacing: 2px; }

.divider { border: 0; border-top: 1.5px dashed #c4c4c4; margin: 14px 0; }

.meta { font-size: 14px; line-height: 1.9; }
.meta .row { display: flex; }
.meta .label { color: #999; width: 46px; flex-shrink: 0; }
.meta .val { font-weight: 600; flex: 1; }

.day { margin-top: 8px; }
.day-head {
  display: flex; align-items: center; justify-content: space-between;
  font-size: 14px; font-weight: 700; color: #333;
  background: #f4f6f8; border-radius: 6px; padding: 5px 10px; margin-bottom: 4px;
}
.day-head .cnt { font-size: 12px; color: #aaa; font-weight: 500; }

table { width: 100%; border-collapse: collapse; }
.item td { padding: 4px 0; font-size: 13.5px; vertical-align: top; line-height: 1.35; }
.item .name { width: 100%; }
.item .name .spec { color: #999; font-size: 12px; margin-left: 4px; }
.item .calc { white-space: nowrap; color: #888; text-align: right; padding: 0 10px; font-size: 12.5px; }
.item .sub { white-space: nowrap; text-align: right; font-weight: 600; min-width: 60px; }
.tag-rep { font-size: 10px; border: 0.5px solid #e6a23c; color: #e6a23c; border-radius: 3px; padding: 0 3px; margin-left: 4px; }
.rep-sub { color: #e6a23c; }

.day-sub { text-align: right; font-size: 12.5px; color: #999; padding: 3px 0 2px; }
.day-sub b { color: #555; }

.total {
  display: flex; align-items: baseline; justify-content: space-between;
  margin-top: 8px; padding-top: 12px; border-top: 2px solid #333;
}
.total .lab { font-size: 15px; font-weight: 700; }
.total .amt { font-size: 26px; font-weight: 800; color: #c0392b; }

.footer { margin-top: 18px; text-align: center; font-size: 12px; color: #aaa; line-height: 1.8; }
.stamp {
  display: inline-block; margin-top: 10px; padding: 4px 16px; border-radius: 6px;
  font-size: 14px; font-weight: 800; letter-spacing: 3px;
}
.stamp.paid   { color: #2e7d32; border: 2px solid #2e7d32; }
.stamp.unpaid { color: #c0392b; border: 2px solid #c0392b; }
</style>

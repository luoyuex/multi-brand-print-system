<template>
  <div class="page-wrap">
    <el-card class="section-card">
      <template #header>
        <div class="card-header">
          <span class="card-title">对账单</span>
          <div class="header-tools">
            <el-input
              v-model="keyword"
              placeholder="客户名"
              size="small"
              clearable
              class="kw-input"
              @keyup.enter="loadBills"
              @clear="loadBills"
            />
            <el-date-picker
              v-model="startDate" type="date" placeholder="账期起"
              value-format="YYYY-MM-DD" size="small" class="date-input" @change="loadBills"
            />
            <span class="date-sep">至</span>
            <el-date-picker
              v-model="endDate" type="date" placeholder="账期止"
              value-format="YYYY-MM-DD" size="small" class="date-input" @change="loadBills"
            />
            <el-select v-model="sentFilter" size="small" class="status-select" @change="loadBills">
              <el-option label="发送:全部" value="" />
              <el-option label="已发送" value="true" />
              <el-option label="未发送" value="false" />
            </el-select>
            <el-select v-model="paidFilter" size="small" class="status-select" @change="loadBills">
              <el-option label="回款:全部" value="" />
              <el-option label="已回款" value="true" />
              <el-option label="未回款" value="false" />
            </el-select>
            <el-button size="small" :loading="loading" @click="loadBills">刷新</el-button>
            <el-button size="small" type="primary" @click="openGenerate">＋ 生成账单</el-button>
            <el-button size="small" type="success" :loading="genTodayLoading" @click="handleGenerateToday">
              一键生成今日
            </el-button>
          </div>
        </div>
      </template>

      <!-- 汇总条 -->
      <div v-if="bills.length" class="summary-bar">
        <span>共 {{ bills.length }} 张</span>
        <span class="unpaid">未回款 ¥{{ unpaidTotal }}（{{ unpaidCount }} 张）</span>
      </div>

      <el-empty v-if="!loading && bills.length === 0" description="暂无账单" :image-size="80" />

      <div v-for="bill in bills" :key="bill.id" class="bill-item">
        <!-- 标题行 -->
        <div class="bill-header" @click="toggleExpand(bill.id)">
          <div class="bill-meta">
            <span class="bill-id">#{{ bill.id }}</span>
            <span class="bill-cust">{{ bill.customer }}</span>
            <span class="bill-period">{{ periodText(bill) }}</span>
            <span class="bill-count">{{ bill.order_count }} 单</span>
            <span class="bill-amt">¥{{ money(bill.total_amount) }}</span>
          </div>
          <div class="bill-actions" @click.stop>
            <el-tag :type="bill.sent ? 'success' : 'info'" size="small" effect="plain" class="st-tag">
              {{ bill.sent ? '已发送' : '未发送' }}
            </el-tag>
            <el-tag :type="bill.paid ? 'success' : 'danger'" size="small" :effect="bill.paid ? 'dark' : 'light'" class="st-tag">
              {{ bill.paid ? '已回款' : '未回款' }}
            </el-tag>
            <el-button size="small" type="primary" plain @click="openImage(bill)">🧾 小票</el-button>
            <el-button size="small" plain @click="openEdit(bill)">✏️ 编辑</el-button>
            <el-button size="small" type="success" plain :loading="copyingId === bill.id" @click="copyBillImage(bill)">📋 复制</el-button>
            <el-button size="small" :type="bill.sent ? 'info' : 'warning'" plain :loading="sentBusy === bill.id" @click="toggleSent(bill)">
              {{ bill.sent ? '取消发送' : '标记已发送' }}
            </el-button>
            <el-button size="small" :type="bill.paid ? 'info' : 'success'" plain :loading="paidBusy === bill.id" @click="togglePaid(bill)">
              {{ bill.paid ? '取消回款' : '标记已回款' }}
            </el-button>
            <el-button size="small" type="danger" plain :loading="deletingId === bill.id" @click="handleDelete(bill)">删除</el-button>
          </div>
        </div>

        <!-- 展开明细（按天分组） -->
        <div v-show="expandedIds.has(bill.id)" class="bill-body">
          <div v-for="day in groupByDay(bill.items)" :key="day.date" class="day-block">
            <div v-if="!isSingleDay(bill)" class="day-title">{{ day.date }}</div>
            <table class="items-table">
              <tbody>
                <tr v-for="(it, i) in day.items" :key="i">
                  <td class="it-name">
                    {{ it.product_name }}
                    <el-tag v-if="it.is_replacement" type="warning" size="small" effect="dark" class="rep-tag">补</el-tag>
                  </td>
                  <td class="it-spec">{{ it.spec || '—' }}</td>
                  <td class="it-calc">
                    <template v-if="it.is_replacement">补发</template>
                    <template v-else>{{ fmtQty(it.qty) }} × {{ money(it.price) }}</template>
                  </td>
                  <td class="it-sub">¥{{ money(it.subtotal) }}</td>
                </tr>
              </tbody>
            </table>
            <div v-if="!isSingleDay(bill)" class="day-subtotal">当日小计 ¥{{ money(day.subtotal) }}</div>
          </div>
          <div class="bill-total-row">合计 <b>¥{{ money(bill.total_amount) }}</b></div>
          <div v-if="bill.note" class="bill-note">备注：{{ bill.note }}</div>
        </div>
      </div>
    </el-card>

    <!-- 生成 / 编辑账单弹窗 -->
    <el-dialog v-model="genVisible" :title="editId ? `编辑账单 #${editId}` : '生成账单'" width="560px">
      <div class="gen-form">
        <div class="gen-row">
          <span class="gen-label">客户</span>
          <el-select v-model="genStoreId" placeholder="选择客户（店铺）" filterable style="flex:1;" :disabled="!!editId" @change="doPreview">
            <el-option v-for="s in stores" :key="s.id" :value="s.id" :label="s.name">
              <span>{{ s.name }}</span>
              <span v-if="s.contact" style="float:right;color:#999;font-size:12px;">{{ s.contact }}</span>
            </el-option>
          </el-select>
        </div>
        <div v-if="editId" class="gen-tip">编辑账单只能改账期和备注；改账期会按新账期重新汇总该客户的订单。</div>
        <div class="gen-row">
          <span class="gen-label">账期</span>
          <el-date-picker v-model="genStart" type="date" placeholder="起" value-format="YYYY-MM-DD" style="flex:1;min-width:0;" @change="doPreview" />
          <span class="date-sep">至</span>
          <el-date-picker v-model="genEnd" type="date" placeholder="止" value-format="YYYY-MM-DD" style="flex:1;min-width:0;" @change="doPreview" />
        </div>
        <div class="gen-row">
          <span class="gen-label">备注</span>
          <el-input v-model="genNote" placeholder="可选，会显示在账单上" style="flex:1;" />
        </div>

        <div class="preview-panel" v-loading="previewLoading">
          <template v-if="preview && preview.order_count > 0">
            <div class="preview-head">
              <span>{{ preview.customer }}</span>
              <span class="preview-total">{{ preview.order_count }} 单 · 合计 ¥{{ money(preview.total) }}</span>
            </div>
            <div v-for="day in preview.days" :key="day.date" class="pv-day">
              <div class="pv-day-title">{{ day.date }}（¥{{ money(day.subtotal) }}）</div>
              <div v-for="(it, i) in day.items" :key="i" class="pv-line">
                <span class="pv-name">{{ it.product_name }} <span class="pv-spec">{{ it.spec }}</span></span>
                <span class="pv-calc">
                  <template v-if="it.is_replacement">补发</template>
                  <template v-else>{{ fmtQty(it.qty) }} × {{ money(it.price) }} = ¥{{ money(it.subtotal) }}</template>
                </span>
              </div>
            </div>
          </template>
          <el-empty v-else :image-size="60" description="该客户在所选账期内没有未出账的订单" />
        </div>
      </div>
      <template #footer>
        <el-button @click="genVisible = false">取消</el-button>
        <el-button type="primary" :loading="creating" :disabled="!preview || preview.order_count === 0" @click="handleSubmit">
          {{ editId ? '保存修改' : '确认生成' }}
        </el-button>
      </template>
    </el-dialog>

    <!-- 小票预览弹窗 -->
    <el-dialog v-model="imgVisible" title="账单小票" width="480px" class="img-dialog">
      <div class="img-wrap">
        <img v-if="imgBill" :src="billApi.imageUrl(imgBill.id, imgTs)" alt="账单小票" class="bill-img" />
      </div>
      <template #footer>
        <el-button @click="imgVisible = false">关闭</el-button>
        <el-button @click="downloadBillImage(imgBill)">下载图片</el-button>
        <el-button type="primary" :loading="copyingId === (imgBill && imgBill.id)" @click="copyBillImage(imgBill)">📋 复制图片</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { billApi, storeApi } from '../api'

function todayStr() {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

// ── 列表 & 筛选 ──
const bills       = ref([])
const keyword     = ref('')
const startDate   = ref(todayStr())   // 默认当天，与打印列表一致
const endDate     = ref(todayStr())
const sentFilter  = ref('')   // '' | 'true' | 'false'
const paidFilter  = ref('')
const loading     = ref(false)

const expandedIds   = ref(new Set())
const deletingId    = ref(null)
const sentBusy      = ref(null)
const paidBusy      = ref(null)
const genTodayLoading = ref(false)

// ── 生成 / 编辑弹窗 ──
const genVisible     = ref(false)
const editId         = ref(null)   // null=生成模式；非空=编辑该账单（改账期/备注）
const stores         = ref([])
const genStoreId     = ref(null)
const genStart       = ref('')
const genEnd         = ref('')
const genNote        = ref('')
const preview        = ref(null)
const previewLoading = ref(false)
const creating       = ref(false)

// ── 小票弹窗 ──
const imgVisible = ref(false)
const imgBill    = ref(null)
const imgTs      = ref(0)
const copyingId  = ref(null)   // 正在复制图片的账单 id（卡片/弹窗共用）

const unpaidCount = computed(() => bills.value.filter((b) => !b.paid).length)
const unpaidTotal = computed(() =>
  money(bills.value.filter((b) => !b.paid).reduce((s, b) => s + Number(b.total_amount || 0), 0))
)

function money(v) {
  const f = Number(v || 0)
  return Number.isInteger(f) ? String(f) : f.toFixed(2)
}
function fmtQty(v) {
  const f = Number(v || 0)
  return Number.isInteger(f) ? String(f) : String(Number(f.toFixed(2)))
}
function periodText(bill) {
  return bill.period_start === bill.period_end
    ? bill.period_start
    : `${bill.period_start} ~ ${bill.period_end}`
}
function isSingleDay(bill) {
  return bill.period_start === bill.period_end
}
function groupByDay(items) {
  const map = new Map()
  for (const it of items || []) {
    const d = it.order_date || ''
    if (!map.has(d)) map.set(d, { date: d, items: [], subtotal: 0 })
    const g = map.get(d)
    g.items.push(it)
    g.subtotal += Number(it.subtotal || 0)
  }
  return [...map.values()]
}

function toggleExpand(id) {
  if (expandedIds.value.has(id)) expandedIds.value.delete(id)
  else expandedIds.value.add(id)
  expandedIds.value = new Set(expandedIds.value)
}

async function loadBills() {
  loading.value = true
  try {
    const params = {}
    if (keyword.value) params.keyword = keyword.value
    if (startDate.value) params.start_date = startDate.value
    if (endDate.value) params.end_date = endDate.value
    if (sentFilter.value !== '') params.sent = sentFilter.value
    if (paidFilter.value !== '') params.paid = paidFilter.value
    bills.value = await billApi.list(params)
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    loading.value = false
  }
}

// ── 生成账单 ──
function ensureStores() {
  if (stores.value.length === 0) {
    storeApi.list().then((list) => { stores.value = list }).catch(() => {})
  }
}

function openGenerate() {
  editId.value = null
  genStoreId.value = null
  genStart.value = todayStr()
  genEnd.value = todayStr()
  genNote.value = ''
  preview.value = null
  genVisible.value = true
  ensureStores()
}

// 编辑账单：锁定客户，账期/备注可改，预览带 bill_id（把本账单已认领的订单也算进来）
function openEdit(bill) {
  editId.value = bill.id
  genStoreId.value = bill.store_id
  genStart.value = bill.period_start
  genEnd.value = bill.period_end
  genNote.value = bill.note || ''
  preview.value = null
  genVisible.value = true
  ensureStores()
  doPreview()
}

async function doPreview() {
  preview.value = null
  if (!genStoreId.value || !genStart.value || !genEnd.value) return
  if (genEnd.value < genStart.value) {
    ElMessage.warning('结束日期不能早于起始日期')
    return
  }
  previewLoading.value = true
  try {
    preview.value = await billApi.preview({
      store_id: genStoreId.value,
      start: genStart.value,
      end: genEnd.value,
      bill_id: editId.value || undefined,
    })
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    previewLoading.value = false
  }
}

async function handleSubmit() {
  creating.value = true
  try {
    if (editId.value) {
      await billApi.update(editId.value, {
        start: genStart.value,
        end: genEnd.value,
        note: genNote.value || null,
      })
      ElMessage.success('账单已更新')
    } else {
      await billApi.create({
        store_id: genStoreId.value,
        start: genStart.value,
        end: genEnd.value,
        note: genNote.value || null,
      })
      ElMessage.success('账单已生成')
    }
    genVisible.value = false
    loadBills()
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    creating.value = false
  }
}

async function handleGenerateToday() {
  try {
    await ElMessageBox.confirm(
      '将为今天有未出账订单的每个客户各生成一张账单（已出账的订单不会重复计入）。',
      '一键生成今日账单',
      { type: 'info', confirmButtonText: '生成', cancelButtonText: '取消' }
    )
  } catch {
    return
  }
  genTodayLoading.value = true
  try {
    const res = await billApi.generateToday()
    if (res.created > 0) ElMessage.success(`已生成 ${res.created} 张账单`)
    else ElMessage.info('今天没有需要出账的客户（订单都已出账或今天暂无订单）')
    loadBills()
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    genTodayLoading.value = false
  }
}

// ── 状态标记 ──
function replaceBill(updated) {
  const idx = bills.value.findIndex((b) => b.id === updated.id)
  if (idx !== -1) bills.value[idx] = updated
}

async function toggleSent(bill) {
  sentBusy.value = bill.id
  try {
    replaceBill(await billApi.markSent(bill.id, !bill.sent))
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    sentBusy.value = null
  }
}

async function togglePaid(bill) {
  paidBusy.value = bill.id
  try {
    replaceBill(await billApi.markPaid(bill.id, !bill.paid))
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    paidBusy.value = null
  }
}

async function handleDelete(bill) {
  try {
    await ElMessageBox.confirm(
      `确定删除账单 #${bill.id}（${bill.customer}）？该账单包含的订单会释放，可重新出账。`,
      '删除账单',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消', confirmButtonClass: 'el-button--danger' }
    )
  } catch {
    return
  }
  deletingId.value = bill.id
  try {
    await billApi.remove(bill.id)
    bills.value = bills.value.filter((b) => b.id !== bill.id)
    ElMessage.success('已删除')
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    deletingId.value = null
  }
}

// ── 小票图片 ──
function openImage(bill) {
  imgBill.value = bill
  imgTs.value = Date.now()   // 防缓存，标记状态变化后重开能刷新已收款戳
  imgVisible.value = true
}

async function downloadBillImage(bill) {
  if (!bill) return
  try {
    const blob = await billApi.downloadImage(bill.id)
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    const period = bill.period_start === bill.period_end
      ? bill.period_start
      : `${bill.period_start}_${bill.period_end}`
    a.href = url
    a.download = `对账单_${bill.customer}_${period}.png`
    document.body.appendChild(a)
    a.click()
    a.remove()
    URL.revokeObjectURL(url)
  } catch (e) {
    ElMessage.error(e.message)
  }
}

// 把小票 PNG 写入系统剪贴板，之后在聊天窗口 Ctrl+V 直接发（省去下载）。
// 需要安全上下文：https 或 localhost；用 ClipboardItem 的 Promise 形式保留用户手势。
async function copyBillImage(bill) {
  if (!bill) return
  if (!navigator.clipboard || !window.ClipboardItem) {
    ElMessage.warning('当前环境不支持复制图片（需 https 或 localhost），请改用下载')
    return
  }
  copyingId.value = bill.id
  try {
    const item = new ClipboardItem({
      'image/png': billApi.downloadImage(bill.id).then((raw) => {
        const b = raw instanceof Blob ? raw : new Blob([raw], { type: 'image/png' })
        return b.type === 'image/png' ? b : new Blob([b], { type: 'image/png' })
      }),
    })
    await navigator.clipboard.write([item])
    ElMessage.success('图片已复制，去聊天窗口 Ctrl+V 直接发')
  } catch (e) {
    ElMessage.error('复制失败：' + (e.message || '浏览器拒绝了剪贴板操作'))
  } finally {
    copyingId.value = null
  }
}

onMounted(() => {
  loadBills()
})
</script>

<style scoped>
.section-card { margin-bottom: 14px; }
.card-title   { font-weight: 600; font-size: 15px; }

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}
.header-tools {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.kw-input { width: 120px; }
.header-tools .date-input { width: 130px; }
.header-tools .date-input :deep(.el-input__wrapper) { min-width: 0; }
.status-select { width: 108px; }
.date-sep { color: #909399; font-size: 13px; }

@media (max-width: 600px) {
  .kw-input,
  .header-tools .date-input { flex: 1 1 0; width: auto; min-width: 0; }
}

/* 汇总条 */
.summary-bar {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 8px 12px;
  margin-bottom: 12px;
  background: #f5f7fa;
  border: 1px solid #e4e9f0;
  border-radius: 8px;
  font-size: 13px;
  color: #606266;
}
.summary-bar .unpaid { color: var(--el-color-danger); font-weight: 700; }

/* 账单卡片 */
.bill-item {
  border: 1px solid #e4e9f0;
  border-radius: 8px;
  margin-bottom: 10px;
  overflow: hidden;
}
.bill-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px;
  background: #f8fafc;
  cursor: pointer;
  gap: 10px;
  flex-wrap: wrap;
}
.bill-header:hover { background: #f0f4f9; }
.bill-meta {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  flex: 1;
}
.bill-id     { font-weight: 700; color: #909399; font-size: 13px; }
.bill-cust   { font-weight: 600; color: #303133; }
.bill-period { font-size: 12px; color: #909399; }
.bill-count  { font-size: 12px; color: #909399; }
.bill-amt    { font-weight: 700; color: var(--color-primary); }

.bill-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.st-tag { flex-shrink: 0; }

/* 明细 */
.bill-body { padding: 12px 14px; }
.day-block { margin-bottom: 12px; }
.day-title {
  font-size: 13px;
  font-weight: 700;
  color: #606266;
  background: #f5f7fa;
  border-radius: 4px;
  padding: 3px 8px;
  margin-bottom: 4px;
}
.items-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
.items-table td {
  padding: 5px 8px;
  border-bottom: 1px solid #f0f0f0;
}
.it-name { font-weight: 500; }
.it-spec { color: #909399; font-size: 12px; white-space: nowrap; }
.it-calc { color: #888; white-space: nowrap; text-align: right; }
.it-sub  { text-align: right; font-weight: 600; color: var(--color-primary); white-space: nowrap; }
.rep-tag { margin-left: 6px; }
.day-subtotal { text-align: right; font-size: 12px; color: #909399; padding: 4px 8px 0; }

.bill-total-row {
  text-align: right;
  margin-top: 8px;
  padding-top: 8px;
  border-top: 2px solid #ebeef5;
  font-size: 14px;
}
.bill-total-row b { color: var(--el-color-danger); font-size: 17px; margin-left: 6px; }
.bill-note { margin-top: 8px; font-size: 12px; color: #909399; }

/* 生成弹窗 */
.gen-form { display: flex; flex-direction: column; gap: 12px; }
.gen-row { display: flex; align-items: center; gap: 8px; }
.gen-label { width: 40px; flex-shrink: 0; color: #606266; font-size: 14px; }
.gen-tip { margin: -4px 0 2px 48px; color: #e6a23c; font-size: 12px; line-height: 1.4; }
.preview-panel {
  margin-top: 4px;
  border: 1px solid #e4e9f0;
  border-radius: 8px;
  padding: 12px;
  max-height: 300px;
  overflow-y: auto;
  background: #fafbfc;
}
.preview-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-weight: 600;
  margin-bottom: 8px;
}
.preview-total { color: var(--el-color-danger); }
.pv-day { margin-bottom: 8px; }
.pv-day-title { font-size: 12px; color: #909399; font-weight: 600; margin-bottom: 2px; }
.pv-line {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 13px;
  padding: 2px 0;
  gap: 12px;
}
.pv-name { flex: 1; }
.pv-spec { color: #b0b3b8; font-size: 12px; }
.pv-calc { color: #666; white-space: nowrap; }

/* 小票弹窗 */
.img-wrap { text-align: center; max-height: 70vh; overflow-y: auto; }
.bill-img { max-width: 100%; box-shadow: 0 2px 12px rgba(0,0,0,0.12); border-radius: 4px; }
</style>

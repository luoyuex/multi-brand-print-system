<template>
  <div class="page-wrap">
    <el-card class="section-card">
      <template #header>
        <div class="card-header">
          <span class="card-title">打印列表</span>
          <div class="header-tools">
            <el-date-picker
              v-model="startDate"
              type="date"
              placeholder="起始日期"
              value-format="YYYY-MM-DD"
              size="small"
              :clearable="false"
              class="date-input"
              @change="loadOrders"
            />
            <span class="date-sep">至</span>
            <el-date-picker
              v-model="endDate"
              type="date"
              placeholder="结束日期"
              value-format="YYYY-MM-DD"
              size="small"
              :clearable="false"
              class="date-input"
              @change="loadOrders"
            />
            <el-tag
              :type="printerReady ? 'success' : 'danger'"
              size="small"
              class="printer-chip"
              @click="refreshPrinterStatus"
            >
              打印机：{{ printerStatusText }}
            </el-tag>
            <el-button size="small" :loading="loading" @click="loadOrders">刷新</el-button>
            <el-button
              size="small"
              type="success"
              :loading="batchRunning"
              :disabled="batchRunning || printableCount === 0"
              @click="handleBatchPrint"
            >
              🖨️ 一键打印{{ printableCount ? `（${printableCount}）` : '' }}
            </el-button>
          </div>
        </div>
      </template>

      <!-- ── 批量打印进度条 ── -->
      <div v-if="batchRunning || batchDone" class="batch-progress">
        <el-progress
          :percentage="batchPercent"
          :status="batchProgressStatus"
          :stroke-width="14"
          class="batch-bar"
        />
        <div class="batch-stats">
          <span>进度 {{ batchProcessed }}/{{ batchTotal }}</span>
          <span class="ok">成功 {{ batchPrinted }}</span>
          <span v-if="batchFailed" class="bad">失败/跳过 {{ batchFailed }}</span>
          <span v-if="batchDone" class="done-tag">
            {{ batchFailed ? '已完成（部分失败）' : '全部完成' }}
          </span>
          <el-button
            v-if="batchDone"
            size="small"
            text
            @click="dismissBatch"
          >收起</el-button>
        </div>
      </div>

      <el-empty v-if="!loading && orders.length === 0" description="暂无订单" :image-size="80" />

      <div v-for="order in orders" :key="order.id" class="order-item">
        <!-- ── 标题行 ── -->
        <div class="order-header" @click="toggleExpand(order.id)">
          <div class="order-meta">
            <span class="order-id">#{{ order.id }}</span>
            <span class="order-brand">{{ order.brand_name }}</span>
            <span class="order-store">{{ order.customer }}</span>
            <span class="order-date">{{ formatDate(order.created_at) }}</span>
            <el-tag v-if="order.bill_id" type="info" size="small" effect="plain" class="billed-tag">已出账</el-tag>
          </div>
          <div class="order-actions" @click.stop>
            <el-tag
              :type="orderTagType(order)"
              size="small"
              class="status-tag"
              :effect="batchStatus.get(order.id) ? 'dark' : 'light'"
            >
              {{ orderTagText(order) }}
            </el-tag>
            <el-button size="small" type="primary" plain :disabled="batchRunning" :loading="printingId === order.id" @click="handlePrint(order)">🖨️ 打印</el-button>
            <el-button size="small" @click="toggleEdit(order)">
              {{ editingId === order.id ? '取消' : '编辑' }}
            </el-button>
            <el-button size="small" type="danger" plain :loading="deletingId === order.id" @click="handleDelete(order)">删除</el-button>
          </div>
        </div>

        <!-- ── 展开内容 ── -->
        <div v-show="expandedIds.has(order.id)" class="order-body">
          <!-- 查看模式 -->
          <template v-if="editingId !== order.id">
            <table class="items-table">
              <thead>
                <tr><th>品名</th><th>规格</th><th>数量</th><th>单价</th><th>小计</th></tr>
              </thead>
              <tbody>
                <tr v-for="item in order.items" :key="item.id">
                  <td>
                    {{ item.product_name }}
                    <el-tag v-if="item.is_replacement" type="warning" size="small" effect="dark" class="rep-tag">补</el-tag>
                  </td>
                  <td>{{ item.spec || '—' }}</td>
                  <td>{{ item.qty }}</td>
                  <td v-if="item.is_replacement" class="rep-cell">0.00</td>
                  <td v-else>¥{{ Number(item.price).toFixed(2) }}</td>
                  <td v-if="item.is_replacement" class="rep-cell">0.00</td>
                  <td v-else>¥{{ (item.qty * item.price).toFixed(2) }}</td>
                </tr>
              </tbody>
              <tfoot>
                <tr>
                  <td colspan="4" class="total-label">合计</td>
                  <td class="total-value">¥{{ orderTotal(order) }}</td>
                </tr>
              </tfoot>
            </table>
          </template>

          <!-- 编辑模式 -->
          <template v-else>
            <div v-for="(item, idx) in editItems" :key="idx" class="edit-row">
              <span class="edit-name">
                {{ item.product_name }}
                <el-tag v-if="item.is_replacement" type="warning" size="small" effect="dark" class="rep-tag">补</el-tag>
              </span>
              <span class="edit-spec">{{ item.spec }}</span>
              <el-input-number v-model="item.qty"   :min="0.01" :precision="2" size="small" style="width:110px;" />
              <el-input-number v-model="item.price" :min="0"    :precision="2" size="small" style="width:110px;" />
              <span class="edit-subtotal">¥{{ (item.qty * item.price).toFixed(2) }}</span>
              <button class="del-btn" @click="editItems.splice(idx, 1)">
                <el-icon><Delete /></el-icon>
              </button>
            </div>
            <div class="edit-footer">
              <span class="edit-total">合计 ¥{{ editTotal }}</span>
              <el-button size="small" type="primary" :loading="saving" @click="saveEdit(order.id)">保存</el-button>
            </div>
          </template>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Delete } from '@element-plus/icons-vue'
import { orderApi, printApi } from '../api'

function todayStr() {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

const orders      = ref([])
const startDate   = ref(todayStr())   // 默认当天
const endDate     = ref(todayStr())
const loading     = ref(false)

const expandedIds = ref(new Set())
const editingId   = ref(null)
const editItems   = ref([])
const saving      = ref(false)
const printingId  = ref(null)
const deletingId  = ref(null)

// ── 打印机状态 ──
const printerReady      = ref(true)
const printerStatusText = ref('检查中…')

// ── 一键批量打印 ──
const batchRunning   = ref(false)   // worker 是否在跑
const batchDone      = ref(false)   // 本批已结束（保留进度条直到用户收起）
const batchTotal     = ref(0)
const batchProcessed = ref(0)
const batchPrinted   = ref(0)
const batchFailed    = ref(0)
// order_id -> 'printing' | 'printed' | 'failed' | 'skipped'，驱动每单实时状态
const batchStatus    = ref(new Map())
let _eventSource     = null         // 当前 SSE 连接，组件卸载/新批次时关掉

// 可打印订单数（一键打印目标：列表里全部订单，无论是否已打印，
// 支持重复打印当天/历史所有单据）
const printableCount = computed(() => orders.value.length)

const batchPercent = computed(() =>
  batchTotal.value ? Math.round((batchProcessed.value / batchTotal.value) * 100) : 0
)
const batchProgressStatus = computed(() => {
  if (!batchDone.value) return ''
  return batchFailed.value ? 'warning' : 'success'
})

// 每单标签：批量进行中优先显示批量状态，否则回落到订单持久状态
function orderTagType(order) {
  const bs = batchStatus.value.get(order.id)
  if (bs === 'printing') return 'primary'
  if (bs === 'printed')  return 'success'
  if (bs === 'failed' || bs === 'skipped') return 'danger'
  return order.status === 'printed' ? 'success' : 'warning'
}
function orderTagText(order) {
  const bs = batchStatus.value.get(order.id)
  if (bs === 'printing') return '打印中…'
  if (bs === 'printed')  return '已打印'
  if (bs === 'failed')   return '失败'
  if (bs === 'skipped')  return '已跳过'
  return order.status === 'printed' ? '已打印' : '暂存'
}

const editTotal = computed(() =>
  editItems.value
    .reduce((s, i) => s + (i.is_replacement ? 0 : i.qty * i.price), 0)
    .toFixed(0)
)

function orderTotal(order) {
  return Math.round(
    order.items.reduce((s, i) => s + (i.is_replacement ? 0 : Number(i.qty) * Number(i.price)), 0)
  )
}

function formatDate(dt) {
  if (!dt) return ''
  const d = new Date(dt)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')} ` +
         `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

async function loadOrders() {
  loading.value = true
  try {
    const params = {}
    if (startDate.value) params.start_date = startDate.value
    if (endDate.value) params.end_date = endDate.value
    orders.value = await orderApi.list(params)
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    loading.value = false
  }
}

function toggleExpand(id) {
  if (expandedIds.value.has(id)) {
    expandedIds.value.delete(id)
  } else {
    expandedIds.value.add(id)
  }
  // 触发响应式更新
  expandedIds.value = new Set(expandedIds.value)
}

function toggleEdit(order) {
  if (editingId.value === order.id) {
    editingId.value = null
    editItems.value = []
    return
  }
  editingId.value = order.id
  editItems.value = order.items.map((i) => ({ ...i }))
  // 确保展开
  expandedIds.value = new Set([...expandedIds.value, order.id])
}

async function saveEdit(orderId) {
  if (editItems.value.length === 0) {
    ElMessage.warning('订单不能为空')
    return
  }
  saving.value = true
  try {
    const updated = await orderApi.update(orderId, { items: editItems.value })
    const idx = orders.value.findIndex((o) => o.id === orderId)
    if (idx !== -1) orders.value[idx] = updated
    editingId.value = null
    editItems.value = []
    ElMessage.success('保存成功')
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    saving.value = false
  }
}

// 查询打印机状态，刷新顶部状态标签。
async function refreshPrinterStatus() {
  try {
    const st = await printApi.status()
    printerReady.value = st.ready
    printerStatusText.value = st.status_text || (st.ready ? '就绪' : '未就绪')
  } catch {
    printerReady.value = false
    printerStatusText.value = '读取失败'
  }
}

// 把批量快照应用到本地状态：每单状态、进度计数、完成标记。
function applyBatchSnapshot(snap) {
  batchTotal.value     = snap.total
  batchProcessed.value = snap.processed
  batchPrinted.value   = snap.printed
  batchFailed.value    = snap.failed

  const m = new Map()
  for (const it of snap.items) m.set(it.order_id, it.status)
  batchStatus.value = m

  // 已打印的订单同步更新其持久状态，收起进度条后仍显示「已打印」。
  for (const it of snap.items) {
    if (it.status === 'printed') {
      const o = orders.value.find((x) => x.id === it.order_id)
      if (o) o.status = 'printed'
    }
  }

  if (snap.done && !batchDone.value) {
    batchDone.value = true
    batchRunning.value = false
    closeStream()
    const msg = snap.failed
      ? `打印完成：成功 ${snap.printed}，失败/跳过 ${snap.failed}`
      : `全部打印完成（${snap.printed} 单）`
    snap.failed ? ElMessage.warning(msg) : ElMessage.success(msg)
    refreshPrinterStatus()
  }
}

function closeStream() {
  if (_eventSource) {
    _eventSource.close()
    _eventSource = null
  }
}

// 一键打印：把当前列表里的全部订单按顺序提交（含已打印，支持重打），
// 后台串行打印，SSE 实时更新进度。
async function handleBatchPrint() {
  const targets = orders.value.slice()   // 列表全部订单，保持展示顺序
  if (targets.length === 0) {
    ElMessage.info('列表里没有订单')
    return
  }
  const reprintCount = targets.filter((o) => o.status === 'printed').length
  const tip = reprintCount
    ? `将按顺序打印 ${targets.length} 张订单（含 ${reprintCount} 张已打印，将重新打印），打印过程中请勿关闭页面。`
    : `将按顺序打印 ${targets.length} 张订单，打印过程中请勿关闭页面。`
  try {
    await ElMessageBox.confirm(tip, '一键打印',
      { type: 'info', confirmButtonText: '开始打印', cancelButtonText: '取消' }
    )
  } catch {
    return
  }

  // 复位批量状态
  closeStream()
  batchDone.value = false
  batchRunning.value = true
  batchStatus.value = new Map()
  batchTotal.value = targets.length
  batchProcessed.value = 0
  batchPrinted.value = 0
  batchFailed.value = 0

  let snap
  try {
    snap = await printApi.batch(targets.map((o) => o.id))
  } catch (e) {
    batchRunning.value = false
    ElMessage.error(e.message)
    return
  }
  applyBatchSnapshot(snap)
  if (batchDone.value) return   // 极端情况下已同步完成

  // 订阅 SSE 进度流
  const es = new EventSource(printApi.batchStreamUrl(snap.batch_id))
  _eventSource = es
  es.onmessage = (ev) => {
    try {
      applyBatchSnapshot(JSON.parse(ev.data))
    } catch { /* 忽略心跳/非 JSON 帧 */ }
  }
  es.onerror = () => {
    // 连接断开：若批次未标记完成，降级为一次性快照轮询兜底。
    closeStream()
    if (!batchDone.value) pollBatchOnce(snap.batch_id)
  }
}

// SSE 断连兜底：轮询快照直到完成。
async function pollBatchOnce(batchId) {
  try {
    const snap = await printApi.batchSnapshot(batchId)
    applyBatchSnapshot(snap)
    if (!batchDone.value) setTimeout(() => pollBatchOnce(batchId), 2000)
  } catch {
    batchRunning.value = false
  }
}

function dismissBatch() {
  batchDone.value = false
  batchStatus.value = new Map()
}

// 打印逻辑：调后端静默打印（主机 Playwright 渲染 PDF → SumatraPDF 出纸），
// 成功出纸后后端才把订单标记为已打印。
async function handlePrint(order) {
  printingId.value = order.id
  try {
    const updated = await orderApi.print(order.id)
    const idx = orders.value.findIndex((o) => o.id === order.id)
    if (idx !== -1) orders.value[idx] = updated
    ElMessage.success('已发送打印')
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    printingId.value = null
  }
}

// 删除订单：二次确认后调后端硬删除（明细随之级联删除），成功后从列表移除。
async function handleDelete(order) {
  try {
    await ElMessageBox.confirm(
      `确定删除订单 #${order.id}（${order.customer}）？该操作不可恢复。`,
      '删除订单',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消', confirmButtonClass: 'el-button--danger' }
    )
  } catch {
    return   // 用户取消
  }
  deletingId.value = order.id
  try {
    await orderApi.remove(order.id)
    orders.value = orders.value.filter((o) => o.id !== order.id)
    expandedIds.value.delete(order.id)
    expandedIds.value = new Set(expandedIds.value)
    if (editingId.value === order.id) {
      editingId.value = null
      editItems.value = []
    }
    ElMessage.success('已删除')
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    deletingId.value = null
  }
}

onMounted(() => {
  loadOrders()
  refreshPrinterStatus()
})

// 离开页面时关掉 SSE 连接，避免泄漏（批量仍会在后端继续跑到完成）。
onBeforeUnmount(() => {
  closeStream()
})
</script>

<style scoped>
.section-card { margin-bottom: 14px; }
.card-title   { font-weight: 600; font-size: 15px; }

/* ── 卡片头部 ── */
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
.date-sep { color: #909399; font-size: 13px; }
/* 单个日期选择器更窄，避免移动端过宽 */
.header-tools .date-input {
  width: 130px;
}
.header-tools .date-input :deep(.el-input__wrapper) {
  min-width: 0;
}

/* 打印机状态标签：可点击刷新 */
.printer-chip { cursor: pointer; user-select: none; }

/* ── 移动端：日期选择器等分一行 ── */
@media (max-width: 600px) {
  .header-tools .date-input { flex: 1 1 0; width: auto; min-width: 0; }
}

/* ── 批量打印进度 ── */
.batch-progress {
  margin-bottom: 14px;
  padding: 12px 14px;
  background: #f5f7fa;
  border: 1px solid #e4e9f0;
  border-radius: 8px;
}
.batch-bar { margin-bottom: 8px; }
.batch-stats {
  display: flex;
  align-items: center;
  gap: 14px;
  flex-wrap: wrap;
  font-size: 13px;
  color: #606266;
}
.batch-stats .ok   { color: var(--el-color-success); font-weight: 600; }
.batch-stats .bad  { color: var(--el-color-danger); font-weight: 600; }
.batch-stats .done-tag { font-weight: 600; color: #303133; }

/* ── 订单卡片 ── */
.order-item {
  border: 1px solid #e4e9f0;
  border-radius: 8px;
  margin-bottom: 10px;
  overflow: hidden;
}

.order-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px;
  background: #f8fafc;
  cursor: pointer;
  gap: 10px;
  flex-wrap: wrap;
}
.order-header:hover { background: #f0f4f9; }

.order-meta {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  flex: 1;
}
.order-id    { font-weight: 700; color: #909399; font-size: 13px; }
.order-brand { font-weight: 600; color: #303133; }
.order-store { color: #606266; }
.order-date  { font-size: 12px; color: #909399; }

.order-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.status-tag { flex-shrink: 0; }

/* ── 订单明细 ── */
.order-body { padding: 12px 14px; }

.items-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
.items-table th,
.items-table td {
  padding: 6px 10px;
  text-align: left;
  border-bottom: 1px solid #f0f0f0;
}
.items-table thead th {
  background: #f5f7fa;
  font-weight: 600;
  color: #606266;
}
.total-label { text-align: right; font-weight: 700; }
.total-value { font-weight: 700; color: var(--color-primary); }

/* 补货标记 */
.rep-tag { margin-left: 6px; }
.rep-cell { color: var(--color-warning); font-weight: 700; }

/* ── 编辑行 ── */
.edit-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 6px 0;
  border-bottom: 1px solid #f0f0f0;
  flex-wrap: wrap;
}
.edit-name     { flex: 1; min-width: 80px; font-weight: 500; }
.edit-spec     { color: #909399; font-size: 12px; white-space: nowrap; }
.edit-subtotal { min-width: 72px; text-align: right; color: var(--color-primary); font-weight: 600; }

.del-btn {
  flex-shrink: 0;
  width: 26px;
  height: 26px;
  padding: 0;
  border: none;
  border-radius: 50%;
  background: var(--el-color-danger);
  color: #fff;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
}
.del-btn:hover { opacity: 0.85; }

.edit-footer {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 10px;
}
.edit-total { font-weight: 700; color: var(--color-primary); }
</style>

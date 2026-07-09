<template>
  <div class="page-wrap">
    <el-card class="section-card">
      <template #header>
        <span class="card-title">打印列表</span>
        <el-button size="small" style="float:right;" :loading="loading" @click="loadOrders">刷新</el-button>
      </template>

      <el-empty v-if="!loading && orders.length === 0" description="暂无订单" :image-size="80" />

      <div v-for="order in orders" :key="order.id" class="order-item">
        <!-- ── 标题行 ── -->
        <div class="order-header" @click="toggleExpand(order.id)">
          <div class="order-meta">
            <span class="order-id">#{{ order.id }}</span>
            <span class="order-brand">{{ order.brand_name }}</span>
            <span class="order-store">{{ order.customer }}</span>
            <span class="order-date">{{ formatDate(order.created_at) }}</span>
          </div>
          <div class="order-actions" @click.stop>
            <el-tag :type="order.status === 'printed' ? 'success' : 'warning'" size="small" class="status-tag">
              {{ order.status === 'printed' ? '已打印' : '暂存' }}
            </el-tag>
            <el-button size="small" type="primary" plain :loading="printingId === order.id" @click="handlePrint(order)">🖨️ 打印</el-button>
            <el-button size="small" @click="toggleEdit(order)">
              {{ editingId === order.id ? '取消' : '编辑' }}
            </el-button>
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
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Delete } from '@element-plus/icons-vue'
import { orderApi } from '../api'

const orders      = ref([])
const loading     = ref(false)
const expandedIds = ref(new Set())
const editingId   = ref(null)
const editItems   = ref([])
const saving      = ref(false)
const printingId  = ref(null)

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
    orders.value = await orderApi.list()
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

onMounted(() => {
  loadOrders()
})
</script>

<style scoped>
.section-card { margin-bottom: 14px; }
.card-title   { font-weight: 600; font-size: 15px; }

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

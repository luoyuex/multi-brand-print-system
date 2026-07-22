<template>
  <div class="page-wrap">
    <!-- ── 品牌 + 客户 ───────────────────────────── -->
    <el-card class="section-card">
      <el-row :gutter="12" class="mobile-row">
        <el-col :xs="24" :sm="10" :md="8">
          <el-form-item label="品牌" class="form-field">
            <el-select
              :key="brandStore.brands.length"
              v-model="currentBrandId"
              placeholder="选择品牌"
              style="width:100%;"
              @change="onBrandChange"
            >
              <el-option
                v-for="b in brandStore.brands"
                :key="b.id"
                :label="b.name"
                :value="b.id"
              />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :xs="24" :sm="10" :md="8">
          <el-form-item label="店铺" class="form-field">
            <el-select
              :key="stores.length"
              v-model="orderStore.storeId"
              placeholder="选择店铺"
              style="width:100%;"
              filterable
            >
              <el-option
                v-for="s in stores"
                :key="s.id"
                :value="s.id"
                :label="s.name"
              >
                <span>{{ s.name }}</span>
                <span v-if="s.contact" style="float:right;color:#999;font-size:12px;">{{ s.contact }}</span>
              </el-option>
            </el-select>
          </el-form-item>
        </el-col>
      </el-row>
    </el-card>

    <!-- ── 商品搜索 ──────────────────────────────── -->
    <el-card class="section-card">
      <el-row :gutter="10" class="mobile-row">
        <el-col :xs="24" :sm="14" :md="14">
          <el-autocomplete
            ref="searchRef"
            v-model="searchKeyword"
            :fetch-suggestions="fetchSuggestions"
            :placeholder="isMobile ? '输入序号或品名搜索' : '输入序号或商品名称搜索（回车确认）'"
            style="width:100%;"
            value-key="label"
            :trigger-on-focus="false"
            @select="onProductSelect"
            @keyup.enter.native="handleEnter"
          >
            <template #default="{ item }">
              <span class="suggest-code">{{ item.code }}</span>
              <span>{{ item.name }}</span>
              <span class="suggest-meta">{{ item.spec }} ¥{{ item.price }}</span>
            </template>
          </el-autocomplete>
        </el-col>
        <el-col :xs="14" :sm="6" :md="5">
          <el-input-number
            v-model="inputQty"
            :min="0.01"
            :precision="2"
            :step="1"
            placeholder="数量"
            style="width:100%;"
            @keyup.enter.native="addToOrder()"
          />
        </el-col>
        <el-col :xs="10" :sm="4" :md="5">
          <el-button
            type="primary"
            style="width:100%;"
            :disabled="!selectedProduct"
            @click="addToOrder()"
          >
            {{ isMobile ? '加入' : '加入订单 ↵' }}
          </el-button>
        </el-col>
      </el-row>
      <el-row :gutter="10" class="mobile-row" style="margin-top:8px;">
        <el-col :span="24">
          <el-button
            type="warning"
            plain
            style="width:100%;"
            :disabled="!selectedProduct"
            @click="addAsReplacement"
          >
            作为补货加入（坏损免费补发）
          </el-button>
        </el-col>
      </el-row>
    </el-card>

    <!-- ── 订单明细 ──────────────────────────────── -->
    <el-card class="section-card order-card">
      <template #header>
        <span class="card-title">订单明细</span>
        <span class="order-total">合计：¥{{ orderStore.total.toFixed(2) }}</span>
      </template>

      <!-- 桌面/平板：表格 -->
      <el-table v-if="!isMobile" :data="orderStore.items" border stripe style="width:100%;">
        <el-table-column type="index" label="#" width="48" />
        <el-table-column prop="product_code" label="序号" width="72" />
        <el-table-column label="品名" min-width="120">
          <template #default="{ row }">
            <span>{{ row.product_name }}</span>
            <el-tag v-if="row.is_replacement" type="warning" size="small" effect="dark" style="margin-left:6px;">补</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="规格" width="110">
          <template #default="{ row, $index }">
            <el-input
              v-model="row.spec"
              size="small"
              placeholder="规格"
              @change="(v) => orderStore.updateItem($index, 'spec', v)"
            />
          </template>
        </el-table-column>
        <el-table-column label="数量" width="118">
          <template #default="{ row, $index }">
            <el-input-number
              v-model="row.qty"
              :min="0.01"
              :precision="2"
              size="small"
              style="width:100%;"
              @change="(v) => orderStore.updateItem($index, 'qty', v)"
            />
          </template>
        </el-table-column>
        <el-table-column label="单价" width="128">
          <template #default="{ row, $index }">
            <el-input-number
              v-model="row.price"
              :min="0"
              :precision="2"
              size="small"
              style="width:100%;"
              :disabled="row.is_replacement"
              :class="row.manual_price ? 'manual-price' : ''"
              @change="(v) => orderStore.updateItem($index, 'price', v)"
            />
          </template>
        </el-table-column>
        <el-table-column label="小计" width="96">
          <template #default="{ row }">
            <span v-if="row.is_replacement" class="replacement-sub">补发</span>
            <span v-else>¥{{ (row.qty * row.price).toFixed(2) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="128">
          <template #default="{ row, $index }">
            <el-button
              :type="row.is_replacement ? 'warning' : 'default'"
              size="small"
              :plain="!row.is_replacement"
              @click="orderStore.toggleReplacement($index)"
            >补</el-button>
            <el-button type="danger" size="small" circle @click="orderStore.removeItem($index)">
              <el-icon><Delete /></el-icon>
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 移动端：卡片列表 -->
      <div v-else class="mobile-item-list">
        <div
          v-for="(item, index) in orderStore.items"
          :key="index"
          class="mobile-item-card"
        >
          <div class="item-header">
            <span class="item-name">{{ item.product_name }}</span>
            <el-tag v-if="item.is_replacement" type="warning" size="small" effect="dark" class="rep-tag">补</el-tag>
            <button class="item-delete" @click="orderStore.removeItem(index)">
              <el-icon><Delete /></el-icon>
            </button>
          </div>
          <div class="item-body">
            <div class="item-field">
              <span class="field-label">规格</span>
              <el-input
                v-model="item.spec"
                size="small"
                placeholder="规格"
                style="width:90px;"
                @change="(v) => orderStore.updateItem(index, 'spec', v)"
              />
            </div>
            <div class="item-field">
              <span class="field-label">数量</span>
              <el-input-number
                v-model="item.qty"
                :min="0.01"
                :precision="2"
                size="small"
                @change="(v) => orderStore.updateItem(index, 'qty', v)"
              />
            </div>
            <div class="item-field">
              <span class="field-label">单价</span>
              <el-input-number
                v-model="item.price"
                :min="0"
                :precision="2"
                size="small"
                :disabled="item.is_replacement"
                :class="item.manual_price ? 'manual-price' : ''"
                @change="(v) => orderStore.updateItem(index, 'price', v)"
              />
            </div>
            <div class="item-subtotal">
              <span v-if="item.is_replacement" class="replacement-sub">补发</span>
              <span v-else>¥{{ (item.qty * item.price).toFixed(2) }}</span>
            </div>
          </div>
          <div class="item-actions">
            <el-button
              :type="item.is_replacement ? 'warning' : 'default'"
              size="small"
              :plain="!item.is_replacement"
              style="width:100%;"
              @click="orderStore.toggleReplacement(index)"
            >{{ item.is_replacement ? '取消补货' : '标记补货（坏损补发）' }}</el-button>
          </div>
        </div>

        <el-empty v-if="orderStore.items.length === 0" description="暂无商品" :image-size="80" />
      </div>

      <!-- 桌面操作按钮 -->
      <div v-if="!isMobile" class="desktop-actions">
        <el-button @click="orderStore.clear()">清空</el-button>
        <el-button type="success" :loading="submitting" @click="submitOrder">
          提交订单
        </el-button>
      </div>
    </el-card>

    <!-- 移动端底部固定操作栏 -->
    <div v-if="isMobile" class="mobile-action-bar">
      <el-button size="small" plain @click="orderStore.clear()">清空</el-button>
      <div class="action-total">合计 <strong>¥{{ orderStore.total.toFixed(2) }}</strong></div>
      <el-button type="success" :loading="submitting" @click="submitOrder">
        提交订单
      </el-button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Delete } from '@element-plus/icons-vue'
import { useBrandStore } from '../stores/brand'
import { useOrderStore } from '../stores/order'
import { productApi, orderApi, storeApi } from '../api'
import { useBreakpoint } from '../composables/useBreakpoint'

const { isMobile } = useBreakpoint()
const brandStore = useBrandStore()
const orderStore = useOrderStore()

const currentBrandId = ref(null)
const stores = ref([])
const searchKeyword = ref('')
const inputQty = ref(1)
const selectedProduct = ref(null)
const submitting = ref(false)
const searchRef = ref(null)

onMounted(async () => {
  await brandStore.fetchBrands()
  // 优先从草稿恢复品牌；否则默认取第一个品牌
  const restoredId = orderStore.brandId
  if (restoredId && brandStore.brands.find((b) => b.id === restoredId)) {
    currentBrandId.value = restoredId
    brandStore.selectBrand(brandStore.brands.find((b) => b.id === restoredId))
  } else if (brandStore.currentBrand) {
    currentBrandId.value = brandStore.currentBrand.id
  }
  // 店铺按当前品牌过滤（一店一品牌）
  await loadStores(currentBrandId.value)
})

// 按品牌拉取店铺；不传品牌则不请求（列表清空）
async function loadStores(brandId) {
  if (!brandId) { stores.value = []; return }
  try {
    stores.value = await storeApi.list({ brand_id: brandId })
  } catch { stores.value = [] }
}

async function onBrandChange(id) {
  orderStore.brandId = id   // 同步到草稿
  brandStore.selectBrand(brandStore.brands.find((b) => b.id === id))
  selectedProduct.value = null
  searchKeyword.value = ''
  // 切品牌：清空已选店铺（原店铺可能不属于新品牌），重新按品牌加载
  orderStore.storeId = null
  await loadStores(id)
}

async function fetchSuggestions(query, cb) {
  if (!currentBrandId.value) return cb([])
  try {
    const list = await productApi.list({ brand_id: currentBrandId.value, search: query })
    cb(list.map((p) => ({ ...p, label: `${p.code} ${p.name}` })))
  } catch { cb([]) }
}

function onProductSelect(item) {
  selectedProduct.value = item
  searchKeyword.value = `${item.code} ${item.name}`
}

async function handleEnter() {
  const kw = searchKeyword.value.trim()
  if (!kw || !currentBrandId.value) return
  if (/^\d+$/.test(kw)) {
    const list = await productApi.list({ brand_id: currentBrandId.value, search: kw })
    const exact = list.find((p) => p.code === kw)
    if (exact) { selectedProduct.value = exact; addToOrder() }
  }
}

function addToOrder(asReplacement = false) {
  if (!selectedProduct.value) { ElMessage.warning('请先选择商品'); return }
  if (!inputQty.value || inputQty.value <= 0) { ElMessage.warning('请输入有效数量'); return }
  orderStore.addItem(selectedProduct.value, inputQty.value, asReplacement)
  selectedProduct.value = null
  searchKeyword.value = ''
  inputQty.value = 1
  searchRef.value?.focus()
}

function addAsReplacement() {
  addToOrder(true)
}

async function submitOrder() {
  if (!orderStore.storeId) { ElMessage.warning('请选择店铺'); return }
  if (orderStore.items.length === 0) { ElMessage.warning('订单为空'); return }
  submitting.value = true
  try {
    await orderApi.create({
      brand_id: currentBrandId.value,
      store_id: orderStore.storeId,
      items: orderStore.items,
    })
    ElMessage.success('订单已暂存，可在「打印列表」查看并打印')
    orderStore.clear()
  } catch (e) { ElMessage.error(e.message) }
  finally { submitting.value = false }
}
</script>

<style scoped>
.section-card { margin-bottom: 14px; }

/* 移动端底部留出操作栏的空间，防止内容被遮挡 */
@media (max-width: 767px) {
  .page-wrap {
    padding-bottom: calc(var(--tab-height, 56px) + 60px);
  }
}

.form-field { margin-bottom: 0; }

/* 搜索建议 */
.suggest-code { font-weight: 700; margin-right: 8px; color: #303133; }
.suggest-meta { float: right; color: #909399; font-size: 12px; }

/* 卡片 header */
.card-title { font-weight: 600; font-size: 15px; }
.order-total { float: right; color: var(--color-primary); font-weight: 700; font-size: 16px; }

/* 桌面操作按钮 */
.desktop-actions { margin-top: 16px; text-align: right; }

/* 手动改价高亮 */
:deep(.manual-price .el-input__inner) {
  color: var(--color-warning);
  font-weight: bold;
}

/* 移动端 el-row 换行时补纵向间距 */
@media (max-width: 767px) {
  :deep(.mobile-row) {
    row-gap: 10px;
  }
}

/* ── 移动端卡片列表 ────────────────────────── */
.mobile-item-list { display: flex; flex-direction: column; gap: 10px; }

.mobile-item-card {
  background: #f8fafc;
  border: 1px solid #e4e9f0;
  border-radius: 10px;
  padding: 12px 14px;
}

.item-header {
  display: flex;
  align-items: center;
  margin-bottom: 10px;
  gap: 8px;
}
.item-name { font-weight: 600; font-size: 15px; flex: 1; }
.item-spec { color: #909399; font-size: 12px; background: #eef0f5; padding: 2px 7px; border-radius: 20px; flex-shrink: 0; }
.item-delete {
  margin-left: auto;
  flex-shrink: 0;
  width: 28px;
  height: 28px;
  padding: 0;
  border: none;
  border-radius: 50%;
  background: var(--el-color-danger);
  color: #fff;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  transition: background 0.2s;
}
.item-delete:hover { background: var(--el-color-danger-dark-2); }
.item-delete:active { background: var(--el-color-danger-dark-2); opacity: 0.85; }

.item-body {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}
.item-field { display: flex; align-items: center; gap: 6px; }
.field-label { font-size: 12px; color: #606266; white-space: nowrap; }
.item-subtotal { margin-left: auto; font-weight: 700; color: var(--color-primary); font-size: 15px; }

/* 补货标记 */
.rep-tag { flex-shrink: 0; margin-left: 6px; }
.replacement-sub { color: var(--color-warning); font-weight: 700; }
.item-actions { margin-top: 10px; }

/* ── 移动端底部操作栏 ──────────────────────── */
.mobile-action-bar {
  position: fixed;
  bottom: var(--tab-height);  /* 刚好在 Tab Bar 上方 */
  left: 0;
  right: 0;
  background: #fff;
  padding: 10px 16px;
  display: flex;
  align-items: center;
  gap: 10px;
  box-shadow: 0 -2px 10px rgba(0,0,0,0.08);
  z-index: 150;
}
.action-total { flex: 1; text-align: center; font-size: 14px; color: #606266; }
.action-total strong { color: var(--color-primary); font-size: 16px; }
</style>

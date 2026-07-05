<template>
  <div>
    <el-card>
      <template #header>
        <span>商品管理</span>
        <el-button type="primary" style="float:right;" @click="openAdd">+ 新增商品</el-button>
      </template>

      <!-- 筛选 -->
      <el-row :gutter="12" style="margin-bottom:16px;">
        <el-col :xs="24" :sm="8" :md="6">
          <el-select
            v-model="filterBrandId"
            placeholder="按品牌筛选"
            clearable
            style="width:100%; margin-bottom:8px;"
            @change="load"
          >
            <el-option v-for="b in brands" :key="b.id" :label="b.name" :value="b.id" />
          </el-select>
        </el-col>
        <el-col :xs="24" :sm="10" :md="8">
          <el-input v-model="filterSearch" placeholder="搜索序号/名称" clearable @input="load" />
        </el-col>
      </el-row>

      <!-- 桌面/平板：表格 -->
      <el-table v-if="!isMobile" :data="products" border stripe>
        <el-table-column prop="code" label="序号" width="80" />
        <el-table-column label="品牌" width="100">
          <template #default="{ row }">
            {{ brands.find((b) => b.id === row.brand_id)?.name || '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="name" label="品名" min-width="120" />
        <el-table-column prop="spec" label="规格" width="80" />
        <el-table-column prop="price" label="单价" width="100">
          <template #default="{ row }">¥{{ row.price }}</template>
        </el-table-column>
        <el-table-column label="操作" width="140">
          <template #default="{ row }">
            <el-button size="small" @click="openEdit(row)">编辑</el-button>
            <el-button size="small" type="danger" @click="remove(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 移动端：卡片列表 -->
      <div v-else class="mobile-product-list">
        <div v-for="p in products" :key="p.id" class="product-card">
          <div class="pc-left">
            <span class="pc-code">{{ p.code }}</span>
            <span class="pc-name">{{ p.name }}</span>
            <span class="pc-spec">{{ p.spec }}</span>
          </div>
          <div class="pc-right">
            <span class="pc-price">¥{{ p.price }}</span>
            <div class="pc-actions">
              <el-button size="small" @click="openEdit(p)">编辑</el-button>
              <el-button size="small" type="danger" @click="remove(p)">删除</el-button>
            </div>
          </div>
        </div>
        <el-empty v-if="products.length === 0" description="暂无商品" :image-size="80" />
      </div>
    </el-card>

    <!-- 新增/编辑 Dialog -->
    <el-dialog
      v-model="dialogVisible"
      :title="editTarget ? '编辑商品' : '新增商品'"
      :width="isMobile ? '92%' : '420px'"
    >
      <el-form :model="form" label-width="60px">
        <el-form-item label="品牌">
          <el-select v-model="form.brand_id" style="width:100%;">
            <el-option v-for="b in brands" :key="b.id" :label="b.name" :value="b.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="序号">
          <el-input v-model="form.code" />
        </el-form-item>
        <el-form-item label="品名">
          <el-input v-model="form.name" />
        </el-form-item>
        <el-form-item label="规格">
          <el-input v-model="form.spec" placeholder="个/箱/kg…" />
        </el-form-item>
        <el-form-item label="单价">
          <el-input-number v-model="form.price" :min="0" :precision="2" style="width:100%;" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="save">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { brandApi, productApi } from '../api'
import { useBreakpoint } from '../composables/useBreakpoint'

const { isMobile } = useBreakpoint()
const brands = ref([])
const products = ref([])
const filterBrandId = ref(null)
const filterSearch = ref('')
const dialogVisible = ref(false)
const editTarget = ref(null)
const saving = ref(false)
const form = ref({ brand_id: null, code: '', name: '', spec: '', price: 0 })

onMounted(async () => {
  brands.value = await brandApi.list()
  await load()
})

async function load() {
  products.value = await productApi.list({
    brand_id: filterBrandId.value || undefined,
    search: filterSearch.value || undefined,
  })
}

function openAdd() {
  editTarget.value = null
  form.value = { brand_id: brands.value[0]?.id || null, code: '', name: '', spec: '', price: 0 }
  dialogVisible.value = true
}

function openEdit(row) {
  editTarget.value = row
  form.value = { brand_id: row.brand_id, code: row.code, name: row.name, spec: row.spec, price: Number(row.price) }
  dialogVisible.value = true
}

async function save() {
  saving.value = true
  try {
    if (editTarget.value) {
      await productApi.update(editTarget.value.id, form.value)
      ElMessage.success('已更新')
    } else {
      await productApi.create(form.value)
      ElMessage.success('已新增')
    }
    dialogVisible.value = false
    await load()
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    saving.value = false
  }
}

async function remove(row) {
  await ElMessageBox.confirm(`确定删除「${row.name}」？`, '提示', { type: 'warning' })
  await productApi.remove(row.id)
  ElMessage.success('已删除')
  await load()
}
</script>

<style scoped>
/* 移动端商品卡片列表 */
.mobile-product-list { display: flex; flex-direction: column; gap: 10px; }

.product-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 14px;
  background: #f8fafc;
  border: 1px solid #e4e9f0;
  border-radius: 10px;
}

.pc-left { display: flex; align-items: center; gap: 8px; flex: 1; min-width: 0; }
.pc-code {
  font-size: 12px;
  background: var(--color-primary);
  color: #fff;
  padding: 2px 7px;
  border-radius: 20px;
  white-space: nowrap;
}
.pc-name { font-weight: 600; font-size: 14px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.pc-spec { font-size: 12px; color: #909399; white-space: nowrap; }

.pc-right { display: flex; flex-direction: column; align-items: flex-end; gap: 6px; }
.pc-price { font-weight: 700; color: var(--color-primary); }
.pc-actions { display: flex; gap: 6px; }
</style>

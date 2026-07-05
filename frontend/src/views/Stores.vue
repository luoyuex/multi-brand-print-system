<template>
  <div>
    <el-card>
      <template #header>
        <span>店铺管理</span>
        <el-button type="primary" style="float:right;" @click="openAdd">+ 新增店铺</el-button>
      </template>

      <!-- 搜索 -->
      <el-row style="margin-bottom:16px;">
        <el-col :xs="24" :sm="10" :md="8">
          <el-input v-model="filterSearch" placeholder="搜索店铺名称/联系人" clearable @input="load" />
        </el-col>
      </el-row>

      <!-- 桌面/平板：表格 -->
      <el-table v-if="!isMobile" :data="stores" border stripe>
        <el-table-column prop="name" label="店铺名称" min-width="120" />
        <el-table-column prop="contact" label="联系人" width="100" />
        <el-table-column prop="phone" label="电话" width="140" />
        <el-table-column prop="address" label="地址" min-width="160" show-overflow-tooltip />
        <el-table-column label="操作" width="140">
          <template #default="{ row }">
            <el-button size="small" @click="openEdit(row)">编辑</el-button>
            <el-button size="small" type="danger" @click="remove(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 移动端：卡片列表 -->
      <div v-else class="store-list">
        <div v-for="s in stores" :key="s.id" class="store-card">
          <div class="sc-main">
            <div class="sc-name">{{ s.name }}</div>
            <div v-if="s.contact || s.phone" class="sc-meta">
              <span v-if="s.contact">👤 {{ s.contact }}</span>
              <span v-if="s.phone">📞 {{ s.phone }}</span>
            </div>
            <div v-if="s.address" class="sc-addr">📍 {{ s.address }}</div>
          </div>
          <div class="sc-actions">
            <el-button size="small" @click="openEdit(s)">编辑</el-button>
            <el-button size="small" type="danger" @click="remove(s)">删除</el-button>
          </div>
        </div>
        <el-empty v-if="stores.length === 0" description="暂无店铺" :image-size="80" />
      </div>
    </el-card>

    <!-- 新增/编辑 Dialog -->
    <el-dialog
      v-model="dialogVisible"
      :title="editTarget ? '编辑店铺' : '新增店铺'"
      :width="isMobile ? '92%' : '440px'"
    >
      <el-form :model="form" label-width="70px">
        <el-form-item label="店铺名称" required>
          <el-input v-model="form.name" placeholder="如：张记水果店" />
        </el-form-item>
        <el-form-item label="联系人">
          <el-input v-model="form.contact" placeholder="可选" />
        </el-form-item>
        <el-form-item label="电话">
          <el-input v-model="form.phone" placeholder="可选" />
        </el-form-item>
        <el-form-item label="地址">
          <el-input v-model="form.address" placeholder="可选" type="textarea" :rows="2" />
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
import { storeApi } from '../api'
import { useBreakpoint } from '../composables/useBreakpoint'

const { isMobile } = useBreakpoint()
const stores = ref([])
const filterSearch = ref('')
const dialogVisible = ref(false)
const editTarget = ref(null)
const saving = ref(false)
const form = ref({ name: '', contact: '', phone: '', address: '' })

onMounted(load)

async function load() {
  stores.value = await storeApi.list({ search: filterSearch.value || undefined })
}

function openAdd() {
  editTarget.value = null
  form.value = { name: '', contact: '', phone: '', address: '' }
  dialogVisible.value = true
}

function openEdit(row) {
  editTarget.value = row
  form.value = { name: row.name, contact: row.contact || '', phone: row.phone || '', address: row.address || '' }
  dialogVisible.value = true
}

async function save() {
  if (!form.value.name.trim()) { ElMessage.warning('店铺名称不能为空'); return }
  saving.value = true
  try {
    if (editTarget.value) {
      await storeApi.update(editTarget.value.id, form.value)
      ElMessage.success('已更新')
    } else {
      await storeApi.create(form.value)
      ElMessage.success('店铺已添加')
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
  await storeApi.remove(row.id)
  ElMessage.success('已删除')
  await load()
}
</script>

<style scoped>
.store-list { display: flex; flex-direction: column; gap: 10px; }

.store-card {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  padding: 14px;
  background: #f8fafc;
  border: 1px solid #e4e9f0;
  border-radius: 10px;
  gap: 12px;
}

.sc-main { flex: 1; min-width: 0; }
.sc-name { font-weight: 600; font-size: 15px; margin-bottom: 4px; }
.sc-meta { display: flex; gap: 12px; font-size: 13px; color: #606266; margin-bottom: 2px; }
.sc-addr { font-size: 12px; color: #909399; margin-top: 4px; }

.sc-actions { display: flex; flex-direction: column; gap: 6px; }
</style>

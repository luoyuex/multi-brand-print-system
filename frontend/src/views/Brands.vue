<template>
  <div>
    <el-card style="max-width: 600px; width: 100%;">
      <template #header>
        <span>品牌管理</span>
        <el-button type="primary" style="float:right;" @click="openAdd">+ 新增品牌</el-button>
      </template>

      <el-table :data="brands" border stripe>
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="name" label="品牌名称" />
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" title="新增品牌" :width="isMobile ? '92%' : '360px'">
      <el-form :model="form" label-width="70px">
        <el-form-item label="品牌名称">
          <el-input v-model="form.name" placeholder="如：MISS" />
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
import { ElMessage } from 'element-plus'
import { brandApi } from '../api'
import { useBreakpoint } from '../composables/useBreakpoint'

const { isMobile } = useBreakpoint()

const brands = ref([])
const dialogVisible = ref(false)
const saving = ref(false)
const form = ref({ name: '' })

onMounted(load)

async function load() {
  brands.value = await brandApi.list()
}

function openAdd() {
  form.value = { name: '' }
  dialogVisible.value = true
}

async function save() {
  if (!form.value.name.trim()) {
    ElMessage.warning('品牌名称不能为空')
    return
  }
  saving.value = true
  try {
    await brandApi.create(form.value)
    ElMessage.success('品牌已添加')
    dialogVisible.value = false
    await load()
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    saving.value = false
  }
}
</script>

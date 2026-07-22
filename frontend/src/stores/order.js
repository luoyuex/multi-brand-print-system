import { defineStore } from 'pinia'
import { ref, computed, watch } from 'vue'

const DRAFT_KEY = 'order_draft'

function loadDraft() {
  try {
    const raw = localStorage.getItem(DRAFT_KEY)
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

export const useOrderStore = defineStore('order', () => {
  const draft = loadDraft()

  const storeId  = ref(draft?.storeId  ?? null)
  const brandId  = ref(draft?.brandId  ?? null)   // 同步品牌，供 OrderEntry 恢复
  const items    = ref(draft?.items    ?? [])      // { product_code, product_name, spec, qty, price, manual_price, is_replacement }

  const total = computed(() =>
    items.value.reduce((sum, item) => sum + item.qty * item.price, 0)
  )

  // 任意字段变化时自动写入 localStorage
  watch([storeId, brandId, items], () => {
    localStorage.setItem(DRAFT_KEY, JSON.stringify({
      storeId: storeId.value,
      brandId: brandId.value,
      items:   items.value,
    }))
  }, { deep: true })

  function addItem(product, qty = 1, asReplacement = false) {
    // 仅合并「补货状态相同」的同款商品，
    // 允许同一商品同时存在「正常售卖行」和「补货行」
    const existingIdx = items.value.findIndex(
      (i) => i.product_code === product.code && !!i.is_replacement === asReplacement
    )
    if (existingIdx !== -1) {
      const [existing] = items.value.splice(existingIdx, 1)
      existing.qty += qty
      items.value.unshift(existing)
      return
    }
    const item = {
      product_code:  product.code,
      product_name:  product.name,
      spec:          product.spec,
      qty,
      price:         product.price,
      manual_price:  false,
      is_replacement: asReplacement,
    }
    if (asReplacement) {
      // 补货：记住原价，单价归 0（坏损免费补发）
      item.orig_price = product.price
      item.price      = 0
    }
    items.value.unshift(item)
  }

  function updateItem(index, field, value) {
    if (field === 'price') {
      items.value[index].price       = value
      items.value[index].manual_price = true
    } else {
      items.value[index][field] = value
    }
  }

  // 切换「补货」：坏损免费补发，单价强制 0；取消时恢复原价
  function toggleReplacement(index) {
    const item = items.value[index]
    if (!item.is_replacement) {
      // 标记为补货：记住当前原价，价格归 0
      item.orig_price   = item.price
      item.price        = 0
      item.is_replacement = true
    } else {
      // 取消补货：恢复原价
      item.price        = item.orig_price ?? 0
      item.is_replacement = false
      delete item.orig_price
    }
  }

  function removeItem(index) {
    items.value.splice(index, 1)
  }

  function clear() {
    storeId.value = null
    brandId.value = null
    items.value   = []
    localStorage.removeItem(DRAFT_KEY)
  }

  return { storeId, brandId, items, total, addItem, updateItem, toggleReplacement, removeItem, clear }
})

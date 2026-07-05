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
  const items    = ref(draft?.items    ?? [])      // { product_code, product_name, spec, qty, price, manual_price }

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

  function addItem(product, qty = 1) {
    const existingIdx = items.value.findIndex((i) => i.product_code === product.code)
    if (existingIdx !== -1) {
      const [existing] = items.value.splice(existingIdx, 1)
      existing.qty += qty
      items.value.unshift(existing)
    } else {
      items.value.unshift({
        product_code: product.code,
        product_name: product.name,
        spec:         product.spec,
        qty,
        price:        product.price,
        manual_price: false,
      })
    }
  }

  function updateItem(index, field, value) {
    if (field === 'price') {
      items.value[index].price       = value
      items.value[index].manual_price = true
    } else {
      items.value[index][field] = value
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

  return { storeId, brandId, items, total, addItem, updateItem, removeItem, clear }
})

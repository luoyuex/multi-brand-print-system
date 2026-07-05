import { defineStore } from 'pinia'
import { ref } from 'vue'
import { brandApi } from '../api'

export const useBrandStore = defineStore('brand', () => {
  const brands = ref([])
  const currentBrand = ref(null)

  async function fetchBrands() {
    brands.value = await brandApi.list()
    if (brands.value.length && !currentBrand.value) {
      currentBrand.value = brands.value[0]
    }
  }

  function selectBrand(brand) {
    currentBrand.value = brand
  }

  return { brands, currentBrand, fetchBrands, selectBrand }
})

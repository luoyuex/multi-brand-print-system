import { createRouter, createWebHistory } from 'vue-router'
import OrderEntry  from '../views/OrderEntry.vue'
import PrintQueue  from '../views/PrintQueue.vue'
import Bills       from '../views/Bills.vue'
import Products    from '../views/Products.vue'
import Brands      from '../views/Brands.vue'
import Stores      from '../views/Stores.vue'

const routes = [
  { path: '/',         component: OrderEntry },
  { path: '/print',    component: PrintQueue },
  { path: '/bills',    component: Bills      },
  { path: '/products', component: Products  },
  { path: '/brands',   component: Brands    },
  { path: '/stores',   component: Stores    },
]

export default createRouter({
  history: createWebHistory(),
  routes,
})
